
import unittest
import os
import shutil
import json
from unittest.mock import patch

from security_utils import SecurityUtils
from checkpoint_manager import CheckpointManager

class TestCheckpointSystem(unittest.TestCase):

    def setUp(self):
        self.master_key = os.urandom(32) # For testing, a random key
        self.security_utils = SecurityUtils(self.master_key)
        self.agent_id = "test_agent"
        self.checkpoint_base_dir = "./.test_checkpoints"
        self.manager = CheckpointManager(self.agent_id, self.checkpoint_base_dir, self.security_utils)
        
        # Ensure a clean slate for each test
        if os.path.exists(self.manager.checkpoint_base_dir):
            shutil.rmtree(self.manager.checkpoint_base_dir)
        os.makedirs(self.manager.checkpoint_base_dir)

    def tearDown(self):
        # Clean up after each test
        if os.path.exists(self.checkpoint_base_dir):
            shutil.rmtree(self.checkpoint_base_dir)

    # --- Test SecurityUtils ---
    def test_security_utils_encryption_decryption(self):
        original_data = b"My secret data."
        ciphertext, nonce, tag = self.security_utils.encrypt(original_data)
        decrypted_data = self.security_utils.decrypt(ciphertext, nonce, tag)
        self.assertEqual(original_data, decrypted_data)

    def test_security_utils_hmac_verification(self):
        data = b"Data for HMAC."
        nonce = os.urandom(12)
        hmac_value = self.security_utils.generate_hmac(data, nonce)
        self.assertTrue(self.security_utils.verify_hmac(data, hmac_value, nonce))

    def test_security_utils_hmac_tampering_detection(self):
        data = b"Data for HMAC."
        nonce = os.urandom(12)
        hmac_value = self.security_utils.generate_hmac(data, nonce)
        tampered_data = b"Tampered data."
        self.assertFalse(self.security_utils.verify_hmac(tampered_data, hmac_value, nonce))

    def test_security_utils_decrypt_tampered_ciphertext(self):
        original_data = b"Another secret."
        ciphertext, nonce, tag = self.security_utils.encrypt(original_data)
        tampered_ciphertext = ciphertext[:-1] + b'X'
        with self.assertRaises(Exception): # GCM decryption will fail on tampering
            self.security_utils.decrypt(tampered_ciphertext, nonce, tag)

    # --- Test CheckpointManager ---
    def test_checkpoint_manager_save_load(self):
        context = {"task": "write code", "step": 1}
        checkpoint_path = self.manager.save_checkpoint(context)
        self.assertTrue(os.path.exists(checkpoint_path))
        self.assertTrue(os.path.exists(self.manager._get_context_file_path(checkpoint_path)))
        self.assertTrue(os.path.exists(self.manager._get_integrity_file_path(checkpoint_path)))
        self.assertTrue(os.path.exists(self.manager._get_metadata_file_path(checkpoint_path)))

        loaded_context, loaded_path = self.manager.load_latest_checkpoint()
        self.assertIsNotNone(loaded_context)
        self.assertEqual(context, loaded_context)
        self.assertEqual(checkpoint_path, loaded_path)

    def test_checkpoint_manager_load_no_checkpoints(self):
        shutil.rmtree(self.checkpoint_base_dir) # Remove any setup checkpoints
        os.makedirs(self.checkpoint_base_dir)
        loaded_context, loaded_path = self.manager.load_latest_checkpoint()
        self.assertIsNone(loaded_context)
        self.assertIsNone(loaded_path)

    def test_checkpoint_manager_load_multiple_checkpoints(self):
        context1 = {"data": "first"}
        self.manager.save_checkpoint(context1)
        
        context2 = {"data": "second", "status": "in progress"}
        self.manager.save_checkpoint(context2)

        loaded_context, _ = self.manager.load_latest_checkpoint()
        self.assertEqual(context2, loaded_context) # Should load the latest
    
    def test_checkpoint_manager_tampered_checkpoint_skipped(self):
        context_good = {"data": "good context"}
        good_checkpoint_path = self.manager.save_checkpoint(context_good)

        context_bad = {"data": "bad context"}
        bad_checkpoint_path = self.manager.save_checkpoint(context_bad)

        # Tamper with the latest (bad) checkpoint's context file
        context_file_path = self.manager._get_context_file_path(bad_checkpoint_path)
        with open(context_file_path, 'rb+') as f:
            content = f.read()
            f.seek(0)
            f.write(content[:-1] + b'\x00') # Corrupt last byte

        # Attempt to load, should skip the bad one and load the good one
        loaded_context, loaded_path = self.manager.load_latest_checkpoint()
        self.assertEqual(context_good, loaded_context)
        self.assertEqual(good_checkpoint_path, loaded_path)
        self.assertNotEqual(bad_checkpoint_path, loaded_path)

    def test_checkpoint_manager_cleanup_old_checkpoints(self):
        for i in range(10):
            self.manager.save_checkpoint({"dummy": i})
        
        # Should have 10 checkpoints initially
        self.assertEqual(len(os.listdir(self.manager.checkpoint_base_dir)), 10)

        self.manager.cleanup_old_checkpoints(keep_count=5)
        self.assertEqual(len(os.listdir(self.manager.checkpoint_base_dir)), 5)
        
        # Verify that the latest 5 are kept
        all_checkpoints = sorted(os.listdir(self.manager.checkpoint_base_dir), reverse=True)
        latest_5_from_dir = all_checkpoints[:5]
        
        # Save 11th checkpoint
        self.manager.save_checkpoint({"dummy": 10})
        self.assertEqual(len(os.listdir(self.manager.checkpoint_base_dir)), 6) # 5 + new one
        self.manager.cleanup_old_checkpoints(keep_count=5)
        self.assertEqual(len(os.listdir(self.manager.checkpoint_base_dir)), 5)


if __name__ == '__main__':
    unittest.main()
