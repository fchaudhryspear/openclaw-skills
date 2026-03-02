
// src/memory-graph.js

class Node {
    constructor(id, type, content, accessControl = []) {
        if (!id || !type || !content) {
            throw new Error("Node requires id, type, and content.");
        }
        this.id = id;
        this.type = type;
        this.content = content;
        this.confidence = 1.0; // Default confidence
        this.semantic_type = 'declarative'; // Default semantic type
        const now = new Date();
        this._created_at = now;
        this._updated_at = now;
        this._accessed_at = now;
        this.source = 'system/optimus';
        this.tags = [];
        this.access_control = accessControl;
        this.sensitive_data_ref = false;
        this.sensitive_data_context = [];
        this.audit_log = [{ timestamp: now.toISOString(), action: 'create', actor: 'system/optimus', details: { type, content } }];
    }

    get created_at() { return this._created_at.toISOString(); }
    get updated_at() { return this._updated_at.toISOString(); }
    get accessed_at() { return this._accessed_at.toISOString(); }

    updateContent(newContent, actor = 'system/optimus') {
        this.content = newContent;
        this._updated_at = new Date();
        this.audit_log.push({ timestamp: this._updated_at.toISOString(), action: 'update', actor, details: { field: 'content', new_value: newContent } });
    }

    hasPermission(userId, permissionType) {
        console.log(`Checking permission for userId: ${userId}, type: ${permissionType}`);
        console.log(`Node/Edge access_control:`, this.access_control);
        // System user always has full permission for internal operations
        if (userId === 'system/optimus') {
            console.log(`System user ${userId} has permission.`);
            return true;
        }
        if (!this.access_control || this.access_control.length === 0) {
            // If no explicit access control, deny access to non-system users
            console.log(`No explicit access control. Denying access to ${userId}.`);
            return false;
        }
        const hasAccess = this.access_control.some(rule =>
            rule.user_id === userId && rule.permission.includes(permissionType)
        );
        console.log(`Explicit access check for ${userId}: ${hasAccess}`);
        return hasAccess;
    }
}

class Edge {
    constructor(id, sourceNodeId, targetNodeId, type, accessControl = []) {
        if (!id || !sourceNodeId || !targetNodeId || !type) {
            throw new Error("Edge requires id, sourceNodeId, targetNodeId, and type.");
        }
        this.id = id;
        this.source_node_id = sourceNodeId;
        this.target_node_id = targetNodeId;
        this.type = type;
        this.weight = 1.0; // Default weight
        const now = new Date();
        this._created_at = now;
        this._updated_at = now;
        this.confidence = 1.0; // Default confidence
        this.access_control = accessControl;
        this.audit_log = [{ timestamp: now.toISOString(), action: 'create', actor: 'system/optimus', details: { sourceNodeId, targetNodeId, type } }];
    }

    get created_at() { return this._created_at.toISOString(); }
    get updated_at() { return this._updated_at.toISOString(); }

    hasPermission(userId, permissionType) {
        if (!this.access_control || this.access_control.length === 0) {
            return userId === 'system/optimus';
        }
        return this.access_control.some(rule =>
            rule.user_id === userId && rule.permission.includes(permissionType)
        );
    }
}

class MemoryGraph {
    constructor() {
        this.nodes = new Map();
        this.edges = new Map();
    }

    addNode(node) {
        if (this.nodes.has(node.id)) {
            throw new Error(`Node with ID ${node.id} already exists.`);
        }
        this.nodes.set(node.id, node);
        return node;
    }

    getNode(id, userId = 'system/optimus') {
        const node = this.nodes.get(id);
        if (node && node.hasPermission(userId, 'read')) {
            node._accessed_at = new Date(); // Update internal Date object
            node.audit_log.push({ timestamp: node.accessed_at, action: 'read', actor: userId });
            return node;
        }
        return null; // Or throw an AccessDeniedError
    }

    updateNode(id, updates, actor = 'system/optimus') {
        const node = this.nodes.get(id);
        if (!node) {
            throw new Error(`Node with ID ${id} not found.`);
        }
        if (!node.hasPermission(actor, 'write')) {
            throw new Error(`Access denied to update node ${id}.`);
        }

        const oldValues = {};
        for (const key in updates) {
            if (node.hasOwnProperty(key) && key !== 'id' && key !== 'created_at') {
                oldValues[key] = node[key];
                node[key] = updates[key];
            }
        }
        node.updated_at = new Date().toISOString();
        node.audit_log.push({ timestamp: node.updated_at, action: 'update', actor, details: { old_values: oldValues, new_values: updates } });
        return node;
    }

    deleteNode(id, actor = 'system/optimus') {
        const node = this.nodes.get(id);
        if (!node) {
            return false;
        }
        if (!node.hasPermission(actor, 'delete')) {
            throw new Error(`Access denied to delete node ${id}.`);
        }
        this.nodes.delete(id);
        // Also remove any edges connected to this node
        this.edges.forEach((edge, edgeId) => {
            if (edge.source_node_id === id || edge.target_node_id === id) {
                this.edges.delete(edgeId);
            }
        });
        node.audit_log.push({ timestamp: new Date().toISOString(), action: 'delete', actor, details: { nodeId: id } });
        return true;
    }

    addEdge(edge) {
        if (this.edges.has(edge.id)) {
            throw new Error(`Edge with ID ${edge.id} already exists.`);
        }
        if (!this.nodes.has(edge.source_node_id) || !this.nodes.has(edge.target_node_id)) {
            throw new Error("Source or target node not found for this edge.");
        }
        this.edges.set(edge.id, edge);
        return edge;
    }

    getEdge(id, userId = 'system/optimus') {
        const edge = this.edges.get(id);
        if (edge && edge.hasPermission(userId, 'read')) {
            return edge;
        }
        return null;
    }

    updateEdge(id, updates, actor = 'system/optimus') {
        console.log(`Attempting to update edge ${id} by actor: ${actor}`);
        const edge = this.edges.get(id);
        if (!edge) {
            throw new Error(`Edge with ID ${id} not found.`);
        }
        if (!edge.hasPermission(actor, 'write')) {
            console.error(`Access denied for actor ${actor} to update edge ${id}.`);
            throw new Error(`Access denied to update edge ${id}.`);
        }

        const oldValues = {};
        for (const key in updates) {
            if (edge.hasOwnProperty(key) && key !== 'id' && key !== 'created_at' && key !== 'source_node_id' && key !== 'target_node_id') {
                oldValues[key] = edge[key];
                edge[key] = updates[key];
            }
        }
        edge.updated_at = new Date().toISOString();
        edge.audit_log.push({ timestamp: edge.updated_at, action: 'update', actor, details: { old_values: oldValues, new_values: updates } });
        return edge;
    }

    deleteEdge(id, actor = 'system/optimus') {
        const edge = this.edges.get(id);
        if (!edge) {
            return false;
        }
        if (!edge.hasPermission(actor, 'delete')) {
            throw new Error(`Access denied to delete edge ${id}.`);
        }
        this.edges.delete(id);
        edge.audit_log.push({ timestamp: new Date().toISOString(), action: 'delete', actor, details: { edgeId: id } });
        return true;
    }

    // Basic graph traversal (BFS)
    traverse(startNodeId, userId = 'system/optimus') {
        const visited = new Set();
        const queue = [startNodeId];
        const traversalPath = [];

        while (queue.length > 0) {
            const currentNodeId = queue.shift();
            const currentNode = this.getNode(currentNodeId, userId);

            if (currentNode && !visited.has(currentNodeId)) {
                visited.add(currentNodeId);
                traversalPath.push(currentNode);

                // Find outgoing edges
                this.edges.forEach(edge => {
                    if (edge.source_node_id === currentNodeId && edge.hasPermission(userId, 'read')) {
                        if (!visited.has(edge.target_node_id)) {
                            queue.push(edge.target_node_id);
                        }
                    }
                });
            }
        }
        return traversalPath;
    }
}

module.exports = { Node, Edge, MemoryGraph };
