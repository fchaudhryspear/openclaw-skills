# OpenClaw Skills & Implementations

A comprehensive suite of production-grade skills and automation tools for AI agents, built on the OpenClaw platform.

## 📁 Repository Structure

```
openclaw-skills/
├── ai-cost-tracker/          # AI/API cost tracking & optimization
├── cross-service-monitor/    # Pipeline correlation across AWS/Snowflake/CRM
├── multi-company-switch/     # Context switching for 6 business entities  
├── proactive-monitoring/     # Real-time health monitoring & alerting
├── secrets-lifecycle/        # Secure credential rotation & expiration tracking
└── skills/                   # OpenClaw skill packages
    ├── memory-knowledge/     # Knowledge retention system
    ├── multi-company-switch/ # Company context switcher
    ├── proactive-monitoring/ # Health monitoring skill
    ├── hardened-aws-inspector/     # Read-only AWS auditing
    └── hardened-snowflake-connector/ # Read-only Snowflake queries
```

---

## 🚀 Quick Start

### Installation

```bash
# Clone repository
git clone https://github.com/Versatly/openclaw-skills.git
cd openclaw-skills

# Install Python dependencies (shared)
pip install cryptography psutil requests pyyaml python-dotenv

# Install Node.js dependencies (if needed)
npm install
```

### Configuration

1. **Set Environment Variables** (`.env` file):
```bash
# Telegram Alerts
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id

# Snowflake Monitoring
SNOWFLAKE_ACCOUNT=your_account_id
SNOWFLAKE_USER=your_service_account
SNOWFLAKE_PASSWORD=your_password

# AWS (if using CloudWatch integration)
AWS_ACCESS_KEY_ID=your_key
AWS_SECRET_ACCESS_KEY=your_secret

# Secrets Manager Master Password
SECRETS_MASTER_PASSWORD=your_secure_password
```

2. **Initialize Multi-Company Switch**:
```bash
python3 skills/multi-company-switch/scripts/company.py --init
```

3. **Setup Cost Tracker Paths**:
```bash
export COST_TRACKER_LOGS=~/openclaw/workspace/ai-cost-tracker/logs
```

---

## 📦 Components

### 1. AI Cost Tracker (`ai-cost-tracker/`)

**Purpose:** Track AI/API costs in real-time, detect anomalies, generate daily summaries.

**Features:**
- Real-time token usage tracking
- Cost calculation ($/1K tokens per model tier)
- Daily/weekly/monthly cost reports
- Email summaries with breakdowns
- Integration with OpenClaw's penny-pincher cascade

**Files:**
- `cost-tracker.js` - Core tracking module
- `daily-token-report.js` - Automated reporting
- `logs/ai-costs.jsonl` - Usage data storage

**Usage:**
```bash
./ai-cost-tracker/run-daily-report.sh
```

**Status:** ✅ Fixed paths, ready for testing

---

### 2. Cross-Service Monitor (`cross-service-monitor/`)

**Purpose:** Unified pipeline health monitoring across AWS → Snowflake → CRMs.

**Features:**
- Real-time service health checks (30-second intervals)
- Cascading failure detection & root cause analysis
- Alert routing via Slack/Telegram/Email
- Visual dashboard with live metrics
- REST API for programmatic access
- Docker deployment support

**Components:**
- `monitors/aws_monitor.py` - Lambda, SQS, CloudWatch
- `monitors/snowflake_monitor.py` - Queries, warehouses, security
- `monitors/crm_monitor.py` - HubSpot, Salesforce APIs
- `engine/correlator.py` - Pattern detection & correlation
- `dashboard/app.py` + `static/index.html` - Web UI

**Usage:**
```bash
cd cross-service-monitor
pip install -r requirements.txt
python main.py
# Open http://localhost:8080
```

**Status:** ✅ Complete (~3,450 lines of code)

---

### 3. Multi-Company Switcher (`multi-company-switch/`)

**Purpose:** Instant context switching between 6 business entities.

**Companies Supported:**
1. **Credologi** (Primary) - faisal@credologi.com 🔵
2. **Spearhead** - faisal@spearhead.io 🟢
3. **Utility Valet** - faisal@utilityvalet.io 🟡
4. **Flobase** - faisal@flobase.ai 🟣
5. **Starship Residential** - faisal@starshipresidential.com 🔴
6. **Dallas Partners** - faisal@dallaspartners.us ⚫

**Features:**
- `/company Credologi` - Switch company context
- Encrypted per-company credential storage
- Project directory isolation
- Automatic environment variable exports
- Email/CRM account switching
- Full audit logging

**Commands:**
```bash
# List all companies
./skills/multi-company-switch/scripts/company.sh list

# Switch to a company
./skills/multi-company-switch/scripts/company.sh set Credologi

# Get current context
./skills/multi-company-switch/scripts/company.sh current
```

**Status:** ✅ Complete with full README & SKILL.md

---

### 4. Proactive Monitoring (`proactive-monitoring/`)

**Purpose:** Real-time system health, cost anomaly detection, security posture monitoring.

**Monitors:**
- **Cost Anomalies** - Triggers at >$10/day AI spending
- **System Health** - CPU >90%, Memory >95%, Disk <10% free
- **Security** - SSH brute force, firewall status, network traffic
- **Network** - UniFi UDM PRO site monitoring (Greenbrier + Kansas)

**Alert Channels:**
- Telegram bot notifications
- Slack webhooks
- Email alerts

**Usage:**
```bash
# One-time check
python3 monitor.py --once

# Continuous monitoring (every 5 minutes)
python3 monitor.py --continuous --interval 300

# View dashboard
open dashboard.html
```

**Integration:** Set as cron job:
```bash
*/5 * * * * /usr/bin/python3 ~/openclaw/workspace/skills/proactive-monitoring/monitor.py >> logs/monitor.log 2>&1
```

**Status:** ✅ Complete with dashboard & shell scripts

---

### 5. Secrets Lifecycle Manager (`secrets-lifecycle/`)

**Purpose:** Secure credential storage with rotation scheduling & expiration alerts.

**Features:**
- AES-256-Fernet encryption
- PBKDF2 key derivation from master password
- API key expiration tracking (30/7/1 day warnings)
- Rotation schedule management
- Audit logging for compliance
- Secure file permissions (700/600)

**API Example:**
```python
from src.secret_manager import SecretManager

sm = SecretManager(data_dir="~/.openclaw/secrets", master_password="your_password")

# Store secret
sm.store("api-key", "sk-proj-abc123", {
    "expires": "2026-06-01",
    "service": "OpenAI",
    "notes": "Main workspace key"
})

# Retrieve secret
key = sm.retrieve("api-key")

# Check expirations
expiring = sm.get_expiring_soon(days=30)
```

**Files:**
- `src/secret_manager.py` - Core encryption & storage
- `scripts/rotation_tracker.py` - Expiration monitoring
- `data/secrets.enc.json` - Encrypted credentials

**Status:** ✅ Complete with encryption & lifecycle tracking

---

### 6. Knowledge Retention System (`skills/memory-knowledge/`)

**Purpose:** Capture lessons learned, searchable via `/remember` and `/recall`.

**Commands:**
```bash
# Store knowledge
/remember <topic> [context] [outcome:success|failure|partial] [link:project]

# Search knowledge base
/realmind <query>
/recall <query>
```

**Example:**
```bash
/remember "Snowflake MFA error" "MFA was enabled on service account" outcome:failure link:snowflake_connector
/realmind "snowflake connection"
# Returns: Lessons about MFA, correct credentials, workspace path fixes
```

**Storage:**
- `memory/lessons/` - Individual lesson markdown files
- `memory/knowledge-index.jsonl` - Searchable index
- `memory/access-logs.jsonl` - Audit trails

**File Format:**
```markdown
# Topic Title

- **Date:** YYYY-MM-DD HH:MM TZ
- **Outcome:** success | failure | partial
- **Project:** Project name or null
- **Tags:** [tag1, tag2]
- **Context:** What happened
- **Lesson Learned:** Key insight
- **Resolution Steps:** Actionable resolution
- **Related:** Links to related lessons
```

**Status:** ✅ Complete with SKILL.md & commands

---

## 🏗️ Hardened Skills

Read-only security-focused skills for external services:

### Hardened AWS Inspector (`skills/hardened-aws-inspector/`)

**Tools:**
- `list_ec2_instances.py` - EC2 inventory
- `list_s3_buckets.py` - S3 bucket listing
- `list_iam_users.py` - IAM user audit
- `list_amplify_apps.py` - Amplify app overview

**Security:**
- No write permissions
- Credentials from environment variables only
- Logs sanitized (no secrets)
- Rate limiting (100 req/min/IP)

### Hardened Snowflake Connector (`skills/hardened-snowflake-connector/`)

**Tools:**
- `list_databases.py` - Database inventory
- Future: schema inspection, query execution (read-only)

**Security:**
- Read-only role enforced
- Credentials via env vars (`SNOWFLAKE_*`)
- Service account without MFA
- Query results cached locally

---

## 🔒 Security Features

All implementations follow these security principles:

✅ **Encryption at Rest** - AES-256 for sensitive data  
✅ **Secure Permissions** - 600 files, 700 directories  
✅ **No Plaintext Secrets** - All credentials encrypted  
✅ **Audit Logging** - Every read/write operation logged  
✅ **Least Privilege** - Read-only access by default  
✅ **Input Sanitization** - Prevent injection attacks  
✅ **Rate Limiting** - Protect against abuse  
✅ **Master Password Derivation** - PBKDF2 for key generation  

---

## 📊 Deployment Options

### Option 1: Docker
```bash
docker build -t openclaw-skills .
docker run -d --name skills \
  -v ~/.openclaw:/root/.openclaw \
  -p 8080:8080 \
  openclaw-skills
```

### Option 2: Systemd Service
```ini
[Unit]
Description=OpenClaw Skills Monitor
After=network.target

[Service]
Type=simple
User=faisalshomemacmini
WorkingDirectory=/Users/faisalshomemacmini/.openclaw/workspace
ExecStart=/usr/bin/python3 /Users/faisalshomemacmini/.openclaw/workspace/cross-service-monitor/main.py
Restart=always

[Install]
WantedBy=multi-user.target
```

### Option 3: Cron Jobs
```bash
# Add to crontab (crontab -e)
*/5 * * * * cd /Users/faisalshomemacmini/.openclaw/workspace && python3 skills/proactive-monitoring/monitor.py --once
0 7 * * * cd /Users/faisalshomemacmini/.openclaw/workspace/ai-cost-tracker && ./run-daily-report.sh
```

---

## 🧪 Testing

Run test suites:
```bash
# Cross-service monitor tests
cd cross-service-monitor
pytest tests/

# Knowledge retention tests
cd skills/memory-knowledge
python -m unittest tests/

# Secrets manager tests
cd secrets-lifecycle
python -m unittest tests/test_secret_manager.py
```

---

## 📚 Documentation

- [Architecture Design](ARCHITECTURE.md) - System overview & patterns
- [Deployment Guide](DEPLOYMENT.md) - Production setup instructions
- [API Reference](API.md) - REST endpoints & parameters
- [Security Model](SECURITY.md) - Threat models & mitigations
- [Troubleshooting](TROUBLESHOOTING.md) - Common issues & solutions

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/improvement`)
3. Commit changes (`git commit -m 'Add feature X'`)
4. Push to branch (`git push origin feature/improvement`)
5. Open Pull Request

**Code Style:**
- Python: Black formatting, type hints preferred
- JavaScript: ESLint, JSDoc comments
- Tests: Minimum 80% coverage required

---

## 📄 License

Copyright © 2026 Versatly. All rights reserved.

Proprietary software for internal use only. Not for distribution.

---

## 🚦 Status

| Component | Status | Version | Last Updated |
|-----------|--------|---------|--------------|
| AI Cost Tracker | ✅ Ready | v1.0.0 | Mar 1, 2026 |
| Cross-Service Monitor | ✅ Ready | v1.0.0 | Mar 1, 2026 |
| Multi-Company Switch | ✅ Ready | v1.0.0 | Mar 1, 2026 |
| Proactive Monitoring | ✅ Ready | v1.0.0 | Mar 1, 2026 |
| Secrets Lifecycle | ✅ Ready | v1.0.0 | Mar 1, 2026 |
| Knowledge Retention | ✅ Ready | v1.0.0 | Mar 1, 2026 |
| AWS Inspector | ✅ Ready | v1.0.0 | Feb 28, 2026 |
| Snowflake Connector | ✅ Ready | v1.0.0 | Mar 1, 2026 |

---

## 📞 Support

Issues: https://github.com/Versatly/openclaw-skills/issues  
Docs: https://docs.openclaw.ai  
Community: https://discord.gg/clawd

Built with ⚡ by Optimus for Faisal Chaudhry & Versatly
