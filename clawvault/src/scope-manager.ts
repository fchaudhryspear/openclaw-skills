/**
 * Memory Scope Manager
 * 
 * Context isolation for memories: work, personal, project-specific, session-based.
 * Enables smart /new command and scope-aware search.
 */

import { MemoryEntry, MemoryScope, MemoryType } from './types';

export type ScopeName = 'work' | 'personal' | 'project' | 'session' | 'global';

export interface ScopeContext {
  name: string;
  scopes: Set<string>;          // Active scopes (e.g., ['work', 'project-aws'])
  excludedScopes: Set<string>;  // Explicitly excluded scopes
}

export interface ScopeStats {
  totalMemories: number;
  byScope: Record<string, number>;
  activeScopes: string[];
  availableScopes: string[];
}

export interface SmartNewOptions {
  /** Clear all scopes except these */
  keep?: ScopeName[];
  /** Clear specific scopes only */
  clear?: ScopeName[];
  /** Full nuclear wipe */
  full?: boolean;
  /** Dry run - preview what would be cleared */
  dryRun?: boolean;
}

export class ScopeManager {
  private activeContext: ScopeContext;
  private allScopes: Map<string, Set<string>>; // scopeName -> set of memory IDs
  private memoryToScopes: Map<string, Set<string>>; // memoryId -> set of scope names

  constructor() {
    this.activeContext = {
      name: 'default',
      scopes: new Set(['global']),
      excludedScopes: new Set()
    };
    
    this.allScopes = new Map();
    this.memoryToScopes = new Map();
    
    // Initialize common scopes
    this.initializeCommonScopes();
  }

  /**
   * Initialize standard scope categories
   */
  private initializeCommonScopes(): void {
    const common: ScopeName[] = ['work', 'personal', 'global'];
    for (const scope of common) {
      if (!this.allScopes.has(scope)) {
        this.allScopes.set(scope, new Set());
      }
    }
  }

  /**
   * Set a single active scope (replaces all others)
   */
  scope(scope: ScopeName | string): void {
    this.activeContext.scopes.clear();
    this.activeContext.scopes.add(scope);
    this.activeContext.name = scope;
  }

  /**
   * Add scope(s) to active context without removing existing
   */
  scopeAdd(...scopes: (ScopeName | string)[]): void {
    for (const scope of scopes) {
      this.activeContext.scopes.add(scope);
    }
  }

  /**
   * Remove scope(s) from active context
   */
  scopeRemove(...scopes: (ScopeName | string)[]): void {
    for (const scope of scopes) {
      this.activeContext.scopes.delete(scope);
    }
    
    // Ensure at least one scope is active
    if (this.activeContext.scopes.size === 0) {
      this.activeContext.scopes.add('global');
    }
  }

  /**
   * Get currently active scopes
   */
  getActiveScopes(): string[] {
    return Array.from(this.activeContext.scopes);
  }

  /**
   * Check if a scope is currently active
   */
  isScopeActive(scope: ScopeName | string): boolean {
    return this.activeContext.scopes.has(scope);
  }

  /**
   * Exclude scope(s) from current context
   */
  excludeScope(...scopes: (ScopeName | string)[]): void {
    for (const scope of scopes) {
      this.activeContext.excludedScopes.add(scope);
    }
  }

  /**
   * Include scope(s) that were previously excluded
   */
  includeScope(...scopes: (ScopeName | string)[]): void {
    for (const scope of scopes) {
      this.activeContext.excludedScopes.delete(scope);
    }
  }

  /**
   * Create a new named scope (e.g., project-specific)
   */
  createScope(name: string): void {
    if (!this.allScopes.has(name)) {
      this.allScopes.set(name, new Set());
    }
  }

  /**
   * Delete a scope and all its memories
   */
  deleteScope(name: string, memoryIds: Set<string>): void {
    // Remove from active context if present
    this.scopeRemove(name);
    
    // Remove from tracking
    this.allScopes.delete(name);
    
    // Clean up memory-to-scope mappings
    for (const memoryId of memoryIds) {
      const memScopes = this.memoryToScopes.get(memoryId);
      if (memScopes) {
        memScopes.delete(name);
        if (memScopes.size === 0) {
          this.memoryToScopes.delete(memoryId);
        }
      }
    }
  }

  /**
   * Associate a memory with a scope
   */
  addMemoryToScope(memoryId: string, scope: string): void {
    // Create scope if it doesn't exist
    if (!this.allScopes.has(scope)) {
      this.allScopes.set(scope, new Set());
    }
    
    // Add to scope tracking
    this.allScopes.get(scope)!.add(memoryId);
    
    // Track reverse mapping
    if (!this.memoryToScopes.has(memoryId)) {
      this.memoryToScopes.set(memoryId, new Set());
    }
    this.memoryToScopes.get(memoryId)!.add(scope);
  }

  /**
   * Remove a memory from a scope
   */
  removeMemoryFromScope(memoryId: string, scope: string): void {
    const scopeSet = this.allScopes.get(scope);
    if (scopeSet) {
      scopeSet.delete(memoryId);
    }
    
    const memScopes = this.memoryToScopes.get(memoryId);
    if (memScopes) {
      memScopes.delete(scope);
      if (memScopes.size === 0) {
        this.memoryToScopes.delete(memoryId);
      }
    }
  }

  /**
   * Get all scopes a memory belongs to
   */
  getMemoryScopes(memoryId: string): string[] {
    const scopes = this.memoryToScopes.get(memoryId);
    return scopes ? Array.from(scopes) : [];
  }

  /**
   * Filter memories by active scope context
   * Returns memories in active scopes, excluding excluded scopes
   */
  filterByActiveContext<T extends { id: string }>(memories: T[]): T[] {
    return memories.filter(memory => {
      const memScopes = this.getMemoryScopes(memory.id);
      
      // Check exclusions first
      const hasExcluded = memScopes.some(s => this.activeContext.excludedScopes.has(s));
      if (hasExcluded) return false;
      
      // Check if matches any active scope
      return memScopes.some(s => this.activeContext.scopes.has(s));
    });
  }

  /**
   * Get scope-aware search filters
   * To be used with search options
   */
  getSearchFilters(): { includeScopes: string[]; excludeScopes: string[] } {
    return {
      includeScopes: Array.from(this.activeContext.scopes),
      excludeScopes: Array.from(this.activeContext.excludedScopes)
    };
  }

  /**
   * Infer scope from content keywords
   */
  inferScope(content: string): ScopeName | null {
    const lower = content.toLowerCase();
    
    // Work indicators
    const workKeywords = ['meeting', 'company', 'client', 'deadline', 'project', 
                          'work', 'business', 'quarter', 'budget', 'stakeholder'];
    if (workKeywords.some(kw => lower.includes(kw))) {
      return 'work';
    }
    
    // Personal indicators
    const personalKeywords = ['family', 'wife', 'kids', 'kids', 'husband', 'partner',
                              'weekend', 'vacation', 'hobby', 'personal', 'home'];
    if (personalKeywords.some(kw => lower.includes(kw))) {
      return 'personal';
    }
    
    return null;
  }

  /**
   * Smart /new command - reset context without wiping vault
   */
  smartNew(options: SmartNewOptions = {}): { 
    cleared: number; 
    preserved: number; 
    affectedMemories: string[]; 
  } {
    if (options.full) {
      // Nuclear option - clear everything
      return this.clearAllScopes();
    }
    
    const result = { cleared: 0, preserved: 0, affectedMemories: [] as string[] };
    
    // Determine which scopes to clear
    const scopesToClear = new Set<string>();
    
    if (options.keep) {
      // Keep only specified scopes, clear everything else
      for (const [scopeName, memoryIds] of this.allScopes.entries()) {
        if (!options.keep.includes(scopeName as ScopeName)) {
          scopesToClear.add(scopeName);
        }
      }
    } else if (options.clear) {
      // Clear only specified scopes
      for (const scope of options.clear) {
        scopesToClear.add(scope);
      }
    } else {
      // Default: clear session scopes only
      for (const [scopeName] of this.allScopes.entries()) {
        if (scopeName.startsWith('session-')) {
          scopesToClear.add(scopeName);
        }
      }
    }
    
    // Calculate and execute clearance
    for (const scope of scopesToClear) {
      const memoryIds = this.allScopes.get(scope);
      if (memoryIds) {
        result.cleared += memoryIds.size;
        
        if (!options.dryRun) {
          // Remove from scope tracking
          this.deleteScope(scope, memoryIds);
        }
        
        result.affectedMemories.push(...Array.from(memoryIds));
      }
    }
    
    // Count preserved
    let totalMemories = 0;
    for (const memoryIds of this.allScopes.values()) {
      totalMemories += memoryIds.size;
    }
    result.preserved = totalMemories;
    
    console.log(`🔄 /new completed: Cleared ${result.cleared}, Preserved ${result.preserved}`);
    
    return result;
  }

  /**
   * Clear all scopes (nuclear option)
   */
  private clearAllScopes(): { cleared: number; preserved: number; affectedMemories: string[] } {
    const allMemoryIds = new Set<string>();
    for (const memoryIds of this.allScopes.values()) {
      memoryIds.forEach(id => allMemoryIds.add(id));
    }
    
    this.allScopes.clear();
    this.memoryToScopes.clear();
    
    // Reset to default scope
    this.activeContext = {
      name: 'default',
      scopes: new Set(['global']),
      excludedScopes: new Set()
    };
    
    return {
      cleared: allMemoryIds.size,
      preserved: 0,
      affectedMemories: Array.from(allMemoryIds)
    };
  }

  /**
   * Get statistics about scope usage
   */
  getStats(): ScopeStats {
    const byScope: Record<string, number> = {};
    
    for (const [scopeName, memoryIds] of this.allScopes.entries()) {
      byScope[scopeName] = memoryIds.size;
    }
    
    // Count total unique memories
    const totalMemories = this.memoryToScopes.size;
    
    return {
      totalMemories,
      byScope,
      activeScopes: this.getActiveScopes(),
      availableScopes: Array.from(this.allScopes.keys())
    };
  }

  /**
   * Export scope configuration
   */
  exportConfig(): {
    activeContext: ScopeContext;
    allScopes: Record<string, string[]>;
    memoryMappings: Record<string, string[]>;
  } {
    const scopeMap: Record<string, string[]> = {};
    for (const [name, ids] of this.allScopes.entries()) {
      scopeMap[name] = Array.from(ids);
    }
    
    const memoryMap: Record<string, string[]> = {};
    for (const [id, scopes] of this.memoryToScopes.entries()) {
      memoryMap[id] = Array.from(scopes);
    }
    
    return {
      activeContext: { ...this.activeContext },
      allScopes: scopeMap,
      memoryMappings: memoryMap
    };
  }

  /**
   * Import scope configuration
   */
  importConfig(config: {
    activeContext: Partial<ScopeContext>;
    allScopes: Record<string, string[]>;
    memoryMappings: Record<string, string[]>;
  }): void {
    // Restore active context
    if (config.activeContext) {
      this.activeContext = {
        name: config.activeContext.name || 'default',
        scopes: new Set(config.activeContext.scopes || ['global']),
        excludedScopes: new Set(config.activeContext.excludedScopes || [])
      };
    }
    
    // Restore scopes
    this.allScopes.clear();
    this.memoryToScopes.clear();
    
    for (const [scopeName, memoryIds] of Object.entries(config.allScopes)) {
      this.allScopes.set(scopeName, new Set(memoryIds));
    }
    
    for (const [memoryId, scopes] of Object.entries(config.memoryMappings)) {
      this.memoryToScopes.set(memoryId, new Set(scopes));
    }
  }
}

// CLI helper for /new command
export function parseSlashNewCommand(args: string[]): SmartNewOptions {
  const options: SmartNewOptions = {};
  
  for (let i = 0; i < args.length; i++) {
    const arg = args[i];
    
    if (arg === '--full') {
      options.full = true;
    } else if (arg === '--dry-run' || arg === '-n') {
      options.dryRun = true;
    } else if (arg === '--keep' && args[i + 1]) {
      options.keep = args[++i].split(',').map(s => s.trim() as ScopeName);
    } else if (arg === '--clear' && args[i + 1]) {
      options.clear = args[++i].split(',').map(s => s.trim() as ScopeName);
    } else if (!arg.startsWith('--')) {
      // Bare argument treated as scope to clear
      if (!options.clear) options.clear = [];
      options.clear.push(arg as ScopeName);
    }
  }
  
  return options;
}
