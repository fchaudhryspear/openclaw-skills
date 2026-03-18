#!/usr/bin/env python3
"""NexDev - Multi-Agent Coordinator
Enables parallel execution of independent stages and agent swarm coordination."""

import json
import time
import concurrent.futures
from typing import Dict, List, Callable, Optional
from datetime import datetime
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from sdlc.agent_engine import create_agent, get_system_prompt


class AgentSwarm:
    """Coordinates multiple agents working on related tasks in parallel."""

    def __init__(self, max_workers: int = 3):
        self.max_workers = max_workers
        self.results = {}
        self.total_cost = 0.0
        self.execution_log = []

    def run_parallel(self, tasks: List[Dict]) -> Dict:
        """Run multiple agent tasks in parallel.

        Each task: {role, prompt, system_prompt (optional), project_id}
        Returns: {task_id: result}
        """
        start = time.time()

        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {}
            for i, task in enumerate(tasks):
                task_id = task.get("id", f"task_{i}")
                future = executor.submit(self._execute_task, task)
                futures[future] = task_id

            for future in concurrent.futures.as_completed(futures):
                task_id = futures[future]
                try:
                    result = future.result(timeout=120)
                    self.results[task_id] = result
                    self.total_cost += result.get("cost", 0)
                    self.execution_log.append({
                        "task_id": task_id,
                        "status": "success" if result.get("success") else "failed",
                        "model": result.get("model", "unknown"),
                        "cost": result.get("cost", 0),
                    })
                except Exception as e:
                    self.results[task_id] = {"error": str(e), "success": False}
                    self.execution_log.append({
                        "task_id": task_id, "status": "error", "error": str(e),
                    })

        elapsed = time.time() - start
        return {
            "results": self.results,
            "total_cost": self.total_cost,
            "elapsed_seconds": round(elapsed, 1),
            "tasks_completed": len(self.results),
            "tasks_failed": sum(1 for r in self.results.values() 
                              if not r.get("success", True) or "error" in r),
        }

    def _execute_task(self, task: Dict) -> Dict:
        """Execute a single agent task."""
        role = task["role"]
        prompt = task["prompt"]
        sys_prompt = task.get("system_prompt", get_system_prompt(role))
        project_id = task.get("project_id")

        agent = create_agent(role, project_id)

        if task.get("json_output", True):
            result = agent.ask_json(prompt, sys_prompt)
            return {
                "data": result.get("data"),
                "model": result.get("model", "unknown"),
                "cost": result.get("cost", 0),
                "success": bool(result.get("data")),
                "error": result.get("error"),
            }
        else:
            result = agent.ask(prompt, sys_prompt)
            return {
                "text": result.get("text", ""),
                "model": result.get("model", "unknown"),
                "cost": result.get("cost_usd", 0),
                "success": result.get("success", False),
            }


class ParallelStageRunner:
    """Identifies and runs independent pipeline stages in parallel."""

    # Stages that can run in parallel (no dependencies between them)
    PARALLEL_GROUPS = {
        "development": ["backend_dev", "frontend_dev", "mobile_dev", "ai_dev"],
        "testing": ["unit_testing", "api_testing", "accessibility_audit"],
    }

    def __init__(self, pipeline):
        self.pipeline = pipeline

    def can_parallelize(self, stages: List[str]) -> Optional[str]:
        """Check if a set of upcoming stages can be parallelized."""
        for group_name, group_stages in self.PARALLEL_GROUPS.items():
            if any(s in group_stages for s in stages):
                return group_name
        return None

    def run_group_parallel(self, project_id: str, group_name: str) -> Dict:
        """Run a parallel group of stages."""
        project = self.pipeline.projects.get(project_id)
        if not project:
            raise ValueError(f"Project {project_id} not found")

        group_stages = self.PARALLEL_GROUPS.get(group_name, [])
        # Filter to stages not skipped
        active_stages = [s for s in group_stages if s not in project.skipped_stages]

        if not active_stages:
            return {"skipped": True, "reason": "All stages in group are skipped"}

        # Build tasks for each stage
        from sdlc.pipeline_v2 import STAGE_AGENT_ROLES, PipelineStage

        tasks = []
        for stage_name in active_stages:
            try:
                stage = PipelineStage(stage_name)
            except ValueError:
                continue
            role = STAGE_AGENT_ROLES.get(stage)
            if not role:
                continue

            context = self.pipeline._build_context(project, stage)
            prompt = self.pipeline._build_prompt(project, stage, context)

            tasks.append({
                "id": stage_name,
                "role": role,
                "prompt": prompt,
                "project_id": project_id,
            })

        if not tasks:
            return {"skipped": True, "reason": "No executable tasks"}

        # Run in parallel
        swarm = AgentSwarm(max_workers=min(len(tasks), 3))
        result = swarm.run_parallel(tasks)

        # Store results as artifacts
        for task_id, task_result in result["results"].items():
            if task_result.get("data"):
                project.artifacts[task_id] = task_result["data"]
                self.pipeline.store.save_artifact(project.id, task_id, "1", task_result["data"])
                project.model_used[task_id] = task_result.get("model", "unknown")
            project.add_event(task_id, 
                            "completed" if task_result.get("success") else "error",
                            STAGE_AGENT_ROLES.get(PipelineStage(task_id), "unknown"),
                            f"Parallel: {task_result.get('model', '?')}")

        project.total_cost += result["total_cost"]
        self.pipeline._save_projects()

        return {
            "group": group_name,
            "stages_run": len(tasks),
            "elapsed": result["elapsed_seconds"],
            "cost": result["total_cost"],
            "failed": result["tasks_failed"],
        }


class ReviewCoordinator:
    """Coordinates multi-agent review sessions for quality gates."""

    def __init__(self):
        self.reviewers = {
            "code_quality": "qa_engineer",
            "security": "security",
            "architecture": "architect",
        }

    def multi_review(self, code: str, project_id: str = None) -> Dict:
        """Run multiple review agents in parallel on the same code."""
        tasks = []
        for review_type, role in self.reviewers.items():
            tasks.append({
                "id": f"review_{review_type}",
                "role": role,
                "prompt": f"Review this code for {review_type} concerns:\n\n{code[:6000]}",
                "project_id": project_id,
            })

        swarm = AgentSwarm(max_workers=3)
        result = swarm.run_parallel(tasks)

        # Merge reviews
        merged = {
            "reviews": {},
            "total_cost": result["total_cost"],
            "elapsed": result["elapsed_seconds"],
        }
        for task_id, task_result in result["results"].items():
            review_type = task_id.replace("review_", "")
            merged["reviews"][review_type] = task_result.get("data") or task_result.get("text", "")

        return merged


if __name__ == "__main__":
    # Quick test of AgentSwarm
    swarm = AgentSwarm(max_workers=2)
    result = swarm.run_parallel([
        {"id": "test1", "role": "rapid_prototyper", 
         "prompt": "Generate a hello world Flask app", "json_output": False},
        {"id": "test2", "role": "sprint_prioritizer",
         "prompt": "Prioritize: fix bug, add feature, refactor code", "json_output": False},
    ])
    print(f"Parallel test: {result['tasks_completed']} tasks in {result['elapsed_seconds']}s")
    print(f"Cost: ${result['total_cost']:.5f}")
    print(f"Failed: {result['tasks_failed']}")
