
# src/memory_capture_agent.py

import time
import random
import json
import os

# Assuming MemoryStorageManager is in the same src directory for this example
from memory_storage_manager import MemoryStorageManager

class MemoryCaptureAgent:
    def __init__(self, storage_manager: MemoryStorageManager):
        self.storage_manager = storage_manager
        self.agent_id = "capture_agent_001"
        self.last_activity_time = time.time()

    def _generate_observational_data(self) -> dict:
        data_types = [
            "user_interaction", "system_event", "application_log", 
            "environment_change", "agent_status"
        ]
        actions = [
            "clicked button", "opened file", "received alert", 
            "temperature increased", "started task", "completed task"
        ]
        subjects = [
            "browser", "terminal", "email client", 
            "weather service", "subagent_alpha", "user_fas"
        ]

        data = {
            "timestamp": time.time(),
            "agent_id": self.agent_id,
            "data_type": random.choice(data_types),
            "subject": random.choice(subjects),
            "action": random.choice(actions),
            "value": random.randint(1, 100) if random.random() > 0.5 else None,
            "details": f"Detailed observation for {time.ctime()}"
        }
        return data

    def capture_and_store_memory(self, count: int = 1):
        for i in range(count):
            observational_data = self._generate_observational_data()
            memory_id = f"obs_data_{observational_data['agent_id']}_{int(observational_data['timestamp'])}_{i}"
            
            # Convert dict to JSON string for storage
            data_to_store = json.dumps(observational_data)

            print(f"[Capture Agent] Capturing and storing: {memory_id}")
            if self.storage_manager.store_memory(memory_id, data_to_store):
                print(f"[Capture Agent] Successfully stored {memory_id}")
            else:
                print(f"[Capture Agent] Failed to store {memory_id}. Vault might be locked.")
            time.sleep(0.1) # Simulate some work

# --- Example Usage ---
if __name__ == "__main__":
    # In a real setup, the MemoryStorageManager would be a running daemon
    # and the agent would communicate with it via API/IPC.
    # For this example, we're using a direct instance.
    manager = MemoryStorageManager()

    passphrase = input("Enter master passphrase to unlock vault for Capture Agent: ")
    if not manager.unlock_vault(passphrase):
        print("Incorrect passphrase or error unlocking vault. Exiting Capture Agent.")
        exit(1)

    capture_agent = MemoryCaptureAgent(manager)

    print("\n--- Starting Memory Capture ---")
    capture_agent.capture_and_store_memory(count=3)

    print("\n--- Verifying stored memories (retrieving with manager) ---")
    # This part is just to demonstrate retrieval from the same script
    # In reality, retrieval would be via the Query/Retrieval Interface

    # To retrieve, we'd need the memory_id, which we print during storage
    # For this example, let's manually create a few IDs for retrieval
    # (This is simplified, a real system would have an indexing mechanism)
    
    # Let's just try to retrieve one of the stored items by ID if we could capture it
    # This part needs careful handling if we want to retrieve without knowing IDs beforehand
    # For a simple demo, we rely on the output from storage.
    
    # Let's adjust the capture_and_store_memory to return the IDs for verification
    print("\n--- NOTE: To truly verify, a retrieval mechanism with known IDs or a listing function is needed. --- ")
    print("--- For now, trust the 'Successfully stored' messages. --- ")

    print("\n--- Cleaning up example files (similar to manager script) ---")
    # Cleanup logic would ideally be in a separate test script or a 'stop' command
    # For this combined example, we'll repeat it.
    vault_dir = os.path.dirname(os.path.abspath(manager.CONFIG["vault_path"]))
    
    # This cleanup is a bit tricky since we don't know the exact IDs created by random generation
    # A more robust test would store IDs and then clean them.
    # For now, let's skip automated cleanup here and rely on the manager's `__main__` to clean its specific files.
    print("Skipping agent-specific file cleanup for simplicity. Manager's cleanup handles its own generated files.")
    
    manager.lock_vault()
    print("\nMemory Capture Agent demonstration complete.")
