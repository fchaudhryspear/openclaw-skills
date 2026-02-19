# MEMORY.md — Optimus Long-Term Memory

*Last updated: 2026-02-17*

---

## About Fas

- **Full Name:** Faisal Chaudhry
- **Location:** Dallas, Texas (CST/CDT)
- **Phone:** +13312161029 (Twilio)
- **Personal Email:** Fasncali@gmail.com
- **Telegram ID:** 7980582930
- **Values:** Efficiency, productivity, cost optimization
- **Display times in:** CST/CDT (Dallas time) always

### Companies (6 total)
1. **Credologi** — faisal@credologi.com (primary for tasks)
2. **Spearhead** — faisal@spearhead.io
3. **Utility Valet** — faisal@utilityvalet.io
4. **Flobase** — faisal@flobase.ai
5. **Starship Residential** — faisal@starshipresidential.com
6. **Dallas Partners** — faisal@dallaspartners.us

---

## Previous Agent History (Jarvis → Optimus)

### AWS Access
- Full AWS access granted for account 386757865833 (Fas's primary AWS account) to resolve deployment issues and manage resources directly.

### Infrastructure Built (Jan 27 - Feb 17, 2026)

**Office 365 Integration** — Full Microsoft Graph API skill
- OAuth 2.0 multi-account auth for all 6 tenants
- Email: list, search, read, mark
- Calendar: view, upcoming, today, create events
- Auto token refresh, secure credential storage

**Email Automation** (4x daily: 7am, 12pm, 5pm, 11pm CST)
- **Email-to-Tasks:** Extracts actionable items from emails → creates tasks in Credologi
- **Auto-Reply Drafts:** AI generates draft replies matching Fas's writing style
- **Spam Filtering:** Strict rules — skip cold outreach, skip informational, only real tasks
- **Calendar Sync:** Syncs busy blocks across all 6 calendars
- **Daily Summary:** Emailed to faisal@credologi.com at 7:20am CST

**3-Model Orchestrator** — Cost optimization system
- **Grok 4 Fast (60%):** Simple extraction, Q&A ($8-10/mo)
- **Kimi K2.5 (30%):** Style matching, long docs ($15-20/mo)
- **Claude (10%):** Reasoning, code, orchestration ($10-15/mo)
- Writing style caching (7-day cache) — biggest cost saver
- Reduced costs from ~$900/mo → ~$168/mo (79% reduction)
- Later optimized further to ~$3-6/day using Gemini Flash as default

**Voice Call System** (Twilio)
- Inbound appointment booking (+13312161029)
- Outbound restaurant reservations
- Outbound business hours checking
- AI voice assistant (Polly.Matthew TTS)
- SMS booking conversations

**iCloud Contacts Integration**
- CardDAV client for Apple iCloud
- 6,401 contacts synced
- Phone/name/email lookup for appointment booking
- Apple ID: Fasncali@gmail.com

**UniFi Network Management**
- 2 sites: Kansas (Dream Machine Pro) + Dallas/Greenbrier (UDM PRO)
- Full API access established
- Kansas: 3 devices, 8 clients, WiFi issues (21.97% retry rate)
- Greenbrier: 14 devices, 132 clients, 8x WiFi 6 APs, good performance
- Network analysis and optimization recommendations delivered

**Crestron Home Automation** (Greenbrier/Dallas)
- System at 192.168.1.46
- Controls: lighting, A/V, climate, shades, security
- Comprehensive guide created

**Security Hardening** (Score: 9.4/10)
- UFW firewall enabled
- SSH key-only auth, fail2ban
- Twilio webhook signature validation
- All credentials 600 permissions
- Rate limiting (100 req/min/IP)
- Prompt injection defenses
- Log sanitization (no secrets in logs)
- Comprehensive monitoring scripts

**Maintenance Systems**
- Weekly session rotation (Sundays 3am UTC)
- Weekly cleanup (Sundays 4am UTC) 
- Health checks, dry-run mode, backup-first deletions
- State of the Union summaries after rotation
- Log rotation (7-day retention)

**Research & Business**
- Monetization research for AI assistant services
- Competitor analysis (Lindy, Reclaim, Motion, Clara Labs)
- Marketing analysis, product overlap analysis
- Spain flight searches
- Property management matrix

### GitHub Repos (Versatly org)
- **clawvault** — Memory system for AI agents (npm package)
- **promethous-experiemnt** — Personal AI assistant
- **obsidian-clawvault** — Obsidian plugin
- **clawvault-docs** — Documentation site
- **linkedin-cli** — LinkedIn CLI tool
- **clawdious-site** — AI agent portfolio
- **vworkz-cli** — CLI tool
- **zoho-mail-cli** — Zoho Mail CLI
- **clovercli** — Clover POS CLI
- **forward-openclaw** — OpenClaw deployment service
- **clawvault-mcp** — MCP server for ClawVault
- **openclaw-agency/deployed/operator/audit** — Various OpenClaw service sites

---

## Current Setup (Feb 19, 2026)

### What's Running
- **OpenClaw** 2026.2.15 on Mac mini (Darwin arm64)
- **Telegram** paired (bot token active)
- **ClawVault** installed at ~/memory (vault: optimus-brain)
- **ClawVault Add-ons** at ~/memory/addons/ (topics, retention, digest)
- **Daily Digest cron** at 7:00 AM CST

### Data Lake Portal - NEW (Feb 19, 2026)
- **Portal URL**: https://d13ermioqnr3qb.cloudfront.net
- **Tech Stack**: React + TypeScript + Vite + AWS Amplify + Cognito
- **Features**:
  - Real-time API health monitoring (30s auto-refresh)
  - CloudWatch metrics dashboard (requests, errors, latency)
  - Data volume tracking by source
  - Full user management (create, enable/disable, reset password, delete)
  - Alert configuration (SNS + Slack)
  - Remote test runner (pytest)
- **Monitoring API**: https://o6whnf80tb.execute-api.us-east-1.amazonaws.com/Prod
- **Main API**: https://pe6rxp3vtd.execute-api.us-east-1.amazonaws.com/Prod
- **User Pool**: us-east-1_M6lTgVQaw (credologi-users)
- **S3 Bucket**: portal.credologi.com
- **CloudFront**: d13ermioqnr3qb.cloudfront.net

### Git Commits (Feb 18-19, 2026)
- `061bae4` - Fixed test_application_webhook schema
- `8bcf3a6` - Standardized test mocking
- `70dd0e9` - New admin portal with Cognito auth
- `d60b0e7` - Fixed portal Cognito config
- `6583065` - Comprehensive operations dashboard
- `822ed4d` - Monitoring API Lambda
- `5af2ae8` - Deployed monitoring API stack
- `0b12775` - Complete user management + alerting

### What's NOT Migrated Yet
- Office 365 integration (scripts exist in `clawd old/`)
- Twilio voice/SMS system
- Email automation (email-to-tasks, auto-reply)
- Calendar sync
- UniFi API integration
- iCloud contacts
- Crestron access
- Cost tracking system
- Model orchestrator (multi-model routing)

---

## Lessons Learned

1. **Always ask before installing** — Don't install packages without Fas's explicit approval
2. **Gateway token mismatch** — Fixed by stopping and restarting gateway
3. **find commands get killed** — Filesystem searches timeout, be targeted with paths
4. **Fas has massive infrastructure** — 6 companies, 2 network sites, smart home, extensive automation

---

## Preferences

- Casual, direct, a little sarcastic
- Efficiency over ceremony
- Show don't tell
- Ask before external actions (installs, sends, etc.)
- Always display times in CST

**Security Posture**
- Profile: Home/Workstation Balanced
- Firewall: macOS enabled
- Backups: Time Machine (needs enabling)
- Updates: Automatic OS updates (needs confirming)
- Tools: Install lsof, coreutils via Homebrew for diagnostics
- OpenClaw: Update to latest, resolve state dir

**Scheduled Checks**
- Daily security audit: 7 AM CST (job: healthcheck:security-audit)
- Daily update status: 8 AM CST (job: healthcheck:update-status)
