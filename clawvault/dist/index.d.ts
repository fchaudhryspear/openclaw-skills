/**
 * ClawVault - AI Agent Memory System
 * Phase 1 + Phase 2 + Phase 3 Integration with Advanced Features
 */
import { MemoryEntry, MemoryType, MemoryScope, ConfidenceScore, SearchResult, ContextMessage, SearchFilters, SearchOptions } from './types';
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
export declare class ClawVault {
    private indexer;
    private searcher;
    private confidenceScorer;
    private sensitiveDetector;
    private semanticBuilder;
    private vectorStore;
    private consolidationModule;
    private cache;
    private safetyModule;
    private sessionManager;
    private config;
    constructor(config?: ClawVaultConfig);
    /**
     * Store a new memory entry
     */
    store(content: string, options?: StoreOptions): MemoryEntry;
    /**
     * Retrieve a memory entry by ID
     */
    retrieve(id: string): MemoryEntry | undefined;
    /**
     * Update an existing memory entry
     */
    update(id: string, updates: {
        content?: string;
        tags?: string[];
    }): MemoryEntry | undefined;
    /**
     * Delete a memory entry
     */
    delete(id: string): boolean;
    /**
     * Search memories with context awareness
     * API: search(query, contextMessages[], options)
     */
    search(query: string, contextMessages?: ContextMessage[], options?: SearchOptions & SearchFilters): SearchResult[];
    /**
     * Get memories by type
     */
    getByType(type: MemoryType): MemoryEntry[];
    /**
     * Get memories by scope
     */
    getByScope(scope: MemoryScope): MemoryEntry[];
    /**
     * Get recent memories
     */
    getRecent(limit?: number): MemoryEntry[];
    /**
     * Get memories by tags
     */
    getByTags(tags: string[]): MemoryEntry[];
    /**
     * Get confidence score for an entry
     */
    getConfidence(id: string): ConfidenceScore | undefined;
    /**
     * Check content for sensitive data
     */
    checkSensitive(content: string): import("./types").SensitiveDataDetection;
    /**
     * Get all statistics
     */
    getStats(): {
        index: import("./indexer").IndexStats;
        search: {
            totalSearches: number;
            cacheHits: number;
            cacheHitRate: number;
            indexedEntries: number;
            cacheSize: number;
        };
    };
    /**
     * Export all memories
     */
    export(): MemoryEntry[];
    /**
     * Import memories
     */
    import(entries: MemoryEntry[]): void;
    /**
     * Clear all memories
     */
    clear(): void;
    private generateId;
}
export * from './types';
export { ConfidenceScorer } from './confidence';
export { SensitiveDataDetector } from './sensitive';
export { SemanticLayerBuilder } from './semantic';
export { IncrementalIndexer } from './indexer';
export { ContextAwareSearch } from './search';
export { generateEmbedding, cosineSimilarity } from './embeddings';
export { VectorStore, getVectorStore } from './vector-store';
export { ConsolidationModule, consolidationModule, consolidate, findDuplicates, bulkConsolidate } from './consolidation';
export { MemoryCache, globalCache, getCached } from './cache';
export { SafetyModule, safetyModule, canAddMemory, enforceSizeLimits, getSafetyStats, healthCheck } from './safety';
export { SessionManager, sessionManager, startSession, endSession, acquireLock, getCurrentSession, SessionInfo } from './session-manager';
//# sourceMappingURL=index.d.ts.map