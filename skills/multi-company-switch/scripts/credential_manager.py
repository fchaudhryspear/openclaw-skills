#!/usr/bin/env python3
"""
Secure Credential Manager for Multi-Company Switch
Handles encrypted storage and retrieval of company-specific credentials.

Usage:
    python3 credential_manager.py store <company> <key> <value>
    python3 credential_manager.py get <company> <key>
    python3 credential_manager.py list <company>
    python3 credential_manager.py delete <company> <key>
"""

import os
import sys
import json
import base64
import argparse
from pathlib import Path
from datetime import datetime

# Try to import cryptography, provide fallback if not available
try:
    from cryptography.fernet import Fernet
    CRYPTO_AVAILABLE = True
except ImportError:
    CRYPTO_AVAILABLE = False
    print("⚠️  Warning: cryptography library not installed")
    print("   Install with: pip install cryptography")
    print("   Credentials will be stored in plain text (not recommended)")

# Paths
WORKSPACE = Path(os.environ.get('OPENCLAW_WORKSPACE', '/Users/faisalshomemacmini/.openclaw/workspace'))
COMPANIES_DIR = WORKSPACE / 'companies'
KEYS_DIR = COMPANIES_DIR / '.keys'

class CredentialManager:
    def __init__(self, company_key):
        self.company_key = company_key.lower().replace(' ', '-').replace('_', '-')
        self.creds_file = COMPANIES_DIR / self.company_key / 'credentials.json'
        self.key_file = KEYS_DIR / f'{self.company_key}.key'
        
        # Ensure directories exist
        COMPANIES_DIR.mkdir(exist_ok=True)
        (COMPANIES_DIR / self.company_key).mkdir(exist_ok=True)
        KEYS_DIR.mkdir(exist_ok=True)
    
    def _get_or_create_key(self):
        """Get or create encryption key for this company."""
        if not CRYPTO_AVAILABLE:
            return None
        
        if not self.key_file.exists():
            key = Fernet.generate_key()
            self.key_file.write_bytes(key)
            self.key_file.chmod(0o600)  # Owner read/write only
            return key
        
        return self.key_file.read_bytes()
    
    def _encrypt(self, value):
        """Encrypt a value."""
        if not CRYPTO_AVAILABLE:
            return base64.b64encode(value.encode()).decode()
        
        key = self._get_or_create_key()
        f = Fernet(key)
        return f.encrypt(value.encode()).decode()
    
    def _decrypt(self, encrypted_value):
        """Decrypt a value."""
        if not CRYPTO_AVAILABLE:
            return base64.b64decode(encrypted_value.encode()).decode()
        
        key = self.key_file.read_bytes()
        f = Fernet(key)
        return f.decrypt(encrypted_value.encode()).decode()
    
    def _load_credentials(self):
        """Load credentials from file."""
        if not self.creds_file.exists():
            return {}
        
        try:
            return json.loads(self.creds_file.read_text())
        except (json.JSONDecodeError, FileNotFoundError):
            return {}
    
    def _save_credentials(self, creds):
        """Save credentials to file."""
        # Remove sensitive keys from display
        metadata = {k: v for k, v in creds.items() if k != '_metadata'}
        
        # Add/update metadata
        creds['_metadata'] = {
            'last_updated': datetime.now().isoformat(),
            'company': self.company_key,
            'version': '1.0'
        }
        
        self.creds_file.write_text(json.dumps(creds, indent=2))
        self.creds_file.chmod(0o600)  # Owner read/write only
    
    def store(self, key, value):
        """Store a credential."""
        creds = self._load_credentials()
        encrypted = self._encrypt(value)
        creds[key] = {
            'encrypted': encrypted,
            'created': datetime.now().isoformat(),
            'type': self._detect_type(value)
        }
        self._save_credentials(creds)
        print(f"✅ Stored credential '{key}' for {self.company_key}")
        return True
    
    def get(self, key):
        """Retrieve a credential."""
        creds = self._load_credentials()
        
        if key not in creds:
            print(f"❌ Credential '{key}' not found for {self.company_key}")
            return None
        
        entry = creds[key]
        encrypted = entry.get('encrypted', entry)  # Handle old format
        
        try:
            value = self._decrypt(encrypted)
            print(f"🔑 {key}: {value}")
            return value
        except Exception as e:
            print(f"❌ Failed to decrypt credential '{key}': {e}")
            return None
    
    def list_credentials(self):
        """List all credentials for this company."""
        creds = self._load_credentials()
        
        if not creds or len(creds) <= 1:  # Only metadata
            print(f"ℹ️  No credentials stored for {self.company_key}")
            return []
        
        print(f"\n=== Credentials for {self.company_key} ===\n")
        
        for key, entry in creds.items():
            if key == '_metadata':
                continue
            
            created = entry.get('created', 'Unknown')
            cred_type = entry.get('type', 'unknown')
            
            print(f"  • {key:<30} ({cred_type}) - Created: {created[:19]}")
        
        print(f"\nTotal: {len(creds) - 1} credentials")
        return [k for k in creds.keys() if k != '_metadata']
    
    def delete(self, key):
        """Delete a credential."""
        creds = self._load_credentials()
        
        if key not in creds:
            print(f"❌ Credential '{key}' not found for {self.company_key}")
            return False
        
        del creds[key]
        self._save_credentials(creds)
        print(f"✅ Deleted credential '{key}' from {self.company_key}")
        return True
    
    def _detect_type(self, value):
        """Detect the type of credential based on value pattern."""
        if value.startswith('sk-') or value.startswith('api_'):
            return 'api_key'
        elif '@' in value and '.' in value.split('@')[-1]:
            return 'email'
        elif value.startswith('http://') or value.startswith('https://'):
            return 'url'
        elif len(value) == 40 and all(c in '0123456789abcdefABCDEF' for c in value):
            return 'sha1'
        else:
            return 'password'
    
    def load_env_vars(self):
        """Load credentials as environment variables."""
        creds = self._load_credentials()
        env_vars = {}
        
        for key, entry in creds.items():
            if key == '_metadata':
                continue
            
            try:
                value = self._decrypt(entry.get('encrypted', entry))
                # Convert key to valid env var name
                env_name = f"{self.company_key.upper()}_{key.upper()}"
                env_vars[env_name] = value
            except:
                pass
        
        return env_vars


def main():
    parser = argparse.ArgumentParser(description='Secure Credential Manager')
    parser.add_argument('command', choices=['store', 'get', 'list', 'delete'], 
                       help='Command to execute')
    parser.add_argument('company', help='Company key')
    parser.add_argument('key', nargs='?', help='Credential key/name')
    parser.add_argument('value', nargs='?', help='Credential value (for store)')
    parser.add_argument('--stdin', action='store_true', help='Read value from stdin')
    
    args = parser.parse_args()
    
    manager = CredentialManager(args.company)
    
    if args.command == 'store':
        if not args.key:
            print("❌ Error: Key is required for store command")
            sys.exit(1)
        
        if args.stdin:
            value = sys.stdin.read().strip()
        elif args.value:
            value = args.value
        else:
            # Prompt for value
            value = input(f"Enter value for {args.key}: ")
        
        manager.store(args.key, value)
    
    elif args.command == 'get':
        if not args.key:
            print("❌ Error: Key is required for get command")
            sys.exit(1)
        
        manager.get(args.key)
    
    elif args.command == 'list':
        manager.list_credentials()
    
    elif args.command == 'delete':
        if not args.key:
            print("❌ Error: Key is required for delete command")
            sys.exit(1)
        
        confirm = input(f"Delete credential '{args.key}'? (yes/no): ")
        if confirm.lower() == 'yes':
            manager.delete(args.key)
        else:
            print("❌ Cancelled")
            sys.exit(1)


if __name__ == '__main__':
    main()
