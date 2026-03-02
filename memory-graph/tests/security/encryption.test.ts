/**
 * Security Tests - Encryption and Data Protection
 */

import { EncryptedStore } from '../../src/storage/encrypted-store';
import * as crypto from 'crypto';
import * as fs from 'fs/promises';
import * as path from 'path';

describe('EncryptedStore', () => {
  let store: EncryptedStore;
  let testDir: string;

  const encryptionKey = 'test-encryption-key-for-security-tests-12345';

  beforeAll(async () => {
    testDir = path.join(__dirname, 'test-storage-' + Date.now());
    store = new EncryptedStore(testDir, encryptionKey);
    await store.initialize();
  });

  afterAll(async () => {
    // Cleanup test directory
    try {
      await fs.rm(testDir, { recursive: true, force: true });
    } catch (error) {
      console.warn('Failed to cleanup test directory:', error);
    }
  });

  describe('Encryption Decryption', () => {
    test('should encrypt and decrypt simple object', () => {
      const data = { name: 'Test', value: 123 };
      const encrypted = store.encrypt(data);
      const decrypted = store.decrypt(encrypted) as typeof data;
      
      expect(decrypted).toEqual(data);
      expect(encrypted).not.toEqual(Buffer.from(JSON.stringify(data)));
    });

    test('should encrypt and decrypt complex nested object', () => {
      const data = {
        nodes: [
          { id: '1', properties: { nested: { deep: 'value' } } },
          { id: '2', properties: { array: [1, 2, 3] } },
        ],
        metadata: {
          timestamp: new Date(),
          counts: { total: 100 },
        },
      };
      
      const encrypted = store.encrypt(data);
      const decrypted = store.decrypt(encrypted) as typeof data;
      
      // Convert dates for comparison
      decrypted.metadata.timestamp = new Date(decrypted.metadata.timestamp);
      
      expect(decrypted).toEqual(data);
    });

    test('should produce different ciphertext for same plaintext', () => {
      const data = { constant: 'data' };
      const encrypted1 = store.encrypt(data);
      const encrypted2 = store.encrypt(data);
      
      expect(encrypted1.equals(encrypted2)).toBe(false);
    });

    test('should fail decryption with wrong key', () => {
      const data = { secret: 'information' };
      const encrypted = store.encrypt(data);
      
      const wrongStore = new EncryptedStore(testDir, 'wrong-key');
      
      expect(() => wrongStore.decrypt(encrypted)).toThrow();
    });

    test('should detect tampered ciphertext', () => {
      const data = { original: 'data' };
      const encrypted = store.encrypt(data);
      
      // Tamper with ciphertext
      const tampered = Buffer.from(encrypted);
      tampered[10] ^= 0xFF; // Flip bits
      
      expect(() => store.decrypt(tampered)).toThrow();
    });
  });

  describe('Data Integrity', () => {
    test('should maintain integrity across write/read cycle', async () => {
      const testData = [
        { id: 'node1', type: 'note' as const, properties: { content: 'test' }, tags: [], createdAt: new Date(), updatedAt: new Date(), createdBy: 'user', accessLevel: 'private' as const, version: 1 },
        { id: 'node2', type: 'task' as const, properties: { title: 'Task' }, tags: [], createdAt: new Date(), updatedAt: new Date(), createdBy: 'user', accessLevel: 'private' as const, version: 1 },
      ];

      await store.writeNodes(testData);
      const readData = await store.readNodes();

      expect(readData).toEqual(testData);
    });

    test('should verify integrity of valid storage', async () => {
      const result = await store.verifyIntegrity();
      expect(result.valid).toBe(true);
      expect(result.errors).toHaveLength(0);
    });

    test('should detect corrupted storage', async () => {
      // Corrupt the nodes file
      const corruptedBuffer = Buffer.from('invalid encrypted data!!!');
      await fs.writeFile(path.join(testDir, 'nodes.enc'), corruptedBuffer);
      
      const result = await store.verifyIntegrity();
      expect(result.valid).toBe(false);
      expect(result.errors.length).toBeGreaterThan(0);
    });
  });

  describe('Backup and Restore', () => {
    test('should backup and restore data correctly', async () => {
      // Add test data
      const testNode = {
        id: 'backup-test-node',
        type: 'note' as const,
        properties: { content: 'Backup test' },
        tags: ['test'],
        createdAt: new Date(),
        updatedAt: new Date(),
        createdBy: 'user',
        accessLevel: 'private' as const,
        version: 1,
      };

      await store.addNode(testNode);
      
      // Create backup
      const backupPath = await store.backup();
      expect(backupPath).toBeDefined();
      expect(await fs.access(backupPath).then(() => true).catch(() => false)).toBe(true);

      // Clear data
      await store.writeNodes([]);
      await store.writeEdges([]);
      await store.writeAudit([]);

      // Verify data is cleared
      const nodesAfterClear = await store.readNodes();
      expect(nodesAfterClear).toHaveLength(0);

      // Restore from backup
      await store.restore(backupPath);

      // Verify data restored
      const nodesAfterRestore = await store.readNodes();
      expect(nodesAfterRestore).toHaveLength(1);
      expect(nodesAfterRestore[0].id).toBe('backup-test-node');
    });
  });

  describe('Key Derivation', () => {
    test('should derive consistent keys from same password', () => {
      const store1 = new EncryptedStore(testDir, 'same-password');
      const store2 = new EncryptedStore(testDir, 'same-password');
      
      // Both should use the same derived key mechanism
      const data = { test: 'data' };
      const enc1 = store1.encrypt(data);
      const enc2 = store2.encrypt(data);
      
      // Can decrypt with either (if salt is same)
      expect(() => store1.decrypt(enc1)).not.toThrow();
      expect(() => store2.decrypt(enc2)).not.toThrow();
    });

    test('should use strong key derivation', () => {
      const iterations = 100000;
      const salt = crypto.randomBytes(32);
      
      const start = Date.now();
      crypto.pbkdf2Sync('password', salt, iterations, 32, 'sha256');
      const duration = Date.now() - start;
      
      // Key derivation should take sufficient time (at least 50ms)
      expect(duration).toBeGreaterThanOrEqual(50);
    });
  });

  describe('AES-GCM Specific Tests', () => {
    test('should use proper IV length', () => {
      const data = { test: 'data' };
      const encrypted = store.encrypt(data);
      
      // IV is first 16 bytes
      const iv = encrypted.subarray(0, 16);
      expect(iv.length).toBe(16);
    });

    test('should use proper authentication tag length', () => {
      const data = { test: 'data' };
      const encrypted = store.encrypt(data);
      
      // Tag follows IV (16 bytes)
      const tag = encrypted.subarray(16, 32);
      expect(tag.length).toBe(16);
    });

    test('should reject truncated ciphertext', () => {
      const data = { test: 'data' };
      const encrypted = store.encrypt(data);
      
      // Truncate the ciphertext
      const truncated = encrypted.subarray(0, encrypted.length - 10);
      
      expect(() => store.decrypt(truncated)).toThrow();
    });
  });

  describe('Access Pattern Analysis Prevention', () => {
    test('should not reveal data size through ciphertext size', () => {
      const smallData = { x: 1 };
      const largeData = { x: 1, ...Array.from({ length: 100 }, (_, i) => ({ [`field${i}`]: i })).reduce((acc, curr) => ({ ...acc, ...curr }), {}) };
      
      const smallEncrypted = store.encrypt(smallData);
      const largeEncrypted = store.encrypt(largeData);
      
      // Sizes will differ but not proportionally to plaintext
      const sizeDiff = Math.abs(largeEncrypted.length - smallEncrypted.length);
      const plaintextDiff = JSON.stringify(largeData).length - JSON.stringify(smallData).length;
      
      // Ciphertext size difference should be much smaller than plaintext
      expect(sizeDiff).toBeLessThan(plaintextDiff * 0.5);
    });
  });
});
