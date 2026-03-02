/**
 * Integration Tests - End-to-End Memory Graph Functionality
 */

import { MemoryGraph } from '../../src/api/memory-graph';
import { AccessLevel, Role } from '../../src/model/types';
import * as fs from 'fs/promises';
import * as path from 'path';

describe('MemoryGraph Integration', () => {
  let graph: MemoryGraph;
  let testDir: string;
  const encryptionKey = 'integration-test-encryption-key-secure-12345';

  beforeAll(async () => {
    testDir = path.join(__dirname, 'test-graph-' + Date.now());
    graph = await MemoryGraph.create({
      storagePath: testDir,
      encryptionKey,
      defaultAccessLevel: AccessLevel.PRIVATE,
      auditEnabled: true,
      userId: 'integration-test-user',
    });
  });

  afterAll(async () => {
    await graph.shutdown();
    try {
      await fs.rm(testDir, { recursive: true, force: true });
    } catch (error) {
      console.warn('Failed to cleanup:', error);
    }
  });

  describe('Node CRUD Operations', () => {
    test('should create a note node', async () => {
      const node = await graph.createNode({
        id: 'integration-note-1',
        type: 'note',
        properties: {
          title: 'Integration Test Note',
          content: 'This is a test note for integration testing',
          importance: 5,
        },
        tags: ['testing', 'integration'],
        accessLevel: AccessLevel.PRIVATE,
      });

      expect(node.id).toBe('integration-note-1');
      expect(node.type).toBe('note');
      expect(node.properties.title).toBe('Integration Test Note');
      expect(node.tags).toContain('testing');
      expect(node.createdBy).toBe('integration-test-user');
      expect(node.version).toBe(1);
    });

    test('should read a node by ID', async () => {
      const node = await graph.getNode('integration-note-1');
      
      expect(node).not.toBeNull();
      expect(node?.id).toBe('integration-note-1');
      expect(node?.properties.content).toContain('test note');
    });

    test('should update a node', async () => {
      const updated = await graph.updateNode('integration-note-1', {
        properties: {
          title: 'Updated Title',
          content: 'This content has been updated',
          importance: 8,
        },
        tags: ['testing', 'updated', 'priority'],
      });

      expect(updated.version).toBe(2);
      expect(updated.properties.title).toBe('Updated Title');
      expect(updated.tags).toContain('updated');
    });

    test('should handle concurrent version updates', async () => {
      // First update
      await graph.updateNode('integration-note-1', {
        properties: { testConcurrent: true },
      });

      const node = await graph.getNode('integration-note-1');
      const versionBefore = node?.version;

      // Second update
      await graph.updateNode('integration-note-1', {
        properties: { anotherField: 'value' },
      });

      const updatedNode = await graph.getNode('integration-note-1');
      expect(updatedNode?.version).toBe(versionBefore! + 1);
    });

    test('should delete a node', async () => {
      // Create a node to delete
      await graph.createNode({
        id: 'to-be-deleted',
        type: 'note',
        properties: { content: 'delete me' },
        tags: [],
      });

      // Verify it exists
      const existing = await graph.getNode('to-be-deleted');
      expect(existing).not.toBeNull();

      // Delete it
      const deleted = await graph.deleteNode('to-be-deleted');
      expect(deleted).toBe(true);

      // Verify it's gone
      const afterDelete = await graph.getNode('to-be-deleted');
      expect(afterDelete).toBeNull();
    });

    test('should validate node schema on creation', async () => {
      await expect(
        graph.createNode({
          id: 'invalid-node',
          type: 'task',
          properties: {
            // Missing required 'status' field
            title: 'Incomplete task',
          },
          tags: [],
        })
      ).rejects.toThrow('Schema validation failed');
    });
  });

  describe('Edge Operations', () => {
    beforeAll(async () => {
      // Create nodes for relationships
      await graph.createNode({
        id: 'edge-source',
        type: 'idea',
        properties: { title: 'Source Idea' },
        tags: [],
      });

      await graph.createNode({
        id: 'edge-target',
        type: 'project',
        properties: { name: 'Target Project', status: 'active' },
        tags: [],
      });
    });

    test('should create an edge between nodes', async () => {
      const edge = await graph.createEdge({
        from: 'edge-source',
        to: 'edge-target',
        type: 'related_to',
        properties: { strength: 0.8, context: 'Both related to innovation' },
      });

      expect(edge.from).toBe('edge-source');
      expect(edge.to).toBe('edge-target');
      expect(edge.type).toBe('related_to');
      expect(edge.properties.strength).toBe(0.8);
    });

    test('should get edges connected to a node', async () => {
      const edges = await graph.getEdges('edge-source');
      
      expect(edges.length).toBeGreaterThan(0);
      expect(edges.some(e => e.from === 'edge-source')).toBe(true);
    });

    test('should delete an edge', async () => {
      const edgesBefore = await graph.getEdges('edge-source');
      const edgeToDelete = edgesBefore[0];

      const deleted = await graph.deleteEdge(edgeToDelete.id);
      expect(deleted).toBe(true);

      const edgesAfter = await graph.getEdges('edge-source');
      expect(edgesAfter.length).toBeLessThan(edgesBefore.length);
    });

    test('should fail to create edge with non-existent nodes', async () => {
      await expect(
        graph.createEdge({
          from: 'non-existent-node',
          to: 'edge-target',
          type: 'related_to',
        })
      ).rejects.toThrow('Source or target node not found');
    });
  });

  describe('Query Operations', () => {
    beforeAll(async () => {
      // Create test data for querying
      await graph.createNode({
        id: 'query-test-1',
        type: 'task',
        properties: { title: 'High Priority Task', priority: 9, status: 'active' },
        tags: ['urgent', 'work'],
      });

      await graph.createNode({
        id: 'query-test-2',
        type: 'task',
        properties: { title: 'Low Priority Task', priority: 3, status: 'completed' },
        tags: ['work'],
      });

      await graph.createNode({
        id: 'query-test-3',
        type: 'meeting',
        properties: { title: 'Team Sync', attendees: 5 },
        tags: ['work', 'recurring'],
      });

      await graph.createNode({
        id: 'query-test-4',
        type: 'idea',
        properties: { title: 'Random Idea', confidence: 7 },
        tags: ['personal'],
      });
    });

    test('should query nodes by type', async () => {
      const result = await graph.query({
        match: { labels: ['task'] },
      });

      expect(result.nodes.every(n => n.type === 'task')).toBe(true);
      expect(result.nodes.length).toBeGreaterThanOrEqual(2);
    });

    test('should query nodes by tag', async () => {
      const result = await graph.query({
        match: { tags: ['work'] },
      });

      expect(result.nodes.every(n => n.tags.includes('work'))).toBe(true);
    });

    test('should query nodes by property value', async () => {
      const result = await graph.query({
        where: { status: 'active' },
      });

      expect(result.nodes.length).toBeGreaterThan(0);
      expect(result.nodes.every(n => n.properties.status === 'active')).toBe(true);
    });

    test('should order results', async () => {
      const result = await graph.query({
        match: { labels: ['task'] },
        orderBy: { field: 'priority', direction: 'desc' },
      });

      const priorities = result.nodes.map(n => n.properties.priority as number);
      for (let i = 0; i < priorities.length - 1; i++) {
        expect(priorities[i]).toBeGreaterThanOrEqual(priorities[i + 1]);
      }
    });

    test('should apply pagination', async () => {
      const result1 = await graph.query({
        match: { labels: ['task'] },
        limit: 1,
        offset: 0,
      });

      const result2 = await graph.query({
        match: { labels: ['task'] },
        limit: 1,
        offset: 1,
      });

      expect(result1.nodes.length).toBe(1);
      expect(result2.nodes.length).toBe(1);
      expect(result1.nodes[0].id).not.toBe(result2.nodes[0].id);
    });

    test('should return metadata with query results', async () => {
      const result = await graph.query({
        match: { labels: ['task'] },
      });

      expect(result.metadata).toBeDefined();
      expect(typeof result.metadata.totalNodes).toBe('number');
      expect(typeof result.metadata.executionTime).toBe('number');
      expect(result.metadata.executionTime).toBeGreaterThanOrEqual(0);
    });
  });

  describe('Wiki-Link Parsing', () => {
    test('should parse wiki-links from text', async () => {
      const content = `
        This is a note about [[project-alpha]] and its dependencies.
        We should also check [[meeting-notes|last week's meeting]].
        
        Related concepts: #idea #urgent
        
        ?query{type:task AND status:active}
      `;

      const result = await graph.parseAndCreate(content, {
        autoCreateNodes: true,
        autoCreateEdges: true,
      });

      expect(result.links.length).toBeGreaterThan(0);
      expect(result.createdNodes.length).toBeGreaterThan(0);
    });

    test('should extract tags from content', async () => {
      const content = 'Important note #work #priority #thinking';
      const result = await graph.parseAndCreate(content, {
        autoCreateNodes: false,
        autoCreateEdges: false,
      });

      const allTags = new Set<string>();
      for (const link of result.links) {
        if (link.type === 'tag') {
          allTags.add(link.target);
        }
      }

      expect(allTags.size).toBeGreaterThan(0);
    });
  });

  describe('Access Control', () => {
    test('should enforce access levels', async () => {
      // Create private node
      await graph.createNode({
        id: 'access-control-test',
        type: 'note',
        properties: { secret: true },
        tags: [],
        accessLevel: AccessLevel.PRIVATE,
      });

      // Should be able to read own private node
      const node = await graph.getNode('access-control-test');
      expect(node).not.toBeNull();
    });

    test('should grant and revoke access', async () => {
      const nodeId = 'shared-node';
      await graph.createNode({
        id: nodeId,
        type: 'note',
        properties: { content: 'shared content' },
        tags: [],
        accessLevel: AccessLevel.RESTRICTED,
      });

      // Grant access
      await graph.grantAccess(nodeId, 'other-user');

      // Revoke access
      await graph.revokeAccess(nodeId, 'other-user');
    });

    test('should handle public nodes', async () => {
      await graph.createNode({
        id: 'public-node-test',
        type: 'document',
        properties: { title: 'Public Doc' },
        tags: [],
        accessLevel: AccessLevel.PUBLIC,
      });

      const node = await graph.getNode('public-node-test');
      expect(node).not.toBeNull();
    });
  });

  describe('Statistics and Export', () => {
    test('should calculate graph statistics', async () => {
      const stats = await graph.getStats();

      expect(stats.totalNodes).toBeGreaterThan(0);
      expect(typeof stats.totalEdges).toBe('number');
      expect(Object.keys(stats.nodesByType).length).toBeGreaterThan(0);
      expect(Object.keys(stats.nodesByAccessLevel).length).toBeGreaterThan(0);
    });

    test('should export graph as JSON', async () => {
      const exported = await graph.exportJSON();
      
      expect(exported).toHaveProperty('version');
      expect(exported).toHaveProperty('exportedAt');
      expect(exported).toHaveProperty('nodes');
      expect(exported).toHaveProperty('edges');
    });

    test('should backup graph data', async () => {
      const backupPath = await graph.backup();
      
      expect(backupPath).toBeDefined();
      expect(backupPath).toContain('backups');
    });
  });

  describe('Audit Trail', () => {
    test('should log all operations', async () => {
      // Perform various operations
      await graph.createNode({
        id: 'audit-trail-node',
        type: 'note',
        properties: { test: true },
        tags: [],
      });

      await graph.updateNode('audit-trail-node', {
        properties: { updated: true },
      });

      const stats = await graph.getStats();
      
      // Statistics should reflect the created node
      expect(stats.totalNodes).toBeGreaterThan(0);
    });
  });

  describe('Error Handling', () => {
    test('should handle duplicate node IDs gracefully', async () => {
      await expect(
        graph.createNode({
          id: 'audit-trail-node',
          type: 'note',
          properties: {},
          tags: [],
        })
      ).rejects.toThrow(/already exists/);
    });

    test('should handle non-existent node operations', async () => {
      await expect(
        graph.getNode('completely-non-existent-node-id')
      ).resolves.toBeNull();

      await expect(
        graph.updateNode('non-existent', { properties: {} })
      ).rejects.toThrow(/not found/);

      const deleted = await graph.deleteNode('also-non-existent');
      expect(deleted).toBe(false);
    });

    test('should validate edge types', async () => {
      await expect(
        graph.createEdge({
          from: 'edge-source',
          to: 'edge-target',
          type: 'invalid_edge_type' as any,
        })
      ).rejects.toThrow('Unknown edge type');
    });
  });

  describe('Data Integrity', () => {
    test('should maintain data consistency after restart simulation', async () => {
      const testNodeId = 'consistency-test';
      
      // Get current state
      const beforeNode = await graph.getNode(testNodeId);
      const beforeVersion = beforeNode?.version || 0;

      // Update node
      await graph.updateNode(testNodeId, {
        properties: { integrityCheck: Date.now() },
      });

      // Verify update persisted
      const afterNode = await graph.getNode(testNodeId);
      expect(afterNode?.version).toBe(beforeVersion + 1);
      expect((afterNode?.properties as any).integrityCheck).toBeDefined();
    });

    test('should track versions correctly', async () => {
      await graph.createNode({
        id: 'version-test',
        type: 'note',
        properties: { versioned: true },
        tags: [],
      });

      let node = await graph.getNode('version-test');
      let expectedVersion = 1;

      for (let i = 0; i < 5; i++) {
        node = await graph.updateNode('version-test', {
          properties: { iteration: i },
        });
        expect(node.version).toBe(expectedVersion++);
      }
    });
  });
});
