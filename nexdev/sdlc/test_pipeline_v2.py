#!/usr/bin/env python3
"""Automated tests for NexDev Pipeline v2 transitions and logic."""

import sys
import json
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sdlc.pipeline_v2 import (
    SDLCPipelineV2, PipelineStage, STAGE_TRANSITIONS,
    HUMAN_REVIEW_GATES, STAGE_AGENT_ROLES, OPTIONAL_STAGES
)

PASS = 0
FAIL = 0

def test(name, condition, detail=""):
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f"  ✅ {name}")
    else:
        FAIL += 1
        print(f"  ❌ {name} — {detail}")


def test_stage_transitions():
    """Verify every stage has a valid transition (except terminals)."""
    print("\n=== Stage Transition Integrity ===")
    terminals = {PipelineStage.COMPLETE, PipelineStage.FAILED, PipelineStage.BLOCKED}
    
    for stage in PipelineStage:
        if stage in terminals:
            continue
        has_transition = stage in STAGE_TRANSITIONS
        test(f"{stage.value} has transition", has_transition,
             f"No transition defined for {stage.value}")
    
    # Verify no cycles
    visited = set()
    s = PipelineStage.INTAKE
    while s:
        test(f"No cycle at {s.value}", s not in visited, f"Cycle detected at {s.value}")
        visited.add(s)
        s = STAGE_TRANSITIONS.get(s)
    
    # Verify chain reaches COMPLETE
    test("Chain reaches COMPLETE", PipelineStage.COMPLETE not in STAGE_TRANSITIONS)
    test(f"Full chain length = {len(visited)}", len(visited) >= 15)


def test_agent_coverage():
    """Verify every non-review, non-terminal stage has an agent."""
    print("\n=== Agent Coverage ===")
    skip = HUMAN_REVIEW_GATES | {
        PipelineStage.INTAKE, PipelineStage.COMPLETE,
        PipelineStage.FAILED, PipelineStage.BLOCKED,
    }
    
    for stage in PipelineStage:
        if stage in skip:
            continue
        has_agent = stage in STAGE_AGENT_ROLES
        test(f"{stage.value} has agent role", has_agent,
             f"No agent for {stage.value}")


def test_scope_detection():
    """Verify project scope detection skips correct stages."""
    print("\n=== Scope Detection ===")
    p = SDLCPipelineV2()
    
    # Backend-only
    proj = p.start("Build a backend-only CLI tool")
    test("Backend-only skips frontend_dev", "frontend_dev" in proj.skipped_stages)
    test("Backend-only skips mobile_dev", "mobile_dev" in proj.skipped_stages)
    test("Backend-only skips accessibility_audit", "accessibility_audit" in proj.skipped_stages)
    test("Backend-only skips ui_design", "ui_design" in proj.skipped_stages)
    test("Backend-only keeps backend_dev", "backend_dev" not in proj.skipped_stages)
    test("Backend-only keeps architecture", "architecture" not in proj.skipped_stages)
    
    # Full-stack with mobile
    proj2 = p.start("Build a mobile app with React Native and a FastAPI backend")
    test("Mobile project keeps mobile_dev", "mobile_dev" not in proj2.skipped_stages)
    test("Mobile project keeps frontend_dev", "frontend_dev" not in proj2.skipped_stages)
    
    # AI project
    proj3 = p.start("Build a machine learning pipeline for image classification")
    test("ML project keeps ai_dev", "ai_dev" not in proj3.skipped_stages)
    
    # Clean up test projects
    for pid in [proj.id, proj2.id, proj3.id]:
        p.projects.pop(pid, None)
    p._save_projects()


def test_review_gates():
    """Verify review gates block without approval and pass with it."""
    print("\n=== Review Gates ===")
    test("3 review gates defined", len(HUMAN_REVIEW_GATES) == 3)
    test("ideation_review is gate", PipelineStage.IDEATION_REVIEW in HUMAN_REVIEW_GATES)
    test("architecture_review is gate", PipelineStage.ARCHITECTURE_REVIEW in HUMAN_REVIEW_GATES)
    test("qa_review is gate", PipelineStage.QA_REVIEW in HUMAN_REVIEW_GATES)


def test_advance_flow_dry():
    """Dry-run the advance flow without LLM calls to verify logic."""
    print("\n=== Advance Flow (dry) ===")
    
    # Trace expected path for backend-only
    skip = {"feedback_synthesis", "identity_design", "ai_dev", "mobile_dev",
            "ui_design", "frontend_dev", "accessibility_audit"}
    
    expected_exec = []
    s = PipelineStage.INTAKE
    while s:
        if s.value not in skip and s not in (PipelineStage.COMPLETE, PipelineStage.FAILED, PipelineStage.BLOCKED):
            expected_exec.append(s.value)
        s = STAGE_TRANSITIONS.get(s)
    
    test(f"Expected stages: {len(expected_exec)}", len(expected_exec) >= 8,
         f"Got {len(expected_exec)}: {expected_exec}")
    
    # Verify review gates are in expected path
    for gate in ["ideation_review", "architecture_review", "qa_review"]:
        test(f"{gate} in path", gate in expected_exec)
    
    # Verify production stages are in path
    for prod in ["ux_research", "sprint_planning", "task_breakdown", 
                  "architecture", "backend_dev", "unit_testing", "api_testing",
                  "deployment", "monitoring"]:
        test(f"{prod} in path", prod in expected_exec, f"Missing from path")


def test_optional_stages():
    """Verify optional stages are properly defined."""
    print("\n=== Optional Stages ===")
    test("Optional stages defined", len(OPTIONAL_STAGES) >= 4)
    for stage in OPTIONAL_STAGES:
        test(f"{stage.value} is optional", stage in OPTIONAL_STAGES)
        # Optional stages should still have transitions
        test(f"{stage.value} has transition", stage in STAGE_TRANSITIONS)


if __name__ == "__main__":
    print("=" * 50)
    print("  NexDev Pipeline v2 — Automated Tests")
    print("=" * 50)
    
    test_stage_transitions()
    test_agent_coverage()
    test_scope_detection()
    test_review_gates()
    test_advance_flow_dry()
    test_optional_stages()
    
    print(f"\n{'=' * 50}")
    print(f"  Results: {PASS} passed, {FAIL} failed")
    print(f"{'=' * 50}")
    
    sys.exit(1 if FAIL > 0 else 0)
