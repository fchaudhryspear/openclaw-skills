#!/usr/bin/env python3
"""
NexDev Engine — Production API Execution Layer
================================================
Handles actual model API calls with:
- Auth from OpenClaw auth-profiles.json
- Retry with exponential backoff
- Self-correction escalation loops
- Cost tracking per execution
- Streaming support (optional)
- Rate limiting
- Timeout handling
"""

import json
import os
import time
import subprocess
import urllib.request
import urllib.error
import ssl
from pathlib import Path
from datetime import datetime, timezone

HOME = Path.home()
AUTH_PROFILES = HOME / ".openclaw" / "agents" / "main" / "agent" / "auth-profiles.json"
NEXDEV_DIR = HOME / ".openclaw" / "workspace" / "nexdev"
COST_LOG = NEXDEV_DIR / "logs" / "costs.jsonl"
EXEC_LOG = NEXDEV_DIR / "logs" / "executions.jsonl"

# ── Provider API Configuration ────────────────────────────────────────────────

PROVIDERS = {
    "anthropic": {
        "base_url": "https://api.anthropic.com/v1/messages",
        "auth_header": "x-api-key",
        "extra_headers": {"anthropic-version": "2023-06-01"},
        "format": "anthropic",
    },
    "google": {
        "base_url": "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
        "auth_header": None,  # Uses ?key= query param
        "format": "google",
    },
    "openai": {
        "base_url": "https://api.openai.com/v1/chat/completions",
        "auth_header": "Authorization",
        "auth_prefix": "Bearer ",
        "format": "openai",
    },
    "moonshot": {
        "base_url": "https://api.moonshot.ai/v1/chat/completions",
        "auth_header": "Authorization",
        "auth_prefix": "Bearer ",
        "format": "openai",
    },
    "xai": {
        "base_url": "https://api.x.ai/v1/chat/completions",
        "auth_header": "Authorization",
        "auth_prefix": "Bearer ",
        "format": "openai",
    },
    "alibaba-sg": {
        "base_url": "https://dashscope-intl.aliyuncs.com/compatible-mode/v1/chat/completions",
        "auth_header": "Authorization",
        "auth_prefix": "Bearer ",
        "format": "openai",
        "model_map": {
            "qwen-coder": "qwen-coder-plus",
            "qwen-turbo": "qwen-turbo-latest",
            "qwen-plus": "qwen-plus-latest",
            "qwen-max": "qwen-max-latest",
            "qwen3.5-122b-a10b": "qwen-plus-latest",  # 122B not on intl API; qwen-plus is best substitute
        },
    },
    "alibaba-us": {
        "base_url": "https://dashscope-intl.aliyuncs.com/compatible-mode/v1/chat/completions",
        "auth_header": "Authorization",
        "auth_prefix": "Bearer ",
        "format": "openai",
    },
    "qwen-portal": {
        "base_url": "https://chat.qwen.ai/api/chat/completions",
        "auth_header": "Authorization",
        "auth_prefix": "Bearer ",
        "format": "openai",
    },
}

# Model ID → provider mapping
MODEL_PROVIDERS = {
    "anthropic/claude-opus-4-6": "anthropic",
    "anthropic/claude-sonnet-4-6": "anthropic",
    "anthropic/claude-3-haiku-20240307": "anthropic",
    "google/gemini-2.5-pro": "google",
    "google/gemini-2.5-flash": "google",
    "google/gemini-2.0-flash": "google",
    "google/gemini-2.0-flash-lite": "google",
    "openai/gpt-4o": "openai",
    "moonshot/kimi-k2.5": "moonshot",
    "xai/grok-4": "xai",
    "xai/grok-3-mini": "xai",
    "xai/grok-4-1-fast-non-reasoning": "xai",
    "xai/grok-4-1-fast-reasoning": "xai",
    "xai/grok-2-vision-1212": "xai",
    "alibaba-sg/qwen3.5-122b-a10b": "alibaba-sg",
    "alibaba-sg/qwen-max": "alibaba-sg",
    "alibaba-sg/qwen-plus": "alibaba-sg",
    "alibaba-sg/qwen-turbo": "alibaba-sg",
    "alibaba-sg/qwen-coder": "alibaba-sg",
    "qwen-portal/coder-model": "qwen-portal",
    "qwen-portal/vision-model": "qwen-portal",
}

# Model costs (per million tokens)
MODEL_COSTS = {
    "anthropic/claude-opus-4-6": (5.00, 25.00),
    "anthropic/claude-sonnet-4-6": (3.00, 15.00),
    "anthropic/claude-3-haiku-20240307": (1.00, 5.00),
    "google/gemini-2.5-pro": (1.25, 10.00),
    "google/gemini-2.5-flash": (0.10, 0.40),
    "google/gemini-2.0-flash": (0.10, 0.40),
    "google/gemini-2.0-flash-lite": (0.075, 0.30),
    "openai/gpt-4o": (5.00, 15.00),
    "moonshot/kimi-k2.5": (0.60, 2.50),
    "xai/grok-4": (3.00, 15.00),
    "xai/grok-3-mini": (0.30, 0.60),
    "xai/grok-4-1-fast-non-reasoning": (2.00, 10.00),
    "xai/grok-4-1-fast-reasoning": (2.00, 10.00),
    "xai/grok-2-vision-1212": (2.00, 10.00),
    "alibaba-sg/qwen3.5-122b-a10b": (0.40, 1.20),
    "alibaba-sg/qwen-max": (1.20, 6.00),
    "alibaba-sg/qwen-plus": (0.40, 1.20),
    "alibaba-sg/qwen-turbo": (0.05, 0.40),
    "alibaba-sg/qwen-coder": (0.30, 1.50),
    "qwen-portal/coder-model": (0.00, 0.00),
    "qwen-portal/vision-model": (0.00, 0.00),
}


# ── Auth Loading ──────────────────────────────────────────────────────────────

def load_api_key(provider: str) -> str:
    """Load API key: Keychain first (freshest), then auth-profiles fallback."""
    # Provider → Keychain service name mapping
    KEYCHAIN_MAP = {
        "anthropic": "anthropic-api-key",
        "google": "google-api-key",
        "openai": "openai-api-key",
        "moonshot": "moonshot-api-key",
        "xai": "xai-api-key",
        "alibaba-sg": "qwen-sg-api-key",
        "alibaba-us": "qwen-sg-api-key",
    }

    # Try macOS Keychain FIRST (always freshest, updated by keychain-load.sh)
    keychain_service = KEYCHAIN_MAP.get(provider)
    if keychain_service:
        try:
            result = subprocess.run(
                ["security", "find-generic-password", "-a", "optimus", "-s", keychain_service, "-w"],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0 and result.stdout.strip():
                return result.stdout.strip()
        except Exception:
            pass

    # Fallback: auth-profiles.json
    if AUTH_PROFILES.exists():
        try:
            data = json.loads(AUTH_PROFILES.read_text())
            profiles = data.get("profiles", {})
            profile_key = f"{provider}:default"
            profile = profiles.get(profile_key, {})

            if profile.get("type") == "api_key":
                key = profile.get("key", "")
                if key and len(key) > 10:
                    return key

            if profile.get("access"):
                return profile["access"]
        except Exception:
            pass

    raise RuntimeError(f"No valid API key found for provider '{provider}' in Keychain or auth-profiles.json")


# ── Request Formatters ────────────────────────────────────────────────────────

def _format_anthropic(model_name: str, messages: list, system_prompt: str = "", max_tokens: int = 4096, temperature: float = 0.2) -> tuple:
    """Format request for Anthropic API."""
    body = {
        "model": model_name,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "messages": messages,
    }
    if system_prompt:
        body["system"] = system_prompt
    return body


def _format_google(model_name: str, messages: list, system_prompt: str = "", max_tokens: int = 4096, temperature: float = 0.2) -> tuple:
    """Format request for Google Gemini API."""
    contents = []
    for msg in messages:
        role = "user" if msg["role"] == "user" else "model"
        contents.append({"role": role, "parts": [{"text": msg["content"]}]})

    body = {
        "contents": contents,
        "generationConfig": {
            "maxOutputTokens": max_tokens,
            "temperature": temperature,
        },
    }
    if system_prompt:
        body["systemInstruction"] = {"parts": [{"text": system_prompt}]}
    return body


def _format_openai(model_name: str, messages: list, system_prompt: str = "", max_tokens: int = 4096, temperature: float = 0.2) -> dict:
    """Format request for OpenAI-compatible APIs (OpenAI, Moonshot, XAI, Alibaba, Qwen)."""
    all_messages = []
    if system_prompt:
        all_messages.append({"role": "system", "content": system_prompt})
    all_messages.extend(messages)

    return {
        "model": model_name,
        "messages": all_messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
    }


# ── Response Parsers ──────────────────────────────────────────────────────────

def _parse_anthropic(response: dict) -> dict:
    """Parse Anthropic response."""
    content = response.get("content", [{}])
    text = content[0].get("text", "") if content else ""
    usage = response.get("usage", {})
    return {
        "text": text,
        "input_tokens": usage.get("input_tokens", 0),
        "output_tokens": usage.get("output_tokens", 0),
        "stop_reason": response.get("stop_reason", "unknown"),
    }


def _parse_google(response: dict) -> dict:
    """Parse Google Gemini response."""
    candidates = response.get("candidates", [{}])
    text = ""
    if candidates:
        parts = candidates[0].get("content", {}).get("parts", [])
        text = parts[0].get("text", "") if parts else ""
    usage = response.get("usageMetadata", {})
    return {
        "text": text,
        "input_tokens": usage.get("promptTokenCount", 0),
        "output_tokens": usage.get("candidatesTokenCount", 0),
        "stop_reason": candidates[0].get("finishReason", "unknown") if candidates else "unknown",
    }


def _parse_openai(response: dict) -> dict:
    """Parse OpenAI-compatible response."""
    choices = response.get("choices", [{}])
    text = choices[0].get("message", {}).get("content", "") if choices else ""
    usage = response.get("usage", {})
    return {
        "text": text,
        "input_tokens": usage.get("prompt_tokens", 0),
        "output_tokens": usage.get("completion_tokens", 0),
        "stop_reason": choices[0].get("finish_reason", "unknown") if choices else "unknown",
    }


# ── Core Execution ────────────────────────────────────────────────────────────

def execute(
    model_id: str,
    prompt: str,
    system_prompt: str = "",
    max_tokens: int = 4096,
    temperature: float = 0.2,
    timeout: int = 120,
    retries: int = 2,
) -> dict:
    """
    Execute an API call to the specified model.
    
    Returns:
        {
            "text": str,           # Model response
            "model": str,          # Model ID used
            "input_tokens": int,   # Tokens consumed
            "output_tokens": int,  # Tokens generated
            "cost_usd": float,     # Estimated cost
            "duration_ms": int,    # Wall clock time
            "success": bool,       # Whether call succeeded
            "error": str|None,     # Error message if failed
        }
    """
    provider = MODEL_PROVIDERS.get(model_id)
    if not provider:
        return _error_result(model_id, f"Unknown model: {model_id}")

    provider_config = PROVIDERS.get(provider)
    if not provider_config:
        return _error_result(model_id, f"Unknown provider: {provider}")

    # Load API key
    try:
        api_key = load_api_key(provider)
    except RuntimeError as e:
        return _error_result(model_id, str(e))

    # Extract model name (strip provider prefix)
    model_name = model_id.split("/", 1)[1] if "/" in model_id else model_id

    # Apply model name mapping if provider has one (e.g., DashScope uses different model IDs)
    model_map = provider_config.get("model_map", {})
    api_model_name = model_map.get(model_name, model_name)

    # Some reasoning models require temperature=1 (e.g., Kimi K2.5)
    TEMP_OVERRIDE = {
        "kimi-k2.5": 1.0,
        "o1": 1.0,
        "o1-mini": 1.0,
    }
    actual_temp = TEMP_OVERRIDE.get(model_name, temperature)

    # Format request body
    messages = [{"role": "user", "content": prompt}]
    fmt = provider_config["format"]

    if fmt == "anthropic":
        body = _format_anthropic(api_model_name, messages, system_prompt, max_tokens, actual_temp)
    elif fmt == "google":
        body = _format_google(api_model_name, messages, system_prompt, max_tokens, actual_temp)
    else:
        body = _format_openai(api_model_name, messages, system_prompt, max_tokens, actual_temp)

    # Build URL
    url = provider_config["base_url"]
    if fmt == "google":
        url = url.format(model=api_model_name)
        url += f"?key={api_key}"

    # Build headers
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "NexDev/2.0",  # Required: XAI/Cloudflare blocks Python's default UA
    }
    if fmt != "google":
        auth_header = provider_config.get("auth_header", "Authorization")
        auth_prefix = provider_config.get("auth_prefix", "")
        headers[auth_header] = f"{auth_prefix}{api_key}"

    extra = provider_config.get("extra_headers", {})
    headers.update(extra)

    # Execute with retries
    last_error = None
    for attempt in range(retries + 1):
        start_time = time.time()
        try:
            result = _http_post(url, headers, body, timeout)
            duration_ms = int((time.time() - start_time) * 1000)

            # Parse response
            if fmt == "anthropic":
                parsed = _parse_anthropic(result)
            elif fmt == "google":
                parsed = _parse_google(result)
            else:
                parsed = _parse_openai(result)

            # Calculate cost
            costs = MODEL_COSTS.get(model_id, (0, 0))
            cost_usd = (parsed["input_tokens"] * costs[0] + parsed["output_tokens"] * costs[1]) / 1_000_000

            response = {
                "text": parsed["text"].strip(),
                "model": model_id,
                "provider": provider,
                "input_tokens": parsed["input_tokens"],
                "output_tokens": parsed["output_tokens"],
                "cost_usd": round(cost_usd, 6),
                "duration_ms": duration_ms,
                "success": True,
                "error": None,
                "stop_reason": parsed.get("stop_reason"),
                "attempt": attempt + 1,
            }

            # Log execution
            _log_execution(response)
            return response

        except Exception as e:
            last_error = str(e)
            duration_ms = int((time.time() - start_time) * 1000)

            if attempt < retries:
                # Exponential backoff: 1s, 2s, 4s
                backoff = 2 ** attempt
                time.sleep(backoff)
                continue

    # All retries exhausted
    error_result = _error_result(model_id, f"All {retries + 1} attempts failed: {last_error}")
    error_result["duration_ms"] = duration_ms
    _log_execution(error_result)
    return error_result


def _http_post(url: str, headers: dict, body: dict, timeout: int) -> dict:
    """Make an HTTP POST request and return parsed JSON response."""
    data = json.dumps(body).encode("utf-8")

    ctx = ssl.create_default_context()
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")

    try:
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
            resp_data = resp.read().decode("utf-8")
            result = json.loads(resp_data)

            # Check for API errors in response body
            if "error" in result and isinstance(result["error"], dict):
                raise RuntimeError(result["error"].get("message", str(result["error"])))

            return result
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8", errors="ignore")
        try:
            error_json = json.loads(error_body)
            msg = error_json.get("error", {}).get("message", error_body[:200])
        except (json.JSONDecodeError, AttributeError):
            msg = error_body[:200]
        raise RuntimeError(f"HTTP {e.code}: {msg}")
    except urllib.error.URLError as e:
        raise RuntimeError(f"Connection error: {e.reason}")


def _error_result(model_id: str, error: str) -> dict:
    """Create a standardized error result."""
    return {
        "text": "",
        "model": model_id,
        "provider": MODEL_PROVIDERS.get(model_id, "unknown"),
        "input_tokens": 0,
        "output_tokens": 0,
        "cost_usd": 0.0,
        "duration_ms": 0,
        "success": False,
        "error": error,
        "stop_reason": "error",
        "attempt": 0,
    }


def _log_execution(result: dict):
    """Log execution to JSONL file."""
    EXEC_LOG.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        **result,
    }
    # Remove the actual response text from logs to save space
    entry.pop("text", None)
    with open(EXEC_LOG, "a") as f:
        f.write(json.dumps(entry) + "\n")


# ── Orchestrated Execution (with escalation) ─────────────────────────────────

def execute_with_escalation(
    routing: dict,
    prompt: str,
    system_prompt: str = "",
    max_tokens: int = 4096,
    temperature: float = 0.2,
    confidence_threshold: float = 0.7,
) -> dict:
    """
    Execute a routed query with automatic escalation on failure.
    
    Flow:
    1. Try primary model from routing decision
    2. If fails → try each model in escalation chain
    3. Log all attempts for learning
    4. Return best result or final error
    """
    primary_model = routing.get("model")
    escalation_chain = routing.get("escalation_chain", [])
    agents = routing.get("agents", [])
    agent_prompts = routing.get("agent_prompts", {})

    # Build full system prompt with agent context
    full_system = system_prompt
    if agents and agent_prompts:
        agent_context = "\n\n".join(
            f"--- {name} ---\n{agent_prompts[name]}"
            for name in agents if name in agent_prompts
        )
        if agent_context:
            full_system = f"{system_prompt}\n\n[ACTIVE AGENTS]\n{agent_context}" if system_prompt else f"[ACTIVE AGENTS]\n{agent_context}"

    # Add memory context if available
    memory_ctx = routing.get("memory_context", "")
    if memory_ctx and memory_ctx != "(no prior context found)":
        memory_section = f"\n\n[RELEVANT MEMORY]\n{memory_ctx[:1000]}"
        full_system = f"{full_system}{memory_section}" if full_system else memory_section

    # Try primary model
    result = execute(primary_model, prompt, full_system, max_tokens, temperature)

    if result["success"]:
        result["escalated"] = False
        result["tier"] = routing.get("tier")
        result["attribution"] = f"— {routing.get('model_alias', primary_model)}"
        return result

    # Escalation chain
    for i, esc_entry in enumerate(escalation_chain):
        # Parse model ID from escalation entry (format: "Alias (provider/model)")
        if "(" in esc_entry and ")" in esc_entry:
            esc_model = esc_entry.split("(")[1].rstrip(")")
        else:
            esc_model = esc_entry

        esc_result = execute(esc_model, prompt, full_system, max_tokens, temperature)

        if esc_result["success"]:
            esc_result["escalated"] = True
            esc_result["escalation_step"] = i + 1
            esc_result["original_model"] = primary_model
            esc_result["tier"] = routing.get("tier")
            # Find alias for the escalated model
            alias = esc_model.split("/")[-1] if "/" in esc_model else esc_model
            esc_result["attribution"] = f"— {alias} (escalated from {routing.get('model_alias', '?')})"
            return esc_result

    # All models failed
    return {
        "text": "",
        "model": primary_model,
        "success": False,
        "error": f"All models failed: primary ({primary_model}) + {len(escalation_chain)} escalation attempts",
        "escalated": True,
        "escalation_step": len(escalation_chain),
        "tier": routing.get("tier"),
        "attribution": "— FAILED (all tiers exhausted)",
        "input_tokens": 0,
        "output_tokens": 0,
        "cost_usd": 0.0,
        "duration_ms": 0,
    }


# ── Cost Summary ──────────────────────────────────────────────────────────────

def get_cost_summary(days: int = 1) -> dict:
    """Get cost summary from execution logs."""
    if not EXEC_LOG.exists():
        return {"total_cost": 0, "total_calls": 0, "by_model": {}}

    cutoff = time.time() - (days * 86400)
    total_cost = 0.0
    total_calls = 0
    by_model = {}
    by_tier = {}

    for line in EXEC_LOG.read_text().strip().split("\n"):
        if not line:
            continue
        try:
            entry = json.loads(line)
            # Parse timestamp
            ts = entry.get("timestamp", "")
            cost = entry.get("cost_usd", 0)
            model = entry.get("model", "unknown")
            tier = entry.get("tier", "unknown")

            total_cost += cost
            total_calls += 1

            if model not in by_model:
                by_model[model] = {"calls": 0, "cost": 0.0, "tokens_in": 0, "tokens_out": 0}
            by_model[model]["calls"] += 1
            by_model[model]["cost"] += cost
            by_model[model]["tokens_in"] += entry.get("input_tokens", 0)
            by_model[model]["tokens_out"] += entry.get("output_tokens", 0)

        except (json.JSONDecodeError, KeyError):
            continue

    return {
        "total_cost": round(total_cost, 4),
        "total_calls": total_calls,
        "by_model": by_model,
    }


# ── Quick Test ────────────────────────────────────────────────────────────────

def quick_test(model_id: str = "alibaba-sg/qwen-turbo") -> dict:
    """Quick connectivity test against a model."""
    return execute(
        model_id,
        "Respond with exactly: OK",
        max_tokens=10,
        temperature=0,
        timeout=15,
        retries=0,
    )


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "test":
        model = sys.argv[2] if len(sys.argv) > 2 else "alibaba-sg/qwen-turbo"
        print(f"Testing {model}...")
        result = quick_test(model)
        if result["success"]:
            print(f"✅ {model} → \"{result['text']}\" ({result['duration_ms']}ms, ${result['cost_usd']})")
        else:
            print(f"❌ {model} → {result['error']}")

    elif len(sys.argv) > 1 and sys.argv[1] == "costs":
        summary = get_cost_summary()
        print(f"Total: ${summary['total_cost']:.4f} across {summary['total_calls']} calls")
        for model, data in sorted(summary["by_model"].items(), key=lambda x: -x[1]["cost"]):
            print(f"  {model:<45} {data['calls']:>3} calls  ${data['cost']:.4f}  ({data['tokens_in']+data['tokens_out']:,} tokens)")

    elif len(sys.argv) > 1 and sys.argv[1] == "test-all":
        test_models = [
            "alibaba-sg/qwen-turbo",
            "alibaba-sg/qwen-coder",
            "google/gemini-2.0-flash-lite",
            "moonshot/kimi-k2.5",
            "xai/grok-3-mini",
        ]
        print("🧪 Testing all tier models...\n")
        for model in test_models:
            result = quick_test(model)
            status = "✅" if result["success"] else "❌"
            detail = f"\"{result['text'][:40]}\" ({result['duration_ms']}ms)" if result["success"] else result["error"][:60]
            print(f"  {status} {model:<45} {detail}")

    else:
        print("NexDev Engine — Production API Layer")
        print("Usage:")
        print("  engine.py test [model_id]    Test single model")
        print("  engine.py test-all           Test all tier models")
        print("  engine.py costs              Show cost summary")
