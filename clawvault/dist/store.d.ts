/**
 * ClawVault Memory Store
 *
 * Core memory management with confidence scoring
 */
import { Memory, MemoryInput, MemoryQuery, MemorySource, UserFeedback, ConfidenceConfig } from './types';
/**
 * Memory Store class with confidence scoring
 */
export declare class MemoryStore {
    private memories;
    private config;
    /**
     * Create a new MemoryStore
     * @param config - Optional custom confidence configuration
     */
    constructor(config?: Partial<ConfidenceConfig>);
    /**
     * Store a new memory with calculated confidence
     *
     * @param input - Memory input data
     * @returns The stored memory with confidence score
     */
    store(input: MemoryInput): Memory;
    /**
     * Store a memory with explicit ID (for loading from storage)
     *
     * @param memory - Complete memory object
     * @returns The stored memory
     */
    storeWithId(memory: Memory): Memory;
    /**
     * Get a memory by ID
     *
     * @param id - Memory ID
     * @returns The memory or undefined if not found
     */
    get(id: string): Memory | undefined;
    /**
     * Update user feedback on a memory and recalculate confidence
     *
     * @param id - Memory ID
     * @param feedback - User feedback ('thumbs_up' or 'thumbs_down')
     * @returns Updated memory or undefined if not found
     */
    setFeedback(id: string, feedback: UserFeedback): Memory | undefined;
    /**
     * Refresh confidence calculation for a memory
     * Called automatically on retrieval to account for time decay
     *
     * @param memory - Memory to refresh
     * @returns Memory with updated confidence
     */
    private refreshConfidence;
    /**
     * Query memories with filtering by minimum confidence threshold
     *
     * @param options - Query options including minConfidence
     * @returns Array of memories matching criteria
     */
    query(options?: MemoryQuery): Memory[];
    /**
     * Get all memories
     * @returns Array of all memories
     */
    getAll(): Memory[];
    /**
     * Delete a memory
     * @param id - Memory ID to delete
     * @returns True if deleted, false if not found
     */
    delete(id: string): boolean;
    /**
     * Get count of memories
     * @returns Number of stored memories
     */
    count(): number;
    /**
     * Clear all memories
     */
    clear(): void;
    /**
     * Get statistics about memories
     */
    getStats(): {
        total: number;
        bySource: Record<MemorySource, number>;
        averageConfidence: number;
        minConfidence: number;
        maxConfidence: number;
        withFeedback: number;
    };
}
//# sourceMappingURL=store.d.ts.map