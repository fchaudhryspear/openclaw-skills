export declare class ClawVault {
    constructor();
    /**
     * Add a memory entry with validation
     * @param {string} key - Unique identifier for the memory
     * @param {string} value - Content of the memory
     * @returns {string} - Memory ID
     */
    addMemory(key: any, value: any): any;
    /**
     * Query memories by key
     * @param {string} key - Key to search for
     * @returns {object[]} - Matching memories
     */
    queryMemories(key: any): any;
    /**
     * List all memories
     * @returns {object[]} - All memories
     */
    listMemories(): any[];
    /**
     * Delete a memory by ID
     * @param {string} id - Memory ID to delete
     */
    deleteMemory(id: any): void;
    /**
     * Update a memory by ID
     * @param {string} id - Memory ID to update
     * @param {string} value - New content for the memory
     */
    updateMemory(id: any, value: any): void;
    /**
     * Search memories by content
     * @param {string} query - Search term
     * @returns {object[]} - Matching memories
     */
    searchMemories(query: any): any;
}
//# sourceMappingURL=index.d.ts.map