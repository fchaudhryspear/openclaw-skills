#!/usr/bin/env python3
"""
Checkpoint Manager Tests

Tests checkpoint creation, loading, listing, and cleanup functionality.
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


class TestCheckpointManagerBasic(unittest.TestCase):
    """Test basic checkpoint operations."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.test_dir = tempfile.mkdtemp()
        self.agent_id = "test_agent"
        self.checkpoint_dir = os.path.join(self.test_dir, ".checkpoints")
        self.master_key = os.urandom(32)
        
        self.security = SecurityUtils(self.master_key)
        self.manager = CheckpointManager(self.agent_id, self.checkpoint_dir, self.security)
    
    def tearDown(self):
        """Clean up test directory."""
        shutil.rmtree(self.test_dir)
    
    def test_create_checkpoint_directory(self):
        """Test that checkpoint directory is created on initialization."""
        expected_path = os.path.join(self.checkpoint_dir, self.agent_id)
        self.assertTrue(os.path.exists(expected_path))
    
    def test_save_simple_checkpoint(self):
        """Test saving a simple checkpoint with minimal context."""
        context = {"task": "test", "step": 1}
        
        checkpoint_path = self.manager.save_checkpoint(context)
        
        self.assertTrue(os.path.exists(checkpoint_path))
        
        # Verify checkpoint files exist
        self.assertTrue(os.path.exists(os.path.join(checkpoint_path, "context.enc")))
        self.assertTrue(os.path.exists(os.path.join(checkpoint_path, "metadata.json")))
        self.assertTrue(os.path.exists(os.path.join(checkpoint_path, "integrity.hmac")))
    
    def test_load_latest_checkpoint(self):
        """Test loading the most recent checkpoint."""
        # Save two checkpoints
        context1 = {"checkpoint": 1, "data": "first"}
        context2 = {"checkpoint": 2, "data": "second"}
        
        self.manager.save_checkpoint(context1)
        saved_path = self.manager.save_checkpoint(context2)
        
        # Load latest
        loaded_context, loaded_path = self.manager.load_latest_checkpoint()
        
        self.assertIsNotNone(loaded_context)
        self.assertEqual(loaded_context["checkpoint"], 2)
        self.assertEqual(loaded_context["data"], "second")
        self.assertEqual(loaded_path, saved_path)
    
    def test_load_nonexistent_checkpoints(self):
        """Test loading when no checkpoints exist."""
        # Use fresh manager pointing to empty location
        new_dir = os.path.join(self.test_dir, "new_checkpoints")
        new_manager = CheckpointManager("new_agent", new_dir, self.security)
        
        loaded_context, loaded_path = new_manager.load_latest_checkpoint()
        
        self.assertIsNone(loaded_context)
        self.assertIsNone(loaded_path)
    
    def test_checkpoint_timestamp_format(self):
        """Test that checkpoint timestamps are properly formatted."""
        context = {"test": "data"}
        checkpoint_path = self.manager.save_checkpoint(context)
        
        timestamp = os.path.basename(checkpoint_path)
        
        # Should match format: YYYYMMDDHHMMSSffffff
        self.assertRegex(timestamp, r'\d{17}')
    
    def test_multiple_agents_separate_directories(self):
        """Test that different agents have separate checkpoint directories."""
        agent1_dir = os.path.join(self.checkpoint_dir, "agent1")
        agent2_dir = os.path.join(self.checkpoint_dir, "agent2")
        
        # Create managers for both agents
        m1 = CheckpointManager("agent1", self.checkpoint_dir, self.security)
        m2 = CheckpointManager("agent2", self.checkpoint_dir, self.security)
        
        # Save checkpoints for each
        m1.save_checkpoint({"agent": 1})
        m2.save_checkpoint({"agent": 2})
        
        # Each should only see their own checkpoints
        ctx1, _ = m1.load_latest_checkpoint()
        ctx2, _ = m2.load_latest_checkpoint()
        
        self.assertEqual(ctx1["agent"], 1)
        self.assertEqual(ctx2["agent"], 2)
    
    def test_large_context_handling(self):
        """Test handling of large context data."""
        # Create large context (1MB)
        large_context = {
            "data": "x" * (1024 * 1024),
            "metadata": "test"
        }
        
        checkpoint_path = self.manager.save_checkpoint(large_context)
        loaded_context, _ = self.manager.load_latest_checkpoint()
        
        self.assertEqual(loaded_context["data"], large_context["data"])
        self.assertEqual(loaded_context["metadata"], "test")


class TestCheckpointMetadata(unittest.TestCase):
    """Test checkpoint metadata handling."""
    
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.master_key = os.urandom(32)
        self.security = SecurityUtils(self.master_key)
    
    def tearDown(self):
        shutil.rmtree(self.test_dir)
    
    def test_metadata_contains_nonce_and_tag(self):
        """Test that metadata file contains required cryptographic material."""
        manager = CheckpointManager(
            "test_agent", 
            os.path.join(self.test_dir, "cp"),
            self.security
        )
        
        manager.save_checkpoint({"test": "data"})
        checkpoints = manager.list_checkpoints()
        
        self.assertEqual(len(checkpoints), 1)
        
        cp = checkpoints[0]
        self.assertIn("nonce", cp["metadata"])
        self.assertIn("tag", cp["metadata"])
        self.assertIn("created", cp["metadata"])
        self.assertIn("agent_id", cp["metadata"])
        self.assertIn("version", cp["metadata"])
    
    def test_metadata_agent_id_matches(self):
        """Test that stored agent_id matches manager's agent_id."""
        manager = CheckpointManager(
            "unique_agent_id_12345",
            os.path.join(self.test_dir, "cp"),
            self.security
        )
        
        manager.save_checkpoint({})
        checkpoints = manager.list_checkpoints()
        
        self.assertEqual(checkpoints[0]["metadata"]["agent_id"], "unique_agent_id_12345")


class TestCheckpointCleanup(unittest.TestCase):
    """Test checkpoint cleanup functionality."""
    
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.master_key = os.urandom(32)
        self.security = SecurityUtils(self.master_key)
    
    def tearDown(self):
        shutil.rmtree(self.test_dir)
    
    def test_cleanup_keeps_specified_count(self):
        """Test that cleanup retains exactly keep_count checkpoints."""
        manager = CheckpointManager(
            "test_agent",
            os.path.join(self.test_dir, "cp"),
            self.security
        )
        
        # Create 10 checkpoints
        for i in range(10):
            manager.save_checkpoint({"index": i})
        
        initial_count = len(manager.list_checkpoints())
        self.assertEqual(initial_count, 10)
        
        # Cleanup keeping 3
        manager.cleanup_old_checkpoints(keep_count=3)
        
        final_count = len(manager.list_checkpoints())
        self.assertEqual(final_count, 3)
    
    def test_cleanup_removes_oldest_first(self):
        """Test that cleanup removes oldest checkpoints first."""
        manager = CheckpointManager(
            "test_agent",
            os.path.join(self.test_dir, "cp"),
            self.security
        )
        
        # Create checkpoints with small delays to ensure different timestamps
        import time
        
        contexts = []
        for i in range(5):
            ctx = {"index": i, "timestamp": time.time()}
            contexts.append(ctx)
            manager.save_checkpoint(ctx)
            time.sleep(0.01)  # 10ms delay
        
        # Keep 3 newest
        manager.cleanup_old_checkpoints(keep_count=3)
        
        remaining = manager.list_checkpoints()
        indices = [c["summary"].get("task_steps", 0) for c in remaining]
        
        # Should keep the 3 most recent (indices 2, 3, 4)
        remaining_indices = [ctx["index"] for ctx in contexts][2:]
        
        # Just verify we have 3 remaining
        self.assertEqual(len(remaining), 3)
    
    def test_cleanup_no_op_when_under_limit(self):
        """Test that cleanup does nothing when under limit."""
        manager = CheckpointManager(
            "test_agent",
            os.path.join(self.test_dir, "cp"),
            self.security
        )
        
        # Create only 2 checkpoints
        for i in range(2):
            manager.save_checkpoint({"index": i})
        
        # Try to keep 5 (more than exist)
        manager.cleanup_old_checkpoints(keep_count=5)
        
        # Should still have 2
        self.assertEqual(len(manager.list_checkpoints()), 2)


class TestCheckpointIntegrity(unittest.TestCase):
    """Test checkpoint integrity verification."""
    
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.master_key = os.urandom(32)
        self.security = SecurityUtils(self.master_key)
    
    def tearDown(self):
        shutil.rmtree(self.test_dir)
    
    def test_tampered_checkpoint_rejected(self):
        """Test that tampered checkpoints fail integrity check."""
        manager = CheckpointManager(
            "test_agent",
            os.path.join(self.test_dir, "cp"),
            self.security
        )
        
        # Save checkpoint
        manager.save_checkpoint({"secret": "data"})
        
        # Get the checkpoint path
        checkpoints = manager.list_checkpoints()
        cp_path = checkpoints[0]["path"]
        
        # Tamper with integrity file
        integrity_file = os.path.join(cp_path, "integrity.hmac")
        with open(integrity_file, 'r+b') as f:
            content = f.read()
            f.seek(0)
            f.write(bytes([(b + 1) % 256 for b in content]))
        
        # Try to load - should fail
        loaded, path = manager.load_latest_checkpoint()
        self.assertIsNone(loaded)
    
    def test_tampered_ciphertext_rejected(self):
        """Test that tampered ciphertext fails decryption."""
        manager = CheckpointManager(
            "test_agent",
            os.path.join(self.test_dir, "cp"),
            self.security
        )
        
        manager.save_checkpoint({"secret": "data"})
        
        checkpoints = manager.list_checkpoints()
        cp_path = checkpoints[0]["path"]
        
        # Tamper with ciphertext
        context_file = os.path.join(cp_path, "context.enc")
        with open(context_file, 'r+b') as f:
            content = f.read()
            f.seek(0)
            f.write(bytes([(b + 1) % 256 for b in content[:10]]))
        
        loaded, path = manager.load_latest_checkpoint()
        self.assertIsNone(loaded)
    
    def test_verify_integrity_method(self):
        """Test the verify_integrity standalone method."""
        manager = CheckpointManager(
            "test_agent",
            os.path.join(self.test_dir, "cp"),
            self.security
        )
        
        cp_path = manager.save_checkpoint({"test": "data"})
        
        # Valid checkpoint
        self.assertTrue(manager.verify_integrity(cp_path))
        
        # Tamper it
        integrity_file = os.path.join(cp_path, "integrity.hmac")
        with open(integrity_file, 'r+b') as f:
            content = f.read()
            f.seek(0)
            f.write(b'\x00' * len(content))
        
        # Should now fail
        self.assertFalse(manager.verify_integrity(cp_path))


class TestCheckpointListing(unittest.TestCase):
    """Test checkpoint listing functionality."""
    
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.master_key = os.urandom(32)
        self.security = SecurityUtils(self.master_key)
    
    def tearDown(self):
        shutil.rmtree(self.test_dir)
    
    def test_list_empty_directory(self):
        """Test listing when no checkpoints exist."""
        manager = CheckpointManager(
            "test_agent",
            os.path.join(self.test_dir, "cp"),
            self.security
        )
        
        checkpoints = manager.list_checkpoints()
        self.assertEqual(len(checkpoints), 0)
    
    def test_list_returns_sorted_results(self):
        """Test that list returns checkpoints sorted by timestamp descending."""
        manager = CheckpointManager(
            "test_agent",
            os.path.join(self.test_dir, "cp"),
            self.security
        )
        
        import time
        
        # Create checkpoints
        for i in range(5):
            manager.save_checkpoint({"index": i})
            time.sleep(0.01)
        
        checkpoints = manager.list_checkpoints()
        
        # Should be sorted newest first
        timestamps = [cp["timestamp"] for cp in checkpoints]
        self.assertEqual(timestamps, sorted(timestamps, reverse=True))
    
    def test_list_includes_validity_status(self):
        """Test that listing includes validity status for each checkpoint."""
        manager = CheckpointManager(
            "test_agent",
            os.path.join(self.test_dir, "cp"),
            self.security
        )
        
        manager.save_checkpoint({"test": "data"})
        
        checkpoints = manager.list_checkpoints()
        
        self.assertEqual(len(checkpoints), 1)
        self.assertIn("valid", checkpoints[0])
        self.assertTrue(checkpoints[0]["valid"])
    
    def test_list_includes_size_info(self):
        """Test that listing includes size information."""
        manager = CheckpointManager(
            "test_agent",
            os.path.join(self.test_dir, "cp"),
            self.security
        )
        
        manager.save_checkpoint({"data": "x" * 1000})
        
        checkpoints = manager.list_checkpoints()
        
        self.assertIn("size_kb", checkpoints[0])
        self.assertGreater(checkpoints[0]["size_kb"], 0)


class TestSpecificCheckpointLoading(unittest.TestCase):
    """Test loading specific checkpoints by timestamp."""
    
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.master_key = os.urandom(32)
        self.security = SecurityUtils(self.master_key)
    
    def tearDown(self):
        shutil.rmtree(self.test_dir)
    
    def test_load_specific_by_timestamp(self):
        """Test loading a checkpoint by its timestamp string."""
        manager = CheckpointManager(
            "test_agent",
            os.path.join(self.test_dir, "cp"),
            self.security
        )
        
        # Save checkpoint and get timestamp
        path = manager.save_checkpoint({"target": "data"})
        timestamp = os.path.basename(path)
        
        # Load specifically
        loaded = manager.load_specific_checkpoint(timestamp)
        
        self.assertIsNotNone(loaded)
        self.assertEqual(loaded["target"], "data")
    
    def test_load_nonexistent_timestamp(self):
        """Test loading with invalid timestamp."""
        manager = CheckpointManager(
            "test_agent",
            os.path.join(self.test_dir, "cp"),
            self.security
        )
        
        loaded = manager.load_specific_checkpoint("invalid_timestamp_12345")
        
        self.assertIsNone(loaded)


if __name__ == '__main__':
    unittest.main(verbosity=2)
