"use strict";
/**
 * ClawVault Memory Store
 *
 * Core memory management with confidence scoring
 */
Object.defineProperty(exports, "__esModule", { value: true });
exports.MemoryStore = void 0;
const types_1 = require("./types");
const confidence_1 = require("./confidence");
/**
 * Generate a unique ID for memories
 */
function generateId() {
    return `mem_${Date.now()}_${Math.random().toString(36).substring(2, 11)}`;
}
/**
 * Memory Store class with confidence scoring
 */
class MemoryStore {
    memories = new Map();
    config;
    /**
     * Create a new MemoryStore
     * @param config - Optional custom confidence configuration
     */
    constructor(config) {
        this.config = { ...types_1.DEFAULT_CONFIDENCE_CONFIG, ...config };
    }
    /**
     * Store a new memory with calculated confidence
     *
     * @param input - Memory input data
     * @returns The stored memory with confidence score
     */
    store(input) {
        const now = new Date();
        const id = generateId();
        const source = input.source || 'auto_extracted';
        // Calculate initial confidence at ingest time
        const confidence = (0, confidence_1.calculateConfidence)({
            source,
            createdAt: now,
            feedback: null,
            config: this.config,
        });
        const memory = {
            id,
            content: input.content,
            sensitive: false, // Default to not sensitive
            metadata: {
                createdAt: now.toISOString(),
                updatedAt: now.toISOString(),
                source,
                tags: input.tags || [],
                feedback: null,
                confidence,
                ...input.metadata,
            },
        };
        this.memories.set(id, memory);
        return memory;
    }
    /**
     * Store a memory with explicit ID (for loading from storage)
     *
     * @param memory - Complete memory object
     * @returns The stored memory
     */
    storeWithId(memory) {
        // Ensure confidence is calculated if not present
        if (memory.metadata.confidence === undefined) {
            (0, confidence_1.updateMemoryConfidence)(memory, this.config);
        }
        this.memories.set(memory.id, memory);
        return memory;
    }
    /**
     * Get a memory by ID
     *
     * @param id - Memory ID
     * @returns The memory or undefined if not found
     */
    get(id) {
        const memory = this.memories.get(id);
        if (memory) {
            // Recalculate confidence on retrieval to account for time decay
            this.refreshConfidence(memory);
            return memory;
        }
        return undefined;
    }
    /**
     * Update user feedback on a memory and recalculate confidence
     *
     * @param id - Memory ID
     * @param feedback - User feedback ('thumbs_up' or 'thumbs_down')
     * @returns Updated memory or undefined if not found
     */
    setFeedback(id, feedback) {
        const memory = this.memories.get(id);
        if (!memory) {
            return undefined;
        }
        memory.metadata.feedback = feedback;
        memory.metadata.updatedAt = new Date().toISOString();
        // Recalculate confidence with new feedback
        (0, confidence_1.updateMemoryConfidence)(memory, this.config);
        return memory;
    }
    /**
     * Refresh confidence calculation for a memory
     * Called automatically on retrieval to account for time decay
     *
     * @param memory - Memory to refresh
     * @returns Memory with updated confidence
     */
    refreshConfidence(memory) {
        const oldConfidence = memory.metadata.confidence || 0;
        (0, confidence_1.updateMemoryConfidence)(memory, this.config);
        // Update timestamp only if confidence changed significantly
        const newConfidence = memory.metadata.confidence || 0;
        if (Math.abs(oldConfidence - newConfidence) > 0.001) {
            memory.metadata.updatedAt = new Date().toISOString();
        }
        return memory;
    }
    /**
     * Query memories with filtering by minimum confidence threshold
     *
     * @param options - Query options including minConfidence
     * @returns Array of memories matching criteria
     */
    query(options = {}) {
        let results = Array.from(this.memories.values());
        // Refresh confidence on all results
        results.forEach(m => this.refreshConfidence(m));
        // Filter by minimum confidence
        if (options.minConfidence !== undefined) {
            results = results.filter(m => (m.metadata.confidence || 0) >= options.minConfidence);
        }
        // Filter by source
        if (options.source !== undefined) {
            results = results.filter(m => m.metadata.source === options.source);
        }
        // Filter by tags (must have all specified tags)
        if (options.tags !== undefined && options.tags.length > 0) {
            results = results.filter(m => options.tags.every(tag => m.metadata.tags?.includes(tag)));
        }
        // Filter by sensitive flag
        if (options.sensitive !== undefined) {
            results = results.filter(m => m.sensitive === options.sensitive);
        }
        // Text search (basic contains match)
        if (options.text !== undefined && options.text.length > 0) {
            const searchText = options.text.toLowerCase();
            results = results.filter(m => m.content.toLowerCase().includes(searchText));
        }
        // Sort by confidence (descending) by default if no sort specified
        results.sort((a, b) => (b.metadata.confidence || 0) - (a.metadata.confidence || 0));
        // Apply offset
        if (options.offset !== undefined && options.offset > 0) {
            results = results.slice(options.offset);
        }
        // Apply limit
        if (options.limit !== undefined && options.limit > 0) {
            results = results.slice(0, options.limit);
        }
        return results;
    }
    /**
     * Get all memories
     * @returns Array of all memories
     */
    getAll() {
        const memories = Array.from(this.memories.values());
        memories.forEach(m => this.refreshConfidence(m));
        return memories;
    }
    /**
     * Delete a memory
     * @param id - Memory ID to delete
     * @returns True if deleted, false if not found
     */
    delete(id) {
        return this.memories.delete(id);
    }
    /**
     * Get count of memories
     * @returns Number of stored memories
     */
    count() {
        return this.memories.size;
    }
    /**
     * Clear all memories
     */
    clear() {
        this.memories.clear();
    }
    /**
     * Get statistics about memories
     */
    getStats() {
        const memories = this.getAll();
        const bySource = {
            user_explicit: 0,
            inferred: 0,
            auto_extracted: 0,
        };
        let totalConfidence = 0;
        let minConfidence = 1;
        let maxConfidence = 0;
        let withFeedback = 0;
        for (const memory of memories) {
            const source = memory.metadata.source || 'auto_extracted';
            bySource[source]++;
            const confidence = memory.metadata.confidence || 0;
            totalConfidence += confidence;
            minConfidence = Math.min(minConfidence, confidence);
            maxConfidence = Math.max(maxConfidence, confidence);
            if (memory.metadata.feedback !== null && memory.metadata.feedback !== undefined) {
                withFeedback++;
            }
        }
        return {
            total: memories.length,
            bySource,
            averageConfidence: memories.length > 0 ? totalConfidence / memories.length : 0,
            minConfidence: memories.length > 0 ? minConfidence : 0,
            maxConfidence: memories.length > 0 ? maxConfidence : 0,
            withFeedback,
        };
    }
}
exports.MemoryStore = MemoryStore;
//# sourceMappingURL=store.js.map