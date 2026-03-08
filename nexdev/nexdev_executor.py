import aiohttp, asyncio, json, time, pathlib

_KEYS = None

def _keys():
    global _KEYS
    if _KEYS: return _KEYS
    p = pathlib.Path.home() / ".openclaw/workspace/workspace/api-keys.json"
    _KEYS = json.loads(p.read_text())["providers"]
    return _KEYS

# (model_id, provider, cost_in_per_1M, cost_out_per_1M)
MODEL_MAP = {
    # Tier 1 — Ultra-cheap
    "QwenFlash":      ("qwen-turbo",            "alibaba_sg",  0.05,  0.40),
    "QwenLite":       ("qwen-turbo",            "alibaba_sg",  0.05,  0.40),
    "GeminiLite":     ("gemini-2.0-flash-lite", "google",      0.075, 0.30),
    # Tier 2 — Standard
    "QwenCoder":      ("qwen-coder-plus",        "alibaba_sg",  0.30,  1.50),
    "GeminiFlash":    ("gemini-2.5-flash",       "google",      0.10,  0.40),
    "Gemini20Flash":  ("gemini-2.0-flash",       "google",      0.10,  0.40),
    "GrokMini":       ("grok-3-mini",            "grok_xai",    0.30,  0.60),
    # Tier 3 — Advanced
    "Qwen35":         ("qwen3.5-122b-a10b",      "alibaba_sg",  0.40,  1.20),
    "QwenPlus":       ("qwen-plus",              "alibaba_sg",  0.40,  1.20),
    "Kimi":           ("kimi-k2.5",              "moonshot",    0.60,  2.50),
    # Tier 4 — Premium
    "Haiku":          ("claude-3-haiku-20240307","anthropic",   1.00,  5.00),
    "QwenMax":        ("qwen-max",               "alibaba_sg",  1.20,  6.00),
    "GeminiPro":      ("gemini-2.5-pro",         "google",      1.25, 10.00),
    # Tier 5 — Expert
    "GrokFast":       ("grok-4-1-fast-non-reasoning", "grok_xai", 2.00, 10.00),
    "Grok":           ("grok-4",                "grok_xai",    3.00, 15.00),
    "Sonnet":         ("claude-sonnet-4-6",      "anthropic",   3.00, 15.00),
    "Opus":           ("claude-opus-4-6",        "anthropic",   5.00, 25.00),
}

PROVIDER_URLS = {
    "alibaba_sg": "https://dashscope-intl.aliyuncs.com/compatible-mode/v1",
    "google":     "https://generativelanguage.googleapis.com/v1beta/openai",
    "moonshot":   "https://api.moonshot.ai/v1",
    "grok_xai":   "https://api.x.ai/v1",
    "anthropic":  "https://api.anthropic.com/v1",
}

async def _execute_openai_compat(session, base_url, api_key, model_id, query, cost_in, cost_out):
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {"model": model_id, "messages": [{"role": "user", "content": query}], "max_tokens": 2048}
    async with session.post(f"{base_url}/chat/completions", headers=headers, json=payload,
                            timeout=aiohttp.ClientTimeout(total=60)) as resp:
        data = await resp.json()
        if resp.status != 200:
            raise Exception(f"API error {resp.status}: {data}")
        text = data["choices"][0]["message"]["content"]
        usage = data.get("usage", {})
        tok_in = usage.get("prompt_tokens", 0)
        tok_out = usage.get("completion_tokens", 0)
        return text, tok_in, tok_out

async def _execute_anthropic(session, api_key, model_id, query, cost_in, cost_out):
    headers = {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
        "Content-Type": "application/json"
    }
    payload = {"model": model_id, "max_tokens": 2048, "messages": [{"role": "user", "content": query}]}
    async with session.post("https://api.anthropic.com/v1/messages", headers=headers, json=payload,
                            timeout=aiohttp.ClientTimeout(total=60)) as resp:
        data = await resp.json()
        if resp.status != 200:
            raise Exception(f"API error {resp.status}: {data}")
        text = data["content"][0]["text"]
        usage = data.get("usage", {})
        tok_in = usage.get("input_tokens", 0)
        tok_out = usage.get("output_tokens", 0)
        return text, tok_in, tok_out

async def execute(model_alias, query):
    keys = _keys()
    cfg = MODEL_MAP.get(model_alias, MODEL_MAP["QwenFlash"])
    model_id, provider, cost_in, cost_out = cfg
    api_key = keys[provider]["apiKey"]
    t0 = time.time()
    try:
        async with aiohttp.ClientSession() as session:
            if provider == "anthropic":
                text, tok_in, tok_out = await _execute_anthropic(session, api_key, model_id, query, cost_in, cost_out)
            else:
                base_url = PROVIDER_URLS[provider]
                text, tok_in, tok_out = await _execute_openai_compat(session, base_url, api_key, model_id, query, cost_in, cost_out)
            latency = round((time.time() - t0) * 1000)
            cost = (tok_in * cost_in + tok_out * cost_out) / 1_000_000
            return {
                "success": True, "response": text, "model_used": model_alias,
                "model_id": model_id, "provider": provider,
                "latency_ms": latency, "tokens_used": tok_in + tok_out,
                "tokens_in": tok_in, "tokens_out": tok_out,
                "cost_usd": round(cost, 6), "confidence": 0.9
            }
    except Exception as e:
        return {
            "success": False, "response": str(e), "model_used": model_alias,
            "model_id": model_id, "provider": provider,
            "latency_ms": round((time.time() - t0) * 1000),
            "tokens_used": 0, "cost_usd": 0, "confidence": 0.0
        }
