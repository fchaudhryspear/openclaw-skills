
# src/memory_storage_manager.py

import os
import json
import logging
from base64 import urlsafe_b64encode, urlsafe_b64decode
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend

# --- Configuration (will be loaded from config.json) ---
CONFIG = {
    "vault_path": "../data/vault.enc",
    "log_file": "../logs/memory_storage_manager.log",
    "salt_file": "../config/salt.bin",
    "kdf_n": 2**14,  # Scrypt N parameter (CPU/memory cost)
    "kdf_r": 8,     # Scrypt r parameter (block size)
    "kdf_p": 1,     # Scrypt p parameter (parallelization)
    "kdf_length": 32 # 32 bytes for AES-256 key
}

# --- Logging Setup ---
logging.basicConfig(filename=CONFIG["log_file"], level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class MemoryStorageManager:
    _instance = None
    _encryption_key = None
    _salt = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(MemoryStorageManager, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if not hasattr(self, '_initialized'):
            self._initialized = True
            self._load_config()
            self._ensure_directories()
            self._load_or_generate_salt()

    def _load_config(self):
        # Placeholder for loading config from config/config.json
        # For now, using hardcoded CONFIG
        logger.info("Configuration loaded (using default for now).")

    def _ensure_directories(self):
        os.makedirs(os.path.dirname(CONFIG["vault_path"]), exist_ok=True)
        os.makedirs(os.path.dirname(CONFIG["salt_file"]), exist_ok=True)
        os.makedirs(os.path.dirname(CONFIG["log_file"]), exist_ok=True)
        logger.info("Ensured necessary directories exist.")

    def _load_or_generate_salt(self):
        if os.path.exists(CONFIG["salt_file"]):
            with open(CONFIG["salt_file"], "rb") as f:
                self._salt = f.read()
            logger.info("Loaded salt from file.")
        else:
            self._salt = os.urandom(16) # 16 bytes is standard for salt
            with open(CONFIG["salt_file"], "wb") as f:
                f.write(self._salt)
            os.chmod(CONFIG["salt_file"], 0o600) # Secure permissions
            logger.info("Generated new salt and saved with 0600 permissions.")

    def _derive_key(self, passphrase: str) -> bytes:
        if not self._salt:
            raise ValueError("Salt not loaded or generated.")
        kdf = Scrypt(
            salt=self._salt,
            length=CONFIG["kdf_length"],
            n=CONFIG["kdf_n"],
            r=CONFIG["kdf_r"],
            p=CONFIG["kdf_p"],
            backend=default_backend()
        )
        key = kdf.derive(passphrase.encode('utf-8'))
        logger.info("Encryption key derived.")
        return key

    def unlock_vault(self, passphrase: str) -> bool:
        try:
            self._encryption_key = self._derive_key(passphrase)
            logger.info("Vault unlocked successfully.")
            return True
        except Exception as e:
            self._encryption_key = None
            logger.error(f"Failed to unlock vault: {e}")
            return False

    def lock_vault(self):
        if self._encryption_key:
            # Securely clear key from memory
            self._encryption_key = None
            # In a real scenario, more thorough memory clearing might be needed
            # e.g., using a library that zeroes out memory.
        logger.info("Vault locked. Encryption key purged from memory.")

    def _encrypt(self, plaintext: bytes) -> bytes:
        if not self._encryption_key:
            raise PermissionError("Vault is locked. Cannot encrypt.")

        iv = os.urandom(16) # AES block size
        cipher = Cipher(algorithms.AES(self._encryption_key), modes.GCM(iv), backend=default_backend())
        encryptor = cipher.encryptor()
        ciphertext = encryptor.update(plaintext) + encryptor.finalize()
        tag = encryptor.tag
        return iv + tag + ciphertext # Store IV, Tag, and Ciphertext together

    def _decrypt(self, encrypted_data: bytes) -> bytes:
        if not self._encryption_key:
            raise PermissionError("Vault is locked. Cannot decrypt.")

        iv = encrypted_data[:16]
        tag = encrypted_data[16:32]
        ciphertext = encrypted_data[32:]

        cipher = Cipher(algorithms.AES(self._encryption_key), modes.GCM(iv, tag), backend=default_backend())
        decryptor = cipher.decryptor()
        plaintext = decryptor.update(ciphertext) + decryptor.finalize()
        return plaintext

    def store_memory(self, memory_id: str, data: str) -> bool:
        if not self._encryption_key:
            logger.warning(f"Attempt to store memory '{memory_id}' while vault is locked.")
            return False
        try:
            encrypted_data = self._encrypt(data.encode('utf-8'))
            vault_file_path = os.path.join(os.path.dirname(CONFIG["vault_path"]), f"{memory_id}.enc")
            with open(vault_file_path, "wb") as f:
                f.write(encrypted_data)
            os.chmod(vault_file_path, 0o600)
            logger.info(f"Memory '{memory_id}' stored securely.")
            return True
        except Exception as e:
            logger.error(f"Error storing memory '{memory_id}': {e}")
            return False

    def retrieve_memory(self, memory_id: str) -> str | None:
        if not self._encryption_key:
            logger.warning(f"Attempt to retrieve memory '{memory_id}' while vault is locked.")
            return None
        try:
            vault_file_path = os.path.join(os.path.dirname(CONFIG["vault_path"]), f"{memory_id}.enc")
            if not os.path.exists(vault_file_path):
                logger.warning(f"Memory '{memory_id}' not found.")
                return None
            with open(vault_file_path, "rb") as f:
                encrypted_data = f.read()
            decrypted_data = self._decrypt(encrypted_data)
            logger.info(f"Memory '{memory_id}' retrieved and decrypted.")
            return decrypted_data.decode('utf-8')
        except Exception as e:
            logger.error(f"Error retrieving memory '{memory_id}': {e}")
            return None

    def __del__(self):
        self.lock_vault() # Ensure key is purged on object destruction

# --- Daemon / CLI Example (Illustrative) ---
if __name__ == "__main__":
    manager = MemoryStorageManager()

    # In a real daemon, passphrase would be provided securely, e.g., via stdin or environment variable
    # For demonstration, prompting here.
    passphrase = input("Enter master passphrase to unlock vault: ")
    if not manager.unlock_vault(passphrase):
        print("Incorrect passphrase or error unlocking vault. Exiting.")
        exit(1)

    # Example usage
    print("\n--- Storing Memory ---")
    if manager.store_memory("user_preference_theme", "dark_mode"):
        print("Stored 'user_preference_theme'.")
    if manager.store_memory("last_activity_summary_2024-03-01", "Worked on Observational Memory system design and setup."):
        print("Stored 'last_activity_summary_2024-03-01'.")

    print("\n--- Retrieving Memory ---")
    retrieved_theme = manager.retrieve_memory("user_preference_theme")
    if retrieved_theme:
        print(f"Retrieved 'user_preference_theme': {retrieved_theme}")
    else:
        print("Failed to retrieve 'user_preference_theme'.")

    retrieved_activity = manager.retrieve_memory("last_activity_summary_2024-03-01")
    if retrieved_activity:
        print(f"Retrieved 'last_activity_summary_2024-03-01': {retrieved_activity}")
    else:
        print("Failed to retrieve 'last_activity_summary_2024-03-01'.")

    print("\n--- Attempting to retrieve non-existent memory ---")
    non_existent = manager.retrieve_memory("non_existent_memory")
    if not non_existent:
        print("Correctly failed to retrieve 'non_existent_memory'.")

    print("\n--- Locking Vault and attempting operations ---")
    manager.lock_vault()

    if not manager.store_memory("should_fail_memory", "this should not be stored"):
        print("Correctly failed to store 'should_fail_memory' (vault locked).")

    if not manager.retrieve_memory("user_preference_theme"):
        print("Correctly failed to retrieve 'user_preference_theme' (vault locked).")

    print("\n--- Cleaning up example files ---")
    vault_dir = os.path.dirname(os.path.abspath(CONFIG["vault_path"]))
    for f_name in ["user_preference_theme.enc", "last_activity_summary_2024-03-01.enc"]:
        f_path = os.path.join(vault_dir, f_name)
        if os.path.exists(f_path):
            os.remove(f_path)
            print(f"Removed {f_name}")

    # Remove salt file (for clean re-run of example)
    if os.path.exists(CONFIG["salt_file"]):
        os.remove(CONFIG["salt_file"])
        print(f"Removed {os.path.basename(CONFIG['salt_file'])}")

    print("\nDemonstration complete.")
