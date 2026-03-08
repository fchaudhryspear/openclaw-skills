#!/usr/bin/env python3
"""
NexDev Phase 1.3 — Architect Agent
====================================
Takes a SpecificationDocument and produces an ArchitectureDesign.
Proposes patterns, defines components, APIs, and database schema.
"""

import json
from typing import Dict, List, Optional
from datetime import datetime

from contracts import (
    SpecificationDocument, ArchitectureDesign, APIEndpoint, DatabaseTable,
    ArtifactStore, ArtifactStatus, AgentRole
)


# Architecture pattern selection criteria
PATTERN_CRITERIA = {
    "serverless": {
        "triggers": ["lambda", "serverless", "event-driven", "low traffic"],
        "features": ["api", "notifications", "file_upload"],
        "scale": "variable/bursty",
        "pros": ["Zero idle cost", "Auto-scaling", "Low ops overhead"],
        "cons": ["Cold starts", "Vendor lock-in", "Complex debugging"],
    },
    "microservices": {
        "triggers": ["microservice", "distributed", "10k+ users", "multiple teams"],
        "features": ["payments", "real_time", "search", "analytics"],
        "scale": "high",
        "pros": ["Independent scaling", "Tech flexibility", "Fault isolation"],
        "cons": ["Network complexity", "Data consistency", "Operational overhead"],
    },
    "monolithic": {
        "triggers": ["simple", "mvp", "small team", "quick"],
        "features": ["authentication", "user_management", "database"],
        "scale": "low-medium",
        "pros": ["Simple deployment", "Easy debugging", "Fast iteration"],
        "cons": ["Scaling limitations", "Tech debt accumulation", "Deploy everything"],
    },
    "modular_monolith": {
        "triggers": ["medium", "growing", "start simple"],
        "features": ["authentication", "api", "frontend", "database"],
        "scale": "medium",
        "pros": ["Simple like monolith", "Modular like microservices", "Easy to split later"],
        "cons": ["Requires discipline", "Single deploy unit", "Shared database"],
    },
}

# Tech stack recommendations by pattern
TECH_STACKS = {
    "serverless": {
        "frontend": ["Next.js", "React + Vite"],
        "backend": ["AWS Lambda + API Gateway", "Vercel Functions"],
        "database": ["DynamoDB", "Aurora Serverless", "PlanetScale"],
        "infrastructure": ["AWS CDK", "Serverless Framework", "SST"],
        "ci_cd": ["GitHub Actions", "AWS CodePipeline"],
    },
    "microservices": {
        "frontend": ["React", "Next.js"],
        "backend": ["Node.js (Express/Fastify)", "Python (FastAPI)", "Go"],
        "database": ["PostgreSQL", "MongoDB", "Redis (cache)"],
        "infrastructure": ["Docker + Kubernetes", "AWS ECS", "Terraform"],
        "ci_cd": ["GitHub Actions", "ArgoCD", "Jenkins"],
    },
    "monolithic": {
        "frontend": ["React", "Vue.js"],
        "backend": ["Node.js (Express)", "Python (Django/FastAPI)", "Ruby on Rails"],
        "database": ["PostgreSQL", "MySQL"],
        "infrastructure": ["Docker", "AWS EC2/ECS", "Heroku"],
        "ci_cd": ["GitHub Actions"],
    },
    "modular_monolith": {
        "frontend": ["React", "Next.js"],
        "backend": ["Node.js (NestJS)", "Python (Django)", ".NET"],
        "database": ["PostgreSQL"],
        "infrastructure": ["Docker", "AWS ECS"],
        "ci_cd": ["GitHub Actions"],
    },
}


class ArchitectAgent:
    """System Architect agent — transforms specs into architecture designs."""
    
    def __init__(self):
        self.store = ArtifactStore()
    
    def recommend_pattern(self, spec: SpecificationDocument) -> Dict:
        """Recommend an architecture pattern based on the spec."""
        scores = {}
        features = [s.title.lower().replace(" ", "_") for s in spec.user_stories]
        spec_text = (spec.summary + " " + " ".join(spec.constraints)).lower()
        
        for pattern, criteria in PATTERN_CRITERIA.items():
            score = 0
            reasons = []
            
            # Check triggers in spec text
            for trigger in criteria["triggers"]:
                if trigger in spec_text:
                    score += 2
                    reasons.append(f"Matched trigger: '{trigger}'")
            
            # Check feature overlap
            for feature in criteria["features"]:
                if any(feature in f for f in features):
                    score += 1
                    reasons.append(f"Supports feature: {feature}")
            
            # Check tech stack preferences
            for pref in spec.tech_stack_preferences:
                stacks = TECH_STACKS.get(pattern, {})
                for category_options in stacks.values():
                    if any(pref.lower() in opt.lower() for opt in category_options):
                        score += 1
                        reasons.append(f"Tech pref '{pref}' available")
            
            scores[pattern] = {"score": score, "reasons": reasons}
        
        # Sort by score
        ranked = sorted(scores.items(), key=lambda x: x[1]["score"], reverse=True)
        recommended = ranked[0][0]
        
        return {
            "recommended": recommended,
            "scores": {k: v["score"] for k, v in scores.items()},
            "reasoning": scores[recommended]["reasons"],
            "pros": PATTERN_CRITERIA[recommended]["pros"],
            "cons": PATTERN_CRITERIA[recommended]["cons"],
            "alternatives": [r[0] for r in ranked[1:3]],
        }
    
    def design(self, spec: SpecificationDocument, 
               pattern_override: str = None) -> ArchitectureDesign:
        """
        Generate an ArchitectureDesign from a SpecificationDocument.
        """
        # Step 1: Choose pattern
        recommendation = self.recommend_pattern(spec)
        pattern = pattern_override or recommendation["recommended"]
        
        # Step 2: Define tech stack
        tech_stack = self._select_tech_stack(pattern, spec.tech_stack_preferences)
        
        # Step 3: Define components
        components = self._define_components(spec, pattern)
        
        # Step 4: Define API endpoints
        endpoints = self._define_endpoints(spec)
        
        # Step 5: Define database schema
        tables = self._define_database(spec)
        
        # Step 6: Infrastructure
        infrastructure = self._define_infrastructure(pattern, tech_stack)
        
        # Step 7: Security considerations
        security = self._security_considerations(spec)
        
        # Step 8: Generate component diagram
        diagram = self._generate_diagram(components, pattern)
        
        design = ArchitectureDesign(
            project_id=spec.project_id,
            version="1",
            spec_version=spec.version,
            architecture_pattern=pattern,
            summary=f"{pattern.replace('_', ' ').title()} architecture for {spec.title}. "
                    f"Pattern chosen because: {'; '.join(recommendation['reasoning'][:3])}",
            components=components,
            api_endpoints=endpoints,
            database_schema=tables,
            infrastructure=infrastructure,
            security_considerations=security,
            scalability_notes=[
                f"Pattern supports {PATTERN_CRITERIA[pattern]['scale']} scale",
                "Horizontal scaling via container orchestration" if pattern != "serverless" 
                    else "Auto-scaling via serverless platform",
                "Database connection pooling recommended",
                "CDN for static assets",
            ],
            deployment_strategy="blue-green" if pattern in ["microservices", "modular_monolith"] else "rolling",
            tech_stack=tech_stack,
            component_diagram=diagram,
            status=ArtifactStatus.DRAFT.value,
        )
        
        # Save artifact
        self.store.save_artifact(spec.project_id, "design", "1", design.to_dict())
        
        return design
    
    def _select_tech_stack(self, pattern: str, preferences: List[str]) -> Dict:
        """Select tech stack, respecting user preferences."""
        stack_options = TECH_STACKS.get(pattern, TECH_STACKS["monolithic"])
        result = {}
        
        for category, options in stack_options.items():
            # Check if user has a preference for this category
            matched = None
            for pref in preferences:
                for opt in options:
                    if pref.lower() in opt.lower():
                        matched = opt
                        break
                if matched:
                    break
            
            result[category] = matched or options[0]
        
        return result
    
    def _define_components(self, spec: SpecificationDocument, pattern: str) -> List[Dict]:
        """Define system components based on spec and pattern."""
        components = []
        
        # Always have these core components
        components.append({
            "name": "API Gateway",
            "type": "infrastructure",
            "description": "Entry point for all API requests. Handles routing, rate limiting, and auth.",
            "technology": "nginx / AWS API Gateway",
            "responsibilities": ["Request routing", "Rate limiting", "Authentication", "CORS"],
        })
        
        # Feature-based components
        feature_components = {
            "authentication": {
                "name": "Auth Service",
                "type": "service",
                "description": "Handles user authentication, authorization, and session management.",
                "technology": "JWT + bcrypt",
                "responsibilities": ["User registration", "Login/logout", "Token management", "Password reset"],
            },
            "user_management": {
                "name": "User Service",
                "type": "service",
                "description": "Manages user profiles, roles, and permissions.",
                "technology": "REST API",
                "responsibilities": ["Profile CRUD", "Role management", "Permissions"],
            },
            "payments": {
                "name": "Payment Service",
                "type": "service",
                "description": "Handles payment processing, subscriptions, and billing.",
                "technology": "Stripe SDK",
                "responsibilities": ["Payment processing", "Subscription management", "Invoicing", "Webhooks"],
            },
            "notifications": {
                "name": "Notification Service",
                "type": "service",
                "description": "Manages sending notifications via email, SMS, and push.",
                "technology": "Event-driven (SQS/SNS or Redis pub/sub)",
                "responsibilities": ["Email sending", "Push notifications", "Notification preferences"],
            },
            "real_time": {
                "name": "WebSocket Service",
                "type": "service",
                "description": "Handles real-time communication via WebSocket connections.",
                "technology": "Socket.io / ws",
                "responsibilities": ["Connection management", "Event broadcasting", "Presence tracking"],
            },
            "search": {
                "name": "Search Service",
                "type": "service",
                "description": "Full-text search and filtering capability.",
                "technology": "Elasticsearch / PostgreSQL full-text",
                "responsibilities": ["Indexing", "Query processing", "Result ranking"],
            },
            "analytics": {
                "name": "Analytics Service",
                "type": "service",
                "description": "Collects, processes, and visualizes usage analytics.",
                "technology": "Time-series DB + aggregation",
                "responsibilities": ["Event collection", "Metric computation", "Dashboard data"],
            },
            "frontend": {
                "name": "Web Frontend",
                "type": "frontend",
                "description": "User-facing web application.",
                "technology": "React/Next.js",
                "responsibilities": ["UI rendering", "State management", "API integration"],
            },
        }
        
        for story in spec.user_stories:
            title_lower = story.title.lower().replace(" ", "_")
            for feature_key, component in feature_components.items():
                if feature_key in title_lower and component not in components:
                    components.append(component)
        
        # Always add a main application service if not microservices
        if pattern != "microservices":
            components.append({
                "name": "Application Service",
                "type": "service",
                "description": "Core business logic service.",
                "technology": "Node.js / Python",
                "responsibilities": ["Business logic", "Data validation", "Domain operations"],
            })
        
        # Database component
        components.append({
            "name": "Primary Database",
            "type": "database",
            "description": "Primary data store.",
            "technology": "PostgreSQL",
            "responsibilities": ["Data persistence", "ACID transactions", "Query optimization"],
        })
        
        return components
    
    def _define_endpoints(self, spec: SpecificationDocument) -> List[APIEndpoint]:
        """Generate API endpoint definitions from user stories."""
        endpoints = []
        
        for story in spec.user_stories:
            title_lower = story.title.lower()
            
            if "auth" in title_lower:
                endpoints.extend([
                    APIEndpoint("POST", "/api/auth/register", "Register a new user",
                               {"email": "string", "password": "string", "name": "string"},
                               {"user": "object", "token": "string"}),
                    APIEndpoint("POST", "/api/auth/login", "Authenticate user",
                               {"email": "string", "password": "string"},
                               {"token": "string", "user": "object"}),
                    APIEndpoint("POST", "/api/auth/logout", "Logout user"),
                    APIEndpoint("POST", "/api/auth/refresh", "Refresh auth token"),
                ])
            
            if "user" in title_lower or "profile" in title_lower:
                endpoints.extend([
                    APIEndpoint("GET", "/api/users/me", "Get current user profile"),
                    APIEndpoint("PUT", "/api/users/me", "Update current user profile",
                               {"name": "string", "email": "string"}),
                    APIEndpoint("GET", "/api/users", "List users (admin)"),
                    APIEndpoint("GET", "/api/users/:id", "Get user by ID"),
                ])
            
            if "payment" in title_lower:
                endpoints.extend([
                    APIEndpoint("POST", "/api/payments/intent", "Create payment intent",
                               {"amount": "number", "currency": "string"}),
                    APIEndpoint("GET", "/api/payments/history", "Get payment history"),
                    APIEndpoint("POST", "/api/subscriptions", "Create subscription"),
                    APIEndpoint("DELETE", "/api/subscriptions/:id", "Cancel subscription"),
                ])
            
            if "notification" in title_lower:
                endpoints.extend([
                    APIEndpoint("GET", "/api/notifications", "List notifications"),
                    APIEndpoint("PUT", "/api/notifications/:id/read", "Mark notification as read"),
                    APIEndpoint("PUT", "/api/notifications/preferences", "Update preferences",
                               {"email": "boolean", "push": "boolean"}),
                ])
        
        # Health check endpoint (always)
        endpoints.append(APIEndpoint("GET", "/api/health", "Health check endpoint", auth_required=False))
        
        return endpoints
    
    def _define_database(self, spec: SpecificationDocument) -> List[DatabaseTable]:
        """Generate database schema from spec."""
        tables = []
        
        # Users table (always needed)
        tables.append(DatabaseTable(
            name="users",
            description="User accounts",
            columns=[
                {"name": "id", "type": "UUID", "nullable": False, "description": "Primary key"},
                {"name": "email", "type": "VARCHAR(255)", "nullable": False, "description": "Unique email"},
                {"name": "password_hash", "type": "VARCHAR(255)", "nullable": False, "description": "Bcrypt hash"},
                {"name": "name", "type": "VARCHAR(255)", "nullable": True, "description": "Display name"},
                {"name": "role", "type": "VARCHAR(50)", "nullable": False, "description": "User role"},
                {"name": "created_at", "type": "TIMESTAMP", "nullable": False, "description": "Creation time"},
                {"name": "updated_at", "type": "TIMESTAMP", "nullable": False, "description": "Last update"},
            ],
            indexes=["UNIQUE(email)", "INDEX(role)"],
            relationships=[],
        ))
        
        return tables
    
    def _define_infrastructure(self, pattern: str, tech_stack: Dict) -> Dict:
        """Define infrastructure based on pattern."""
        return {
            "compute": tech_stack.get("backend", "Node.js"),
            "database": tech_stack.get("database", "PostgreSQL"),
            "infrastructure_as_code": tech_stack.get("infrastructure", "Docker"),
            "ci_cd": tech_stack.get("ci_cd", "GitHub Actions"),
            "monitoring": "CloudWatch / Datadog",
            "logging": "Structured JSON logs → CloudWatch / ELK",
            "secrets": "AWS Secrets Manager / .env (dev)",
        }
    
    def _security_considerations(self, spec: SpecificationDocument) -> List[str]:
        """Generate security considerations."""
        considerations = [
            "All passwords hashed with bcrypt (cost factor ≥ 12)",
            "JWT tokens with short expiry (15min access, 7d refresh)",
            "HTTPS enforced in production",
            "Input validation on all endpoints",
            "SQL injection prevention via parameterized queries",
            "XSS prevention via output encoding",
            "CORS configured for allowed origins only",
            "Rate limiting on authentication endpoints",
        ]
        
        if any("payment" in s.title.lower() for s in spec.user_stories):
            considerations.extend([
                "PCI DSS compliance for payment handling",
                "No raw card data stored — use Stripe tokens",
            ])
        
        return considerations
    
    def _generate_diagram(self, components: List[Dict], pattern: str) -> str:
        """Generate a text-based component diagram."""
        lines = [f"Architecture: {pattern.replace('_', ' ').title()}", "=" * 40]
        
        frontends = [c for c in components if c["type"] == "frontend"]
        services = [c for c in components if c["type"] == "service"]
        databases = [c for c in components if c["type"] == "database"]
        infra = [c for c in components if c["type"] == "infrastructure"]
        
        if frontends:
            lines.append("\n[Frontend Layer]")
            for c in frontends:
                lines.append(f"  └── {c['name']} ({c['technology']})")
        
        if infra:
            lines.append("\n[Infrastructure Layer]")
            for c in infra:
                lines.append(f"  └── {c['name']} ({c['technology']})")
        
        if services:
            lines.append("\n[Service Layer]")
            for c in services:
                lines.append(f"  └── {c['name']} ({c['technology']})")
        
        if databases:
            lines.append("\n[Data Layer]")
            for c in databases:
                lines.append(f"  └── {c['name']} ({c['technology']})")
        
        return "\n".join(lines)


if __name__ == "__main__":
    from pm_agent import PMAgent
    
    pm = PMAgent()
    spec = pm.generate_spec(
        "Build a SaaS platform for property maintenance. Tenants submit tickets, "
        "managers assign to contractors. Real-time notifications, dashboard, "
        "Stripe billing. React and Node.js. 10K users."
    )
    
    architect = ArchitectAgent()
    pattern_rec = architect.recommend_pattern(spec)
    print(f"Recommended pattern: {pattern_rec['recommended']}")
    print(f"Reasoning: {pattern_rec['reasoning']}")
    
    design = architect.design(spec)
    print(f"\nArchitecture: {design.architecture_pattern}")
    print(f"Components: {len(design.components)}")
    print(f"Endpoints: {len(design.api_endpoints)}")
    print(f"Tables: {len(design.database_schema)}")
    print(f"\n{design.component_diagram}")
