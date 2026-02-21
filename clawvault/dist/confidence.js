"use strict";
/**
 * Phase 1: Confidence Scoring
 * Calculates confidence scores for memory entries
 */
Object.defineProperty(exports, "__esModule", { value: true });
exports.ConfidenceScorer = void 0;
class ConfidenceScorer {
    VERIFICATION_WEIGHT = 0.3;
    SOURCE_WEIGHT = 0.25;
    CONSISTENCY_WEIGHT = 0.2;
    AGE_WEIGHT = 0.15;
    ACCESS_WEIGHT = 0.1;
    calculate(entry) {
        const factors = {
            sourceReliability: this.scoreSourceReliability(entry.metadata),
            consistency: this.scoreConsistency(entry),
            verificationStatus: this.scoreVerification(entry),
            age: this.scoreAge(entry.timestamp),
            accessPatterns: this.scoreAccessPatterns(entry.metadata)
        };
        const overall = factors.sourceReliability * this.SOURCE_WEIGHT +
            factors.consistency * this.CONSISTENCY_WEIGHT +
            factors.verificationStatus * this.VERIFICATION_WEIGHT +
            factors.age * this.AGE_WEIGHT +
            factors.accessPatterns * this.ACCESS_WEIGHT;
        return {
            overall: Math.round(overall * 100) / 100,
            factors: {
                sourceReliability: Math.round(factors.sourceReliability * 100) / 100,
                consistency: Math.round(factors.consistency * 100) / 100,
                verificationStatus: Math.round(factors.verificationStatus * 100) / 100,
                age: Math.round(factors.age * 100) / 100,
                accessPatterns: Math.round(factors.accessPatterns * 100) / 100
            }
        };
    }
    scoreSourceReliability(metadata) {
        const sourceScores = {
            'user_explicit': 1.0,
            'user_implicit': 0.8,
            'system_inferred': 0.6,
            'external_api': 0.7,
            'unknown': 0.4
        };
        return sourceScores[metadata.source || 'unknown'] || 0.5;
    }
    scoreConsistency(entry) {
        // Check relationships and semantic coherence
        const hasRelationships = entry.metadata.relationships.length > 0;
        const hasSemanticLayer = entry.semanticLayer.concepts.length > 0;
        const hasEntities = entry.semanticLayer.entities.length > 0;
        let score = 0.5;
        if (hasRelationships)
            score += 0.2;
        if (hasSemanticLayer)
            score += 0.15;
        if (hasEntities)
            score += 0.15;
        return Math.min(score, 1.0);
    }
    scoreVerification(entry) {
        // Higher version = more verified/updated
        const versionBoost = Math.min((entry.version - 1) * 0.1, 0.3);
        // Semantic layer completeness
        const semanticScore = Math.min((entry.semanticLayer.entities.length + entry.semanticLayer.concepts.length) / 10, 0.5);
        return Math.min(0.5 + versionBoost + semanticScore, 1.0);
    }
    scoreAge(timestamp) {
        const age = Date.now() - timestamp;
        const oneDay = 24 * 60 * 60 * 1000;
        const oneMonth = 30 * oneDay;
        if (age < oneDay)
            return 1.0;
        if (age < oneWeek())
            return 0.9;
        if (age < oneMonth)
            return 0.8;
        if (age < 3 * oneMonth)
            return 0.7;
        if (age < 6 * oneMonth)
            return 0.6;
        return 0.5;
        function oneWeek() { return 7 * oneDay; }
    }
    scoreAccessPatterns(metadata) {
        const accessCount = metadata.accessCount;
        const recency = Date.now() - metadata.lastAccessed;
        const oneDay = 24 * 60 * 60 * 1000;
        // More accesses = higher confidence (validated usefulness)
        let score = Math.min(accessCount / 10, 0.5);
        // Recent access boosts confidence
        if (recency < oneDay)
            score += 0.3;
        else if (recency < 7 * oneDay)
            score += 0.2;
        else if (recency < 30 * oneDay)
            score += 0.1;
        return Math.min(score + 0.2, 1.0);
    }
    shouldPromote(confidence) {
        return confidence >= 0.7;
    }
    shouldReview(confidence) {
        return confidence < 0.4;
    }
}
exports.ConfidenceScorer = ConfidenceScorer;
//# sourceMappingURL=confidence.js.map