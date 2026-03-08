#!/usr/bin/env python3
"""
NexDev Phase 1.4 — Agent Role Definitions & Contracts
======================================================
Defines the input/output contracts for each SDLC agent role.
Every handoff between agents produces a versioned, structured artifact.

Roles:
  PM (Product Manager)  → Produces: Specification Document
  Architect             → Produces: Architecture Design Document
  Developer             → Produces: Implementation (code + tests)
  QA                    → Produces: Test Report & Sign-off

Each artifact has a defined schema so agents know exactly what to
expect as input and what to produce as output.
"""

import json
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional
from datetime import datetime
from enum import Enum
from pathlib import Path


class AgentRole(Enum):
    PM = "product_manager"
    ARCHITECT = "architect"
    DEVELOPER = "developer"
    QA = "qa_engineer"
    SECURITY = "security_architect"
    PERFORMANCE = "performance_engineer"
    DEVOPS = "devops_engineer"


class ArtifactStatus(Enum):
    DRAFT = "draft"
    REVIEW = "review"
    APPROVED = "approved"
    REJECTED = "rejected"
    SUPERSEDED = "superseded"


# ── Artifact Schemas ─────────────────────────────────────────────────────────

@dataclass
class UserStory:
    """Single user story within a specification."""
    id: str
    title: str
    description: str
    acceptance_criteria: List[str]
    priority: str = "medium"  # low, medium, high, critical
    estimated_complexity: str = "medium"  # simple, medium, complex
    dependencies: List[str] = field(default_factory=list)


@dataclass
class NonFunctionalRequirement:
    """Non-functional requirement (performance, security, etc.)."""
    id: str
    category: str  # performance, security, scalability, reliability, usability
    description: str
    metric: str  # Measurable target
    priority: str = "medium"


@dataclass
class SpecificationDocument:
    """
    OUTPUT of PM Agent → INPUT for Architect Agent
    The PM produces this structured spec from user's raw request.
    """
    project_id: str
    version: str
    title: str
    summary: str
    user_stories: List[UserStory]
    non_functional_requirements: List[NonFunctionalRequirement]
    constraints: List[str]
    assumptions: List[str]
    out_of_scope: List[str]
    tech_stack_preferences: List[str] = field(default_factory=list)
    target_users: str = ""
    timeline: str = ""
    status: str = ArtifactStatus.DRAFT.value
    created_by: str = AgentRole.PM.value
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    review_notes: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return asdict(self)
    
    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)
    
    def to_markdown(self) -> str:
        lines = [
            f"# Specification: {self.title}",
            f"**Project:** {self.project_id} | **Version:** {self.version} | **Status:** {self.status}",
            f"**Created:** {self.created_at} by {self.created_by}",
            f"\n## Summary\n{self.summary}",
            f"\n## User Stories",
        ]
        for story in self.user_stories:
            lines.append(f"\n### {story.id}: {story.title}")
            lines.append(f"**Priority:** {story.priority} | **Complexity:** {story.estimated_complexity}")
            lines.append(f"\n{story.description}")
            lines.append(f"\n**Acceptance Criteria:**")
            for ac in story.acceptance_criteria:
                lines.append(f"- [ ] {ac}")
            if story.dependencies:
                lines.append(f"\n**Dependencies:** {', '.join(story.dependencies)}")
        
        if self.non_functional_requirements:
            lines.append(f"\n## Non-Functional Requirements")
            for nfr in self.non_functional_requirements:
                lines.append(f"- **{nfr.id} ({nfr.category}):** {nfr.description} — Target: {nfr.metric}")
        
        if self.constraints:
            lines.append(f"\n## Constraints")
            for c in self.constraints:
                lines.append(f"- {c}")
        
        if self.assumptions:
            lines.append(f"\n## Assumptions")
            for a in self.assumptions:
                lines.append(f"- {a}")
        
        if self.out_of_scope:
            lines.append(f"\n## Out of Scope")
            for o in self.out_of_scope:
                lines.append(f"- {o}")
        
        return "\n".join(lines)


@dataclass
class APIEndpoint:
    method: str  # GET, POST, PUT, DELETE
    path: str
    description: str
    request_body: Optional[Dict] = None
    response_schema: Optional[Dict] = None
    auth_required: bool = True


@dataclass 
class DatabaseTable:
    name: str
    description: str
    columns: List[Dict]  # [{name, type, nullable, description}]
    indexes: List[str] = field(default_factory=list)
    relationships: List[str] = field(default_factory=list)


@dataclass
class ArchitectureDesign:
    """
    OUTPUT of Architect Agent → INPUT for Developer Agent
    The Architect produces this from the PM's Specification.
    """
    project_id: str
    version: str
    spec_version: str  # Which spec version this design is based on
    architecture_pattern: str  # microservice, monolithic, serverless, etc.
    summary: str
    components: List[Dict]  # [{name, type, description, technology, responsibilities}]
    api_endpoints: List[APIEndpoint]
    database_schema: List[DatabaseTable]
    infrastructure: Dict  # IaC descriptions
    security_considerations: List[str]
    scalability_notes: List[str]
    deployment_strategy: str
    tech_stack: Dict  # {frontend, backend, database, infrastructure, ci_cd}
    component_diagram: str = ""  # Mermaid or text diagram
    data_flow: str = ""
    status: str = ArtifactStatus.DRAFT.value
    created_by: str = AgentRole.ARCHITECT.value
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    review_notes: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return asdict(self)
    
    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)


@dataclass
class ImplementationFile:
    path: str
    language: str
    description: str
    content: str
    tests_path: Optional[str] = None


@dataclass
class Implementation:
    """
    OUTPUT of Developer Agent → INPUT for QA Agent
    The Developer produces this from the Architect's Design.
    """
    project_id: str
    version: str
    design_version: str
    files: List[ImplementationFile]
    test_files: List[ImplementationFile]
    dependencies: Dict  # {package: version}
    build_commands: List[str]
    run_commands: List[str]
    environment_variables: List[str]
    notes: str = ""
    status: str = ArtifactStatus.DRAFT.value
    created_by: str = AgentRole.DEVELOPER.value
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    review_notes: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class TestResult:
    test_name: str
    status: str  # pass, fail, skip, error
    duration_ms: float = 0
    error_message: str = ""


@dataclass
class QAReport:
    """
    OUTPUT of QA Agent → Decision: Ship or Fix
    The QA agent produces this after testing the Implementation.
    """
    project_id: str
    version: str
    impl_version: str
    test_results: List[TestResult]
    total_tests: int
    passed: int
    failed: int
    skipped: int
    coverage_pct: float
    security_issues: List[str]
    performance_notes: List[str]
    recommendation: str  # "approve", "fix_required", "redesign_required"
    blocking_issues: List[str]
    non_blocking_issues: List[str]
    status: str = ArtifactStatus.DRAFT.value
    created_by: str = AgentRole.QA.value
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict:
        return asdict(self)


# ── Handoff Contract Definitions ─────────────────────────────────────────────

HANDOFF_CONTRACTS = {
    "user_to_pm": {
        "input": "Raw user request (natural language, any format)",
        "output": "SpecificationDocument",
        "agent": AgentRole.PM,
        "description": "PM takes raw user input and produces structured specification",
    },
    "pm_to_architect": {
        "input": "SpecificationDocument",
        "output": "ArchitectureDesign",
        "agent": AgentRole.ARCHITECT,
        "description": "Architect takes spec and produces system design with APIs, DB schema, and infrastructure",
    },
    "architect_to_developer": {
        "input": "ArchitectureDesign",
        "output": "Implementation",
        "agent": AgentRole.DEVELOPER,
        "description": "Developer takes design and produces working code with tests",
    },
    "developer_to_qa": {
        "input": "Implementation",
        "output": "QAReport",
        "agent": AgentRole.QA,
        "description": "QA takes implementation and produces test report with recommendation",
    },
    "qa_to_deploy": {
        "input": "QAReport (recommendation=approve)",
        "output": "Deployment artifact",
        "agent": AgentRole.DEVOPS,
        "description": "DevOps takes approved QA report and deploys to target environment",
    },
}


# ── Artifact Storage ─────────────────────────────────────────────────────────

class ArtifactStore:
    """Stores and retrieves versioned SDLC artifacts."""
    
    def __init__(self, base_path: str = None):
        self.base_path = Path(base_path or 
            str(Path.home() / ".openclaw" / "workspace" / "nexdev" / "projects"))
        self.base_path.mkdir(parents=True, exist_ok=True)
    
    def save_artifact(self, project_id: str, artifact_type: str, 
                      version: str, data: Dict) -> str:
        """Save an artifact and return its path."""
        project_dir = self.base_path / project_id / artifact_type
        project_dir.mkdir(parents=True, exist_ok=True)
        
        filepath = project_dir / f"v{version}.json"
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
        
        return str(filepath)
    
    def load_artifact(self, project_id: str, artifact_type: str,
                      version: str = None) -> Optional[Dict]:
        """Load an artifact. If no version specified, load latest."""
        project_dir = self.base_path / project_id / artifact_type
        
        if not project_dir.exists():
            return None
        
        if version:
            filepath = project_dir / f"v{version}.json"
        else:
            # Find latest version
            files = sorted(project_dir.glob("v*.json"))
            if not files:
                return None
            filepath = files[-1]
        
        with open(filepath) as f:
            return json.load(f)
    
    def list_projects(self) -> List[str]:
        """List all project IDs."""
        return [d.name for d in self.base_path.iterdir() if d.is_dir()]
    
    def list_artifacts(self, project_id: str) -> Dict[str, List[str]]:
        """List all artifacts and versions for a project."""
        project_dir = self.base_path / project_id
        if not project_dir.exists():
            return {}
        
        result = {}
        for artifact_dir in project_dir.iterdir():
            if artifact_dir.is_dir():
                versions = sorted([f.stem for f in artifact_dir.glob("v*.json")])
                result[artifact_dir.name] = versions
        return result


if __name__ == "__main__":
    print("NexDev SDLC Contracts — Agent Role Definitions")
    print("=" * 50)
    for name, contract in HANDOFF_CONTRACTS.items():
        print(f"\n{name}:")
        print(f"  Agent: {contract['agent'].value}")
        print(f"  Input: {contract['input']}")
        print(f"  Output: {contract['output']}")
        print(f"  Description: {contract['description']}")
