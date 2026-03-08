# Optimus Heartbeat Preferences

**Frequency:** Low — Only alert on urgent/important items. Skip routine reminders.

**Alert on:**
- Urgent emails (<2 hours old, needs action)
- Calendar events <30 min away
- System issues or failures (medic checks)
- Cost anomalies (> $20/day, > $100/week)
- Active projects with pending steps >24h old

**Do NOT alert on:**
- Routine meeting reminders (user has calendar)
- Pills/medication (user has own system)
- Minor updates or "checking in" messages
- Information that repeats within 4+ hours

---

# 🚀 DEPLOYED FEATURES (All Live)

## Security Pipeline
✅ **Auto-Rotation Reminder** - `auto-rotation-reminder.sh`  
   • Tracks key ages in Keychain  
   • Sends Telegram alerts at 90 days  
   • Runs via cron: `0 9 * * *`

✅ **Pre-commit Scanner** - `pre_commit_scanner.py`  
   • Blocks commits with exposed secrets  
   • Scans: AWS, Anthropic, Google, XAI, Alibaba, Stripe, GitHub  

## Cost Tracking v3.0
✅ **Real Billing Integration** - `cost-tracking-v3.js`  
   • AWS CloudWatch metrics API  
   • Claude Platform CSV parsing  
   • OpenClaw session cross-check  
   • Usage: `cost-real daily|weekly`

## Project Management
✅ **Visual Dashboard** - `project-dashboard.js`  
   • HTML web UI with status overview  
   • Stale project detection (>7 days idle)  
   • Dependency graph builder  
   • Usage: `dashboard` (opens browser)

## Health Monitoring
✅ **Medic Workflow** - `medic.sh`  
   • Continuous health checks every 10min  
   • Monitors: Gateway, sessions, cron, keys, costs  
   • Alerts via Telegram on failures  
   • Usage: `medic --watch` (foreground) or `--once` (cron)

## Antfarm Workflows
✅ **Deployed** - All 4 workflows active  
   • `bug-fix` - Code bug resolution  
   • `feature-dev` - Pair programming  
   • `model-orchestrator` - MO optimization  
   • `security-audit` - Quarterly audits  
   • Usage: `antfarm run <workflow> "task"`

## Model Orchestrator v2.0
✅ **Production Mode** - Qwen cascade routing  
   • Email/Tasks: qwen-coder → kimi-k2.5 → gemini → grok  
   • Drafts: qwen-turbo → gemini → kimi  
   • Cost savings: 85% cheaper on extraction  
   • Attribution tags enabled

---

# Smart Penny Pincher with ClawVault Context

## Before Every Query

1. **Check Active Projects** (`~/memory/active_projects.json`)
   - If continuing a project → Use same model for consistency
   - Load project context into system prompt
   - Reference completed/pending steps

2. **Check Model Performance** (`~/memory/model_performance.json`)
   - Query topic in performance database
   - Use model with highest success rate for topic
   - Consider cost vs. reliability trade-off

3. **Check Recent Memory** (`memory/YYYY-MM-DD.md`)
   - Similar queries in last 48h?
   - Same approach already tried?
   - Avoid repeating failed attempts

## Project State Management

**Track:**
- Current step in progress
- Model being used
- Completed steps with timestamps
- Blockers or dependencies
- Next actions

**Update After Each Session:**
- Mark steps complete
- Log model performance
- Save context for next session
- Update `active_projects.json`

## Smart Model Selection

```
IF project_active AND same_topic:
    → Continue with current model

ELSE IF topic_in_performance_db AND success_rate > 80%:
    → Use proven model for topic

ELSE IF complexity = HIGH AND new_topic:
    → Start with Sonnet, track performance

ELSE:
    → Use standard penny pincher chain
```

## Model Performance Tracking

Track per topic:
- Success/failure count
- Average cost per 1K tokens
- Average response time
- Best use cases

Topics tracked:
- aws-infrastructure
- lambda-development
- snowflake-integration
- api-gateway-cors
- cognito-user-management
- clawvault-development
- system-architecture
- debugging-troubleshooting

---

# Smart Model Orchestrator v2.0 — Unified Cascade System

## Core Flow (ClawVault-Integrated)

**Step 1: ClawVault Memory Lookup** (before any routing)
- Search `~/memory/` for matching project/topic/context
- If match found AND confidence >= 0.8 → Use same model as previous session
- If no match → Proceed to Step 2

**Step 2: Complexity Detection**
Based on query patterns, route to appropriate tier:

| Task Type | Primary Model | Escalation Chain |
|-----------|--------------|------------------|
| Simple Q&A / Facts | `QwenFlash` (Tier 1) | 1 escalation max |
| Code Generation/Fixes | `QwenCoder` (Tier 2) | → Qwen35 → Sonnet → Opus |
| Architecture Design | `Qwen35` (Tier 3) | → Sonnet → Opus |
| Long Docs / Summaries | `GeminiFlash` (Tier 2) | → Kimi (agent swarm) → Pro |
| Vision / Images | `GeminiFlash` (Tier 2) | → Sonnet (vision) |
| Agent Orchestration | `Kimi` (forced, Tier 3) | agent_swarm feature |
| Creative Content | `Sonnet` (Tier 5) | → Opus |
| Deep Research | `Kimi` (Tier 3) | → Pro → Opus |

**Step 3: Self-Evaluation & Confidence Scoring**
Model must output JSON:
```json
{
  "status": "success" | "escalate",
  "confidence_score": 0.0-1.0,
  "answer": "...",
  "reasoning": "brief explanation"
}
```

**Thresholds:**
- `confidence >= 0.85`: Auto-accept ✅
- `confidence 0.70-0.85`: Manual review ⚠️
- `confidence < 0.70`: Auto-escalate 📈

**Step 4: Escalation Chain** (only if needed)
Follow tier progression: Tier 1 → Tier 2 → Tier 3 → Tier 4 → Tier 5
Max 3 escalations per query before flagging as unresolved.

---

## Complete Model Stack (Cost-Ranked)

### Tier 1: Ultra-Cheap ($0.05-0.10/1M input)
| Model | Alias | Use Case |
|-------|-------|----------|
| `alibaba-sg/qwen-turbo` | QwenFlash | Quick facts, extraction, simple queries |
| `google/gemini-2.0-flash-lite` | GeminiLite | Fast responses, light reasoning |

### Tier 2: Standard ($0.10-0.30/1M input)
| Model | Alias | Use Case |
|-------|-------|----------|
| `google/gemini-2.5-flash` | GeminiFlash | Summaries, multi-turn, vision |
| `google/gemini-2.0-flash` | Gemini20Flash | OCR, image understanding |
| `xai/grok-3-mini` | GrokMini | Quick reasoning, casual chat |
| `alibaba-sg/qwen-coder` | QwenCoder | Code gen, debugging, refactoring |

### Tier 3: Advanced ($0.40-0.60/1M input)
| Model | Alias | Use Case | Special Features |
|-------|-------|----------|------------------|
| `alibaba-sg/qwen3.5-122b-a10b` | Qwen35 | Complex coding, architecture, long docs | Escalation: Sonnet → Opus |
| `alibaba-sg/qwen-plus` | QwenPlus | Balanced performance, large context | - |
| `moonshot/kimi-k2.5` | Kimi | Agent swarm, very long docs | **Agent Swarm**: Spawns army of sub-agents with different roles |

### Tier 4: Premium Reasoning ($1.00-1.25/1M input)
| Model | Alias | Use Case |
|-------|-------|----------|
| `anthropic/claude-3-haiku-20240307` | Haiku | Fast premium responses |
| `alibaba-sg/qwen-max` | QwenMax | Highest quality outputs |
| `google/gemini-2.5-pro` | GeminiPro | Premium vision+reasoning, ultra-long contexts |

### Tier 5: Expert Only ($3.00-5.00/1M input)
| Model | Alias | Use Case | Cascade Role |
|-------|-------|----------|--------------|
| `xai/grok-4` | Grok | Advanced reasoning, real-time knowledge | - |
| `anthropic/claude-sonnet-4-6` | Sonnet | Complex problems, nuanced reasoning | **Primary Escalation Target** |
| `anthropic/claude-opus-4-6` | Opus | Mission-critical, impossible problems | **Final Escalation** |
| `openai/gpt-4o` | GPT4o | Alternative expert opinion | Cross-validation |

---

## Manual Override Commands

```bash
/model QwenFlash   # Cheapest mode for simple queries
/model GeminiLite  # Fast light reasoning
/model GrokMini    # Quick iteration/casual
/model QwenCoder   # Code-focused tasks
/model Qwen35      # Complex reasoning & heavy coding
/model Kimi        # Agent swarm orchestration / long documents
/model Sonnet      # Quality mode / primary escalation target
/model Opus        # Maximum capability / ultimate escalation
/model default     # Back to automatic cascade
```

---

## Global Chat Group Support

✅ Works across all channels: Telegram, Discord, WhatsApp, Slack

**Session Context Tracking:**
- Project state saved to `~/memory/active_projects.json`
- Continues seamlessly across turns and sessions
- ClawVault memory searched before every routing decision

**Cross-Session Memory:**
- Same conversation flows between groups without losing context
- Project history preserved via ClawVault
- Model preference learned per topic/project

---

## Performance Tracking

**Track per topic:**
- Success/failure rate
- Average cost per 1K tokens
- Average response time
- Confidence score distribution

**Tracked Topics:**
- aws-infrastructure, lambda-development
- snowflake-integration, api-gateway-cors
- cognito-user-management, clawvault-development
- system-architecture, debugging-troubleshooting
- travel-research, points-transfer-bonuses

**Check status:** `/status` shows current model + session costs
