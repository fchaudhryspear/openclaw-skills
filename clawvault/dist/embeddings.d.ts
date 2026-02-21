/**
 * Embedding Utilities
 * Generates vector representations for semantic search
 */
export declare function generateEmbedding(text: string): number[];
export declare function cosineSimilarity(a: number[], b: number[]): number;
export declare function tokenize(text: string): string[];
export declare function removeStopwords(tokens: string[]): string[];
export declare function calculateRecencyBoost(timestamp: number, halfLife?: number): number;
export declare function extractKeywords(text: string): string[];
//# sourceMappingURL=embeddings.d.ts.map