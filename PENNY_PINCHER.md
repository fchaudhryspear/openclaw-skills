# Penny Pincher Model Routing Strategy

## Cost Tiers (per 1M tokens, input+output)

| Tier | Model | Cost | Best For |
|------|-------|------|----------|
| **T1** | GeminiLite | $0.375 | Simple Q&A, facts, casual chat |
| **T2** | GeminiFlash | $0.50 | Standard tasks, longer context |
| **T3** | GrokMini | $0.90 | Quick reasoning, coding snippets |
| **T4** | Kimi | $3.10 | Long docs, nuanced reasoning |
| **T5** | Haiku | $6.00 | Anthropic ecosystem, vision |
| **T6** | GeminiPro | $11.25 | Complex analysis, 1M context |
| **T7** | GrokVision | $12.00 | Image analysis, vision tasks |
| **T8** | GrokFast | $12.00 | Fast premium responses |
| **T9** | Sonnet | $18.00 | Best reasoning quality |
| **T10** | Opus | $30.00 | Maximum capability, coding |

## Routing Logic

### Simple Tasks (T1-T3)
- Greetings, casual chat
- Factual lookups
- Simple math
- Yes/no questions
- Current: `GeminiLite` → fallback `GeminiFlash` → `GrokMini`

### Standard Tasks (T3-T5)
- Email drafting
- Summarization
- Basic coding
- Translation
- Current: `GrokMini` → `Kimi` → `Haiku`

### Complex Tasks (T5-T8)
- Multi-step reasoning
- Document analysis
- Complex coding
- Data extraction
- Current: `Kimi` → `GeminiPro` → `GrokVision`/`GrokFast`

### Premium Tasks (T8-T10)
- Critical decisions
- Complex architecture
- Creative writing
- Maximum accuracy needed
- Current: `Sonnet` → `Opus`

## Implementation Options

### Option 1: Sub-agent Orchestrator
Create a router sub-agent that:
1. Analyzes task complexity
2. Picks appropriate tier
3. Spawns task to cheapest model
4. Evaluates confidence/quality
5. Re-queues to higher tier if needed

### Option 2: Confidence-Based Escalation
- Start with T1
- If response confidence < threshold → retry T2
- Continue up chain until satisfied
- Track "success rate" per model per task type

### Option 3: Task-Type Routing
Pre-classify tasks and map to optimal tier:
- `summarize` → T2 (GeminiFlash)
- `code_review` → T4 (Kimi)
- `architecture` → T9 (Sonnet)
- `chat` → T1 (GeminiLite)
- `vision` → T7 (GrokVision)

## Quick Win: Default Routing

Set default model by conversation type:
- **Casual/DM chats**: `GeminiLite` (7.5¢/$0.30)
- **Group mentions**: `GeminiFlash` (10¢/$0.40)
- **Code/technical**: `Kimi` (60¢/$2.50)
- **Complex tasks**: `Sonnet` ($3/$15)

## Cost Savings Estimate

Old approach (always Sonnet): ~$3-15 per session
New approach: 
- 70% T1/T2: ~$0.10-0.50
- 20% T3/T4: ~$1-3
- 10% T9/T10: ~$5-15

**Savings: ~80% on typical usage**

## Next Steps

1. Set `GeminiLite` as primary default
2. Create `/smart` command that auto-routes
3. Add model suggestion to HEARTBEAT.md
4. Track actual costs per session in logs
