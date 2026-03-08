#!/usr/bin/env python3
"""
NexDev Orchestrator v2 — "The Sovereign Architect"
===================================================
Tier-based coding orchestrator with ClawVault memory integration,
autonomous agent modules, and self-correction loops.

Architecture:
  ClawVault Memory → Tier Router → Model Execution → Validation → Learning

Tiers:
  Strategic  (Opus 4 / Grok 4)      — Architecture, migrations, security audits
  Execution  (Qwen 3.5 122B)        — Default engine, feature dev, refactoring
  Context    (Gemini 2.5 Pro)        — Repo-wide analysis, 200K+ token tasks
  Validation (Grok 4.1 Fast)        — TDD loops, build failure debugging
  Utility    (Qwen Coder / Flash)   — Tests, docs, boilerplate
  Vision     (Qwen Vision)          — UI screenshot comparison

Author: Optimus for Fas
Date: 2026-03-03
"""

import json
import os
import time
import hashlib
import subprocess
import sys
from pathlib import Path
from datetime import datetime, timezone

# Add nexdev dir to path for engine import
NEXDEV_MODULE_DIR = Path(__file__).parent
sys.path.insert(0, str(NEXDEV_MODULE_DIR))

# ── Constants ──────────────────────────────────────────────────────────────────

HOME = Path.home()
WORKSPACE = HOME / ".openclaw" / "workspace"
MEMORY_ROOT = HOME / "memory"
NEXDEV_DIR = WORKSPACE / "nexdev"
CLAWVAULT_DB = MEMORY_ROOT / ".clawvault.db"
PERFORMANCE_DB = MEMORY_ROOT / "model_performance.json"
ACTIVE_PROJECTS = MEMORY_ROOT / "active_projects.json"
NEXDEV_LOG = NEXDEV_DIR / "logs" / "nexdev.jsonl"
NEXDEV_CONFIG = NEXDEV_DIR / "config.json"

# ── Model Inventory ───────────────────────────────────────────────────────────

TIERS = {
    "strategic": {
        "name": "Strategic Tier",
        "description": "Architecture, migrations, security audits, 5+ interdependent files",
        "models": [
            {"id": "anthropic/claude-opus-4-6", "alias": "Opus", "cost_in": 5.00, "cost_out": 25.00, "ctx": 200_000, "reasoning": True},
            {"id": "xai/grok-4", "alias": "Grok", "cost_in": 3.00, "cost_out": 15.00, "ctx": 131_000, "reasoning": False},
        ],
        "triggers": [
            "database migration", "schema redesign", "architecture", "security audit",
            "multi-service", "microservice", "system design", "infrastructure",
            "breaking change", "data model", "auth system", "permissions"
        ],
        "file_threshold": 5,  # Route here if >5 interdependent files
    },
    "execution": {
        "name": "Execution Tier (DEFAULT)",
        "description": "Feature implementation, API development, complex refactoring",
        "models": [
            {"id": "alibaba-sg/qwen3.5-122b-a10b", "alias": "Qwen35", "cost_in": 0.40, "cost_out": 1.20, "ctx": 1_000_000, "reasoning": True},
        ],
        "triggers": [
            "implement", "feature", "api", "endpoint", "refactor", "build",
            "create", "develop", "integrate", "service", "handler", "controller",
            "lambda", "function", "module", "class", "component"
        ],
    },
    "context": {
        "name": "Context Tier",
        "description": "Repo-wide analysis, documentation >200K tokens, global knowledge",
        "models": [
            {"id": "google/gemini-2.5-pro", "alias": "GeminiPro", "cost_in": 1.25, "cost_out": 10.00, "ctx": 1_000_000, "reasoning": True},
        ],
        "triggers": [
            "entire repo", "codebase", "all files", "repo-wide", "search across",
            "documentation", "summarize repo", "dependency graph", "audit all",
            "find everywhere", "global search", "tech debt"
        ],
        "token_threshold": 200_000,  # Route here if context >200K tokens
    },
    "validation": {
        "name": "Validation Tier",
        "description": "TDD loops, build failure debugging, real-time fixes",
        "models": [
            {"id": "xai/grok-4-1-fast-non-reasoning", "alias": "GrokFast", "cost_in": 2.00, "cost_out": 10.00, "ctx": 131_000, "reasoning": False},
            {"id": "xai/grok-4-1-fast-reasoning", "alias": "GrokFastR", "cost_in": 2.00, "cost_out": 10.00, "ctx": 131_000, "reasoning": True},
        ],
        "triggers": [
            "build fail", "test fail", "error", "debug", "fix bug", "broken",
            "TypeError", "SyntaxError", "compile error", "lint", "tsc",
            "npm run build", "pytest", "jest", "CI failed", "pipeline"
        ],
    },
    "utility": {
        "name": "Utility Tier",
        "description": "Unit tests, docs, CSS/Tailwind, boilerplate, simple edits",
        "models": [
            {"id": "alibaba-sg/qwen-coder", "alias": "QwenCoder", "cost_in": 0.30, "cost_out": 1.50, "ctx": 1_000_000, "reasoning": False},
            {"id": "google/gemini-2.0-flash-lite", "alias": "GeminiLite", "cost_in": 0.075, "cost_out": 0.30, "ctx": 1_000_000, "reasoning": False},
        ],
        "triggers": [
            "unit test", "test for", "write test", "documentation", "readme",
            "css", "tailwind", "style", "boilerplate", "scaffold", "template",
            "rename", "move file", "simple change", "typo", "comment"
        ],
    },
    "vision": {
        "name": "Vision Tier",
        "description": "UI screenshot comparison, design-vs-reality checks",
        "models": [
            {"id": "qwen-portal/vision-model", "alias": "QwenVision", "cost_in": 0.00, "cost_out": 0.00, "ctx": 128_000, "reasoning": False},
            {"id": "xai/grok-2-vision-1212", "alias": "GrokVision", "cost_in": 2.00, "cost_out": 10.00, "ctx": 32_000, "reasoning": False},
        ],
        "triggers": [
            "screenshot", "ui comparison", "design vs", "visual", "layout",
            "responsive", "pixel", "mockup", "figma", "frontend preview"
        ],
    },
}

# ── Autonomous Agent Modules ──────────────────────────────────────────────────

AGENTS = {
    "shadow_sec": {
        "name": "Shadow Sec (Security Agent)",
        "description": "Scans for env leaks, SQL injection, vulnerable dependencies",
        "model": "alibaba-sg/qwen-coder",
        "triggers": ["security", "env leak", "injection", "vulnerability", "CVE", "npm audit"],
        "system_prompt": """You are Shadow Sec, a security-focused code auditor.
Your job is to scan code for:
1. Exposed secrets (API keys, tokens, passwords in code or .env files)
2. SQL injection vulnerabilities (unsanitized inputs in queries)
3. XSS risks (unescaped user input in templates/JSX)
4. Insecure dependencies (known CVEs in package.json/requirements.txt)
5. Overly permissive IAM policies or CORS configurations
6. Hardcoded credentials or connection strings

Output format:
- SEVERITY: CRITICAL/HIGH/MEDIUM/LOW
- FILE: path/to/file
- LINE: approximate line number
- FINDING: description
- FIX: recommended remediation

Never suggest disabling security features. Always recommend the most secure alternative.""",
    },
    "sre": {
        "name": "SRE (DevOps Agent)",
        "description": "Handles Dockerization, CI/CD YAML health, infrastructure",
        "model": "alibaba-sg/qwen3.5-122b-a10b",
        "triggers": ["docker", "ci/cd", "yaml", "pipeline", "deploy", "kubernetes", "terraform"],
        "system_prompt": """You are the SRE Agent, a DevOps specialist.
Your responsibilities:
1. Dockerfile optimization (multi-stage builds, minimal images)
2. CI/CD pipeline health (GitHub Actions, GitLab CI, Jenkins)
3. Infrastructure as Code review (Terraform, CloudFormation, SAM)
4. Container orchestration (Docker Compose, Kubernetes)
5. Monitoring and alerting configuration
6. Secret management in deployment pipelines

Always prefer:
- Multi-stage Docker builds over single-stage
- GitHub Actions reusable workflows over copy-paste
- Least-privilege IAM roles
- Immutable infrastructure patterns
- Blue/green or canary deployments over direct updates""",
    },
    "archivist": {
        "name": "The Archivist (Documentation Agent)",
        "description": "Auto-generates Mermaid diagrams, README updates per feature branch",
        "model": "google/gemini-2.0-flash-lite",
        "triggers": ["diagram", "mermaid", "readme", "docs", "architecture diagram", "flowchart"],
        "system_prompt": """You are The Archivist, a documentation specialist.
Your responsibilities:
1. Generate Mermaid diagrams for system architecture
2. Update README.md with new features, API changes, and setup instructions
3. Create API documentation (OpenAPI/Swagger format when appropriate)
4. Maintain CHANGELOG.md entries
5. Generate data flow diagrams for complex pipelines
6. Create onboarding docs for new developers

Output format for diagrams:
```mermaid
graph TD
    A[Component] --> B[Component]
```

Keep docs concise, accurate, and developer-friendly.""",
    },
}

# ── Escalation Chains ─────────────────────────────────────────────────────────

ESCALATION = {
    "utility":    ["validation", "execution", "strategic"],
    "validation": ["execution", "strategic"],
    "execution":  ["context", "strategic"],
    "context":    ["strategic"],
    "strategic":  [],  # No escalation from top tier
    "vision":     ["execution"],
}

# ── ClawVault Memory Integration ──────────────────────────────────────────────

def search_clawvault(query: str, limit: int = 5) -> list:
    """Search ClawVault memory for relevant context before routing."""
    results = []

    # Search daily memory files
    memory_dir = MEMORY_ROOT
    if memory_dir.exists():
        for md_file in sorted(memory_dir.glob("*.md"), reverse=True)[:7]:  # Last 7 days
            try:
                content = md_file.read_text(errors="ignore")
                query_words = set(query.lower().split())
                content_lower = content.lower()
                matches = sum(1 for w in query_words if w in content_lower)
                if matches >= 2:
                    # Extract relevant lines
                    relevant = []
                    for line in content.split("\n"):
                        if any(w in line.lower() for w in query_words):
                            relevant.append(line.strip())
                    if relevant:
                        results.append({
                            "source": str(md_file.name),
                            "relevance": matches / len(query_words),
                            "snippets": relevant[:3],
                        })
            except Exception:
                continue

    # Search active projects
    if ACTIVE_PROJECTS.exists():
        try:
            projects = json.loads(ACTIVE_PROJECTS.read_text())
            for name, data in projects.items():
                if isinstance(data, dict):
                    keywords = data.get("keywords", [])
                    if any(k in query.lower() for k in keywords):
                        results.append({
                            "source": "active_projects.json",
                            "project": name,
                            "status": data.get("status", "unknown"),
                            "model_used": data.get("model_used", "unknown"),
                        })
        except Exception:
            pass

    # Search performance DB for topic-model affinity
    if PERFORMANCE_DB.exists():
        try:
            perf = json.loads(PERFORMANCE_DB.read_text())
            by_topic = perf.get("by_topic", {})
            for topic, data in by_topic.items():
                if any(w in topic for w in query.lower().split()):
                    best_model = None
                    best_rate = 0
                    for model, scores in data.get("model_scores", {}).items():
                        rate = scores.get("success_rate", 0)
                        if rate > best_rate:
                            best_rate = rate
                            best_model = model
                    if best_model:
                        results.append({
                            "source": "performance_db",
                            "topic": topic,
                            "recommended_model": best_model,
                            "success_rate": best_rate,
                        })
        except Exception:
            pass

    return results[:limit]


def get_project_context(query: str) -> dict:
    """Get active project context if query matches a known project."""
    if not ACTIVE_PROJECTS.exists():
        return {}

    try:
        projects = json.loads(ACTIVE_PROJECTS.read_text())
        query_lower = query.lower()
        for name, data in projects.items():
            if isinstance(data, dict):
                keywords = data.get("keywords", [])
                # Require at least 2 keyword matches to avoid false positives
                matches = sum(1 for k in keywords if k in query_lower)
                if matches >= 2 or name.replace("-", " ") in query_lower:
                    return {
                        "project": name,
                        "status": data.get("status"),
                        "model_used": data.get("model_used"),
                        "started": data.get("started"),
                        "notes": data.get("notes", ""),
                    }
    except Exception:
        pass
    return {}


# ── Tier Router ───────────────────────────────────────────────────────────────

def _find_model_by_id(model_id: str) -> dict:
    """Find model details from any tier by its ID."""
    for tier_config in TIERS.values():
        for m in tier_config["models"]:
            if m["id"] == model_id:
                return m
    return {"alias": model_id.split("/")[-1], "cost_in": "?", "cost_out": "?", "ctx": 0, "reasoning": False}


def detect_complexity(query: str) -> dict:
    """Analyze query complexity and return routing metadata."""
    query_lower = query.lower()
    result = {
        "estimated_tokens": len(query.split()) * 1.5,  # Rough estimate
        "file_count": 0,
        "has_error_trace": False,
        "has_screenshot": False,
        "needs_security": False,
        "needs_devops": False,
        "needs_docs": False,
    }

    # Count file references (extensions + semantic mentions)
    file_extensions = [".py", ".ts", ".js", ".tsx", ".jsx", ".json", ".yaml", ".yml",
                       ".sh", ".css", ".html", ".sql", ".tf", ".dockerfile"]
    for ext in file_extensions:
        result["file_count"] += query_lower.count(ext)

    # Also count semantic file/service references (e.g. "8 Lambda functions")
    import re
    numeric_refs = re.findall(r'(\d+)\s+(?:lambda|function|service|table|endpoint|file|module|component|microservice|api|handler|worker)', query_lower)
    for count_str in numeric_refs:
        result["file_count"] += int(count_str)

    # Detect error traces
    error_indicators = ["traceback", "error:", "failed", "exception", "stack trace",
                        "TypeError", "SyntaxError", "ModuleNotFoundError", "ENOENT"]
    result["has_error_trace"] = any(e.lower() in query_lower for e in error_indicators)

    # Detect screenshot/vision needs (must be actual visual/UI tasks)
    vision_indicators = ["screenshot", "ui comparison", "mockup vs", "layout check",
                         "pixel perfect", "figma", "frontend preview", "visual diff",
                         "compare design", "responsive test"]
    result["has_screenshot"] = any(v in query_lower for v in vision_indicators)

    # Detect agent needs
    security_indicators = ["security", "vulnerability", "injection", "leak", "CVE", "audit"]
    result["needs_security"] = any(s.lower() in query_lower for s in security_indicators)

    devops_indicators = ["docker", "ci/cd", "pipeline", "deploy", "kubernetes", "terraform"]
    result["needs_devops"] = any(d.lower() in query_lower for d in devops_indicators)

    docs_indicators = ["diagram", "readme", "documentation", "mermaid", "changelog"]
    result["needs_docs"] = any(d.lower() in query_lower for d in docs_indicators)

    return result


def route_to_tier(query: str, context: dict = None) -> dict:
    """
    Route a coding query to the appropriate tier and model.
    
    Flow:
    1. Search ClawVault memory for background context
    2. Check active projects for model continuity
    3. Analyze complexity
    4. Match to tier based on triggers + complexity
    5. Select specific model within tier
    6. Return routing decision with full context
    """
    context = context or {}
    query_lower = query.lower()

    # ── Step 1: ClawVault Memory Search ──
    memory_results = search_clawvault(query)
    memory_context = ""
    recommended_model_from_memory = None

    for mem in memory_results:
        if mem.get("source") == "performance_db":
            recommended_model_from_memory = mem.get("recommended_model")
        if mem.get("snippets"):
            memory_context += "\n".join(mem["snippets"]) + "\n"

    # ── Step 2: Active Project Continuity ──
    project = get_project_context(query)
    if project and project.get("model_used") and project.get("status") == "in_progress":
        # Find model details from our inventory
        model_id = project["model_used"]
        model_details = _find_model_by_id(model_id)
        esc_chain = []
        for esc_tier in ESCALATION.get("execution", []):
            if esc_tier in TIERS:
                em = TIERS[esc_tier]["models"][0]
                esc_chain.append(f"{em['alias']} ({em['id']})")

        return {
            "tier": "execution",
            "tier_name": "Execution Tier (Project Continuity)",
            "model": model_id,
            "model_alias": model_details.get("alias", model_id.split("/")[-1]),
            "model_cost": f"${model_details.get('cost_in', '?')}/M in, ${model_details.get('cost_out', '?')}/M out",
            "context_window": f"{model_details.get('ctx', 0) // 1000}K" if model_details.get("ctx") else "?",
            "reasoning": model_details.get("reasoning", False),
            "reason": f"Project continuity: '{project['project']}' (started {project.get('started', 'unknown')})",
            "memory_context": memory_context[:500] if memory_context else "(no prior context found)",
            "memory_results": len(memory_results),
            "project": project,
            "complexity": detect_complexity(query),
            "escalation_chain": esc_chain,
            "agents": [],
            "all_scores": {},
        }

    # ── Step 3: Complexity Analysis ──
    complexity = detect_complexity(query)

    # ── Step 4: Determine Autonomous Agents Needed ──
    active_agents = []
    if complexity["needs_security"]:
        active_agents.append(AGENTS["shadow_sec"])
    if complexity["needs_devops"]:
        active_agents.append(AGENTS["sre"])
    if complexity["needs_docs"]:
        active_agents.append(AGENTS["archivist"])

    # ── Step 5: Tier Matching ──
    tier_scores = {}
    for tier_name, tier_config in TIERS.items():
        score = 0
        triggers = tier_config.get("triggers", [])
        for trigger in triggers:
            if trigger.lower() in query_lower:
                score += 2

        # Bonus scoring for complexity signals
        if tier_name == "strategic" and complexity["file_count"] > tier_config.get("file_threshold", 5):
            score += 5
        if tier_name == "context" and complexity["estimated_tokens"] > tier_config.get("token_threshold", 200_000):
            score += 5
        if tier_name == "validation" and complexity["has_error_trace"]:
            score += 4
        if tier_name == "vision" and complexity["has_screenshot"]:
            score += 6

        tier_scores[tier_name] = score

    # Select highest scoring tier (default to execution)
    best_tier = max(tier_scores, key=tier_scores.get)
    if tier_scores[best_tier] == 0:
        best_tier = "execution"  # Default engine

    # ── Step 6: Model Selection ──
    tier_config = TIERS[best_tier]
    models = tier_config["models"]

    # If memory recommends a specific model and it's in this tier, use it
    selected_model = models[0]  # Default to first (cheapest/best in tier)
    if recommended_model_from_memory:
        for m in models:
            if m["id"] == recommended_model_from_memory:
                selected_model = m
                break

    # Build escalation chain with actual model IDs
    escalation_models = []
    for esc_tier in ESCALATION.get(best_tier, []):
        if esc_tier in TIERS:
            esc_model = TIERS[esc_tier]["models"][0]
            escalation_models.append(f"{esc_model['alias']} ({esc_model['id']})")

    return {
        "tier": best_tier,
        "tier_name": tier_config["name"],
        "model": selected_model["id"],
        "model_alias": selected_model["alias"],
        "model_cost": f"${selected_model['cost_in']}/M in, ${selected_model['cost_out']}/M out",
        "context_window": f"{selected_model['ctx'] // 1000}K",
        "reasoning": selected_model.get("reasoning", False),
        "reason": f"Matched {tier_scores[best_tier]} triggers for {tier_config['name']}",
        "memory_context": memory_context[:500] if memory_context else "(no prior context found)",
        "memory_results": len(memory_results),
        "project": project,
        "complexity": complexity,
        "escalation_chain": escalation_models,
        "agents": [a["name"] for a in active_agents],
        "agent_prompts": {a["name"]: a["system_prompt"] for a in active_agents},
        "all_scores": tier_scores,
    }


# ── Self-Correction Loop ─────────────────────────────────────────────────────

def self_correction_loop(result: dict, tier: str) -> dict:
    """
    If Utility Tier code fails linting/tests, escalate to Validation Tier.
    If Validation Tier fails, escalate to Execution Tier.
    """
    if not result.get("success", True):
        escalation = ESCALATION.get(tier, [])
        if escalation:
            next_tier = escalation[0]
            next_model = TIERS[next_tier]["models"][0]
            return {
                "action": "escalate",
                "from_tier": tier,
                "to_tier": next_tier,
                "model": next_model["id"],
                "alias": next_model["alias"],
                "reason": f"Self-correction: {tier} failed, escalating to {next_tier}",
            }
    return {"action": "accept", "tier": tier}


# ── Dependency Guard ──────────────────────────────────────────────────────────

def dependency_guard(package_name: str, ecosystem: str = "npm") -> dict:
    """
    Before Execution Tier installs a library, Strategic Tier must verify
    its security posture and license.
    """
    return {
        "check": "dependency_guard",
        "package": package_name,
        "ecosystem": ecosystem,
        "routed_to": "strategic",
        "model": TIERS["strategic"]["models"][0]["id"],
        "prompt": f"""Security review required for package: {package_name} ({ecosystem})

Check:
1. Known CVEs in the latest version
2. License compatibility (MIT/Apache preferred, avoid GPL for commercial)
3. Maintenance status (last commit, open issues, bus factor)
4. Download count / community adoption
5. Transitive dependency count (prefer minimal dependency trees)

Respond with: APPROVED / REVIEW_NEEDED / REJECTED and reasoning.""",
    }


# ── Context Compression ──────────────────────────────────────────────────────

def context_compression_check(pr_count: int) -> dict:
    """
    Every 5 PRs, Gemini 2.5 Pro summarizes the repo state
    to keep Strategic Tier context lean.
    """
    if pr_count % 5 == 0 and pr_count > 0:
        return {
            "action": "compress_context",
            "routed_to": "context",
            "model": TIERS["context"]["models"][0]["id"],
            "prompt": """Summarize the current repository state:
1. Architecture overview (key modules and their relationships)
2. Recent changes (last 5 PRs) - what was added/changed/removed
3. Current tech debt items
4. Open issues and their priority
5. Dependency health status

Keep the summary under 2000 tokens for Strategic Tier consumption.""",
        }
    return {"action": "skip", "reason": f"PR count {pr_count} not at compression threshold (every 5)"}


# ── Performance Logging ───────────────────────────────────────────────────────

def log_execution(routing: dict, success: bool, confidence: float, duration_ms: int = 0):
    """Log model execution for learning."""
    NEXDEV_LOG.parent.mkdir(parents=True, exist_ok=True)

    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "tier": routing.get("tier"),
        "model": routing.get("model"),
        "model_alias": routing.get("model_alias"),
        "success": success,
        "confidence": confidence,
        "duration_ms": duration_ms,
        "agents": routing.get("agents", []),
        "memory_hits": routing.get("memory_results", 0),
        "escalated": False,
    }

    with open(NEXDEV_LOG, "a") as f:
        f.write(json.dumps(entry) + "\n")

    # Update performance DB
    _update_performance_db(routing, success, confidence)


def _update_performance_db(routing: dict, success: bool, confidence: float):
    """Update the shared performance database."""
    try:
        perf = json.loads(PERFORMANCE_DB.read_text()) if PERFORMANCE_DB.exists() else {"by_topic": {}}
    except Exception:
        perf = {"by_topic": {}}

    tier = routing.get("tier", "unknown")
    model = routing.get("model", "unknown")

    if tier not in perf["by_topic"]:
        perf["by_topic"][tier] = {"model_scores": {}, "total_queries": 0}

    topic = perf["by_topic"][tier]
    topic["total_queries"] = topic.get("total_queries", 0) + 1

    if model not in topic["model_scores"]:
        topic["model_scores"][model] = {
            "success_count": 0, "failure_count": 0,
            "total_cost": 0, "avg_confidence": 0,
            "usage_count": 0, "success_rate": 0,
        }

    scores = topic["model_scores"][model]
    scores["usage_count"] += 1
    if success:
        scores["success_count"] += 1
    else:
        scores["failure_count"] += 1
    scores["success_rate"] = scores["success_count"] / scores["usage_count"]
    scores["avg_confidence"] = (
        (scores["avg_confidence"] * (scores["usage_count"] - 1) + confidence)
        / scores["usage_count"]
    )

    PERFORMANCE_DB.write_text(json.dumps(perf, indent=2))


# ── CLI Interface ─────────────────────────────────────────────────────────────

def print_routing(routing: dict):
    """Pretty-print a routing decision."""
    print("=" * 80)
    print("🛠️  NexDev Orchestrator v2 — Routing Decision")
    print("=" * 80)

    print(f"\n📍 Tier:     {routing.get('tier_name', routing.get('tier', '?'))}")
    print(f"🤖 Model:    {routing.get('model_alias', '?')} ({routing.get('model', '?')})")
    print(f"💰 Cost:     {routing.get('model_cost', '?')}")
    print(f"📐 Context:  {routing.get('context_window', '?')}")
    print(f"🧠 Reason:   {routing.get('reasoning', False)}")
    print(f"📋 Reason:   {routing.get('reason', '?')}")

    if routing.get("memory_results", 0) > 0:
        print(f"\n📚 Memory:   {routing['memory_results']} relevant memories found")
        if routing.get("memory_context") and routing["memory_context"] != "(no prior context found)":
            print(f"   Context:  {routing['memory_context'][:200]}...")

    if routing.get("project"):
        p = routing["project"]
        print(f"\n📂 Project:  {p.get('project', '?')} ({p.get('status', '?')})")

    if routing.get("agents"):
        print(f"\n🕵️ Agents:   {', '.join(routing['agents'])}")

    if routing.get("escalation_chain"):
        print(f"\n⬆️ Escalation: {' → '.join(routing['escalation_chain'])}")

    if routing.get("all_scores"):
        print(f"\n📊 Tier Scores:")
        for tier, score in sorted(routing["all_scores"].items(), key=lambda x: -x[1]):
            bar = "█" * score + "░" * (10 - score)
            print(f"   {tier:<14} [{bar}] {score}")

    print()
    print(f"— {routing.get('model_alias', '?')}")
    print("=" * 80)


def run_demo():
    """Run demo queries through the router."""
    queries = [
        "Implement a new REST API endpoint for user authentication with JWT tokens",
        "The build is failing: TypeError: Cannot read properties of undefined (reading 'map') in UserList.tsx",
        "Design a microservice architecture for handling real-time financial data processing across 8 Lambda functions and 3 DynamoDB tables",
        "Write unit tests for the email validation utility function",
        "Review the entire codebase for SQL injection vulnerabilities and hardcoded API keys",
        "Summarize the repository structure and generate a Mermaid architecture diagram",
        "Compare this screenshot of our dashboard with the Figma mockup and identify layout differences",
        "Create a Dockerfile with multi-stage build for our Node.js API and set up GitHub Actions CI/CD",
        "Refactor the payment processing module to support Stripe and Square payment gateways",
        "Debug: npm run build fails with 'Module not found: @azure/msal-node' in office365-runner.js",
    ]

    print()
    print("🛠️  NexDev Orchestrator v2 — DEMO")
    print("=" * 80)
    print()

    for i, query in enumerate(queries, 1):
        routing = route_to_tier(query)
        tier = routing.get("tier", "?")
        alias = routing.get("model_alias", "?")
        agents = routing.get("agents", [])
        esc = routing.get("escalation_chain", [])
        cost = routing.get("model_cost", "?")

        agent_str = f" + [{', '.join(agents)}]" if agents else ""
        esc_str = f" → {' → '.join(esc)}" if esc else ""

        print(f"{i:2}. Query: '{query[:70]}{'...' if len(query) > 70 else ''}'")
        print(f"    → Tier: {tier:<14} Model: {alias:<12} Cost: {cost}{agent_str}")
        if esc_str:
            print(f"    → Escalation:{esc_str}")
        print()

    # Summary table
    print("=" * 80)
    print("TIER SUMMARY")
    print("=" * 80)
    for tier_name, tier_config in TIERS.items():
        models = tier_config["models"]
        model_list = ", ".join(m["alias"] for m in models)
        cost_range = f"${min(m['cost_in'] for m in models):.2f}-${max(m['cost_in'] for m in models):.2f}/M"
        print(f"  {tier_name:<14} → {model_list:<30} {cost_range}")
    print()
    print("AUTONOMOUS AGENTS")
    print("-" * 40)
    for agent_name, agent_config in AGENTS.items():
        print(f"  🕵️ {agent_config['name']:<35} → {agent_config['model']}")
    print()


def main():
    """CLI entry point."""
    args = sys.argv[1:]

    if not args or args[0] in ("help", "--help", "-h"):
        print("""
🛠️  NexDev Orchestrator v2 — "The Sovereign Architect"

Usage:
  nexdev route "<query>"     Route a coding task (dry-run, no API call)
  nexdev run "<query>"       Route AND execute against the model API
  nexdev demo                Run demo with 10 example queries
  nexdev test [model]        Test model connectivity (default: qwen-turbo)
  nexdev test-all            Test all tier models
  nexdev agents              List autonomous agent modules
  nexdev tiers               Show all tiers and models
  nexdev guard <package>     Run Dependency Guard on a package
  nexdev compress <pr_count> Check if context compression is needed
  nexdev costs               Show execution cost summary
  nexdev log                 Show recent routing decisions
  nexdev help                Show this help

Tiers: Strategic → Execution → Context → Validation → Utility → Vision
Default: Execution (Qwen 3.5 122B — the Value-Intelligence Sweet Spot)
        """)

    elif args[0] == "demo":
        run_demo()

    elif args[0] == "route" and len(args) > 1:
        query = " ".join(args[1:])
        routing = route_to_tier(query)
        print_routing(routing)

    elif args[0] == "run" and len(args) > 1:
        query = " ".join(args[1:])
        routing = route_to_tier(query)
        print_routing(routing)

        # Import engine and execute
        try:
            from engine import execute_with_escalation
            print("\n⏳ Executing against API...\n")
            result = execute_with_escalation(
                routing, query,
                system_prompt="You are NexDev v2, a Sovereign Engineering Lead. Provide precise, production-ready code and technical guidance.",
            )
            if result["success"]:
                tier = routing.get('tier', '?')
                alias = routing.get('model_alias', '?')
                model_id = result.get('model', '?')
                esc_tag = f" ⬆️ escalated from {result.get('original_model', '?')}" if result.get("escalated") else ""

                print(f"┌{'─' * 78}┐")
                print(f"│ 🤖 Model: {alias} ({model_id}){esc_tag}")
                print(f"│ 🏗️  Tier:  {routing.get('tier_name', tier)}")
                print(f"│ 💰 Cost:  ${result['cost_usd']:.4f} | {result['input_tokens']+result['output_tokens']:,} tokens | {result['duration_ms']}ms")
                if routing.get("agents"):
                    print(f"│ 🕵️  Agents: {', '.join(routing['agents'])}")
                print(f"└{'─' * 78}┘")
                print()
                print(result["text"])
                print()
                print(f"— {alias}")
            else:
                print(f"❌ Execution failed: {result.get('error', 'unknown')}")
        except ImportError as e:
            print(f"❌ Engine not available: {e}")

    elif args[0] == "test":
        from engine import quick_test
        model = args[1] if len(args) > 1 else "alibaba-sg/qwen-turbo"
        print(f"🧪 Testing {model}...")
        result = quick_test(model)
        if result["success"]:
            print(f"✅ {model} → \"{result['text']}\" ({result['duration_ms']}ms, ${result['cost_usd']})")
        else:
            print(f"❌ {model} → {result['error']}")

    elif args[0] == "test-all":
        from engine import quick_test
        test_models = [
            ("Utility",    "alibaba-sg/qwen-turbo"),
            ("Utility",    "alibaba-sg/qwen-coder"),
            ("Utility",    "google/gemini-2.0-flash-lite"),
            ("Execution",  "alibaba-sg/qwen3.5-122b-a10b"),
            ("Context",    "google/gemini-2.5-pro"),
            ("Validation", "xai/grok-4-1-fast-non-reasoning"),
            ("Strategic",  "moonshot/kimi-k2.5"),
        ]
        print("\n🧪 NexDev Production Readiness Test\n")
        passed = 0
        for tier, model in test_models:
            result = quick_test(model)
            status = "✅" if result["success"] else "❌"
            detail = f"\"{result['text'][:30]}\" ({result['duration_ms']}ms)" if result["success"] else result["error"][:50]
            print(f"  {status} [{tier:<11}] {model:<45} {detail}")
            if result["success"]:
                passed += 1
        print(f"\n  Result: {passed}/{len(test_models)} models operational")

    elif args[0] == "costs":
        from engine import get_cost_summary
        summary = get_cost_summary()
        print(f"\n💰 NexDev Cost Summary")
        print(f"   Total: ${summary['total_cost']:.4f} across {summary['total_calls']} calls\n")
        for model, data in sorted(summary["by_model"].items(), key=lambda x: -x[1]["cost"]):
            print(f"   {model:<45} {data['calls']:>3} calls  ${data['cost']:.4f}")

    elif args[0] == "agents":
        print("\n🕵️  NexDev Autonomous Agents\n")
        for name, agent in AGENTS.items():
            print(f"  {agent['name']}")
            print(f"    Model: {agent['model']}")
            print(f"    Triggers: {', '.join(agent['triggers'][:5])}")
            print()

    elif args[0] == "tiers":
        print("\n🏗️  NexDev Model Tiers\n")
        for tier_name, tier_config in TIERS.items():
            models = tier_config["models"]
            print(f"  {'█' if tier_name == 'execution' else '░'} {tier_config['name']}")
            for m in models:
                r = "🧠" if m.get("reasoning") else "  "
                print(f"    {r} {m['alias']:<15} {m['id']:<40} ${m['cost_in']:<6}/M  Ctx:{m['ctx']//1000}K")
            print()

    elif args[0] == "guard" and len(args) > 1:
        result = dependency_guard(args[1], args[2] if len(args) > 2 else "npm")
        print(json.dumps(result, indent=2))

    elif args[0] == "compress" and len(args) > 1:
        result = context_compression_check(int(args[1]))
        print(json.dumps(result, indent=2))

    elif args[0] == "log":
        if NEXDEV_LOG.exists():
            lines = NEXDEV_LOG.read_text().strip().split("\n")
            for line in lines[-10:]:
                entry = json.loads(line)
                print(f"  [{entry.get('timestamp', '?')[:19]}] {entry.get('tier', '?'):<14} → {entry.get('model_alias', '?'):<12} {'✅' if entry.get('success') else '❌'} conf:{entry.get('confidence', 0):.2f}")
        else:
            print("  (no logs yet)")

    else:
        # Treat everything as a routing query
        query = " ".join(args)
        routing = route_to_tier(query)
        print_routing(routing)


if __name__ == "__main__":
    main()
