#!/usr/bin/env python3
"""
MO Phase 1.4 — Fallback & Graceful Degradation
================================================
Guarantees MO always returns an answer even when preferred models
are down, slow, or rate-limited.

Tracks model health in real-time and maintains fallback chains
per tier so there's always an alternative.

Usage:
    from mo.v2.fallback_chain import FallbackManager
    fm = FallbackManager()
    model = fm.get_available_model(preferred="Sonnet", tier=5)
    fm.report_failure("Sonnet", error="timeout")
    fm.report_success("Sonnet", latency_ms=1200)
"""

import json
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from collections import defaultdict


# ── Fallback Chains (ordered by preference within each tier) ─────────────────

FALLBACK_CHAINS = {
    1: ["QwenFlash", "GeminiLite"],
    2: ["GeminiFlash", "QwenCoder", "Gemini20Flash", "GrokMini"],
    3: ["Qwen35", "Kimi", "QwenPlus"],
    4: ["GeminiPro", "QwenMax", "Haiku"],
    5: ["Sonnet", "Grok", "GrokFast", "GPT4o", "opus"],
}

# Cross-tier fallback: if entire tier is down, fall to these
CROSS_TIER_FALLBACK = {
    5: [4, 3],  # If all Tier 5 down → try Tier 4 → Tier 3
    4: [3, 2],
    3: [2, 1],
    2: [1],
    1: [],      # If Tier 1 is down, we're in trouble
}

# Health thresholds
HEALTH_CONFIG = {
    "failure_window_minutes": 10,     # Track failures in last N minutes
    "max_failures_before_blacklist": 3, # Blacklist after N failures in window
    "blacklist_duration_minutes": 5,  # How long to blacklist
    "slow_threshold_ms": 30000,       # Mark as slow if > 30s
    "slow_penalty_factor": 0.5,       # Deprioritize slow models
}


class ModelHealth:
    """Tracks health status of a single model."""
    
    def __init__(self):
        self.failures: List[float] = []      # timestamps of recent failures
        self.successes: List[float] = []     # timestamps of recent successes
        self.latencies: List[float] = []     # recent latencies in ms
        self.blacklisted_until: float = 0    # unix timestamp
        self.total_requests: int = 0
        self.total_failures: int = 0
    
    def is_available(self) -> bool:
        """Check if model is currently available (not blacklisted)."""
        if time.time() < self.blacklisted_until:
            return False
        return True
    
    def is_slow(self) -> bool:
        """Check if model is currently slow."""
        if not self.latencies:
            return False
        recent = self.latencies[-5:]  # Last 5 requests
        avg = sum(recent) / len(recent)
        return avg > HEALTH_CONFIG["slow_threshold_ms"]
    
    def record_failure(self, error: str = ""):
        """Record a failure. May trigger blacklist."""
        now = time.time()
        self.failures.append(now)
        self.total_failures += 1
        self.total_requests += 1
        
        # Clean old failures
        window = HEALTH_CONFIG["failure_window_minutes"] * 60
        self.failures = [t for t in self.failures if now - t < window]
        
        # Check blacklist threshold
        if len(self.failures) >= HEALTH_CONFIG["max_failures_before_blacklist"]:
            self.blacklisted_until = now + HEALTH_CONFIG["blacklist_duration_minutes"] * 60
    
    def record_success(self, latency_ms: float = 0):
        """Record a successful request."""
        self.successes.append(time.time())
        self.total_requests += 1
        if latency_ms > 0:
            self.latencies.append(latency_ms)
            # Keep only last 20 latencies
            self.latencies = self.latencies[-20:]
    
    def get_score(self) -> float:
        """Get health score 0-1 (1 = perfectly healthy)."""
        if not self.is_available():
            return 0.0
        
        if self.total_requests == 0:
            return 0.8  # Unknown = cautiously optimistic
        
        success_rate = 1.0 - (self.total_failures / self.total_requests)
        slow_penalty = HEALTH_CONFIG["slow_penalty_factor"] if self.is_slow() else 1.0
        
        return min(1.0, success_rate * slow_penalty)
    
    def to_dict(self) -> Dict:
        return {
            "available": self.is_available(),
            "slow": self.is_slow(),
            "health_score": round(self.get_score(), 3),
            "total_requests": self.total_requests,
            "total_failures": self.total_failures,
            "blacklisted_until": datetime.fromtimestamp(self.blacklisted_until).isoformat() 
                                if self.blacklisted_until > time.time() else None,
            "avg_latency_ms": round(sum(self.latencies[-5:]) / len(self.latencies[-5:]), 0) 
                             if self.latencies else None,
        }


class FallbackManager:
    """Manages model fallback chains and health tracking."""
    
    def __init__(self):
        self.health: Dict[str, ModelHealth] = defaultdict(ModelHealth)
    
    def report_failure(self, model_alias: str, error: str = ""):
        """Report a model failure."""
        self.health[model_alias].record_failure(error)
    
    def report_success(self, model_alias: str, latency_ms: float = 0):
        """Report a successful request."""
        self.health[model_alias].record_success(latency_ms)
    
    def get_available_model(self, preferred: str = None, tier: int = None) -> Optional[str]:
        """
        Get the best available model, falling back as needed.
        
        Args:
            preferred: Preferred model alias
            tier: Model tier (1-5)
        
        Returns:
            Model alias string, or None if everything is down
        """
        # Try preferred model first
        if preferred and self.health[preferred].is_available():
            return preferred
        
        # Determine which tier to search
        if tier is None and preferred:
            tier = self._find_tier(preferred)
        tier = tier or 3  # Default to tier 3
        
        # Try models in the same tier
        for model in FALLBACK_CHAINS.get(tier, []):
            if self.health[model].is_available():
                # Prefer non-slow models
                if not self.health[model].is_slow():
                    return model
        
        # All non-slow models in tier exhausted, try slow ones
        for model in FALLBACK_CHAINS.get(tier, []):
            if self.health[model].is_available():
                return model
        
        # Cross-tier fallback
        for fallback_tier in CROSS_TIER_FALLBACK.get(tier, []):
            for model in FALLBACK_CHAINS.get(fallback_tier, []):
                if self.health[model].is_available():
                    return model
        
        # Nuclear option: try everything
        for t in sorted(FALLBACK_CHAINS.keys()):
            for model in FALLBACK_CHAINS[t]:
                if self.health[model].is_available():
                    return model
        
        return None  # Everything is down — this should never happen
    
    def _find_tier(self, model_alias: str) -> int:
        """Find which tier a model belongs to."""
        for tier, models in FALLBACK_CHAINS.items():
            if model_alias in models:
                return tier
        return 3  # Default
    
    def get_health_report(self) -> Dict:
        """Get health status of all models."""
        report = {"timestamp": datetime.now().isoformat(), "models": {}, "tiers": {}}
        
        for tier, models in FALLBACK_CHAINS.items():
            tier_health = []
            for model in models:
                h = self.health[model]
                status = h.to_dict()
                report["models"][model] = status
                tier_health.append(status["health_score"])
            
            report["tiers"][f"tier_{tier}"] = {
                "models": models,
                "avg_health": round(sum(tier_health) / len(tier_health), 3) if tier_health else 0,
                "all_available": all(self.health[m].is_available() for m in models),
            }
        
        return report
    
    def get_ranked_models(self, tier: int = None) -> List[Tuple[str, float]]:
        """Get models ranked by health score."""
        models = []
        tiers = [tier] if tier else sorted(FALLBACK_CHAINS.keys())
        
        for t in tiers:
            for model in FALLBACK_CHAINS.get(t, []):
                score = self.health[model].get_score()
                models.append((model, score))
        
        models.sort(key=lambda x: x[1], reverse=True)
        return models


if __name__ == "__main__":
    fm = FallbackManager()
    
    # Simulate some health events
    fm.report_success("Sonnet", latency_ms=1500)
    fm.report_success("Sonnet", latency_ms=2000)
    fm.report_failure("Grok", error="timeout")
    fm.report_failure("Grok", error="timeout")
    fm.report_failure("Grok", error="timeout")  # Should blacklist
    
    print(f"Preferred Sonnet: {fm.get_available_model(preferred='Sonnet', tier=5)}")
    print(f"Preferred Grok (blacklisted): {fm.get_available_model(preferred='Grok', tier=5)}")
    print(f"\nHealth report:")
    for model, score in fm.get_ranked_models():
        h = fm.health[model]
        print(f"  {model:15s} | score={score:.3f} | available={h.is_available()} | slow={h.is_slow()}")
