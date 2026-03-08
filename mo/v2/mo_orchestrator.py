#!/usr/bin/env python3
"""
MO v2.1 — Unified Orchestrator (Phase 1 Complete)
===================================================
Ties together all Phase 1 components into a single routing decision engine.

Usage:
    from mo.v2.mo_orchestrator import MOOrchestrator
    mo = MOOrchestrator()
    decision = mo.route("Design a microservice architecture for payments", topic="architecture")
    print(f"Use model: {decision['model']} (estimated cost: ${decision['estimated_cost']:.6f})")
"""

import json
from pathlib import Path
from typing import Dict, Optional
from datetime import datetime

from token_estimator import TokenEstimator, MODEL_COSTS
from dynamic_thresholds import ThresholdManager, TASK_CRITICALITY
from user_feedback import FeedbackCollector
from fallback_chain import FallbackManager
from cost_dashboard import CostTracker


# ── Complexity → Tier Mapping ────────────────────────────────────────────────

COMPLEXITY_TIER_MAP = {
    1: ["QwenFlash", "GeminiLite"],           # Simple Q&A
    2: ["GeminiFlash", "QwenCoder"],          # Standard tasks
    3: ["Qwen35", "Kimi"],                     # Advanced
    4: ["GeminiPro", "QwenMax"],              # Premium
    5: ["Sonnet", "opus"],                     # Expert
}

TOPIC_MODEL_PREFERENCES = {
    "code_gen":       ["QwenCoder", "Qwen35", "Sonnet"],
    "architecture":   ["Qwen35", "Sonnet", "opus"],
    "debug":          ["QwenCoder", "GrokFast", "Sonnet"],
    "simple_qa":      ["QwenFlash", "GeminiLite"],
    "summarize":      ["GeminiFlash", "Kimi"],
    "creative":       ["Sonnet", "GPT4o"],
    "security_audit": ["Sonnet", "opus"],
    "refactor":       ["QwenCoder", "Qwen35"],
}


class MOOrchestrator:
    """Unified MO routing engine with all Phase 1 enhancements."""
    
    def __init__(self):
        self.estimator = TokenEstimator()
        self.thresholds = ThresholdManager()
        self.feedback = FeedbackCollector()
        self.fallback = FallbackManager()
        self.cost_tracker = CostTracker()
    
    def route(self, query: str, topic: str = None, 
              complexity: int = None,
              criticality: str = None,
              max_cost: float = None,
              preferred_model: str = None) -> Dict:
        """
        Make a complete routing decision.
        
        Args:
            query: User's query text
            topic: Topic/domain (auto-detected if not provided)
            complexity: 1-5 (auto-detected if not provided)
            criticality: Override criticality level
            max_cost: Maximum acceptable cost per query
            preferred_model: User's preferred model (manual override)
        
        Returns:
            Dict with routing decision, cost estimate, and reasoning
        """
        task_type = self.estimator.classify_task(query)
        topic = topic or task_type
        
        # Step 1: Check user feedback for this topic
        recommendations = self.feedback.get_model_recommendations(topic)
        feedback_model = recommendations[0]["model"] if recommendations else None
        
        # Step 2: Determine complexity and tier
        if complexity is None:
            complexity = self._auto_complexity(query, task_type)
        tier = min(5, max(1, complexity))
        
        # Step 3: Get thresholds for this task
        task_criticality = criticality or TASK_CRITICALITY.get(task_type, "medium")
        thresholds = self.thresholds.get_thresholds(
            criticality=task_criticality, task_type=task_type
        )
        
        # Step 4: Select candidate model
        candidates = self._get_candidates(tier, topic, feedback_model, preferred_model)
        
        # Step 5: Pre-flight cost estimation for each candidate
        best_model = None
        best_estimate = None
        reasoning = []
        
        for candidate in candidates:
            # Check availability
            if not self.fallback.health[candidate].is_available():
                reasoning.append(f"  ⛔ {candidate}: unavailable (blacklisted)")
                continue
            
            estimate = self.estimator.estimate(query, model_alias=candidate)
            cost = estimate["cost"]["estimated_cost"]
            
            # Check max cost constraint
            if max_cost and cost > max_cost:
                reasoning.append(f"  💰 {candidate}: ${cost:.6f} exceeds budget ${max_cost:.6f}")
                continue
            
            if best_model is None or cost < best_estimate["cost"]["estimated_cost"]:
                best_model = candidate
                best_estimate = estimate
                reasoning.append(f"  ✅ {candidate}: ${cost:.6f} — selected")
            else:
                reasoning.append(f"  ➖ {candidate}: ${cost:.6f} — more expensive")
        
        # Step 6: Fallback if no candidate found
        if not best_model:
            best_model = self.fallback.get_available_model(tier=tier)
            if best_model:
                best_estimate = self.estimator.estimate(query, model_alias=best_model)
                reasoning.append(f"  🔄 Fallback to {best_model}")
            else:
                best_model = "QwenFlash"  # Nuclear fallback
                best_estimate = self.estimator.estimate(query, model_alias="QwenFlash")
                reasoning.append(f"  🚨 Nuclear fallback to QwenFlash")
        
        return {
            "model": best_model,
            "model_full": MODEL_COSTS.get(best_model, {}).get("alias", best_model),
            "tier": tier,
            "task_type": task_type,
            "topic": topic,
            "criticality": task_criticality,
            "thresholds": {
                "accept": thresholds.accept,
                "review": thresholds.review,
                "escalate": thresholds.escalate,
                "max_escalations": thresholds.max_escalations,
            },
            "estimated_cost": best_estimate["cost"]["estimated_cost"] if best_estimate else 0,
            "estimated_tokens": best_estimate["total_tokens"] if best_estimate else 0,
            "feedback_recommendation": feedback_model,
            "candidates_evaluated": len(candidates),
            "reasoning": reasoning,
            "timestamp": datetime.now().isoformat(),
        }
    
    def record_completion(self, model: str, input_tokens: int, output_tokens: int,
                          confidence: float = None, topic: str = "general",
                          task_type: str = "default", latency_ms: float = None,
                          was_escalated: bool = False, original_model: str = None):
        """Record a completed query for tracking and learning."""
        # Track cost
        self.cost_tracker.record_query(
            model=model, input_tokens=input_tokens, output_tokens=output_tokens,
            topic=topic, task_type=task_type, was_escalated=was_escalated,
            original_model=original_model, latency_ms=latency_ms
        )
        
        # Track model health
        self.fallback.report_success(model, latency_ms=latency_ms or 0)
        
        # Calibrate token estimator
        word_count = (input_tokens / 1.35)  # Rough reverse estimate
        self.estimator.record_actual(model, input_tokens, output_tokens,
                                     input_tokens, int(word_count))
        
        # Auto-rate based on confidence (implicit feedback)
        if confidence is not None:
            if confidence >= 0.9:
                self.feedback.record_feedback(model, 5, topic=topic, 
                                              feedback_type="implicit")
            elif confidence >= 0.75:
                self.feedback.record_feedback(model, 4, topic=topic,
                                              feedback_type="implicit")
            elif confidence >= 0.5:
                self.feedback.record_feedback(model, 3, topic=topic,
                                              feedback_type="implicit")
    
    def record_failure(self, model: str, error: str = ""):
        """Record a model failure."""
        self.fallback.report_failure(model, error)
    
    def get_daily_report(self) -> str:
        """Get formatted daily cost report."""
        report = self.cost_tracker.daily_report()
        return self.cost_tracker.format_report(report)
    
    def _auto_complexity(self, query: str, task_type: str) -> int:
        """Auto-detect query complexity (1-5)."""
        query_lower = query.lower()
        word_count = len(query.split())
        
        # Simple heuristics
        score = 2  # Default medium
        
        if word_count < 10:
            score = 1
        elif word_count > 100:
            score += 1
        
        # Complexity indicators
        complex_words = ["architecture", "system design", "migration", "enterprise",
                        "distributed", "microservice", "security audit", "compliance",
                        "scalability", "fault-tolerant", "real-time"]
        for word in complex_words:
            if word in query_lower:
                score += 1
                break
        
        # Task type boost
        task_boost = {
            "architecture": 1, "security_audit": 2, "production_deploy": 2,
            "simple_qa": -1, "summarize": -1,
        }
        score += task_boost.get(task_type, 0)
        
        return max(1, min(5, score))
    
    def _get_candidates(self, tier: int, topic: str, 
                        feedback_model: str, preferred_model: str) -> list:
        """Build ordered candidate list."""
        candidates = []
        
        # Manual override first
        if preferred_model:
            candidates.append(preferred_model)
        
        # Feedback-recommended model
        if feedback_model and feedback_model not in candidates:
            candidates.append(feedback_model)
        
        # Topic-preferred models
        for m in TOPIC_MODEL_PREFERENCES.get(topic, []):
            if m not in candidates:
                candidates.append(m)
        
        # Tier defaults
        for m in COMPLEXITY_TIER_MAP.get(tier, []):
            if m not in candidates:
                candidates.append(m)
        
        # Adjacent tiers as backup
        for adj in [tier - 1, tier + 1]:
            for m in COMPLEXITY_TIER_MAP.get(adj, []):
                if m not in candidates:
                    candidates.append(m)
        
        return candidates


if __name__ == "__main__":
    mo = MOOrchestrator()
    
    test_queries = [
        "What is Python?",
        "Design a microservice architecture for a payments platform handling 10M transactions/day",
        "Fix this TypeError in auth.py line 42",
        "Write a React component for a user dashboard",
        "Perform a security audit on our API endpoints",
    ]
    
    for query in test_queries:
        decision = mo.route(query)
        print(f"\n{'='*60}")
        print(f"Query: {query[:60]}...")
        print(f"Model: {decision['model']} (Tier {decision['tier']})")
        print(f"Task: {decision['task_type']} | Criticality: {decision['criticality']}")
        print(f"Est. Cost: ${decision['estimated_cost']:.6f}")
        print(f"Reasoning:")
        for r in decision['reasoning']:
            print(f"  {r}")
