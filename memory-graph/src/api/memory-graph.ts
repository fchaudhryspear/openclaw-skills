/**
 * Memory Graph Core - Main API integrating all components
 */

import {
  Node,
  Edge,
  NodeType,
  EdgeType,
  AccessLevel,
  Role,
  AuditAction,
  QueryParams,
  QueryResult,
  AccessContext,
} from '../model/types';
import { EncryptedStore } from '../storage/encrypted-store';
import { AccessController, AccessContext as RBACContext } from '../access/rbac';
import { Auditor } from '../audit/auditor';
import { WikiParser } from '../parser/wiki-parser';
import { schemaManager } from '../model/schema-manager';

export interface MemoryGraphConfig {
  storagePath: string;
  encryptionKey: string;
  defaultAccessLevel?: AccessLevel;
  auditEnabled?: boolean;
  userId: string;
}

export class MemoryGraph {
  private store: EncryptedStore;
  private accessController: AccessController;
  private auditor: Auditor;
  private wikiParser: WikiParser;
  private config: MemoryGraphConfig;
  private currentNodeCache: Map<string, Node>;
  private currentEdgeCache: Map<string, Edge>;

  private constructor(config: MemoryGraphConfig) {
    this.config = config;
    this.store = new EncryptedStore(config.storagePath, config.encryptionKey);
    this.accessController = new AccessController();
    this.wikiParser = new WikiParser();
    this.currentNodeCache = new Map();
    this.currentEdgeCache = new Map();
    
    // Auditor is initialized after store initialization
    this.auditor = new Auditor(this.store, {
      logReads: config.auditEnabled ?? true,
      logWrites: config.auditEnabled ?? true,
      logDeletes: config.auditEnabled ?? true,
      retentionDays: 90,
    });
  }

  /**
   * Create and initialize a new MemoryGraph instance
   */
  static async create(config: MemoryGraphConfig): Promise<MemoryGraph> {
    const graph = new MemoryGraph(config);
    await graph.store.initialize();
    
    // Load existing data into cache
    const nodes = await graph.store.readNodes();
    for (const node of nodes) {
      graph.currentNodeCache.set(node.id, node);
    }
    
    const edges = await graph.store.readEdges();
    for (const edge of edges) {
      graph.currentEdgeCache.set(edge.id, edge);
    }
    
    return graph;
  }

  /**
   * Get access context for current user
   */
  private getContext(roles: Role[] = [Role.EDITOR]): RBACContext {
    return {
      userId: this.config.userId,
      userRoles: roles,
    };
  }

  // ==================== NODE OPERATIONS ====================

  /**
   * Create a new node
   */
  async createNode(params: {
    id: string;
    type: NodeType;
    properties: Record<string, unknown>;
    tags?: string[];
    accessLevel?: AccessLevel;
  }): Promise<Node> {
    const { id, type, properties, tags = [], accessLevel } = params;
    const context = this.getContext();

    // Validate schema
    const validation = schemaManager.validateNode(type, properties);
    if (!validation.valid) {
      throw new Error(`Schema validation failed: ${validation.errors.join(', ')}`);
    }

    // Check for duplicate ID
    if (this.currentNodeCache.has(id)) {
      throw new Error(`Node with id '${id}' already exists`);
    }

    const now = new Date();
    const node: Node = {
      id,
      type,
      properties,
      tags,
      createdAt: now,
      updatedAt: now,
      createdBy: this.config.userId,
      accessLevel: accessLevel || this.config.defaultAccessLevel || AccessLevel.PRIVATE,
      version: 1,
    };

    // Store node
    await this.store.addNode(node);
    this.currentNodeCache.set(id, node);

    // Audit log
    await this.auditor.logNodeOperation(
      AuditAction.CREATE,
      id,
      context.userId,
      { after: node }
    );

    return node;
  }

  /**
   * Read a node by ID
   */
  async getNode(id: string): Promise<Node | null> {
    const context = this.getContext([Role.VIEWER, Role.EDITOR, Role.ADMIN]);
    const node = this.currentNodeCache.get(id) || await this.store.findNode(id);

    if (!node) {
      return null;
    }

    // Check access
    if (!this.accessController.canAccessNode(context, node, 'read')) {
      await this.auditor.logAccessDenial(id, context.userId, 'read');
      return null;
    }

    await this.auditor.logNodeOperation(AuditAction.READ, id, context.userId);
    return node;
  }

  /**
   * Update a node
   */
  async updateNode(
    id: string,
    updates: Partial<Pick<Node, 'properties' | 'tags' | 'accessLevel'>>
  ): Promise<Node> {
    const context = this.getContext();
    const existing = await this.getNode(id);

    if (!existing) {
      throw new Error(`Node '${id}' not found`);
    }

    // Check write access
    if (!this.accessController.canAccessNode(context, existing, 'write')) {
      await this.auditor.logAccessDenial(id, context.userId, 'write');
      throw new Error('Access denied');
    }

    const updated: Node = {
      ...existing,
      ...updates,
      updatedAt: new Date(),
      version: existing.version + 1,
    };

    await this.store.updateNode(id, updated);
    this.currentNodeCache.set(id, updated);

    await this.auditor.logNodeOperation(
      AuditAction.UPDATE,
      id,
      context.userId,
      { before: existing, after: updated }
    );

    return updated;
  }

  /**
   * Delete a node
   */
  async deleteNode(id: string): Promise<boolean> {
    const context = this.getContext();
    const node = await this.getNode(id);

    if (!node) {
      return false;
    }

    // Check delete access
    if (!this.accessController.canAccessNode(context, node, 'delete')) {
      await this.auditor.logAccessDenial(id, context.userId, 'delete');
      throw new Error('Access denied');
    }

    // Also delete associated edges
    const edges = await this.store.findEdgesByNode(id);
    for (const edge of edges) {
      await this.store.deleteEdge(edge.id);
      this.currentEdgeCache.delete(edge.id);
    }

    const deleted = await this.store.deleteNode(id);
    if (deleted) {
      this.currentNodeCache.delete(id);
      
      await this.auditor.logNodeOperation(
        AuditAction.DELETE,
        id,
        context.userId,
        { before: node }
      );
    }

    return deleted;
  }

  /**
   * Query nodes with filters
   */
  async query(params: QueryParams): Promise<QueryResult> {
    const context = this.getContext([Role.VIEWER, Role.EDITOR, Role.ADMIN]);
    const startTime = Date.now();

    let nodes = Array.from(this.currentNodeCache.values());
    const edges: Edge[] = [];

    // Apply filters
    if (params.match?.labels) {
      nodes = nodes.filter(n => params.match!.labels!.includes(n.type));
    }

    if (params.match?.ids) {
      nodes = nodes.filter(n => params.match!.ids!.includes(n.id));
    }

    if (params.match?.tags) {
      nodes = nodes.filter(n => 
        params.match!.tags!.some(tag => n.tags.includes(tag))
      );
    }

    if (params.where) {
      for (const [key, value] of Object.entries(params.where)) {
        nodes = nodes.filter(n => 
          JSON.stringify(n.properties[key]) === JSON.stringify(value)
        );
      }
    }

    // Filter by access level
    nodes = this.accessController.filterAccessibleNodes(context, nodes);

    // Apply ordering
    if (params.orderBy) {
      nodes.sort((a, b) => {
        const aVal = a.properties[params.orderBy!.field];
        const bVal = b.properties[params.orderBy!.field];
        
        if (params.orderBy!.direction === 'desc') {
          return aVal > bVal ? -1 : 1;
        }
        return aVal < bVal ? -1 : 1;
      });
    }

    // Apply pagination
    if (params.offset) {
      nodes = nodes.slice(params.offset);
    }
    if (params.limit) {
      nodes = nodes.slice(0, params.limit);
    }

    // Fetch related edges if depth specified
    if (params.depth && params.depth > 0) {
      const nodeIds = nodes.map(n => n.id);
      for (const nodeId of nodeIds) {
        const relatedEdges = await this.store.findEdgesByNode(nodeId);
        edges.push(...relatedEdges);
      }
    }

    return {
      nodes,
      edges,
      metadata: {
        totalNodes: nodes.length,
        totalEdges: edges.length,
        executionTime: Date.now() - startTime,
      },
    };
  }

  // ==================== EDGE OPERATIONS ====================

  /**
   * Create a relationship between nodes
   */
  async createEdge(params: {
    from: string;
    to: string;
    type: EdgeType;
    properties?: Record<string, unknown>;
  }): Promise<Edge> {
    const context = this.getContext();
    const { from, to, type, properties = {} } = params;

    // Validate nodes exist and are accessible
    const fromNode = await this.getNode(from);
    const toNode = await this.getNode(to);

    if (!fromNode || !toNode) {
      throw new Error('Source or target node not found');
    }

    // Validate edge schema
    const validation = schemaManager.validateEdge(type, properties);
    if (!validation.valid) {
      throw new Error(`Edge schema validation failed: ${validation.errors.join(', ')}`);
    }

    const id = `${from}_${type}_${to}_${Date.now()}`;
    const edge: Edge = {
      id,
      from,
      to,
      type,
      properties,
      createdAt: new Date(),
      createdBy: this.config.userId,
    };

    await this.store.addEdge(edge);
    this.currentEdgeCache.set(id, edge);

    await this.auditor.logEdgeOperation(
      AuditAction.CREATE,
      id,
      context.userId,
      { after: edge }
    );

    return edge;
  }

  /**
   * Delete an edge
   */
  async deleteEdge(id: string): Promise<boolean> {
    const context = this.getContext();
    const edge = this.currentEdgeCache.get(id) || await this.store.readEdges()
      .then(edges => edges.find(e => e.id === id));

    if (!edge) {
      return false;
    }

    const deleted = await this.store.deleteEdge(id);
    if (deleted) {
      this.currentEdgeCache.delete(id);
      
      await this.auditor.logEdgeOperation(
        AuditAction.DELETE,
        id,
        context.userId,
        { before: edge }
      );
    }

    return deleted;
  }

  /**
   * Get edges connected to a node
   */
  async getEdges(nodeId: string): Promise<Edge[]> {
    return this.store.findEdgesByNode(nodeId);
  }

  // ==================== WIKI-LINK PARSING ====================

  /**
   * Parse text and create nodes/links automatically
   */
  async parseAndCreate(content: string, options?: {
    autoCreateNodes: boolean;
    autoCreateEdges: boolean;
  }): Promise<{
    createdNodes: Node[];
    createdEdges: Edge[];
    links: WikiLink[];
  }> {
    const parsed = this.wikiParser.parse(content);
    const createdNodes: Node[] = [];
    const createdEdges: Edge[] = [];

    // Extract wiki-links
    for (const link of parsed.links) {
      if (link.type === 'link' && options?.autoCreateNodes !== false) {
        // Check if target node exists
        const existing = await this.getNode(link.target);
        
        if (!existing) {
          // Create new node from parsed link
          const inferredType = this.wikiParser.inferNodeType(parsed.tags, link.context);
          const node = await this.createNode({
            id: link.target,
            type: inferredType as NodeType,
            properties: { title: link.target, sourceContent: content },
            tags: parsed.tags,
          });
          createdNodes.push(node);
        }
      }
    }

    // Create edges for detected relationships
    if (options?.autoCreateEdges !== false) {
      const relationships = this.wikiParser.suggestRelationships(parsed.links);
      for (const rel of relationships) {
        try {
          const edge = await this.createEdge({
            from: rel.from,
            to: rel.to,
            type: rel.type as EdgeType,
            properties: { confidence: rel.confidence },
          });
          createdEdges.push(edge);
        } catch (error) {
          // Skip if nodes don't exist or error occurs
          console.warn(`Failed to create edge: ${error}`);
        }
      }
    }

    return { createdNodes, createdEdges, links: parsed.links };
  }

  // ==================== ACCESS CONTROL ====================

  /**
   * Grant access to a node
   */
  async grantAccess(nodeId: string, userId: string): Promise<void> {
    const context = this.getContext([Role.ADMIN]);
    const node = await this.getNode(nodeId);

    if (!node) {
      throw new Error('Node not found');
    }

    this.accessController.grantAccess(nodeId, userId);
    
    await this.auditor.logPermissionChange(nodeId, context.userId, userId, true);
  }

  /**
   * Revoke access from a node
   */
  async revokeAccess(nodeId: string, userId: string): Promise<void> {
    const context = this.getContext([Role.ADMIN]);
    
    this.accessController.revokeAccess(nodeId, userId);
    
    await this.auditor.logPermissionChange(nodeId, context.userId, userId, false);
  }

  // ==================== UTILITIES ====================

  /**
   * Backup the entire graph
   */
  async backup(): Promise<string> {
    return this.store.backup();
  }

  /**
   * Export graph as JSON (unencrypted)
   */
  async exportJSON(): Promise<unknown> {
    const nodes = await this.store.readNodes();
    const edges = await this.store.readEdges();
    
    return {
      version: '1.0',
      exportedAt: new Date().toISOString(),
      nodes,
      edges,
    };
  }

  /**
   * Get statistics
   */
  async getStats(): Promise<{
    totalNodes: number;
    totalEdges: number;
    nodesByType: Record<string, number>;
    nodesByAccessLevel: Record<string, number>;
    tagsDistribution: Record<string, number>;
  }> {
    const nodes = Array.from(this.currentNodeCache.values());
    const edges = Array.from(this.currentEdgeCache.values());

    const stats = {
      totalNodes: nodes.length,
      totalEdges: edges.length,
      nodesByType: {} as Record<string, number>,
      nodesByAccessLevel: {} as Record<string, number>,
      tagsDistribution: {} as Record<string, number>,
    };

    for (const node of nodes) {
      // Count by type
      stats.nodesByType[node.type] = (stats.nodesByType[node.type] || 0) + 1;
      
      // Count by access level
      stats.nodesByAccessLevel[node.accessLevel] = 
        (stats.nodesByAccessLevel[node.accessLevel] || 0) + 1;
      
      // Count tags
      for (const tag of node.tags) {
        stats.tagsDistribution[tag] = (stats.tagsDistribution[tag] || 0) + 1;
      }
    }

    return stats;
  }

  /**
   * Shutdown and cleanup
   */
  async shutdown(): Promise<void> {
    await this.auditor.shutdown();
  }
}

export default MemoryGraph;
