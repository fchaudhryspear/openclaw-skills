"""
Utility functions for Observational Memory system
"""

import hashlib
import secrets
from pathlib import Path
from typing import List, Optional


def ensure_secure_permissions(filepath: Path) -> None:
    """Ensure file has secure permissions (0600)"""
    filepath.chmod(0o600)


def generate_secure_id() -> str:
    """Generate a cryptographically secure ID"""
    return secrets.token_hex(16)


def secure_hash(data: str) -> str:
    """Create SHA-256 hash of data"""
    return hashlib.sha256(data.encode('utf-8')).hexdigest()


def mask_sensitive_data(text: str, pattern: str = "secret", replacement: str = "***") -> str:
    """Replace sensitive patterns with masked version"""
    import re
    return re.sub(pattern, replacement, text, flags=re.IGNORECASE)


def truncate_text(text: str, max_length: int = 1000, suffix: str = "...") -> str:
    """Truncate text to max length while preserving word boundaries"""
    if len(text) <= max_length:
        return text
    
    truncated = text[:max_length]
    # Find last complete word
    last_space = truncated.rfind(' ')
    if last_space > max_length * 0.8:  # Only truncate at word boundary if reasonable
        truncated = truncated[:last_space]
    
    return truncated + suffix


def clean_memory(*objects):
    """
    Attempt to securely clear sensitive objects from memory
    
    Warning: Python's memory management makes true secure deletion difficult.
    This is best-effort only.
    """
    for obj in objects:
        try:
            if hasattr(obj, '__setitem__'):
                # Dict-like object
                for key in list(obj.keys()):
                    obj[key] = None
            elif isinstance(obj, (list, tuple)):
                # Sequence
                for i in range(len(obj)):
                    obj[i] = None
            elif isinstance(obj, bytes):
                # Bytes - overwrite
                obj[:] = b'\x00' * len(obj)
            elif isinstance(obj, str):
                # Strings are immutable, just delete reference
                pass
        except Exception:
            pass  # Best effort only
        
        del obj
