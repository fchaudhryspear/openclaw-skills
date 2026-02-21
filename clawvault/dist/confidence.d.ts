/**
 * Phase 1: Confidence Scoring
 * Calculates confidence scores for memory entries
 */
import { ConfidenceScore, MemoryEntry } from './types';
export declare class ConfidenceScorer {
    private readonly VERIFICATION_WEIGHT;
    private readonly SOURCE_WEIGHT;
    private readonly CONSISTENCY_WEIGHT;
    private readonly AGE_WEIGHT;
    private readonly ACCESS_WEIGHT;
    calculate(entry: MemoryEntry): ConfidenceScore;
    private scoreSourceReliability;
    private scoreConsistency;
    private scoreVerification;
    private scoreAge;
    private scoreAccessPatterns;
    shouldPromote(confidence: number): boolean;
    shouldReview(confidence: number): boolean;
}
//# sourceMappingURL=confidence.d.ts.map