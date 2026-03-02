#!/usr/bin/env python3
"""
Telegram Integration Handler
Handles /company commands in Telegram channel.
"""

import os
import sys
import json
from pathlib import Path

# Add scripts directory to path
SCRIPT_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPT_DIR))

from company import (
    list_companies, show_current_context, 
    set_active_company, reset_to_default,
    ensure_directories, init_config
)

class CompanyCommandHandler:
    def __init__(self):
        ensure_directories()
        init_config()
    
    def handle_command(self, command, args):
        """Handle company commands from Telegram."""
        cmd = command.lower().strip()
        
        if cmd == 'list':
            return self._cmd_list()
        
        elif cmd == 'set' or cmd == 'switch':
            if not args:
                return "❌ Usage: /company set <company>\n\n" + self._get_company_list_text()
            
            company_name = ' '.join(args)
            success = set_active_company(company_name)
            if success:
                return f"✅ Switched to {company_name}"
            else:
                return f"❌ Failed to switch to {company_name}"
        
        elif cmd == 'show' or cmd == 'current':
            return self._cmd_show()
        
        elif cmd == 'reset':
            reset_to_default()
            return "🔄 Reset to default company (Credologi)"
        
        elif cmd in ['help', '-h', '--help']:
            return self._cmd_help()
        
        else:
            # Try to set if it's a valid company name
            companies = {c.lower(): c for c in ['credologi', 'spearhead', 'utility-valet', 'flobase', 'starship', 'dallas-partners']}
            if cmd.lower() in companies:
                success = set_active_company(cmd)
                if success:
                    return f"✅ Switched to {companies[cmd.lower()]}"
            
            return f"❌ Unknown command: {cmd}\n\n{self._cmd_help()}"
    
    def _cmd_list(self):
        """List all companies."""
        text = "🏢 **Available Companies**\n\n"
        
        active = None
        try:
            active_file = Path('/Users/faisalshomemacmini/.openclaw/workspace/companies/.active_company')
            if active_file.exists():
                active = active_file.read_text().strip()
        except:
            pass
        
        companies_config = [
            ('🔵', 'Credologi', 'credologi', True),
            ('🟢', 'Spearhead', 'spearhead', False),
            ('🟡', 'Utility Valet', 'utility-valet', False),
            ('🟣', 'Flobase', 'flobase', False),
            ('🔴', 'Starship Residential', 'starship', False),
            ('⚫', 'Dallas Partners', 'dallas-partners', False)
        ]
        
        for emoji, name, key, is_primary in companies_config:
            marker = "⭐ " if is_primary else "   "
            status = ""
            if key == active:
                status = " ← ACTIVE ✅"
            
            text += f"{emoji} {marker}{name}{status}\n"
        
        return text
    
    def _cmd_show(self):
        """Show current context."""
        text = "📊 **Current Company Context**\n\n"
        
        active_file = Path('/Users/faisalshomemacmini/.openclaw/workspace/companies/.active_company')
        active = active_file.read_text().strip() if active_file.exists() else 'credologi'
        
        companies = {
            'credologi': {'emoji': '🔵', 'email': 'faisal@credologi.com'},
            'spearhead': {'emoji': '🟢', 'email': 'faisal@spearhead.io'},
            'utility-valet': {'emoji': '🟡', 'email': 'faisal@utilityvalet.io'},
            'flobase': {'emoji': '🟣', 'email': 'faisal@flobase.ai'},
            'starship': {'emoji': '🔴', 'email': 'faisal@starshipresidential.com'},
            'dallas-partners': {'emoji': '⚫', 'email': 'faisal@dallaspartners.us'}
        }
        
        company = companies.get(active, companies['credologi'])
        
        text += f"{company['emoji']} **Company:** {active.title()}\n"
        text += f"✉️ **Email:** {company['email']}\n\n"
        
        text += "_Use /company list to see all available companies_"
        
        return text
    
    def _get_company_list_text(self):
        """Get formatted company list."""
        text = "🏢 **Available Companies:**\n\n"
        
        companies = [
            'Credologi', 'Spearhead', 'Utility Valet',
            'Flobase', 'Starship', 'Dallas Partners'
        ]
        
        for company in companies:
            text += f"• `{company}`\n"
        
        return text
    
    def _cmd_help(self):
        """Show help."""
        text = "🏢 **Multi-Company Context Switcher**\n\n"
        text += "Manage context between your 6 companies.\n\n"
        text += "**Commands:**\n"
        text += "• `/company list` - Show all companies\n"
        text += "• `/company set <name>` - Switch to company\n"
        text += "• `/company show` - Show current context\n"
        text += "• `/company reset` - Reset to default\n"
        text += "• `/company help` - Show this help\n\n"
        text += "**Examples:**\n"
        text += "• `/company set Credologi`\n"
        text += "• `/company set Spearhead`\n"
        text += "• `/company list`\n"
        
        return text


def main():
    """Main entry point for Telegram integration."""
    handler = CompanyCommandHandler()
    
    # Read command from stdin or args
    if len(sys.argv) > 1:
        command = sys.argv[1]
        args = sys.argv[2:] if len(sys.argv) > 2 else []
    else:
        # Try reading from stdin
        try:
            input_data = json.loads(sys.stdin.read())
            command = input_data.get('command', 'help')
            args = input_data.get('args', [])
        except:
            command = 'help'
            args = []
    
    result = handler.handle_command(command, args)
    print(result)


if __name__ == '__main__':
    main()
