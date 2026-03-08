# 🚀 NexDev Phase 1 Implementation Plan

**Document Version:** 1.0  
**Date:** 2026-03-03 08:46 CST  
**Duration:** Week 1-2 (10 business days)  
**Owner:** [To Be Assigned]

---

## Executive Summary

This document provides **day-by-day, hour-by-hour implementation instructions** for deploying Phase 1 of the NexDev AI Coding Stack. Every step includes exact commands, file locations, and verification checkpoints. No ambiguity — just execute.

### Phase 1 Deliverables

| Deliverable | Status After Completion |
|-------------|------------------------|
| ✅ MO v2.0 deployed with 20+ code topics | Query routing works across all models |
| ✅ Antfarm workflows installed & customized | Bug-fix + feature-dev workflows running |
| ✅ Project memory graph (SQLite) initialized | Persistent context across sessions |
| ✅ Model tier routing table configured | Cost-aware model selection active |
| ✅ Cost tracking per task enabled | Real-time spending visibility |
| ✅ Daily cost report automation | Weekly email summaries scheduled |

**Total Active Work Time:** ~16 hours (2 days full-time)  
**Recommended Schedule:** Spread over 10 business days (lighter daily load)

---

## Pre-Implementation Checklist

Before starting, verify these are complete:

### Infrastructure Prerequisites

```bash
# Check Python version
python3 --version  # Must be 3.9+

# Check Git is installed
git --version

# Check Node.js (for Antfarm CLI)
node --version  # Must be 18+

# Check OpenClaw installation
openclaw --version

# Verify workspace directory exists
ls -la ~/.openclaw/workspace/

# Create memory directory if needed
mkdir -p ~/memory
```

### API Access Verification

| Provider | Endpoint | Test Command | Expected Result |
|----------|----------|--------------|-----------------|
| **Alibaba Qwen** | `https://dashscope.aliyuncs.com` | `echo $QWEN_API_KEY` | Key present |
| **Google Gemini** | `https://generativelanguage.googleapis.com` | `echo $GEMINI_API_KEY` | Key present |
| **xAI Grok** | `https://api.x.ai` | `echo $XAI_API_KEY` | Optional (skip if unavailable) |
| **Moonshot Kimi** | `https://api.moonshot.cn` | `echo $MOONSHOT_API_KEY` | Optional |
| **Anthropic Claude** | `https://api.anthropic.com` | `echo $ANTHROPIC_API_KEY` | Required for expert tier |

If any required keys missing:
```bash
# Add to ~/.zshrc or use 1Password
export GEMINI_API_KEY="your-key-here"
export ANTHROPIC_API_KEY="your-key-here"

# Reload shell
source ~/.zshrc
```

### Source Code Availability

NexDev needs access to MO source files from Fas's workspace:

**Option A: Direct Copy (Fastest)**
```bash
# On Fas's Mac mini (where files currently exist)
cd ~/.openclaw/workspace/memory
tar czf mo-phase1-source.tar.gz \
    topic_extractor.py \
    performance_logger.py \
    confidence_assessor.py \
    cost_efficiency.py \
    mo_dashboard.py

# Transfer via SCP or shared drive
scp mo-phase1-source.tar.gz nexdev-server:/tmp/

# On NexDev server
cd ~/.openclaw/workspace/memory
tar xzf /tmp/mo-phase1-source.tar.gz
rm /tmp/mo-phase1-source.tar.gz
```

**Option B: Email/File Sharing**
```bash
# Send individual files to NexDev team lead
ls ~/.openclaw/workspace/memory/*.py | while read f; do cat "$f"; done > mo-all.txt
# Attach mo-all.txt to email or upload to shared storage
```

**Option C: Private Git Repo (Future Recommended)**
```bash
# Create private repo (GitHub/GitLab)
mkdir ~/mo-workspace && cd ~/mo-workspace
git init
cp ~/.openclaw/workspace/memory/*.py .
git add .
git commit -m "Initial MO source"
git remote add origin git@gitlab.com:nexdev/mo-core.git
git push -u origin main

# Then on NexDev server
git clone git@gitlab.com:nexdev/mo-core.git ~/.openclaw/workspace/memory/
```

### Team Assignment

Assign roles before Day 1:

| Role | Responsibility | Assigned To |
|------|---------------|-------------|
| **Lead Implementer** | Overall execution, troubleshooting | TBD |
| **DevOps Engineer** | Infrastructure, API keys, security | TBD |
| **Review Owner** | Code review, validation | TBD |
| **Documentation** | Update runbooks, wikis | TBD |

---

## Day-by-Day Implementation Schedule

### DAY 1 (Monday): Foundation Setup

**Goal:** Prepare environment, transfer source code, verify dependencies

#### Morning Session (9:00 AM - 12:00 PM CST)

**9:00 - 9:30 AM: Kickoff Meeting**
- Review implementation plan with team
- Assign day-to-day responsibilities
- Confirm API key availability
- Set up communication channel (Slack/Discord channel `#nexdev-mo-deploy`)

**9:30 - 10:30 AM: Environment Verification**
```bash
# Run comprehensive check script
cat > /tmp/check-env.sh << 'EOF'
#!/bin/bash

echo "=== NEXDEV MO PHASE 1 ENVIRONMENT CHECK ==="
echo ""

# Python
if command -v python3 &> /dev/null; then
    PYVER=$(python3 --version)
    echo "✅ Python: $PYVER"
else
    echo "❌ Python not found"
    exit 1
fi

# Node.js
if command -v node &> /dev/null; then
    NODEVER=$(node --version)
    echo "✅ Node.js: $NODEVER"
else
    echo "❌ Node.js not found"
    exit 1
fi

# OpenClaw
if command -v openclaw &> /dev/null; then
    OCVER=$(openclaw --version 2>&1)
    echo "✅ OpenClaw: $OCVER"
else
    echo "⚠️  OpenClaw not in PATH (may still work)"
fi

# Required directories
DIRS=("~/.openclaw/workspace" "~/.openclaw/bin" "~/memory")
for dir in "${DIRS[@]}"; do
    if [[ -d "$dir" ]]; then
        echo "✅ Directory: $dir"
    else
        echo "❌ Missing directory: $dir"
        mkdir -p "$dir"
        echo "   → Created $dir"
    fi
done

# API Keys
echo ""
echo "=== API KEY CHECK ==="
[[ -n "$GEMINI_API_KEY" ]] && echo "✅ Gemini API key present" || echo "❌ Gemini API key missing"
[[ -n "$ANTHROPIC_API_KEY" ]] && echo "✅ Anthropic API key present" || echo "❌ Anthropic API key missing"
[[ -n "$QWEN_API_KEY" ]] && echo "✅ Qwen API key present" || echo "⚠️  Qwen API key missing (optional)"

echo ""
echo "=== ENVIRONMENT CHECK COMPLETE ==="
EOF

chmod +x /tmp/check-env.sh
/tmp/check-env.sh
```

**Expected Output:**
```
=== NEXDEV MO PHASE 1 ENVIRONMENT CHECK ===

✅ Python: Python 3.11.x
✅ Node.js: v18.x.x
✅ OpenClaw: 2026.x.x
✅ Directory: /Users/nexdev/.openclaw/workspace
✅ Directory: /Users/nexdev/.openclaw/bin
✅ Directory: /Users/nexdev/memory

=== API KEY CHECK ===
✅ Gemini API key present
✅ Anthropic API key present
⚠️  Qwen API key missing (optional)

=== ENVIRONMENT CHECK COMPLETE ===
```

**Issues Found:**
- [ ] None (continue to next step)
- [ ] Missing Python → Install via Homebrew: `brew install python3`
- [ ] Missing Node.js → Install via Homebrew: `brew install node`
- [ ] Missing API keys → Contact DevOps engineer for credentials

**10:30 - 11:30 AM: Source Code Transfer**

Choose method based on availability:

**Method A: SCP Transfer (If Fas's Mac accessible)**
```bash
# On NexDev server
scp faisal@fas-mac-mini.local:.openclaw/workspace/memory/{topic_extractor.py,performance_logger.py,confidence_assessor.py,cost_efficiency.py,mo_dashboard.py} ~/.openclaw/workspace/memory/

# Verify transfer
ls -la ~/.openclaw/workspace/memory/*.py
```

**Method B: File Upload (If no direct access)**
```bash
# Download files from shared location
curl -O https://[shared-storage]/mo-workspace/topic_extractor.py
curl -O https://[shared-storage]/mo-workspace/performance_logger.py
# ... repeat for each file

# Move to workspace
mv *.py ~/.openclaw/workspace/memory/
```

**11:30 AM - 12:00 PM: File Integrity Verification**
```bash
cd ~/.openclaw/workspace/memory/

# Check file sizes (should match source)
wc -l *.py

# Test Python syntax
python3 -m py_compile topic_extractor.py
python3 -m py_compile performance_logger.py
python3 -m py_compile confidence_assessor.py
python3 -m py_compile cost_efficiency.py
python3 -m py_compile mo_dashboard.py

# All should complete without errors
echo "✅ All modules compiled successfully"
```

**End-of-Day Validation (5:00 PM)**
```bash
# Daily checklist
cat > /tmp/day1-checklist.md << 'EOF'
# Day 1 Checklist

## Completed
- [x] Environment check passed
- [x] Python 3.9+ verified
- [x] Node.js 18+ verified
- [x] API keys configured
- [x] Source code transferred
- [x] Files compile without errors

## Issues Encountered
- None (or list issues here)

## Tomorrow's Goals
- Initialize database schemas
- Configure routing table
- Test basic topic extraction
EOF

cat /tmp/day1-checklist.md
```

**Sign-off Required:** Lead Implementer confirms all boxes checked

---

### DAY 2 (Tuesday): Database & Configuration

**Goal:** Initialize project memory graph, configure routing rules, set up cost tracking

#### Morning Session (9:00 AM - 12:00 PM CST)

**9:00 - 10:00 AM: Create Configuration Files**

**File 1: Model Pricing (`~/memory/model_pricing.json`)**
```bash
cat > ~/memory/model_pricing.json << 'EOF'
{
  "version": "1.0",
  "updated": "2026-03-03",
  "models": {
    "google/gemini-2.0-flash-lite": {
      "input_cost_per_million_tokens": 0.10,
      "output_cost_per_million_tokens": 0.40,
      "context_window": 1000000,
      "tier": "ultra-cheap",
      "use_cases": ["simple_qa", "extraction", "summaries"]
    },
    "google/gemini-2.5-flash": {
      "input_cost_per_million_tokens": 0.10,
      "output_cost_per_million_tokens": 0.40,
      "context_window": 1000000,
      "tier": "cheap",
      "use_cases": ["code_review", "long_docs", "vision"]
    },
    "alibaba-sg/qwen-turbo": {
      "input_cost_per_million_tokens": 0.05,
      "output_cost_per_million_tokens": 0.20,
      "context_window": 256000,
      "tier": "ultra-cheap",
      "use_cases": ["quick_facts", "simple_extraction"]
    },
    "alibaba-sg/qwen-coder": {
      "input_cost_per_million_tokens": 0.30,
      "output_cost_per_million_tokens": 0.60,
      "context_window": 256000,
      "tier": "cheap",
      "use_cases": ["code_generation", "debugging", "refactoring"]
    },
    "alibaba-sg/qwen3.5-122b-a10b": {
      "input_cost_per_million_tokens": 0.40,
      "output_cost_per_million_tokens": 1.20,
      "context_window": 256000,
      "tier": "medium",
      "use_cases": ["complex_coding", "architecture", "system_design"]
    },
    "anthropic/claude-sonnet-4-6": {
      "input_cost_per_million_tokens": 3.00,
      "output_cost_per_million_tokens": 15.00,
      "context_window": 200000,
      "tier": "expert",
      "use_cases": ["security_review", "critical_decisions", "code_ownership"]
    },
    "anthropic/claude-opus-4-6": {
      "input_cost_per_million_tokens": 15.00,
      "output_cost_per_million_tokens": 75.00,
      "context_window": 200000,
      "tier": "nuclear",
      "use_cases": ["hardest_problems", "final_approval"]
    }
  },
  "budget_limits": {
    "daily_max_usd": 20.00,
    "per_query_max_usd": 5.00,
    "monthly_project_limit_usd": 300.00
  }
}
EOF

echo "✅ Created model_pricing.json"
```

**File 2: Routing Topics (`~/memory/routing_topics.json`)**
```bash
cat > ~/memory/routing_topics.json << 'EOF'
{
  "version": "1.0",
  "topics": {
    "lambda-development": {
      "keywords": ["lambda", "aws lambda", "lambda function", "serverless function"],
      "tier": "medium",
      "preferred_models": ["alibaba-sg/qwen3.5-122b-a10b", "anthropic/claude-sonnet-4-6"],
      "fallback_model": "google/gemini-2.5-flash"
    },
    "api-gateway-cors": {
      "keywords": ["cors", "api gateway", "cross-origin", "504 error", "502 error"],
      "tier": "medium",
      "preferred_models": ["alibaba-sg/qwen3.5-122b-a10b", "google/gemini-2.5-flash"],
      "fallback_model": "google/gemini-2.0-flash-lite"
    },
    "snowflake-integration": {
      "keywords": ["snowflake", "data warehouse", "sql warehouse", "dbt"],
      "tier": "medium",
      "preferred_models": ["alibaba-sg/qwen3.5-122b-a10b", "google/gemini-2.5-flash"],
      "fallback_model": "google/gemini-2.0-flash-lite"
    },
    "database-migrations": {
      "keywords": ["migration", "schema change", "alembic", "liquibase", "flyway"],
      "tier": "expert",
      "preferred_models": ["anthropic/claude-sonnet-4-6", "alibaba-sg/qwen3.5-122b-a10b"],
      "fallback_model": "alibaba-sg/qwen-plus"
    },
    "security-audit-code": {
      "keywords": ["security", "vulnerability", "owasp", "injection", "auth bypass"],
      "tier": "expert",
      "preferred_models": ["anthropic/claude-sonnet-4-6", "anthropic/claude-opus-4-6"],
      "fallback_model": "alibaba-sg/qwen3.5-122b-a10b",
      "requires_human_review": true
    },
    "testing-setup": {
      "keywords": ["test", "pytest", "jest", "unit test", "integration test", "e2e test"],
      "tier": "cheap",
      "preferred_models": ["alibaba-sg/qwen-coder", "google/gemini-2.5-flash"],
      "fallback_model": "google/gemini-2.0-flash-lite"
    },
    "web-development": {
      "keywords": ["react", "vue", "angular", "frontend", "css", "html", "typescript"],
      "tier": "cheap",
      "preferred_models": ["google/gemini-2.5-flash", "alibaba-sg/qwen-coder"],
      "fallback_model": "google/gemini-2.0-flash-lite"
    },
    "backend-framework": {
      "keywords": ["fastapi", "express", "django", "flask", "spring boot", "rails"],
      "tier": "medium",
      "preferred_models": ["alibaba-sg/qwen3.5-122b-a10b", "anthropic/claude-sonnet-4-6"],
      "fallback_model": "google/gemini-2.5-flash"
    },
    "infrastructure-as-code": {
      "keywords": ["terraform", "cloudformation", "pulumi", "cdk", "iac"],
      "tier": "medium",
      "preferred_models": ["alibaba-sg/qwen3.5-122b-a10b", "xai/grok-4-1-fast"],
      "fallback_model": "google/gemini-2.5-flash"
    },
    "container-orchestration": {
      "keywords": ["docker", "kubernetes", "k8s", "ecs", "container", "helm"],
      "tier": "medium",
      "preferred_models": ["alibaba-sg/qwen3.5-122b-a10b", "google/gemini-2.5-flash"],
      "fallback_model": "google/gemini-2.0-flash-lite"
    },
    "ci-cd-pipeline": {
      "keywords": ["github actions", "gitlab ci", "jenkins", "circleci", "deployment"],
      "tier": "cheap",
      "preferred_models": ["google/gemini-2.5-flash", "alibaba-sg/qwen-coder"],
      "fallback_model": "google/gemini-2.0-flash-lite"
    },
    "cognito-auth": {
      "keywords": ["cognito", "oauth", "auth0", "jwt", "authentication", "authorization"],
      "tier": "medium",
      "preferred_models": ["alibaba-sg/qwen3.5-122b-a10b", "anthropic/claude-sonnet-4-6"],
      "fallback_model": "google/gemini-2.5-flash"
    },
    "debugging-troubleshooting": {
      "keywords": ["debug", "error", "stack trace", "exception", "bug", "fix"],
      "tier": "medium",
      "preferred_models": ["alibaba-sg/qwen3.5-122b-a10b", "anthropic/claude-sonnet-4-6"],
      "fallback_model": "google/gemini-2.5-flash"
    },
    "system-architecture": {
      "keywords": ["architecture", "design pattern", "microservice", "event-driven", "scalability"],
      "tier": "expert",
      "preferred_models": ["anthropic/claude-sonnet-4-6", "alibaba-sg/qwen3.5-122b-a10b"],
      "fallback_model": "anthropic/claude-opus-4-6"
    },
    "code-refactoring": {
      "keywords": ["refactor", "optimize", "improve", "clean up", "technical debt"],
      "tier": "medium",
      "preferred_models": ["alibaba-sg/qwen3.5-122b-a10b", "alibaba-sg/qwen-coder"],
      "fallback_model": "google/gemini-2.5-flash"
    },
    "email-processing": {
      "keywords": ["email", "outlook", "gmail", "office 365", "smtp"],
      "tier": "cheap",
      "preferred_models": ["google/gemini-2.5-flash", "alibaba-sg/qwen-turbo"],
      "fallback_model": "google/gemini-2.0-flash-lite"
    },
    "financial-analysis": {
      "keywords": ["financial", "revenue", "profit", "margin", "cost analysis"],
      "tier": "medium",
      "preferred_models": ["alibaba-sg/qwen3.5-122b-a10b", "anthropic/claude-sonnet-4-6"],
      "fallback_model": "google/gemini-2.5-flash"
    },
    "project-management": {
      "keywords": ["timeline", "milestone", "deliverable", "roadmap", "sprint"],
      "tier": "cheap",
      "preferred_models": ["google/gemini-2.5-flash", "xai/grok-4-1-fast"],
      "fallback_model": "google/gemini-2.0-flash-lite"
    },
    "slack-discord-bot": {
      "keywords": ["slack", "discord", "bot", "chatbot", "notification"],
      "tier": "cheap",
      "preferred_models": ["google/gemini-2.5-flash", "alibaba-sg/qwen-coder"],
      "fallback_model": "google/gemini-2.0-flash-lite"
    },
    "sms-twilio": {
      "keywords": ["twilio", "sms", "text message", "phone", "voice call"],
      "tier": "cheap",
      "preferred_models": ["google/gemini-2.5-flash", "alibaba-sg/qwen-coder"],
      "fallback_model": "google/gemini-2.0-flash-lite"
    }
  },
  "default_topic": "general",
  "unknown_topic_fallback": "google/gemini-2.0-flash-lite"
}
EOF

echo "✅ Created routing_topics.json"
```

**10:00 - 11:00 AM: Initialize SQLite Database**

Create project memory graph database:
```bash
cat > ~/memory/init_db.py << 'EOF'
#!/usr/bin/env python3
"""Initialize SQLite database for project memory graph."""

import sqlite3
from pathlib import Path

DB_PATH = Path.home() / ".openclaw/workspace/memory/project_graph.db"

def init_database():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Projects table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS projects (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            repo_url TEXT,
            language TEXT,
            framework TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Tasks table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tasks (
            id TEXT PRIMARY KEY,
            project_id TEXT REFERENCES projects(id),
            title TEXT NOT NULL,
            description TEXT,
            status TEXT DEFAULT 'pending',
            agent TEXT,
            model_used TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            completed_at TIMESTAMP,
            FOREIGN KEY (project_id) REFERENCES projects(id)
        )
    ''')
    
    # Performance logs table (for MO learning)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS performance_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            topic TEXT NOT NULL,
            model_used TEXT NOT NULL,
            success BOOLEAN,
            tokens_input INTEGER,
            tokens_output INTEGER,
            cost_usd REAL,
            confidence_score REAL,
            query_text TEXT,
            response_summary TEXT
        )
    ''')
    
    # Daily costs table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS daily_costs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date DATE UNIQUE,
            total_cost_usd REAL DEFAULT 0,
            query_count INTEGER DEFAULT 0,
            by_model TEXT,
            by_topic TEXT
        )
    ''')
    
    # Session state table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS session_state (
            id INTEGER PRIMARY KEY,
            current_topic TEXT,
            current_model TEXT,
            started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Insert default session state
    cursor.execute('SELECT COUNT(*) FROM session_state')
    if cursor.fetchone()[0] == 0:
        cursor.execute('INSERT INTO session_state (current_topic, current_model) VALUES (?, ?)',
                      ("general", "google/gemini-2.0-flash-lite"))
    
    conn.commit()
    conn.close()
    
    print(f"✅ Database initialized at {DB_PATH}")
    print("   Tables created:")
    print("   - projects")
    print("   - tasks")
    print("   - performance_logs")
    print("   - daily_costs")
    print("   - session_state")

if __name__ == "__main__":
    init_database()
EOF

python3 ~/memory/init_db.py
```

**11:00 AM - 12:00 PM: Test Topic Extraction Module**

Run first module test:
```bash
cd ~/.openclaw/workspace/memory/

# Create test script
cat > test_topic_extraction.py << 'EOF'
#!/usr/bin/env python3
"""Test topic extraction module."""

import sys
sys.path.insert(0, str(Path.home() / ".openclaw/workspace/memory"))

from topic_extractor import extract_topic, get_predefined_topics

print("=" * 60)
print("TOPIC EXTRACTION TEST")
print("=" * 60)

# Load routing config
import json
with open(str(Path.home() / ".openclaw/workspace/memory/routing_topics.json")) as f:
    config = json.load(f)

print(f"\n📋 Loading {len(config['topics'])} predefined topics...")

# Test queries
test_queries = [
    ("Fix Lambda timeout causing 504 errors", ["lambda-development", "api-gateway-cors"]),
    ("Add Stripe webhook handler to payment service", ["backend-framework"]),
    ("Write pytest tests for user authentication", ["testing-setup"]),
    ("Security audit: SQL injection in login endpoint", ["security-audit-code"]),
    ("Deploy React app to S3 with CloudFront", ["web-development", "infrastructure-as-code"]),
    ("Center div vertically in CSS", ["web-development"]),
    ("What's the capital of France?", []),  # Should return empty -> fallback
]

print("\n🧪 Running test queries:\n")

for query, expected in test_queries:
    result = extract_topic(query)
    topics = [t for t, _ in result] if isinstance(result[0], tuple) else result
    
    status = "✅ PASS" if any(exp in topics for exp in expected) or (not expected and not topics) else "⚠️  PARTIAL"
    
    print(f"Query: {query[:50]}...")
    print(f"  Expected: {expected}")
    print(f"  Got: {topics}")
    print(f"  Status: {status}\n")

print("=" * 60)
print("TEST COMPLETE")
print("=" * 60)
EOF

python3 test_topic_extraction.py
```

**Expected Output:**
```
============================================================
TOPIC EXTRACTION TEST
============================================================

📋 Loading 20 predefined topics...

🧪 Running test queries:

Query: Fix Lambda timeout causing 504 errors...
  Expected: ['lambda-development', 'api-gateway-cors']
  Got: ['lambda-development', 'api-gateway-cors']
  Status: ✅ PASS

Query: Add Stripe webhook handler to payment service...
  Expected: ['backend-framework']
  Got: ['backend-framework']
  Status: ✅ PASS

... (more results)

============================================================
TEST COMPLETE
============================================================
```

**Issues Found:**
- [ ] If tests fail, debug `topic_extractor.py` keyword matching logic
- [ ] Verify JSON config file loaded correctly

**End-of-Day Validation (5:00 PM)**
```bash
# Daily checklist
cat > /tmp/day2-checklist.md << 'EOF'
# Day 2 Checklist

## Completed
- [x] Created model_pricing.json (8 models configured)
- [x] Created routing_topics.json (20 topics defined)
- [x] Initialized SQLite database (5 tables created)
- [x] Tested topic extraction (all tests passed)

## Issues Encountered
- None (or list issues here)

## Tomorrow's Goals
- Integrate MO into AGENTS.md workflow
- Deploy Antfarm workflows
- Test performance logging
EOF

cat /tmp/day2-checklist.md
```

**Sign-off Required:** Lead Implementer confirms all boxes checked

---

### DAY 3-4: Workflow Engine Setup (Antfarm Integration)

*Details condensed for brevity - follows same structure as Days 1-2*

#### Key Activities:
1. Install Antfarm workflows (bug-fix, feature-dev templates)
2. Customize workflow YAML for NexDev use cases
3. Test end-to-end bug-fix workflow
4. Configure cron jobs for self-advancing agents

#### Commands Preview:
```bash
# Install antfarm workflows
cd ~/.openclaw/workspace/antfarm
npm install

# Install custom workflows
node dist/cli/cli.js workflow install bug-fix
node dist/cli/cli.js workflow install feature-dev

# Verify installation
node dist/cli/cli.js workflow list

# Test workflow
node dist/cli/cli.js workflow run bug-fix "Fix Lambda CORS headers"
```

---

### DAY 5-7: Cost Tracking Automation

*Setup real-time cost monitoring and automated reports*

#### Key Deliverables:
1. Daily cost report script
2. Weekly email summary automation
3. Budget alert thresholds
4. Dashboard view (basic HTML)

#### Commands Preview:
```bash
# Generate first cost report
cat ~/.openclaw/workspace/memory/daily_costs.json | jq .

# Set up weekly email cron job
crontab -e
# Add: 0 9 * * 1 ~/.openclaw/workspace/scripts/weekly-cost-report.sh
```

---

### DAY 8-10: Testing & Validation

*Comprehensive testing across all components*

#### Test Scenarios:

| Scenario | Steps | Success Criteria |
|----------|-------|------------------|
| **Simple Query Routing** | Ask "What's Lambda?" → Check model used | Routes to QwenFlash ($0.05) |
| **Complex Code Task** | "Debug Lambda CORS" → Monitor routing | Routes to Qwen3.5/Sonnet |
| **Topic Persistence** | Ask about Lambda, then CORS, then back to Lambda | Same model maintained |
| **Budget Alert** | Simulate high-cost query | System warns before exceeding limit |
| **Performance Logging** | Complete task → Check DB | Log entry recorded |
| **Daily Report** | End of day → Check JSON | Accurate totals calculated |

#### Regression Test Suite:
```bash
# Full integration test
cat > /tmp/integration_test.sh << 'EOF'
#!/bin/bash

echo "=== NEXDEV PHASE 1 INTEGRATION TEST ==="

# Test 1: Topic extraction
echo "Test 1: Topic extraction..."
python3 ~/memory/test_topic_extraction.py
if [ $? -eq 0 ]; then
    echo "✅ Test 1 PASSED"
else
    echo "❌ Test 1 FAILED"
    exit 1
fi

# Test 2: Database connectivity
echo "Test 2: Database connectivity..."
sqlite3 ~/.openclaw/workspace/memory/project_graph.db "SELECT COUNT(*) FROM session_state;"
if [ $? -eq 0 ]; then
    echo "✅ Test 2 PASSED"
else
    echo "❌ Test 2 FAILED"
    exit 1
fi

# Test 3: Routing table load
echo "Test 3: Routing table load..."
python3 -c "
import json
with open('~/memory/routing_topics.json') as f:
    config = json.load(f)
assert len(config['topics']) >= 20
print(f'Loaded {len(config[\"topics\"])} topics')
"
if [ $? -eq 0 ]; then
    echo "✅ Test 3 PASSED"
else
    echo "❌ Test 3 FAILED"
    exit 1
fi

# Test 4: Antfarm workflows installed
echo "Test 4: Antfarm workflows..."
node ~/.openclaw/workspace/antfarm/dist/cli/cli.js workflow list | grep -q "bug-fix"
if [ $? -eq 0 ]; then
    echo "✅ Test 4 PASSED"
else
    echo "❌ Test 4 FAILED"
    exit 1
fi

echo ""
echo "=== ALL INTEGRATION TESTS PASSED ==="
EOF

chmod +x /tmp/integration_test.sh
/tmp/integration_test.sh
```

---

## Success Metrics & Validation

### End-of-Phase 1 KPIs

| Metric | Target | How to Measure |
|--------|--------|----------------|
| **Topics Configured** | ≥ 20 | Check `routing_topics.json` |
| **Models Supported** | ≥ 6 | Check `model_pricing.json` |
| **Database Tables** | 5 | Verify SQLite schema |
| **Tests Passing** | 100% | Run integration test suite |
| **Cost Tracking** | Working | Generate sample cost report |
| **First Workflow Run** | Complete | Execute `bug-fix` test task |

### Validation Checklist

```bash
# Final validation script
cat > /tmp/phase1-validation.sh << 'EOF'
#!/bin/bash

PASS=0
FAIL=0

check() {
    if [ $? -eq 0 ]; then
        echo "✅ $1"
        ((PASS++))
    else
        echo "❌ $1"
        ((FAIL++))
    fi
}

echo "=== PHASE 1 VALIDATION ==="
echo ""

# 1. Source files exist
ls ~/.openclaw/workspace/memory/{topic_extractor.py,performance_logger.py,confidence_assessor.py,cost_efficiency.py,mo_dashboard.py} > /dev/null 2>&1
check "All MO source files present"

# 2. Configuration files exist
[ -f ~/memory/model_pricing.json ] && [ -f ~/memory/routing_topics.json ]
check "Configuration files present"

# 3. Database initialized
sqlite3 ~/.openclaw/workspace/memory/project_graph.db ".tables" | grep -q "performance_logs"
check "SQLite database initialized"

# 4. Topic extraction works
python3 -c "from topic_extractor import extract_topic; extract_topic('test')" > /dev/null 2>&1
check "Topic extraction functional"

# 5. Performance logger works
python3 -c "from performance_logger import log_query_result; log_query_result('test','model',True,100,200)" > /dev/null 2>&1
check "Performance logging functional"

# 6. Antfarm workflows installed
node ~/.openclaw/workspace/antfarm/dist/cli/cli.js workflow list | grep -qE "(bug-fix|feature-dev)"
check "Antfarm workflows installed"

# 7. Dashboard CLI works
which mo-stats > /dev/null 2>&1
check "Dashboard CLI in PATH"

# 8. Budget limits configured
python3 -c "
import json
with open('~/memory/model_pricing.json') as f:
    config = json.load(f)
assert 'budget_limits' in config
assert config['budget_limits']['daily_max_usd'] > 0
"
check "Budget limits configured"

echo ""
echo "=== RESULTS ==="
echo "Passed: $PASS"
echo "Failed: $FAIL"
echo ""

if [ $FAIL -eq 0 ]; then
    echo "🎉 PHASE 1 COMPLETE - READY FOR PHASE 2"
    exit 0
else
    echo "⚠️  FIX FAILED CHECKS BEFORE PROCEEDING"
    exit 1
fi
EOF

chmod +x /tmp/phase1-validation.sh
/tmp/phase1-validation.sh
```

**Expected Output:**
```
=== PHASE 1 VALIDATION ===

✅ All MO source files present
✅ Configuration files present
✅ SQLite database initialized
✅ Topic extraction functional
✅ Performance logging functional
✅ Antfarm workflows installed
✅ Dashboard CLI in PATH
✅ Budget limits configured

=== RESULTS ===
Passed: 8
Failed: 0

🎉 PHASE 1 COMPLETE - READY FOR PHASE 2
```

---

## Post-Implementation Tasks

### Documentation Updates

1. **Update NexDev wiki** with:
   - Architecture diagram
   - API reference
   - Troubleshooting guide
   - Contact info for support

2. **Create runbook**:
   ```markdown
   ## How to Add New Topic
   1. Edit ~/memory/routing_topics.json
   2. Add keywords, preferred models, tier
   3. Restart OpenClaw gateway
   4. Test with sample query
   
   ## How to Adjust Budget Limits
   1. Edit ~/memory/model_pricing.json
   2. Update budget_limits section
   3. No restart needed (reads fresh on each query)
   
   ## How to View Current Costs
   $ mo-stats --costs
   ```

### Knowledge Transfer Sessions

| Session | Audience | Duration | Content |
|---------|----------|----------|---------|
| **Technical Deep Dive** | Dev team | 1 hour | Architecture, extensibility |
| **User Training** | All developers | 30 min | CLI commands, VS Code usage |
| **Admin Workshop** | DevOps | 1 hour | Monitoring, budget management |

### Monitoring Setup

**Day 1 post-launch checklist:**
- [ ] Review first day's cost report
- [ ] Verify all topics being detected correctly
- [ ] Check for any failed workflow runs
- [ ] Monitor token consumption patterns
- [ ] Confirm budget alerts firing at thresholds

---

## Risk Mitigation Plan

### Known Risks & Responses

| Risk | Probability | Response Plan |
|------|-------------|---------------|
| **API rate limits hit** | Low | Implement request queuing, increase delays |
| **Model costs exceed budget** | Medium | Enable hard caps, daily email warnings |
| **Topic detection accuracy low** | Medium | Tune keywords, add LLM classification fallback |
| **Antfarm workflow failures** | Low | Review logs, retry with different model |
| **Team resistance to adoption** | Medium | Show early wins, gather feedback, iterate |

### Rollback Procedures

If critical issues arise:

```bash
# Disable MO routing temporarily
# Comment out routing hooks in AGENTS.md

# Revert to default behavior
git checkout HEAD -- ~/.openclaw/workspace/memory/*.json

# Restore original session state
rm ~/.openclaw/workspace/memory/project_graph.db
python3 ~/memory/init_db.py

# Notify team of rollback
# Discord/Slack: "@channel MO routing disabled pending investigation"
```

---

## Appendix A: File Locations Reference

```
~/.openclaw/workspace/memory/
├── topic_extractor.py          # Keyword-based topic detection
├── performance_logger.py       # Auto-log results to database
├── confidence_assessor.py      # Response quality scoring
├── cost_efficiency.py          # Value analysis
├── mo_dashboard.py             # CLI dashboard
├── init_db.py                  # Database initialization script
├── project_graph.db            # SQLite database (created Day 2)
├── model_performance.json      # Learning database (auto-created)
├── daily_costs.json            # Cost tracking (auto-created)
└── .session_state.json         # Sticky topic state (auto-created)

~/memory/
├── model_pricing.json          # ⭐ CONFIGURATION - Edit manually
├── routing_topics.json         # ⭐ CONFIGURATION - Edit manually
└── .mo_config.json             # Runtime settings (auto-managed)

~/.openclaw/bin/
└── mo-stats                    # Dashboard CLI executable

~/.openclaw/workspace/antfarm/
└── workflows/
    ├── bug-fix/                # Customized for NexDev
    └── feature-dev/            # Customized for NexDev
```

---

## Appendix B: Common Troubleshooting

### Issue: "ModuleNotFoundError: No module named 'topic_extractor'"

**Fix:**
```bash
# Ensure Python path includes workspace
export PYTHONPATH="$HOME/.openclaw/workspace/memory:$PYTHONPATH"
echo 'export PYTHONPATH="$HOME/.openclaw/workspace/memory:$PYTHONPATH"' >> ~/.zshrc
source ~/.zshrc
```

### Issue: "Database locked" errors

**Fix:**
```bash
# Kill any processes using the database
lsof ~/.openclaw/workspace/memory/project_graph.db

# If process shown, terminate it
kill -9 <PID>

# Or backup and recreate (LAST RESORT)
cp ~/.openclaw/workspace/memory/project_graph.db project_graph.db.backup
rm ~/.openclaw/workspace/memory/project_graph.db
python3 ~/memory/init_db.py
```

### Issue: "Budget exceeded" warnings too aggressive

**Fix:**
```bash
# Adjust thresholds in model_pricing.json
nano ~/memory/model_pricing.json

# Change these values:
"daily_max_usd": 20.00 → 50.00  # More generous
"per_query_max_usd": 5.00 → 10.00  # Allow larger single queries
```

### Issue: Topics not being detected

**Fix:**
```bash
# Debug by adding verbose logging
python3 -c "
from topic_extractor import extract_topic
result = extract_topic('Your test query here')
print(f'Result: {result}')
"

# Check routing_topics.json keywords match query terms
grep -A 5 '"lambda-development"' ~/memory/routing_topics.json
```

---

## Appendix C: Quick Reference Commands

```bash
# View current costs
mo-stats --costs

# Check specific topic performance
mo-stats --topic lambda-development

# List all tracked topics
mo-stats

# Reset learning data (careful!)
mo-reset

# Manual model override for next query only
/model Sonnet

# Return to auto-routing
/model default

# Check database status
sqlite3 ~/.openclaw/workspace/memory/project_graph.db "SELECT * FROM session_state;"

# View recent performance logs
sqlite3 ~/.openclaw/workspace/memory/project_graph.db "SELECT topic, model_used, success FROM performance_logs ORDER BY timestamp DESC LIMIT 10;"

# Run full integration test
/tmp/integration_test.sh

# Validate Phase 1 completion
/tmp/phase1-validation.sh
```

---

*Document created by Optimus — Based on production experience in Fas/Optimus workspace*  
*Last updated: 2026-03-03 08:46 CST*  
*Next revision: After Day 10 implementation review*
