#!/usr/bin/env python3
"""
NexDev Task Decomposition Engine (Phase 3 Feature)

Breaks down epics into user stories, then into actionable tasks with
estimates, dependencies, and assignment suggestions.
Part of NexDev v3.0 World-Class Build Team Upgrade
"""

import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta


@dataclass
class SubTask:
    """Represents a single subtask."""
    id: str
    title: str
    description: str
    estimated_hours: float
    priority: str  # "critical", "high", "medium", "low"
    dependencies: List[str]
    skills_required: List[str]
    assignee_suggestions: List[str]
    acceptance_criteria: List[str]


@dataclass
class UserStory:
    """Represents a user story."""
    id: str
    title: str
    description: str  # As a [role], I want [feature], so that [benefit]
    acceptance_criteria: List[str]
    story_points: int
    subtasks: List[SubTask]
    tags: List[str]
    
    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "acceptance_criteria": self.acceptance_criteria,
            "story_points": self.story_points,
            "subtasks": [asdict(t) for t in self.subtasks],
            "tags": self.tags
        }


@dataclass  
class Epic:
    """Represents an epic/project."""
    id: str
    title: str
    description: str
    timeline_weeks: int
    budget_usd: Optional[float]
    tech_stack: List[str]
    user_stories: List[UserStory]
    risks: List[Dict[str, Any]]
    
    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "timeline_weeks": self.timeline_weeks,
            "budget_usd": self.budget_usd,
            "tech_stack": self.tech_stack,
            "user_stories": [s.to_dict() for s in self.user_stories],
            "risks": self.risks,
            "total_story_points": sum(s.story_points for s in self.user_stories),
            "total_subtasks": sum(len(s.subtasks) for s in self.user_stories)
        }


# ──────────────────────────────────────────────────────────────────────────────
# Decomposition Templates (Pattern-Based)
# ──────────────────────────────────────────────────────────────────────────────

DECOMPOSITION_TEMPLATES = {
    "authentication_service": {
        "name": "Authentication & Authorization System",
        "default_stories": [
            {
                "template_id": "user_registration",
                "title": "User Registration",
                "description": "As a new user, I want to create an account so that I can access the system",
                "estimate_points": 5,
                "subtasks": [
                    {"title": "Design user data model", "hours": 4},
                    {"title": "Implement registration API endpoint", "hours": 8},
                    {"title": "Add email validation", "hours": 6},
                    {"title": "Implement password hashing", "hours": 4},
                    {"title": "Create unit tests", "hours": 6}
                ]
            },
            {
                "template_id": "login_system",
                "title": "Login System",
                "description": "As a registered user, I want to log in so that I can access my account",
                "estimate_points": 3,
                "subtasks": [
                    {"title": "Implement login API endpoint", "hours": 6},
                    {"title": "Add JWT token generation", "hours": 4},
                    {"title": "Implement refresh token logic", "hours": 4},
                    {"title": "Create rate limiting", "hours": 3}
                ]
            },
            {
                "template_id": "password_reset",
                "title": "Password Reset",
                "description": "As a user who forgot their password, I want to reset it so that I can regain access",
                "estimate_points": 3,
                "subtasks": [
                    {"title": "Generate password reset token", "hours": 4},
                    {"title": "Send email with reset link", "hours": 4},
                    {"title": "Implement reset form API", "hours": 4},
                    {"title": "Add token expiration logic", "hours": 3}
                ]
            }
        ],
        "tech_stack": ["OAuth 2.0", "JWT", "Redis", "PostgreSQL"],
        "typical_risks": [
            {"risk": "Security vulnerabilities", "mitigation": "Code review + security scan"},
            {"risk": "Token leakage", "mitigation": "Proper storage + HTTPS only"}
        ]
    },
    
    "api_gateway": {
        "name": "API Gateway Setup",
        "default_stories": [
            {
                "template_id": "gateway_setup",
                "title": "API Gateway Configuration",
                "description": "As a developer, I want centralized request routing so that I can manage traffic efficiently",
                "estimate_points": 8,
                "subtasks": [
                    {"title": "Select gateway technology", "hours": 4},
                    {"title": "Configure routing rules", "hours": 6},
                    {"title": "Set up rate limiting", "hours": 4},
                    {"title": "Implement authentication middleware", "hours": 6},
                    {"title": "Add logging/monitoring", "hours": 4}
                ]
            },
            {
                "template_id": "circuit_breaker",
                "title": "Circuit Breaker Pattern",
                "description": "As a system architect, I want fault tolerance so that failures don't cascade",
                "estimate_points": 5,
                "subtasks": [
                    {"title": "Implement circuit breaker", "hours": 6},
                    {"title": "Configure fallback responses", "hours": 4},
                    {"title": "Add health checks", "hours": 4}
                ]
            }
        ],
        "tech_stack": ["Kong", "nginx", "Redis", "Prometheus"],
        "typical_risks": [
            {"risk": "Single point of failure", "mitigation": "Redundant instances"},
            {"risk": "Performance bottleneck", "mitigation": "Load testing + auto-scaling"}
        ]
    },
    
    "microservice": {
        "name": "Microservice Development",
        "default_stories": [
            {
                "template_id": "service_bootstrap",
                "title": "Service Bootstrap",
                "description": "As a developer, I want a working microservice template so that I can build features quickly",
                "estimate_points": 3,
                "subtasks": [
                    {"title": "Create project structure", "hours": 4},
                    {"title": "Set up Docker containerization", "hours": 4},
                    {"title": "Configure CI/CD pipeline", "hours": 6},
                    {"title": "Add health check endpoint", "hours": 2}
                ]
            },
            {
                "template_id": "database_integration",
                "title": "Database Integration",
                "description": "As the service, I need database connectivity so that I can persist data",
                "estimate_points": 5,
                "subtasks": [
                    {"title": "Design database schema", "hours": 4},
                    {"title": "Implement repository pattern", "hours": 6},
                    {"title": "Add migration scripts", "hours": 4},
                    {"title": "Configure connection pooling", "hours": 3}
                ]
            }
        ],
        "tech_stack": ["FastAPI/Express", "PostgreSQL/MongoDB", "Docker", "Kubernetes"],
        "typical_risks": [
            {"risk": "Data consistency", "mitigation": "Transaction management"},
            {"risk": "Inter-service communication", "mitigation": "Message queue + retries"}
        ]
    }
}


# ──────────────────────────────────────────────────────────────────────────────
# Decomposition Logic
# ──────────────────────────────────────────────────────────────────────────────

def detect_epic_type(requirements: str, tech_stack: List[str]) -> str:
    """Detect what type of epic this is based on requirements and stack."""
    req_lower = requirements.lower()
    
    if any(kw in req_lower for kw in ["authenticat", "oauth", "jwt", "login", "password"]):
        return "authentication_service"
    elif any(kw in req_lower for kw in ["gateway", "routing", "rate limit", "circuit break"]):
        return "api_gateway"

        return "microservice"
    
    # Check tech stack hints
    if "postgres" in tech_stack or "mongo" in tech_stack:
        return "microservice"
    
    return "custom"  # Generic decomposition


def estimate_story_complexity(story: Dict[str, Any]) -> int:
    """Estimate story points based on subtask count and hours."""
    total_hours = sum(t.get("hours", 4) for t in story.get("subtasks", []))
    
    # Rough estimation: 8 hours = 1 day, factor in complexity
    if total_hours < 16:
        return 2  # Small
    elif total_hours < 32:
        return 3  # Medium
    elif total_hours < 48:
        return 5  # Large
    else:
        return 8  # Very large (should be split)


def decompose_epic(
    title: str,
    description: str,
    tech_stack: List[str],
    requirements: Optional[str] = None,
    constraints: Optional[Dict[str, Any]] = None
) -> Epic:
    """
    Decompose an epic into user stories and subtasks.
    
    Args:
        title: Epic title
        description: Epic description
        tech_stack: Technology stack being used
        requirements: Additional requirements text
        constraints: Timeline, budget constraints
        
    Returns:
        Epic object with full decomposition
    """
    # Detect epic type
    epic_type = detect_epic_type(requirements or description, tech_stack)
    
    # Get template or create custom
    if epic_type in DECOMPOSITION_TEMPLATES:
        template = DECOMPOSITION_TEMPLATES[epic_type]
        default_stories = template["default_stories"]
        default_risks = template["typical_risks"]
    else:
        # Generate generic decomposition
        default_stories = _generate_generic_stories(description)
        default_risks = [
            {"risk": "Scope creep", "mitigation": "Clear requirement documentation"},
            {"risk": "Technical debt", "mitigation": "Regular refactoring sprints"}
        ]
    
    # Create user stories from template
    user_stories = []
    for i, story_template in enumerate(default_stories, 1):
        story_id = f"{title.replace(' ', '-').lower()}-{i}"
        
        subtasks = []
        for j, task_data in enumerate(story_template.get("subtasks", []), 1):
            task_id = f"{story_id}-t{j}"
            
            subtasks.append(SubTask(
                id=task_id,
                title=task_data["title"],
                description=f"Implementation details for {task_data['title']}",
                estimated_hours=task_data.get("hours", 4),
                priority="medium",
                dependencies=[],
                skills_required=["development"],
                assignee_suggestions=[],
                acceptance_criteria=[f"{task_data['title']} implemented and tested"]
            ))
        
        user_stories.append(UserStory(
            id=story_id,
            title=story_template["title"],
            description=story_template["description"],
            acceptance_criteria=[
                f"All subtasks completed",
                f"Code reviewed and merged",
                f"Tests passing"
            ],
            story_points=estimate_story_complexity(story_template),
            subtasks=subtasks,
            tags=[]
        ))
    
    # Calculate timeline
    total_hours = sum(sum(t.estimated_hours for t in s.subtasks) for s in user_stories)
    weeks_needed = max((total_hours / 40) // 40, 1)  # Assuming 40hr weeks
    
    return Epic(
        id=title.replace(" ", "-").lower(),
        title=title,
        description=description,
        timeline_weeks=int(constraints.get("timeline_weeks", weeks_needed)),
        budget_usd=constraints.get("budget_usd"),
        tech_stack=tech_stack,
        user_stories=user_stories,
        risks=default_risks
    )


def _generate_generic_stories(description: str) -> List[Dict[str, Any]]:
    """Generate generic user stories when no template matches."""
    return [
        {
            "template_id": "foundation",
            "title": "Project Foundation",
            "description": f"As a developer, I want proper project setup so that development can proceed smoothly",
            "estimate_points": 3,
            "subtasks": [
                {"title": "Create project structure", "hours": 4},
                {"title": "Setup CI/CD pipeline", "hours": 6},
                {"title": "Configure linting/testing", "hours": 4}
            ]
        },
        {
            "template_id": "core_feature",
            "title": "Core Feature Implementation",
            "description": "As a user, I want the main feature so that I can achieve my goal",
            "estimate_points": 8,
            "subtasks": [
                {"title": "Design architecture", "hours": 8},
                {"title": "Implement core logic", "hours": 16},
                {"title": "Add integration tests", "hours": 8}
            ]
        },
        {
            "template_id": "documentation",
            "title": "Documentation",
            "description": "As a maintainer, I want documentation so that others can use/maintain the system",
            "estimate_points": 3,
            "subtasks": [
                {"title": "Write README", "hours": 4},
                {"title": "Document APIs", "hours": 4},
                {"title": "Create deployment guide", "hours": 4}
            ]
        }
    ]


def generate_project_timeline(epic: Epic, sprint_length_days: int = 14) -> Dict[str, Any]:
    """
    Generate project timeline with sprint breakdown.
    
    Args:
        epic: Decomposed epic
        sprint_length_days: Sprint length in days (default 14)
        
    Returns:
        Dictionary with sprint-by-sprint plan
    """
    sprints = []
    current_week = 1
    
    for story in epic.user_stories:
        story_hours = sum(t.estimated_hours for t in story.subtasks)
        story_weeks = max((story_hours / 40), 0.5)  # Assume 40hr week per dev
        sprint_num = int(current_week / 7 * 2) + 1  # Approx sprint number
        
        sprints.append({
            "sprint_number": sprint_num,
            "story": story.title,
            "story_points": story.story_points,
            "estimated_completion": f"Week {int(current_week)}",
            "subtask_count": len(story.subtasks)
        })
        
        current_week += story_weeks
    
    return {
        "epic_id": epic.id,
        "total_story_points": sum(s.story_points for s in epic.user_stories),
        "total_subtasks": sum(len(s.subtasks) for s in epic.user_stories),
        "estimated_weeks": epic.timeline_weeks,
        "estimated_sprints": len(sprints),
        "sprints": sprints
    }


def export_to_jira_format(epic: Epic) -> List[Dict[str, Any]]:
    """Export decomposition to Jira-compatible format."""
    jira_items = []
    
    # Create epic
    jira_items.append({
        "summary": epic.title,
        "description": epic.description,
        "issuetype": "Epic",
        "labels": epic.tech_stack
    })
    
    # Create stories
    for story in epic.user_stories:
        jira_items.append({
            "summary": story.title,
            "description": story.description,
            "issuetype": "Story",
            "parent": {"key": epic.id.upper()},
            "labels": story.tags,
            "points": story.story_points
        })
        
        # Create subtasks
        for task in story.subtasks:
            jira_items.append({
                "summary": task.title,
                "description": task.description,
                "issuetype": "Sub-task",
                "parent": {"key": story.id},
                "timeworked": f"{task.estimated_hours}h"
            })
    
    return jira_items


if __name__ == "__main__":
    # Demo mode
    print("=" * 60)
    print("🗂️  NEXDEV TASK DECOMPOSITION - DEMO")
    print("=" * 60)
    
    # Test with authentication epic
    epic_result = decompose_epic(
        title="OAuth Authentication Service",
        description="Build a complete authentication system with OAuth 2.0, JWT tokens, and password management",
        tech_stack=["Python", "PostgreSQL", "Redis", "OAuth 2.0"],
        requirements="Need user registration, login, password reset, role-based access control",
        constraints={
            "timeline_weeks": 6,
            "budget_usd": 25000
        }
    )
    
    print(f"\n✅ Epic: {epic_result.title}")
    print(f"   Tech Stack: {', '.join(epic_result.tech_stack)}")
    print(f"   Timeline: {epic_result.timeline_weeks} weeks")
    print(f"   Budget: ${epic_result.budget_usd:,}")
    
    print(f"\n📊 Decomposition Summary:")
    print(f"   Total Stories: {len(epic_result.user_stories)}")
    print(f"   Total Story Points: {epic_result.to_dict()['total_story_points']}")
    print(f"   Total Subtasks: {epic_result.to_dict()['total_subtasks']}")
    
    # Show first story
    if epic_result.user_stories:
        first_story = epic_result.user_stories[0]
        print(f"\n📖 Sample Story: {first_story.title}")
        print(f"   Description: {first_story.description}")
        print(f"   Story Points: {first_story.story_points}")
        print(f"   Subtasks ({len(first_story.subtasks)}):")
        for task in first_story.subtasks[:3]:
            print(f"      • {task.title} ({task.estimated_hours}h)")
    
    # Timeline
    timeline = generate_project_timeline(epic_result)
    print(f"\n📅 Project Timeline:")
    print(f"   Estimated Sprints: {timeline['estimated_sprints']}")
    print(f"   First 3 sprints:")
    for sprint in timeline['sprints'][:3]:
        print(f"      Sprint {sprint['sprint_number']}: {sprint['story']} ({sprint['story_points']}pts)")
    
    print("\n" + "=" * 60)
    print("Demo complete!")
