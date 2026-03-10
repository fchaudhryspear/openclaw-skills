#!/usr/bin/env python3
"""
MO Phase 1.1 — Pre-flight Token Estimation
============================================
Estimates token usage and cost BEFORE sending a query to any model.
Uses provider-specific heuristics with a universal fallback.

Usage:
    from mo.v2.token_estimator import TokenEstimator
    estimator = TokenEstimator()
    estimate = estimator.estimate("Design a microservice architecture", model_alias="Sonnet")
    print(f"Estimated tokens: {estimate['total_tokens']}, Cost: ${estimate['estimated_cost']:.4f}")
"""

import re
import json
from pathlib import Path
from typing import Dict, Optional, Tuple
from datetime import datetime


# ── Model Cost Database (per 1M tokens) ──────────────────────────────────────

MODEL_COSTS = {
    # Tier 1: Ultra-Cheap
    "QwenFlash":    {"input": 0.05,  "output": 0.10,  "provider": "alibaba", "alias": "alibaba-sg/qwen-turbo"},
    "GeminiLite":   {"input": 0.075, "output": 0.15,  "provider": "google",  "alias": "google/gemini-2.0-flash-lite"},
    
    # Tier 2: Standard
    "GeminiFlash":  {"input": 0.15,  "output": 0.60,  "provider": "google",  "alias": "google/gemini-2.5-flash"},
    "Gemini20Flash":{"input": 0.10,  "output": 0.40,  "provider": "google",  "alias": "google/gemini-2.0-flash"},
    "GrokMini":     {"input": 0.30,  "output": 0.50,  "provider": "xai",     "alias": "xai/grok-3-mini"},
    "QwenCoder":    {"input": 0.14,  "output": 0.28,  "provider": "alibaba", "alias": "alibaba-sg/qwen-coder"},
    
    # Tier 3: Advanced
    "Qwen35":       {"input": 0.40,  "output": 0.60,  "provider": "alibaba", "alias": "alibaba-sg/qwen3.5-122b-a10b"},
    "QwenPlus":     {"input": 0.40,  "output": 0.60,  "provider": "alibaba", "alias": "alibaba-sg/qwen-plus"},
    "Kimi":         {"input": 0.50,  "output": 0.50,  "provider": "moonshot","alias": "moonshot/kimi-k2.5"},
    
    # Tier 4: Premium
    "Haiku":        {"input": 0.80,  "output": 1.00,  "provider": "anthropic","alias": "anthropic/claude-3-haiku-20240307"},
    "QwenMax":      {"input": 1.00,  "output": 1.20,  "provider": "alibaba", "alias": "alibaba-sg/qwen-max"},
    "GeminiPro":    {"input": 1.25,  "output": 5.00,  "provider": "google",  "alias": "google/gemini-2.5-pro"},
    
    # Tier 5: Expert
    "Grok":         {"input": 3.00,  "output": 9.00,  "provider": "xai",     "alias": "xai/grok-4"},
    "GrokFast":     {"input": 3.00,  "output": 9.00,  "provider": "xai",     "alias": "xai/grok-4-1-fast-non-reasoning"},
    "Sonnet":       {"input": 3.00,  "output": 15.00, "provider": "anthropic","alias": "anthropic/claude-sonnet-4-6"},
    "opus":         {"input": 5.00,  "output": 25.00, "provider": "anthropic","alias": "anthropic/claude-opus-4-6"},
    "GPT4o":        {"input": 2.50,  "output": 10.00, "provider": "openai",  "alias": "openai/gpt-4o"},
}

# Provider-specific token-per-word ratios (empirically derived)
PROVIDER_TOKEN_RATIOS = {
    "anthropic": 1.35,   # Claude tends to be close to ~1.35 tokens/word
    "openai":    1.33,   # GPT tokenizer is well-documented
    "google":    1.30,   # Gemini slightly more efficient
    "alibaba":   1.40,   # Qwen tokenizer tends to be a bit heavier for English
    "xai":       1.35,   # Grok similar to Anthropic
    "moonshot":  1.40,   # Kimi similar to Qwen
    "default":   1.35,   # Universal fallback
}

# Average output-to-input ratio by task type
OUTPUT_RATIOS = {
    "simple_qa":     0.5,    # Short answers
    "code_gen":      2.5,    # Code is usually longer than the prompt
    "architecture":  2.0,    # Design docs are verbose
    "summarize":     0.3,    # Summaries compress input
    "refactor":      1.5,    # Refactored code ~ same length
    "debug":         1.0,    # Explanations match query length
    "creative":      3.0,    # Creative writing generates a lot
    "default":       1.5,    # General fallback
}


class TokenEstimator:
    """Pre-flight token and cost estimation for MO routing decisions."""
    
    def __init__(self, model_costs: Dict = None, calibration_path: str = None):
        self.model_costs = model_costs or MODEL_COSTS
        self.calibration_data = {}
        self.calibration_path = calibration_path or str(
            Path.home() / ".openclaw" / "workspace" / "mo" / "v2" / "token_calibration.json"
        )
        self._load_calibration()
    
    def _load_calibration(self):
        """Load historical calibration data to improve estimates."""
        try:
            path = Path(self.calibration_path)
            if path.exists():
                with open(path) as f:
                    self.calibration_data = json.load(f)
        except (json.JSONDecodeError, IOError):
            self.calibration_data = {}
    
    def save_calibration(self):
        """Persist calibration data."""
        path = Path(self.calibration_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, 'w') as f:
            json.dump(self.calibration_data, f, indent=2)
    
    def count_words(self, text: str) -> int:
        """Count words in text, handling code blocks specially."""
        # Code blocks tend to have more tokens per "word" due to symbols
        code_blocks = re.findall(r'```[\s\S]*?```', text)
        code_word_count = sum(len(block.split()) for block in code_blocks)
        
        # Remove code blocks and count remaining words
        text_no_code = re.sub(r'```[\s\S]*?```', '', text)
        text_word_count = len(text_no_code.split())
        
        # Code blocks get a 1.5x multiplier (symbols = more tokens)
        return text_word_count + int(code_word_count * 1.5)
    
    def classify_task(self, query: str) -> str:
        """Classify the task type for output ratio estimation."""
        query_lower = query.lower()
        
        patterns = {
            "security_audit": r"(security audit|penetration test|vulnerability|owasp|threat model|compliance audit)",
            "architecture": r"(design|architect|system design|infrastructure|microservice|serverless|scalab|distributed)",
            "debug":        r"(fix|debug|error|bug|issue|broken|failing|crash|exception|traceback|typeerror|valueerror)",
            "refactor":     r"(refactor|optimize|improve|clean up|modernize|upgrade|migrate)",
            "code_gen":     r"(write|create|build|implement|generate|code|function|class|api|endpoint|component)",
            "summarize":    r"(summar|explain|what is|describe|overview|tldr|brief)",
            "creative":     r"(write a story|blog|article|essay|creative|narrative|poem)",
            "simple_qa":    r"(what|who|when|where|how much|how many|is it|can you|list)",
        }
        
        for task_type, pattern in patterns.items():
            if re.search(pattern, query_lower):
                return task_type
        
        return "default"
    
    def estimate_tokens(self, text: str, model_alias: str = None) -> Dict:
        """Estimate input tokens for a given text and model."""
        word_count = self.count_words(text)
        
        # Get provider-specific ratio
        provider = "default"
        if model_alias and model_alias in self.model_costs:
            provider = self.model_costs[model_alias].get("provider", "default")
        
        # Check calibration for this provider (learned adjustment)
        ratio = PROVIDER_TOKEN_RATIOS.get(provider, PROVIDER_TOKEN_RATIOS["default"])
        if provider in self.calibration_data:
            cal = self.calibration_data[provider]
            if cal.get("samples", 0) >= 10:
                # Use calibrated ratio if we have enough samples
                ratio = cal["avg_ratio"]
        
        input_tokens = int(word_count * ratio)
        
        return {
            "word_count": word_count,
            "token_ratio": ratio,
            "provider": provider,
            "input_tokens": input_tokens,
        }
    
    def estimate(self, query: str, model_alias: str = None, 
                 system_prompt_tokens: int = 2000,
                 task_type: str = None) -> Dict:
        """
        Full pre-flight estimation: tokens + cost for a given query and model.
        
        Args:
            query: The user's query text
            model_alias: Model alias (e.g., "Sonnet", "QwenFlash")
            system_prompt_tokens: Estimated system prompt tokens (default 2000)
            task_type: Override task classification (optional)
        
        Returns:
            Dict with token estimates, cost projections, and recommendations
        """
        # Estimate input tokens
        token_info = self.estimate_tokens(query, model_alias)
        input_tokens = token_info["input_tokens"] + system_prompt_tokens
        
        # Classify task and estimate output
        detected_task = task_type or self.classify_task(query)
        output_ratio = OUTPUT_RATIOS.get(detected_task, OUTPUT_RATIOS["default"])
        output_tokens = int(token_info["input_tokens"] * output_ratio)
        
        total_tokens = input_tokens + output_tokens
        
        # Calculate cost for requested model
        cost_info = {}
        if model_alias and model_alias in self.model_costs:
            mc = self.model_costs[model_alias]
            input_cost = (input_tokens / 1_000_000) * mc["input"]
            output_cost = (output_tokens / 1_000_000) * mc["output"]
            cost_info = {
                "model": model_alias,
                "input_cost": round(input_cost, 6),
                "output_cost": round(output_cost, 6),
                "estimated_cost": round(input_cost + output_cost, 6),
            }
        
        # Calculate cost for ALL models (for comparison)
        all_costs = []
        for alias, mc in self.model_costs.items():
            input_cost = (input_tokens / 1_000_000) * mc["input"]
            output_cost = (output_tokens / 1_000_000) * mc["output"]
            total_cost = input_cost + output_cost
            all_costs.append({
                "model": alias,
                "provider": mc["provider"],
                "estimated_cost": round(total_cost, 6),
            })
        
        all_costs.sort(key=lambda x: x["estimated_cost"])
        
        return {
            "query_words": token_info["word_count"],
            "task_type": detected_task,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": total_tokens,
            "token_ratio": token_info["token_ratio"],
            "provider": token_info["provider"],
            "cost": cost_info,
            "cheapest_3": all_costs[:3],
            "most_expensive_3": all_costs[-3:],
            "all_costs": all_costs,
            "timestamp": datetime.now().isoformat(),
        }
    
    def record_actual(self, model_alias: str, actual_input: int, actual_output: int,
                      estimated_input: int, word_count: int):
        """
        Record actual token usage to improve future estimates.
        Called after each API response to calibrate the estimator.
        """
        provider = "default"
        if model_alias in self.model_costs:
            provider = self.model_costs[model_alias].get("provider", "default")
        
        if word_count > 0:
            actual_ratio = actual_input / word_count
            
            if provider not in self.calibration_data:
                self.calibration_data[provider] = {
                    "avg_ratio": actual_ratio,
                    "samples": 1,
                    "total_error_pct": abs(estimated_input - actual_input) / max(actual_input, 1) * 100,
                }
            else:
                cal = self.calibration_data[provider]
                n = cal["samples"]
                # Running average
                cal["avg_ratio"] = (cal["avg_ratio"] * n + actual_ratio) / (n + 1)
                error_pct = abs(estimated_input - actual_input) / max(actual_input, 1) * 100
                cal["total_error_pct"] = (cal["total_error_pct"] * n + error_pct) / (n + 1)
                cal["samples"] = n + 1
            
            self.save_calibration()
    
    def cheapest_for_task(self, query: str, min_tier: int = 1, 
                          max_cost: float = None) -> Dict:
        """
        Find the cheapest model for a given task, optionally filtered by tier and max cost.
        
        Args:
            query: The query text
            min_tier: Minimum model tier (1-5)
            max_cost: Maximum acceptable cost per query
        
        Returns:
            Dict with recommended model and cost estimate
        """
        tier_map = {
            1: ["QwenFlash", "GeminiLite"],
            2: ["GeminiFlash", "Gemini20Flash", "GrokMini", "QwenCoder"],
            3: ["Qwen35", "QwenPlus", "Kimi"],
            4: ["Haiku", "QwenMax", "GeminiPro"],
            5: ["Grok", "GrokFast", "Sonnet", "opus", "GPT4o"],
        }
        
        eligible_models = []
        for tier in range(min_tier, 6):
            eligible_models.extend(tier_map.get(tier, []))
        
        best = None
        for model in eligible_models:
            est = self.estimate(query, model_alias=model)
            cost = est["cost"]["estimated_cost"]
            if max_cost and cost > max_cost:
                continue
            if best is None or cost < best["cost"]["estimated_cost"]:
                best = est
        
        return best


def estimate_query_cost(query: str, model_alias: str = None) -> Dict:
    """Convenience function for quick estimation."""
    estimator = TokenEstimator()
    return estimator.estimate(query, model_alias=model_alias)


if __name__ == "__main__":
    # Quick demo
    estimator = TokenEstimator()
    
    test_queries = [
        ("What is Python?", "QwenFlash"),
        ("Design a microservice architecture for an e-commerce platform with 10M users", "Sonnet"),
        ("Fix this bug: TypeError in line 42 of auth.py", "QwenCoder"),
        ("Write a React component for a user dashboard with charts", "Qwen35"),
    ]
    
    for query, model in test_queries:
        est = estimator.estimate(query, model_alias=model)
        print(f"\nQuery: '{query[:50]}...'")
        print(f"  Task: {est['task_type']} | Tokens: ~{est['total_tokens']:,}")
        print(f"  Cost on {model}: ${est['cost']['estimated_cost']:.6f}")
        print(f"  Cheapest: {est['cheapest_3'][0]['model']} (${est['cheapest_3'][0]['estimated_cost']:.6f})")
