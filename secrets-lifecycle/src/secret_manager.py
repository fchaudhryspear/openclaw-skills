"""
Secrets Lifecycle Manager - Core Secret Storage with Encryption
Tracks API keys, credentials, rotation schedules, and expirations.
"""

import os
import json
import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64
import stat


class SecretManager:
    """Encrypted secret storage with lifecycle tracking."""
    
    def __init__(self, data_dir: str, master_password: str):
        self.data_dir = data_dir
        self.secrets_file = os.path.join(data_dir, 'secrets.enc.json')
        self.audit_file = os.path.join(data_dir, 'audit.log')
        
        # Ensure data directory exists with secure permissions
        os.makedirs(data_dir, mode=0o700, exist_ok=True)
        
        # Derive encryption key from master password
        self._init_encryption(master_password)
        
        # Load or initialize secrets store
        self.secrets = self._load_secrets()
        
    def _init_encryption(self, master_password: str):
        """Derve encryption key using PBKDF2."""
        salt = b'secrets-lifecycle-salt-v1'  # In production, use random salt stored separately
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=480000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(master_password.encode()))
        self.cipher = Fernet(key)
        
    def _load_secrets(self) -> Dict[str, Any]:
        """Load encrypted secrets from disk."""
        if os.path.exists(self.secrets_file):
            with open(self.secrets_file, 'rb') as f:
                encrypted = f.read()
            decrypted = self.cipher.decrypt(encrypted)
            return json.loads(decrypted.decode())
        
        # Initialize new secrets store
        return {
            'secrets': {},
            'metadata': {
                'created': datetime.now().isoformat(),
                'version': '1.0',
                'last_modified': None
            }
        }
    
    def _save_secrets(self):
        """Save encrypted secrets to disk with secure permissions."""
        self.secrets['metadata']['last_modified'] = datetime.now().isoformat()
        
        encrypted = self.cipher.encrypt(
            json.dumps(self.secrets, indent=2).encode()
        )
        
        # Write with atomic operation for safety
        temp_file = self.secrets_file + '.tmp'
        with open(temp_file, 'wb') as f:
            f.write(encrypted)
        
        # Set restrictive permissions before rename
        os.chmod(temp_file, 0o600)
        os.rename(temp_file, self.secrets_file)
        
    def _log_audit(self, action: str, secret_id: str, details: Dict = None):
        """Log audit trail entry."""
        entry = {
            'timestamp': datetime.now().isoformat(),
            'action': action,
            'secret_id': secret_id,
            'details': details or {}
        }
        
        with open(self.audit_file, 'a') as f:
            f.write(json.dumps(entry) + '\n')
            
    def add_secret(
        self,
        name: str,
        value: str,
        service: str,
        expiration_date: Optional[datetime] = None,
        rotation_days: Optional[int] = None,
        notes: str = '',
        tags: List[str] = None
    ) -> str:
        """Add a new secret to the vault."""
        secret_id = hashlib.sha256(f"{name}-{service}-{datetime.now().isoformat()}".encode()).hexdigest()[:16]
        
        # Encrypt the actual secret value
        encrypted_value = self.cipher.encrypt(value.encode()).decode()
        
        secret_data = {
            'id': secret_id,
            'name': name,
            'service': service,
            'value': encrypted_value,  # Encrypted
            'expiration_date': expiration_date.isoformat() if expiration_date else None,
            'rotation_days': rotation_days,
            'next_rotation': (datetime.now() + timedelta(days=rotation_days)).isoformat() if rotation_days else None,
            'notes': notes,
            'tags': tags or [],
            'created': datetime.now().isoformat(),
            'last_rotated': None,
            'status': 'active'
        }
        
        self.secrets['secrets'][secret_id] = secret_data
        self._save_secrets()
        self._log_audit('ADD_SECRET', secret_id, {'name': name, 'service': service})
        
        return secret_id
    
    def get_secret(self, secret_id: str) -> Optional[Dict]:
        """Retrieve a secret by ID (returns decrypted value)."""
        if secret_id not in self.secrets['secrets']:
            return None
            
        secret = self.secrets['secrets'][secret_id].copy()
        
        # Decrypt the value
        try:
            secret['value'] = self.cipher.decrypt(secret['value'].encode()).decode()
        except Exception as e:
            self._log_audit('DECRYPT_ERROR', secret_id, {'error': str(e)})
            return None
            
        self._log_audit('GET_SECRET', secret_id)
        return secret
    
    def update_secret(self, secret_id: str, updates: Dict) -> bool:
        """Update secret metadata (not the value directly - use rotate for that)."""
        if secret_id not in self.secrets['secrets']:
            return False
            
        allowed_fields = ['name', 'service', 'expiration_date', 'rotation_days', 
                         'next_rotation', 'notes', 'tags', 'status']
        
        for field, value in updates.items():
            if field in allowed_fields:
                if field == 'expiration_date' and value:
                    value = value.isoformat() if isinstance(value, datetime) else value
                if field == 'next_rotation' and value:
                    value = value.isoformat() if isinstance(value, datetime) else value
                self.secrets['secrets'][secret_id][field] = value
        
        self._save_secrets()
        self._log_audit('UPDATE_SECRET', secret_id, {'updates': list(updates.keys())})
        return True
    
    def rotate_secret(self, secret_id: str, new_value: str) -> bool:
        """Rotate a secret with a new value."""
        if secret_id not in self.secrets['secrets']:
            return False
            
        secret = self.secrets['secrets'][secret_id]
        
        # Store old value metadata for audit
        old_metadata = {
            'expiration_date': secret.get('expiration_date'),
            'next_rotation': secret.get('next_rotation')
        }
        
        # Encrypt and set new value
        secret['value'] = self.cipher.encrypt(new_value.encode()).decode()
        secret['last_rotated'] = datetime.now().isoformat()
        
        # Update next rotation based on rotation_days
        if secret.get('rotation_days'):
            secret['next_rotation'] = (
                datetime.now() + timedelta(days=secret['rotation_days'])
            ).isoformat()
            
        self._save_secrets()
        self._log_audit('ROTATE_SECRET', secret_id, {'old_metadata': old_metadata})
        return True
    
    def delete_secret(self, secret_id: str) -> bool:
        """Delete a secret (soft delete - marks as deleted)."""
        if secret_id not in self.secrets['secrets']:
            return False
            
        self.secrets['secrets'][secret_id]['status'] = 'deleted'
        self.secrets['secrets'][secret_id]['deleted_at'] = datetime.now().isoformat()
        self._save_secrets()
        self._log_audit('DELETE_SECRET', secret_id)
        return True
    
    def list_secrets(self, include_deleted: bool = False) -> List[Dict]:
        """List all secrets (metadata only, no values)."""
        secrets_list = []
        for sid, secret in self.secrets['secrets'].items():
            if not include_deleted and secret.get('status') == 'deleted':
                continue
            # Return metadata only (never expose values in list)
            secrets_list.append({
                'id': sid,
                'name': secret['name'],
                'service': secret['service'],
                'expiration_date': secret.get('expiration_date'),
                'rotation_days': secret.get('rotation_days'),
                'next_rotation': secret.get('next_rotation'),
                'status': secret.get('status', 'active'),
                'created': secret.get('created'),
                'last_rotated': secret.get('last_rotated'),
                'tags': secret.get('tags', [])
            })
        return secrets_list
    
    def get_expiring_secrets(self, days: int = 30) -> List[Dict]:
        """Get secrets expiring within specified days."""
        now = datetime.now()
        cutoff = now + timedelta(days=days)
        expiring = []
        
        for sid, secret in self.secrets['secrets'].items():
            if secret.get('status') == 'deleted':
                continue
            if not secret.get('expiration_date'):
                continue
                
            exp_date = datetime.fromisoformat(secret['expiration_date'])
            if exp_date <= cutoff:
                expiring.append({
                    **secret,
                    'days_until_expiry': (exp_date - now).days
                })
                
        return sorted(expiring, key=lambda x: x['days_until_expiry'])
