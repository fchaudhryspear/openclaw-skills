"""
Observational Memory System - Security-focused memory for AI agents
"""

from .core.memory import MemoryVault, Observation, ObservationType
from .core.observer import ObservationObserver
from .core.encryption import SecureStorage, SecurityError
from .config.settings import Config

__version__ = "0.1.0"
__all__ = [
    "MemoryVault",
    "Observation", 
    "ObservationType",
    "ObservationObserver",
    "SecureStorage",
    "SecurityError",
    "Config"
]
