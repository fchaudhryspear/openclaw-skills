---
id: qwen35-model-integration
created: 2026-03-01
type: project
status: completed
priority: high
tags: [ai-models, qwen, alibaba, singapore-region, model-provider]
related: [[custom-memory-system-clawvault-clone]], [[openclaw-configuration]]
---

# Qwen3.5-122B-A10B Model Integration

## Summary
Successfully integrated Alibaba's Qwen3.5-122B-A10B model via the Singapore region endpoint (dashscope-intl.aliyuncs.com).

## Configuration Details

### Provider Setup
```json
{
  "alibaba-sg": {
    "baseUrl": "https://dashscope-intl.aliyuncs.com/compatible-mode/v1",
    "apiKey": "${ALIBABA_SG_API_KEY}",
    "api": "openai-completions",
    "models": [
      {
        "id": "qwen3.5-122b-a10b",
        "name": "Qwen 3.5 122B",
        "reasoning": true,
        "contextWindow": 262144,
        "maxTokens": 8192
      }
    ]
  }
}
```

### Model Alias
- **Alias**: `Qwen35` → maps to `alibaba-sg/qwen3.5-122b-a10b`

## Key Learnings
1. **Region Matters**: This specific model requires Singapore region (dashscope-intl.aliyuncs.com), not US-East
2. **Model ID Format**: Must be lowercase `qwen3.5-122b-a10b`, not `Qwen3.5-122B-A10B`
3. **OAuth vs API Key**: Unlike the Qwen Portal OAuth (coder-model, vision-model), this uses direct API key auth
4. **Context Window**: 262,144 tokens (larger than typical models)

## Challenges Overcome
- Initially tried adding to `qwen-portal` provider (wrong - uses OAuth)
- Had to create separate `alibaba-sg` provider for Singapore region
- Model ID case sensitivity caused routing failures
- Required updating both `openclaw.json` and `models.json`

## Status
✅ **COMPLETE** - Model is online and accepting requests via `Qwen35` alias
