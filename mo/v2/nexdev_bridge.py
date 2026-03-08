#!/usr/bin/env python3
"""
MO ↔ NexDev Bridge — Symbiotic Integration
=============================================
NexDev uses MO for all internal model selections.
MO learns from NexDev's diverse, heavy workloads.

This bridge connects both systems for mutual benefit.
"""

import json
import sys
from pathlib import Path
from typing import Dict, Optional
from datetime import datetime

# Add MO to path
MO_DIR = Path(__file__).parent
sys.path.insert(0, str(MO_DIR))

from mo_orchestrator import MOOrchestrator
from token_estimator import TokenEstimator
from fallback_chain import FallbackManager
from cost_dashboard import CostTracker


class MONexDevBridge:
    """
    Bridge between MO and NexDev.
    
    NexDev calls this to:
    - Get model recommendations for each SDLC stage
    - Report completions back to MO for learning
    - Track costs across the full pipeline
    
    MO benefits from:
    - Diverse workload data (PM, Architect, Developer, QA tasks)
    - Large sample sizes for learning
    - Real-world performance metrics
    """
    
    # Default model preferences per SDLC agent role
    ROLE_MODEL_PREFERENCES = {
        "product_manager": {
            "default_tier": 3,
            "preferred": ["Qwen35", "Kimi"],
            "topic": "requirements_engineering",
            "criticality": "medium",
        },
        "architect": {
            "default_tier": 4,
            "preferred": ["Sonnet", "Qwen35"],
            "topic": "architecture",
            "criticality": "high",
        },
        "developer": {
            "default_tier": 3,
            "preferred": ["QwenCoder", "Qwen35"],
            "topic": "code_gen",
            "criticality": "medium",
        },
        "qa_engineer": {
            "default_tier": 2,
            "preferred": ["QwenCoder", "GeminiFlash"],
            "topic": "testing",
            "criticality": "medium",
        },
        "security_architect": {
            "default_tier": 5,
            "preferred": ["Sonnet", "opus"],
            "topic": "security_audit",
            "criticality": "critical",
        },
        "performance_engineer": {
            "default_tier": 3,
            "preferred": ["Qwen35", "GeminiPro"],
            "topic": "performance",
            "criticality": "high",
        },
        "devops_engineer": {
            "default_tier": 2,
            "preferred": ["QwenCoder", "GeminiFlash"],
            "topic": "infrastructure",
            "criticality": "medium",
        },
    }
    
    def __init__(self):
        self.mo = MOOrchestrator()
        self.pipeline_costs: Dict[str, float] = {}  # project_id → total cost
    
    def get_model_for_stage(self, agent_role: str, query: str,
                            project_id: str = None,
                            budget_mode: str = None) -> Dict:
        """
        Get the optimal model for a NexDev pipeline stage.
        
        Args:
            agent_role: The SDLC agent role (e.g., "developer", "architect")
            query: The actual prompt/task being sent to the model
            project_id: Project ID for cost tracking
            budget_mode: Override budget mode
        
        Returns:
            Dict with model recommendation and reasoning
        """
        role_config = self.ROLE_MODEL_PREFERENCES.get(
            agent_role, self.ROLE_MODEL_PREFERENCES["developer"]
        )
        
        # Use MO's full routing engine
        decision = self.mo.route(
            query=query,
            topic=role_config["topic"],
            complexity=role_config["default_tier"],
            criticality=role_config["criticality"],
            preferred_model=role_config["preferred"][0] if role_config["preferred"] else None,
        )
        
        # Annotate with NexDev context
        decision["nexdev_role"] = agent_role
        decision["nexdev_project"] = project_id
        
        return decision
    
    def report_stage_completion(self, agent_role: str, model: str,
                                 input_tokens: int, output_tokens: int,
                                 confidence: float = None,
                                 project_id: str = None,
                                 latency_ms: float = None,
                                 success: bool = True):
        """
        Report a completed NexDev stage back to MO for learning.
        
        This is the key feedback loop — MO learns from NexDev's
        diverse workload to improve future routing decisions.
        """
        role_config = self.ROLE_MODEL_PREFERENCES.get(
            agent_role, self.ROLE_MODEL_PREFERENCES["developer"]
        )
        
        if success:
            self.mo.record_completion(
                model=model,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                confidence=confidence,
                topic=role_config["topic"],
                task_type=role_config["topic"],
                latency_ms=latency_ms,
            )
        else:
            self.mo.record_failure(model, error=f"NexDev {agent_role} stage failed")
        
        # Track pipeline cost
        if project_id:
            cost = self.mo.cost_tracker._calculate_cost(model, input_tokens, output_tokens)
            self.pipeline_costs[project_id] = self.pipeline_costs.get(project_id, 0) + cost
    
    def get_pipeline_cost(self, project_id: str) -> Dict:
        """Get total MO cost for a NexDev pipeline."""
        return {
            "project_id": project_id,
            "total_cost": round(self.pipeline_costs.get(project_id, 0), 6),
            "timestamp": datetime.now().isoformat(),
        }
    
    def get_stage_cost_breakdown(self, project_id: str = None) -> str:
        """Get formatted cost report for NexDev pipelines."""
        daily = self.mo.get_daily_report()
        
        lines = [
            "🔗 **MO ↔ NexDev Cost Bridge**",
            daily,
        ]
        
        if project_id and project_id in self.pipeline_costs:
            lines.append(f"\n**Pipeline {project_id}:** ${self.pipeline_costs[project_id]:.6f}")
        
        return "\n".join(lines)


# Singleton instance for easy import
_bridge_instance = None

def get_bridge() -> MONexDevBridge:
    """Get or create the singleton bridge instance."""
    global _bridge_instance
    if _bridge_instance is None:
        _bridge_instance = MONexDevBridge()
    return _bridge_instance


if __name__ == "__main__":
    bridge = MONexDevBridge()
    
    # Simulate NexDev pipeline stages using MO
    stages = [
        ("product_manager", "Generate a specification for a SaaS property management platform"),
        ("architect", "Design microservice architecture for property management with 10K users"),
        ("developer", "Implement FastAPI endpoints for maintenance ticket CRUD operations"),
        ("qa_engineer", "Generate unit tests for the maintenance ticket service"),
        ("security_architect", "Audit the authentication flow for OWASP Top 10 vulnerabilities"),
    ]
    
    print("🔗 MO ↔ NexDev Bridge — Model Selection Demo\n")
    
    for role, query in stages:
        decision = bridge.get_model_for_stage(role, query, project_id="PROJ-DEMO-001")
        print(f"Stage: {role:25s} → Model: {decision['model']:15s} "
              f"(Tier {decision['tier']}) | Est: ${decision['estimated_cost']:.6f}")
        
        # Simulate completion
        bridge.report_stage_completion(
            role, decision['model'], 
            input_tokens=1500, output_tokens=3000,
            confidence=0.88, project_id="PROJ-DEMO-001",
            latency_ms=2500, success=True
        )
    
    print(f"\n{bridge.get_stage_cost_breakdown('PROJ-DEMO-001')}")
