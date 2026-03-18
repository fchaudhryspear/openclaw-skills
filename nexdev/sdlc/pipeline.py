#!/usr/bin/env python3
"""
NexDev Phase 2A.1 — Multi-Agent SDLC Pipeline Orchestrator
============================================================
Core handoff engine that manages the PM → Architect → Developer → QA pipeline.
Each step produces versioned artifacts. Human review gates at key transitions.

Usage:
    from nexdev.sdlc.pipeline import SDLCPipeline
    pipeline = SDLCPipeline()
    project = pipeline.start("Build a SaaS property management platform...")
    pipeline.advance(project.id)  # PM → Architect
    pipeline.advance(project.id)  # Architect → Developer
    pipeline.advance(project.id)  # Developer → QA
"""

import json
import time
from pathlib import Path
from typing import Dict, List, Optional, Callable
from datetime import datetime
from enum import Enum
from dataclasses import dataclass, field, asdict

from .contracts import (
    AgentRole, ArtifactStatus, ArtifactStore,
    SpecificationDocument, ArchitectureDesign, Implementation, QAReport
)
from .pm_agent import PMAgent
from .architect_agent import ArchitectAgent
from .test_gen_agent import TestGenAgent
from .qa_agent import QAEngineer


class PipelineStage(Enum):
    INTAKE = "intake"                # Raw request received
    REQUIREMENTS = "requirements"     # PM producing spec
    REQUIREMENTS_REVIEW = "requirements_review"  # Human reviews spec
    DESIGN = "design"                # Architect producing design
    DESIGN_REVIEW = "design_review"  # Human reviews design
    DEVELOPMENT = "development"      # Developer writing code
    TESTING = "testing"              # QA running tests
    QA_REVIEW = "qa_review"          # Human reviews QA report
    DEPLOYMENT = "deployment"        # Deploying to target
    COMPLETE = "complete"            # Done
    FAILED = "failed"                # Pipeline failed
    BLOCKED = "blocked"              # Waiting for human input


# Stage transitions: current → next (with conditions)
STAGE_TRANSITIONS = {
    PipelineStage.INTAKE: PipelineStage.REQUIREMENTS,
    PipelineStage.REQUIREMENTS: PipelineStage.REQUIREMENTS_REVIEW,
    PipelineStage.REQUIREMENTS_REVIEW: PipelineStage.DESIGN,
    PipelineStage.DESIGN: PipelineStage.DESIGN_REVIEW,
    PipelineStage.DESIGN_REVIEW: PipelineStage.DEVELOPMENT,
    PipelineStage.DEVELOPMENT: PipelineStage.TESTING,
    PipelineStage.TESTING: PipelineStage.QA_REVIEW,
    PipelineStage.QA_REVIEW: PipelineStage.DEPLOYMENT,
    PipelineStage.DEPLOYMENT: PipelineStage.COMPLETE,
}

# Which stages require human approval before advancing
HUMAN_REVIEW_GATES = {
    PipelineStage.REQUIREMENTS_REVIEW,
    PipelineStage.DESIGN_REVIEW,
    PipelineStage.QA_REVIEW,
}

# Which agent handles each stage
STAGE_AGENTS = {
    PipelineStage.REQUIREMENTS: AgentRole.PM,
    PipelineStage.DESIGN: AgentRole.ARCHITECT,
    PipelineStage.DEVELOPMENT: AgentRole.DEVELOPER,
    PipelineStage.TESTING: AgentRole.QA,
    PipelineStage.DEPLOYMENT: AgentRole.DEVOPS,
}


@dataclass
class PipelineEvent:
    """A single event in the pipeline history."""
    timestamp: str
    stage: str
    action: str  # started, completed, approved, rejected, error
    agent: str
    message: str
    artifact_path: Optional[str] = None
    duration_ms: Optional[float] = None


@dataclass
class Project:
    """Represents a project flowing through the SDLC pipeline."""
    id: str
    title: str
    raw_request: str
    current_stage: str
    created_at: str
    updated_at: str
    
    # Artifact versions at each stage
    spec_version: Optional[str] = None
    design_version: Optional[str] = None
    impl_version: Optional[str] = None
    qa_version: Optional[str] = None
    
    # Review gate status
    review_gates: Dict = field(default_factory=lambda: {
        "requirements_review": {"status": "pending", "reviewer": None, "notes": ""},
        "design_review": {"status": "pending", "reviewer": None, "notes": ""},
        "qa_review": {"status": "pending", "reviewer": None, "notes": ""},
    })
    
    # Pipeline history
    events: List[Dict] = field(default_factory=list)
    
    # Metadata
    model_used: Dict = field(default_factory=dict)  # stage → model alias
    total_cost: float = 0.0
    error: Optional[str] = None
    
    def to_dict(self) -> Dict:
        return asdict(self)
    
    def add_event(self, stage: str, action: str, agent: str, 
                  message: str, artifact_path: str = None, duration_ms: float = None):
        self.events.append(asdict(PipelineEvent(
            timestamp=datetime.now().isoformat(),
            stage=stage, action=action, agent=agent,
            message=message, artifact_path=artifact_path,
            duration_ms=duration_ms,
        )))
        self.updated_at = datetime.now().isoformat()


class SDLCPipeline:
    """
    Multi-agent SDLC pipeline orchestrator.
    
    Manages the flow: Intake → PM → [Review] → Architect → [Review] → Developer → QA → [Review] → Deploy
    """
    
    def __init__(self, auto_approve: bool = False, llm_mode: bool = False):
        self.store = ArtifactStore()
        self.projects: Dict[str, Project] = {}
        self.auto_approve = auto_approve  # Skip human review gates
        self.llm_mode = llm_mode  # Use LLM-powered agents when True
        self.project_db_path = Path.home() / ".openclaw" / "workspace" / "nexdev" / "projects" / "pipeline.json"
        
        # Initialize agents
        self.pm = PMAgent()
        self.architect = ArchitectAgent()
        self.test_gen = TestGenAgent()
        self.qa = QAEngineer()
        
        # Load existing projects
        self._load_projects()
    
    def _load_projects(self):
        """Load projects from disk."""
        if self.project_db_path.exists():
            try:
                with open(self.project_db_path) as f:
                    data = json.load(f)
                for pid, pdata in data.items():
                    self.projects[pid] = Project(**pdata)
            except (json.JSONDecodeError, TypeError):
                pass
    
    def _save_projects(self):
        """Save projects to disk."""
        self.project_db_path.parent.mkdir(parents=True, exist_ok=True)
        data = {pid: p.to_dict() for pid, p in self.projects.items()}
        with open(self.project_db_path, 'w') as f:
            json.dump(data, f, indent=2)
    
    def start(self, raw_request: str, project_id: str = None, 
              title: str = None) -> Project:
        """
        Start a new project in the pipeline.
        
        Args:
            raw_request: Natural language project description
            project_id: Override project ID
            title: Override project title
        
        Returns:
            Project instance
        """
        now = datetime.now()
        pid = project_id or f"PROJ-{now.strftime('%Y%m%d-%H%M%S')}"
        
        project = Project(
            id=pid,
            title=title or raw_request[:60],
            raw_request=raw_request,
            current_stage=PipelineStage.INTAKE.value,
            created_at=now.isoformat(),
            updated_at=now.isoformat(),
        )
        
        project.add_event("intake", "started", "pipeline", 
                         f"Project '{pid}' created from request")
        
        self.projects[pid] = project
        self._save_projects()
        
        # Auto-advance from intake to requirements
        return self.advance(pid)
    
    def advance(self, project_id: str, approval: str = None,
                review_notes: str = None) -> Project:
        """
        Advance a project to the next pipeline stage.
        
        Args:
            project_id: Project to advance
            approval: For review gates: "approve" or "reject"
            review_notes: Optional reviewer notes
        
        Returns:
            Updated Project instance
        """
        project = self.projects.get(project_id)
        if not project:
            raise ValueError(f"Project {project_id} not found")
        
        current = PipelineStage(project.current_stage)

        # Handle BLOCKED state: find the last review gate and re-enter it
        if current == PipelineStage.BLOCKED and approval:
            # Find the last review gate from events
            review_stages = {s.value for s in HUMAN_REVIEW_GATES}
            last_gate = None
            for event in reversed(project.events):
                if event.get("stage") in review_stages and event.get("action") == "blocked":
                    last_gate = PipelineStage(event["stage"])
                    break
            if last_gate:
                project.current_stage = last_gate.value
                current = last_gate
            else:
                # Fallback: check review_gates for first pending one
                for gate_stage in [PipelineStage.REQUIREMENTS_REVIEW, PipelineStage.DESIGN_REVIEW, PipelineStage.QA_REVIEW]:
                    gate_data = project.review_gates.get(gate_stage.value, {})
                    if gate_data.get("status") == "pending":
                        project.current_stage = gate_stage.value
                        current = gate_stage
                        break

        
        # Handle review gates
        if current in HUMAN_REVIEW_GATES:
            return self._handle_review_gate(project, current, approval, review_notes)
        
        # Get next stage
        next_stage = STAGE_TRANSITIONS.get(current)
        if not next_stage:
            project.add_event(current.value, "error", "pipeline",
                            f"No transition from {current.value}")
            return project
        
        # Execute the stage
        start_time = time.time()
        try:
            result = self._execute_stage(project, next_stage)
            duration = (time.time() - start_time) * 1000
            
            project.current_stage = next_stage.value
            project.add_event(next_stage.value, "completed", 
                            STAGE_AGENTS.get(next_stage, AgentRole.PM).value,
                            f"Stage {next_stage.value} completed",
                            duration_ms=duration)
            
            # If next stage is a review gate and auto_approve is on, skip it
            if next_stage in HUMAN_REVIEW_GATES and self.auto_approve:
                project.review_gates[next_stage.value] = {
                    "status": "auto_approved", "reviewer": "pipeline", "notes": "Auto-approved"
                }
                project.add_event(next_stage.value, "approved", "pipeline",
                                "Auto-approved (auto_approve=True)")
                # Advance past the review gate
                after_review = STAGE_TRANSITIONS.get(next_stage)
                if after_review:
                    project.current_stage = next_stage.value
                    self._save_projects()
                    return self.advance(project_id, approval="approve")
            
        except Exception as e:
            project.current_stage = PipelineStage.FAILED.value
            project.error = str(e)
            project.add_event(next_stage.value, "error",
                            STAGE_AGENTS.get(next_stage, AgentRole.PM).value,
                            f"Error: {str(e)}")
        
        self._save_projects()
        return project
    
    def _handle_review_gate(self, project: Project, stage: PipelineStage,
                           approval: str, notes: str) -> Project:
        """Handle a human review gate."""
        gate_key = stage.value
        
        if not approval:
            # No approval provided — project stays blocked
            project.current_stage = PipelineStage.BLOCKED.value
            project.add_event(gate_key, "blocked", "pipeline",
                            f"Waiting for human review at {gate_key}")
            self._save_projects()
            return project
        
        if approval == "approve":
            project.review_gates[gate_key] = {
                "status": "approved",
                "reviewer": "human",
                "notes": notes or "",
                "timestamp": datetime.now().isoformat(),
            }
            project.add_event(gate_key, "approved", "human",
                            f"Approved: {notes or 'No notes'}")
            
            # Set stage past the gate and execute next production stage
            next_stage = STAGE_TRANSITIONS.get(stage)
            if next_stage:
                # Skip past the review gate to the production stage
                project.current_stage = next_stage.value
                project.add_event(next_stage.value, "started",
                                STAGE_AGENTS.get(next_stage, AgentRole.PM).value,
                                f"Starting {next_stage.value}")
                
                # If the next stage is also a review gate, just return
                if next_stage in HUMAN_REVIEW_GATES:
                    self._save_projects()
                    return project
                
                # Execute the next stage
                start_time = time.time()
                try:
                    result = self._execute_stage(project, next_stage)
                    duration = (time.time() - start_time) * 1000
                    project.add_event(next_stage.value, "completed",
                                    STAGE_AGENTS.get(next_stage, AgentRole.PM).value,
                                    f"Stage {next_stage.value} completed",
                                    duration_ms=duration)
                    
                    # Advance to the next stage after this one
                    after_next = STAGE_TRANSITIONS.get(next_stage)
                    if after_next:
                        if after_next in HUMAN_REVIEW_GATES:
                            # Next is a review gate — park here for approval
                            project.current_stage = after_next.value
                            if self.auto_approve:
                                project.review_gates[after_next.value] = {
                                    "status": "auto_approved", "reviewer": "pipeline", "notes": "Auto-approved"
                                }
                                project.add_event(after_next.value, "approved", "pipeline",
                                                "Auto-approved (auto_approve=True)")
                                self._save_projects()
                                return self.advance(project.id, approval="approve")
                        else:
                            # Next is a production stage — execute it inline
                            project.current_stage = after_next.value
                            project.add_event(after_next.value, "started",
                                            STAGE_AGENTS.get(after_next, AgentRole.PM).value,
                                            f"Starting {after_next.value}")
                            start2 = time.time()
                            try:
                                result2 = self._execute_stage(project, after_next)
                                dur2 = (time.time() - start2) * 1000
                                project.add_event(after_next.value, "completed",
                                                STAGE_AGENTS.get(after_next, AgentRole.PM).value,
                                                f"Stage {after_next.value} completed",
                                                duration_ms=dur2)
                                # Continue chain for whatever comes after
                                after_after = STAGE_TRANSITIONS.get(after_next)
                                if after_after:
                                    project.current_stage = after_after.value
                            except Exception as e2:
                                project.current_stage = PipelineStage.FAILED.value
                                project.error = str(e2)
                                project.add_event(after_next.value, "error",
                                                STAGE_AGENTS.get(after_next, AgentRole.PM).value,
                                                f"Error: {str(e2)}")
                    
                except Exception as e:
                    project.current_stage = PipelineStage.FAILED.value
                    project.error = str(e)
                    project.add_event(next_stage.value, "error",
                                    STAGE_AGENTS.get(next_stage, AgentRole.PM).value,
                                    f"Error: {str(e)}")
        
        elif approval == "reject":
            # Go back to previous production stage
            project.review_gates[gate_key] = {
                "status": "rejected",
                "reviewer": "human",
                "notes": notes or "",
                "timestamp": datetime.now().isoformat(),
            }
            project.add_event(gate_key, "rejected", "human",
                            f"Rejected: {notes or 'No notes'}")
            
            # Determine which stage to go back to
            rollback_map = {
                PipelineStage.REQUIREMENTS_REVIEW: PipelineStage.INTAKE,
                PipelineStage.DESIGN_REVIEW: PipelineStage.REQUIREMENTS,
                PipelineStage.QA_REVIEW: PipelineStage.DEVELOPMENT,
            }
            rollback = rollback_map.get(stage, PipelineStage.INTAKE)
            project.current_stage = rollback.value
            project.add_event(gate_key, "rollback", "pipeline",
                            f"Rolled back to {rollback.value}")
        
        self._save_projects()
        return project
    
    def _execute_stage_llm(self, project: Project, stage: PipelineStage) -> Dict:
        """Execute a pipeline stage using LLM-powered agents via MO routing."""
        from .agent_engine import create_agent, get_system_prompt
        
        if stage == PipelineStage.REQUIREMENTS:
            agent = create_agent("product_manager", project.id)
            prompt = f"Generate a complete software specification for:\n\n{project.raw_request}"
            result = agent.ask_json(prompt, get_system_prompt("product_manager"))
            
            if "data" in result:
                spec_data = result["data"]
                spec_data.setdefault("project_id", project.id)
                spec_data.setdefault("version", "1")
                self.store.save_artifact(project.id, "specs", "1", spec_data)
                project.spec_version = "1"
                project.total_cost += result.get("cost", 0)
                project.model_used[stage.value] = result.get("model", "unknown")
                return {"spec": spec_data}
            else:
                # Fallback to rule-based
                return self._execute_stage_rules(project, stage)
        
        elif stage == PipelineStage.DESIGN:
            spec_data = self.store.load_artifact(project.id, "specs", project.spec_version)
            if not spec_data:
                raise ValueError("No specification found")
            
            agent = create_agent("architect", project.id)
            prompt = f"Design the system architecture for this specification:\n\n{json.dumps(spec_data, indent=2)}"
            result = agent.ask_json(prompt, get_system_prompt("architect"))
            
            if "data" in result:
                design_data = result["data"]
                design_data.setdefault("project_id", project.id)
                design_data.setdefault("version", "1")
                design_data.setdefault("spec_version", project.spec_version)
                self.store.save_artifact(project.id, "design", "1", design_data)
                project.design_version = "1"
                project.total_cost += result.get("cost", 0)
                project.model_used[stage.value] = result.get("model", "unknown")
                return {"design": design_data}
            else:
                return self._execute_stage_rules(project, stage)
        
        elif stage == PipelineStage.DEVELOPMENT:
            design_data = self.store.load_artifact(project.id, "design", project.design_version)
            if not design_data:
                raise ValueError("No architecture design found")
            
            agent = create_agent("developer", project.id)
            prompt = f"Generate production-ready implementation code for this architecture:\n\n{json.dumps(design_data, indent=2)}"
            result = agent.ask_json(prompt, get_system_prompt("developer"))
            
            if "data" in result:
                impl_data = result["data"]
                self.store.save_artifact(project.id, "impl", "1", impl_data)
                project.impl_version = "1"
                project.total_cost += result.get("cost", 0)
                project.model_used[stage.value] = result.get("model", "unknown")
                return impl_data
            else:
                return self._execute_stage_rules(project, stage)
        
        elif stage == PipelineStage.TESTING:
            impl_data = self.store.load_artifact(project.id, "impl", project.impl_version)
            if not impl_data:
                raise ValueError("No implementation found")
            
            from .build_runner import verify_implementation
            MAX_FIX_ROUNDS = 3
            qa_data = None
            
            for fix_round in range(MAX_FIX_ROUNDS + 1):
                round_label = f"round {fix_round}" if fix_round > 0 else "initial"
                project.add_event("testing", "started" if fix_round == 0 else "fix_round",
                                "qa", f"Testing {round_label}")
                
                # Step 1: Generate tests via LLM
                all_code = "\n".join(f.get("content", "") for f in impl_data.get("files", []))
                file_manifest = "\n".join(
                    f"- {f['path']} ({f.get('language','?')})" for f in impl_data.get("files", [])
                )
                
                test_agent = create_agent("test_engineer", project.id)
                test_prompt = (
                    "Generate comprehensive pytest test files for this code.\n"
                    "IMPORTANT: Use the EXACT module paths shown in the file manifest below.\n"
                    "Output JSON with: test_files (array of {path, language, description, content}).\n"
                    "Write REAL tests with real assertions — not stubs or placeholders.\n\n"
                    f"FILE MANIFEST:\n{file_manifest}\n\n"
                    f"SOURCE CODE:\n{all_code[:8000]}"
                )
                test_result = test_agent.ask_json(test_prompt,
                    "You are a senior test engineer. Write thorough pytest tests. "
                    "Import from the EXACT file paths listed in the manifest.")
                
                if "data" in test_result:
                    new_tests = test_result["data"].get("test_files", [])
                    if new_tests:
                        impl_data["test_files"] = new_tests
                        self.store.save_artifact(project.id, "impl", project.impl_version, impl_data)
                    project.total_cost += test_result.get("cost", 0)
                    project.model_used["test_generation"] = test_result.get("model", "unknown")
                
                # Step 2: Build verification & test execution
                build_results = verify_implementation(impl_data)
                report_ver = str(fix_round + 1)
                self.store.save_artifact(project.id, "build_report", report_ver, build_results)
                
                # Step 3: QA analysis
                qa_agent = create_agent("qa_engineer", project.id)
                qa_prompt = (
                    "Analyze these build and test results. Provide a QA assessment.\n"
                    "Output JSON with: recommendation (ship_it|fix_required|major_rework), "
                    "blocking_issues (array), non_blocking_issues (array), "
                    "security_concerns (array), quality_score (0-100).\n\n"
                    f"Build grade: {build_results['summary']['grade']}\n"
                    f"Verdict: {build_results['summary']['verdict']}\n"
                    f"Syntax: {json.dumps(build_results['syntax_checks'], indent=2)[:1500]}\n"
                    f"Lint: {json.dumps(build_results['lint_results'], indent=2)[:1000]}\n"
                    f"Tests: {json.dumps(build_results['test_results'], indent=2)[:1500]}"
                )
                qa_result = qa_agent.ask_json(qa_prompt, get_system_prompt("qa_engineer"))
                
                if "data" in qa_result:
                    qa_data = qa_result["data"]
                    qa_data["build_verification"] = build_results["summary"]
                    qa_data["project_id"] = project.id
                    qa_data["fix_round"] = fix_round
                    project.total_cost += qa_result.get("cost", 0)
                    project.model_used["qa"] = qa_result.get("model", "unknown")
                else:
                    qa_data = {
                        "project_id": project.id,
                        "fix_round": fix_round,
                        "recommendation": "fix_required" if build_results["summary"]["grade"] in ("D", "F") else "ship_it",
                        "build_verification": build_results["summary"],
                        "blocking_issues": [s["errors"][0] for s in build_results["syntax_checks"] if s["status"] == "fail"],
                        "non_blocking_issues": [],
                        "quality_score": 0,
                    }
                
                # Check if we can ship
                rec = qa_data.get("recommendation", "fix_required")
                grade = build_results["summary"].get("grade", "F")
                
                if rec == "ship_it" or grade in ("A", "B+", "B"):
                    project.add_event("testing", "passed", "qa",
                                    f"QA passed ({round_label}): grade={grade}, score={qa_data.get('quality_score', '?')}")
                    break
                
                # If last round, accept whatever we have
                if fix_round >= MAX_FIX_ROUNDS:
                    project.add_event("testing", "max_retries", "qa",
                                    f"Max fix rounds reached ({MAX_FIX_ROUNDS}). Grade: {grade}")
                    break
                
                # Fix loop: send failures back to developer
                project.add_event("testing", "fix_requested", "qa",
                                f"Round {fix_round}: grade={grade}, sending back to developer")
                
                dev_agent = create_agent("developer", project.id)
                blocking = qa_data.get("blocking_issues", [])
                syntax_errors = [s for s in build_results["syntax_checks"] if s["status"] == "fail"]
                test_failures = [t.get("output", "")[:500] for t in build_results["test_results"] if t.get("status") == "fail"]
                
                fix_prompt = (
                    "The code has issues that need fixing. Here are the problems:\n\n"
                    f"BUILD GRADE: {grade}\n"
                    f"BLOCKING ISSUES: {json.dumps(blocking[:5])}\n"
                    f"SYNTAX ERRORS: {json.dumps([{'file': s['file'], 'error': s['errors'][0][:200]} for s in syntax_errors])}\n"
                    f"TEST FAILURES:\n{''.join(test_failures[:3])}\n\n"
                    f"CURRENT CODE:\n{all_code[:6000]}\n\n"
                    "Fix ALL issues. Output the complete corrected implementation as JSON with: "
                    "files (array of {path, language, description, content}).\n"
                    "Return ALL files, not just the changed ones."
                )
                fix_result = dev_agent.ask_json(fix_prompt,
                    "You are a senior developer. Fix the reported bugs. Return complete working code.")
                
                if "data" in fix_result:
                    fixed_files = fix_result["data"].get("files", [])
                    if fixed_files:
                        impl_data["files"] = fixed_files
                        impl_data["test_files"] = []  # Clear old tests, will regenerate
                        new_ver = str(int(project.impl_version or "1") + 1)
                        project.impl_version = new_ver
                        self.store.save_artifact(project.id, "impl", new_ver, impl_data)
                        project.total_cost += fix_result.get("cost", 0)
                        project.model_used[f"fix_round_{fix_round + 1}"] = fix_result.get("model", "unknown")
                        project.add_event("testing", "code_fixed", "developer",
                                        f"Developer fixed code (v{new_ver}), {len(fixed_files)} files")
                    else:
                        project.add_event("testing", "fix_empty", "developer",
                                        "Developer returned no files, stopping fix loop")
                        break
                else:
                    project.add_event("testing", "fix_failed", "developer",
                                    f"Developer fix failed: {fix_result.get('error', '?')[:100]}")
                    break
            
            # Save final QA report
            self.store.save_artifact(project.id, "qa", "1", qa_data)
            project.qa_version = "1"
            return qa_data
        
        elif stage == PipelineStage.DEPLOYMENT:
            self.store.save_artifact(project.id, "deploy", "1", {
                "deployed_at": datetime.now().isoformat(),
                "status": "success",
                "impl_version": project.impl_version,
                "qa_version": project.qa_version,
            })
            return {"status": "deployed"}
        
        # Review gates and others fall through to rules
        return self._execute_stage_rules(project, stage)


    def _execute_stage_rules(self, project, stage):
        """Execute stage using rule-based agents (no LLM)."""
        saved = self.llm_mode
        self.llm_mode = False
        try:
            return self._execute_stage(project, stage)
        finally:
            self.llm_mode = saved

    def _execute_stage(self, project: Project, stage: PipelineStage) -> Dict:
        """Execute a pipeline stage using the appropriate agent."""
        # Route to LLM or rule-based execution
        if self.llm_mode and stage not in (PipelineStage.REQUIREMENTS_REVIEW, PipelineStage.DESIGN_REVIEW, PipelineStage.QA_REVIEW):
            try:
                return self._execute_stage_llm(project, stage)
            except Exception as e:
                # Fallback to rules on LLM failure
                project.add_event(stage.value, "llm_fallback", "pipeline",
                                f"LLM failed ({e}), falling back to rules")
        
        
        if stage == PipelineStage.REQUIREMENTS:
            # PM Agent: raw request → spec
            analysis = self.pm.analyze_request(project.raw_request)
            spec = self.pm.generate_spec(project.raw_request, project_id=project.id)
            project.spec_version = "1"
            return {"spec": spec.to_dict(), "analysis": analysis}
        
        elif stage == PipelineStage.REQUIREMENTS_REVIEW:
            # Just mark as needing review — no agent work
            return {"gate": "requirements_review", "awaiting": "human"}
        
        elif stage == PipelineStage.DESIGN:
            # Architect Agent: spec → design
            spec_data = self.store.load_artifact(project.id, "specs", project.spec_version)
            if not spec_data:
                raise ValueError("No specification found for project")
            
            # Reconstruct spec from stored data
            from .contracts import UserStory, NonFunctionalRequirement
            spec = SpecificationDocument(
                project_id=spec_data["project_id"],
                version=spec_data["version"],
                title=spec_data["title"],
                summary=spec_data["summary"],
                user_stories=[UserStory(**s) for s in spec_data["user_stories"]],
                non_functional_requirements=[NonFunctionalRequirement(**n) for n in spec_data["non_functional_requirements"]],
                constraints=spec_data["constraints"],
                assumptions=spec_data["assumptions"],
                out_of_scope=spec_data["out_of_scope"],
                tech_stack_preferences=spec_data.get("tech_stack_preferences", []),
            )
            
            design = self.architect.design(spec)
            project.design_version = "1"
            return {"design": design.to_dict()}
        
        elif stage == PipelineStage.DESIGN_REVIEW:
            return {"gate": "design_review", "awaiting": "human"}
        
        elif stage == PipelineStage.DEVELOPMENT:
            # Developer: design → code + tests
            design_data = self.store.load_artifact(project.id, "design", project.design_version)
            if not design_data:
                raise ValueError("No architecture design found for project")
            
            # Generate code based on design
            impl = self._generate_code(project, design_data)
            project.impl_version = "1"
            
            # Generate tests for the code
            for impl_file in impl["files"]:
                if impl_file["language"] == "python":
                    test_code = self.test_gen.generate_from_code(
                        impl_file["content"], "python"
                    )
                    impl["test_files"].append({
                        "path": f"tests/test_{Path(impl_file['path']).stem}.py",
                        "language": "python",
                        "description": f"Tests for {impl_file['path']}",
                        "content": test_code,
                    })
            
            # Save implementation artifact
            self.store.save_artifact(project.id, "impl", "1", impl)
            return impl
        
        elif stage == PipelineStage.TESTING:
            # QA Agent: implementation → test report
            impl_data = self.store.load_artifact(project.id, "impl", project.impl_version)
            if not impl_data:
                raise ValueError("No implementation found for project")
            
            all_code = "\n".join(f["content"] for f in impl_data.get("files", []))
            all_tests = "\n".join(f["content"] for f in impl_data.get("test_files", []))
            
            qa_report = self.qa.run_tests(all_code, all_tests)
            project.qa_version = "1"
            
            self.store.save_artifact(project.id, "qa", "1", qa_report.to_dict())
            return qa_report.to_dict()
        
        elif stage == PipelineStage.QA_REVIEW:
            return {"gate": "qa_review", "awaiting": "human"}
        
        elif stage == PipelineStage.DEPLOYMENT:
            # Deploy the project
            self.store.save_artifact(project.id, "deploy", "1", {
                "deployed_at": datetime.now().isoformat(),
                "status": "success",
                "impl_version": project.impl_version,
                "qa_version": project.qa_version,
            })
            return {"status": "deployed"}
        
        elif stage == PipelineStage.COMPLETE:
            return {"status": "complete"}
        
        return {}
    
    def _generate_code(self, project: Project, design_data: Dict) -> Dict:
        """Generate code from architecture design."""
        pattern = design_data.get("architecture_pattern", "monolithic")
        tech = design_data.get("tech_stack", {})
        components = design_data.get("components", [])
        endpoints = design_data.get("api_endpoints", [])
        tables = design_data.get("database_schema", [])
        
        files = []
        test_files = []
        
        # Generate main app file
        if "node" in tech.get("backend", "").lower() or "express" in tech.get("backend", "").lower():
            files.append(self._gen_node_app(endpoints, components))
        else:
            files.append(self._gen_python_app(endpoints, components))
        
        # Generate database models
        if tables:
            files.append(self._gen_db_models(tables))
        
        # Generate config
        files.append({
            "path": "config.py",
            "language": "python",
            "description": "Application configuration",
            "content": self._gen_config(design_data),
        })
        
        # Generate Dockerfile
        files.append({
            "path": "Dockerfile",
            "language": "dockerfile",
            "description": "Container definition",
            "content": self._gen_dockerfile(tech),
        })
        
        # Generate requirements.txt
        files.append({
            "path": "requirements.txt",
            "language": "text",
            "description": "Python dependencies",
            "content": self._gen_requirements(components),
        })
        
        return {
            "files": files,
            "test_files": test_files,
            "dependencies": {},
            "build_commands": ["docker build -t app ."],
            "run_commands": ["docker run -p 8000:8000 app"],
            "environment_variables": ["DATABASE_URL", "SECRET_KEY", "API_KEY"],
        }
    
    def _gen_python_app(self, endpoints: List, components: List) -> Dict:
        """Generate a Python FastAPI application."""
        route_code = []
        for ep in endpoints:
            method = ep.get("method", "GET").lower()
            path = ep.get("path", "/")
            desc = ep.get("description", "")
            auth = ep.get("auth_required", True)
            
            auth_dep = ", current_user: dict = Depends(get_current_user)" if auth else ""
            
            route_code.append(f'''
@app.{method}("{path}")
async def {self._path_to_func(path)}({auth_dep}):
    """{desc}"""
    # TODO: Implement business logic
    return {{"message": "{desc}", "status": "ok"}}
''')
        
        content = f'''#!/usr/bin/env python3
"""Auto-generated FastAPI application"""
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
import uvicorn

app = FastAPI(title="Generated App", version="1.0.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Auth dependency (placeholder)
async def get_current_user():
    # TODO: Implement JWT validation
    return {{"id": "user-1", "role": "admin"}}

# Health check
@app.get("/api/health")
async def health():
    return {{"status": "healthy", "version": "1.0.0"}}

{"".join(route_code)}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
'''
        return {
            "path": "app/main.py",
            "language": "python",
            "description": "Main FastAPI application",
            "content": content,
        }
    
    def _gen_node_app(self, endpoints: List, components: List) -> Dict:
        """Generate a Node.js Express application."""
        route_code = []
        for ep in endpoints:
            method = ep.get("method", "GET").lower()
            path = ep.get("path", "/")
            desc = ep.get("description", "")
            
            route_code.append(f'''
router.{method}('{path}', async (req, res) => {{
  // {desc}
  try {{
    // TODO: Implement business logic
    res.json({{ message: '{desc}', status: 'ok' }});
  }} catch (error) {{
    res.status(500).json({{ error: error.message }});
  }}
}});
''')
        
        content = f'''const express = require('express');
const cors = require('cors');
const app = express();
const router = express.Router();

app.use(cors());
app.use(express.json());

// Health check
router.get('/api/health', (req, res) => {{
  res.json({{ status: 'healthy', version: '1.0.0' }});
}});

{"".join(route_code)}

app.use(router);

const PORT = process.env.PORT || 8000;
app.listen(PORT, () => console.log(`Server running on port ${{PORT}}`));

module.exports = app;
'''
        return {
            "path": "src/index.js",
            "language": "javascript",
            "description": "Main Express application",
            "content": content,
        }
    
    def _gen_db_models(self, tables: List) -> Dict:
        """Generate database models."""
        model_code = ['"""Auto-generated database models"""\n']
        model_code.append("from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Boolean")
        model_code.append("from sqlalchemy.dialects.postgresql import UUID")
        model_code.append("from sqlalchemy.ext.declarative import declarative_base")
        model_code.append("from datetime import datetime")
        model_code.append("import uuid\n")
        model_code.append("Base = declarative_base()\n")
        
        type_map = {
            "UUID": "UUID(as_uuid=True)",
            "VARCHAR": "String",
            "TEXT": "String",
            "INTEGER": "Integer",
            "BOOLEAN": "Boolean",
            "TIMESTAMP": "DateTime",
        }
        
        for table in tables:
            name = table.get("name", "unknown")
            class_name = name.replace("_", " ").title().replace(" ", "")
            desc = table.get("description", "")
            
            model_code.append(f'\nclass {class_name}(Base):')
            model_code.append(f'    """{desc}"""')
            model_code.append(f'    __tablename__ = "{name}"\n')
            
            for col in table.get("columns", []):
                col_name = col.get("name", "unknown")
                col_type = col.get("type", "String").split("(")[0].upper()
                nullable = col.get("nullable", True)
                
                sa_type = type_map.get(col_type, "String")
                
                if col_name == "id":
                    model_code.append(f'    {col_name} = Column({sa_type}, primary_key=True, default=uuid.uuid4)')
                else:
                    model_code.append(f'    {col_name} = Column({sa_type}, nullable={nullable})')
            
            model_code.append("")
        
        return {
            "path": "app/models.py",
            "language": "python",
            "description": "Database models (SQLAlchemy)",
            "content": "\n".join(model_code),
        }
    
    def _gen_config(self, design: Dict) -> str:
        return '''"""Application configuration"""
import os

class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "change-me-in-production")
    DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://localhost:5432/app")
    DEBUG = os.getenv("DEBUG", "false").lower() == "true"
    API_VERSION = "1.0.0"
    CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*").split(",")
'''
    
    def _gen_dockerfile(self, tech: Dict) -> str:
        if "node" in tech.get("backend", "").lower():
            return '''FROM node:20-alpine
WORKDIR /app
COPY package*.json ./
RUN npm ci --only=production
COPY . .
EXPOSE 8000
CMD ["node", "src/index.js"]
'''
        return '''FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
'''
    
    def _gen_requirements(self, components: List) -> str:
        reqs = ["fastapi>=0.110.0", "uvicorn>=0.29.0", "sqlalchemy>=2.0", 
                "pydantic>=2.6", "python-jose[cryptography]>=3.3", "bcrypt>=4.1",
                "alembic>=1.13", "psycopg2-binary>=2.9", "httpx>=0.27"]
        
        for comp in components:
            name = comp.get("name", "").lower()
            if "websocket" in name:
                reqs.append("websockets>=12.0")
            if "redis" in comp.get("technology", "").lower():
                reqs.append("redis>=5.0")
        
        return "\n".join(sorted(set(reqs)))
    
    def _path_to_func(self, path: str) -> str:
        """Convert API path to function name."""
        clean = path.replace("/api/", "").replace("/", "_").replace(":", "").replace("-", "_")
        return clean.strip("_") or "root"
    
    # ── Status & Reporting ───────────────────────────────────────────────────
    
    def status(self, project_id: str) -> Dict:
        """Get current pipeline status for a project."""
        project = self.projects.get(project_id)
        if not project:
            return {"error": f"Project {project_id} not found"}
        
        current = PipelineStage(project.current_stage)
        
        # Determine what's needed to advance
        next_action = "unknown"
        if current in HUMAN_REVIEW_GATES:
            next_action = f"Human review required at {current.value}. Call advance('{project_id}', approval='approve')"
        elif current == PipelineStage.BLOCKED:
            next_action = "Project blocked — check review gates"
        elif current == PipelineStage.COMPLETE:
            next_action = "Project complete!"
        elif current == PipelineStage.FAILED:
            next_action = f"Project failed: {project.error}"
        else:
            next_action = f"Call advance('{project_id}') to proceed to next stage"
        
        return {
            "project_id": project.id,
            "title": project.title,
            "current_stage": project.current_stage,
            "next_action": next_action,
            "spec_version": project.spec_version,
            "design_version": project.design_version,
            "impl_version": project.impl_version,
            "qa_version": project.qa_version,
            "review_gates": project.review_gates,
            "events_count": len(project.events),
            "total_cost": project.total_cost,
            "created": project.created_at,
            "updated": project.updated_at,
        }
    
    def list_projects(self) -> List[Dict]:
        """List all projects with current status."""
        return [
            {
                "id": p.id,
                "title": p.title[:50],
                "stage": p.current_stage,
                "created": p.created_at,
                "events": len(p.events),
            }
            for p in self.projects.values()
        ]
    
    def get_artifacts(self, project_id: str) -> Dict:
        """Get all artifacts for a project."""
        return self.store.list_artifacts(project_id)
    
    def format_status(self, project_id: str) -> str:
        """Format project status for chat display."""
        s = self.status(project_id)
        if "error" in s:
            return f"❌ {s['error']}"
        
        stage_emoji = {
            "intake": "📥", "requirements": "📝", "requirements_review": "👀",
            "design": "🏗️", "design_review": "👀", "development": "💻",
            "testing": "🧪", "qa_review": "👀", "deployment": "🚀",
            "complete": "✅", "failed": "❌", "blocked": "🔒",
        }
        
        emoji = stage_emoji.get(s["current_stage"], "❓")
        
        lines = [
            f"{emoji} **Project: {s['title'][:40]}**",
            f"Stage: `{s['current_stage']}` | ID: `{s['project_id']}`",
            f"",
            f"**Artifacts:**",
            f"• Spec: v{s['spec_version'] or '-'} | Design: v{s['design_version'] or '-'}",
            f"• Impl: v{s['impl_version'] or '-'} | QA: v{s['qa_version'] or '-'}",
            f"",
            f"**Next:** {s['next_action']}",
        ]
        
        # Review gate status
        for gate, info in s.get("review_gates", {}).items():
            status = info.get("status", "pending")
            gate_emoji = {"pending": "⏳", "approved": "✅", "rejected": "❌", 
                         "auto_approved": "🤖"}.get(status, "❓")
            lines.append(f"• {gate}: {gate_emoji} {status}")
        
        return "\n".join(lines)


if __name__ == "__main__":
    # Demo: run a full pipeline with auto-approve
    pipeline = SDLCPipeline(auto_approve=True)
    
    project = pipeline.start(
        "Build a REST API for a task management app with user auth, "
        "task CRUD, and team collaboration. Use Python FastAPI and PostgreSQL."
    )
    
    print(f"\n{'='*60}")
    print(pipeline.format_status(project.id))
    
    # Advance through all stages
    for i in range(10):  # Max iterations
        status = pipeline.status(project.id)
        if status["current_stage"] in ["complete", "failed"]:
            break
        project = pipeline.advance(project.id)
        print(f"\nAdvanced to: {project.current_stage}")
    
    print(f"\n{'='*60}")
    print(pipeline.format_status(project.id))
    
    # Show artifacts
    print(f"\nArtifacts: {pipeline.get_artifacts(project.id)}")
