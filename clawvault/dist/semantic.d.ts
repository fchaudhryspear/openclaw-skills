/**
 * Phase 1: Semantic Layer
 * Extracts semantic meaning from memory content
 */
import { SemanticLayer } from './types';
export declare class SemanticLayerBuilder {
    private categories;
    build(content: string): SemanticLayer;
    private extractEntities;
    private extractConcepts;
    private determineCategory;
    private analyzeSentiment;
    private assessImportance;
}
//# sourceMappingURL=semantic.d.ts.map