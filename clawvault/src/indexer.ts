/**
 * Phase 1: Incremental Indexing
 * Manages efficient indexing of memory entries
 */

import { MemoryEntry, MemoryType, MemoryScope } from './types';

export interface IndexStats {
  totalEntries: number;
  byType: Record<MemoryType, number>;
  byScope: Record<MemoryScope, number>;
  lastIndexed: number;
  pendingUpdates: number;
}

export class IncrementalIndexer {
  private entries: Map<string, MemoryEntry> = new Map();
  private typeIndex: Map<MemoryType, Set<string>> = new Map();
  private scopeIndex: Map<MemoryScope, Set<string>> = new Map();
  private tagIndex: Map<string, Set<string>> = new Map();
  private timeIndex: Map<string, Set<string>> = new Map(); // YYYY-MM-DD
  private pendingUpdates: Set<string> = new Set();
  private lastIndexed: number = 0;

  constructor() {
    // Initialize type indices
    for (const type of ['episodic', 'semantic', 'procedural', 'working'] as MemoryType[]) {
      this.typeIndex.set(type, new Set());
    }
    // Initialize scope indices
    for (const scope of ['session', 'user', 'global'] as MemoryScope[]) {
      this.scopeIndex.set(scope, new Set());
    }
  }

  index(entry: MemoryEntry): void {
    const existing = this.entries.get(entry.id);
    
    if (existing) {
      // Remove from old indices
      this.removeFromIndices(existing);
    }
    
    // Add to main storage
    this.entries.set(entry.id, entry);
    
    // Add to indices
    this.addToIndices(entry);
    
    // Track update
    this.pendingUpdates.add(entry.id);
    this.lastIndexed = Date.now();
  }

  remove(id: string): boolean {
    const entry = this.entries.get(id);
    if (!entry) return false;
    
    this.removeFromIndices(entry);
    this.entries.delete(id);
    this.pendingUpdates.delete(id);
    
    return true;
  }

  get(id: string): MemoryEntry | undefined {
    return this.entries.get(id);
  }

  getByType(type: MemoryType): MemoryEntry[] {
    const ids = this.typeIndex.get(type) || new Set();
    return Array.from(ids).map(id => this.entries.get(id)).filter(Boolean) as MemoryEntry[];
  }

  getByScope(scope: MemoryScope): MemoryEntry[] {
    const ids = this.scopeIndex.get(scope) || new Set();
    return Array.from(ids).map(id => this.entries.get(id)).filter(Boolean) as MemoryEntry[];
  }

  getByTags(tags: string[]): MemoryEntry[] {
    const result = new Set<string>();
    
    for (const tag of tags) {
      const ids = this.tagIndex.get(tag);
      if (ids) {
        for (const id of ids) {
          result.add(id);
        }
      }
    }
    
    return Array.from(result).map(id => this.entries.get(id)).filter(Boolean) as MemoryEntry[];
  }

  getByTimeRange(start: number, end: number): MemoryEntry[] {
    const results: MemoryEntry[] = [];
    
    for (const entry of this.entries.values()) {
      if (entry.timestamp >= start && entry.timestamp <= end) {
        results.push(entry);
      }
    }
    
    return results;
  }

  getRecent(limit: number = 10): MemoryEntry[] {
    return Array.from(this.entries.values())
      .sort((a, b) => b.timestamp - a.timestamp)
      .slice(0, limit);
  }

  getAll(): MemoryEntry[] {
    return Array.from(this.entries.values());
  }

  private addToIndices(entry: MemoryEntry): void {
    // Type index
    this.typeIndex.get(entry.type)?.add(entry.id);
    
    // Scope index
    this.scopeIndex.get(entry.scope)?.add(entry.id);
    
    // Tag index
    for (const tag of entry.metadata.tags) {
      if (!this.tagIndex.has(tag)) {
        this.tagIndex.set(tag, new Set());
      }
      this.tagIndex.get(tag)!.add(entry.id);
    }
    
    // Time index (YYYY-MM-DD)
    const dateKey = new Date(entry.timestamp).toISOString().split('T')[0];
    if (!this.timeIndex.has(dateKey)) {
      this.timeIndex.set(dateKey, new Set());
    }
    this.timeIndex.get(dateKey)!.add(entry.id);
  }

  private removeFromIndices(entry: MemoryEntry): void {
    this.typeIndex.get(entry.type)?.delete(entry.id);
    this.scopeIndex.get(entry.scope)?.delete(entry.id);
    
    for (const tag of entry.metadata.tags) {
      this.tagIndex.get(tag)?.delete(entry.id);
    }
    
    const dateKey = new Date(entry.timestamp).toISOString().split('T')[0];
    this.timeIndex.get(dateKey)?.delete(entry.id);
  }

  getStats(): IndexStats {
    const byType = {
      episodic: this.typeIndex.get('episodic')?.size || 0,
      semantic: this.typeIndex.get('semantic')?.size || 0,
      procedural: this.typeIndex.get('procedural')?.size || 0,
      working: this.typeIndex.get('working')?.size || 0
    };
    
    const byScope = {
      session: this.scopeIndex.get('session')?.size || 0,
      user: this.scopeIndex.get('user')?.size || 0,
      global: this.scopeIndex.get('global')?.size || 0
    };
    
    return {
      totalEntries: this.entries.size,
      byType,
      byScope,
      lastIndexed: this.lastIndexed,
      pendingUpdates: this.pendingUpdates.size
    };
  }

  flushPending(): string[] {
    const updates = Array.from(this.pendingUpdates);
    this.pendingUpdates.clear();
    return updates;
  }

  searchByText(text: string): MemoryEntry[] {
    const query = text.toLowerCase();
    return Array.from(this.entries.values()).filter(entry => 
      entry.content.toLowerCase().includes(query) ||
      entry.metadata.tags.some(tag => tag.toLowerCase().includes(query))
    );
  }
}
