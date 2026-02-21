"use strict";
/**
 * Phase 2: Context-Aware Search
 * Hybrid search combining vector similarity, keyword matching, and temporal relevance
 */
Object.defineProperty(exports, "__esModule", { value: true });
exports.ContextAwareSearch = void 0;
const embeddings_1 = require("./embeddings");
// Default search weights
const DEFAULT_WEIGHTS = {
    vector: 0.6,
    keyword: 0.25,
    temporal: 0.15
};
class ContextAwareSearch {
    entries = new Map();
    hybridIndex;
    cache = new Map();
    cacheSize = 100;
    cacheHits = 0;
    totalSearches = 0;
    constructor() {
        this.hybridIndex = {
            tfidf: new Map(),
            documentFrequency: new Map(),
            documentCount: 0,
            idf: new Map()
        };
    }
    /**
     * Add or update an entry in the search index
     */
    index(entry) {
        // Remove old index if exists
        if (this.entries.has(entry.id)) {
            this.removeFromIndex(entry.id);
        }
        // Store entry
        this.entries.set(entry.id, entry);
        // Build TF-IDF index
        this.addToHybridIndex(entry);
        // Clear cache for related queries
        this.invalidateCache();
    }
    /**
     * Remove entry from search index
     */
    remove(id) {
        if (!this.entries.has(id))
            return false;
        this.removeFromIndex(id);
        this.entries.delete(id);
        this.invalidateCache();
        return true;
    }
    /**
     * Main search API
     * search(query, contextMessages[], options)
     */
    search(query, contextMessages = [], options = {}) {
        this.totalSearches++;
        const searchQuery = {
            query,
            contextMessages,
            filters: options,
            options
        };
        // Check cache
        const cacheKey = this.generateCacheKey(searchQuery);
        const cached = this.checkCache(cacheKey);
        if (cached) {
            this.cacheHits++;
            return cached;
        }
        // Build query embedding
        const queryEmbedding = (0, embeddings_1.generateEmbedding)(query);
        const queryKeywords = (0, embeddings_1.extractKeywords)(query);
        // Extract context keywords for relevance boosting
        const contextKeywords = this.extractContextKeywords(contextMessages);
        // Get candidate entries (apply filters early for performance)
        const candidates = this.getCandidates(options);
        // Score all candidates
        const results = [];
        for (const entry of candidates) {
            // Vector similarity score (0-1)
            const vectorScore = this.calculateVectorScore(entry, queryEmbedding);
            // Keyword matching score (0-1)
            const keywordScore = this.calculateKeywordScore(entry, queryKeywords);
            // Temporal relevance score (0-1)
            const temporalScore = this.calculateTemporalScore(entry);
            // Context relevance score (0-1) - boosts if matches conversation context
            const contextScore = contextKeywords.length > 0
                ? this.calculateContextScore(entry, contextKeywords)
                : 0;
            // Combine scores with weights
            const weights = options.weights || DEFAULT_WEIGHTS;
            const combinedScore = this.combineScores(vectorScore, keywordScore, temporalScore, contextScore, weights);
            // Apply confidence filter
            if (options.minConfidence !== undefined && entry.confidence < options.minConfidence) {
                continue;
            }
            results.push({
                entry,
                scores: {
                    vector: Math.round(vectorScore * 1000) / 1000,
                    keyword: Math.round(keywordScore * 1000) / 1000,
                    temporal: Math.round(temporalScore * 1000) / 1000,
                    context: Math.round(contextScore * 1000) / 1000,
                    combined: Math.round(combinedScore * 1000) / 1000
                }
            });
        }
        // Sort by combined score
        results.sort((a, b) => b.scores.combined - a.scores.combined);
        // Apply limit
        const limit = options.limit || 10;
        const finalResults = results.slice(0, limit);
        // Cache top-5 results
        if (finalResults.length > 0) {
            this.cacheResults(cacheKey, finalResults.slice(0, 5));
        }
        return finalResults;
    }
    /**
     * Get search statistics
     */
    getStats() {
        return {
            totalSearches: this.totalSearches,
            cacheHits: this.cacheHits,
            cacheHitRate: this.totalSearches > 0
                ? Math.round((this.cacheHits / this.totalSearches) * 100 * 100) / 100
                : 0,
            indexedEntries: this.entries.size,
            cacheSize: this.cache.size
        };
    }
    /**
     * Clear search cache
     */
    clearCache() {
        this.cache.clear();
        this.cacheHits = 0;
    }
    // ===== Private Methods =====
    addToHybridIndex(entry) {
        const tokens = (0, embeddings_1.removeStopwords)((0, embeddings_1.tokenize)(entry.content));
        const tokenFreq = new Map();
        // Calculate term frequency
        for (const token of tokens) {
            tokenFreq.set(token, (tokenFreq.get(token) || 0) + 1);
        }
        // Normalize TF
        const maxFreq = Math.max(...tokenFreq.values(), 1);
        const tf = new Map();
        for (const [token, freq] of tokenFreq) {
            tf.set(token, freq / maxFreq);
        }
        this.hybridIndex.tfidf.set(entry.id, tf);
        this.hybridIndex.documentCount++;
        // Update document frequency
        for (const token of new Set(tokens)) {
            this.hybridIndex.documentFrequency.set(token, (this.hybridIndex.documentFrequency.get(token) || 0) + 1);
        }
        // Recalculate IDF
        this.recalculateIdf();
    }
    removeFromIndex(id) {
        const tfMap = this.hybridIndex.tfidf.get(id);
        if (!tfMap)
            return;
        // Update document frequency
        for (const token of tfMap.keys()) {
            const df = this.hybridIndex.documentFrequency.get(token);
            if (df && df > 1) {
                this.hybridIndex.documentFrequency.set(token, df - 1);
            }
            else {
                this.hybridIndex.documentFrequency.delete(token);
            }
        }
        this.hybridIndex.tfidf.delete(id);
        this.hybridIndex.documentCount--;
        this.recalculateIdf();
    }
    recalculateIdf() {
        this.hybridIndex.idf.clear();
        for (const [token, df] of this.hybridIndex.documentFrequency) {
            const idf = Math.log((this.hybridIndex.documentCount + 1) / (df + 1)) + 1;
            this.hybridIndex.idf.set(token, idf);
        }
    }
    calculateVectorScore(entry, queryEmbedding) {
        if (!entry.embedding) {
            // Generate embedding on-the-fly if not stored
            entry.embedding = (0, embeddings_1.generateEmbedding)(entry.content);
        }
        return (0, embeddings_1.cosineSimilarity)(queryEmbedding, entry.embedding);
    }
    calculateKeywordScore(entry, queryKeywords) {
        if (queryKeywords.length === 0)
            return 0;
        const entryTfIdf = this.hybridIndex.tfidf.get(entry.id);
        if (!entryTfIdf)
            return 0;
        let score = 0;
        let matchedTerms = 0;
        for (const keyword of queryKeywords) {
            const tfidf = entryTfIdf.get(keyword);
            const idf = this.hybridIndex.idf.get(keyword);
            if (tfidf !== undefined && idf !== undefined) {
                score += tfidf * idf;
                matchedTerms++;
            }
        }
        // Normalize by query length
        const normalizedScore = score / Math.sqrt(queryKeywords.length);
        // Boost for exact matches
        const exactMatchBoost = matchedTerms / queryKeywords.length;
        return Math.min(normalizedScore * (1 + exactMatchBoost), 1);
    }
    calculateTemporalScore(entry) {
        // Recency boost with 7-day half-life
        return (0, embeddings_1.calculateRecencyBoost)(entry.timestamp, 7 * 24 * 60 * 60 * 1000);
    }
    calculateContextScore(entry, contextKeywords) {
        const contentTokens = new Set((0, embeddings_1.tokenize)(entry.content.toLowerCase()));
        const entityMatch = entry.semanticLayer.entities.some(e => contextKeywords.some(ck => e.toLowerCase().includes(ck)));
        let matches = 0;
        for (const keyword of contextKeywords) {
            if (contentTokens.has(keyword))
                matches++;
        }
        let score = matches / Math.max(contextKeywords.length, 5);
        if (entityMatch)
            score += 0.3;
        return Math.min(score, 1);
    }
    extractContextKeywords(messages) {
        const allText = messages.map(m => m.content).join(' ');
        return (0, embeddings_1.extractKeywords)(allText);
    }
    combineScores(vector, keyword, temporal, context, weights) {
        // Normalize weights
        const totalWeight = weights.vector + weights.keyword + weights.temporal;
        const normWeights = {
            vector: weights.vector / totalWeight,
            keyword: weights.keyword / totalWeight,
            temporal: weights.temporal / totalWeight
        };
        // Base combined score
        let combined = vector * normWeights.vector +
            keyword * normWeights.keyword +
            temporal * normWeights.temporal;
        // Apply context boost (up to 20% boost)
        if (context > 0) {
            combined = combined * (1 + context * 0.2);
        }
        return Math.min(combined, 1);
    }
    getCandidates(filters) {
        let candidates = Array.from(this.entries.values());
        if (filters.types && filters.types.length > 0) {
            candidates = candidates.filter(e => filters.types.includes(e.type));
        }
        if (filters.scopes && filters.scopes.length > 0) {
            candidates = candidates.filter(e => filters.scopes.includes(e.scope));
        }
        if (filters.tags && filters.tags.length > 0) {
            candidates = candidates.filter(e => filters.tags.some(tag => e.metadata.tags.includes(tag)));
        }
        if (filters.excludeSensitive) {
            candidates = candidates.filter(e => e.sensitivity === 'public' || e.sensitivity === 'internal');
        }
        if (filters.maxAge) {
            const cutoff = Date.now() - filters.maxAge;
            candidates = candidates.filter(e => e.timestamp >= cutoff);
        }
        return candidates;
    }
    generateCacheKey(query) {
        const contextHash = query.contextMessages
            ? query.contextMessages.map(m => m.content).join('|').slice(0, 100)
            : '';
        const filterHash = JSON.stringify(query.filters);
        return `${query.query}|${contextHash}|${filterHash}`;
    }
    checkCache(key) {
        const cached = this.cache.get(key);
        if (!cached)
            return null;
        // Update hit count
        cached.hitCount++;
        return cached.results;
    }
    cacheResults(key, results) {
        // Implement LRU cache eviction
        if (this.cache.size >= this.cacheSize) {
            const oldest = Array.from(this.cache.entries())
                .sort((a, b) => a[1].timestamp - b[1].timestamp)[0];
            if (oldest) {
                this.cache.delete(oldest[0]);
            }
        }
        this.cache.set(key, {
            key,
            results,
            timestamp: Date.now(),
            hitCount: 0
        });
    }
    invalidateCache() {
        // Clear all cache on index changes
        this.cache.clear();
    }
}
exports.ContextAwareSearch = ContextAwareSearch;
//# sourceMappingURL=search.js.map