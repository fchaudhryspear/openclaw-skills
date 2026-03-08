"use strict";
/**
 * ClawVault - AI Agent Memory System
 * Phase 1 + Phase 2 + Phase 3 Integration with Advanced Features
 */
var __createBinding = (this && this.__createBinding) || (Object.create ? (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    var desc = Object.getOwnPropertyDescriptor(m, k);
    if (!desc || ("get" in desc ? !m.__esModule : desc.writable || desc.configurable)) {
      desc = { enumerable: true, get: function() { return m[k]; } };
    }
    Object.defineProperty(o, k2, desc);
}) : (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    o[k2] = m[k];
}));
var __setModuleDefault = (this && this.__setModuleDefault) || (Object.create ? (function(o, v) {
    Object.defineProperty(o, "default", { enumerable: true, value: v });
}) : function(o, v) {
    o["default"] = v;
});
var __importStar = (this && this.__importStar) || (function () {
    var ownKeys = function(o) {
        ownKeys = Object.getOwnPropertyNames || function (o) {
            var ar = [];
            for (var k in o) if (Object.prototype.hasOwnProperty.call(o, k)) ar[ar.length] = k;
            return ar;
        };
        return ownKeys(o);
    };
    return function (mod) {
        if (mod && mod.__esModule) return mod;
        var result = {};
        if (mod != null) for (var k = ownKeys(mod), i = 0; i < k.length; i++) if (k[i] !== "default") __createBinding(result, mod, k[i]);
        __setModuleDefault(result, mod);
        return result;
    };
})();
var __exportStar = (this && this.__exportStar) || function(m, exports) {
    for (var p in m) if (p !== "default" && !Object.prototype.hasOwnProperty.call(exports, p)) __createBinding(exports, m, p);
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.getCurrentSession = exports.acquireLock = exports.endSession = exports.startSession = exports.sessionManager = exports.SessionManager = exports.healthCheck = exports.getSafetyStats = exports.enforceSizeLimits = exports.canAddMemory = exports.safetyModule = exports.SafetyModule = exports.getCached = exports.globalCache = exports.MemoryCache = exports.bulkConsolidate = exports.findDuplicates = exports.consolidate = exports.consolidationModule = exports.ConsolidationModule = exports.getVectorStore = exports.VectorStore = exports.cosineSimilarity = exports.generateEmbedding = exports.ContextAwareSearch = exports.IncrementalIndexer = exports.SemanticLayerBuilder = exports.SensitiveDataDetector = exports.ConfidenceScorer = exports.ClawVault = void 0;
const embeddings_1 = require("./embeddings");
const confidence_1 = require("./confidence");
const sensitive_1 = require("./sensitive");
const semantic_1 = require("./semantic");
const indexer_1 = require("./indexer");
const search_1 = require("./search");
const vector_store_1 = require("./vector-store");
const consolidation_1 = require("./consolidation");
const cache_1 = require("./cache");
const safety_1 = require("./safety");
const session_manager_1 = require("./session-manager");
const crypto = __importStar(require("crypto"));
class ClawVault {
    constructor(config = {}) {
        this.config = {
            enableSensitiveDetection: true,
            minConfidenceThreshold: 0.3,
            autoIndex: true,
            defaultScope: 'user',
            ...config
        };
        // Core modules
        this.indexer = new indexer_1.IncrementalIndexer();
        this.searcher = new search_1.ContextAwareSearch();
        this.confidenceScorer = new confidence_1.ConfidenceScorer();
        this.sensitiveDetector = new sensitive_1.SensitiveDataDetector();
        this.semanticBuilder = new semantic_1.SemanticLayerBuilder();
        // New advanced modules
        this.vectorStore = (0, vector_store_1.getVectorStore)();
        this.consolidationModule = consolidation_1.consolidationModule;
        this.cache = cache_1.globalCache;
        this.safetyModule = safety_1.safetyModule;
        this.sessionManager = session_manager_1.sessionManager;
    }
    /**
     * Store a new memory entry
     */
    store(content, options = {}) {
        const id = this.generateId();
        const timestamp = Date.now();
        // Check for sensitive data
        let finalContent = content;
        let sensitivity = 'public';
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
        const entry = {
            id,
            content: finalContent,
            type: options.type || 'semantic',
            scope: options.scope || this.config.defaultScope,
            timestamp,
            confidence: 0.5, // Initial confidence
            embedding: (0, embeddings_1.generateEmbedding)(content),
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
    retrieve(id) {
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
    update(id, updates) {
        const existing = this.indexer.get(id);
        if (!existing)
            return undefined;
        if (updates.content) {
            existing.content = updates.content;
            existing.embedding = (0, embeddings_1.generateEmbedding)(updates.content);
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
    delete(id) {
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
    search(query, contextMessages = [], options = {}) {
        return this.searcher.search(query, contextMessages, options);
    }
    /**
     * Get memories by type
     */
    getByType(type) {
        return this.indexer.getByType(type);
    }
    /**
     * Get memories by scope
     */
    getByScope(scope) {
        return this.indexer.getByScope(scope);
    }
    /**
     * Get recent memories
     */
    getRecent(limit = 10) {
        return this.indexer.getRecent(limit);
    }
    /**
     * Get memories by tags
     */
    getByTags(tags) {
        return this.indexer.getByTags(tags);
    }
    /**
     * Get confidence score for an entry
     */
    getConfidence(id) {
        const entry = this.indexer.get(id);
        if (!entry)
            return undefined;
        return this.confidenceScorer.calculate(entry);
    }
    /**
     * Check content for sensitive data
     */
    checkSensitive(content) {
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
    export() {
        return this.indexer.getAll();
    }
    /**
     * Import memories
     */
    import(entries) {
        for (const entry of entries) {
            this.indexer.index(entry);
            this.searcher.index(entry);
        }
    }
    /**
     * Clear all memories
     */
    clear() {
        for (const id of this.indexer.getAll().map(e => e.id)) {
            this.indexer.remove(id);
            this.searcher.remove(id);
        }
    }
    generateId() {
        return `mem_${crypto.randomUUID()}`;
    }
}
exports.ClawVault = ClawVault;
// Export all modules
__exportStar(require("./types"), exports);
var confidence_2 = require("./confidence");
Object.defineProperty(exports, "ConfidenceScorer", { enumerable: true, get: function () { return confidence_2.ConfidenceScorer; } });
var sensitive_2 = require("./sensitive");
Object.defineProperty(exports, "SensitiveDataDetector", { enumerable: true, get: function () { return sensitive_2.SensitiveDataDetector; } });
var semantic_2 = require("./semantic");
Object.defineProperty(exports, "SemanticLayerBuilder", { enumerable: true, get: function () { return semantic_2.SemanticLayerBuilder; } });
var indexer_2 = require("./indexer");
Object.defineProperty(exports, "IncrementalIndexer", { enumerable: true, get: function () { return indexer_2.IncrementalIndexer; } });
var search_2 = require("./search");
Object.defineProperty(exports, "ContextAwareSearch", { enumerable: true, get: function () { return search_2.ContextAwareSearch; } });
var embeddings_2 = require("./embeddings");
Object.defineProperty(exports, "generateEmbedding", { enumerable: true, get: function () { return embeddings_2.generateEmbedding; } });
Object.defineProperty(exports, "cosineSimilarity", { enumerable: true, get: function () { return embeddings_2.cosineSimilarity; } });
// Phase 3 + Advanced features exports
var vector_store_2 = require("./vector-store");
Object.defineProperty(exports, "VectorStore", { enumerable: true, get: function () { return vector_store_2.VectorStore; } });
Object.defineProperty(exports, "getVectorStore", { enumerable: true, get: function () { return vector_store_2.getVectorStore; } });
var consolidation_2 = require("./consolidation");
Object.defineProperty(exports, "ConsolidationModule", { enumerable: true, get: function () { return consolidation_2.ConsolidationModule; } });
Object.defineProperty(exports, "consolidationModule", { enumerable: true, get: function () { return consolidation_2.consolidationModule; } });
Object.defineProperty(exports, "consolidate", { enumerable: true, get: function () { return consolidation_2.consolidate; } });
Object.defineProperty(exports, "findDuplicates", { enumerable: true, get: function () { return consolidation_2.findDuplicates; } });
Object.defineProperty(exports, "bulkConsolidate", { enumerable: true, get: function () { return consolidation_2.bulkConsolidate; } });
var cache_2 = require("./cache");
Object.defineProperty(exports, "MemoryCache", { enumerable: true, get: function () { return cache_2.MemoryCache; } });
Object.defineProperty(exports, "globalCache", { enumerable: true, get: function () { return cache_2.globalCache; } });
Object.defineProperty(exports, "getCached", { enumerable: true, get: function () { return cache_2.getCached; } });
var safety_2 = require("./safety");
Object.defineProperty(exports, "SafetyModule", { enumerable: true, get: function () { return safety_2.SafetyModule; } });
Object.defineProperty(exports, "safetyModule", { enumerable: true, get: function () { return safety_2.safetyModule; } });
Object.defineProperty(exports, "canAddMemory", { enumerable: true, get: function () { return safety_2.canAddMemory; } });
Object.defineProperty(exports, "enforceSizeLimits", { enumerable: true, get: function () { return safety_2.enforceSizeLimits; } });
Object.defineProperty(exports, "getSafetyStats", { enumerable: true, get: function () { return safety_2.getSafetyStats; } });
Object.defineProperty(exports, "healthCheck", { enumerable: true, get: function () { return safety_2.healthCheck; } });
var session_manager_2 = require("./session-manager");
Object.defineProperty(exports, "SessionManager", { enumerable: true, get: function () { return session_manager_2.SessionManager; } });
Object.defineProperty(exports, "sessionManager", { enumerable: true, get: function () { return session_manager_2.sessionManager; } });
Object.defineProperty(exports, "startSession", { enumerable: true, get: function () { return session_manager_2.startSession; } });
Object.defineProperty(exports, "endSession", { enumerable: true, get: function () { return session_manager_2.endSession; } });
Object.defineProperty(exports, "acquireLock", { enumerable: true, get: function () { return session_manager_2.acquireLock; } });
Object.defineProperty(exports, "getCurrentSession", { enumerable: true, get: function () { return session_manager_2.getCurrentSession; } });
