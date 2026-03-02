
import os
import json
import shutil
from datetime import datetime
from typing import Any, Dict, Tuple

from security_utils import SecurityUtils

class CheckpointManager:
    def __init__(self, agent_id: str, checkpoint_dir: str, security_utils: SecurityUtils):
        self.agent_id = agent_id
        self.checkpoint_base_dir = os.path.join(checkpoint_dir, agent_id)
        os.makedirs(self.checkpoint_base_dir, exist_ok=True)
        self.security_utils = security_utils

    def _get_checkpoint_path(self, timestamp: str) -> str:
        return os.path.join(self.checkpoint_base_dir, timestamp)

    def _get_context_file_path(self, checkpoint_path: str) -> str:
        return os.path.join(checkpoint_path, "context.enc")

    def _get_integrity_file_path(self, checkpoint_path: str) -> str:
        return os.path.join(checkpoint_path, "integrity.hmac")

    def _get_metadata_file_path(self, checkpoint_path: str) -> str:
        return os.path.join(checkpoint_path, "metadata.json") # For nonce, tag, etc.

    def save_checkpoint(self, agent_context: Dict[str, Any]) -> str:
        """Saves the agent's context to a new, encrypted checkpoint."""
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S%f")
        checkpoint_path = self._get_checkpoint_path(timestamp)
        os.makedirs(checkpoint_path, exist_ok=True)

        # Serialize context to JSON bytes
        context_bytes = json.dumps(agent_context, indent=2).encode('utf-8')

        # Encrypt the context
        ciphertext, nonce, tag = self.security_utils.encrypt(context_bytes)

        # Save encrypted context, nonce, and tag
        with open(self._get_context_file_path(checkpoint_path), 'wb') as f:
            f.write(ciphertext)

        # Save metadata (nonce and tag)
        metadata = {
            "nonce": nonce.hex(),
            "tag": tag.hex()
        }
        with open(self._get_metadata_file_path(checkpoint_path), 'w') as f:
            json.dump(metadata, f, indent=2)

        # Generate and save HMAC for integrity of the encrypted data + metadata
        # We hash the ciphertext, nonce, and tag to ensure integrity of the entire encrypted bundle
        data_for_hmac = ciphertext + nonce + tag
        hmac_value = self.security_utils.generate_hmac(data_for_hmac, nonce)
        with open(self._get_integrity_file_path(checkpoint_path), 'wb') as f:
            f.write(hmac_value)

        print(f"Checkpoint saved to: {checkpoint_path}")
        return checkpoint_path

    def load_latest_checkpoint(self) -> Tuple[Dict[str, Any], str] | Tuple[None, None]:
        """Loads the latest valid checkpoint for the agent."""
        if not os.path.exists(self.checkpoint_base_dir):
            return None, None
        checkpoints = sorted([d for d in os.listdir(self.checkpoint_base_dir) 
                              if os.path.isdir(os.path.join(self.checkpoint_base_dir, d))], reverse=True)

        for timestamp in checkpoints:
            checkpoint_path = self._get_checkpoint_path(timestamp)
            try:
                # Load metadata
                with open(self._get_metadata_file_path(checkpoint_path), 'r') as f:
                    metadata = json.load(f)
                nonce = bytes.fromhex(metadata["nonce"])
                tag = bytes.fromhex(metadata["tag"])

                # Load ciphertext
                with open(self._get_context_file_path(checkpoint_path), 'rb') as f:
                    ciphertext = f.read()
                
                # Verify HMAC first
                with open(self._get_integrity_file_path(checkpoint_path), 'rb') as f:
                    expected_hmac = f.read()

                data_for_hmac = ciphertext + nonce + tag
                if not self.security_utils.verify_hmac(data_for_hmac, expected_hmac, nonce):
                    print(f"Integrity check failed for checkpoint {timestamp}. Skipping.")
                    continue

                # Decrypt context
                plaintext_bytes = self.security_utils.decrypt(ciphertext, nonce, tag)
                agent_context = json.loads(plaintext_bytes.decode('utf-8'))
                print(f"Successfully loaded checkpoint from: {checkpoint_path}")
                return agent_context, checkpoint_path

            except Exception as e:
                print(f"Error loading checkpoint {timestamp}: {e}. Skipping.")
                # Optionally, clean up corrupted checkpoint
                # shutil.rmtree(checkpoint_path, ignore_errors=True)
        
        print("No valid checkpoint found.")
        return None, None

    def cleanup_old_checkpoints(self, keep_count: int = 5):
        """Removes older checkpoints, keeping only the most recent `keep_count`."""
        checkpoints = sorted([d for d in os.listdir(self.checkpoint_base_dir) 
                              if os.path.isdir(os.path.join(self.checkpoint_base_dir, d))], reverse=True)
        
        if len(checkpoints) > keep_count:
            for old_checkpoint in checkpoints[keep_count:]:
                path_to_delete = os.path.join(self.checkpoint_base_dir, old_checkpoint)
                shutil.rmtree(path_to_delete)
                print(f"Cleaned up old checkpoint: {path_to_delete}")


# Example usage (for testing)
if __name__ == "__main__":
    # Setup
    AGENT_ID = "test_agent_123"
    CHECKPOINT_BASE_DIR = "./.checkpoints"
    MASTER_KEY = os.urandom(32) # In a real app, load this securely

    security = SecurityUtils(MASTER_KEY)
    manager = CheckpointManager(AGENT_ID, CHECKPOINT_BASE_DIR, security)

    # Simulate agent context
    initial_context = {
        "task_plan": ["step 1", "step 2", "step 3"],
        "current_step": 0,
        "memory": ["fact A", "fact B"],
        "tool_sessions": {"exec_1": {"id": "abc", "status": "running"}}
    }

    print("\n--- Saving initial checkpoint ---")
    manager.save_checkpoint(initial_context)

    # Simulate some work and another checkpoint
    initial_context["current_step"] = 1
    initial_context["memory"].append("fact C")
    print("\n--- Saving updated checkpoint ---")
    manager.save_checkpoint(initial_context)

    # Load latest checkpoint
    print("\n--- Loading latest checkpoint ---")
    loaded_context, loaded_path = manager.load_latest_checkpoint()
    if loaded_context:
        print(f"Loaded Context: {json.dumps(loaded_context, indent=2)}")
        assert loaded_context["current_step"] == 1
        assert "fact C" in loaded_context["memory"]
        print("Context loaded successfully and matches updated state.")
    else:
        print("Failed to load any checkpoint.")
    
    # Test cleanup
    print("\n--- Saving more checkpoints for cleanup test ---")
    for i in range(5):
        temp_context = {"data": f"checkpoint {i}"}
        manager.save_checkpoint(temp_context)

    print("\n--- Cleaning up old checkpoints (keeping 3) ---")
    manager.cleanup_old_checkpoints(keep_count=3)
    print("Remaining checkpoints:")
    print(os.listdir(manager.checkpoint_base_dir))

    # Simulate tampering with a checkpoint
    print("\n--- Testing tampering ---")
    tamper_timestamp = datetime.now().strftime("%Y%m%d%H%M%S%f") # New checkpoint for tampering
    tamper_context = {"secret": "should not be read"}
    tamper_checkpoint_path = manager.save_checkpoint(tamper_context)

    print(f"Tampering with checkpoint: {tamper_checkpoint_path}")
    context_file = manager._get_context_file_path(tamper_checkpoint_path)
    with open(context_file, 'rb+') as f:
        content = f.read()
        f.seek(0)
        f.write(content[:-1] + b'\x00') # Corrupt last byte

    print("\n--- Attempting to load latest (tampered) checkpoint ---")
    tampered_loaded_context, _ = manager.load_latest_checkpoint()
    if tampered_loaded_context:
        print("ERROR: Tampered checkpoint was loaded!")
    else:
        print("SUCCESS: Tampered checkpoint was detected and skipped.")

    # Cleanup test checkpoints directory
    print(f"\n--- Cleaning up all test checkpoints in {CHECKPOINT_BASE_DIR} ---")
    shutil.rmtree(CHECKPOINT_BASE_DIR)

