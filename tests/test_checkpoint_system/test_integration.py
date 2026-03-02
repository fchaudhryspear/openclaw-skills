#!/usr/bin/env python3
"""
Integration Tests for Checkpoint System

End-to-end tests covering checkpoint creation, workspace diffing, 
wake/restore, and CLI operations.
"""

import os
import sys
import unittest
import tempfile
import shutil
import json
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from security_utils import SecurityUtils
from checkpoint_system.checkpoint_manager import CheckpointManager
from checkpoint_system.wake_handler import WakeHandler


class TestWorkspaceDiff(unittest.TestCase):
    """Test workspace diff capture and restoration."""
    
    def setUp(self):
        """Set up test workspace."""
        self.test_dir = tempfile.mkdtemp()
        self.workspace = Path(self.test_dir) / "workspace"
        self.workspace.mkdir()
        
        # Create initial files
        (self.workspace / "file1.txt").write_text("original content")
        (self.workspace / "subdir").mkdir()
        (self.workspace / "subdir" / "file2.txt").write_text("another file")
        
        self.master_key = os.urandom(32)
        self.security = SecurityUtils(self.master_key)
        
        self.manager = CheckpointManager(
            "test_agent",
            os.path.join(self.test_dir, ".checkpoints"),
            self.security
        )
        
        self.wake_handler = WakeHandler(self.manager, str(self.workspace))
    
    def tearDown(self):
        """Clean up test workspace."""
        shutil.rmtree(self.test_dir)
    
    def test_detect_new_file(self):
        """Test detection of newly added files."""
        # Save initial checkpoint
        self.manager.save_checkpoint({"state": 1}, workspace_root=str(self.workspace))
        
        # Add new file
        (self.workspace / "new_file.txt").write_text("brand new")
        
        # Get diff
        diff = self.manager._get_workspace_diff(str(self.workspace))
        
        self.assertEqual(len(diff["added"]), 1)
        self.assertEqual(diff["added"][0]["path"], "new_file.txt")
    
    def test_detect_modified_file(self):
        """Test detection of modified files."""
        # Save initial checkpoint
        self.manager.save_checkpoint({"state": 1}, workspace_root=str(self.workspace))
        
        # Modify file
        (self.workspace / "file1.txt").write_text("modified content")
        
        diff = self.manager._get_workspace_diff(str(self.workspace))
        
        self.assertEqual(len(diff["modified"]), 1)
        self.assertEqual(diff["modified"][0]["path"], "file1.txt")
    
    def test_detect_deleted_file(self):
        """Test detection of deleted files."""
        # Save initial checkpoint
        self.manager.save_checkpoint({"state": 1}, workspace_root=str(self.workspace))
        
        # Delete file
        (self.workspace / "file1.txt").unlink()
        
        diff = self.manager._get_workspace_diff(str(self.workspace))
        
        self.assertEqual(len(diff["deleted"]), 1)
        self.assertEqual(diff["deleted"][0]["path"], "file1.txt")
    
    def test_no_changes_detected(self):
        """Test that no changes detected when workspace unchanged."""
        # Save checkpoint
        self.manager.save_checkpoint({"state": 1}, workspace_root=str(self.workspace))
        
        # Get diff without changes
        diff = self.manager._get_workspace_diff(str(self.workspace))
        
        self.assertEqual(len(diff["added"]), 0)
        self.assertEqual(len(diff["modified"]), 0)
        self.assertEqual(len(diff["deleted"]), 0)
    
    def test_exclude_patterns(self):
        """Test that excluded patterns are not tracked."""
        # Create .git folder with file
        git_dir = self.workspace / ".git"
        git_dir.mkdir()
        (git_dir / "config").write_text("[core]")
        
        # Save checkpoint
        self.manager.save_checkpoint({"state": 1}, workspace_root=str(self.workspace))
        
        # Modify .git/config
        (git_dir / "config").write_text("[core]\nmodified = true")
        
        diff = self.manager._get_workspace_diff(str(self.workspace))
        
        # Should not be in modified list due to exclusion
        modified_paths = [f["path"] for f in diff["modified"]]
        self.assertNotIn(".git/config", modified_paths)
    
    def test_capture_file_content(self):
        """Test capturing file content for changed files."""
        # Save checkpoint
        self.manager.save_checkpoint({"state": 1}, workspace_root=str(self.workspace))
        
        # Add new file with known content
        test_content = "This is test content for verification"
        (self.workspace / "capture_test.txt").write_text(test_content)
        
        diff = self.manager._get_workspace_diff(str(self.workspace))
        
        # Capture content
        captured = self.manager._capture_file_content(str(self.workspace), diff["added"])
        
        self.assertEqual(len(captured), 1)
        self.assertEqual(captured[0]["content"], test_content)


class TestBackupBeforeDelete(unittest.TestCase):
    """Test backup-before-delete policy."""
    
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.workspace = Path(self.test_dir) / "workspace"
        self.workspace.mkdir()
        
        # Create file to delete
        (self.workspace / "to_delete.txt").write_text("important data")
        
        self.master_key = os.urandom(32)
        self.security = SecurityUtils(self.master_key)
    
    def tearDown(self):
        shutil.rmtree(self.test_dir)
    
    def test_backup_created_before_deletion(self):
        """Test that backups are created for deleted files."""
        manager = CheckpointManager(
            "test_agent",
            os.path.join(self.test_dir, ".checkpoints"),
            self.security
        )
        
        wake_handler = WakeHandler(manager, str(self.workspace))
        
        deleted_files = [{"path": "to_delete.txt"}]
        
        success = wake_handler._create_backup_before_delete(
            str(self.workspace),
            deleted_files
        )
        
        self.assertTrue(success)
        
        # Verify backup exists
        backup_dir = self.workspace / ".checkpoint_backups"
        backups = list(backup_dir.iterdir())
        self.assertGreaterEqual(len(backups), 1)
        
        # Find the deleted file backup
        deleted_backups = backups[0] / "deleted"
        self.assertTrue(deleted_backups.exists())
        self.assertTrue((deleted_backups / "to_delete.txt").exists())
    
    def test_backup_preserves_original_content(self):
        """Test that backup preserves original file content."""
        manager = CheckpointManager(
            "test_agent",
            os.path.join(self.test_dir, ".checkpoints"),
            self.security
        )
        
        wake_handler = WakeHandler(manager, str(self.workspace))
        
        original_content = (self.workspace / "to_delete.txt").read_text()
        
        deleted_files = [{"path": "to_delete.txt"}]
        wake_handler._create_backup_before_delete(str(self.workspace), deleted_files)
        
        # Find backup
        backup_dir = self.workspace / ".checkpoint_backups"
        backup_file = list((backup_dir.iterdir())[0] / "deleted").pop()
        
        backup_content = backup_file.read_text()
        self.assertEqual(backup_content, original_content)


class TestFullCheckpointLifecycle(unittest.TestCase):
    """Test complete checkpoint lifecycle: save → modify → load → restore."""
    
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.workspace = Path(self.test_dir) / "workspace"
        self.workspace.mkdir()
        
        # Initial workspace state
        (self.workspace / "main.py").write_text("# v1\nprint('hello')")
        
        self.master_key = os.urandom(32)
        self.security = SecurityUtils(self.master_key)
        
        self.manager = CheckpointManager(
            "test_agent",
            os.path.join(self.test_dir, ".checkpoints"),
            self.security
        )
        
        self.wake_handler = WakeHandler(self.manager, str(self.workspace))
    
    def tearDown(self):
        shutil.rmtree(self.test_dir)
    
    def test_complete_lifecycle(self):
        """Test saving, modifying, loading, and restoring."""
        # Phase 1: Save initial checkpoint
        context_v1 = {
            "task_plan": ["write code", "test", "deploy"],
            "current_step": 0,
            "memory": ["Remember to add error handling"]
        }
        
        cp_path_1 = self.manager.save_checkpoint(
            context_v1,
            workspace_root=str(self.workspace),
            include_workspace_diff=True
        )
        
        # Phase 2: Make changes to workspace and context
        (self.workspace / "main.py").write_text("# v2\nprint('hello world')\ndef main(): pass")
        (self.workspace / "utils.py").write_text("def helper(): return True")
        
        context_v2 = context_v1.copy()
        context_v2["current_step"] = 1
        context_v2["memory"].append("Added utility functions")
        
        cp_path_2 = self.manager.save_checkpoint(
            context_v2,
            workspace_root=str(self.workspace),
            include_workspace_diff=True
        )
        
        # Phase 3: Simulate interruption - delete workspace files
        (self.workspace / "main.py").unlink()
        (self.workspace / "utils.py").unlink()
        
        # Phase 4: Load latest checkpoint
        loaded_context, loaded_path = self.wake_handler.wake_agent(
            dry_run=False
        )
        
        # Phase 5: Verify restoration
        self.assertIsNotNone(loaded_context)
        self.assertEqual(loaded_context["current_step"], 1)
        self.assertIn("Added utility functions", loaded_context["memory"])
        
        # Verify workspace restored
        self.assertTrue((self.workspace / "main.py").exists())
        self.assertTrue((self.workspace / "utils.py").exists())
        
        restored_main = (self.workspace / "main.py").read_text()
        self.assertIn("def main()", restored_main)


class TestCheckpointWithLargeWorkspace(unittest.TestCase):
    """Test checkpoint performance with larger workspaces."""
    
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.workspace = Path(self.test_dir) / "workspace"
        self.workspace.mkdir()
        
        # Create ~100 small files
        for i in range(100):
            (self.workspace / f"file_{i:03d}.txt").write_text(f"Content {i}")
        
        self.master_key = os.urandom(32)
        self.security = SecurityUtils(self.master_key)
    
    def tearDown(self):
        shutil.rmtree(self.test_dir)
    
    def test_incremental_detection_after_partial_change(self):
        """Test that only changed files are detected."""
        manager = CheckpointManager(
            "test_agent",
            os.path.join(self.test_dir, ".checkpoints"),
            self.security
        )
        
        # Full initial checkpoint
        manager.save_checkpoint({}, workspace_root=str(self.workspace))
        
        # Modify only 5 files
        for i in range(5):
            (self.workspace / f"file_{i:03d}.txt").write_text(f"Modified {i}")
        
        diff = manager._get_workspace_diff(str(self.workspace))
        
        # Should detect exactly 5 modifications
        self.assertEqual(len(diff["modified"]), 5)
        self.assertEqual(len(diff["added"]), 0)
        self.assertEqual(len(diff["deleted"]), 0)
    
    def test_hash_index_persistence(self):
        """Test that file hash index persists between checkpoints."""
        manager = CheckpointManager(
            "test_agent",
            os.path.join(self.test_dir, ".checkpoints"),
            self.security
        )
        
        # First checkpoint
        manager.save_checkpoint({}, workspace_root=str(self.workspace))
        
        # Verify index was saved
        index_file = manager.checkpoint_base_dir / ".file_hashes.json"
        self.assertTrue(index_file.exists())
        
        # Load and check
        with open(index_file) as f:
            index = json.load(f)
        
        self.assertEqual(len(index), 100)  # All 100 files indexed


class TestDryRunMode(unittest.TestCase):
    """Test dry-run mode for wake operations."""
    
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.workspace = Path(self.test_dir) / "workspace"
        self.workspace.mkdir()
        
        (self.workspace / "original.txt").write_text("original")
        
        self.master_key = os.urandom(32)
        self.security = SecurityUtils(self.master_key)
        
        self.manager = CheckpointManager(
            "test_agent",
            os.path.join(self.test_dir, ".checkpoints"),
            self.security
        )
        
        self.wake_handler = WakeHandler(self.manager, str(self.workspace))
    
    def tearDown(self):
        shutil.rmtree(self.test_dir)
    
    def test_dry_run_does_not_modify_workspace(self):
        """Test that dry run doesn't change workspace."""
        # Save checkpoint with different workspace state
        (self.workspace / "original.txt").write_text("modified")
        (self.workspace / "new.txt").write_text("new file")
        
        self.manager.save_checkpoint(
            {},
            workspace_root=str(self.workspace)
        )
        
        # Revert workspace
        (self.workspace / "original.txt").write_text("original")
        (self.workspace / "new.txt").unlink()
        
        # Dry run wake
        self.wake_handler.wake_agent(dry_run=True)
        
        # Workspace should be unchanged
        self.assertEqual(
            (self.workspace / "original.txt").read_text(),
            "original"
        )
        self.assertFalse((self.workspace / "new.txt").exists())


if __name__ == '__main__':
    unittest.main(verbosity=2)
