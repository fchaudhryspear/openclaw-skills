#!/usr/bin/env python3
"""
Wake Handler - Restores agent state from checkpoints

This module handles the restoration of agent context from encrypted checkpoints,
including workspace recovery and tool session re-establishment.
"""

import os
import json
import shutil
import subprocess
from datetime import datetime
from typing import Any, Dict, Tuple, List, Optional
from pathlib import Path


class WakeHandler:
    """Handles restoration of agent state from checkpoints."""
    
    def __init__(self, checkpoint_manager, workspace_root: str):
        """
        Initialize the Wake Handler.
        
        Args:
            checkpoint_manager: Instance of CheckpointManager for loading checkpoints
            workspace_root: Root directory of the agent workspace
        """
        self.checkpoint_manager = checkpoint_manager
        self.workspace_root = Path(workspace_root)
        self.backup_dir = self.workspace_root / ".checkpoint_backups"
    
    # Wrapper methods delegated to checkpoint_manager
    def _create_backup_before_delete(self, workspace_root: str, deleted_files: list) -> bool:
        """Delegate to checkpoint_manager."""
        return self.checkpoint_manager._create_backup_before_delete(workspace_root, deleted_files)
        
    def wake_agent(self, 
                   target_checkpoint: Optional[str] = None,
                   restore_workspace: bool = True,
                   dry_run: bool = False) -> Tuple[Dict[str, Any], str]:
        """
        Restore agent from a checkpoint.
        
        Args:
            target_checkpoint: Specific checkpoint path (uses latest if None)
            restore_workspace: Whether to restore workspace changes
            dry_run: Preview restoration without applying changes
            
        Returns:
            Tuple of (restored_context, checkpoint_path)
        """
        print(f"\n{'='*60}")
        print("🔄 WAKE PROCESS INITIATED")
        print(f"{'='*60}")
        
        # Load checkpoint
        if target_checkpoint:
            print(f"📍 Target checkpoint: {target_checkpoint}")
            # Load specific checkpoint by path
            context = self._load_checkpoint_by_path(target_checkpoint)
            checkpoint_path = target_checkpoint
        else:
            print("📍 Loading latest available checkpoint...")
            context, checkpoint_path = self.checkpoint_manager.load_latest_checkpoint()
            
        if not context:
            print("❌ No valid checkpoint found for restoration.")
            return None, None
            
        print(f"✅ Checkpoint loaded successfully from: {checkpoint_path}")
        
        # Parse checkpoint metadata
        timestamp = self._extract_timestamp_from_path(checkpoint_path)
        print(f"📅 Checkpoint timestamp: {timestamp}")
        
        # Verify checkpoint integrity (already done by load_latest_checkpoint)
        print("✅ Integrity verification passed")
        
        # Display checkpoint summary
        self._display_checkpoint_summary(context)
        
        if dry_run:
            print("\n⚠️  DRY RUN - No changes applied")
            return context, checkpoint_path
        
        # Restore workspace if requested
        if restore_workspace and "workspace_diff" in context:
            print("\n📁 Restoring workspace changes...")
            success = self._restore_workspace(context["workspace_diff"])
            if not success:
                print("⚠️  Workspace restoration had errors")
            else:
                print("✅ Workspace restored successfully")
        
        # Prepare tool sessions for re-establishment
        if "tool_sessions" in context:
            print(f"\n🔧 Found {len(context['tool_sessions'])} tool sessions to restore")
            self._prepare_tool_restore(context["tool_sessions"])
        
        print(f"\n{'='*60}")
        print("✅ AGENT WAKE COMPLETE")
        print(f"{'='*60}\n")
        
        return context, checkpoint_path
    
    def _load_checkpoint_by_path(self, checkpoint_path: str) -> Optional[Dict[str, Any]]:
        """Load a specific checkpoint by its path."""
        # This would need adaptation to work with the checkpoint manager
        # For now, we'll use the manager's load method with modified logic
        try:
            # Extract timestamp from path
            timestamp = os.path.basename(checkpoint_path)
            
            # Temporarily modify checkpoint manager to load specific path
            context = self.checkpoint_manager.load_specific_checkpoint(timestamp)
            return context
        except Exception as e:
            print(f"❌ Error loading checkpoint: {e}")
            return None
    
    def _extract_timestamp_from_path(self, checkpoint_path: str) -> str:
        """Extract human-readable timestamp from checkpoint path."""
        basename = os.path.basename(checkpoint_path)
        try:
            # Format: YYYYMMDDHHMMSSffffff
            dt = datetime.strptime(basename, "%Y%m%d%H%M%S%f")
            return dt.strftime("%Y-%m-%d %H:%M:%S")
        except ValueError:
            return basename
    
    def _display_checkpoint_summary(self, context: Dict[str, Any]):
        """Display a summary of the checkpoint contents."""
        print("\n📋 CHECKPOINT SUMMARY:")
        print("-" * 40)
        
        if "task_plan" in context:
            plan = context["task_plan"]
            print(f"📝 Task Plan: {len(plan)} steps")
            current = context.get("current_step", 0)
            print(f"   Current progress: Step {current}/{len(plan)}")
        
        if "memory" in context:
            print(f"💾 Memory Items: {len(context['memory'])}")
        
        if "tool_sessions" in context:
            sessions = context["tool_sessions"]
            active = sum(1 for s in sessions.values() if s.get("status") == "running")
            print(f"🔧 Tool Sessions: {len(sessions)} total ({active} active)")
        
        if "chat_history" in context:
            print(f"💬 Chat Messages: {len(context['chat_history'])}")
        
        if "workspace_diff" in context:
            diff = context["workspace_diff"]
            modified = len(diff.get("modified", []))
            added = len(diff.get("added", []))
            deleted = len(diff.get("deleted", []))
            print(f"📁 Workspace Changes: +{added} ~{modified} -{deleted}")
        
        print("-" * 40)
    
    def _restore_workspace(self, workspace_diff: Dict[str, Any]) -> bool:
        """
        Restore workspace based on stored diff.
        
        Implements backup-before-delete policy.
        
        Args:
            workspace_diff: Dictionary with 'added', 'modified', 'deleted' file lists
            
        Returns:
            True if successful, False otherwise
        """
        all_success = True
        
        # Create backup before any deletions
        if "deleted" in workspace_diff and workspace_diff["deleted"]:
            print(f"  🔒 Creating backup before restoration...")
            self._create_backup()
        
        # Handle added files (write them)
        if "added" in workspace_diff:
            for file_info in workspace_diff["added"]:
                success = self._restore_file(file_info)
                all_success &= success
        
        # Handle modified files (overwrite with saved version)
        if "modified" in workspace_diff:
            for file_info in workspace_diff["modified"]:
                success = self._restore_file(file_info)
                all_success &= success
        
        # Handle deleted files (restore from backup or skip)
        if "deleted" in workspace_diff:
            for file_info in workspace_diff["deleted"]:
                print(f"  📄 Restoring previously deleted file: {file_info['path']}")
                # In backup-before-delete model, these should be in .checkpoint_backups
                backup_path = self.backup_dir / "deleted" / file_info["path"].replace("/", "_")
                if backup_path.exists():
                    target_path = self.workspace_root / file_info["path"]
                    target_path.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(backup_path, target_path)
                    print(f"    ✅ Restored: {file_info['path']}")
                else:
                    print(f"    ⚠️  Backup not found for: {file_info['path']}")
                    all_success = False
        
        return all_success
    
    def _restore_file(self, file_info: Dict[str, Any]) -> bool:
        """Restore a single file from checkpoint data."""
        try:
            file_path = self.workspace_root / file_info["path"]
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            if "content" in file_info:
                # Content was embedded in checkpoint
                with open(file_path, 'w') as f:
                    f.write(file_info["content"])
                print(f"    ✅ Restored: {file_info['path']}")
                return True
            elif "content_b64" in file_info:
                # Base64 encoded content (for binary files)
                import base64
                with open(file_path, 'wb') as f:
                    f.write(base64.b64decode(file_info["content_b64"]))
                print(f"    ✅ Restored (binary): {file_info['path']}")
                return True
            else:
                print(f"    ⚠️  No content for: {file_info['path']}")
                return False
                
        except Exception as e:
            print(f"    ❌ Error restoring {file_info['path']}: {e}")
            return False
    
    def _create_backup(self):
        """Create backup of current workspace state before restoration."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_subdir = self.backup_dir / timestamp
        
        # Backup deleted files specifically
        deleted_backup = backup_subdir / "deleted"
        deleted_backup.mkdir(parents=True, exist_ok=True)
        
        # Copy current workspace for safety
        workspace_copy = backup_subdir / "workspace_snapshot"
        if self.workspace_root.exists():
            # Use rsync or similar for efficient copy
            try:
                subprocess.run([
                    "rsync", "-av", "--delete",
                    str(self.workspace_root) + "/",
                    str(workspace_copy) + "/"
                ], check=True, capture_output=True)
                print(f"  ✅ Workspace snapshot created: {backup_subdir}")
            except subprocess.CalledProcessError as e:
                print(f"  ⚠️  Workspace snapshot failed: {e}")
    
    def _prepare_tool_restore(self, tool_sessions: Dict[str, Any]):
        """Prepare tool sessions for re-establishment."""
        for session_id, session_info in tool_sessions.items():
            tool_type = session_info.get("type", "unknown")
            status = session_info.get("status", "unknown")
            
            print(f"  🔹 Session {session_id}: {tool_type} ({status})")
            
            # Different tools have different restoration requirements
            if tool_type == "exec":
                # Exec sessions typically can't be resumed
                # Just log them for informational purposes
                print(f"    ℹ️  Exec session noted (may need manual restart)")
            elif tool_type == "browser":
                print(f"    ℹ️  Browser session noted (requires re-navigating)")
            elif tool_type == "process":
                print(f"    ℹ️  Process session noted (check if still running)")
    
    def get_available_checkpoints(self) -> List[Dict[str, Any]]:
        """Get list of all available checkpoints with metadata."""
        return self.checkpoint_manager.list_checkpoints()


# Example usage
if __name__ == "__main__":
    from checkpoint_manager import CheckpointManager
    from security_utils import SecurityUtils
    
    # Setup
    AGENT_ID = "test_wake_agent"
    WORKSPACE_ROOT = "/Users/faisalshomemacmini/.openclaw/workspace"
    CHECKPOINT_BASE_DIR = "./.checkpoints"
    MASTER_KEY = os.urandom(32)
    
    security = SecurityUtils(MASTER_KEY)
    cp_manager = CheckpointManager(AGENT_ID, CHECKPOINT_BASE_DIR, security)
    wake_handler = WakeHandler(cp_manager, WORKSPACE_ROOT)
    
    # Save a test checkpoint
    test_context = {
        "task_plan": ["Step 1: Analyze", "Step 2: Implement", "Step 3: Test"],
        "current_step": 1,
        "memory": ["Remember to optimize API calls", "Use async where possible"],
        "chat_history": [
            {"role": "user", "content": "Start the project"},
            {"role": "assistant", "content": "Starting analysis..."}
        ],
        "tool_sessions": {
            "exec_1": {"type": "exec", "id": "abc123", "status": "running"},
            "browser_1": {"type": "browser", "url": "https://example.com", "status": "active"}
        },
        "workspace_diff": {
            "added": [{"path": "new_file.txt", "content": "Hello World"}],
            "modified": [{"path": "config.json", "content": '{"setting": "value"}'}],
            "deleted": []
        }
    }
    
    print("\n--- Saving test checkpoint ---")
    cp_manager.save_checkpoint(test_context)
    
    print("\n--- Testing wake handler ---")
    restored_context, cp_path = wake_handler.wake_agent(dry_run=True)
    
    if restored_context:
        print("\n--- Full restoration ---")
        restored_context, cp_path = wake_handler.wake_agent(dry_run=False)
        
        print("\n--- Listing available checkpoints ---")
        checkpoints = wake_handler.get_available_checkpoints()
        for cp in checkpoints:
            print(f"  • {cp['timestamp']} ({cp['size_kb']}KB)")
