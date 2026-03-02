/**
 * Relationship Mapper Module
 * 
 * Builds and queries a knowledge graph of entity relationships.
 * Supports traversal, pattern matching, and graph analytics.
 */

import { Entity } from './entity-extractor';

export type RelationshipType = 
  | 'associated_with'
  | 'works_at'
  | 'uses'
  | 'part_of'
  | 'located_in'
  | 'created'
  | 'owned_by'
  | 'related_to';

export interface Relationship {
  id: string;
  source: string;          // Entity ID
  target: string;          // Entity ID
  type: RelationshipType;
  confidence: number;      // 0-1
  createdAt: number;
  context: string;         // Evidence snippet
  metadata?: Record<string, any>;
}

export interface GraphNode {
  entityId: string;
  entity: Entity;
  inDegree: number;        // Incoming relationships
  outDegree: number;       // Outgoing relationships
  neighbors: Set<string>;  // Connected entity IDs
}

export interface PathResult {
  path: string[];           // Sequence of entity IDs
  relationships: Relationship[];
  totalConfidence: number;  // Product of individual confidences
  length: number;
}

export interface GraphStats {
  totalNodes: number;
  totalRelationships: number;
  averageDegree: number;
  connectedComponents: number;
  diameter: number;         // Longest shortest path
  density: number;
}

export class RelationshipMapper {
  private relationships: Map<string, Relationship>;
  private sourceIndex: Map<string, Set<string>>;
  private targetIndex: Map<string, Set<string>>;
  private typeIndex: Map<RelationshipType, Set<string>>;
  private entityCache: Map<string, Entity>;

  constructor() {
    this.relationships = new Map();
    this.sourceIndex = new Map();
    this.targetIndex = new Map();
    this.typeIndex = new Map();
    this.entityCache = new Map();
    
    const types: RelationshipType[] = ['associated_with', 'works_at', 'uses', 'part_of', 'located_in', 'created', 'owned_by', 'related_to'];
    for (const type of types) {
      this.typeIndex.set(type, new Set());
    }
  }

  addRelationship(relationship: Omit<Relationship, 'id' | 'createdAt'>): Relationship {
    const id = `rel-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
    const rel: Relationship = { ...relationship, id, createdAt: Date.now() };
    this.relationships.set(id, rel);
    this.addIndex(rel, 'source');
    this.addIndex(rel, 'target');
    this.typeIndex.get(rel.type)?.add(id);
    return rel;
  }

  addFromExtraction(extracted: { source: string; target: string; type: string; confidence: number; context: string }): Relationship | null {
    if (!this.entityExists(extracted.source) || !this.entityExists(extracted.target)) {
      return null;
    }
    return this.addRelationship({
      source: extracted.source,
      target: extracted.target,
      type: extracted.type as RelationshipType,
      confidence: extracted.confidence,
      context: extracted.context
    });
  }

  private addIndex(rel: Relationship, direction: 'source' | 'target'): void {
    const indexMap = direction === 'source' ? this.sourceIndex : this.targetIndex;
    const entityId = direction === 'source' ? rel.source : rel.target;
    if (!indexMap.has(entityId)) {
      indexMap.set(entityId, new Set());
    }
    indexMap.get(entityId)!.add(rel.id);
  }

  entityExists(entityId: string): boolean {
    return this.entityCache.has(entityId);
  }

  cacheEntity(entity: Entity): void {
    this.entityCache.set(entity.id, entity);
  }

  getRelationship(id: string): Relationship | undefined {
    return this.relationships.get(id);
  }

  getAllRelationships(): Relationship[] {
    return Array.from(this.relationships.values());
  }

  getByType(type: RelationshipType): Relationship[] {
    const ids = this.typeIndex.get(type) || new Set();
    return Array.from(ids).map(id => this.relationships.get(id)).filter((r): r is Relationship => r !== undefined);
  }

  getOutgoing(entityId: string): Relationship[] {
    const ids = this.sourceIndex.get(entityId) || new Set();
    return Array.from(ids).map(id => this.relationships.get(id)).filter((r): r is Relationship => r !== undefined);
  }

  getIncoming(entityId: string): Relationship[] {
    const ids = this.targetIndex.get(entityId) || new Set();
    return Array.from(ids).map(id => this.relationships.get(id)).filter((r): r is Relationship => r !== undefined);
  }

  getNeighbors(entityId: string, direction: 'both' | 'out' | 'in' = 'both'): Set<string> {
    const neighbors = new Set<string>();
    if (direction === 'both' || direction === 'out') {
      const outgoing = this.sourceIndex.get(entityId) || new Set();
      for (const relId of outgoing) {
        const rel = this.relationships.get(relId);
        if (rel && rel.target !== entityId) neighbors.add(rel.target);
      }
    }
    if (direction === 'both' || direction === 'in') {
      const incoming = this.targetIndex.get(entityId) || new Set();
      for (const relId of incoming) {
        const rel = this.relationships.get(relId);
        if (rel && rel.source !== entityId) neighbors.add(rel.source);
      }
    }
    return neighbors;
  }

  findShortestPath(startId: string, endId: string, maxDepth: number = 5): PathResult | null {
    if (startId === endId) return { path: [startId], relationships: [], totalConfidence: 1.0, length: 0 };
    const queue: Array<{ current: string; path: string[]; rels: Relationship[]; confidence: number }> = [{ current: startId, path: [startId], rels: [], confidence: 1.0 }];
    const visited = new Set<string>([startId]);
    while (queue.length > 0) {
      const { current, path, rels, confidence } = queue.shift()!;
      if (path.length > maxDepth) continue;
      const neighbors = this.getNeighbors(current);
      for (const neighbor of neighbors) {
        if (visited.has(neighbor)) continue;
        const newRel = this.findRelationshipBetween(current, neighbor);
        if (!newRel) continue;
        const newPath = [...path, neighbor];
        const newRels = [...rels, newRel];
        const newConfidence = confidence * newRel.confidence;
        if (neighbor === endId) return { path: newPath, relationships: newRels, totalConfidence: newConfidence, length: newPath.length - 1 };
        visited.add(neighbor);
        queue.push({ current: neighbor, path: newPath, rels: newRels, confidence: newConfidence });
      }
    }
    return null;
  }

  findRelationshipBetween(sourceId: string, targetId: string): Relationship | null {
    const outgoing = this.sourceIndex.get(sourceId) || new Set();
    for (const relId of outgoing) {
      const rel = this.relationships.get(relId);
      if (rel && rel.target === targetId) return rel;
    }
    return null;
  }

  findAllPaths(startId: string, endId: string, maxDepth: number = 5): PathResult[] {
    const paths: PathResult[] = [];
    const dfs = (current: string, path: string[], rels: Relationship[], confidence: number, visited: Set<string>) => {
      if (path.length > maxDepth) return;
      if (current === endId) {
        paths.push({ path: [...path], relationships: [...rels], totalConfidence: confidence, length: path.length - 1 });
        return;
      }
      const neighbors = this.getNeighbors(current);
      for (const neighbor of neighbors) {
        if (visited.has(neighbor)) continue;
        const rel = this.findRelationshipBetween(current, neighbor);
        if (!rel) continue;
        visited.add(neighbor);
        dfs(neighbor, [...path, neighbor], [...rels, rel], confidence * rel.confidence, visited);
        visited.delete(neighbor);
      }
    };
    dfs(startId, [startId], [], 1.0, new Set([startId]));
    return paths.sort((a, b) => b.totalConfidence - a.totalConfidence);
  }

  query(filter: { entityType?: string; relationshipType?: RelationshipType; minConfidence?: number; limit?: number }): Relationship[] {
    let results = Array.from(this.relationships.values());
    if (filter.entityType) {
      const targetType = filter.entityType;
      results = results.filter(rel => {
        const sourceEntity = this.entityCache.get(rel.source);
        const targetEntity = this.entityCache.get(rel.target);
        return sourceEntity?.type === targetType || targetEntity?.type === targetType;
      });
    }
    if (filter.relationshipType) results = results.filter(rel => rel.type === filter.relationshipType);
    if (filter.minConfidence !== undefined) results = results.filter(rel => rel.confidence >= filter.minConfidence!);
    if (filter.limit) results = results.slice(0, filter.limit);
    return results;
  }

  findFrequentPairs(minCount: number = 2): Array<{ entity1: string; entity2: string; count: number; relationshipTypes: RelationshipType[] }> {
    const pairCounts = new Map<string, { count: number; types: Set<RelationshipType> }>();
    for (const rel of this.relationships.values()) {
      const pairKey = [rel.source, rel.target].sort().join('|');
      if (!pairCounts.has(pairKey)) pairCounts.set(pairKey, { count: 0, types: new Set() });
      const pair = pairCounts.get(pairKey)!;
      pair.count++;
      pair.types.add(rel.type);
    }
    return Array.from(pairCounts.entries()).filter(([_, data]) => data.count >= minCount).map(([key, data]) => {
      const [entity1, entity2] = key.split('|');
      return { entity1, entity2, count: data.count, relationshipTypes: Array.from(data.types) };
    }).sort((a, b) => b.count - a.count);
  }

  calculateStats(): GraphStats {
    const nodeDegrees = new Map<string, { in: number; out: number }>();
    for (const rel of this.relationships.values()) {
      if (!nodeDegrees.has(rel.source)) nodeDegrees.set(rel.source, { in: 0, out: 0 });
      if (!nodeDegrees.has(rel.target)) nodeDegrees.set(rel.target, { in: 0, out: 0 });
      nodeDegrees.get(rel.source)!.out++;
      nodeDegrees.get(rel.target)!.in++;
    }
    const totalNodes = this.entityCache.size;
    const totalRelationships = this.relationships.size;
    let totalDegree = 0;
    for (const { in: inDeg, out: outDeg } of nodeDegrees.values()) totalDegree += inDeg + outDeg;
    const averageDegree = totalNodes > 0 ? totalDegree / totalNodes : 0;
    const visited = new Set<string>();
    let components = 0;
    const dfs = (node: string) => {
      if (visited.has(node)) return;
      visited.add(node);
      const neighbors = this.getNeighbors(node);
      for (const neighbor of neighbors) dfs(neighbor);
    };
    for (const entityId of this.entityCache.keys()) {
      if (!visited.has(entityId)) { dfs(entityId); components++; }
    }
    const maxEdges = totalNodes * (totalNodes - 1);
    const density = maxEdges > 0 ? totalRelationships / maxEdges : 0;
    return { totalNodes, totalRelationships, averageDegree, connectedComponents: components, diameter: 0, density };
  }

  findCentralEntities(limit: number = 10): Array<{ entityId: string; degree: number; inDegree: number; outDegree: number }> {
    const degrees = new Map<string, { in: number; out: number }>();
    for (const rel of this.relationships.values()) {
      if (!degrees.has(rel.source)) degrees.set(rel.source, { in: 0, out: 0 });
      if (!degrees.has(rel.target)) degrees.set(rel.target, { in: 0, out: 0 });
      degrees.get(rel.source)!.out++;
      degrees.get(rel.target)!.in++;
    }
    return Array.from(degrees.entries()).map(([entityId, { in: inDeg, out: outDeg }]) => ({ entityId, degree: inDeg + outDeg, inDegree: inDeg, outDegree: outDeg })).sort((a, b) => b.degree - a.degree).slice(0, limit);
  }

  exportAdjacencyList(): Record<string, Array<{ target: string; type: RelationshipType; confidence: number }>> {
    const adjList: Record<string, Array<{ target: string; type: RelationshipType; confidence: number }>> = {};
    for (const rel of this.relationships.values()) {
      if (!adjList[rel.source]) adjList[rel.source] = [];
      adjList[rel.source].push({ target: rel.target, type: rel.type, confidence: rel.confidence });
    }
    return adjList;
  }

  clear(): void {
    this.relationships.clear();
    this.sourceIndex.clear();
    this.targetIndex.clear();
    for (const typeSet of this.typeIndex.values()) typeSet.clear();
    this.entityCache.clear();
  }

  /**
   * Get related entities for an entity
   */
  getRelatedEntities(entityId: string, limit: number = 5): Array<{ entity?: Entity; coOccurrence: number }> {
    const outgoing = this.sourceIndex.get(entityId) || new Set();
    const incoming = this.targetIndex.get(entityId) || new Set();
    const neighborCounts = new Map<string, number>();
    for (const relId of outgoing) {
      const rel = this.relationships.get(relId);
      if (rel && rel.target !== entityId) neighborCounts.set(rel.target, (neighborCounts.get(rel.target) || 0) + 1);
    }
    for (const relId of incoming) {
      const rel = this.relationships.get(relId);
      if (rel && rel.source !== entityId) neighborCounts.set(rel.source, (neighborCounts.get(rel.source) || 0) + 1);
    }
    return Array.from(neighborCounts.entries()).sort((a, b) => b[1] - a[1]).slice(0, limit).map(([otherEntityId, count]) => {
      const entity = this.entityCache.get(otherEntityId);
      return { entity, coOccurrence: count };
    });
  }
}
