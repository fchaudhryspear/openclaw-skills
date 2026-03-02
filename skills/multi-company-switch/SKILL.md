---
name: multi-company-switch
description: Manage 6 companies (Credologi, Spearhead, Utility Valet, Flobase, Starship, Dallas Partners) with context loading, email/CRM switching, project isolation, and secure credential separation. Usage: /company [company-name] [--list|--set|--reset|--show]
---

# Multi-Company Context Switcher

This skill enables seamless context switching between your 6 companies with isolated credentials, projects, and configurations.

## Companies Supported

1. **Credologi** — faisal@credologi.com (primary)
2. **Spearhead** — faisal@spearhead.io
3. **Utility Valet** — faisal@utilityvalet.io
4. **Flobase** — faisal@flobase.ai
5. **Starship Residential** — faisal@starshipresidential.com
6. **Dallas Partners** — faisal@dallaspartners.us

## Features

- **Context Loading**: Automatically loads company-specific configs, credentials, and project contexts
- **Email Switching**: Switches email accounts and SMTP/IMAP configurations per company
- **CRM Integration**: Company-specific CRM connections and API keys
- **Project Isolation**: Separate working directories and git repositories per company
- **Secure Credential Separation**: Encrypted credential storage with company-level isolation
- **Quick Commands**: Easy `/company` command interface for switching

## Usage

### List Available Companies
```bash
python3 skills/multi-company-switch/scripts/company.py --list
```

### Set Active Company
```bash
python3 skills/multi-company-switch/scripts/company.py --set Credologi
```

### Show Current Company Context
```bash
python3 skills/multi-company-switch/scripts/company.py --show
```

### Reset to Default (Credologi)
```bash
python3 skills/multi-company-switch/scripts/company.py --reset
```

## Security Model

- **Encrypted Storage**: All credentials stored in encrypted format using ClawVault
- **Company-Specific Keys**: Each company has separate encryption keys
- **Memory隔离**: Company context loaded only when active, cleared on switch
- **Audit Logging**: All company switches logged with timestamps

## Configuration Files

- `config.json` - Company mappings and default settings
- `credentials.enc` - Encrypted company-specific credentials
- `context/[company].json` - Company-specific workspace contexts
- `.env.[company]` - Environment variables per company

## Environment Variables Per Company

Each company context sets these environment variables:

- `COMPANY_NAME` - Active company identifier
- `COMPANY_EMAIL` - Primary email address
- `CREDLOGI_API_KEY` - (Credologi only)
- `SPEARHEAD_API_KEY` - (Spearhead only)
- And so on for each company...

## Project Directory Structure

```
~/.openclaw/companies/
├── credologi/
│   ├── projects/
│   ├── credentials.enc
│   └── context.json
├── spearhead/
│   ├── projects/
│   ├── credentials.enc
│   └── context.json
├── utility-valet/
│   ├── projects/
│   ├── credentials.enc
│   └── context.json
├── flobase/
│   ├── projects/
│   ├── credentials.enc
│   └── context.json
├── starship/
│   ├── projects/
│   ├── credentials.enc
│   └── context.json
└── dallas-partners/
    ├── projects/
    ├── credentials.enc
    └── context.json
```

## Integration Points

- **Telegram**: Can switch company context via `/company` commands
- **GitHub**: Switches GitHub token/context per company
- **Email**: Updates SMTP/IMAP settings automatically
- **CRM**: Loads company-specific CRM API credentials
- **AWS**: Switches AWS profiles if configured per company
