#!/usr/bin/env python3
"""
NexDev SDLC Pipeline v2.0 - Full Agent Integration
===================================================
6-stage pipeline with 22 specialized agents:
  1. Ideation (Feedback, UX, Sprint, PM)
  2. Architecture (Legal, Architect, Identity, UI Designer)
  3. Development (Backend, Frontend, Mobile, AI, Rapid Prototyper)
  4. Testing (Unit/Integration, API, Accessibility)
  5. QA & Deploy (QA analysis, deployment)
  6. Monitoring (Analytics, feedback loop)
"""

import json
import time
from enum import Enum
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional

from .agent_engine import create_agent, get_system_prompt, AgentLLM
from .contracts import ArtifactStore, AgentRole


class PipelineStage(Enum):
    # Stage 1: Ideation
    INTAKE = "intake"
    FEEDBACK_SYNTHESIS = "feedback_synthesis"
    UX_RESEARCH = "ux_research"
    SPRINT_PLANNING = "sprint_planning"
    TASK_BREAKDOWN = "task_breakdown"
    IDEATION_REVIEW = "ideation_review"

    # Stage 2: Architecture
    # LEGAL_PRECHECK removed from pipeline flow
    ARCHITECTURE = "architecture"
    IDENTITY_DESIGN = "identity_design"
    UI_DESIGN = "ui_design"
    ARCHITECTURE_REVIEW = "architecture_review"

    # Stage 3: Development
    BACKEND_DEV = "backend_dev"
    FRONTEND_DEV = "frontend_dev"
    MOBILE_DEV = "mobile_dev"
    AI_DEV = "ai_dev"

    # Stage 4: Testing
    UNIT_TESTING = "unit_testing"
    API_TESTING = "api_testing"
    ACCESSIBILITY_AUDIT = "accessibility_audit"

    # Stage 5: QA & Deploy
    QA_REVIEW = "qa_review"
    DEPLOYMENT = "deployment"

    # Stage 6: Monitoring
    MONITORING = "monitoring"

    # Terminal states
    COMPLETE = "complete"
    FAILED = "failed"
    BLOCKED = "blocked"


# Linear pipeline flow
STAGE_TRANSITIONS = {
    PipelineStage.INTAKE: PipelineStage.FEEDBACK_SYNTHESIS,
    PipelineStage.FEEDBACK_SYNTHESIS: PipelineStage.UX_RESEARCH,
    PipelineStage.UX_RESEARCH: PipelineStage.SPRINT_PLANNING,
    PipelineStage.SPRINT_PLANNING: PipelineStage.TASK_BREAKDOWN,
    PipelineStage.TASK_BREAKDOWN: PipelineStage.IDEATION_REVIEW,
    PipelineStage.IDEATION_REVIEW: PipelineStage.ARCHITECTURE,
    PipelineStage.ARCHITECTURE: PipelineStage.IDENTITY_DESIGN,
    PipelineStage.IDENTITY_DESIGN: PipelineStage.UI_DESIGN,
    PipelineStage.UI_DESIGN: PipelineStage.ARCHITECTURE_REVIEW,
    PipelineStage.ARCHITECTURE_REVIEW: PipelineStage.BACKEND_DEV,
    PipelineStage.BACKEND_DEV: PipelineStage.FRONTEND_DEV,
    PipelineStage.FRONTEND_DEV: PipelineStage.MOBILE_DEV,
    PipelineStage.MOBILE_DEV: PipelineStage.AI_DEV,
    PipelineStage.AI_DEV: PipelineStage.UNIT_TESTING,
    PipelineStage.UNIT_TESTING: PipelineStage.API_TESTING,
    PipelineStage.API_TESTING: PipelineStage.ACCESSIBILITY_AUDIT,
    PipelineStage.ACCESSIBILITY_AUDIT: PipelineStage.QA_REVIEW,
    PipelineStage.QA_REVIEW: PipelineStage.DEPLOYMENT,
    PipelineStage.DEPLOYMENT: PipelineStage.MONITORING,
    PipelineStage.MONITORING: PipelineStage.COMPLETE,
}

HUMAN_REVIEW_GATES = {
    PipelineStage.IDEATION_REVIEW,
    PipelineStage.ARCHITECTURE_REVIEW,
    PipelineStage.QA_REVIEW,
}

# Agent mapping per stage
STAGE_AGENT_ROLES = {
    PipelineStage.FEEDBACK_SYNTHESIS: "feedback_synthesizer",
    PipelineStage.UX_RESEARCH: "ux_researcher",
    PipelineStage.SPRINT_PLANNING: "sprint_prioritizer",
    PipelineStage.TASK_BREAKDOWN: "senior_project_manager",
    PipelineStage.ARCHITECTURE: "architect",
    PipelineStage.IDENTITY_DESIGN: "identity_trust_architect",
    PipelineStage.UI_DESIGN: "ui_designer",
    PipelineStage.BACKEND_DEV: "developer",
    PipelineStage.FRONTEND_DEV: "frontend_developer",
    PipelineStage.MOBILE_DEV: "mobile_developer",
    PipelineStage.AI_DEV: "ai_engineer",
    PipelineStage.UNIT_TESTING: "test_engineer",
    PipelineStage.API_TESTING: "api_tester",
    PipelineStage.ACCESSIBILITY_AUDIT: "accessibility_auditor",
    PipelineStage.QA_REVIEW: "qa_engineer",
    PipelineStage.DEPLOYMENT: "devops",
    PipelineStage.MONITORING: "analytics_reporter",
}

# Stages that can be skipped if not relevant to the project
OPTIONAL_STAGES = {
    PipelineStage.FEEDBACK_SYNTHESIS,  # Skip if no existing feedback
    PipelineStage.MOBILE_DEV,          # Skip if no mobile requirement
    PipelineStage.AI_DEV,              # Skip if no ML requirement
    PipelineStage.IDENTITY_DESIGN,     # Skip if no multi-agent auth needed
    PipelineStage.ACCESSIBILITY_AUDIT, # Skip if backend-only
}


class ProjectV2:
    """Project state for v2 pipeline."""

    def __init__(self, project_id: str, raw_request: str, config: Dict = None):
        self.id = project_id
        self.raw_request = raw_request
        self.config = config or {}
        self.current_stage = PipelineStage.INTAKE.value
        self.events = []
        self.artifacts = {}  # stage_name -> artifact data
        self.model_used = {}
        self.total_cost = 0.0
        self.skipped_stages = set()
        self.created_at = datetime.now().isoformat()
        self.review_gates = {}
        self.error = None
        # Detect which optional stages to skip
        self._detect_scope()

    def _detect_scope(self):
        """Detect which stages to skip based on the request."""
        req = self.raw_request.lower().replace("-", " ")

        # Skip mobile if not mentioned
        if not any(w in req for w in ["mobile", "app", "ios", "android", "react native", "flutter"]):
            self.skipped_stages.add(PipelineStage.MOBILE_DEV.value)

        # Skip AI if not mentioned
        if not any(w in req for w in ["ml", "ai", "machine learning", "model", "training", "neural"]):
            self.skipped_stages.add(PipelineStage.AI_DEV.value)

        # Skip identity if not multi-agent
        if not any(w in req for w in ["agent", "multi-agent", "identity", "trust", "rbac"]):
            self.skipped_stages.add(PipelineStage.IDENTITY_DESIGN.value)

        # Skip frontend if backend-only
        if any(w in req for w in ["api only", "backend only", "no ui", "cli", "command line"]):
            self.skipped_stages.add(PipelineStage.FRONTEND_DEV.value)
            self.skipped_stages.add(PipelineStage.ACCESSIBILITY_AUDIT.value)
            self.skipped_stages.add(PipelineStage.UI_DESIGN.value)
            self.skipped_stages.add(PipelineStage.MOBILE_DEV.value)

        # Skip feedback synthesis if new project (no existing feedback)
        if not self.config.get("existing_feedback"):
            self.skipped_stages.add(PipelineStage.FEEDBACK_SYNTHESIS.value)

    def add_event(self, stage, action, agent, message, **kwargs):
        self.events.append({
            "stage": stage, "action": action, "agent": agent,
            "message": message, "timestamp": datetime.now().isoformat(),
            **kwargs,
        })

    def to_dict(self):
        return {
            "id": self.id, "raw_request": self.raw_request,
            "current_stage": self.current_stage, "events": self.events,
            "artifacts": {k: "..." for k in self.artifacts},
            "model_used": self.model_used, "total_cost": self.total_cost,
            "skipped_stages": list(self.skipped_stages),
            "review_gates": self.review_gates,
            "created_at": self.created_at,
        }


class SDLCPipelineV2:
    """Full 6-stage SDLC pipeline with 22 agents."""

    MAX_FIX_ROUNDS = 3

    def __init__(self, parallel_mode: bool = False):
        self.parallel_mode = parallel_mode
        self.store = ArtifactStore()
        self.projects: Dict[str, ProjectV2] = {}
        self.db_path = Path.home() / ".openclaw" / "workspace" / "nexdev" / "projects" / "pipeline_v2.json"
        self._load_projects()

    def _load_projects(self):
        if self.db_path.exists():
            try:
                with open(self.db_path) as f:
                    data = json.load(f)
                for pid, pdata in data.items():
                    proj = ProjectV2(pid, pdata.get("raw_request", ""))
                    proj.current_stage = pdata.get("current_stage", "intake")
                    proj.events = pdata.get("events", [])
                    proj.model_used = pdata.get("model_used", {})
                    proj.total_cost = pdata.get("total_cost", 0)
                    proj.skipped_stages = set(pdata.get("skipped_stages", []))
                    proj.review_gates = pdata.get("review_gates", {})
                    self.projects[pid] = proj
            except Exception:
                pass

    def _save_projects(self):
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        data = {pid: p.to_dict() for pid, p in self.projects.items()}
        with open(self.db_path, "w") as f:
            json.dump(data, f, indent=2, default=str)

    def start(self, request: str, config: Dict = None) -> ProjectV2:
        """Start a new project."""
        pid = f"V2-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        project = ProjectV2(pid, request, config)
        project.add_event("intake", "created", "pipeline", f"Project created: {request[:80]}")
        self.projects[pid] = project
        self._save_projects()
        return project

    def advance(self, project_id: str, approval: str = None, notes: str = "") -> ProjectV2:
        """Advance to next stage."""
        project = self.projects.get(project_id)
        if not project:
            raise ValueError(f"Project {project_id} not found")

        current = PipelineStage(project.current_stage)

        # Handle blocked state
        if current == PipelineStage.BLOCKED and approval:
            for gate in [PipelineStage.IDEATION_REVIEW, PipelineStage.ARCHITECTURE_REVIEW, PipelineStage.QA_REVIEW]:
                gate_data = project.review_gates.get(gate.value, {})
                if gate_data.get("status") == "pending":
                    current = gate
                    project.current_stage = gate.value
                    break

        # Handle review gates
        if current in HUMAN_REVIEW_GATES:
            return self._handle_review(project, current, approval, notes)

        # Get next stage (skip optional stages not in scope)
        next_stage = STAGE_TRANSITIONS.get(current)
        while next_stage and next_stage.value in project.skipped_stages:
            project.add_event(next_stage.value, "skipped", "pipeline",
                            f"Skipped (not in scope)")
            next_stage = STAGE_TRANSITIONS.get(next_stage)

        if not next_stage:
            return project

        if next_stage in HUMAN_REVIEW_GATES:
            project.current_stage = next_stage.value
            if not approval:
                project.review_gates[next_stage.value] = {"status": "pending"}
                project.add_event(next_stage.value, "awaiting_review", "pipeline", "Awaiting approval")
                self._save_projects()
                return project
            return self._handle_review(project, next_stage, approval, notes)

        # Execute the stage
        self._run_stage(project, next_stage)

        # Auto-advance through any following skippable or production stages
        after = STAGE_TRANSITIONS.get(next_stage)
        while after and after.value in project.skipped_stages:
            project.add_event(after.value, "skipped", "pipeline", "Skipped (not in scope)")
            after = STAGE_TRANSITIONS.get(after)

        if after:
            project.current_stage = after.value
            # If next is a production stage (not review), execute it too
            if after not in HUMAN_REVIEW_GATES and after not in (PipelineStage.COMPLETE, PipelineStage.FAILED):
                self._save_projects()
                return self.advance(project_id)

        self._save_projects()
        return project

    def _handle_review(self, project, stage, approval, notes):
        """Handle review gate."""
        if not approval:
            project.current_stage = PipelineStage.BLOCKED.value
            project.review_gates[stage.value] = {"status": "pending"}
            project.add_event(stage.value, "blocked", "pipeline", "Awaiting review")
            self._save_projects()
            return project

        if approval == "approve":
            project.review_gates[stage.value] = {
                "status": "approved", "timestamp": datetime.now().isoformat(), "notes": notes,
            }
            project.add_event(stage.value, "approved", "human", f"Approved: {notes or 'OK'}")

            # Advance past the gate
            next_stage = STAGE_TRANSITIONS.get(stage)
            while next_stage and next_stage.value in project.skipped_stages:
                project.add_event(next_stage.value, "skipped", "pipeline", "Skipped")
                next_stage = STAGE_TRANSITIONS.get(next_stage)

            if next_stage:
                if next_stage not in HUMAN_REVIEW_GATES:
                    # Execute the production stage directly
                    self._run_stage(project, next_stage)
                    # Then set current to the stage AFTER
                    after = STAGE_TRANSITIONS.get(next_stage)
                    while after and after.value in project.skipped_stages:
                        project.add_event(after.value, "skipped", "pipeline", "Skipped")
                        after = STAGE_TRANSITIONS.get(after)
                    project.current_stage = after.value if after else PipelineStage.COMPLETE.value
                else:
                    project.current_stage = next_stage.value
                self._save_projects()
                return project

        elif approval == "reject":
            project.review_gates[stage.value] = {"status": "rejected", "notes": notes}
            project.add_event(stage.value, "rejected", "human", f"Rejected: {notes}")
            # Roll back to previous non-review stage
            rollback = {
                PipelineStage.IDEATION_REVIEW: PipelineStage.INTAKE,
                PipelineStage.ARCHITECTURE_REVIEW: PipelineStage.LEGAL_PRECHECK,
                PipelineStage.QA_REVIEW: PipelineStage.BACKEND_DEV,
            }
            project.current_stage = rollback.get(stage, PipelineStage.INTAKE).value

        self._save_projects()
        return project

    def _run_stage(self, project, stage):
        """Execute a single pipeline stage via LLM."""
        role = STAGE_AGENT_ROLES.get(stage)
        if not role:
            return

        agent = create_agent(role, project.id)
        sys_prompt = get_system_prompt(role)

        project.add_event(stage.value, "started", role, f"Starting {stage.value}")
        start = time.time()

        # Build context from previous artifacts
        context = self._build_context(project, stage)
        prompt = self._build_prompt(project, stage, context)

        try:
            result = agent.ask_json(prompt, sys_prompt)
            duration = (time.time() - start) * 1000

            if "data" in result:
                # Store artifact
                project.artifacts[stage.value] = result["data"]
                self.store.save_artifact(project.id, stage.value, "1", result["data"])
                project.total_cost += result.get("cost", 0)
                project.model_used[stage.value] = result.get("model", "unknown")
                project.add_event(stage.value, "completed", role,
                                f"Completed in {duration:.0f}ms", duration_ms=duration)
            else:
                project.add_event(stage.value, "llm_parse_fail", role,
                                f"LLM returned non-JSON: {result.get('error', '?')[:80]}")
                # Store raw text as artifact anyway
                project.artifacts[stage.value] = {"raw": result.get("raw_text", ""), "error": result.get("error", "")}
                self.store.save_artifact(project.id, stage.value, "1", project.artifacts[stage.value])

        except Exception as e:
            project.add_event(stage.value, "error", role, f"Error: {str(e)[:100]}")
            project.artifacts[stage.value] = {"error": str(e)}

        project.current_stage = stage.value

    def _build_context(self, project, stage) -> str:
        """Build optimized context from previous stage artifacts.
        
        Cost optimization: Only include artifacts directly relevant to 
        the current stage, and compress them to essential fields.
        """
        # Define which stages each agent needs context from
        context_deps = {
            PipelineStage.UX_RESEARCH: [],  # Works from raw request only
            PipelineStage.SPRINT_PLANNING: ["ux_research"],
            PipelineStage.TASK_BREAKDOWN: ["sprint_planning"],
            PipelineStage.ARCHITECTURE: ["task_breakdown"],
            PipelineStage.IDENTITY_DESIGN: ["architecture"],
            PipelineStage.UI_DESIGN: ["architecture"],
            PipelineStage.BACKEND_DEV: ["architecture", "task_breakdown"],
            PipelineStage.FRONTEND_DEV: ["ui_design", "backend_dev"],
            PipelineStage.MOBILE_DEV: ["ui_design", "backend_dev"],
            PipelineStage.AI_DEV: ["architecture", "backend_dev"],
            PipelineStage.UNIT_TESTING: ["backend_dev", "frontend_dev"],
            PipelineStage.API_TESTING: ["backend_dev", "architecture"],
            PipelineStage.ACCESSIBILITY_AUDIT: ["frontend_dev", "ui_design"],
            PipelineStage.QA_REVIEW: ["unit_testing", "api_testing", "accessibility_audit"],
            PipelineStage.DEPLOYMENT: ["backend_dev", "frontend_dev", "architecture"],
            PipelineStage.MONITORING: ["deployment", "architecture"],
        }
        
        deps = context_deps.get(stage, [])
        relevant = []
        
        for dep_name in deps:
            if dep_name in project.artifacts:
                data = project.artifacts[dep_name]
                if isinstance(data, dict) and "error" not in data:
                    text = json.dumps(data, indent=2)
                    # Aggressive truncation for cost savings
                    max_len = 2000 if dep_name in ("backend_dev", "frontend_dev") else 1500
                    if len(text) > max_len:
                        text = text[:max_len] + "\n... (truncated)"
                    relevant.append(f"[{dep_name}]:\n{text}")
        
        return "\n\n".join(relevant)

    def _build_prompt(self, project, stage, context) -> str:
        """Build the prompt for a stage."""
        base = f"Project: {project.raw_request}\n\n"
        if context:
            base += f"Previous stage outputs:\n{context}\n\n"

        stage_instructions = {
            PipelineStage.FEEDBACK_SYNTHESIS: "Synthesize user feedback and extract priorities.",
            PipelineStage.UX_RESEARCH: "Validate user stories, create personas and journey maps.",
            PipelineStage.SPRINT_PLANNING: "Prioritize the backlog and create a sprint plan.",
            PipelineStage.TASK_BREAKDOWN: "Break down into granular tasks with time estimates.",
            PipelineStage.ARCHITECTURE: "Design the system architecture, database schema, and API contracts.",
            PipelineStage.IDENTITY_DESIGN: "Design agent authentication and audit trail systems.",
            PipelineStage.UI_DESIGN: "Create design system specs, component library, and style tokens.",
            PipelineStage.BACKEND_DEV: "Generate production-ready backend code based on the architecture.",
            PipelineStage.FRONTEND_DEV: "Generate frontend React/Vue components based on UI design and API specs.",
            PipelineStage.MOBILE_DEV: "Generate React Native/Flutter mobile app code.",
            PipelineStage.AI_DEV: "Scaffold ML pipelines and model integration code.",
            PipelineStage.UNIT_TESTING: "Generate comprehensive unit and integration tests for all code.",
            PipelineStage.API_TESTING: "Generate HTTP endpoint test suites for all API routes.",
            PipelineStage.ACCESSIBILITY_AUDIT: "Audit all frontend code for WCAG 2.2 AA compliance.",
            PipelineStage.QA_REVIEW: "Analyze all test results and provide final QA assessment.",
            PipelineStage.DEPLOYMENT: "Generate deployment configuration (Docker, CI/CD, env vars).",
            PipelineStage.MONITORING: "Generate analytics dashboard specs and monitoring config.",
        }

        instruction = stage_instructions.get(stage, f"Execute {stage.value} stage.")
        return base + instruction

    def status(self, project_id: str) -> Dict:
        """Get project status."""
        project = self.projects.get(project_id)
        if not project:
            return {"error": "Not found"}

        stages_completed = [e["stage"] for e in project.events if e["action"] == "completed"]
        stages_skipped = list(project.skipped_stages)

        return {
            "id": project.id,
            "request": project.raw_request[:80],
            "current_stage": project.current_stage,
            "completed_stages": stages_completed,
            "skipped_stages": stages_skipped,
            "total_cost": round(project.total_cost, 4),
            "models_used": project.model_used,
            "artifacts": list(project.artifacts.keys()),
            "events_count": len(project.events),
        }



    def advance_parallel(self, project_id: str, group: str = None) -> "ProjectV2":
        """Advance using parallel execution for development/testing stages.
        
        Args:
            project_id: Project to advance
            group: 'development' or 'testing' to run that group in parallel
        """
        from .multi_agent import ParallelStageRunner
        runner = ParallelStageRunner(self)
        
        project = self.projects.get(project_id)
        if not project:
            raise ValueError(f"Project {project_id} not found")
        
        if group:
            result = runner.run_group_parallel(project_id, group)
            project.add_event(group, "parallel_complete", "swarm",
                            f"Parallel {group}: {result.get('stages_run', 0)} stages, "
                            f"{result.get('elapsed', 0)}s, ${result.get('cost', 0):.4f}")
            
            # Advance current_stage past the parallel group
            from .pipeline_v2 import PipelineStage, STAGE_TRANSITIONS
            parallel_groups = {
                "development": PipelineStage.AI_DEV,     # Last dev stage
                "testing": PipelineStage.ACCESSIBILITY_AUDIT,  # Last test stage
            }
            last_stage = parallel_groups.get(group)
            if last_stage:
                after = STAGE_TRANSITIONS.get(last_stage)
                while after and after.value in project.skipped_stages:
                    after = STAGE_TRANSITIONS.get(after)
                project.current_stage = after.value if after else PipelineStage.COMPLETE.value
            
            self._save_projects()
        
        return project

    def create_feedback_loop(self, project_id: str) -> "ProjectV2":
        """Create a new iteration from monitoring insights.
        
        Takes the monitoring/analytics output from a completed project
        and feeds it into a new ideation cycle as existing_feedback.
        This implements the monitoring → ideation feedback loop.
        """
        old_project = self.projects.get(project_id)
        if not old_project:
            raise ValueError(f"Project {project_id} not found")
        
        if old_project.current_stage != PipelineStage.COMPLETE.value:
            raise ValueError("Can only create feedback loop from completed projects")
        
        # Extract monitoring insights as feedback for next iteration
        monitoring_data = old_project.artifacts.get("monitoring", {})
        qa_data = old_project.artifacts.get("qa_review", {})
        
        feedback = {
            "source_project": project_id,
            "monitoring_insights": monitoring_data,
            "qa_findings": qa_data,
            "iteration": old_project.config.get("iteration", 0) + 1,
        }
        
        # Start new project with feedback context
        new_request = f"[Iteration {feedback['iteration']}] {old_project.raw_request}"
        new_project = self.start(new_request, config={
            "existing_feedback": feedback,
            "parent_project": project_id,
            "iteration": feedback["iteration"],
        })
        
        # Since we have existing_feedback, feedback_synthesis won't be skipped
        new_project.skipped_stages.discard("feedback_synthesis")
        new_project.add_event("intake", "feedback_loop", "pipeline",
                            f"Feedback loop from {project_id} (iteration {feedback['iteration']})")
        
        self._save_projects()
        return new_project
    
    def get_iteration_history(self, project_id: str) -> list:
        """Get the full iteration chain for a project."""
        chain = []
        current = project_id
        while current:
            proj = self.projects.get(current)
            if not proj:
                break
            chain.append({
                "id": current,
                "iteration": proj.config.get("iteration", 0),
                "stage": proj.current_stage,
                "cost": proj.total_cost,
            })
            current = proj.config.get("parent_project")
        return list(reversed(chain))

    def list_projects(self):
        return [self.status(pid) for pid in self.projects]
