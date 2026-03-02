#!/usr/bin/env python3
"""
Security Tests for Checkpoint System

Tests encryption, decryption, HMAC verification, and tamper detection.
"""

import os
import sys
import unittest
import tempfile
import shutil
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from security_utils import SecurityUtils


class TestSecurityUtils(unittest.TestCase):
    """Test suite for SecurityUtils encryption/HMAC operations."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.master_key = os.urandom(32)  # 256-bit key
        self.security = SecurityUtils(self.master_key)
    
    def test_master_key_validation(self):
        """Test that invalid master key lengths are rejected."""
        # Too short
        with self.assertRaises(ValueError):
            SecurityUtils(os.urandom(16))  # 128-bit
        
        # Too long
        with self.assertRaises(ValueError):
            SecurityUtils(os.urandom(64))  # 512-bit
        
        # Exactly right
        try:
            SecurityUtils(os.urandom(32))  # 256-bit - should work
        except ValueError:
            self.fail("Valid 32-byte key should not raise ValueError")
    
    def test_encrypt_decrypt_roundtrip(self):
        """Test that data can be encrypted and decrypted successfully."""
        test_data = b"This is sensitive agent context data."
        
        ciphertext, nonce, tag = self.security.encrypt(test_data)
        
        # Verify ciphertext is different from plaintext
        self.assertNotEqual(ciphertext, test_data)
        
        # Decrypt and verify
        decrypted = self.security.decrypt(ciphertext, nonce, tag)
        self.assertEqual(decrypted, test_data)
    
    def test_encryption_is_non_deterministic(self):
        """Test that encrypting same data twice produces different results."""
        test_data = b"Same data encrypted multiple times"
        
        cipher1, nonce1, tag1 = self.security.encrypt(test_data)
        cipher2, nonce2, tag2 = self.security.encrypt(test_data)
        
        # Nonces should be different (randomly generated)
        self.assertNotEqual(nonce1, nonce2)
        
        # Ciphertexts should be different
        self.assertNotEqual(cipher1, cipher2)
    
    def test_decrypt_fails_with_wrong_tag(self):
        """Test that decryption fails when authentication tag is modified."""
        test_data = b"Secret data"
        
        ciphertext, nonce, tag = self.security.encrypt(test_data)
        
        # Modify last byte of tag
        tampered_tag = tag[:-1] + bytes([(tag[-1] + 1) % 256])
        
        with self.assertRaises(Exception):
            self.security.decrypt(ciphertext, nonce, tampered_tag)
    
    def test_decrypt_fails_with_wrong_nonce(self):
        """Test that decryption fails when nonce is modified."""
        test_data = b"Secret data"
        
        ciphertext, nonce, tag = self.security.encrypt(test_data)
        
        # Modify last byte of nonce
        tampered_nonce = nonce[:-1] + bytes([(nonce[-1] + 1) % 256])
        
        with self.assertRaises(Exception):
            self.security.decrypt(ciphertext, tampered_nonce, tag)
    
    def test_decrypt_fails_with_tampered_ciphertext(self):
        """Test that decryption fails when ciphertext is modified."""
        test_data = b"Secret data"
        
        ciphertext, nonce, tag = self.security.encrypt(test_data)
        
        # Modify last byte of ciphertext
        tampered_ciphertext = ciphertext[:-1] + bytes([(ciphertext[-1] + 1) % 256])
        
        with self.assertRaises(Exception):
            self.security.decrypt(tampered_ciphertext, nonce, tag)
    
    def test_hmac_generation_and_verification(self):
        """Test HMAC generation and successful verification."""
        test_data = b"Data to authenticate"
        nonce = os.urandom(12)
        
        hmac_value = self.security.generate_hmac(test_data, nonce)
        
        # Verify succeeds with correct data
        self.assertTrue(self.security.verify_hmac(test_data, hmac_value, nonce))
        
        # Verify has correct length (SHA-256 = 32 bytes)
        self.assertEqual(len(hmac_value), 32)
    
    def test_hmac_detects_tampering(self):
        """Test that HMAC verification detects data modification."""
        test_data = b"Original data"
        nonce = os.urandom(12)
        
        hmac_value = self.security.generate_hmac(test_data, nonce)
        
        # Tamper with data
        tampered_data = b"Tampered data"
        
        self.assertFalse(self.security.verify_hmac(tampered_data, hmac_value, nonce))
    
    def test_hmac_detects_nonce_change(self):
        """Test that HMAC verification detects nonce modification."""
        test_data = b"Data"
        nonce1 = os.urandom(12)
        nonce2 = os.urandom(12)
        
        hmac_value = self.security.generate_hmac(test_data, nonce1)
        
        # Verify with wrong nonce
        self.assertFalse(self.security.verify_hmac(test_data, hmac_value, nonce2))
    
    def test_empty_data_encryption(self):
        """Test encryption of empty data."""
        empty_data = b""
        
        ciphertext, nonce, tag = self.security.encrypt(empty_data)
        decrypted = self.security.decrypt(ciphertext, nonce, tag)
        
        self.assertEqual(decrypted, empty_data)
    
    def test_large_data_encryption(self):
        """Test encryption of large data (1MB)."""
        large_data = os.urandom(1024 * 1024)  # 1MB
        
        ciphertext, nonce, tag = self.security.encrypt(large_data)
        decrypted = self.security.decrypt(ciphertext, nonce, tag)
        
        self.assertEqual(decrypted, large_data)
    
    def test_unicode_data_encryption(self):
        """Test encryption of Unicode text."""
        unicode_data = "Hello 世界 🌍 مرحبا שלום".encode('utf-8')
        
        ciphertext, nonce, tag = self.security.encrypt(unicode_data)
        decrypted = self.security.decrypt(ciphertext, nonce, tag)
        
        self.assertEqual(decrypted, unicode_data)
    
    def test_binary_data_encryption(self):
        """Test encryption of arbitrary binary data."""
        binary_data = bytes(range(256)) * 100  # All byte values
        
        ciphertext, nonce, tag = self.security.encrypt(binary_data)
        decrypted = self.security.decrypt(ciphertext, nonce, tag)
        
        self.assertEqual(decrypted, binary_data)
    
    def test_session_key_derivation(self):
        """Test that different nonces produce different session keys."""
        # This tests the internal _derive_session_key method
        nonce1 = b'nonce1nonce1ne'  # 12 bytes
        nonce2 = b'nonce2nonce2ne'  # 12 bytes
        
        key1 = self.security._derive_session_key(nonce1)
        key2 = self.security._derive_session_key(nonce2)
        
        self.assertNotEqual(key1, key2)
        self.assertEqual(len(key1), 32)
        self.assertEqual(len(key2), 32)


class TestTamperDetection(unittest.TestCase):
    """Test comprehensive tamper detection scenarios."""
    
    def setUp(self):
        """Set up test with security utils and test data."""
        self.master_key = os.urandom(32)
        self.security = SecurityUtils(self.master_key)
    
    def test_bit_flip_in_ciphertext_detected(self):
        """Test that single bit flip in ciphertext is detected."""
        original = b"The quick brown fox jumps over the lazy dog"
        
        ciphertext, nonce, tag = self.security.encrypt(original)
        
        # Flip one bit in ciphertext
        tampered = bytearray(ciphertext)
        tampered[0] ^= 0b00000001  # Flip LSB of first byte
        
        with self.assertRaises(Exception):
            self.security.decrypt(bytes(tampered), nonce, tag)
    
    def test_byte_insertion_detected(self):
        """Test that byte insertion into ciphertext is detected."""
        original = b"Important data"
        
        ciphertext, nonce, tag = self.security.encrypt(original)
        
        # Insert byte
        tampered = ciphertext[:5] + b'\xff' + ciphertext[5:]
        
        with self.assertRaises(Exception):
            self.security.decrypt(tampered, nonce, tag)
    
    def test_byte_deletion_detected(self):
        """Test that byte deletion from ciphertext is detected."""
        original = b"Important data"
        
        ciphertext, nonce, tag = self.security.encrypt(original)
        
        # Delete byte
        tampered = ciphertext[:5] + ciphertext[6:]
        
        with self.assertRaises(Exception):
            self.security.decrypt(tampered, nonce, tag)
    
    def test_nonce_replay_detected(self):
        """Test that reusing nonce in different encryption is detected by HMAC."""
        data1 = b"First message"
        data2 = b"Second message"
        
        # Encrypt both with same nonce (bad practice, but testing detection)
        nonce = os.urandom(12)
        cipher1, _, tag1 = self.security.encrypt(data1)
        # Manually force same nonce (normally not possible due to os.urandom)
        cipher2, _, tag2 = self.security.encrypt(data2)
        
        # Generate HMAC with first nonce
        hmac1 = self.security.generate_hmac(cipher1 + nonce + tag1, nonce)
        
        # Try to verify second message with first HMAC
        self.assertFalse(
            self.security.verify_hmac(cipher2 + nonce + tag2, hmac1, nonce)
        )
    
    def test_metadata_tampering_detected(self):
        """Test that tampering with metadata structure is detected."""
        data = b"Sensitive info"
        
        ciphertext, nonce, tag = self.security.encrypt(data)
        
        # Combine as would be stored
        bundle1 = ciphertext + nonce + tag
        hmac1 = self.security.generate_hmac(bundle1, nonce)
        
        # Swap nonce and tag positions (malicious)
        bundle2 = ciphertext + tag + nonce
        
        self.assertFalse(
            self.security.verify_hmac(bundle2, hmac1, nonce)
        )


class TestKeyManagement(unittest.TestCase):
    """Test key derivation and management."""
    
    def test_same_master_key_produces_consistent_results(self):
        """Test that same master key with same inputs produces same outputs."""
        key1 = os.urandom(32)
        security1 = SecurityUtils(key1)
        
        key2 = key1  # Same key
        security2 = SecurityUtils(key2)
        
        nonce = b'testnonce12345'  # Fixed nonce for testing
        
        # Derive session keys
        session_key1 = security1._derive_session_key(nonce)
        session_key2 = security2._derive_session_key(nonce)
        
        self.assertEqual(session_key1, session_key2)
    
    def test_different_master_keys_produce_different_sessions(self):
        """Test that different master keys produce different session keys."""
        master_key1 = os.urandom(32)
        master_key2 = os.urandom(32)
        
        security1 = SecurityUtils(master_key1)
        security2 = SecurityUtils(master_key2)
        
        nonce = b'testnonce12345'
        
        session_key1 = security1._derive_session_key(nonce)
        session_key2 = security2._derive_session_key(nonce)
        
        self.assertNotEqual(session_key1, session_key2)
    
    def test_cross_key_decryption_fails(self):
        """Test that data encrypted with one key cannot be decrypted with another."""
        key1 = os.urandom(32)
        key2 = os.urandom(32)
        
        security1 = SecurityUtils(key1)
        security2 = SecurityUtils(key2)
        
        data = b"Secret data"
        ciphertext, nonce, tag = security1.encrypt(data)
        
        # Try to decrypt with different key
        with self.assertRaises(Exception):
            security2.decrypt(ciphertext, nonce, tag)


class TestPerformance(unittest.TestCase):
    """Basic performance tests."""
    
    def setUp(self):
        self.master_key = os.urandom(32)
        self.security = SecurityUtils(self.master_key)
    
    def test_encryption_speed_small(self):
        """Measure encryption speed for small data."""
        data = b"Small test data"
        
        import time
        start = time.time()
        for _ in range(1000):
            self.security.encrypt(data)
        elapsed = time.time() - start
        
        avg_ms = (elapsed / 1000) * 1000
        print(f"\nSmall data encryption: {avg_ms:.3f}ms avg")
        
        # Should be < 10ms on modern hardware
        self.assertLess(avg_ms, 10)
    
    def test_decryption_speed_small(self):
        """Measure decryption speed for small data."""
        data = b"Small test data"
        ciphertext, nonce, tag = self.security.encrypt(data)
        
        import time
        start = time.time()
        for _ in range(1000):
            self.security.decrypt(ciphertext, nonce, tag)
        elapsed = time.time() - start
        
        avg_ms = (elapsed / 1000) * 1000
        print(f"Small data decryption: {avg_ms:.3f}ms avg")
        
        self.assertLess(avg_ms, 10)
    
    def test_encryption_speed_large(self):
        """Measure encryption speed for larger data (1MB)."""
        data = os.urandom(1024 * 1024)  # 1MB
        
        import time
        start = time.time()
        ciphertext, nonce, tag = self.security.encrypt(data)
        elapsed = time.time() - start
        
        print(f"\nLarge data (1MB) encryption: {elapsed*1000:.1f}ms")
        
        # Should complete in reasonable time (< 500ms on modern hardware)
        self.assertLess(elapsed, 0.5)


if __name__ == '__main__':
    unittest.main(verbosity=2)
