#!/usr/bin/env python3
"""
NexDev Agent Engine — LLM-powered SDLC agents with MO routing.

Each pipeline stage can optionally use an LLM to produce richer output.
Model selection follows MO tiers: cheap models for simple tasks,
premium models for architecture/security decisions.

This sits between pipeline.py and engine.py, providing a unified
interface for all agents to call LLMs with appropriate model routing.
"""

import json
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional, List

# Add engine to path
NEXDEV_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(NEXDEV_DIR))

from engine import execute, execute_with_escalation, load_api_key

# ── Agent-to-Model Mapping (MO-integrated) ────────────────────────────────────
# Each agent role maps to a model tier based on task complexity.
# Cheap models handle extraction/formatting; expensive ones handle reasoning.

AGENT_MODELS = {
    # Tier 1: Simple extraction & formatting ($0.05-0.10/1M)
    "product_manager": {
        "primary": "alibaba-sg/qwen-turbo",
        "task": "Extract requirements, generate user stories from natural language",
        "escalation": ["google/gemini-2.5-flash", "alibaba-sg/qwen-coder"],
    },
    
    # Tier 2: Code generation ($0.10-0.30/1M)
    "developer": {
        "primary": "alibaba-sg/qwen-coder",
        "task": "Generate implementation code from architecture specs",
        "escalation": ["alibaba-sg/qwen3.5-122b-a10b", "anthropic/claude-sonnet-4-6"],
    },
    "test_engineer": {
        "primary": "alibaba-sg/qwen-coder",
        "task": "Generate test suites, unit tests, integration tests",
        "escalation": ["alibaba-sg/qwen3.5-122b-a10b"],
    },
    "qa_engineer": {
        "primary": "google/gemini-2.5-flash",
        "task": "Analyze code quality, review test coverage, produce QA reports",
        "escalation": ["alibaba-sg/qwen3.5-122b-a10b"],
    },
    
    # Tier 3: Design & reasoning ($0.40-0.60/1M)
    "architect": {
        "primary": "alibaba-sg/qwen3.5-122b-a10b",
        "task": "Design system architecture, component layout, API contracts",
        "escalation": ["anthropic/claude-sonnet-4-6"],
    },
    "devops": {
        "primary": "google/gemini-2.5-flash",
        "task": "Generate CI/CD pipelines, Dockerfiles, deploy configs",
        "escalation": ["alibaba-sg/qwen3.5-122b-a10b"],
    },
    
    # Tier 5: Critical reasoning ($3-5/1M) — only when escalated
    "security": {
        "primary": "alibaba-sg/qwen3.5-122b-a10b",
        "task": "Security audit, threat modeling, vulnerability analysis",
        "escalation": ["anthropic/claude-sonnet-4-6"],
    },
    "performance": {
        "primary": "google/gemini-2.5-flash",
        "task": "Performance analysis, bottleneck detection, optimization suggestions",
        "escalation": ["alibaba-sg/qwen3.5-122b-a10b"],
    },

    # ── NEW HIGH-VALUE AGENTS ──────────────────────────────────────────────────
    
    # Frontend Development
    "frontend_developer": {
        "primary": "alibaba-sg/qwen-coder",
        "task": "Generate React/Vue/Angular components, pages, and UI implementations",
        "escalation": ["alibaba-sg/qwen3.5-122b-a10b", "anthropic/claude-sonnet-4-6"],
    },
    "ui_designer": {
        "primary": "google/gemini-2.5-flash",
        "task": "Design system specs, component libraries, style guides, Tailwind configs",
        "escalation": ["alibaba-sg/qwen3.5-122b-a10b"],
    },
    "ux_researcher": {
        "primary": "google/gemini-2.5-flash",
        "task": "User persona analysis, journey mapping, usability heuristics, story validation",
        "escalation": ["alibaba-sg/qwen3.5-122b-a10b"],
    },
    
    # Mobile
    "mobile_developer": {
        "primary": "alibaba-sg/qwen-coder",
        "task": "React Native/Flutter/Swift/Kotlin mobile app generation",
        "escalation": ["alibaba-sg/qwen3.5-122b-a10b", "anthropic/claude-sonnet-4-6"],
    },
    
    # AI/ML
    "ai_engineer": {
        "primary": "alibaba-sg/qwen3.5-122b-a10b",
        "task": "ML pipeline scaffolding, model integration, data pipeline design",
        "escalation": ["anthropic/claude-sonnet-4-6"],
    },
    
    # Rapid Prototyping
    "rapid_prototyper": {
        "primary": "alibaba-sg/qwen-turbo",
        "task": "Fast MVP generation, skip reviews, minimal viable code",
        "escalation": ["alibaba-sg/qwen-coder"],
    },
    
    # Testing Specialists
    "api_tester": {
        "primary": "alibaba-sg/qwen-coder",
        "task": "HTTP endpoint testing, integration tests, API contract validation",
        "escalation": ["alibaba-sg/qwen3.5-122b-a10b"],
    },
    "accessibility_auditor": {
        "primary": "google/gemini-2.5-flash",
        "task": "WCAG 2.2 compliance audit, ARIA validation, keyboard nav testing",
        "escalation": ["alibaba-sg/qwen3.5-122b-a10b"],
    },
    
    # Product & Project Management
    "sprint_prioritizer": {
        "primary": "alibaba-sg/qwen-turbo",
        "task": "Backlog prioritization, sprint planning, effort estimation",
        "escalation": ["google/gemini-2.5-flash"],
    },
    "feedback_synthesizer": {
        "primary": "google/gemini-2.5-flash",
        "task": "Aggregate user feedback, extract themes, prioritize improvements",
        "escalation": ["alibaba-sg/qwen3.5-122b-a10b"],
    },
    "senior_project_manager": {
        "primary": "alibaba-sg/qwen-turbo",
        "task": "Spec-to-task conversion, scope management, timeline estimation",
        "escalation": ["google/gemini-2.5-flash"],
    },
    
    # Support & Compliance
    "analytics_reporter": {
        "primary": "google/gemini-2.5-flash",
        "task": "Dashboard generation, KPI tracking, data visualization specs",
        "escalation": ["alibaba-sg/qwen3.5-122b-a10b"],
    },
    "legal_compliance": {
        "primary": "alibaba-sg/qwen3.5-122b-a10b",
        "task": "Regulatory compliance checking, GDPR/HIPAA/SOC2 code review",
        "escalation": ["anthropic/claude-sonnet-4-6"],
    },
    "identity_trust_architect": {
        "primary": "anthropic/claude-sonnet-4-6",
        "task": "Agent identity systems, auth architecture, audit trail design",
        "escalation": ["anthropic/claude-opus-4-6"],
    },
}


class AgentLLM:
    """Provides LLM capability to any SDLC agent."""
    
    def __init__(self, agent_role: str, project_id: str = None):
        self.role = agent_role
        self.project_id = project_id
        self.config = AGENT_MODELS.get(agent_role, AGENT_MODELS["developer"])
        self.call_log = []
    
    def ask(self, prompt: str, system_prompt: str = None, 
            max_tokens: int = 4096, temperature: float = 0.2) -> Dict:
        """
        Ask the LLM a question using the agent's assigned model.
        Returns dict with text, model, cost, etc.
        """
        model = self.config["primary"]
        
        # Build the full prompt with system context
        if system_prompt:
            full_prompt = f"System: {system_prompt}\n\nUser: {prompt}"
        else:
            full_prompt = prompt
        
        # Execute with escalation support
        routing = {
            "model": model,
            "escalation_chain": self.config["escalation"],
        }
        
        result = execute_with_escalation(
            routing, full_prompt,
            system_prompt=system_prompt or "",
            max_tokens=max_tokens,
            temperature=temperature,
        )
        
        # Log the call
        self.call_log.append({
            "timestamp": datetime.now().isoformat(),
            "agent": self.role,
            "project": self.project_id,
            "model": result.get("model", model),
            "escalated": result.get("escalated", False),
            "cost_usd": result.get("cost_usd", 0),
            "duration_ms": result.get("duration_ms", 0),
            "success": result.get("success", False),
            "tokens": result.get("input_tokens", 0) + result.get("output_tokens", 0),
        })
        
        return result
    
    def ask_json(self, prompt: str, system_prompt: str = None) -> Dict:
        """Ask the LLM and parse the response as JSON."""
        json_prompt = prompt + "\n\nRespond with valid JSON only. No markdown, no explanation."
        result = self.ask(json_prompt, system_prompt)
        
        if not result.get("success"):
            return {"error": result.get("text", "LLM call failed"), "raw": result}
        
        text = result["text"].strip()
        # Strip markdown code fences if present
        if text.startswith("```"):
            text = text.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
        
        try:
            parsed = json.loads(text)
            return {"data": parsed, "model": result["model"], "cost": result["cost_usd"]}
        except json.JSONDecodeError:
            return {"error": "Failed to parse JSON", "raw_text": text, "model": result["model"]}
    
    def get_cost_summary(self) -> Dict:
        """Get cost summary for all calls made by this agent."""
        total_cost = sum(c["cost_usd"] for c in self.call_log)
        total_tokens = sum(c["tokens"] for c in self.call_log)
        return {
            "agent": self.role,
            "total_calls": len(self.call_log),
            "total_cost_usd": round(total_cost, 6),
            "total_tokens": total_tokens,
            "models_used": list(set(c["model"] for c in self.call_log)),
            "escalations": sum(1 for c in self.call_log if c["escalated"]),
        }


# ── Prompt Templates for Each Agent ──────────────────────────────────────────

PM_SYSTEM = """You are a senior Product Manager. Given a user request, produce a structured specification.
Output JSON with: title, summary, user_stories (array of {id, title, description, acceptance_criteria, priority}),
non_functional_requirements (array of {category, requirement, priority}),
constraints, assumptions, out_of_scope, tech_stack_preferences."""

ARCHITECT_SYSTEM = """You are a senior Software Architect. Given a specification, produce a system design.
Output JSON with: architecture_pattern, summary, components (array of {name, type, responsibility, technology, interfaces}),
api_endpoints (array of {method, path, description, request_body, response_body}),
database_schema (array of {table, columns (array of {name, type, constraints}), indexes}),
tech_stack (object with backend, frontend, database, cache, queue keys),
deployment_strategy, security_considerations, scalability_notes."""

DEVELOPER_SYSTEM = """You are a senior Full-Stack Developer. Given an architecture design, generate production-ready code.
Output JSON with: files (array of {path, language, description, content}),
test_files (array of same format), dependencies (object),
build_commands (array), run_commands (array), environment_variables (array).
Write real, working code — not stubs or placeholders."""

QA_SYSTEM = """You are a senior QA Engineer. Given implementation code, analyze quality and produce a test report.
Output JSON with: test_results (array of {name, status, duration_ms, details}),
coverage_pct (number), security_issues (array), performance_notes (array),
recommendation (one of: ship_it, fix_required, major_rework),
blocking_issues (array), non_blocking_issues (array)."""

SECURITY_SYSTEM = """You are a senior Security Engineer. Analyze code for vulnerabilities.
Output JSON with: severity (critical/high/medium/low), vulnerabilities (array of {type, location, description, fix}),
threat_model (array of {threat, impact, likelihood, mitigation}),
owasp_compliance (object mapping OWASP top 10 to pass/fail with notes)."""


FRONTEND_SYSTEM = """You are a senior Frontend Developer specializing in React, Vue, and modern web frameworks.
Given a design spec or architecture, generate production-ready frontend code.
Output JSON with: files (array of {path, language, description, content}),
dependencies (object of package.json deps), scripts (object of npm scripts).
Include: components, pages, routing, state management, API integration, responsive CSS/Tailwind.
Write real JSX/TSX with proper hooks, error boundaries, and accessibility attributes."""

UI_DESIGN_SYSTEM = """You are a senior UI Designer. Create design system specifications.
Output JSON with: design_tokens ({colors, typography, spacing, breakpoints}),
components (array of {name, variants, props, usage_examples}),
layout_system ({grid, containers, responsive_rules}),
tailwind_config (tailwind.config.js content as string),
style_guide (markdown string with usage guidelines)."""

UX_RESEARCH_SYSTEM = """You are a senior UX Researcher. Analyze user needs and validate requirements.
Output JSON with: personas (array of {name, demographics, goals, pain_points, scenarios}),
user_journeys (array of {persona, steps (array of {action, touchpoint, emotion, opportunity})}),
usability_heuristics (array of {heuristic, assessment, severity, recommendation}),
research_findings (array of {finding, evidence, impact, priority}),
recommendations (array of actionable improvements)."""

MOBILE_SYSTEM = """You are a senior Mobile Developer specializing in React Native and Flutter.
Given a spec, generate cross-platform mobile app code.
Output JSON with: files (array of {path, language, description, content}),
platform (react_native|flutter), dependencies (object),
screens (array of screen names), navigation_type (stack|tab|drawer).
Include: screens, navigation, API integration, local storage, push notification setup."""

AI_ENGINEER_SYSTEM = """You are a senior AI/ML Engineer. Design ML pipelines and AI integrations.
Output JSON with: pipeline_stages (array of {name, type, description, config}),
model_spec ({framework, architecture, input_schema, output_schema}),
data_pipeline ({sources, transformations, validation_rules}),
deployment ({serving_method, scaling, monitoring}),
files (array of {path, language, description, content}) with actual Python/config code."""

RAPID_PROTO_SYSTEM = """You are a Rapid Prototyper. Generate minimal viable implementations FAST.
Skip perfectionism. No over-engineering. Get something working in the fewest files possible.
Output JSON with: files (array of {path, language, description, content}),
run_command (string to start the app), dependencies (minimal list).
Prefer: single-file apps, SQLite over Postgres, Flask over FastAPI, minimal deps.
Goal: working demo in <5 files."""

API_TESTER_SYSTEM = """You are a senior API Tester. Generate comprehensive API test suites.
Output JSON with: test_suites (array of {name, base_url, tests (array of {
  name, method, path, headers, body, expected_status, expected_body_contains,
  assertions (array of {field, operator, value})})}),
setup_script (string: Python/JS code for test data setup),
environment_vars (array of required env vars),
performance_thresholds ({p95_ms, max_error_rate_pct, min_throughput_rps}).
Include: auth flow tests, CRUD tests, edge cases, error handling, rate limit tests."""

ACCESSIBILITY_SYSTEM = """You are a senior Accessibility Auditor. Audit code for WCAG 2.2 AA compliance.
Output JSON with: audit_results (array of {criterion, level (A|AA|AAA), status (pass|fail|warning),
element, issue, remediation, severity (critical|major|minor)}),
summary ({total_issues, critical, major, minor, compliance_score}),
keyboard_nav ({issues (array), tab_order_correct (bool)}),
aria_audit ({issues (array), missing_labels (array), incorrect_roles (array)}),
recommendations (array of prioritized fixes)."""

SPRINT_SYSTEM = """You are a senior Sprint Prioritizer. Analyze a backlog and prioritize for the next sprint.
Output JSON with: sprint_plan ({goal, duration_days, capacity_points}),
prioritized_items (array of {id, title, priority (P0-P3), story_points, assignee_role,
  dependencies, rationale}),
deferred (array of {id, title, reason}),
risks (array of {risk, mitigation, probability}),
velocity_estimate (number)."""

FEEDBACK_SYSTEM = """You are a senior Feedback Synthesizer. Analyze user feedback and extract insights.
Output JSON with: themes (array of {theme, frequency, sentiment, quotes (array)}),
pain_points (array of {issue, severity, affected_users_pct, suggested_fix}),
feature_requests (array of {feature, demand_level, effort_estimate, priority}),
satisfaction_score (0-100), nps_estimate (-100 to 100),
action_items (array of {action, priority, expected_impact})."""

SPM_SYSTEM = """You are a Senior Project Manager. Convert specs into actionable task breakdowns.
Output JSON with: phases (array of {name, duration_days, tasks (array of {
  id, title, description, assignee_role, story_points, dependencies (array of task ids),
  acceptance_criteria (array)})}),
milestones (array of {name, date_offset_days, deliverables}),
risks (array of {risk, impact, mitigation}),
total_estimate ({days, story_points, team_size}),
critical_path (array of task ids)."""

ANALYTICS_SYSTEM = """You are a senior Analytics Reporter. Generate dashboard specs and data visualizations.
Output JSON with: dashboards (array of {name, description, widgets (array of {
  type (chart|metric|table), title, data_source, query, visualization_config})}),
kpis (array of {name, formula, target, frequency}),
data_sources (array of {name, type, connection_config}),
reports (array of {name, schedule, recipients, sections})."""

LEGAL_COMPLIANCE_SYSTEM = """You are a Legal Compliance Checker. Audit code for regulatory compliance.
Output JSON with: frameworks_checked (array of framework names),
findings (array of {framework, requirement, status (compliant|non_compliant|partial),
  code_location, issue, remediation, severity}),
data_handling ({pii_detected (array), encryption_status, retention_policy, consent_mechanism}),
compliance_score (0-100), risk_level (low|medium|high|critical),
action_items (array of {action, framework, deadline_urgency, effort})."""

IDENTITY_TRUST_SYSTEM = """You are an Identity & Trust Architect. Design agent authentication and audit systems.
Output JSON with: identity_model ({agents (array of {id, role, permissions, trust_level}),
  auth_mechanism, token_format, rotation_policy}),
trust_framework ({verification_methods, escalation_rules, revocation_process}),
audit_trail ({log_format, storage, retention_days, searchable_fields}),
files (array of {path, language, description, content}) with implementation code."""

PROMPTS = {
    "product_manager": PM_SYSTEM,
    "architect": ARCHITECT_SYSTEM,
    "developer": DEVELOPER_SYSTEM,
    "qa_engineer": QA_SYSTEM,
    "security": SECURITY_SYSTEM,
    "frontend_developer": FRONTEND_SYSTEM,
    "ui_designer": UI_DESIGN_SYSTEM,
    "ux_researcher": UX_RESEARCH_SYSTEM,
    "mobile_developer": MOBILE_SYSTEM,
    "ai_engineer": AI_ENGINEER_SYSTEM,
    "rapid_prototyper": RAPID_PROTO_SYSTEM,
    "api_tester": API_TESTER_SYSTEM,
    "accessibility_auditor": ACCESSIBILITY_SYSTEM,
    "sprint_prioritizer": SPRINT_SYSTEM,
    "feedback_synthesizer": FEEDBACK_SYSTEM,
    "senior_project_manager": SPM_SYSTEM,
    "analytics_reporter": ANALYTICS_SYSTEM,
    "legal_compliance": LEGAL_COMPLIANCE_SYSTEM,
    "identity_trust_architect": IDENTITY_TRUST_SYSTEM,
}


def create_agent(role: str, project_id: str = None) -> AgentLLM:
    """Factory function to create an agent with the right model config."""
    return AgentLLM(role, project_id)


def get_system_prompt(role: str) -> str:
    """Get the system prompt for an agent role."""
    return PROMPTS.get(role, "You are a helpful software engineering assistant.")
