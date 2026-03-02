/**
 * Time-Decay Weighting Module
 * 
 * Applies exponential decay to memory scores based on age.
 * Configurable half-life per memory type.
 */

import { MemoryEntry, MemoryType } from './types';

export interface DecayConfig {
  /** Half-life in days; null = no decay */
  halfLifeDays: number | null;
}

export interface TypeDecayConfig {
  episodic: DecayConfig;      // Events fade fast
  declarative: DecayConfig;   // Facts persist longer
  semantic: DecayConfig;      // Knowledge decays slowly
  procedural: DecayConfig;    // How-to never fades
  working: DecayConfig;       // Working memory fades very fast
}

export interface DecayResult {
  originalScore: number;
  decayedScore: number;
  decayFactor: number;
  ageInDays: number;
  halfLifeDays: number | null;
}

// Default decay configuration
export const DEFAULT_DECAY_CONFIG: TypeDecayConfig = {
  episodic: { halfLifeDays: 15 },     // Events fade fast
  declarative: { halfLifeDays: 60 },  // Facts persist
  semantic: { halfLifeDays: 90 },     // Knowledge slow decay
  procedural: { halfLifeDays: null }, // How-to never fades
  working: { halfLifeDays: 7 }        // Working memory fades very fast
};

export class TimeDecayEngine {
  private config: TypeDecayConfig;

  constructor(config?: Partial<TypeDecayConfig>) {
    this.config = {
      ...DEFAULT_DECAY_CONFIG,
      ...config
    };
  }

  /**
   * Apply exponential decay to a score
   * Formula: decayed = original × e^(-λ × days)
   * where λ = ln(2) / halfLifeDays
   */
  applyDecay(
    score: number,
    createdAt: number,
    memoryType: MemoryType,
    now: number = Date.now()
  ): DecayResult {
    const config = this.config[memoryType];
    
    // No decay configured
    if (config.halfLifeDays === null) {
      return {
        originalScore: score,
        decayedScore: score,
        decayFactor: 1.0,
        ageInDays: 0,
        halfLifeDays: null
      };
    }

    const ageInDays = (now - createdAt) / (1000 * 60 * 60 * 24);
    const lambda = Math.log(2) / config.halfLifeDays!;
    const decayFactor = Math.exp(-lambda * ageInDays);
    const decayedScore = score * decayFactor;

    return {
      originalScore: score,
      decayedScore,
      decayFactor,
      ageInDays,
      halfLifeDays: config.halfLifeDays
    };
  }

  /**
   * Apply decay to multiple memories and sort by decayed score
   */
  applyAndSort<T extends { score: number; entry: MemoryEntry }>(
    items: T[],
    now: number = Date.now()
  ): Array<T & { decayInfo: DecayResult }> {
    const enriched = items.map(item => {
      const decayInfo = this.applyDecay(
        item.score,
        item.entry.createdAt || item.entry.timestamp,
        item.entry.type,
        now
      );
      
      return {
        ...item,
        decayedScore: decayInfo.decayedScore,
        decayInfo
      };
    });

    // Sort by decayed score descending
    return enriched.sort((a, b) => b.decayedScore - a.decayedScore);
  }

  /**
   * Get decay factor for a single memory (no modification)
   */
  getDecayFactor(memory: MemoryEntry, now: number = Date.now()): number {
    const result = this.applyDecay(
      1.0,
      memory.createdAt || memory.timestamp,
      memory.type,
      now
    );
    return result.decayFactor;
  }

  /**
   * Calculate adjusted confidence for a memory
   * Combines base confidence with time decay
   */
  calculateAdjustedConfidence(
    baseConfidence: number,
    memory: MemoryEntry,
    now: number = Date.now()
  ): number {
    const decayFactor = this.getDecayFactor(memory, now);
    return baseConfidence * decayFactor;
  }

  /**
   * Batch process memories with decay
   * Returns statistics about decay distribution
   */
  batchAnalyze(memories: MemoryEntry[], now: number = Date.now()): {
    totalMemories: number;
    averageDecayFactor: number;
    byType: Record<string, { count: number; avgDecay: number }>;
    heavilyDecayed: number;      // decayFactor < 0.5
    moderatelyDecayed: number;   // decayFactor 0.5-0.8
    lightlyDecayed: number;      // decayFactor > 0.8
  } {
    const byType: Record<string, { scores: number[] }> = {};
    let totalDecay = 0;
    let heavilyDecayed = 0;
    let moderatelyDecayed = 0;
    let lightlyDecayed = 0;

    for (const memory of memories) {
      const decayFactor = this.getDecayFactor(memory, now);
      totalDecay += decayFactor;

      const type = memory.type;
      if (!byType[type]) {
        byType[type] = { scores: [] };
      }
      byType[type].scores.push(decayFactor);

      if (decayFactor < 0.5) heavilyDecayed++;
      else if (decayFactor < 0.8) moderatelyDecayed++;
      else lightlyDecayed++;
    }

    const byTypeStats: Record<string, { count: number; avgDecay: number }> = {};
    for (const [type, data] of Object.entries(byType)) {
      byTypeStats[type] = {
        count: data.scores.length,
        avgDecay: data.scores.reduce((a, b) => a + b, 0) / data.scores.length
      };
    }

    return {
      totalMemories: memories.length,
      averageDecayFactor: totalDecay / memories.length,
      byType: byTypeStats,
      heavilyDecayed,
      moderatelyDecayed,
      lightlyDecayed
    };
  }

  /**
   * Update configuration at runtime
   */
  updateConfig(type: MemoryType, halfLifeDays: number | null): void {
    this.config[type] = { halfLifeDays };
  }

  /**
   * Reset to default configuration
   */
  resetToDefaults(): void {
    this.config = { ...DEFAULT_DECAY_CONFIG };
  }

  /**
   * Get current configuration
   */
  getConfig(): TypeDecayConfig {
    return { ...this.config };
  }

  /**
   * Estimate when a memory will reach a certain decay threshold
   */
  estimateThresholdDate(
    memory: MemoryEntry,
    threshold: number,
    now: number = Date.now()
  ): number | null {
    const config = this.config[memory.type];
    
    if (config.halfLifeDays === null) return null;

    const currentFactor = this.getDecayFactor(memory, now);
    
    // If already below threshold, return current time
    if (currentFactor <= threshold) return now;

    // Solve: e^(-λ × days) = threshold / currentFactor
    // days = ln(threshold / currentFactor) / -λ
    const lambda = Math.log(2) / config.halfLifeDays!;
    const daysUntilThreshold = Math.log(threshold / currentFactor) / -lambda;

    return now + (daysUntilThreshold * 24 * 60 * 60 * 1000);
  }
}

// Export helper for search integration
export function createDecayConfig(overrides?: Partial<TypeDecayConfig>): TypeDecayConfig {
  return {
    ...DEFAULT_DECAY_CONFIG,
    ...overrides
  };
}
