#!/usr/bin/env python3
"""
Multi-Company Context Switcher
Manage context switching between 6 companies with secure credential separation.

Usage:
    python3 company.py --list              # List all companies
    python3 company.py --set <company>     # Set active company
    python3 company.py --show              # Show current company context
    python3 company.py --reset             # Reset to default (Credologi)
"""

import json
import os
import sys
import argparse
from pathlib import Path
from datetime import datetime

# Configuration paths
WORKSPACE = Path(os.environ.get('OPENCLAW_WORKSPACE', '/Users/faisalshomemacmini/.openclaw/workspace'))
COMPANIES_DIR = WORKSPACE / 'companies'
CONFIG_FILE = COMPANIES_DIR / 'config.json'
ACTIVE_COMPANY_FILE = COMPANIES_DIR / '.active_company'
CONTEXT_FILE = COMPANIES_DIR / 'current_context.json'

# Company definitions
COMPANIES = {
    'credologi': {
        'name': 'Credologi',
        'email': 'faisal@credologi.com',
        'primary': True,
        'env_prefix': 'CREDOLOGI_',
        'color': '🔵'
    },
    'spearhead': {
        'name': 'Spearhead',
        'email': 'faisals@spearhead.io',
        'primary': False,
        'env_prefix': 'SPEARHEAD_',
        'color': '🟢'
    },
    'utility-valet': {
        'name': 'Utility Valet',
        'email': 'faisal@utilityvalet.io',
        'primary': False,
        'env_prefix': 'UTILITYVALET_',
        'color': '🟡'
    },
    'flobase': {
        'name': 'Flobase',
        'email': 'faisal@flobase.ai',
        'primary': False,
        'env_prefix': 'FLOBASE_',
        'color': '🟣'
    },
    'starship': {
        'name': 'Starship Residential',
        'email': 'faisal@starshipresidential.com',
        'primary': False,
        'env_prefix': 'STARSHIP_',
        'color': '🔴'
    },
    'dallas-partners': {
        'name': 'Dallas Partners',
        'email': 'faisal@dallaspartners.us',
        'primary': False,
        'env_prefix': 'DALLASPARTNERS_',
        'color': '⚫'
    }
}

def ensure_directories():
    """Create necessary directories for company contexts."""
    COMPANIES_DIR.mkdir(exist_ok=True)
    for key in COMPANIES:
        (COMPANIES_DIR / key / 'projects').mkdir(parents=True, exist_ok=True)
        (COMPANIES_DIR / key / 'credentials').mkdir(parents=True, exist_ok=True)

def init_config():
    """Initialize configuration file if it doesn't exist."""
    if not CONFIG_FILE.exists():
        config = {
            'default_company': 'credologi',
            'companies': list(COMPANIES.keys()),
            'last_switched': None,
            'switch_history': []
        }
        CONFIG_FILE.write_text(json.dumps(config, indent=2))
        return config
    
    return json.loads(CONFIG_FILE.read_text())

def get_active_company():
    """Get currently active company."""
    if ACTIVE_COMPANY_FILE.exists():
        return ACTIVE_COMPANY_FILE.read_text().strip()
    return 'credologi'  # Default

def set_active_company(company_key):
    """Set the active company and load its context."""
    company_key = company_key.lower().replace(' ', '-').replace('_', '-')
    
    if company_key not in COMPANIES:
        print(f"❌ Error: Unknown company '{company_key}'")
        print(f"Available companies: {', '.join(COMPANIES.keys())}")
        return False
    
    config = init_config()
    previous_company = get_active_company()
    
    # Update active company
    ACTIVE_COMPANY_FILE.write_text(company_key)
    
    # Load company context
    load_company_context(company_key)
    
    # Update config
    config['last_switched'] = datetime.now().isoformat()
    config['switch_history'].append({
        'from': previous_company,
        'to': company_key,
        'timestamp': datetime.now().isoformat()
    })
    
    # Keep last 50 switches
    config['switch_history'] = config['switch_history'][-50:]
    CONFIG_FILE.write_text(json.dumps(config, indent=2))
    
    # Export environment variables
    export_env_vars(company_key)
    
    company = COMPANIES[company_key]
    print(f"{company['color']} ✅ Switched to {company['name']}")
    print(f"   Email: {company['email']}")
    print(f"   Previous: {COMPANIES.get(previous_company, {}).get('name', 'Unknown')}")
    
    return True

def load_company_context(company_key):
    """Load company-specific context and settings."""
    company_dir = COMPANIES_DIR / company_key
    context_file = company_dir / 'context.json'
    
    context = {
        'company': company_key,
        'last_loaded': datetime.now().isoformat(),
        'projects': [],
        'settings': {}
    }
    
    if context_file.exists():
        loaded_context = json.loads(context_file.read_text())
        context.update(loaded_context)
    
    # Save current context
    CONTEXT_FILE.write_text(json.dumps(context, indent=2))
    
    return context

def export_env_vars(company_key):
    """Export company-specific environment variables to a shell-readable file."""
    company = COMPANIES[company_key]
    env_file = COMPANIES_DIR / '.env_active'
    
    env_content = f"""# Active Company Environment
export COMPANY_NAME="{company['name']}"
export COMPANY_KEY="{company_key}"
export COMPANY_EMAIL="{company['email']}"
export COMPANY_COLOR="{company['color']}"
export COMPANY_PRIMARY={"true" if company['primary'] else "false"}
"""
    
    env_file.write_text(env_content)
    
    # Also update bash_profile/zshrc reference
    print(f"   Context exported to: {env_file}")

def show_current_context():
    """Display current company context."""
    company_key = get_active_company()
    company = COMPANIES.get(company_key)
    
    if not company:
        print("❌ No active company set")
        return
    
    print(f"\n{company['color']} === Current Company Context ===")
    print(f"Company: {company['name']} ({company_key})")
    print(f"Email: {company['email']}")
    print(f"Primary: {'Yes' if company['primary'] else 'No'}")
    print(f"Directory: {COMPANIES_DIR / company_key}")
    
    if CONTEXT_FILE.exists():
        context = json.loads(CONTEXT_FILE.read_text())
        print(f"Last Loaded: {context.get('last_loaded', 'Never')}")
        
        if context.get('projects'):
            print(f"Projects: {len(context['projects'])} registered")
    
    config = init_config()
    if config.get('switch_history'):
        last_switch = config['switch_history'][-1]
        print(f"\nLast Switch: {last_switch['timestamp']}")
        print(f"From: {last_switch['from']} → To: {last_switch['to']}")

def list_companies():
    """List all available companies."""
    print("\n=== Available Companies ===\n")
    
    config = init_config()
    active = get_active_company()
    
    for key, company in COMPANIES.items():
        status = ""
        if key == active:
            status = f" ← ACTIVE {company['color']}"
        elif company['primary']:
            status = " ← DEFAULT"
        
        emoji = company['color']
        primary_marker = "⭐ " if company['primary'] else "   "
        
        print(f"{emoji} {primary_marker}{company['name']:<25} {key:<20}{status}")
    
    print(f"\nTotal: {len(COMPANIES)} companies")
    print(f"Active: {COMPANIES[active]['name']}")

def reset_to_default():
    """Reset to default company (Credologi)."""
    config = init_config()
    default = config.get('default_company', 'credologi')
    
    print(f"🔄 Resetting to default company: {COMPANIES[default]['name']}")
    set_active_company(default)

def create_company_profile(company_key):
    """Create a company-specific profile with initial context."""
    company_key = company_key.lower().replace(' ', '-').replace('_', '-')
    
    if company_key not in COMPANIES:
        print(f"❌ Error: Unknown company '{company_key}'")
        return False
    
    company_dir = COMPANIES_DIR / company_key
    context_file = company_dir / 'context.json'
    
    profile = {
        'company': company_key,
        'created': datetime.now().isoformat(),
        'projects': [],
        'settings': {
            'git_user': COMPANIES[company_key]['email'].split('@')[0],
            'notifications': True,
            'auto_sync': False
        },
        'integrations': {
            'email': {},
            'crm': {},
            'github': {},
            'aws': {}
        }
    }
    
    if not context_file.exists():
        context_file.write_text(json.dumps(profile, indent=2))
        print(f"✅ Created profile for {COMPANIES[company_key]['name']}")
    else:
        print(f"ℹ️  Profile already exists for {COMPANIES[company_key]['name']}")
    
    return True

def add_project(company_key, project_name, project_path):
    """Add a project to a company's context."""
    company_key = company_key.lower().replace(' ', '-').replace('_', '-')
    
    if company_key not in COMPANIES:
        print(f"❌ Error: Unknown company '{company_key}'")
        return False
    
    company_dir = COMPANIES_DIR / company_key
    context_file = company_dir / 'context.json'
    
    if not context_file.exists():
        create_company_profile(company_key)
    
    context = json.loads(context_file.read_text())
    
    project = {
        'name': project_name,
        'path': str(project_path),
        'added': datetime.now().isoformat()
    }
    
    if 'projects' not in context:
        context['projects'] = []
    
    context['projects'].append(project)
    context_file.write_text(json.dumps(context, indent=2))
    
    print(f"✅ Added project '{project_name}' to {COMPANIES[company_key]['name']}")
    return True

def main():
    parser = argparse.ArgumentParser(
        description='Multi-Company Context Switcher',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python3 company.py --list              List all companies
    python3 company.py --set Credologi     Switch to Credologi
    python3 company.py --show              Show current context
    python3 company.py --reset             Reset to default
    python3 company.py --init              Initialize profiles
        """
    )
    
    parser.add_argument('--list', action='store_true', help='List all companies')
    parser.add_argument('--set', type=str, help='Set active company')
    parser.add_argument('--show', action='store_true', help='Show current context')
    parser.add_argument('--reset', action='store_true', help='Reset to default')
    parser.add_argument('--init', action='store_true', help='Initialize company profiles')
    parser.add_argument('--add-project', nargs=2, metavar=('PROJECT_NAME', 'PATH'), 
                       help='Add project to current company')
    
    args = parser.parse_args()
    
    # Ensure directories exist
    ensure_directories()
    init_config()
    
    if args.list:
        list_companies()
    elif args.set:
        set_active_company(args.set)
    elif args.show:
        show_current_context()
    elif args.reset:
        reset_to_default()
    elif args.init:
        print("🔧 Initializing company profiles...")
        for key in COMPANIES:
            create_company_profile(key)
        print("✅ All company profiles initialized")
    elif args.add_project:
        company_key = get_active_company()
        add_project(company_key, args.add_project[0], args.add_project[1])
    else:
        # Default: show help
        parser.print_help()
        print("\n💡 Quick Start:")
        print(f"   python3 skills/multi-company-switch/scripts/company.py --list")
        print(f"   python3 skills/multi-company-switch/scripts/company.py --set Credologi")

if __name__ == '__main__':
    main()
