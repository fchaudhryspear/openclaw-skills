#!/usr/bin/env python3
"""
MO Phase 1.2 — Dynamic Cost-Critical Thresholds
=================================================
Adjusts confidence score thresholds for model escalation based on
task criticality, budget constraints, and historical performance.

Usage:
    from mo.v2.dynamic_thresholds import ThresholdManager
    tm = ThresholdManager()
    thresholds = tm.get_thresholds(criticality="low", budget_mode="penny_pincher")
    # thresholds.accept = 0.75, thresholds.review = 0.55, thresholds.escalate = 0.55
"""

import json
from pathlib import Path
from typing import Dict, Optional, NamedTuple
from datetime import datetime


class Thresholds(NamedTuple):
    """Confidence score thresholds for routing decisions."""
    accept: float      # >= this: auto-accept response
    review: float      # >= this but < accept: flag for review
    escalate: float    # < this: auto-escalate to next tier
    max_escalations: int  # max escalation chain length


# ── Preset Profiles ──────────────────────────────────────────────────────────

PROFILES = {
    # Criticality-based
    "low": Thresholds(accept=0.75, review=0.55, escalate=0.55, max_escalations=1),
    "medium": Thresholds(accept=0.85, review=0.70, escalate=0.70, max_escalations=2),
    "high": Thresholds(accept=0.92, review=0.80, escalate=0.80, max_escalations=3),
    "critical": Thresholds(accept=0.95, review=0.85, escalate=0.85, max_escalations=4),
    
    # Budget-based overlays
    "penny_pincher": Thresholds(accept=0.70, review=0.50, escalate=0.50, max_escalations=1),
    "balanced": Thresholds(accept=0.85, review=0.70, escalate=0.70, max_escalations=2),
    "quality_first": Thresholds(accept=0.90, review=0.80, escalate=0.80, max_escalations=3),
    
    # Default (matches existing MO v2.0)
    "default": Thresholds(accept=0.85, review=0.70, escalate=0.70, max_escalations=3),
}

# Task type → default criticality mapping
TASK_CRITICALITY = {
    "simple_qa":     "low",
    "summarize":     "low",
    "code_gen":      "medium",
    "debug":         "medium",
    "refactor":      "medium",
    "architecture":  "high",
    "creative":      "low",
    "security_audit": "critical",
    "production_deploy": "critical",
    "default":       "medium",
}


class ThresholdManager:
    """Manages dynamic confidence thresholds for MO routing."""
    
    def __init__(self, config_path: str = None):
        self.config_path = config_path or str(
            Path.home() / ".openclaw" / "workspace" / "mo" / "v2" / "threshold_config.json"
        )
        self.config = self._load_config()
        self.override = None  # Manual override
        
    def _load_config(self) -> Dict:
        """Load user customizations."""
        try:
            path = Path(self.config_path)
            if path.exists():
                with open(path) as f:
                    return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
        return {
            "default_budget_mode": "balanced",
            "custom_profiles": {},
            "task_overrides": {},
        }
    
    def save_config(self):
        """Persist config."""
        path = Path(self.config_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, 'w') as f:
            json.dump(self.config, f, indent=2)
    
    def set_budget_mode(self, mode: str):
        """Set global budget mode: penny_pincher, balanced, quality_first."""
        if mode in PROFILES:
            self.config["default_budget_mode"] = mode
            self.save_config()
    
    def set_manual_override(self, thresholds: Optional[Thresholds]):
        """Set manual threshold override (None to clear)."""
        self.override = thresholds
    
    def get_thresholds(self, criticality: str = None, 
                       task_type: str = None,
                       budget_mode: str = None) -> Thresholds:
        """
        Get dynamic thresholds based on task criticality and budget mode.
        
        Priority: manual_override > criticality > task_type default > budget_mode > default
        """
        if self.override:
            return self.override
        
        # Determine criticality
        if not criticality and task_type:
            criticality = TASK_CRITICALITY.get(task_type, 
                         self.config.get("task_overrides", {}).get(task_type, "medium"))
        
        if criticality and criticality in PROFILES:
            base = PROFILES[criticality]
        else:
            # Fall back to budget mode
            mode = budget_mode or self.config.get("default_budget_mode", "balanced")
            base = PROFILES.get(mode, PROFILES["default"])
        
        # Check for custom profile
        custom = self.config.get("custom_profiles", {}).get(criticality or "default")
        if custom:
            return Thresholds(
                accept=custom.get("accept", base.accept),
                review=custom.get("review", base.review),
                escalate=custom.get("escalate", base.escalate),
                max_escalations=custom.get("max_escalations", base.max_escalations),
            )
        
        return base
    
    def should_accept(self, confidence: float, criticality: str = None,
                      task_type: str = None) -> str:
        """
        Evaluate a confidence score and return routing decision.
        
        Returns: "accept", "review", or "escalate"
        """
        t = self.get_thresholds(criticality=criticality, task_type=task_type)
        
        if confidence >= t.accept:
            return "accept"
        elif confidence >= t.review:
            return "review"
        else:
            return "escalate"
    
    def escalation_allowed(self, current_escalations: int, 
                           criticality: str = None,
                           task_type: str = None) -> bool:
        """Check if another escalation is allowed."""
        t = self.get_thresholds(criticality=criticality, task_type=task_type)
        return current_escalations < t.max_escalations


if __name__ == "__main__":
    tm = ThresholdManager()
    
    test_cases = [
        ("simple_qa", 0.78),
        ("architecture", 0.78),
        ("security_audit", 0.88),
        ("code_gen", 0.65),
        ("creative", 0.60),
    ]
    
    for task, confidence in test_cases:
        decision = tm.should_accept(confidence, task_type=task)
        t = tm.get_thresholds(task_type=task)
        print(f"Task: {task:20s} | Confidence: {confidence:.2f} | "
              f"Thresholds: {t.accept:.2f}/{t.review:.2f}/{t.escalate:.2f} | "
              f"Decision: {decision}")
