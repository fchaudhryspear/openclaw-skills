#!/usr/bin/env python3
"""
NexDev Phase 1.1 — Product Manager Agent
==========================================
Takes raw user requests and produces structured SpecificationDocuments.
Asks clarifying questions when requirements are vague.

This is the ENTRY POINT of the NexDev SDLC pipeline.
"""

import json
import re
from typing import Dict, List, Optional, Tuple
from datetime import datetime

from contracts import (
    SpecificationDocument, UserStory, NonFunctionalRequirement,
    ArtifactStore, ArtifactStatus, AgentRole
)


class PMAgent:
    """Product Manager agent — transforms raw requests into structured specs."""
    
    def __init__(self):
        self.store = ArtifactStore()
        self.project_counter = 0
    
    def analyze_request(self, raw_request: str) -> Dict:
        """
        Analyze a raw user request and identify what's clear vs. ambiguous.
        
        Returns analysis with:
        - detected_features: What we can extract
        - ambiguities: What needs clarification
        - suggested_questions: Questions to ask the user
        - completeness_score: 0-1 how complete the request is
        """
        analysis = {
            "raw_request": raw_request,
            "word_count": len(raw_request.split()),
            "detected_features": [],
            "detected_tech": [],
            "detected_constraints": [],
            "ambiguities": [],
            "suggested_questions": [],
            "completeness_score": 0.0,
        }
        
        request_lower = raw_request.lower()
        
        # Feature detection
        feature_patterns = {
            "authentication": r"(auth|login|sign[- ]?up|register|oauth|sso|jwt)",
            "user_management": r"(user|profile|account|role|permission|admin)",
            "api": r"(api|endpoint|rest|graphql|webhook)",
            "database": r"(database|db|storage|persist|sql|nosql|mongo|postgres)",
            "frontend": r"(frontend|ui|dashboard|page|component|react|vue|angular)",
            "payments": r"(payment|billing|stripe|subscription|charge|invoice)",
            "notifications": r"(notification|email|sms|push|alert|notify)",
            "search": r"(search|filter|sort|query|elasticsearch)",
            "file_upload": r"(upload|file|image|document|s3|storage)",
            "real_time": r"(real[- ]?time|websocket|socket|live|streaming)",
            "analytics": r"(analytics|dashboard|metrics|report|tracking)",
            "ci_cd": r"(ci/?cd|deploy|pipeline|docker|kubernetes|terraform)",
        }
        
        for feature, pattern in feature_patterns.items():
            if re.search(pattern, request_lower):
                analysis["detected_features"].append(feature)
        
        # Tech stack detection
        tech_patterns = {
            "React": r"\breact\b", "Vue": r"\bvue\b", "Angular": r"\bangular\b",
            "Node.js": r"\bnode\.?js?\b", "Python": r"\bpython\b", "Go": r"\bgo(lang)?\b",
            "PostgreSQL": r"\b(postgres|postgresql)\b", "MongoDB": r"\bmongo(db)?\b",
            "Redis": r"\bredis\b", "AWS": r"\baws\b", "Docker": r"\bdocker\b",
            "Kubernetes": r"\b(k8s|kubernetes)\b", "TypeScript": r"\btypescript\b",
            "Next.js": r"\bnext\.?js\b", "FastAPI": r"\bfastapi\b",
            "Lambda": r"\blambda\b", "Serverless": r"\bserverless\b",
        }
        
        for tech, pattern in tech_patterns.items():
            if re.search(pattern, request_lower):
                analysis["detected_tech"].append(tech)
        
        # Constraint detection
        constraint_patterns = {
            "scale": (r"(\d+[kmb]?\+?\s*(users?|requests?|transactions?|records?))", "Scale requirement detected"),
            "timeline": (r"(by|within|deadline|before)\s+\w+", "Timeline constraint detected"),
            "budget": (r"(budget|cost|cheap|affordable|free tier)", "Budget constraint detected"),
            "compliance": (r"(hipaa|gdpr|soc2|pci|compliance|regulated)", "Compliance requirement detected"),
        }
        
        for name, (pattern, desc) in constraint_patterns.items():
            match = re.search(pattern, request_lower)
            if match:
                analysis["detected_constraints"].append({
                    "type": name, "description": desc, "match": match.group(0)
                })
        
        # Identify ambiguities and generate questions
        completeness = 0
        checks = [
            (len(analysis["detected_features"]) > 0, 
             "What specific features do you need?", "features"),
            (len(analysis["detected_tech"]) > 0,
             "Do you have a preferred tech stack (frontend, backend, database)?", "tech_stack"),
            (any(c["type"] == "scale" for c in analysis["detected_constraints"]),
             "What's the expected scale? (users, requests/sec, data volume)", "scale"),
            (any(c["type"] == "timeline" for c in analysis["detected_constraints"]),
             "What's the timeline or deadline?", "timeline"),
            (len(raw_request.split()) > 30,
             "Can you describe the primary user flow in 2-3 sentences?", "user_flow"),
            ("target" in request_lower or "audience" in request_lower or "user" in request_lower,
             "Who are the target users? (internal team, consumers, B2B, etc.)", "target_users"),
            (any(c["type"] == "compliance" for c in analysis["detected_constraints"]),
             "Are there any compliance requirements (HIPAA, GDPR, SOC2, PCI)?", "compliance"),
        ]
        
        for is_present, question, aspect in checks:
            if is_present:
                completeness += 1.0 / len(checks)
            else:
                analysis["ambiguities"].append(aspect)
                analysis["suggested_questions"].append(question)
        
        analysis["completeness_score"] = round(min(1.0, completeness), 2)
        
        return analysis
    
    def generate_spec(self, raw_request: str, 
                      answers: Dict = None,
                      project_id: str = None) -> SpecificationDocument:
        """
        Generate a SpecificationDocument from a raw request.
        
        Args:
            raw_request: User's natural language request
            answers: Dict of answers to clarifying questions (optional)
            project_id: Override project ID (auto-generated if not provided)
        """
        analysis = self.analyze_request(raw_request)
        
        if not project_id:
            self.project_counter += 1
            project_id = f"PROJ-{datetime.now().strftime('%Y%m%d')}-{self.project_counter:03d}"
        
        # Generate user stories from detected features
        user_stories = []
        story_counter = 0
        
        for feature in analysis["detected_features"]:
            story_counter += 1
            story = self._generate_story(feature, story_counter, project_id, raw_request)
            user_stories.append(story)
        
        # If no features detected, create a generic story from the request
        if not user_stories:
            story_counter += 1
            user_stories.append(UserStory(
                id=f"{project_id}-US-{story_counter:03d}",
                title="Core Feature Implementation",
                description=f"As a user, I want {raw_request}",
                acceptance_criteria=[
                    "Feature works as described in the request",
                    "Error handling for edge cases",
                    "Basic input validation",
                ],
                priority="high",
                estimated_complexity="medium",
            ))
        
        # Generate NFRs
        nfrs = self._generate_nfrs(analysis, project_id)
        
        # Build constraints and assumptions
        constraints = [c["description"] + f": {c['match']}" 
                      for c in analysis["detected_constraints"]]
        if not constraints:
            constraints = ["Standard web application constraints apply"]
        
        assumptions = [
            "Modern browser support required",
            "Internet connectivity required",
            "Standard REST API patterns",
        ]
        
        if answers:
            # Incorporate user's answers
            if "tech_stack" in answers:
                analysis["detected_tech"].extend(
                    [t.strip() for t in str(answers["tech_stack"]).split(",")]
                )
            if "scale" in answers:
                constraints.append(f"Scale: {answers['scale']}")
            if "timeline" in answers:
                constraints.append(f"Timeline: {answers['timeline']}")
        
        spec = SpecificationDocument(
            project_id=project_id,
            version="1",
            title=self._extract_title(raw_request),
            summary=raw_request,
            user_stories=user_stories,
            non_functional_requirements=nfrs,
            constraints=constraints,
            assumptions=assumptions,
            out_of_scope=["Mobile native apps (unless specified)", 
                         "Legacy browser support (IE11)"],
            tech_stack_preferences=analysis["detected_tech"],
            target_users=answers.get("target_users", "End users") if answers else "End users",
            timeline=answers.get("timeline", "TBD") if answers else "TBD",
            status=ArtifactStatus.DRAFT.value,
        )
        
        # Save artifact
        self.store.save_artifact(project_id, "specs", "1", spec.to_dict())
        
        return spec
    
    def _extract_title(self, request: str) -> str:
        """Extract a concise title from the request."""
        # Take first sentence or first 60 chars
        first_sentence = request.split('.')[0].split('\n')[0]
        if len(first_sentence) > 60:
            return first_sentence[:57] + "..."
        return first_sentence
    
    def _generate_story(self, feature: str, counter: int, 
                        project_id: str, context: str) -> UserStory:
        """Generate a user story for a detected feature."""
        story_templates = {
            "authentication": {
                "title": "User Authentication",
                "description": "As a user, I want to securely log in and register so that my data is protected.",
                "criteria": [
                    "User can register with email/password",
                    "User can log in with valid credentials",
                    "Invalid credentials show appropriate error",
                    "Password is hashed and stored securely",
                    "Session management with secure tokens",
                ],
                "complexity": "medium",
            },
            "user_management": {
                "title": "User Profile Management",
                "description": "As a user, I want to manage my profile so I can keep my information up to date.",
                "criteria": [
                    "User can view their profile",
                    "User can update profile information",
                    "Profile changes are validated",
                    "Admin can manage user roles",
                ],
                "complexity": "simple",
            },
            "api": {
                "title": "RESTful API Endpoints",
                "description": "As a developer, I want well-documented API endpoints so I can integrate with the system.",
                "criteria": [
                    "API follows REST conventions",
                    "Proper HTTP status codes returned",
                    "Request/response validation",
                    "API documentation generated (OpenAPI/Swagger)",
                ],
                "complexity": "medium",
            },
            "database": {
                "title": "Data Persistence Layer",
                "description": "As the system, I need reliable data storage so that user data is safely persisted.",
                "criteria": [
                    "Database schema designed for the domain",
                    "Proper indexes for common queries",
                    "Migration scripts for schema changes",
                    "Backup and recovery procedures defined",
                ],
                "complexity": "medium",
            },
            "frontend": {
                "title": "User Interface",
                "description": "As a user, I want an intuitive interface so I can easily use the application.",
                "criteria": [
                    "Responsive design (mobile + desktop)",
                    "Accessible (WCAG 2.1 AA)",
                    "Consistent design system",
                    "Loading states and error handling",
                ],
                "complexity": "complex",
            },
            "payments": {
                "title": "Payment Processing",
                "description": "As a user, I want to make secure payments so I can purchase services.",
                "criteria": [
                    "Integration with payment provider (Stripe/etc.)",
                    "Secure handling of payment information",
                    "Transaction history viewable",
                    "Failed payment handling and retry",
                    "Receipt generation",
                ],
                "complexity": "complex",
            },
            "notifications": {
                "title": "Notification System",
                "description": "As a user, I want to receive notifications so I stay informed about important events.",
                "criteria": [
                    "Email notifications for key events",
                    "In-app notification center",
                    "Notification preferences configurable",
                    "Notification delivery is reliable",
                ],
                "complexity": "medium",
            },
            "search": {
                "title": "Search & Filtering",
                "description": "As a user, I want to search and filter content so I can find what I need quickly.",
                "criteria": [
                    "Full-text search capability",
                    "Filter by relevant attributes",
                    "Sort by multiple criteria",
                    "Search results are fast (<500ms)",
                ],
                "complexity": "medium",
            },
            "real_time": {
                "title": "Real-time Updates",
                "description": "As a user, I want real-time updates so I see changes without refreshing.",
                "criteria": [
                    "WebSocket connection for live updates",
                    "Graceful reconnection on disconnect",
                    "Efficient message broadcasting",
                    "State synchronization between clients",
                ],
                "complexity": "complex",
            },
            "analytics": {
                "title": "Analytics Dashboard",
                "description": "As an admin, I want analytics dashboards so I can understand usage patterns.",
                "criteria": [
                    "Key metrics visualized (charts/graphs)",
                    "Date range filtering",
                    "Export capability (CSV/PDF)",
                    "Real-time or near-real-time data",
                ],
                "complexity": "complex",
            },
        }
        
        template = story_templates.get(feature, {
            "title": feature.replace("_", " ").title(),
            "description": f"As a user, I want {feature.replace('_', ' ')} functionality.",
            "criteria": [f"{feature.replace('_', ' ').title()} works as expected"],
            "complexity": "medium",
        })
        
        return UserStory(
            id=f"{project_id}-US-{counter:03d}",
            title=template["title"],
            description=template["description"],
            acceptance_criteria=template["criteria"],
            priority="high" if feature in ["authentication", "database", "api"] else "medium",
            estimated_complexity=template["complexity"],
        )
    
    def _generate_nfrs(self, analysis: Dict, project_id: str) -> List[NonFunctionalRequirement]:
        """Generate non-functional requirements based on analysis."""
        nfrs = [
            NonFunctionalRequirement(
                id=f"{project_id}-NFR-001",
                category="performance",
                description="API response time under normal load",
                metric="p95 latency < 500ms",
                priority="high",
            ),
            NonFunctionalRequirement(
                id=f"{project_id}-NFR-002",
                category="security",
                description="Authentication and authorization",
                metric="OWASP Top 10 vulnerabilities addressed",
                priority="high",
            ),
            NonFunctionalRequirement(
                id=f"{project_id}-NFR-003",
                category="reliability",
                description="System availability",
                metric="99.9% uptime SLA",
                priority="medium",
            ),
        ]
        
        # Add scale-specific NFRs
        if any(c["type"] == "scale" for c in analysis["detected_constraints"]):
            nfrs.append(NonFunctionalRequirement(
                id=f"{project_id}-NFR-004",
                category="scalability",
                description="Horizontal scaling capability",
                metric="Auto-scale to handle 10x normal load",
                priority="high",
            ))
        
        # Add compliance NFRs
        if any(c["type"] == "compliance" for c in analysis["detected_constraints"]):
            nfrs.append(NonFunctionalRequirement(
                id=f"{project_id}-NFR-005",
                category="compliance",
                description="Regulatory compliance",
                metric="Pass compliance audit for applicable regulations",
                priority="critical",
            ))
        
        return nfrs


if __name__ == "__main__":
    pm = PMAgent()
    
    # Test with a real request
    request = """Build a SaaS platform for managing property maintenance requests. 
    Tenants should be able to submit maintenance tickets with photos, 
    property managers can assign them to contractors, and contractors 
    can update status. Need real-time notifications, a dashboard for 
    property managers, and Stripe for billing. Must handle 10K users. 
    Use React and Node.js."""
    
    # First analyze
    analysis = pm.analyze_request(request)
    print("=== Analysis ===")
    print(f"Completeness: {analysis['completeness_score']}")
    print(f"Features detected: {analysis['detected_features']}")
    print(f"Tech detected: {analysis['detected_tech']}")
    print(f"Ambiguities: {analysis['ambiguities']}")
    print(f"Questions:")
    for q in analysis['suggested_questions']:
        print(f"  ? {q}")
    
    # Generate spec
    spec = pm.generate_spec(request)
    print(f"\n=== Specification ===")
    print(spec.to_markdown()[:2000])
