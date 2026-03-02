
import os
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes, hmac

class SecurityUtils:
    def __init__(self, master_key: bytes):
        if len(master_key) != 32:
            raise ValueError("Master key must be 32 bytes for AES-256.")
        self.master_key = master_key

    def _derive_session_key(self, nonce: bytes) -> bytes:
        """Derives a session-specific key using HKDF-SHA256."""
        # For simplicity, we'll use a basic KDF here. In a real system, use HKDF.
        # For this PoC, we'll just XOR the master key with a padded nonce for demonstration.
        # This is NOT cryptographically secure for key derivation in production.
        # A proper KDF like HKDF-SHA256 should be used.
        padded_nonce = (nonce * (32 // len(nonce) + 1))[:32]
        return bytes(mk ^ pn for mk, pn in zip(self.master_key, padded_nonce))

    def encrypt(self, data: bytes) -> tuple[bytes, bytes, bytes]:
        """Encrypts data using AES-256 GCM and returns ciphertext, nonce, and tag."""
        nonce = os.urandom(12)  # GCM recommended nonce size is 12 bytes
        session_key = self._derive_session_key(nonce)
        cipher = Cipher(algorithms.AES(session_key), modes.GCM(nonce), backend=default_backend())
        encryptor = cipher.encryptor()
        ciphertext = encryptor.update(data) + encryptor.finalize()
        return ciphertext, nonce, encryptor.tag

    def decrypt(self, ciphertext: bytes, nonce: bytes, tag: bytes) -> bytes:
        """Decrypts data using AES-256 GCM given ciphertext, nonce, and tag."""
        session_key = self._derive_session_key(nonce)
        # Create cipher with tag for authenticated decryption
        cipher = Cipher(algorithms.AES(session_key), modes.GCM(nonce, tag), backend=default_backend())
        decryptor = cipher.decryptor()
        decryptor.authenticate_additional_data(b'') # No additional data for now
        plaintext = decryptor.update(ciphertext) + decryptor.finalize()
        return plaintext

    def generate_hmac(self, data: bytes, nonce: bytes) -> bytes:
        """Generates an HMAC-SHA256 for the given data."""
        session_key = self._derive_session_key(nonce)
        h = hmac.HMAC(session_key, hashes.SHA256(), backend=default_backend())
        h.update(data)
        return h.finalize()

    def verify_hmac(self, data: bytes, expected_hmac: bytes, nonce: bytes) -> bool:
        """Verifies an HMAC-SHA256 for the given data."""
        session_key = self._derive_session_key(nonce)
        h = hmac.HMAC(session_key, hashes.SHA256(), backend=default_backend())
        h.update(data)
        try:
            h.verify(expected_hmac)
            return True
        except Exception:
            return False

# Example usage (for testing)
if __name__ == "__main__":
    master_key = os.urandom(32)  # A random 32-byte master key
    security = SecurityUtils(master_key)

    original_data = b"This is some sensitive agent context data."

    # Encryption
    ciphertext, nonce, tag = security.encrypt(original_data)
    print(f"Original Data: {original_data}")
    print(f"Ciphertext: {ciphertext.hex()}")
    print(f"Nonce: {nonce.hex()}")
    print(f"Tag: {tag.hex()}")

    # HMAC generation for integrity
    data_to_hash = ciphertext + nonce + tag # Hash the entire encrypted bundle
    data_hmac = security.generate_hmac(data_to_hash, nonce)
    print(f"HMAC: {data_hmac.hex()}")

    # Decryption
    try:
        decrypted_data = security.decrypt(ciphertext, nonce, tag)
        print(f"Decrypted Data: {decrypted_data}")
        assert original_data == decrypted_data
        print("Decryption successful and matches original data.")
    except Exception as e:
        print(f"Decryption failed: {e}")

    # HMAC verification
    is_hmac_valid = security.verify_hmac(data_to_hash, data_hmac, nonce)
    print(f"HMAC valid: {is_hmac_valid}")

    # Test tampering
    print("\nTesting tampering...")
    tampered_ciphertext = ciphertext[:-1] + b'X' # Tamper with one byte
    tampered_data_to_hash = tampered_ciphertext + nonce + tag
    is_tampered_hmac_valid = security.verify_hmac(tampered_data_to_hash, data_hmac, nonce)
    print(f"HMAC valid after tampering (should be False): {is_tampered_hmac_valid}")

    try:
        security.decrypt(tampered_ciphertext, nonce, tag)
        print("Tampered decryption successful (should fail).")
    except Exception as e:
        print(f"Tampered decryption failed as expected: {e}")

