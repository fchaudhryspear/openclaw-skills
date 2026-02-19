# Penny Pincher Routing - Use Cheap Models First

## Default Model Chain (Cheapest → Premium)
1. **GeminiLite** ($0.375/1M) - Simple chats, facts
2. **GeminiFlash** ($0.50/1M) - Standard tasks  
3. **GrokMini** ($0.90/1M) - Quick reasoning
4. **Kimi** ($3.10/1M) - Long docs, nuance
5. **GeminiPro** ($11.25/1M) - Complex analysis
6. **GrokFast** ($12.00/1M) - Fast premium
7. **Sonnet** ($18.00/1M) - Best reasoning
8. **Opus** ($30.00/1M) - Maximum quality

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
