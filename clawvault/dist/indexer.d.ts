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
export declare class IncrementalIndexer {
    private entries;
    private typeIndex;
    private scopeIndex;
    private tagIndex;
    private timeIndex;
    private pendingUpdates;
    private lastIndexed;
    constructor();
    index(entry: MemoryEntry): void;
    remove(id: string): boolean;
    get(id: string): MemoryEntry | undefined;
    getByType(type: MemoryType): MemoryEntry[];
    getByScope(scope: MemoryScope): MemoryEntry[];
    getByTags(tags: string[]): MemoryEntry[];
    getByTimeRange(start: number, end: number): MemoryEntry[];
    getRecent(limit?: number): MemoryEntry[];
    getAll(): MemoryEntry[];
    private addToIndices;
    private removeFromIndices;
    getStats(): IndexStats;
    flushPending(): string[];
    searchByText(text: string): MemoryEntry[];
}
//# sourceMappingURL=indexer.d.ts.map