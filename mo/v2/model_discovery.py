#!/usr/bin/env python3
"""
MO Phase 3.1 — Semi-Automated Model Discovery & Benchmarking
==============================================================
Discovers new models from providers, benchmarks them, and presents
results for human approval before adding to live rotation.
"""

import json
import time
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime
from dataclasses import dataclass, asdict, field

from token_estimator import MODEL_COSTS


@dataclass
class ModelCandidate:
    """A newly discovered model candidate."""
    provider: str
    model_id: str
    alias: str
    input_cost_per_m: float
    output_cost_per_m: float
    context_window: int = 0
    discovered_at: str = ""
    benchmark_results: Dict = field(default_factory=dict)
    status: str = "discovered"  # discovered, benchmarking, ready_for_review, approved, rejected
    review_notes: str = ""
    tier_recommendation: int = 0


class ModelDiscovery:
    """Semi-automated model discovery and benchmarking."""
    
    BENCHMARK_PROMPTS = {
        "simple_qa": {
            "prompt": "What is the capital of France?",
            "expected_contains": "Paris",
            "max_tokens": 50,
        },
        "code_gen": {
            "prompt": "Write a Python function that calculates the fibonacci sequence up to n terms.",
            "expected_contains": "def",
            "max_tokens": 300,
        },
        "reasoning": {
            "prompt": "If all roses are flowers and some flowers fade quickly, can we conclude that some roses fade quickly? Explain your reasoning step by step.",
            "expected_contains": "cannot conclude",
            "max_tokens": 500,
        },
        "architecture": {
            "prompt": "Design a high-level architecture for a real-time chat application that supports 1M concurrent users. Include components, data flow, and technology choices.",
            "expected_contains": "WebSocket",
            "max_tokens": 1000,
        },
        "instruction_following": {
            "prompt": "List exactly 5 programming languages that start with the letter P. Format as a numbered list.",
            "expected_contains": "Python",
            "max_tokens": 200,
        },
    }
    
    def __init__(self):
        self.candidates: Dict[str, ModelCandidate] = {}
        self.db_path = Path.home() / ".openclaw" / "workspace" / "mo" / "v2" / "model_discovery.json"
        self._load()
    
    def _load(self):
        if self.db_path.exists():
            try:
                with open(self.db_path) as f:
                    data = json.load(f)
                for k, v in data.items():
                    self.candidates[k] = ModelCandidate(**v)
            except (json.JSONDecodeError, TypeError):
                pass
    
    def _save(self):
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        data = {k: asdict(v) for k, v in self.candidates.items()}
        with open(self.db_path, 'w') as f:
            json.dump(data, f, indent=2)
    
    def register_candidate(self, provider: str, model_id: str, alias: str,
                          input_cost: float, output_cost: float,
                          context_window: int = 0) -> ModelCandidate:
        """Register a new model candidate for evaluation."""
        candidate = ModelCandidate(
            provider=provider,
            model_id=model_id,
            alias=alias,
            input_cost_per_m=input_cost,
            output_cost_per_m=output_cost,
            context_window=context_window,
            discovered_at=datetime.now().isoformat(),
        )
        self.candidates[alias] = candidate
        self._save()
        return candidate
    
    def benchmark_candidate(self, alias: str, api_caller=None) -> Dict:
        """
        Run benchmarks on a candidate model.
        
        Args:
            alias: Model alias to benchmark
            api_caller: Optional callable(prompt, max_tokens) → response_text
                       If None, generates simulated results
        """
        candidate = self.candidates.get(alias)
        if not candidate:
            return {"error": f"Candidate '{alias}' not found"}
        
        candidate.status = "benchmarking"
        results = {}
        
        for test_name, test_config in self.BENCHMARK_PROMPTS.items():
            start = time.time()
            
            if api_caller:
                try:
                    response = api_caller(test_config["prompt"], test_config["max_tokens"])
                    latency = (time.time() - start) * 1000
                    
                    # Score the response
                    contains_expected = test_config["expected_contains"].lower() in response.lower()
                    word_count = len(response.split())
                    
                    results[test_name] = {
                        "latency_ms": round(latency, 0),
                        "contains_expected": contains_expected,
                        "response_length": word_count,
                        "score": 1.0 if contains_expected else 0.5,
                        "status": "pass" if contains_expected else "partial",
                    }
                except Exception as e:
                    results[test_name] = {
                        "status": "error",
                        "error": str(e),
                        "score": 0.0,
                    }
            else:
                # Simulated benchmark (for testing without API calls)
                results[test_name] = {
                    "latency_ms": 0,
                    "contains_expected": True,
                    "score": 0.85,
                    "status": "simulated",
                }
        
        # Calculate overall score
        scores = [r.get("score", 0) for r in results.values()]
        overall = sum(scores) / len(scores) if scores else 0
        
        # Recommend tier based on cost and quality
        cost_avg = (candidate.input_cost_per_m + candidate.output_cost_per_m) / 2
        if cost_avg <= 0.15:
            tier_rec = 1
        elif cost_avg <= 0.5:
            tier_rec = 2
        elif cost_avg <= 1.0:
            tier_rec = 3
        elif cost_avg <= 2.0:
            tier_rec = 4
        else:
            tier_rec = 5
        
        # Adjust tier by quality
        if overall >= 0.9:
            tier_rec = min(5, tier_rec + 1)
        elif overall < 0.6:
            tier_rec = max(1, tier_rec - 1)
        
        candidate.benchmark_results = {
            "tests": results,
            "overall_score": round(overall, 3),
            "benchmarked_at": datetime.now().isoformat(),
        }
        candidate.tier_recommendation = tier_rec
        candidate.status = "ready_for_review"
        
        self._save()
        
        return {
            "alias": alias,
            "overall_score": overall,
            "tier_recommendation": tier_rec,
            "tests": results,
            "cost": {"input": candidate.input_cost_per_m, "output": candidate.output_cost_per_m},
        }
    
    def approve_candidate(self, alias: str, notes: str = "") -> bool:
        """Approve a candidate and add to MODEL_COSTS."""
        candidate = self.candidates.get(alias)
        if not candidate or candidate.status != "ready_for_review":
            return False
        
        candidate.status = "approved"
        candidate.review_notes = notes
        self._save()
        
        # Add to live model costs
        MODEL_COSTS[alias] = {
            "input": candidate.input_cost_per_m,
            "output": candidate.output_cost_per_m,
            "provider": candidate.provider,
            "alias": candidate.model_id,
        }
        
        return True
    
    def reject_candidate(self, alias: str, notes: str = "") -> bool:
        """Reject a candidate."""
        candidate = self.candidates.get(alias)
        if not candidate:
            return False
        
        candidate.status = "rejected"
        candidate.review_notes = notes
        self._save()
        return True
    
    def list_candidates(self, status: str = None) -> List[Dict]:
        """List all candidates."""
        results = []
        for alias, c in self.candidates.items():
            if status and c.status != status:
                continue
            results.append({
                "alias": alias,
                "provider": c.provider,
                "model_id": c.model_id,
                "cost": f"${c.input_cost_per_m}/${c.output_cost_per_m}",
                "tier_rec": c.tier_recommendation,
                "score": c.benchmark_results.get("overall_score", "N/A"),
                "status": c.status,
            })
        return results
    
    def format_review(self, alias: str) -> str:
        """Format candidate review for chat."""
        c = self.candidates.get(alias)
        if not c:
            return f"❌ Candidate '{alias}' not found"
        
        score = c.benchmark_results.get("overall_score", 0)
        score_bar = "█" * int(score * 10) + "░" * (10 - int(score * 10))
        
        lines = [
            f"🆕 **New Model Review: {alias}**",
            f"Provider: {c.provider} | ID: `{c.model_id}`",
            f"Cost: ${c.input_cost_per_m}/M input, ${c.output_cost_per_m}/M output",
            f"Score: {score_bar} {score:.0%}",
            f"Tier Recommendation: **{c.tier_recommendation}**",
            f"Status: {c.status}",
            "",
            "**Benchmark Results:**",
        ]
        
        for test_name, result in c.benchmark_results.get("tests", {}).items():
            emoji = "✅" if result.get("score", 0) >= 0.8 else "⚠️" if result.get("score", 0) >= 0.5 else "❌"
            lines.append(f"  {emoji} {test_name}: {result.get('status', 'unknown')}")
        
        lines.append(f"\nTo approve: `discovery.approve_candidate('{alias}')`")
        lines.append(f"To reject: `discovery.reject_candidate('{alias}')`")
        
        return "\n".join(lines)


if __name__ == "__main__":
    discovery = ModelDiscovery()
    
    # Register a new model
    discovery.register_candidate(
        provider="deepseek", model_id="deepseek-v3",
        alias="DeepSeekV3", input_cost=0.27, output_cost=1.10,
        context_window=128000
    )
    
    # Benchmark it (simulated)
    results = discovery.benchmark_candidate("DeepSeekV3")
    print(f"Benchmark score: {results['overall_score']:.0%}")
    print(f"Tier recommendation: {results['tier_recommendation']}")
    
    # Review
    print(f"\n{discovery.format_review('DeepSeekV3')}")
    
    # Approve
    discovery.approve_candidate("DeepSeekV3", notes="Looks good for code tasks")
    print(f"\nApproved! Candidates: {discovery.list_candidates()}")
    print("\n✅ Model Discovery tested")
