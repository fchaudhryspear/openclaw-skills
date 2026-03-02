"""
Configuration settings for Observational Memory system
"""

from pathlib import Path
from typing import Optional


class Config:
    """Global configuration for obsmem"""
    
    # Default vault location
    DEFAULT_VAULT_PATH = Path.home() / ".obsmem" / "vault"
    
    # Encryption settings
    ENCRYPTION_ALGORITHM = "AES-256-GCM"
    KDF_ALGORITHM = "scrypt"
    KDF_N_PARAMETER = 16384
    KDF_R_PARAMETER = 8
    KDF_P_PARAMETER = 1
    
    # File permissions (secure)
    FILE_PERMISSIONS = 0o600
    
    # Observation defaults
    DEFAULT_MIN_CONFIDENCE = 0.7
    DEFAULT_MIN_IMPORTANCE = 0.5
    
    # Search settings
    SEMANTIC_SEARCH_ENABLED = False  # Set True to enable vector search
    SEARCH_MAX_RESULTS = 50
    
    @classmethod
    def get_vault_path(cls, custom_path: Optional[str | Path] = None) -> Path:
        """Get vault path, using custom if provided"""
        if custom_path:
            return Path(custom_path)
        return cls.DEFAULT_VAULT_PATH
    
    @classmethod
    def ensure_vault_dir(cls, vault_path: Optional[str | Path] = None) -> Path:
        """Ensure vault directory exists"""
        path = cls.get_vault_path(vault_path)
        path.mkdir(parents=True, exist_ok=True)
        return path
