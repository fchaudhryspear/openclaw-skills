#!/usr/bin/env python3
"""
MO Phase 2.3 — API Latency & Uptime Monitoring
================================================
Real-time tracking of API latency and error rates per provider.
Auto-deprioritizes slow/failing models within 30s of degradation.
"""

import json
import time
import threading
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from collections import defaultdict, deque


class LatencyMonitor:
    """Real-time latency and uptime monitor for model providers."""
    
    def __init__(self):
        self._metrics: Dict[str, deque] = defaultdict(lambda: deque(maxlen=100))
        self._errors: Dict[str, deque] = defaultdict(lambda: deque(maxlen=50))
        self._status: Dict[str, str] = {}  # model → "healthy"|"degraded"|"down"
        self._callbacks: List = []
        
        # Thresholds
        self.slow_threshold_ms = 15000      # 15s = slow
        self.very_slow_threshold_ms = 30000 # 30s = very slow
        self.error_threshold = 0.3          # 30% error rate = degraded
        self.down_threshold = 0.5           # 50% error rate = down
        self.window_seconds = 300           # 5-minute sliding window
    
    def record_request(self, model: str, latency_ms: float, 
                       success: bool = True, error: str = None):
        """Record a completed API request."""
        now = time.time()
        
        self._metrics[model].append({
            "timestamp": now,
            "latency_ms": latency_ms,
            "success": success,
        })
        
        if not success:
            self._errors[model].append({
                "timestamp": now,
                "error": error or "unknown",
            })
        
        # Evaluate health
        old_status = self._status.get(model, "healthy")
        new_status = self._evaluate_health(model)
        self._status[model] = new_status
        
        # Fire callbacks on status change
        if old_status != new_status:
            for cb in self._callbacks:
                try:
                    cb(model, old_status, new_status)
                except Exception:
                    pass
    
    def on_status_change(self, callback):
        """Register callback for status changes: callback(model, old_status, new_status)"""
        self._callbacks.append(callback)
    
    def _evaluate_health(self, model: str) -> str:
        """Evaluate current health status of a model."""
        now = time.time()
        cutoff = now - self.window_seconds
        
        # Get recent metrics
        recent = [m for m in self._metrics[model] if m["timestamp"] >= cutoff]
        if not recent:
            return "healthy"  # No data = assume healthy
        
        # Error rate
        total = len(recent)
        errors = sum(1 for m in recent if not m["success"])
        error_rate = errors / total
        
        if error_rate >= self.down_threshold:
            return "down"
        
        if error_rate >= self.error_threshold:
            return "degraded"
        
        # Latency check
        latencies = [m["latency_ms"] for m in recent if m["success"]]
        if latencies:
            p95 = sorted(latencies)[int(len(latencies) * 0.95)]
            if p95 >= self.very_slow_threshold_ms:
                return "degraded"
        
        return "healthy"
    
    def get_model_health(self, model: str) -> Dict:
        """Get detailed health metrics for a model."""
        now = time.time()
        cutoff = now - self.window_seconds
        recent = [m for m in self._metrics[model] if m["timestamp"] >= cutoff]
        
        if not recent:
            return {
                "model": model,
                "status": self._status.get(model, "unknown"),
                "requests": 0,
                "error_rate": 0,
                "avg_latency_ms": 0,
                "p95_latency_ms": 0,
                "p99_latency_ms": 0,
            }
        
        latencies = sorted([m["latency_ms"] for m in recent if m["success"]])
        errors = sum(1 for m in recent if not m["success"])
        
        return {
            "model": model,
            "status": self._status.get(model, "healthy"),
            "requests": len(recent),
            "error_rate": round(errors / len(recent), 3),
            "errors": errors,
            "avg_latency_ms": round(sum(latencies) / len(latencies), 0) if latencies else 0,
            "p50_latency_ms": latencies[len(latencies) // 2] if latencies else 0,
            "p95_latency_ms": latencies[int(len(latencies) * 0.95)] if latencies else 0,
            "p99_latency_ms": latencies[int(len(latencies) * 0.99)] if latencies else 0,
            "window_seconds": self.window_seconds,
        }
    
    def get_all_health(self) -> List[Dict]:
        """Get health summary for all tracked models."""
        models = set(list(self._metrics.keys()) + list(self._status.keys()))
        return sorted(
            [self.get_model_health(m) for m in models],
            key=lambda x: {"healthy": 0, "degraded": 1, "down": 2}.get(x["status"], 3)
        )
    
    def is_available(self, model: str) -> bool:
        """Quick check if a model is available for routing."""
        return self._status.get(model, "healthy") != "down"
    
    def is_healthy(self, model: str) -> bool:
        """Quick check if a model is fully healthy."""
        return self._status.get(model, "healthy") == "healthy"
    
    def get_penalty(self, model: str) -> float:
        """Get routing penalty factor (1.0 = no penalty, 0 = blocked)."""
        status = self._status.get(model, "healthy")
        return {"healthy": 1.0, "degraded": 0.5, "down": 0.0, "unknown": 0.8}.get(status, 1.0)
    
    def format_health_report(self) -> str:
        """Format health report for chat."""
        health = self.get_all_health()
        if not health:
            return "📡 **API Health:** No data yet"
        
        emoji_map = {"healthy": "🟢", "degraded": "🟡", "down": "🔴", "unknown": "⚪"}
        
        lines = ["📡 **API Health Monitor**", ""]
        for h in health:
            emoji = emoji_map.get(h["status"], "⚪")
            lines.append(
                f"{emoji} **{h['model']}** — {h['status']} | "
                f"Reqs: {h['requests']} | Errors: {h['error_rate']*100:.0f}% | "
                f"Avg: {h['avg_latency_ms']:.0f}ms | P95: {h['p95_latency_ms']:.0f}ms"
            )
        
        return "\n".join(lines)


if __name__ == "__main__":
    monitor = LatencyMonitor()
    
    # Status change callback
    monitor.on_status_change(lambda m, old, new: print(f"  ⚡ {m}: {old} → {new}"))
    
    # Simulate healthy model
    for _ in range(10):
        monitor.record_request("Sonnet", latency_ms=2000, success=True)
    
    # Simulate degrading model
    for _ in range(5):
        monitor.record_request("Grok", latency_ms=25000, success=True)
    for _ in range(3):
        monitor.record_request("Grok", latency_ms=0, success=False, error="timeout")
    
    # Simulate down model
    for _ in range(8):
        monitor.record_request("GPT4o", latency_ms=0, success=False, error="503")
    
    print(monitor.format_health_report())
    print(f"\nSonnet available: {monitor.is_available('Sonnet')}")
    print(f"Grok available: {monitor.is_available('Grok')}")
    print(f"GPT4o available: {monitor.is_available('GPT4o')}")
    print("\n✅ Latency Monitor tested")
