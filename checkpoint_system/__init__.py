"""
Auto-Checkpoint & Wake System for OpenClaw

A comprehensive checkpointing system with AES-256 encryption, 
HMAC integrity verification, and workspace diff tracking.
"""

from .checkpoint_manager import CheckpointManager
from .wake_handler import WakeHandler
from .integration import AutoCheckpointIntegration, CheckpointContextInjector

# Import SecurityUtils directly from parent directory
import sys
sys.path.insert(0, "/Users/faisalshomemacmini/.openclaw/workspace")
from security_utils import SecurityUtils

__version__ = "1.0.0"
__all__ = [
    "CheckpointManager",
    "WakeHandler",
    "AutoCheckpointIntegration",
    "CheckpointContextInjector",
    "SecurityUtils"
]


def get_default_config():
    """Get default configuration for checkpoint system."""
    return {
        "auto_checkpoint_interval_minutes": 10,
        "checkpoint_before_long_exec": True,
        "long_exec_threshold_seconds": 30,
        "checkpoint_before_subagent_spawn": True,
        "context_limit_warning_percent": 80,
        "max_context_tokens": 125000,
        "backup_workspace": True,
        "enable_time_based": True,
        "event_based_triggers": True
    }


def setup_checkpoints(agent_id=None):
    """
    Convenience function to set up checkpoint system.
    
    Returns:
        Tuple of (checkpoint_manager, wake_handler, integration)
    """
    import os
    
    from pathlib import Path
    
    # Get configuration
    agent_id = agent_id or os.environ.get("AGENT_ID", "default_agent")
    workspace_root = os.environ.get(
        "WORKSPACE_ROOT",
        "/Users/faisalshomemacmini/.openclaw/workspace"
    )
    checkpoint_dir = os.environ.get(
        "CHECKPOINT_DIR",
        str(Path(workspace_root) / ".checkpoints")
    )
    
    # Load master key
    master_key_b64 = os.environ.get("CHECKPOINT_MASTER_KEY")
    if master_key_b64:
        import base64
        master_key = base64.b64decode(master_key_b64)
    else:
        raise ValueError(
            "CHECKPOINT_MASTER_KEY environment variable not set. "
            "Generate one with: python -c 'import os,base64; print(base64.b64encode(os.urandom(32)).decode())'"
        )
    
    # Initialize components
    security = SecurityUtils(master_key)
    manager = CheckpointManager(agent_id, checkpoint_dir, security)
    wake_handler = WakeHandler(manager, workspace_root)
    integration = AutoCheckpointIntegration(manager, wake_handler)
    
    return manager, wake_handler, integration
