# 🚀 NexDev 3.0 - Integration Plan
**Enhancing Tier System with MO v2.0 Learning + Antfarm Workflows**  
**Date:** 2026-03-03 09:24 CST  
**Backup:** `nexdev-backup-20260303_092356/`

---

## Current State Analysis

### What Exists Now ✅
```
~/.openclaw/workspace/nexdev/
├── nexdev.py (38KB)           # Orchestrator with 6-tier routing
├── engine.py (24KB)           # API execution layer
├── config.json                # Tier definitions, cost limits
└── logs/                      # Execution tracking
```

**Strengths:**
- ✅ Multi-provider API support (Anthropic, Google, Alibaba, xAI)
- ✅ Tiered routing (Strategic → Utility based on triggers)
- ✅ Self-correction loops (escalate on failures)
- ✅ ClawVault memory integration
- ✅ Cost tracking & limits ($20/day default)

**Gaps MO v2.0 Fills:**
- ❌ No learning from historical success rates
- ❌ Static tier rules (not adaptive)
- ❌ No confidence scoring for quality control
- ❌ Limited session context awareness
- ❌ No RL feedback loop from user ratings

---

## Integration Strategy: Layering, Not Replacing

### Guiding Principles

1. **Preserve Core Architecture** - Keep NexDev's tier system intact
2. **Add Intelligence Layers** - MO modules sit ABOVE static tiers
3. **Fallback Hierarchy** - Learning data → Tier rules → Default
4. **Unified Tracking** - Merge MO performance DB with NexDev logs
5. **Backward Compatibility** - All existing workflows continue

### Data Flow Diagram

```
User Query
    ↓
[NEW] MO Topic Extractor (detect technical topic)
    ↓
[NEW] Performance DB Check (historical best model?)
    ↓
[EXISTING] NexDev Tier Router (fallback to tier rules)
    ↓
[EXISTING] Engine API Call (execute on selected model)
    ↓
[NEW] Confidence Assessor (quality self-check)
    ↓
[NEW] Session Awareness (maintain context?)
    ↓
[NEW] Performance Logger (log result to learning DB)
    ↓
[NEW] RL Feedback (optionally prompt for rating)
    ↓
Result to User
```

---

## Phase 1: MO Module Integration (Day 1)

### 1.1 Topic Extractor Integration

**File:** `nexdev.py`  
**Function:** Modify `route_to_tier()` to check MO topics first

```python
# BEFORE (existing code in nexdev.py):
def route_to_tier(query: str) -> str:
    for tier_name, tier_config in TIERS.items():
        if any(trigger in query.lower() for trigger in tier_config['triggers']):
            return tier_name
    return 'execution'  # default

# AFTER (with MO integration):
from memory.topic_extractor import extract_topic
from memory.performance_logger import get_best_model_for_topic

def route_to_tier_and_model(query: str) -> Tuple[str, Optional[str]]:
    """Route using MO learning first, then fall back to tier rules."""
    
    # Step 1: Extract technical topic
    matches = extract_topic(query)
    if not matches:
        return ('execution', None)  # No topic detected
    
    top_topic = matches[0].topic
    
    # Step 2: Check performance database for learned winner
    learned_model = get_best_model_for_topic(top_topic)
    
    # If strong learning signal (≥3 queries, ≥0.85 confidence)
    if learned_model and learned_model['recommendation'] == 'strong':
        # Return model directly (skip tier logic for now)
        return ('execution', learned_model['model_id'])
    
    # Step 3: Fall back to existing tier rules
    for tier_name, tier_config in TIERS.items():
        if any(trigger in query.lower() for trigger in tier_config['triggers']):
            return (tier_name, None)
    
    return ('execution', None)
```

**Changes Required:**
- Add import: `from pathlib import Path; sys.path.insert(0, str(Path.home() / 'memory'))`
- Replace `route_to_tier()` call with new function
- Store both tier AND specific model recommendation

---

### 1.2 Performance Logger Integration

**File:** `engine.py`  
**Function:** Modify `execute_query()` to log results to MO DB

```python
# BEFORE (existing):
def execute_query(model_id: str, prompt: str) -> Dict[str, Any]:
    response = call_api(model_id, prompt)
    cost = calculate_cost(model_id, tokens_in, tokens_out)
    return {'response': response, 'cost': cost}

# AFTER (with MO logging):
from memory.performance_logger import log_query_result
from memory.confidence_assessor import assess_confidence

def execute_query_with_logging(model_id: str, prompt: str, 
                               topic: str, success: bool = True) -> Dict[str, Any]:
    response = call_api(model_id, prompt)
    tokens_in = estimate_tokens(prompt)
    tokens_out = estimate_tokens(response['content'])
    cost = calculate_cost(model_id, tokens_in, tokens_out)
    
    # Assess response quality
    confidence = assess_confidence(response['content']).score
    
    # Log to MO performance database
    log_query_result(
        topic=topic,
        model_used=model_id,
        success=success,
        tokens_input=tokens_in,
        tokens_output=tokens_out,
        cost_usd=cost,
        confidence_score=confidence,
        query_text=prompt[:500],
        response_summary=response['content'][:200]
    )
    
    return {'response': response, 'cost': cost, 'confidence': confidence}
```

**Changes Required:**
- Add imports for MO modules
- Capture topic from routing step
- Pass success status (True unless exception raised)
- Update error handling to mark `success=False`

---

### 1.3 Session Awareness Integration

**File:** `nexdev.py`  
**Function:** Maintain model consistency across conversation turns

```python
# Add to main interaction loop:
from memory.session_aware_router import update_session, get_current_model

def process_query(query: str, conversation_turn: int) -> str:
    # Get current sticky session state
    current_model = get_current_model()
    
    # Route with optional model override
    tier, recommended_model = route_to_tier_and_model(query)
    
    # Use recommended model OR session-persistent model OR tier default
    if recommended_model:
        final_model = recommended_model
    elif current_model and _should_keep_session_model(query):
        final_model = current_model
    else:
        final_model = get_default_model_for_tier(tier)
    
    # Execute
    result = execute_query_with_logging(final_model, query, topic)
    
    # Update session state
    update_session(topic=topic, model=final_model)
    
    return result['response']['content']
```

**Helper Function:**
```python
def _should_keep_session_model(new_query: str) -> bool:
    """Decide if we maintain current model or switch."""
    from memory.session_aware_router import suggest_model_switch
    suggestion = suggest_model_switch(new_query)
    return suggestion.get('recommendation') == 'keep'
```

---

### 1.4 Cost Monitor Enhancement

**File:** `config.json` + `engine.py`  
**Integration:** Replace basic cost tracking with MO real-time monitoring

**Update config.json:**
```json
{
  "version": "3.0",
  "name": "NexDev Orchestrator v3",
  "cost_monitoring": {
    "use_mo_monitor": true,
    "daily_max_usd": 20.00,
    "per_query_max_usd": 5.00,
    "alert_threshold_pct": 80,
    "prefer_cheapest_viable": true
  }
}
```

**Update engine.py:**
```python
from memory.cost_monitor import check_budget, calculate_query_cost

def validate_budget_before_exec(model_id: str, query_complexity: str) -> Tuple[bool, str]:
    """Check if execution stays within budget."""
    check = check_budget(model_id, complexity=query_complexity)
    
    if not check.within_budget:
        alert_msg = f"⚠️ Budget warning: {check.alerts}"
        if check.alternatives:
            alt = check.alternatives[0]
            alert_msg += f"\n   Suggest: {alt['model_name']} (saves ${alt['savings']:.4f})"
        return False, alert_msg
    
    return True, "Budget OK"
```

---

## Phase 2: Antfarm Workflow Bridges (Day 2)

### 2.1 Trigger Antfarm from NexDev

**New File:** `~/.openclaw/workspace/nexdev/antfarm_bridge.py`

```python
#!/usr/bin/env python3
"""Bridge between NexDev task detection and Antfarm workflow execution."""

import subprocess
import json
from pathlib import Path
from datetime import datetime

ANTFARM_CLI = Path.home() / '.openclaw/workspace/antfarm/dist/cli/cli.js'

WORKFLOW_MAPPING = {
    'bug-fix': {
        'keywords': ['fix bug', 'error', 'broken', 'test fail', 'debug'],
        'workflow_id': 'bug-fix',
        'timeout_min': 30
    },
    'feature-dev': {
        'keywords': ['implement feature', 'add endpoint', 'create component'],
        'workflow_id': 'feature-dev',
        'timeout_min': 120
    },
    'security-audit': {
        'keywords': ['security audit', 'vulnerability', 'OWASP'],
        'workflow_id': 'security-audit',
        'timeout_min': 60
    }
}

def detect_antfarm_task(query: str) -> dict:
    """Detect if query should trigger an Antfarm workflow."""
    query_lower = query.lower()
    
    for task_type, config in WORKFLOW_MAPPING.items():
        if any(kw in query_lower for kw in config['keywords']):
            return {
                'trigger_antfarm': True,
                'task_type': task_type,
                'workflow_id': config['workflow_id'],
                'timeout_min': config['timeout_min']
            }
    
    return {'trigger_antfarm': False}

def run_antfarm_workflow(workflow_id: str, task_description: str) -> dict:
    """Execute Antfarm workflow and return result."""
    cmd = [
        'node', str(ANTFARM_CLI), 'workflow', 'run',
        workflow_id, task_description
    ]
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=1800  # 30 min max
        )
        
        return {
            'success': result.returncode == 0,
            'stdout': result.stdout,
            'stderr': result.stderr,
            'exit_code': result.returncode
        }
    except subprocess.TimeoutExpired:
        return {'success': False, 'error': 'Workflow timeout'}
    except Exception as e:
        return {'success': False, 'error': str(e)}

def report_workflow_result(task_type: str, result: dict):
    """Report Antfarm workflow result back to NexDev memory."""
    from memory.performance_logger import log_query_result
    
    # Map workflow success to performance tracking
    log_query_result(
        topic=f"antfarm-{task_type}",
        model_used="antfarm-workflow",
        success=result['success'],
        tokens_input=0,  # N/A for workflows
        tokens_output=0,
        cost_usd=0.10,  # Estimate (no direct billing)
        confidence_score=1.0 if result['success'] else 0.0,
        query_text="",
        response_summary=str(result)[:500]
    )
```

### 2.2 Integrate Bridge into NexDev Main Loop

**Update:** `nexdev.py`

```python
from antfarm_bridge import detect_antfarm_task, run_antfarm_workflow, report_workflow_result

def process_query_enhanced(query: str) -> str:
    # Step 1: Check if Antfarm workflow should trigger
    antfarm_check = detect_antfarm_task(query)
    
    if antfarm_check['trigger_antfarm']:
        print(f"🤖 Triggering Antfarm workflow: {antfarm_check['task_type']}")
        result = run_antfarm_workflow(
            antfarm_check['workflow_id'],
            query
        )
        
        # Report to performance DB
        report_workflow_result(antfarm_check['task_type'], result)
        
        if result['success']:
            return f"✅ Antfarm completed: {result['stdout'][:500]}"
        else:
            return f"❌ Antfarm failed: {result.get('error', 'Unknown error')}"
    
    # Step 2: Fall back to normal NexDev processing
    return process_query(query)
```

---

## Phase 3: Unified Dashboard

**New File:** `~/.openclaw/workspace/nexdev/dashboard.py`

```python
#!/usr/bin/env python3
"""Combined NexDev + MO dashboard."""

import json
from pathlib import Path
from datetime import datetime

NEXDEV_LOG = Path.home() / '.openclaw/workspace/nexdev/logs/executions.jsonl'
MO_COST_LOG = Path.home() / '.openclaw/workspace/memory/daily_costs.json'

def generate_dashboard() -> str:
    """Generate unified overview of NexDev + MO activity."""
    
    lines = []
    lines.append("=" * 70)
    lines.append("NEXDEV V3.0 DASHBOARD - COMBINED VIEW")
    lines.append("=" * 70)
    
    # NexDev stats
    nexdev_stats = _parse_nexdev_logs()
    lines.append("\n📊 NEXDEV EXECUTIONS (Last 7 Days)")
    lines.append(f"  Total queries: {nexdev_stats['total_queries']}")
    lines.append(f"  Total cost: ${nexdev_stats['total_cost']:.4f}")
    lines.append(f"  Success rate: {nexdev_stats['success_rate']:.0%}")
    
    # MO stats
    mo_stats = _parse_mo_logs()
    lines.append("\n🧠 MO LEARNING DATABASE")
    lines.append(f"  Topics tracked: {mo_stats['topics_count']}")
    lines.append(f"  Queries logged: {mo_stats['queries_count']}")
    lines.append(f"  Strong recommendations: {mo_stats['strong_recs']}")
    
    # Top models
    lines.append("\n🏆 TOP PERFORMING MODELS")
    for rank, model in enumerate(mo_stats['top_models'][:3], 1):
        lines.append(f"  {rank}. {model['model']} ({model['success_rate']:.0%} success)")
    
    lines.append("\n" + "=" * 70)
    return "\n".join(lines)

if __name__ == "__main__":
    print(generate_dashboard())
```

---

## Testing Checklist

After each phase, verify:

### Phase 1 Tests
- [ ] Topic extraction detects AWS/Lambda/CORS correctly
- [ ] Performance DB logs after each query
- [ ] Confident responses score higher than uncertain ones
- [ ] Session maintains model during related topics

### Phase 2 Tests
- [ ] Bug-fix query triggers Antfarm workflow
- [ ] Workflow result reported back to MO DB
- [ ] Error handling works if Antfarm unavailable

### Phase 3 Tests
- [ ] Dashboard shows combined stats
- [ ] Costs from both systems sum correctly
- [ ] Top models ranked accurately

---

## Rollback Procedure

If issues arise:

```bash
# Stop all processes
pkill -f "python.*nexdev" || true

# Restore from backup
cd ~/.openclaw/workspace
rm -rf nexdev
mv nexdev-backup-* nexdev

# Restart gateway
openclaw gateway restart
```

---

## Timeline

| Phase | Duration | Deliverable |
|-------|----------|-------------|
| **Phase 1A** | 2 hrs | Topic extractor + router integration |
| **Phase 1B** | 2 hrs | Performance logger + confidence scorer |
| **Phase 1C** | 1 hr | Session awareness + cost monitor |
| **Phase 2** | 2 hrs | Antfarm bridge integration |
| **Phase 3** | 1 hr | Unified dashboard |
| **Testing** | 2 hrs | Full validation suite |
| **TOTAL** | ~10 hrs | Complete over 2 days |

---

Ready to proceed? I'll start with **Phase 1A** (topic extractor integration) next. Confirm when you want me to begin actual file modifications.
