#!/usr/bin/env python3
"""
MO v2.1 CLI — Command-line interface for the Model Orchestrator.

Usage:
    mo route "query text"                    # Get model recommendation
    mo route "query" --topic code_gen        # With topic hint
    mo cost                                  # Daily cost report
    mo test                                  # Run routing tests
    mo cache-stats                           # Show cache/calibration stats
    mo feedback <model> <rating> [topic]     # Record model feedback
"""

import sys
import json
import argparse
from pathlib import Path

# Ensure mo/v2 is in path
sys.path.insert(0, str(Path(__file__).parent))

from mo_orchestrator import MOOrchestrator
from token_estimator import TokenEstimator
from nexdev_bridge import MONexDevBridge


def cmd_route(args):
    """Route a query to the optimal model."""
    mo = MOOrchestrator()
    query = " ".join(args.query)
    
    decision = mo.route(
        query=query,
        topic=args.topic,
        complexity=args.complexity,
        criticality=args.criticality,
        max_cost=args.max_cost,
        preferred_model=args.prefer,
    )
    
    if args.json:
        print(json.dumps(decision, indent=2))
    else:
        print(f"Model: {decision['model']} (Tier {decision['tier']})")
        print(f"Task: {decision['task_type']} | Topic: {decision['topic']}")
        print(f"Criticality: {decision['criticality']}")
        print(f"Est. Cost: ${decision['estimated_cost']:.6f}")
        print(f"Est. Tokens: {decision['estimated_tokens']:,}")
        if decision.get('feedback_recommendation'):
            print(f"Feedback rec: {decision['feedback_recommendation']}")
        if args.verbose:
            print("Reasoning:")
            for r in decision.get('reasoning', []):
                print(f"  {r}")


def cmd_cost(args):
    """Show daily cost report."""
    mo = MOOrchestrator()
    print(mo.get_daily_report())


def cmd_test(args):
    """Run routing test suite."""
    mo = MOOrchestrator()
    
    tests = [
        ("What is Python?", "simple_qa", 1, "QwenFlash"),
        ("List my S3 buckets", "simple_qa", 1, "QwenFlash"),
        ("Fix TypeError in auth.py line 42", "debug", 2, "QwenCoder"),
        ("Write a FastAPI endpoint for user CRUD", "code_gen", 2, "QwenCoder"),
        ("Refactor the payment service to use async", "refactor", 3, "QwenCoder"),
        ("Design microservice architecture for 10M users", "architecture", 4, "Qwen35"),
        ("Security audit on our API authentication flow", "security_audit", 5, "Sonnet"),
    ]
    
    passed = 0
    failed = 0
    
    for query, expected_task, expected_min_tier, expected_model in tests:
        decision = mo.route(query)
        model = decision['model']
        tier = decision['tier']
        task = decision['task_type']
        
        # Check if routing is reasonable
        tier_ok = tier >= expected_min_tier - 1  # Allow 1 tier tolerance
        model_ok = model == expected_model
        
        status = "✅" if model_ok else ("⚠️" if tier_ok else "❌")
        if model_ok:
            passed += 1
        else:
            failed += 1
        
        print(f"{status} \"{query[:50]}...\"")
        print(f"   Expected: {expected_model} (Tier {expected_min_tier}) | Got: {model} (Tier {tier})")
        print(f"   Task: {task} | Cost: ${decision['estimated_cost']:.6f}")
        print()
    
    print(f"Results: {passed}/{passed+failed} exact matches")


def cmd_nexdev(args):
    """Run NexDev bridge demo."""
    bridge = MONexDevBridge()
    
    stages = [
        ("product_manager", "Generate specs for a SaaS property management platform"),
        ("architect", "Design microservice architecture for property management"),
        ("developer", "Implement FastAPI endpoints for maintenance tickets"),
        ("qa_engineer", "Generate unit tests for the maintenance service"),
        ("security_architect", "Audit authentication flow for OWASP Top 10"),
    ]
    
    project_id = args.project or "DEMO-001"
    
    print(f"🔗 NexDev Pipeline — Project: {project_id}\n")
    
    total_cost = 0
    for role, query in stages:
        decision = bridge.get_model_for_stage(role, query, project_id=project_id)
        cost = decision.get('estimated_cost', 0)
        total_cost += cost
        
        print(f"  {role:25s} → {decision['model']:15s} (Tier {decision['tier']}) | ${cost:.6f}")
        
        # Simulate completion
        bridge.report_stage_completion(
            role, decision['model'],
            input_tokens=1500, output_tokens=3000,
            confidence=0.88, project_id=project_id,
            latency_ms=2500, success=True
        )
    
    print(f"\n  {'Total Pipeline Cost':25s}    ${total_cost:.6f}")
    print(f"\n{bridge.get_stage_cost_breakdown(project_id)}")


def cmd_estimate(args):
    """Estimate cost for a query on a specific model."""
    estimator = TokenEstimator()
    query = " ".join(args.query)
    
    est = estimator.estimate(query, model_alias=args.model)
    
    if args.json:
        print(json.dumps(est, indent=2, default=str))
    else:
        print(f"Query: \"{query[:60]}...\"")
        print(f"Task: {est['task_type']}")
        print(f"Tokens: ~{est['total_tokens']:,} (in: {est['input_tokens']:,}, out: {est['output_tokens']:,})")
        if est['cost']:
            print(f"Cost on {args.model}: ${est['cost']['estimated_cost']:.6f}")
        print(f"\nCheapest 3:")
        for c in est['cheapest_3']:
            print(f"  {c['model']:15s} ${c['estimated_cost']:.6f}")


def cmd_feedback(args):
    """Record user feedback for a model."""
    from user_feedback import FeedbackCollector
    fc = FeedbackCollector()
    fc.record_feedback(args.model, args.rating, topic=args.topic or "general")
    print(f"✅ Recorded: {args.model} = {args.rating}/5 (topic: {args.topic or 'general'})")


def cmd_cache(args):
    """Show calibration/cache stats."""
    estimator = TokenEstimator()
    cal = estimator.calibration_data
    
    if not cal:
        print("No calibration data yet. Token estimates will use defaults.")
        return
    
    print("Token Calibration Data:")
    for provider, data in cal.items():
        print(f"  {provider}: ratio={data['avg_ratio']:.3f}, "
              f"samples={data['samples']}, error={data['total_error_pct']:.1f}%")


def main():
    parser = argparse.ArgumentParser(description="MO v2.1 — Model Orchestrator CLI")
    sub = parser.add_subparsers(dest="command")
    
    # route
    p_route = sub.add_parser("route", help="Get model recommendation for a query")
    p_route.add_argument("query", nargs="+", help="Query text")
    p_route.add_argument("--topic", help="Topic hint")
    p_route.add_argument("--complexity", type=int, help="Complexity 1-5")
    p_route.add_argument("--criticality", help="Criticality level")
    p_route.add_argument("--max-cost", type=float, help="Max cost per query")
    p_route.add_argument("--prefer", help="Preferred model")
    p_route.add_argument("--json", action="store_true", help="JSON output")
    p_route.add_argument("--verbose", "-v", action="store_true")
    
    # cost
    sub.add_parser("cost", help="Daily cost report")
    
    # test
    sub.add_parser("test", help="Run routing test suite")
    
    # nexdev
    p_nexdev = sub.add_parser("nexdev", help="NexDev bridge demo")
    p_nexdev.add_argument("--project", help="Project ID")
    
    # estimate
    p_est = sub.add_parser("estimate", help="Estimate cost for a query")
    p_est.add_argument("query", nargs="+", help="Query text")
    p_est.add_argument("--model", default="GeminiFlash", help="Model alias")
    p_est.add_argument("--json", action="store_true")
    
    # feedback
    p_fb = sub.add_parser("feedback", help="Record model feedback")
    p_fb.add_argument("model", help="Model alias")
    p_fb.add_argument("rating", type=int, choices=[1,2,3,4,5])
    p_fb.add_argument("--topic", help="Topic")
    
    # cache
    sub.add_parser("cache", help="Show calibration stats")
    
    args = parser.parse_args()
    
    if args.command == "route":
        cmd_route(args)
    elif args.command == "cost":
        cmd_cost(args)
    elif args.command == "test":
        cmd_test(args)
    elif args.command == "nexdev":
        cmd_nexdev(args)
    elif args.command == "estimate":
        cmd_estimate(args)
    elif args.command == "feedback":
        cmd_feedback(args)
    elif args.command == "cache":
        cmd_cache(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
