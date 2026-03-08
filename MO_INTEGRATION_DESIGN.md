# MO Full Integration Design — Gap Analysis

*Created: 2026-03-03 | Status: IN PROGRESS*

---

## Current State ✅ What Works

| Component | Status | Location |
|-----------|--------|----------|
| Tier-based routing | ✅ Working | `MO_ROUTING.md`, `AGENTS.md` |
| Model switching API | ✅ Working | `session_status(model="alias")` |
| Attribution format | ✅ Working | `SOUL.md` (`— MO model-name`) |
| Learning database | ✅ Exists | `~/memory/model_performance.json` |
| Topic tracking | ⚠️ Minimal | Only 3 topics in DB |
| Cost logging | ⚠️ Partial | Logged but not driving decisions |

---

## Missing Components ❌ What Needs To Be Built

### 1. **Topic Extraction Engine** (NEW)

**Purpose:** Automatically detect topic from query to match with learning DB

**Current Gap:** No systematic topic detection → routing ignores historical data

**Design:**
```python
def extract_topic(query: str) -> list[str]:
    """
    Extract topics from query using keyword matching + LLM classification.
    
    Example: "Fix Lambda CORS headers on API Gateway"
    → ["lambda-development", "api-gateway-cors", "aws-infrastructure"]
    """
    # Step 1: Keyword extraction (fast, no API call)
    TOPIC_KEYWORDS = {
        "lambda-development": ["lambda", "aws lambda", "cloudfunction", "function deployment"],
        "api-gateway-cors": ["cors", "cross-origin", "api gateway", "http error 504"],
        "snowflake-integration": ["snowflake", "data warehouse", "sql connector"],
        "email-processing": ["email", "outlook", "gmail", "smtp", "sendgrid"],
        "web-development": ["react", "typescript", "javascript", "frontend", "css"],
        "database-design": ["schema", "table", "database", "migration"],
        # ... 20+ more topics
    }
    
    matches = []
    for topic, keywords in TOPIC_KEYWORDS.items():
        if any(k.lower() in query.lower() for k in keywords):
            matches.append(topic)
    
    # Step 2: If ≥2 keywords match → high confidence topic
    if len(matches) >= 2:
        return matches[:2]  # Return top 2
    
    # Step 3: Single keyword match → classify with cheap LLM
    if len(matches) == 1:
        return [matches[0]]
    
    # Step 4: No matches → fallback to tier routing
    return ["general"]


def classify_with_llm(query: str, candidates: list[str]) -> str:
    """Use QwenFlash ($0.05/M) to classify ambiguous queries"""
    prompt = f"""Classify this task into one category: {', '.join(candidates)}
    
Task: "{query}"
Answer with just the category name."""
    response = qwen_flash_complete(prompt, max_tokens=20)
    return response.strip().lower()
```

**Files to Create:**
- `~/.openclaw/workspace/memory/topic_extractor.py`
- Add to `MO_ROUTING.md`: Step 0 — extract topic before routing

---

### 2. **Learning-Based Routing Logic** (UPDATE)

**Purpose:** Check performance DB BEFORE falling back to static tiers

**Current Gap:** Always uses tier logic → misses historical winners

**Updated Flow:**
```
1️⃣ User sends message
    ↓
2️⃣ Extract topic(s) from query (TOPIC EXTRACTOR)
    ↓
3️⃣ Query Performance DB for topic
   - Search ~/memory/model_performance.json by_topic.{topic}.model_scores
   - Find model with highest success_rate AND usage_count > 3
   - If confidence ≥ 0.85 → Route to that model IMMEDIATELY
    ↓
4️⃣ If no learning data OR low confidence → Fall back to tier mapping
    ↓
5️⃣ Compare current model vs target → Switch if needed
    ↓
6️⃣ Answer on optimal model
    ↓
7️⃣ Log result to performance DB
```

**Algorithm:**
```python
def get_best_model_for_topic(topic: str) -> dict:
    """Return best model for topic based on performance data"""
    perf = json.loads(PERF_DB.read_text())
    by_topic = perf.get("by_topic", {})
    
    topic_data = by_topic.get(topic, {"model_scores": {}})
    model_scores = topic_data["model_scores"]
    
    if not model_scores:
        return None  # No data, fall back to tier
    
    # Score models by: success_rate * log(usage_count + 1)
    scored = []
    for model, scores in model_scores.items():
        rate = scores.get("success_rate", 0)
        count = scores.get("usage_count", 0)
        
        # Weight: 70% success rate, 30% usage volume
        score = (rate * 0.7) + ((min(count / 10, 1.0)) * 0.3)
        
        # Bonus if success_rate ≥ 0.95
        if rate >= 0.95:
            score += 0.1
        
        scored.append({"model": model, "score": score, "details": scores})
    
    # Sort by score descending
    ranked = sorted(scored, key=lambda x: -x["score"])
    
    # Only recommend if score ≥ 0.75 AND usage_count ≥ 3
    top = ranked[0]
    if top["score"] < 0.75 or top["details"]["usage_count"] < 3:
        return None  # Insufficient data
    
    return {
        "model_id": top["model"],
        "success_rate": top["details"]["success_rate"],
        "usage_count": top["details"]["usage_count"],
        "confidence_score": top["score"],
        "recommendation": "strong" if top["score"] >= 0.85 else "weak"
    }
```

**Integration Points:**
- Modify `MO_ROUTING.md`: Replace Step 2 with "Check Learning DB First"
- Modify `model_router.py`: Add `get_best_model_for_topic()` function

---

### 3. **Automated Logging After Every Query** (NEW)

**Purpose:** Update performance DB after every response to build learning over time

**Current Gap:** Logs are manual / sporadic → insufficient training data

**Design:**
```python
def log_query_result(topic: str, model_used: str, result: dict):
    """
    Log query result to performance DB.
    
    Called automatically after every response.
    
    Input:
      topic: detected topic ("lambda-development", "general", etc.)
      model_used: full model ID ("anthropic/claude-sonnet-4-6")
      result: {
          "success": True/False,
          "cost_usd": 0.003,
          "tokens_used": 1234,
          "confidence_score": 0.95,
          "escalated": False,
          "escalation_step": 0
      }
    """
    PERF_DB = Path("~/memory/model_performance.json")
    perf = json.loads(PERF_DB.read_text()) if PERF_DB.exists() else {"by_topic": {}}
    
    # Initialize topic if new
    if topic not in perf["by_topic"]:
        perf["by_topic"][topic] = {"model_scores": {}, "total_queries": 0}
    
    topic_data = perf["by_topic"][topic]
    topic_data["total_queries"] = topic_data.get("total_queries", 0) + 1
    
    # Update model stats
    if model_used not in topic_data["model_scores"]:
        topic_data["model_scores"][model_used] = {
            "success_count": 0,
            "failure_count": 0,
            "total_cost": 0.0,
            "avg_confidence": 0.0,
            "usage_count": 0,
            "success_rate": 0.0,
            "last_used": None
        }
    
    model_stats = topic_data["model_scores"][model_used]
    model_stats["usage_count"] += 1
    model_stats["total_cost"] = result.get("cost_usd", 0)
    model_stats["last_used"] = datetime.now(timezone.utc).isoformat()
    
    if result.get("success"):
        model_stats["success_count"] += 1
    else:
        model_stats["failure_count"] += 1
    
    model_stats["success_rate"] = model_stats["success_count"] / model_stats["usage_count"]
    
    # Rolling average for confidence
    total_conf = model_stats["avg_confidence"] * (model_stats["usage_count"] - 1)
    total_conf += result.get("confidence_score", 0.85)
    model_stats["avg_confidence"] = total_conf / model_stats["usage_count"]
    
    # Write back
    PERF_DB.write_text(json.dumps(perf, indent=2))


def auto_log():
    """
    Hook to run at end of EVERY response.
    
    Called from SOUL.md post-flight check.
    """
    # Extract last topic discussed
    topic = extract_topic(last_user_message)
    
    # Get model used for response
    model_used = current_model_id  # From session_status
    
    # Build result object
    result = {
        "success": True,  # Or infer from error messages
        "cost_usd": estimate_cost(model_used, tokens_sent),
        "tokens_used": tokens_sent,
        "confidence_score": self_assess_confidence(),  # Optional
        "escalated": was_escalated,
        "escalation_step": escalation_count
    }
    
    log_query_result(topic, model_used, result)
```

**Trigger Mechanism:**
- Option A: Post-flight check in AGENTS.md ("After every response, log it")
- Option B: Automatic hook in OpenClaw gateway (requires code change)
- Option C: Manual trigger after important responses (`/log-this`)

Recommendation: Start with **Option A** (simplest), upgrade to Option B later.

---

### 4. **Confidence Self-Assessment** (OPTIONAL)

**Purpose:** Let model grade its own quality → train future routing

**Current Gap:** All logged results have 0.89 confidence → no variance

**Design:**
```python
def self_assess_confidence(response_text: str, user_followup: str = "") -> float:
    """
    Model grades its own response quality.
    
    Scale: 0.0-1.0 where 1.0 = perfect answer
    """
    indicators = {
        "positive": [
            "✅", "correctly", "successfully", "here's how", 
            "I've analyzed", "this solution", "tested"
        ],
        "negative": [
            "❌", "failed", "error", "troubleshoot", 
            "debug", "might work", "try this", "I'm not sure",
            "could be", "possibly", "maybe"
        ]
    }
    
    text_lower = (response_text + " " + user_followup).lower()
    
    pos_score = sum(1 for w in indicators["positive"] if w in text_lower)
    neg_score = sum(1 for w in indicators["negative"] if w in text_lower)
    
    # Base confidence: 0.85
    # +0.02 per positive indicator, -0.05 per negative
    confidence = 0.85 + (pos_score * 0.02) - (neg_score * 0.05)
    
    return max(0.0, min(1.0, confidence))  # Clamp 0-1
```

**Usage:**
```python
# In logging flow:
result["confidence_score"] = self_assess_confidence(response, next_user_query)
```

---

### 5. **Cost Tracking Per Topic** (ENHANCEMENT)

**Purpose:** Learn which models are cost-effective per topic

**Current Gap:** Cost logged but not analyzed by topic

**Enhancement:**
```python
def get_cost_efficient_model(topic: str, budget_max_usd: float = 5.0) -> str:
    """
    Return cheapest model that works well enough for topic.
    
    Budget constraint: Never recommend model > $X/query expected cost
    """
    perf = json.loads(PERF_DB.read_text())
    topic_data = perf.get("by_topic", {}).get(topic, {})
    model_scores = topic_data.get("model_scores", {})
    
    candidates = []
    for model, stats in model_scores.items():
        avg_cost_per_query = stats["total_cost"] / stats["usage_count"]
        success_rate = stats["success_rate"]
        
        # Only consider models with success_rate ≥ 0.80
        if success_rate < 0.80:
            continue
        
        # Only consider if within budget
        if avg_cost_per_query > budget_max_usd:
            continue
        
        # Score: Success rate / cost (efficiency metric)
        efficiency = success_rate / avg_cost_per_query if avg_cost_per_query > 0 else 0
        candidates.append({
            "model": model,
            "efficiency": efficiency,
            "avg_cost": avg_cost_per_query,
            "success_rate": success_rate
        })
    
    if not candidates:
        return None  # No good data, use tier fallback
    
    # Pick most efficient
    best = sorted(candidates, key=lambda x: -x["efficiency"])[0]
    return best["model"]
```

**Use Case:**
- For "email-processing" topic, if Sonnet costs $0.50/query at 95% success vs Flash at $0.01/query at 85% success
- Efficiency: Sonnet = 1.9, Flash = 85
- Recommendation: Flash (much more cost-efficient even if slightly lower quality)

---

### 6. **Periodic Learning Review & Pruning** (NEW)

**Purpose:** Prevent stale data from polluting routing decisions

**Current Gap:** Old topics stay forever, may not reflect current stack

**Design:**
```python
def prune_stale_topics(days_threshold: int = 60):
    """Remove topics with no activity in N days"""
    perf = json.loads(PERF_DB.read_text())
    cutoff = datetime.now(timezone.utc) - timedelta(days=days_threshold)
    
    for topic in list(perf.get("by_topic", {}).keys()):
        topic_data = perf["by_topic"][topic]
        
        # Check last update across all models
        last_update = None
        for model_stats in topic_data["model_scores"].values():
            last_used = model_stats.get("last_used")
            if last_used:
                updated = datetime.fromisoformat(last_used.replace('Z', '+00:00'))
                if last_update is None or updated > last_update:
                    last_update = updated
        
        if last_update is None or last_update < cutoff:
            del perf["by_topic"][topic]
            print(f"Pruned stale topic: {topic}")
    
    PERF_DB.write_text(json.dumps(perf, indent=2))
```

**Cron Job:**
- Run monthly: `prune_stale_topics(90)` (90-day threshold)
- Also notify user when pruning happens

---

### 7. **Learning Dashboard CLI** (NEW)

**Purpose:** Visualize model performance by topic

**Command:**
```bash
mo learn-stats           # Show all topics + model performance
mo learn-topics          # List tracked topics
mo learn-model <model>   # Show where specific model excels
mo learn-wipe            # Reset all learning data (with confirmation)
```

**Implementation:**
```python
def show_learning_stats():
    """Pretty-print model performance dashboard"""
    perf = json.loads(PERF_DB.read_text())
    by_topic = perf.get("by_topic", {})
    
    print("=" * 80)
    print("📊 LEARNING DATABASE — MODEL PERFORMANCE BY TOPIC")
    print("=" * 80)
    
    for topic, data in sorted(by_topic.items()):
        print(f"\n📁 {topic.upper()} ({data['total_queries']} queries)")
        print("-" * 40)
        
        for model, stats in sorted(data["model_scores"].items()):
            model_short = model.split("/")[-1]
            success = stats["success_rate"] * 100
            cost = stats["total_cost"] / stats["usage_count"] if stats["usage_count"] > 0 else 0
            
            bar = "█" * int(success // 5) + "░" * (20 - int(success // 5))
            
            print(f"  [{bar}] {model_short:<30} {success:>5.1f}%  ${cost:.4f}/query  {stats['usage_count']:>3}×")
    
    print("\n" + "=" * 80)
```

**File:** `~/.openclaw/bin/mo-learn` (or extend existing `mo` CLI)

---

## Implementation Roadmap

### Phase 1: Core Learning (Priority: 🔥 HIGH)

**Deliverables:**
1. Topic extraction engine (keyword matching)
2. `get_best_model_for_topic()` function
3. Auto-logging after every response
4. Updated `MO_ROUTING.md` with learning-first logic

**Time Estimate:** 2-3 hours  
**Impact:** Immediate learning-driven routing for technical topics

---

### Phase 2: Confidence Scoring (Priority: 🟡 MEDIUM)

**Deliverables:**
1. Self-assessment function
2. Integration into logging
3. Threshold tuning (auto-accept 0.85, escalate <0.7)

**Time Estimate:** 1 hour  
**Impact:** Better filtering of weak recommendations

---

### Phase 3: Cost Efficiency (Priority: 🟡 MEDIUM)

**Deliverables:**
1. Cost-per-query analysis by topic
2. Budget-constrained model selection
3. Cost-efficiency recommendations

**Time Estimate:** 1 hour  
**Impact:** Balance quality vs. cost per topic

---

### Phase 4: Maintenance (Priority: 🟢 LOW)

**Deliverables:**
1. Periodic pruning script (monthly cron)
2. Learning dashboard CLI
3. Wipe/reset capability

**Time Estimate:** 2 hours  
**Impact:** Long-term system health

---

### Phase 5: Advanced Features (Priority: 🔵 FUTURE)

**Deliverables:**
1. LLM-based topic classification (for new/unseen topics)
2. Cross-topic pattern recognition
3. Dynamic tier rebalancing
4. Real-time cost optimization during long conversations

**Time Estimate:** 5-10 hours  
**Impact:** Adaptive routing that evolves mid-session

---

## Recommended Order

1. **Start with Phase 1** — get basic learning working
2. **Phase 2** — add confidence scoring (quick win)
3. **Test for 1 week** — gather real data
4. **Phase 3** — optimize for cost-efficiency once we have 50+ data points
5. **Phase 4** — maintenance tools after system matures

**Total Time for Phases 1-3:** ~5 hours  
**Expected Outcome:** 50-80% of technical queries route via learning (vs. static tiers)

---

## Files To Modify/Create

### Create
- `~/.openclaw/workspace/memory/topic_extractor.py`
- `~/.openclaw/workspace/memory/performance_logger.py`
- `~/.openclaw/workspace/memory/learning_dashboard.py`
- `~/.openclaw/bin/mo-learn`

### Modify
- `MO_ROUTING.md` — Add learning-first logic
- `AGENTS.md` — Add logging hook
- `SOUL.md` — Already has attribution, add logging reminder
- `model_router.py` — Integrate `get_best_model_for_topic()`

---

## Key Decisions Needed

| Decision | Options | Recommendation |
|----------|---------|---------------|
| **Topic detection** | Keyword vs. LLM | Start with keyword (cheap), add LLM later |
| **Logging trigger** | Manual vs. Auto | Auto (post-flight check in AGENTS.md) |
| **Confidence scoring** | Heuristic vs. Learned | Heuristic (pattern matching) |
| **Pruning threshold** | 30 vs. 60 vs. 90 days | 90 days (avoid losing valid patterns) |
| **Budget constraint** | Global vs. Per-topic | Per-topic (different budgets per complexity) |

---

*Next step: Ask user which phase to prioritize and begin implementation.*
