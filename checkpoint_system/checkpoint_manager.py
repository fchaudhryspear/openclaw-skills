#!/usr/bin/env python3
"""
Enhanced Checkpoint Manager - Handles agent state persistence

Features:
- AES-256 GCM encryption for context data
- HMAC-SHA256 integrity verification
- Workspace diff/snapshot capture
- Backup-before-delete policy
- Automatic cleanup of old checkpoints
"""

import os
import json
import shutil
import hashlib
import subprocess
from datetime import datetime
from typing import Any, Dict, Tuple, List, Optional
from pathlib import Path


class CheckpointManager:
    """Manages saving and loading of encrypted agent checkpoints."""
    
    def __init__(self, agent_id: str, checkpoint_dir: str, security_utils):
        """
        Initialize the checkpoint manager.
        
        Args:
            agent_id: Unique identifier for this agent
            checkpoint_dir: Base directory for storing checkpoints
            security_utils: Instance of SecurityUtils for encryption/HMAC
        """
        self.agent_id = agent_id
        self.checkpoint_base_dir = Path(checkpoint_dir) / agent_id
        self.checkpoint_base_dir.mkdir(parents=True, exist_ok=True)
        self.security_utils = security_utils
        
        # Track file hashes for incremental diffs
        self._file_hash_index = self._load_file_hash_index()
    
    def _load_file_hash_index(self) -> Dict[str, str]:
        """Load the file hash index from disk."""
        index_path = self.checkpoint_base_dir / ".file_hashes.json"
        if index_path.exists():
            try:
                with open(index_path, 'r') as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}
    
    def _save_file_hash_index(self):
        """Save the file hash index to disk."""
        index_path = self.checkpoint_base_dir / ".file_hashes.json"
        with open(index_path, 'w') as f:
            json.dump(self._file_hash_index, f, indent=2)
    
    def _calculate_file_hash(self, file_path: Path) -> str:
        """Calculate SHA-256 hash of a file."""
        sha256_hash = hashlib.sha256()
        try:
            with open(file_path, "rb") as f:
                for byte_block in iter(lambda: f.read(4096), b""):
                    sha256_hash.update(byte_block)
            return sha256_hash.hexdigest()
        except Exception:
            return ""
    
    def _get_workspace_diff(self, workspace_root: str, 
                           exclude_patterns: List[str] = None) -> Dict[str, Any]:
        """
        Calculate workspace differences since last checkpoint.
        
        Uses hash-based change detection similar to ClawVault's incremental indexing.
        
        Args:
            workspace_root: Root directory of the workspace
            exclude_patterns: Patterns to exclude from tracking
            
        Returns:
            Dictionary with 'added', 'modified', 'deleted' file lists
        """
        workspace_root = Path(workspace_root)
        current_hashes = {}
        diff = {
            "added": [],
            "modified": [],
            "deleted": []
        }
        
        if not workspace_root.exists():
            return diff
        
        # Default exclusion patterns
        if exclude_patterns is None:
            exclude_patterns = [
                ".git", ".venv", "__pycache__", ".checkpoints", 
                ".checkpoint_backups", "node_modules", ".pytest_cache",
                ".openclaw", "*.pyc", ".DS_Store"
            ]
        
        # Walk workspace and calculate hashes
        for file_path in workspace_root.rglob("*"):
            if file_path.is_file():
                # Check exclusions
                rel_path = str(file_path.relative_to(workspace_root))
                excluded = any(pattern in rel_path for pattern in exclude_patterns)
                
                if not excluded:
                    file_hash = self._calculate_file_hash(file_path)
                    current_hashes[rel_path] = file_hash
                    
                    # Compare with previous checkpoint
                    if rel_path not in self._file_hash_index:
                        # New file
                        diff["added"].append({
                            "path": rel_path,
                            "hash": file_hash
                        })
                    elif self._file_hash_index[rel_path] != file_hash:
                        # Modified file
                        diff["modified"].append({
                            "path": rel_path,
                            "hash": file_hash,
                            "previous_hash": self._file_hash_index[rel_path]
                        })
        
        # Check for deleted files
        for prev_path in self._file_hash_index.keys():
            if prev_path not in current_hashes:
                diff["deleted"].append({
                    "path": prev_path,
                    "hash": self._file_hash_index[prev_path]
                })
        
        # Update index
        self._file_hash_index = current_hashes
        self._save_file_hash_index()
        
        return diff
    
    def _capture_file_content(self, workspace_root: str, 
                             files: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Capture content of specified files.
        
        Args:
            workspace_root: Root directory of workspace
            files: List of file info dicts with 'path' key
            
        Returns:
            Updated file info with content embedded
        """
        workspace_root = Path(workspace_root)
        captured = []
        
        for file_info in files:
            file_path = workspace_root / file_info["path"]
            
            if file_path.exists():
                try:
                    # Check file size (limit to 10MB per file)
                    file_size = file_path.stat().st_size
                    if file_size > 10 * 1024 * 1024:
                        print(f"⚠️  Skipping large file: {file_info['path']} ({file_size} bytes)")
                        continue
                    
                    # Try text first
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            file_info["content"] = f.read()
                    except UnicodeDecodeError:
                        # Binary file - use base64
                        import base64
                        with open(file_path, 'rb') as f:
                            file_info["content_b64"] = base64.b64encode(f.read()).decode('utf-8')
                    
                    captured.append(file_info)
                except Exception as e:
                    print(f"⚠️  Could not capture {file_info['path']}: {e}")
        
        return captured
    
    def _create_backup_before_delete(self, workspace_root: str,
                                    deleted_files: List[Dict[str, Any]]) -> bool:
        """
        Create backup of workspace before deletion operations.
        
        Implements backup-before-delete policy.
        
        Args:
            workspace_root: Root directory of workspace
            deleted_files: List of deleted file infos
            
        Returns:
            True if backup successful
        """
        if not deleted_files:
            return True
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_dir = Path(workspace_root) / ".checkpoint_backups" / timestamp
        
        try:
            # Backup specific deleted files
            deleted_backup_dir = backup_dir / "deleted"
            deleted_backup_dir.mkdir(parents=True, exist_ok=True)
            
            workspace_root = Path(workspace_root)
            for file_info in deleted_files:
                file_path = workspace_root / file_info["path"]
                if file_path.exists():
                    # Create safe filename
                    safe_name = file_info["path"].replace("/", "_").replace("\\", "_")
                    dest_path = deleted_backup_dir / safe_name
                    dest_path.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(file_path, dest_path)
            
            print(f"✅ Backup created: {backup_dir}")
            return True
            
        except Exception as e:
            print(f"❌ Backup failed: {e}")
            return False
    
    def save_checkpoint(self, 
                       agent_context: Dict[str, Any],
                       workspace_root: Optional[str] = None,
                       include_workspace_diff: bool = True,
                       backup_deleted: bool = True) -> str:
        """
        Save agent context to an encrypted checkpoint.
        
        Args:
            agent_context: Dictionary containing agent state
            workspace_root: Optional workspace root for diff capture
            include_workspace_diff: Whether to capture workspace changes
            backup_deleted: Whether to backup deleted files before removal
            
        Returns:
            Path to the saved checkpoint
        """
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S%f")
        checkpoint_path = self.checkpoint_base_dir / timestamp
        checkpoint_path.mkdir(parents=True, exist_ok=True)
        
        print(f"\n{'='*60}")
        print("💾 SAVING CHECKPOINT")
        print(f"{'='*60}")
        print(f"Agent ID: {self.agent_id}")
        print(f"Timestamp: {timestamp}")
        
        # Capture workspace diff if requested
        if include_workspace_diff and workspace_root:
            print("\n📁 Capturing workspace changes...")
            workspace_diff = self._get_workspace_diff(workspace_root)
            
            # Capture content of changed files
            all_changed = (workspace_diff["added"] + 
                          workspace_diff["modified"])
            captured_files = self._capture_file_content(workspace_root, all_changed)
            
            # Attach captured content to diff
            content_map = {f["path"]: f for f in captured_files}
            for file_info in workspace_diff["added"] + workspace_diff["modified"]:
                path = file_info["path"]
                if path in content_map:
                    # Merge captured data into file_info
                    for key, value in content_map[path].items():
                        if key != "path":  # Don't overwrite path
                            file_info[key] = value
            
            # Backup deleted files before removing them from workspace
            if backup_deleted and workspace_diff["deleted"]:
                print(f"  🔒 Backing up {len(workspace_diff['deleted'])} deleted files...")
                self._create_backup_before_delete(workspace_root, workspace_diff["deleted"])
            
            agent_context["workspace_diff"] = workspace_diff
            print(f"  ✅ Captured: +{len(workspace_diff['added'])} ~{len(workspace_diff['modified'])} -{len(workspace_diff['deleted'])}")
        
        # Serialize context to JSON bytes
        context_bytes = json.dumps(agent_context, indent=2, default=str).encode('utf-8')
        
        # Encrypt the context
        print("\n🔐 Encrypting context...")
        ciphertext, nonce, tag = self.security_utils.encrypt(context_bytes)
        print(f"  Encrypted size: {len(ciphertext)} bytes")
        
        # Save encrypted context
        context_file_path = checkpoint_path / "context.enc"
        with open(context_file_path, 'wb') as f:
            f.write(ciphertext)
        
        # Save metadata (nonce and tag)
        metadata = {
            "nonce": nonce.hex(),
            "tag": tag.hex(),
            "created": datetime.now().isoformat(),
            "agent_id": self.agent_id,
            "version": "1.0"
        }
        metadata_path = checkpoint_path / "metadata.json"
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        # Generate and save HMAC for integrity
        data_for_hmac = ciphertext + nonce + tag
        hmac_value = self.security_utils.generate_hmac(data_for_hmac, nonce)
        
        integrity_path = checkpoint_path / "integrity.hmac"
        with open(integrity_path, 'wb') as f:
            f.write(hmac_value)
        
        print(f"✅ Checkpoint saved: {checkpoint_path}")
        print(f"{'='*60}\n")
        
        return str(checkpoint_path)
    
    def load_latest_checkpoint(self) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        """
        Load the latest valid checkpoint for the agent.
        
        Returns:
            Tuple of (agent_context, checkpoint_path) or (None, None) if none found
        """
        if not self.checkpoint_base_dir.exists():
            print("ℹ️  No checkpoint directory found.")
            return None, None
        
        # Get sorted list of checkpoints (newest first)
        checkpoints = sorted([
            d for d in self.checkpoint_base_dir.iterdir() 
            if d.is_dir() and d.name != "."
        ], key=lambda x: x.name, reverse=True)
        
        print(f"\n{'='*60}")
        print("🔄 LOADING LATEST CHECKPOINT")
        print(f"{'='*60}")
        print(f"Found {len(checkpoints)} checkpoint(s)")
        
        for checkpoint_path in checkpoints:
            timestamp = checkpoint_path.name
            print(f"\n🔍 Attempting: {timestamp}")
            
            try:
                # Load metadata
                metadata_path = checkpoint_path / "metadata.json"
                if not metadata_path.exists():
                    print(f"  ❌ Missing metadata.json")
                    continue
                    
                with open(metadata_path, 'r') as f:
                    metadata = json.load(f)
                
                nonce = bytes.fromhex(metadata["nonce"])
                tag = bytes.fromhex(metadata["tag"])
                
                # Load ciphertext
                context_path = checkpoint_path / "context.enc"
                if not context_path.exists():
                    print(f"  ❌ Missing context.enc")
                    continue
                    
                with open(context_path, 'rb') as f:
                    ciphertext = f.read()
                
                # Verify HMAC first (before decryption)
                integrity_path = checkpoint_path / "integrity.hmac"
                if not integrity_path.exists():
                    print(f"  ❌ Missing integrity.hmac")
                    continue
                    
                with open(integrity_path, 'rb') as f:
                    expected_hmac = f.read()
                
                data_for_hmac = ciphertext + nonce + tag
                if not self.security_utils.verify_hmac(data_for_hmac, expected_hmac, nonce):
                    print(f"  ❌ Integrity check FAILED - possible tampering")
                    continue
                
                print(f"  ✅ Integrity verified")
                
                # Decrypt context
                plaintext_bytes = self.security_utils.decrypt(ciphertext, nonce, tag)
                agent_context = json.loads(plaintext_bytes.decode('utf-8'))
                
                print(f"✅ Successfully loaded checkpoint from: {checkpoint_path}")
                print(f"{'='*60}\n")
                
                return agent_context, str(checkpoint_path)
                
            except Exception as e:
                print(f"  ⚠️  Error loading checkpoint: {e}")
                # Continue to next checkpoint
        
        print("\n❌ No valid checkpoint found.\n")
        return None, None
    
    def load_specific_checkpoint(self, timestamp: str) -> Optional[Dict[str, Any]]:
        """Load a specific checkpoint by timestamp."""
        checkpoint_path = self.checkpoint_base_dir / timestamp
        
        if not checkpoint_path.exists():
            print(f"❌ Checkpoint not found: {timestamp}")
            return None
        
        try:
            # Similar to load_latest_checkpoint but without iteration
            metadata_path = checkpoint_path / "metadata.json"
            with open(metadata_path, 'r') as f:
                metadata = json.load(f)
            
            nonce = bytes.fromhex(metadata["nonce"])
            tag = bytes.fromhex(metadata["tag"])
            
            with open(checkpoint_path / "context.enc", 'rb') as f:
                ciphertext = f.read()
            
            with open(checkpoint_path / "integrity.hmac", 'rb') as f:
                expected_hmac = f.read()
            
            data_for_hmac = ciphertext + nonce + tag
            if not self.security_utils.verify_hmac(data_for_hmac, expected_hmac, nonce):
                print(f"❌ Integrity check failed")
                return None
            
            plaintext_bytes = self.security_utils.decrypt(ciphertext, nonce, tag)
            return json.loads(plaintext_bytes.decode('utf-8'))
            
        except Exception as e:
            print(f"❌ Error loading checkpoint: {e}")
            return None
    
    def list_checkpoints(self) -> List[Dict[str, Any]]:
        """
        List all available checkpoints with metadata.
        
        Returns:
            List of checkpoint info dictionaries
        """
        checkpoints = []
        
        if not self.checkpoint_base_dir.exists():
            return checkpoints
        
        for cp_dir in self.checkpoint_base_dir.iterdir():
            if not cp_dir.is_dir() or cp_dir.name.startswith("."):
                continue
            
            try:
                # Get basic info
                size_bytes = sum(f.stat().st_size for f in cp_dir.glob("**/*") if f.is_file())
                
                # Load metadata if available
                metadata_path = cp_dir / "metadata.json"
                metadata = {}
                summary = {}
                valid = False
                
                if metadata_path.exists():
                    try:
                        with open(metadata_path, 'r') as f:
                            metadata = json.load(f)
                        
                        # Try to load and summarize context
                        context_path = cp_dir / "context.enc"
                        integrity_path = cp_dir / "integrity.hmac"
                        
                        if context_path.exists() and integrity_path.exists():
                            nonce = bytes.fromhex(metadata["nonce"])
                            tag = bytes.fromhex(metadata["tag"])
                            
                            with open(context_path, 'rb') as f:
                                ciphertext = f.read()
                            with open(integrity_path, 'rb') as f:
                                expected_hmac = f.read()
                            
                            data_for_hmac = ciphertext + nonce + tag
                            if self.security_utils.verify_hmac(data_for_hmac, expected_hmac, nonce):
                                valid = True
                                plaintext_bytes = self.security_utils.decrypt(ciphertext, nonce, tag)
                                context = json.loads(plaintext_bytes.decode('utf-8'))
                                
                                # Create summary
                                summary = {
                                    "has_task_plan": "task_plan" in context,
                                    "task_steps": len(context.get("task_plan", [])),
                                    "memory_items": len(context.get("memory", [])),
                                    "tool_sessions": len(context.get("tool_sessions", {})),
                                    "chat_messages": len(context.get("chat_history", [])),
                                    "workspace_changes": bool(context.get("workspace_diff"))
                                }
                    except Exception:
                        pass
                
                checkpoints.append({
                    "path": str(cp_dir),
                    "timestamp": cp_dir.name,
                    "size_kb": size_bytes / 1024,
                    "valid": valid,
                    "metadata": metadata,
                    "summary": summary
                })
                
            except Exception as e:
                print(f"⚠️  Error reading checkpoint {cp_dir.name}: {e}")
        
        # Sort by timestamp descending
        checkpoints.sort(key=lambda x: x["timestamp"], reverse=True)
        
        return checkpoints
    
    def cleanup_old_checkpoints(self, keep_count: int = 5):
        """
        Remove older checkpoints, keeping only the most recent.
        
        Args:
            keep_count: Number of checkpoints to keep
        """
        checkpoints = self.list_checkpoints()
        
        if len(checkpoints) <= keep_count:
            print(f"ℹ️  Only {len(checkpoints)} checkpoint(s) exist, nothing to clean.")
            return
        
        print(f"\n🧹 Cleaning up checkpoints (keeping {keep_count} of {len(checkpoints)})...")
        
        to_remove = checkpoints[keep_count:]
        for cp_info in to_remove:
            try:
                shutil.rmtree(cp_info["path"])
                print(f"  🗑️  Removed: {cp_info['timestamp']}")
            except Exception as e:
                print(f"  ❌ Failed to remove {cp_info['timestamp']}: {e}")
        
        print(f"✅ Cleanup complete. {len(to_remove)} checkpoint(s) removed.")
    
    def verify_integrity(self, checkpoint_path: str) -> bool:
        """
        Verify integrity of a specific checkpoint without loading it.
        
        Args:
            checkpoint_path: Path to checkpoint directory
            
        Returns:
            True if integrity check passes
        """
        cp_path = Path(checkpoint_path)
        
        try:
            metadata_path = cp_path / "metadata.json"
            context_path = cp_path / "context.enc"
            integrity_path = cp_path / "integrity.hmac"
            
            if not all(p.exists() for p in [metadata_path, context_path, integrity_path]):
                return False
            
            with open(metadata_path, 'r') as f:
                metadata = json.load(f)
            
            nonce = bytes.fromhex(metadata["nonce"])
            tag = bytes.fromhex(metadata["tag"])
            
            with open(context_path, 'rb') as f:
                ciphertext = f.read()
            with open(integrity_path, 'rb') as f:
                expected_hmac = f.read()
            
            data_for_hmac = ciphertext + nonce + tag
            return self.security_utils.verify_hmac(data_for_hmac, expected_hmac, nonce)
            
        except Exception:
            return False


# Example usage
if __name__ == "__main__":
    from security_utils import SecurityUtils
    
    # Setup
    AGENT_ID = "test_manager"
    WORKSPACE_ROOT = "/Users/faisalshomemacmini/.openclaw/workspace"
    CHECKPOINT_BASE_DIR = "./.checkpoints"
    MASTER_KEY = os.urandom(32)
    
    security = SecurityUtils(MASTER_KEY)
    manager = CheckpointManager(AGENT_ID, CHECKPOINT_BASE_DIR, security)
    
    # Test 1: Simple checkpoint
    print("\n=== Test 1: Simple Context Checkpoint ===")
    simple_context = {
        "task_plan": ["analyze", "implement", "test"],
        "current_step": 0,
        "memory": ["key insight here"]
    }
    path1 = manager.save_checkpoint(simple_context)
    
    # Test 2: Workspace diff checkpoint
    print("\n=== Test 2: Workspace Diff Checkpoint ===")
    enhanced_context = {
        **simple_context,
        "chat_history": [{"role": "user", "content": "hello"}],
        "tool_sessions": {"exec_1": {"id": "abc", "status": "running"}}
    }
    path2 = manager.save_checkpoint(enhanced_context, workspace_root=WORKSPACE_ROOT)
    
    # Test 3: Load latest
    print("\n=== Test 3: Load Latest ===")
    loaded, path = manager.load_latest_checkpoint()
    if loaded:
        print(f"Loaded successfully from: {path}")
        print(f"Task plan: {loaded.get('task_plan')}")
    
    # Test 4: List checkpoints
    print("\n=== Test 4: List Checkpoints ===")
    checkpoints = manager.list_checkpoints()
    for cp in checkpoints:
        status = "✅" if cp["valid"] else "❌"
        print(f"{status} {cp['timestamp']} ({cp['size_kb']:.1f} KB)")
    
    # Test 5: Cleanup
    print("\n=== Test 5: Cleanup Old Checkpoints ===")
    manager.cleanup_old_checkpoints(keep_count=1)
    
    # Cleanup test
    print("\n=== Cleaning Up ===")
    shutil.rmtree(CHECKPOINT_BASE_DIR)
