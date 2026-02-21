/**
 * Phase 2: Context-Aware Search
 * Hybrid search combining vector similarity, keyword matching, and temporal relevance
 */
import { MemoryEntry, SearchResult, SearchFilters, SearchOptions, ContextMessage } from './types';
export declare class ContextAwareSearch {
    private entries;
    private hybridIndex;
    private cache;
    private cacheSize;
    private cacheHits;
    private totalSearches;
    constructor();
    /**
     * Add or update an entry in the search index
     */
    index(entry: MemoryEntry): void;
    /**
     * Remove entry from search index
     */
    remove(id: string): boolean;
    /**
     * Main search API
     * search(query, contextMessages[], options)
     */
    search(query: string, contextMessages?: ContextMessage[], options?: SearchOptions & SearchFilters): SearchResult[];
    /**
     * Get search statistics
     */
    getStats(): {
        totalSearches: number;
        cacheHits: number;
        cacheHitRate: number;
        indexedEntries: number;
        cacheSize: number;
    };
    /**
     * Clear search cache
     */
    clearCache(): void;
    private addToHybridIndex;
    private removeFromIndex;
    private recalculateIdf;
    private calculateVectorScore;
    private calculateKeywordScore;
    private calculateTemporalScore;
    private calculateContextScore;
    private extractContextKeywords;
    private combineScores;
    private getCandidates;
    private generateCacheKey;
    private checkCache;
    private cacheResults;
    private invalidateCache;
}
//# sourceMappingURL=search.d.ts.map