#!/usr/bin/env python3
"""
Environment Loader for Multi-Company Switch
Exports company-specific environment variables for shell use.

Usage:
    eval $(python3 env_loader.py export)     # Export to current shell
    source <(python3 env_loader.py export)   # Source in bash/zsh
"""

import os
import sys
import json
from pathlib import Path

WORKSPACE = Path(os.environ.get('OPENCLAW_WORKSPACE', '/Users/faisalshomemacmini/.openclaw/workspace'))
COMPANIES_DIR = WORKSPACE / 'companies'
ACTIVE_FILE = COMPANIES_DIR / '.active_company'

def get_active_company():
    """Get the currently active company."""
    if not ACTIVE_FILE.exists():
        return 'credologi'
    return ACTIVE_FILE.read_text().strip()

def load_credentials(company_key):
    """Load encrypted credentials for a company."""
    creds_file = COMPANIES_DIR / company_key / 'credentials.json'
    
    if not creds_file.exists():
        return {}
    
    try:
        creds = json.loads(creds_file.read_text())
        # Return keys without values (for security - actual decryption happens elsewhere)
        return {k: v.get('type', 'unknown') for k, v in creds.items() if k != '_metadata'}
    except:
        return {}

def generate_export(company_key=None):
    """Generate shell export commands for the active company."""
    if not company_key:
        company_key = get_active_company()
    
    companies_config = {
        'credologi': {'name': 'Credologi', 'email': 'faisal@credologi.com'},
        'spearhead': {'name': 'Spearhead', 'email': 'faisal@spearhead.io'},
        'utility-valet': {'name': 'Utility Valet', 'email': 'faisal@utilityvalet.io'},
        'flobase': {'name': 'Flobase', 'email': 'faisal@flobase.ai'},
        'starship': {'name': 'Starship Residential', 'email': 'faisal@starshipresidential.com'},
        'dallas-partners': {'name': 'Dallas Partners', 'email': 'faisal@dallaspartners.us'}
    }
    
    company = companies_config.get(company_key, {})
    
    exports = f"""# Company Context - {company.get('name', company_key)}
export COMPANY_KEY="{company_key}"
export COMPANY_NAME="{company.get('name', company_key)}"
export COMPANY_EMAIL="{company.get('email', '')}"
export COMPANY_WORKSPACE="{COMPANIES_DIR / company_key}"
export COMPANIES_DIR="{COMPANIES_DIR}"

# Clear previous company vars
unset CREDOLOGI_API_KEY 2>/dev/null
unset SPEARHEAD_API_KEY 2>/dev/null
unset UTILITYVALET_API_KEY 2>/dev/null
unset FLOBASE_API_KEY 2>/dev/null
unset STARSHIP_API_KEY 2>/dev/null
unset DALLASPARTNERS_API_KEY 2>/dev/null

# Note: Load specific API keys with:
# python3 skills/multi-company-switch/scripts/credential_manager.py get {company_key} api_key
"""
    
    return exports

def list_available():
    """List available companies."""
    companies = [
        ('🔵 Credologi', 'credologi'),
        ('🟢 Spearhead', 'spearhead'),
        ('🟡 Utility Valet', 'utility-valet'),
        ('🟣 Flobase', 'flobase'),
        ('🔴 Starship Residential', 'starship'),
        ('⚫ Dallas Partners', 'dallas-partners')
    ]
    
    active = get_active_company()
    
    print("\nAvailable Companies:")
    for name, key in companies:
        marker = "← ACTIVE " if key == active else "           "
        print(f"{marker}{name} ({key})")
    
    print(f"\nCurrent: {get_active_company()}")

def main():
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == 'export':
            company = sys.argv[2] if len(sys.argv) > 2 else None
            print(generate_export(company))
        
        elif command == 'list':
            list_available()
        
        elif command == 'set':
            if len(sys.argv) < 3:
                print("❌ Usage: env_loader.py set <company>")
                sys.exit(1)
            
            company = sys.argv[2]
            # Import and call the company switcher
            import subprocess
            result = subprocess.run([
                sys.executable,
                str(WORKSPACE / 'skills' / 'multi-company-switch' / 'scripts' / 'company.py'),
                '--set', company
            ], capture_output=True, text=True)
            
            print(result.stdout)
            if result.stderr:
                print(result.stderr, file=sys.stderr)
            
            # Also export the new environment
            print(generate_export(company))
        
        else:
            print(f"❌ Unknown command: {command}")
            print("Usage: env_loader.py [export|list|set <company>]")
            sys.exit(1)
    else:
        # Default: just export current
        print(generate_export())

if __name__ == '__main__':
    main()
