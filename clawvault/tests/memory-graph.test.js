
// tests/memory-graph.test.js

const assert = require('assert');
const { Node, Edge, MemoryGraph } = require('../src/memory-graph');

describe('MemoryGraph', () => {
    let graph;
    let user1 = 'user-1';
    let user2 = 'user-2';
    let system = 'system/optimus';

    beforeEach(() => {
        graph = new MemoryGraph();
    });

    describe('Node', () => {
        it('should create a node with basic properties', () => {
            const node = new Node('n1', 'Concept', 'Test Concept');
            assert.strictEqual(node.id, 'n1');
            assert.strictEqual(node.type, 'Concept');
            assert.strictEqual(node.content, 'Test Concept');
            assert.strictEqual(node.confidence, 1.0);
            assert.strictEqual(node.semantic_type, 'declarative');
            assert.ok(node.created_at);
            assert.ok(node.audit_log.length > 0);
            assert.strictEqual(node.audit_log[0].action, 'create');
        });

        it('should require id, type, and content', () => {
            assert.throws(() => new Node(), Error, 'Node requires id, type, and content.');
            assert.throws(() => new Node('n1'), Error, 'Node requires id, type, and content.');
            assert.throws(() => new Node('n1', 'type'), Error, 'Node requires id, type, and content.');
        });

        it('should update node content and log audit', () => {
            const node = new Node('n1', 'Concept', 'Old Content');
            node.updateContent('New Content', user1);
            assert.strictEqual(node.content, 'New Content');
            assert.notStrictEqual(node.updated_at, node.created_at);
            assert.strictEqual(node.audit_log.length, 2);
            assert.strictEqual(node.audit_log[1].action, 'update');
            assert.strictEqual(node.audit_log[1].actor, user1);
            assert.strictEqual(node.audit_log[1].details.new_value, 'New Content');
        });

        it('should manage access control for nodes', () => {
            const node = new Node('n2', 'Secret', 'Sensitive Info', [{
                user_id: user1,
                permission: ['read', 'write']
            }]);

            assert.ok(node.hasPermission(user1, 'read'), 'User 1 should have read permission');
            assert.ok(node.hasPermission(user1, 'write'), 'User 1 should have write permission');
            assert.ok(!node.hasPermission(user2, 'read'), 'User 2 should not have read permission');
            assert.ok(!node.hasPermission(user2, 'write'), 'User 2 should not have write permission');
            assert.ok(node.hasPermission(system, 'read'), 'System should always have read permission (default behavior if access_control is present)');
        });

        it('should mark sensitive data reference', () => {
            const node = new Node('n3', 'Key', '__OPENAI_API_KEY__', [], true, ['OpenAI API Key']);
            node.sensitive_data_ref = true;
            node.sensitive_data_context = ['OpenAI API Key'];

            assert.ok(node.sensitive_data_ref, 'Node should be marked as sensitive data reference');
            assert.deepStrictEqual(node.sensitive_data_context, ['OpenAI API Key'], 'Sensitive data context should be stored');
        });
    });

    describe('Edge', () => {
        let node1, node2;

        beforeEach(() => {
            node1 = graph.addNode(new Node('n1', 'Person', 'Fas'));
            node2 = graph.addNode(new Node('n2', 'Company', 'Versatly'));
        });

        it('should create an edge with basic properties', () => {
            const edge = new Edge('e1', node1.id, node2.id, 'WORKS_FOR');
            assert.strictEqual(edge.id, 'e1');
            assert.strictEqual(edge.source_node_id, 'n1');
            assert.strictEqual(edge.target_node_id, 'n2');
            assert.strictEqual(edge.type, 'WORKS_FOR');
            assert.strictEqual(edge.weight, 1.0);
            assert.ok(edge.created_at);
            assert.ok(edge.audit_log.length > 0);
            assert.strictEqual(edge.audit_log[0].action, 'create');
        });

        it('should require id, sourceNodeId, targetNodeId, and type', () => {
            assert.throws(() => new Edge(), Error, 'Edge requires id, sourceNodeId, targetNodeId, and type.');
            assert.throws(() => new Edge('e1'), Error, 'Edge requires id, sourceNodeId, targetNodeId, and type.');
            assert.throws(() => new Edge('e1', 'n1'), Error, 'Edge requires id, sourceNodeId, targetNodeId, and type.');
            assert.throws(() => new Edge('e1', 'n1', 'n2'), Error, 'Edge requires id, sourceNodeId, targetNodeId, and type.');
        });

        it('should update edge properties and log audit', () => {
            const edge = new Edge('e1', node1.id, node2.id, 'WORKS_FOR');
            graph.addEdge(edge);

            graph.updateEdge('e1', { weight: 0.8 }, user1);
            assert.strictEqual(edge.weight, 0.8);
            assert.ok(edge.updated_at > edge.created_at);
            assert.strictEqual(edge.audit_log.length, 2);
            assert.strictEqual(edge.audit_log[1].action, 'update');
            assert.strictEqual(edge.audit_log[1].actor, user1);
            assert.deepStrictEqual(edge.audit_log[1].details.new_values, { weight: 0.8 });
        });

        it('should manage access control for edges', () => {
            const edge = new Edge('e2', node1.id, node2.id, 'OWNS', [{
                user_id: user1,
                permission: ['read']
            }]);

            assert.ok(edge.hasPermission(user1, 'read'), 'User 1 should have read permission');
            assert.ok(!edge.hasPermission(user1, 'write'), 'User 1 should not have write permission');
            assert.ok(!edge.hasPermission(user2, 'read'), 'User 2 should not have read permission');
            assert.ok(edge.hasPermission(system, 'read'), 'System should always have read permission (default behavior if access_control is present)');
        });
    });

    describe('MemoryGraph operations', () => {
        let node1, node2, node3;

        beforeEach(() => {
            node1 = graph.addNode(new Node('n1', 'Person', 'Fas', [{ user_id: user1, permission: ['read', 'write', 'delete'] }]));
            node2 = graph.addNode(new Node('n2', 'Company', 'Versatly', [{ user_id: user1, permission: ['read'] }]));
            node3 = graph.addNode(new Node('n3', 'Project', 'ClawVault', [{ user_id: user2, permission: ['read'] }]));
        });

        it('should add and retrieve nodes', () => {
            assert.strictEqual(graph.getNode('n1').content, 'Fas');
            assert.strictEqual(graph.getNode('n2', user1).content, 'Versatly');
            assert.strictEqual(graph.getNode('n3', user2).content, 'ClawVault');
            assert.strictEqual(graph.getNode('n3', user1), null, 'User 1 should not read node 3');

            assert.throws(() => graph.addNode(new Node('n1', 'Duplicate', 'Node')), Error, 'Node with ID n1 already exists.');
        });

        it('should update nodes with proper permissions', () => {
            graph.updateNode('n1', { content: 'Faisal' }, user1);
            assert.strictEqual(graph.getNode('n1', user1).content, 'Faisal');

            assert.throws(() => graph.updateNode('n2', { content: 'New Company' }, user1), Error, 'Access denied to update node n2.');
        });

        it('should delete nodes and associated edges with proper permissions', () => {
            const edge1 = graph.addEdge(new Edge('e1', 'n1', 'n2', 'WORKS_FOR', [{ user_id: user1, permission: ['read', 'delete'] }]));
            const edge2 = graph.addEdge(new Edge('e2', 'n1', 'n3', 'MANAGES', [{ user_id: user1, permission: ['read'] }]));

            assert.strictEqual(graph.nodes.size, 3);
            assert.strictEqual(graph.edges.size, 2);

            assert.throws(() => graph.deleteNode('n2', user1), Error, 'Access denied to delete node n2.');
            assert.ok(graph.deleteNode('n1', user1), 'Node n1 should be deleted by user1');
            assert.strictEqual(graph.nodes.size, 2);
            assert.strictEqual(graph.edges.size, 0, 'Edges connected to n1 should also be deleted');

            assert.ok(!graph.deleteNode('n4'), 'Deleting non-existent node should return false');
        });

        it('should add and retrieve edges', () => {
            const edge = new Edge('e1', node1.id, node2.id, 'WORKS_FOR', [{ user_id: user1, permission: ['read'] }]);
            graph.addEdge(edge);

            assert.strictEqual(graph.getEdge('e1', user1).type, 'WORKS_FOR');
            assert.strictEqual(graph.getEdge('e1', user2), null, 'User 2 should not read edge e1');

            assert.throws(() => graph.addEdge(new Edge('e1', node1.id, node3.id, 'DUPLICATE')), Error, 'Edge with ID e1 already exists.');
            assert.throws(() => graph.addEdge(new Edge('e2', 'nonExistentNode', node1.id, 'REL')), Error, 'Source or target node not found for this edge.');
        });

        it('should update edges with proper permissions', () => {
            const edge = graph.addEdge(new Edge('e1', node1.id, node2.id, 'WORKS_FOR', [{ user_id: user1, permission: ['read', 'write'] }]));

            graph.updateEdge('e1', { weight: 0.5 }, user1);
            assert.strictEqual(graph.getEdge('e1', user1).weight, 0.5);

            assert.throws(() => graph.updateEdge('e1', { weight: 0.1 }, user2), Error, 'Access denied to update edge e1.');
        });

        it('should delete edges with proper permissions', () => {
            const edge = graph.addEdge(new Edge('e1', node1.id, node2.id, 'WORKS_FOR', [{ user_id: user1, permission: ['read', 'delete'] }]));
            assert.strictEqual(graph.edges.size, 1);

            assert.throws(() => graph.deleteEdge('e1', user2), Error, 'Access denied to delete edge e1.');
            assert.ok(graph.deleteEdge('e1', user1), 'Edge e1 should be deleted by user1');
            assert.strictEqual(graph.edges.size, 0);
            assert.ok(!graph.deleteEdge('e2'), 'Deleting non-existent edge should return false');
        });

        it('should perform basic graph traversal (BFS) respecting permissions', () => {
            // Create more nodes and edges
            const node4 = graph.addNode(new Node('n4', 'Task', 'Design UI', [{ user_id: user1, permission: ['read'] }]));
            const node5 = graph.addNode(new Node('n5', 'Dependency', 'Backend API', [{ user_id: user2, permission: ['read'] }])); // User2 only

            graph.addEdge(new Edge('e1', 'n1', 'n2', 'WORKS_FOR', [{ user_id: user1, permission: ['read'] }]));
            graph.addEdge(new Edge('e2', 'n1', 'n4', 'ASSIGNED_TO', [{ user_id: user1, permission: ['read'] }]));
            graph.addEdge(new Edge('e3', 'n4', 'n5', 'DEPENDS_ON', [{ user_id: user1, permission: ['read'] }]));

            // User1 traversal starting from n1
            const user1Traversal = graph.traverse('n1', user1);
            const user1NodeIds = user1Traversal.map(n => n.id).sort();
            assert.deepStrictEqual(user1NodeIds, ['n1', 'n2', 'n4'], 'User1 should only traverse nodes they have read access to');
            
            // System traversal starting from n1 (has access to all)
            const systemTraversal = graph.traverse('n1', system);
            const systemNodeIds = systemTraversal.map(n => n.id).sort();
            assert.deepStrictEqual(systemNodeIds, ['n1', 'n2', 'n4', 'n5'], 'System should traverse all connected nodes');

            // Traversal from a node user does not have read access to
            const user2TraversalFromN1 = graph.traverse('n1', user2);
            assert.deepStrictEqual(user2TraversalFromN1, [], 'User2 should not traverse from n1 due to no read access');

            // Traversal from a node user2 has read access to
            const user2TraversalFromN3 = graph.traverse('n3', user2);
            const user2NodeIdsFromN3 = user2TraversalFromN3.map(n => n.id).sort();
            assert.deepStrictEqual(user2NodeIdsFromN3, ['n3'], 'User2 should traverse from n3 only');
        });

        it('should correctly log read access on nodes', () => {
            const initialAuditLogLength = node1.audit_log.length;
            graph.getNode('n1', user1);
            assert.strictEqual(node1.audit_log.length, initialAuditLogLength + 1);
            assert.strictEqual(node1.audit_log[initialAuditLogLength].action, 'read');
            assert.strictEqual(node1.audit_log[initialAuditLogLength].actor, user1);
        });
    });
});
