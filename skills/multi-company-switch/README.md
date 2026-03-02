# Multi-Company Context Switcher Skill

A comprehensive solution for managing 6 business entities with isolated contexts, credentials, and projects.

## 🏢 Companies Supported

1. **Credologi** (Primary) - faisal@credologi.com 🔵
2. **Spearhead** - faisal@spearhead.io 🟢
3. **Utility Valet** - faisal@utilityvalet.io 🟡
4. **Flobase** - faisal@flobase.ai 🟣
5. **Starship Residential** - faisal@starshipresidential.com 🔴
6. **Dallas Partners** - faisal@dallaspartners.us ⚫

## ✨ Features

- **Quick Context Switching**: Instantly switch between company contexts
- **Secure Credential Storage**: Encrypted, company-specific credential management
- **Project Isolation**: Separate project directories per company
- **Environment Variable Management**: Automatic environment variable exports
- **Email/CRM Switching**: Seamless email and CRM account switching
- **Audit Logging**: Full history of company switches
- **Telegram Integration**: Use `/company` commands in Telegram

## 🚀 Quick Start

### Initialize the System

```bash
cd /Users/faisalshomemacmini/.openclaw/workspace
python3 skills/multi-company-switch/scripts/company.py --init
```

### List Available Companies

```bash
python3 skills/multi-company-switch/scripts/company.py --list
```

Or use the shell helper:

```bash
./skills/multi-company-switch/scripts/company.sh list
```

### Switch to a Company

```bash
python3 skills/multi-company-switch/scripts/company.py --set Credologi
```

Or:

```bash
./skills/multi-company-switch/scripts/company.sh set Spearhead
```

### Show Current Context

```bash
python3 skills/multi-company-switch/scripts/company.py --show
```

## 📖 Usage Guide

### Shell Commands

The skill provides a convenient shell helper script:

```bash
# Basic usage
company                          # Show help
company list                     # List all companies
company set <company>           # Switch to company
company show                    # Show current context
company reset                   # Reset to default
company init                    # Initialize profiles
company env                     # Export environment variables
company creds store <key> <val> # Store a credential
company creds get <key>         # Get a credential
company creds list              # List credentials
```

### Python Scripts Directly

**Company Manager:**
```bash
python3 skills/multi-company-switch/scripts/company.py [options]
  --list    List all companies
  --set     Set active company
  --show    Show current context
  --reset   Reset to default
  --init    Initialize company profiles
```

**Credential Manager:**
```bash
python3 skills/multi-company-switch/scripts/credential_manager.py [command] [company] [key] [value]
  store <company> <key> <value>  # Store encrypted credential
  get <company> <key>            # Retrieve credential
  list <company>                 # List all credentials
  delete <company> <key>         # Delete credential
```

**Environment Loader:**
```bash
python3 skills/multi-company-switch/scripts/env_loader.py [command]
  export                       # Export environment variables
  list                         # List available companies
  set <company>                # Set company and export env vars
```

### Telegram Commands

Use in Telegram channel:

```
/company list          - Show all companies
/company set Credologi - Switch to Credologi
/company show          - Show current context
/company reset         - Reset to default
/company help          - Show help
```

## 🔐 Security Model

### Encrypted Credentials

All credentials are encrypted using Fernet (AES-128-CBC) encryption:

```bash
# Store a credential
company creds store credologi api_key "your-api-key-here"

# Retrieve it (you'll need the decryption key)
company creds get credologi api_key

# List all credentials
company creds list credologi
```

### Company Isolation

- **Separate directories**: Each company has its own directory under `~/.openclaw/workspace/companies/`
- **Encrypted keys**: Each company has its own encryption key stored securely
- **No cross-access**: Credentials from one company cannot be accessed when another is active
- **File permissions**: All sensitive files have 0o600 permissions (owner read/write only)

### Environment Variables

When you switch companies, the following variables are set:

```bash
export COMPANY_KEY="credologi"
export COMPANY_NAME="Credologi"
export COMPANY_EMAIL="faisal@credologi.com"
export COMPANY_WORKSPACE="/path/to/companies/credologi"
```

## 📁 Directory Structure

```
~/.openclaw/workspace/
├── skills/
│   └── multi-company-switch/
│       ├── SKILL.md
│       ├── config.json
│       └── scripts/
│           ├── company.py          # Main company manager
│           ├── company.sh          # Shell helper
│           ├── credential_manager.py
│           ├── env_loader.py
│           └── telegram_handler.py
└── companies/                      # Created on first run
    ├── .active_company             # Currently active company
    ├── .env_active                 # Active environment exports
    ├── config.json                 # Global configuration
    ├── .keys/                      # Encryption keys (separate per company)
    │   ├── credologi.key
    │   ├── spearhead.key
    │   └── ...
    ├── credologi/
    │   ├── credentials.json        # Encrypted credentials
    │   ├── context.json            # Company context
    │   └── projects/               # Company-specific projects
    ├── spearhead/
    │   ├── credentials.json
    │   ├── context.json
    │   └── projects/
    └── ... (other companies)
```

## ⚙️ Configuration

Edit `config.json` to customize behavior:

```json
{
  "settings": {
    "default_company": "credologi",
    "encryption_method": "aes-256-gcm",
    "auto_load_context": true,
    "context_persistence": true,
    "log_switches": true
  },
  "isolation_rules": {
    "separate_credentials": true,
    "separate_projects": true,
    "separate_env_vars": true,
    "cross_company_access": false
  }
}
```

## 🔄 Shell Integration

Add this to your `.zshrc` or `.bashrc`:

```bash
# Multi-Company Switch
alias company='/Users/faisalshomemacmini/.openclaw/workspace/skills/multi-company-switch/scripts/company.sh'

# Auto-load environment when switching companies
company_switch() {
    local company="$1"
    company set "$company"
    eval "$(python3 ~/.openclaw/workspace/skills/multi-company-switch/scripts/env_loader.py export)"
}
```

Then reload your shell:

```bash
source ~/.zshrc  # or source ~/.bashrc
```

Usage:

```bash
company switch Credologi  # Custom command that sets both context and env
```

## 🎯 Example Workflows

### Workflow 1: Morning Company Check-in

```bash
# List all companies and see what's active
company list

# Switch to primary company
company set Credologi

# Load environment
company env

# Verify
company show
```

### Workflow 2: Working Across Multiple Companies

```bash
# Start with Credologi
company set Credologi
git clone https://github.com/versatly/credologi-project.git

# Switch to Spearhead
company set Spearhead
git clone https://github.com/versatly/spearhead-project.git

# Back to Credologi
company set Credologi
# All Credologi environment variables and context are restored
```

### Workflow 3: Managing API Keys

```bash
# Store API key for Credologi
company creds store credologi openai_api_key "sk-..."

# Store API key for Spearhead
company creds store spearhead openai_api_key "sk-..."

# When working with each company, retrieve their specific key
company set Credologi
API_KEY=$(company creds get credologi openai_api_key | grep -v '^🔑')
```

## 🛠️ Advanced Usage

### Adding Projects to Company Context

```bash
python3 skills/multi-company-switch/scripts/company.py --add-project "My Project" "/path/to/project"
```

This registers the project in the current company's context.

### Programmatic Access

```python
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent / 'skills' / 'multi-company-switch' / 'scripts'))

from company import set_active_company, get_active_company
from credential_manager import CredentialManager

# Switch company
set_active_company('spearhead')

# Get active company
current = get_active_company()

# Manage credentials
mgr = CredentialManager('spearhead')
mgr.store('api_key', 'secret-value')
key = mgr.get('api_key')
```

## 🧪 Testing

Test the installation:

```bash
# Test initialization
python3 skills/multi-company-switch/scripts/company.py --init

# Test listing
python3 skills/multi-company-switch/scripts/company.py --list

# Test switching
python3 skills/multi-company-switch/scripts/company.py --set Spearhead
python3 skills/multi-company-switch/scripts/company.py --show

# Test credentials
python3 skills/multi-company-switch/scripts/credential_manager.py store spearhead test_key "test_value"
python3 skills/multi-company-switch/scripts/credential_manager.py list spearhead

# Test shell helper
./skills/multi-company-switch/scripts/company.sh list
./skills/multi-company-switch/scripts/company.sh show
```

## 🔧 Troubleshooting

### Issue: "Command not found: company"

**Solution:** Add the script directory to your PATH or use the full path:

```bash
export PATH="$PATH:/Users/faisalshomemacmini/.openclaw/workspace/skills/multi-company-switch/scripts"
```

### Issue: "Cryptography library not installed"

**Solution:** Install the cryptography package:

```bash
pip install cryptography
```

### Issue: "Permission denied"

**Solution:** Ensure scripts are executable:

```bash
chmod +x skills/multi-company-switch/scripts/*.py
chmod +x skills/multi-company-switch/scripts/*.sh
```

### Issue: "Company not found"

**Solution:** Check the company name spelling:

```bash
company list  # See valid company names
# Use lowercase with hyphens: utility-valet, dallas-partners
```

## 📚 Related Files

- **SKILL.md**: Official skill documentation
- **config.json**: Configuration settings
- **companies/**: Runtime data directory
- **scripts/company.py**: Main logic
- **scripts/credential_manager.py**: Secure credential storage
- **scripts/env_loader.py**: Environment variable management

## 🤝 Contributing

To extend this skill:

1. Add new company by editing `COMPANIES` dict in `company.py`
2. Add new credential types in `credential_manager.py`
3. Update `SKILL.md` with new features
4. Test thoroughly before deploying

## 📝 License

Internal use only - part of OpenClaw workspace tools.
