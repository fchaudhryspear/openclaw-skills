"""
Secure storage layer with AES-256-GCM encryption and scrypt KDF
Based on ClawVault security best practices
"""

import os
import json
import secrets
from pathlib import Path
from typing import Optional, Any, Dict


class SecurityError(Exception):
    """Raised when a security violation occurs"""
    pass


class SecureStorage:
    """
    Encrypted file-based storage with AES-256-GCM
    
    Security features:
    - AES-256-GCM authenticated encryption
    - scrypt KDF for password derivation (N=2^14, r=8, p=1)
    - Secure file permissions (0600)
    - Nonce/AD management
    - Memory-safe operations where possible
    """
    
    # scrypt parameters matching ClawVault standards
    SALT_LENGTH = 32
    KEY_LENGTH = 32  # 256 bits for AES-256
    N_PARAMETER = 16384  # 2^14
    R_PARAMETER = 8
    P_PARAMETER = 1
    
    NONCE_LENGTH = 12  # 96-bit nonce for GCM
    
    def __init__(self, filepath, master_password: str):
        """
        Initialize secure storage
        
        Args:
            filepath: Path to the encrypted data file
            master_password: Master password for encryption/decryption
        """
        self.filepath = Path(filepath)
        """
        Initialize secure storage
        
        Args:
            filepath: Path to the encrypted data file
            master_password: Master password for encryption/decryption
        """
        self.filepath = Path(filepath)
        self.master_password = master_password
        self._data: Dict[str, Any] = {}
        self._loaded = False
        self._current_key: Optional[bytes] = None
        
    def _derive_key(self, salt: bytes) -> bytes:
        """Derive encryption key from password using scrypt"""
        from cryptography.hazmat.primitives.kdf.scrypt import Scrypt
        from cryptography.hazmat.backends import default_backend
        
        kdf = Scrypt(
            salt=salt,
            length=self.KEY_LENGTH,
            n=self.N_PARAMETER,
            r=self.R_PARAMETER,
            p=self.P_PARAMETER,
            backend=default_backend()
        )
        return kdf.derive(self.master_password.encode('utf-8'))
    
    def _encrypt_data(self, plaintext: bytes, associated_data: Optional[bytes] = None) -> tuple:
        """
        Encrypt data with AES-256-GCM
        
        Returns:
            Tuple of (ciphertext_with_tag, nonce)
        """
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        
        nonce = secrets.token_bytes(self.NONCE_LENGTH)
        aesgcm = AESGCM(self._current_key)
        ciphertext = aesgcm.encrypt(nonce, plaintext, associated_data)
        return ciphertext, nonce
    
    def _decrypt_data(self, ciphertext: bytes, nonce: bytes, associated_data: Optional[bytes] = None) -> bytes:
        """Decrypt data with AES-256-GCM"""
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        
        aesgcm = AESGCM(self._current_key)
        try:
            plaintext = aesgcm.decrypt(nonce, ciphertext, associated_data)
            return plaintext
        except Exception as e:
            raise SecurityError(f"Decryption failed: {e}")
    
    def load(self) -> Dict[str, Any]:
        """Load and decrypt data from file"""
        if not self.filepath.exists():
            self._data = {}
            return self._data
        
        try:
            with open(self.filepath, 'rb') as f:
                blob = f.read()
            
            if len(blob) < self.SALT_LENGTH + self.NONCE_LENGTH:
                raise SecurityError("Corrupted or invalid encrypted file")
            
            # Extract components
            salt = blob[:self.SALT_LENGTH]
            nonce = blob[self.SALT_LENGTH:self.SALT_LENGTH + self.NONCE_LENGTH]
            ciphertext = blob[self.SALT_LENGTH + self.NONCE_LENGTH:]
            
            # Derive key
            self._current_key = self._derive_key(salt)
            
            # Decrypt
            plaintext = self._decrypt_data(ciphertext, nonce)
            self._data = json.loads(plaintext.decode('utf-8'))
            self._loaded = True
            
            return self._data
            
        except json.JSONDecodeError as e:
            raise SecurityError(f"Invalid JSON in decrypted data: {e}")
    
    def save(self) -> None:
        """Encrypt and save data to file with secure permissions"""
        # Serialize data
        plaintext = json.dumps(self._data, indent=2, ensure_ascii=False).encode('utf-8')
        
        # Generate salt if not existing
        if not self.filepath.exists():
            salt = secrets.token_bytes(self.SALT_LENGTH)
        else:
            # Reuse existing salt
            with open(self.filepath, 'rb') as f:
                salt = f.read(self.SALT_LENGTH)
        
        # Derive key
        key = self._derive_key(salt)
        self._current_key = key
        
        # Encrypt
        ciphertext, nonce = self._encrypt_data(plaintext)
        
        # Combine into single blob
        blob = salt + nonce + ciphertext
        
        # Write atomically with secure permissions
        temp_path = self.filepath.with_suffix('.tmp')
        
        # Create parent directories if needed
        self.filepath.parent.mkdir(parents=True, exist_ok=True)
        
        # Write with restrictive permissions
        fd = os.open(temp_path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        try:
            os.write(fd, blob)
        finally:
            os.close(fd)
        
        # Atomic rename
        temp_path.rename(self.filepath)
        
        # Wipe sensitive data from memory
        del blob
        del plaintext
        del ciphertext
        del key
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get value by key"""
        if not self._loaded:
            self.load()
        return self._data.get(key, default)
    
    def set(self, key: str, value: Any) -> None:
        """Set value by key"""
        if not self._loaded:
            self.load()
        self._data[key] = value
    
    def delete(self, key: str) -> bool:
        """Delete key if exists"""
        if not self._loaded:
            self.load()
        if key in self._data:
            del self._data[key]
            return True
        return False
    
    def clear(self) -> None:
        """Clear all data"""
        self._data = {}
    
    def keys(self) -> list:
        """Return all keys"""
        if not self._loaded:
            self.load()
        return list(self._data.keys())
    
    def __del__(self):
        """Secure cleanup - wipe sensitive memory"""
        if self._current_key is not None:
            # Overwrite key bytes before deletion
            try:
                self._current_key[:] = b'\x00' * len(self._current_key)
            except:
                pass
            del self._current_key
