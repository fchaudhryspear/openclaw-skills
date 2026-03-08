/**
 * ClawVault - AI Agent Memory System
 * Phase 1 + Phase 2 + Phase 3 Integration with Advanced Features
 */

import { 
  MemoryEntry, MemoryType, MemoryScope, ConfidenceScore, 
  SearchResult, ContextMessage, SearchFilters, SearchOptions, Memory
} from './types';
import { generateEmbedding } from './embeddings';
import { ConfidenceScorer } from './confidence';
import { SensitiveDataDetector } from './sensitive';
import { SemanticLayerBuilder } from './semantic';
import { IncrementalIndexer } from './indexer';
import { ContextAwareSearch } from './search';
import { VectorStore, getVectorStore } from './vector-store';
import { ConsolidationModule, consolidationModule, consolidate, findDuplicates, bulkConsolidate } from './consolidation';
import { MemoryCache, globalCache, getCached } from './cache';
import { SafetyModule, safetyModule, canAddMemory, enforceSizeLimits, getSafetyStats, healthCheck } from './safety';
import { SessionManager, sessionManager, startSession, endSession, acquireLock, getCurrentSession } from './session-manager';
import * as crypto from 'crypto';

export interface ClawVaultConfig {
  enableSensitiveDetection?: boolean;
  minConfidenceThreshold?: number;
  autoIndex?: boolean;
  defaultScope?: MemoryScope;
}

export interface StoreOptions {
  type?: MemoryType;
  scope?: MemoryScope;
  tags?: string[];
  source?: string;
  skipSensitiveCheck?: boolean;
}

export class ClawVault {
  private indexer: IncrementalIndexer;
  private searcher: ContextAwareSearch;
  private confidenceScorer: ConfidenceScorer;
  private sensitiveDetector: SensitiveDataDetector;
  private semanticBuilder: SemanticLayerBuilder;
  
  // New Phase 3 + Advanced modules
  private vectorStore: VectorStore;
  private consolidationModule: ConsolidationModule;
  private cache: MemoryCache;
  private safetyModule: SafetyModule;
  private sessionManager: SessionManager;
  
  private config: ClawVaultConfig;

  constructor(config: ClawVaultConfig = {}) {
    this.config = {
      enableSensitiveDetection: true,
      minConfidenceThreshold: 0.3,
      autoIndex: true,
      defaultScope: 'user',
      ...config
    };

    // Core modules
    this.indexer = new IncrementalIndexer();
    this.searcher = new ContextAwareSearch();
    this.confidenceScorer = new ConfidenceScorer();
    this.sensitiveDetector = new SensitiveDataDetector();
    this.semanticBuilder = new SemanticLayerBuilder();
    
    // New advanced modules
    this.vectorStore = getVectorStore();
    this.consolidationModule = consolidationModule;
    this.cache = globalCache;
    this.safetyModule = safetyModule;
    this.sessionManager = sessionManager;
  }

  /**
   * Store a new memory entry
   */
  store(content: string, options: StoreOptions = {}): MemoryEntry {
    const id = this.generateId();
    const timestamp = Date.now();
    
    // Check for sensitive data
    let finalContent = content;
    let sensitivity: MemoryEntry['sensitivity'] = 'public';
    
    if (this.config.enableSensitiveDetection && !options.skipSensitiveCheck) {
      const detection = this.sensitiveDetector.detect(content);
      sensitivity = this.sensitiveDetector.determineSensitivityLevel(detection);
      
      if (detection.hasSensitiveData && detection.redactedContent) {
        // Store redacted version but keep original analysis
        finalContent = detection.redactedContent;
      }
    }

    // Build semantic layer
    const semanticLayer = this.semanticBuilder.build(content);

    // Create entry
    const entry: MemoryEntry = {
      id,
      content: finalContent,
      type: options.type || 'semantic',
      scope: options.scope || this.config.defaultScope!,
      timestamp,
      confidence: 0.5, // Initial confidence
      embedding: generateEmbedding(content),
      metadata: {
        source: options.source || 'user_explicit',
        tags: options.tags || [],
        relationships: [],
        accessCount: 0,
        lastAccessed: timestamp,
        createdBy: 'system',
        modifiedAt: timestamp
      },
      semanticLayer,
      sensitivity,
      version: 1
    };

    // Calculate confidence
    const confidenceScore = this.confidenceScorer.calculate(entry);
    entry.confidence = confidenceScore.overall;

    // Index the entry
    if (this.config.autoIndex) {
      this.indexer.index(entry);
      this.searcher.index(entry);
    }

    return entry;
  }

  /**
   * Retrieve a memory entry by ID
   */
  retrieve(id: string): MemoryEntry | undefined {
    const entry = this.indexer.get(id);
    if (entry) {
      entry.metadata.accessCount++;
      entry.metadata.lastAccessed = Date.now();
    }
    return entry;
  }

  /**
   * Update an existing memory entry
   */
  update(id: string, updates: { content?: string; tags?: string[] }): MemoryEntry | undefined {
    const existing = this.indexer.get(id);
    if (!existing) return undefined;

    if (updates.content) {
      existing.content = updates.content;
      existing.embedding = generateEmbedding(updates.content);
      existing.semanticLayer = this.semanticBuilder.build(updates.content);
    }

    if (updates.tags) {
      existing.metadata.tags = updates.tags || [];
    }

    existing.version++;
    existing.metadata.modifiedAt = Date.now();
    
    // Recalculate confidence
    const confidenceScore = this.confidenceScorer.calculate(existing);
    existing.confidence = confidenceScore.overall;

    // Re-index
    this.indexer.index(existing);
    this.searcher.index(existing);

    return existing;
  }

  /**
   * Delete a memory entry
   */
  delete(id: string): boolean {
    const removed = this.indexer.remove(id);
    if (removed) {
      this.searcher.remove(id);
    }
    return removed;
  }

  /**
   * Search memories with context awareness
   * API: search(query, contextMessages[], options)
   */
  search(
    query: string,
    contextMessages: ContextMessage[] = [],
    options: SearchOptions & SearchFilters = {}
  ): SearchResult[] {
    return this.searcher.search(query, contextMessages, options);
  }

  /**
   * Get memories by type
   */
  getByType(type: MemoryType): MemoryEntry[] {
    return this.indexer.getByType(type);
  }

  /**
   * Get memories by scope
   */
  getByScope(scope: MemoryScope): MemoryEntry[] {
    return this.indexer.getByScope(scope);
  }

  /**
   * Get recent memories
   */
  getRecent(limit: number = 10): MemoryEntry[] {
    return this.indexer.getRecent(limit);
  }

  /**
   * Get memories by tags
   */
  getByTags(tags: string[]): MemoryEntry[] {
    return this.indexer.getByTags(tags);
  }

  /**
   * Get confidence score for an entry
   */
  getConfidence(id: string): ConfidenceScore | undefined {
    const entry = this.indexer.get(id);
    if (!entry) return undefined;
    
    return this.confidenceScorer.calculate(entry);
  }

  /**
   * Check content for sensitive data
   */
  checkSensitive(content: string) {
    return this.sensitiveDetector.detect(content);
  }

  /**
   * Get all statistics
   */
  getStats() {
    return {
      index: this.indexer.getStats(),
      search: this.searcher.getStats()
    };
  }

  /**
   * Export all memories
   */
  export(): MemoryEntry[] {
    return this.indexer.getAll();
  }

  /**
   * Import memories
   */
  import(entries: MemoryEntry[]): void {
    for (const entry of entries) {
      this.indexer.index(entry);
      this.searcher.index(entry);
    }
  }

  /**
   * Clear all memories
   */
  clear(): void {
    for (const id of this.indexer.getAll().map(e => e.id)) {
      this.indexer.remove(id);
      this.searcher.remove(id);
    }
  }

  private generateId(): string {
    return `mem_${crypto.randomUUID()}`;
  }
}

// Export all modules
export * from './types';
export { ConfidenceScorer } from './confidence';
export { SensitiveDataDetector } from './sensitive';
export { SemanticLayerBuilder } from './semantic';
export { IncrementalIndexer } from './indexer';
export { ContextAwareSearch } from './search';
export { generateEmbedding, cosineSimilarity } from './embeddings';

// Phase 3 + Advanced features exports
export { VectorStore, getVectorStore } from './vector-store';
export { ConsolidationModule, consolidationModule, consolidate, findDuplicates, bulkConsolidate } from './consolidation';
export { MemoryCache, globalCache, getCached } from './cache';
export { SafetyModule, safetyModule, canAddMemory, enforceSizeLimits, getSafetyStats, healthCheck } from './safety';
export { SessionManager, sessionManager, startSession, endSession, acquireLock, getCurrentSession, SessionInfo } from './session-manager';
