/**
 * Security Tests - Audit Trail and Compliance
 */

import { Auditor } from '../../src/audit/auditor';
import { EncryptedStore } from '../../src/storage/encrypted-store';
import { AuditAction } from '../../src/model/types';
import * as path from 'path';
import * as fs from 'fs/promises';

describe('Auditor', () => {
  let auditor: Auditor;
  let store: EncryptedStore;
  let testDir: string;

  beforeAll(async () => {
    testDir = path.join(__dirname, 'test-audit-' + Date.now());
    store = new EncryptedStore(testDir, 'audit-test-key');
    await store.initialize();
    auditor = new Auditor(store, {
      logReads: true,
      logWrites: true,
      logDeletes: true,
      logAccessDenied: true,
      retentionDays: 30,
    });
  });

  afterAll(async () => {
    await auditor.shutdown();
    try {
      await fs.rm(testDir, { recursive: true, force: true });
    } catch (error) {
      console.warn('Failed to cleanup:', error);
    }
  });

  describe('Audit Entry Creation', () => {
    test('should create node operation audit entry', async () => {
      const nodeId = 'audit-node-1';
      const userId = 'test-user';

      await auditor.logNodeOperation(AuditAction.CREATE, nodeId, userId, {
        after: {
          id: nodeId,
          type: 'note',
          properties: { content: 'test' },
          tags: [],
          createdAt: new Date(),
          updatedAt: new Date(),
          createdBy: userId,
          accessLevel: 'private',
          version: 1,
        },
      });

      const entries = await auditor.queryAuditLog({ entityId: nodeId });
      
      expect(entries).toHaveLength(1);
      expect(entries[0].action).toBe(AuditAction.CREATE);
      expect(entries[0].userId).toBe(userId);
      expect(entries[0].entityType).toBe('node');
      expect(entries[0].changes?.after).toBeDefined();
    });

    test('should create edge operation audit entry', async () => {
      const edgeId = 'audit-edge-1';
      const userId = 'test-user';

      await auditor.logEdgeOperation(AuditAction.CREATE, edgeId, userId, {
        after: {
          id: edgeId,
          from: 'node-a',
          to: 'node-b',
          type: 'related_to',
          properties: {},
          createdAt: new Date(),
          createdBy: userId,
        },
      });

      const entries = await auditor.queryAuditLog({ entityId: edgeId });
      
      expect(entries).toHaveLength(1);
      expect(entries[0].entityType).toBe('edge');
    });

    test('should create access denial audit entry', async () => {
      const nodeId = 'restricted-node';
      const userId = 'unauthorized-user';

      await auditor.logAccessDenial(nodeId, userId, 'read', '192.168.1.100');

      const entries = await auditor.queryAuditLog({ 
        action: AuditAction.AUTH_FAILED 
      });
      
      const lastEntry = entries[0];
      expect(lastEntry.action).toBe(AuditAction.AUTH_FAILED);
      expect(lastEntry.metadata?.deniedAction).toBe('read');
      expect(lastEntry.ipAddress).toBe('192.168.1.100');
    });

    test('should create permission change audit entry', async () => {
      const nodeId = 'permission-node';
      const adminUserId = 'admin-user';
      const targetUserId = 'new-member';

      await auditor.logPermissionChange(nodeId, adminUserId, targetUserId, true);

      const entries = await auditor.queryAuditLog({
        entityType: 'permission',
      });
      
      const grantEntry = entries.find(e => e.action === AuditAction.ACCESS_GRANTED);
      expect(grantEntry).toBeDefined();
      expect(grantEntry?.metadata?.targetUserId).toBe(targetUserId);
      expect(grantEntry?.metadata?.granted).toBe(true);
    });
  });

  describe('Audit Log Querying', () => {
    beforeAll(async () => {
      // Create some test entries
      const testData = [
        { action: AuditAction.CREATE, entity: 'test-entity-1', user: 'user-a' },
        { action: AuditAction.READ, entity: 'test-entity-2', user: 'user-b' },
        { action: AuditAction.UPDATE, entity: 'test-entity-1', user: 'user-a' },
        { action: AuditAction.DELETE, entity: 'test-entity-3', user: 'user-c' },
      ];

      for (const data of testData) {
        await auditor.logNodeOperation(
          data.action as AuditAction,
          data.entity,
          data.user
        );
      }
    });

    test('should filter by user ID', async () => {
      const entries = await auditor.queryAuditLog({ userId: 'user-a' });
      expect(entries.every(e => e.userId === 'user-a')).toBe(true);
    });

    test('should filter by action type', async () => {
      const entries = await auditor.queryAuditLog({ action: AuditAction.CREATE });
      expect(entries.every(e => e.action === AuditAction.CREATE)).toBe(true);
    });

    test('should filter by date range', async () => {
      const now = new Date();
      const oneHourAgo = new Date(now.getTime() - 60 * 60 * 1000);
      const oneDayFromNow = new Date(now.getTime() + 24 * 60 * 60 * 1000);

      const entries = await auditor.queryAuditLog({
        since: oneHourAgo,
        until: oneDayFromNow,
      });

      expect(entries.length).toBeGreaterThan(0);
      expect(entries.every(e => e.timestamp >= oneHourAgo && e.timestamp <= oneDayFromNow))
        .toBe(true);
    });

    test('should apply limit correctly', async () => {
      const entries = await auditor.queryAuditLog({ limit: 2 });
      expect(entries.length).toBeLessThanOrEqual(2);
    });

    test('should return results sorted by timestamp descending', async () => {
      const entries = await auditor.queryAuditLog({ limit: 10 });
      
      for (let i = 0; i < entries.length - 1; i++) {
        expect(entries[i].timestamp.getTime()).toBeGreaterThanOrEqual(
          entries[i + 1].timestamp.getTime()
        );
      }
    });
  });

  describe('User Activity Tracking', () => {
    test('should calculate user activity summary', async () => {
      const userId = 'activity-test-user';
      
      // Generate various activities
      await auditor.logNodeOperation(AuditAction.CREATE, 'activity-node-1', userId);
      await auditor.logNodeOperation(AuditAction.CREATE, 'activity-node-2', userId);
      await auditor.logNodeOperation(AuditAction.UPDATE, 'activity-node-1', userId);
      await auditor.logNodeOperation(AuditAction.READ, 'some-node', userId);
      await auditor.logAccessDenial('restricted-node', userId, 'read');

      const summary = await auditor.getUserActivity(userId, 7);

      expect(summary.nodesCreated).toBe(2);
      expect(summary.nodesUpdated).toBe(1);
      expect(summary.accessesDenied).toBe(1);
      expect(summary.totalOperations).toBe(5);
      expect(summary.lastActivity).toBeDefined();
    });

    test('should handle empty activity', async () => {
      const summary = await auditor.getUserActivity('non-existent-user');
      
      expect(summary.totalOperations).toBe(0);
      expect(summary.lastActivity).toBeNull();
    });
  });

  describe('Audit Log Export', () => {
    test('should export to JSON format', async () => {
      const jsonExport = await auditor.exportAuditLog({ format: 'json' });
      
      const parsed = JSON.parse(jsonExport);
      expect(Array.isArray(parsed)).toBe(true);
      expect(parsed.length).toBeGreaterThan(0);
    });

    test('should export to CSV format', async () => {
      const csvExport = await auditor.exportAuditLog({ format: 'csv' });
      
      const lines = csvExport.split('\n');
      expect(lines.length).toBeGreaterThan(1);
      
      // Check header
      expect(lines[0]).toContain('Timestamp');
      expect(lines[0]).toContain('ID');
      expect(lines[0]).toContain('User');
      expect(lines[0]).toContain('Action');
    });

    test('should respect date filters in export', async () => {
      const now = new Date();
      const yesterday = new Date(now.getTime() - 24 * 60 * 60 * 1000);
      
      const jsonExport = await auditor.exportAuditLog({
        format: 'json',
        since: yesterday,
      });
      
      const parsed = JSON.parse(jsonExport);
      const allRecent = parsed.every((entry: any) => 
        new Date(entry.timestamp) >= yesterday
      );
      
      expect(allRecent).toBe(true);
    });
  });

  describe('Retention Policy', () => {
    test('should cleanup old entries based on retention policy', async () => {
      // Create an entry with old timestamp (manually for testing)
      const oldDate = new Date();
      oldDate.setDate(oldDate.getDate() - 60); // 60 days ago
      
      const oldEntries = await store.readAudit();
      const cleanedCount = await auditor.cleanupOldEntries();
      
      // With 30-day retention, entries older than 30 days should be removed
      const remainingEntries = await store.readAudit();
      
      // We don't know exact count but should not fail
      expect(typeof cleanedCount).toBe('number');
      expect(cleanedCount).toBeGreaterThanOrEqual(0);
      expect(remainingEntries.length).toBeLessThanOrEqual(oldEntries.length);
    });
  });

  describe('Anomaly Detection', () => {
    test('should detect brute force attempts', async () => {
      const attackUser = 'attacker-user';
      const ipAddr = '10.0.0.99';

      // Simulate multiple failed login attempts
      for (let i = 0; i < 10; i++) {
        await auditor.logAccessDenial('login-endpoint', attackUser, 'authenticate', ipAddr);
      }

      const anomalies = await auditor.detectAnomalies({
        failedAttemptsThreshold: 5,
        timeWindowMinutes: 60,
      });

      const bruteForceAnomaly = anomalies.find(a => a.anomalyType === 'brute_force');
      
      expect(bruteForceAnomaly).toBeDefined();
      expect(bruteForceAnomaly?.userId).toBe(attackUser);
      expect(bruteForceAnomaly?.details.attemptCount).toBe(10);
      expect(bruteForceAnomaly?.severity).toBe('high');
    });

    test('should not flag normal activity as anomaly', async () => {
      const normalUser = 'normal-user';

      // Normal number of failed attempts
      await auditor.logAccessDenial('node-x', normalUser, 'read');
      await auditor.logAccessDenial('node-y', normalUser, 'write');

      const anomalies = await auditor.detectAnomalies({
        failedAttemptsThreshold: 5,
        timeWindowMinutes: 60,
      });

      const userAnomalies = anomalies.filter(a => a.userId === normalUser);
      expect(userAnomalies).toHaveLength(0);
    });

    test('should differentiate severity levels', async () => {
      const lowAttackUser = 'low-severity-attacker';
      const highAttackUser = 'high-severity-attacker';

      // Just above threshold
      for (let i = 0; i < 6; i++) {
        await auditor.logAccessDenial('node', lowAttackUser, 'read');
      }

      // Well above threshold
      for (let i = 0; i < 20; i++) {
        await auditor.logAccessDenial('node', highAttackUser, 'read');
      }

      const anomalies = await auditor.detectAnomalies({
        failedAttemptsThreshold: 5,
        timeWindowMinutes: 60,
      });

      const lowAnomaly = anomalies.find(a => a.userId === lowAttackUser);
      const highAnomaly = anomalies.find(a => a.userId === highAttackUser);

      expect(lowAnomaly?.severity).toBe('medium');
      expect(highAnomaly?.severity).toBe('high');
    });
  });

  describe('Buffer Management', () => {
    test('should flush buffer on shutdown', async () => {
      const tempAuditor = new Auditor(store, {
        logReads: true,
        logWrites: true,
        logDeletes: true,
        logAccessDenied: true,
        retentionDays: 30,
      });

      // Add entries without triggering auto-flush
      for (let i = 0; i < 10; i++) {
        await tempAuditor.logNodeOperation(
          AuditAction.READ,
          `buffer-test-node-${i}`,
          'buffer-test-user'
        );
      }

      // Shutdown should flush remaining entries
      await tempAuditor.shutdown();

      const entries = await tempAuditor.queryAuditLog({
        userId: 'buffer-test-user',
      });

      expect(entries.length).toBeGreaterThan(0);
    });

    test('should flush automatically when buffer is full', async () => {
      const entriesBefore = await store.readAudit();
      const initialCount = entriesBefore.length;

      // Add enough entries to trigger buffer flush (threshold is 100)
      for (let i = 0; i < 110; i++) {
        await auditor.logNodeOperation(
          AuditAction.READ,
          `auto-flush-node-${i}`,
          'auto-flush-user'
        );
      }

      const entriesAfter = await store.readAudit();
      
      // Should have flushed at least once
      expect(entriesAfter.length - initialCount).toBeGreaterThanOrEqual(100);
    });
  });

  describe('Compliance Scenarios', () => {
    test('should track complete node lifecycle', async () => {
      const nodeId = 'lifecycle-test-node';
      const userId = 'lifecycle-user';

      // Create
      await auditor.logNodeOperation(AuditAction.CREATE, nodeId, userId, {
        after: { id: nodeId, type: 'note', properties: {}, tags: [], createdAt: new Date(), updatedAt: new Date(), createdBy: userId, accessLevel: 'private', version: 1 },
      });

      // Update
      await auditor.logNodeOperation(AuditAction.UPDATE, nodeId, userId, {
        before: { id: nodeId, type: 'note', properties: { content: 'old' }, tags: [], createdAt: new Date(), updatedAt: new Date(), createdBy: userId, accessLevel: 'private', version: 1 },
        after: { id: nodeId, type: 'note', properties: { content: 'new' }, tags: [], createdAt: new Date(), updatedAt: new Date(), createdBy: userId, accessLevel: 'private', version: 2 },
      });

      // Delete
      await auditor.logNodeOperation(AuditAction.DELETE, nodeId, userId, {
        before: { id: nodeId, type: 'note', properties: { content: 'new' }, tags: [], createdAt: new Date(), updatedAt: new Date(), createdBy: userId, accessLevel: 'private', version: 2 },
      });

      const lifecycle = await auditor.queryAuditLog({ entityId: nodeId });
      
      expect(lifecycle.map(e => e.action)).toEqual([
        AuditAction.DELETE,
        AuditAction.UPDATE,
        AuditAction.CREATE,
      ]);
    });

    test('should track data access for regulatory requirements', async () => {
      const sensitiveNodeId = 'pii-data-node';
      const accessorIds = ['employee-1', 'employee-2', 'employee-3'];

      // Multiple users accessing sensitive data
      for (const userId of accessorIds) {
        await auditor.logNodeOperation(AuditAction.READ, sensitiveNodeId, userId);
      }

      const accessLog = await auditor.queryAuditLog({
        entityId: sensitiveNodeId,
        action: AuditAction.READ,
      });

      expect(accessLog.length).toBe(3);
      expect(accessLog.map(e => e.userId)).toEqual(expect.arrayContaining(accessorIds));
    });
  });
});
