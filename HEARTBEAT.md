# Optimus Heartbeat Preferences

**Frequency:** Low — Only alert on urgent/important items. Skip routine reminders.

**Alert on:**
- Urgent emails (<2 hours old, needs action)
- Calendar events <30 min away
- System issues or failures
- Cost anomalies
- Active projects with pending steps >24h old

**Do NOT alert on:**
- Routine meeting reminders (user has calendar)
- Pills/medication (user has own system)
- Minor updates or "checking in" messages
- Information that repeats within 4+ hours

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

# Penny Pincher Cascading Flow with ClawVault

1. ClawVault Check (Memory Manager): Before processing, search ClawVault to determine if the query relates to a previously completed or in-process task. 
• Match Found: Bypass the standard cascade. Route the query directly to the last model that worked on the task and append the retrieved task history as context. 
• No Match: Proceed to Step 2. 
2. Initial Query: Route new queries to Tier 1 (Gemini 2.0 Flash Lite). 
3. Evaluation: The active model generates a response and self-evaluates based on completeness, certainty, and resolution. It must output JSON: 
• Fail (<0.7 score or refusal): {"status": "escalate", "confidence_score": [score]} 
• Pass (>=0.7 score): {"status": "success", "confidence_score": [score], "answer": "[The final answer]"} 
4. Escalation: If the status is "escalate", suppress the output and automatically escalate the exact prompt to the next tier: 
• Tier 2: GeminiFlash 
• Tier 3: GrokMini 
• Tier 4: Kimi 
5. Resolution: The cascade loops sequentially until a model outputs a "success" status. The process halts, and the answer string is delivered to the user.

## Tiers
1. **GeminiLite** ($0.375/1M) - Simple chats, facts
2. **GeminiFlash** ($0.50/1M) - Standard tasks  
3. **GrokMini** ($0.90/1M) - Quick reasoning
4. **Kimi** ($3.10/1M) - Long docs, nuance

## Manual Override Commands
- `/model GeminiLite` - Cheapest mode
- `/model Kimi` - Long context mode
- `/model Sonnet` - Quality mode
- `/model opus` - Maximum capability
- `/model default` - Back to penny pincher chain

## Cost Tracking
Check `/status` to see current model and session costs.

## When to Override
- **Code review** → `/model Kimi` or `/model Sonnet`
- **Vision tasks** → `/model GrokVision`
- **Creative writing** → `/model opus`
- **Quick facts** → `/model GeminiLite` (already default)
