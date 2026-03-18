#!/usr/bin/env python3
"""
NexDev Pipeline Runner — Spawns cost-optimized sub-agents for SDLC stages.

Usage:
    python3 nexdev_pipeline.py run "Build a task management API" --project TASK-001
    python3 nexdev_pipeline.py status --project TASK-001
    python3 nexdev_pipeline.py cost --project TASK-001
"""

import json
import argparse
import subprocess
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional

import sys
sys.path.insert(0, str(Path(__file__).parent))

from nexdev_bridge import MONexDevBridge, get_bridge
from result_cache import ResultCache

PROJECTS_DIR = Path.home() / ".openclaw" / "workspace" / "nexdev" / "projects"


class NexDevPipeline:
    """Manages SDLC pipeline execution with cost-optimized model selection."""
    
    STAGES = [
        {"role": "product_manager", "label": "PM Analysis", "alias": "Kimi"},
        {"role": "architect", "label": "Architecture", "alias": "Qwen35"},
        {"role": "developer", "label": "Code Generation", "alias": "QwenCoder"},
        {"role": "qa_engineer", "label": "QA & Testing", "alias": "GeminiFlash"},
    ]
    
    def __init__(self):
        self.bridge = get_bridge()
        self.cache = ResultCache()
    
    def run(self, task: str, project_id: str = None, 
            stages: List[str] = None, dry_run: bool = False) -> Dict:
        """Run the full SDLC pipeline."""
        project_id = project_id or f"PROJ-{int(time.time())}"
        project_dir = PROJECTS_DIR / project_id
        project_dir.mkdir(parents=True, exist_ok=True)
        
        # Save project metadata
        meta = {
            "project_id": project_id,
            "task": task,
            "started_at": datetime.now().isoformat(),
            "status": "running",
            "stages": {},
            "total_cost": 0.0,
        }
        
        results = {}
        total_cost = 0.0
        
        for stage_def in self.STAGES:
            role = stage_def["role"]
            label = stage_def["label"]
            
            # Skip if not in requested stages
            if stages and role not in stages:
                continue
            
            print(f"\n{'='*60}")
            print(f"Stage: {label} ({role})")
            print(f"{'='*60}")
            
            # Check cache first
            cached = self.cache.get(role, task, project_id)
            if cached:
                print(f"  📦 Cache hit! (age: {cached['age_seconds']}s, hits: {cached['hits']})")
                print(f"  💰 Saved: ${cached['cost']:.6f}")
                results[role] = cached['result']
                meta["stages"][role] = {
                    "status": "cached",
                    "model": cached['model'],
                    "cost": 0.0,
                    "cached_cost": cached['cost'],
                }
                continue
            
            # Get model recommendation from MO
            decision = self.bridge.get_model_for_stage(role, task, project_id=project_id)
            model = decision['model']
            est_cost = decision.get('estimated_cost', 0)
            
            print(f"  🤖 Model: {model} (Tier {decision['tier']})")
            print(f"  💰 Est. Cost: ${est_cost:.6f}")
            
            if dry_run:
                meta["stages"][role] = {
                    "status": "dry_run",
                    "model": model,
                    "estimated_cost": est_cost,
                }
                continue
            
            # Build the prompt with context from previous stages
            prompt = self._build_stage_prompt(role, task, results)
            
            # Save prompt for debugging
            (project_dir / f"{role}_prompt.md").write_text(prompt)
            
            # Execute via OpenClaw sub-agent
            stage_result = self._execute_stage(role, model, prompt, project_id)
            
            if stage_result.get("success"):
                results[role] = stage_result["output"]
                actual_cost = stage_result.get("cost", est_cost)
                total_cost += actual_cost
                
                # Cache the result
                self.cache.put(
                    role, task, stage_result["output"],
                    project_id=project_id, model=model,
                    tokens_used=stage_result.get("tokens", 0),
                    cost=actual_cost,
                )
                
                # Report completion to MO for learning
                self.bridge.report_stage_completion(
                    role, model,
                    input_tokens=stage_result.get("input_tokens", 1500),
                    output_tokens=stage_result.get("output_tokens", 3000),
                    confidence=stage_result.get("confidence", 0.85),
                    project_id=project_id,
                    latency_ms=stage_result.get("latency_ms", 5000),
                    success=True,
                )
                
                # Save output
                (project_dir / f"{role}_output.md").write_text(
                    json.dumps(stage_result["output"], indent=2) if isinstance(stage_result["output"], dict)
                    else str(stage_result["output"])
                )
                
                meta["stages"][role] = {
                    "status": "completed",
                    "model": model,
                    "cost": actual_cost,
                    "tokens": stage_result.get("tokens", 0),
                }
                
                print(f"  ✅ Completed | Cost: ${actual_cost:.6f}")
            else:
                # Report failure
                self.bridge.report_stage_completion(
                    role, model,
                    input_tokens=0, output_tokens=0,
                    project_id=project_id, success=False,
                )
                
                meta["stages"][role] = {
                    "status": "failed",
                    "model": model,
                    "error": stage_result.get("error", "Unknown error"),
                }
                
                print(f"  ❌ Failed: {stage_result.get('error', 'Unknown')}")
        
        # Finalize
        meta["status"] = "completed" if not dry_run else "dry_run"
        meta["completed_at"] = datetime.now().isoformat()
        meta["total_cost"] = round(total_cost, 6)
        
        # Save project metadata
        (project_dir / "meta.json").write_text(json.dumps(meta, indent=2))
        
        return meta
    
    def _build_stage_prompt(self, role: str, task: str, previous_results: Dict) -> str:
        """Build a context-rich prompt using previous stage outputs."""
        prompt_parts = [f"# Task: {task}\n"]
        
        if previous_results:
            prompt_parts.append("## Context from Previous Stages\n")
            for prev_role, output in previous_results.items():
                label = next((s["label"] for s in self.STAGES if s["role"] == prev_role), prev_role)
                prompt_parts.append(f"### {label}\n{output}\n")
        
        role_instructions = {
            "product_manager": "Analyze this task and produce a clear specification with user stories, acceptance criteria, and scope definition.",
            "architect": "Design the technical architecture including components, data flow, API contracts, and technology choices.",
            "developer": "Implement the solution based on the architecture. Produce clean, well-documented code.",
            "qa_engineer": "Generate comprehensive test cases including unit tests, integration tests, and edge cases.",
            "security_architect": "Audit the design and implementation for security vulnerabilities. Produce a security report.",
            "performance_engineer": "Analyze performance characteristics and recommend optimizations.",
            "devops_engineer": "Create deployment configuration, CI/CD pipeline, and infrastructure-as-code.",
        }
        
        prompt_parts.append(f"\n## Your Role: {role}\n{role_instructions.get(role, 'Complete the assigned task.')}\n")
        
        return "\n".join(prompt_parts)
    
    def _execute_stage(self, role: str, model: str, prompt: str, project_id: str) -> Dict:
        """Execute a stage via OpenClaw sub-agent spawn."""
        try:
            # Use openclaw sessions_send or spawn a sub-agent
            # For now, use the CLI to send to a sub-agent
            result = subprocess.run(
                ["openclaw", "cron", "run", "--model", model, "--message", prompt[:500]],
                capture_output=True, text=True, timeout=120,
            )
            
            if result.returncode == 0:
                return {
                    "success": True,
                    "output": result.stdout,
                    "input_tokens": len(prompt.split()) * 1.35,
                    "output_tokens": len(result.stdout.split()) * 1.35,
                    "cost": 0.001,  # Estimate, will be tracked by MO
                    "latency_ms": 5000,
                    "confidence": 0.85,
                }
            else:
                return {"success": False, "error": result.stderr[:200]}
        except subprocess.TimeoutExpired:
            return {"success": False, "error": "Stage timed out after 120s"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def status(self, project_id: str) -> Dict:
        """Get project status."""
        meta_path = PROJECTS_DIR / project_id / "meta.json"
        if meta_path.exists():
            return json.loads(meta_path.read_text())
        return {"error": f"Project {project_id} not found"}
    
    def cost_report(self, project_id: str = None) -> str:
        """Get cost report for a project or all projects."""
        if project_id:
            meta = self.status(project_id)
            if "error" in meta:
                return meta["error"]
            
            lines = [f"📊 Project: {project_id}", f"Total Cost: ${meta.get('total_cost', 0):.6f}", ""]
            for role, stage in meta.get("stages", {}).items():
                status_icon = "✅" if stage["status"] == "completed" else ("📦" if stage["status"] == "cached" else "❌")
                cost = stage.get("cost", 0)
                model = stage.get("model", "?")
                lines.append(f"  {status_icon} {role:25s} {model:15s} ${cost:.6f}")
            return "\n".join(lines)
        
        # All projects
        if not PROJECTS_DIR.exists():
            return "No projects found."
        
        lines = ["📊 All Projects\n"]
        for pdir in sorted(PROJECTS_DIR.iterdir()):
            meta_path = pdir / "meta.json"
            if meta_path.exists():
                meta = json.loads(meta_path.read_text())
                lines.append(f"  {meta['project_id']:20s} ${meta.get('total_cost', 0):.6f}  {meta.get('status', '?')}")
        return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="NexDev Pipeline Runner")
    sub = parser.add_subparsers(dest="command")
    
    p_run = sub.add_parser("run", help="Run SDLC pipeline")
    p_run.add_argument("task", help="Task description")
    p_run.add_argument("--project", help="Project ID")
    p_run.add_argument("--stages", nargs="+", help="Specific stages to run")
    p_run.add_argument("--dry-run", action="store_true", help="Show plan without executing")
    
    p_status = sub.add_parser("status", help="Get project status")
    p_status.add_argument("--project", required=True, help="Project ID")
    
    p_cost = sub.add_parser("cost", help="Cost report")
    p_cost.add_argument("--project", help="Project ID (all if omitted)")
    
    p_cache = sub.add_parser("cache", help="Cache statistics")
    
    args = parser.parse_args()
    pipeline = NexDevPipeline()
    
    if args.command == "run":
        result = pipeline.run(args.task, project_id=args.project, 
                            stages=args.stages, dry_run=args.dry_run)
        print(f"\n{'='*60}")
        print(f"Pipeline {'plan' if args.dry_run else 'complete'}: {result['project_id']}")
        print(f"Total Cost: ${result.get('total_cost', 0):.6f}")
    elif args.command == "status":
        print(json.dumps(pipeline.status(args.project), indent=2))
    elif args.command == "cost":
        print(pipeline.cost_report(args.project))
    elif args.command == "cache":
        print(json.dumps(pipeline.cache.stats(), indent=2))
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
