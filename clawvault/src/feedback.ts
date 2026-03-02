/**
 * Memory Feedback Loop Module
 * 
 * Learn from user feedback to improve relevance over time.
 * Supports thumbs up/down, pinning, and immediate deletion.
 */

import { ClawVault, MemoryEntry } from './index.js';

export type FeedbackType = 'thumbs_up' | 'thumbs_down' | 'pin' | 'unpin' | 'delete';

export interface FeedbackRecord {
  type: FeedbackType;
  timestamp: number;
  context?: string;
  userId?: string;
}

export interface MemoryWithFeedback extends MemoryEntry {
  feedback?: FeedbackRecord[];
  isPinned?: boolean;
  lastFeedbackAt?: number;
}

export interface FeedbackStats {
  totalMemories: number;
  withThumbsUp: number;
  withThumbsDown: number;
  pinned: number;
  averageConfidenceBoost: number;
  lowValueRecommendations: number;
}

export class FeedbackManager {
  private vault: ClawVault;
  
  // Confidence adjustment constants
  private readonly THUMBS_UP_BOOST = 0.1;
  private readonly THUMBS_DOWN_PENALTY = 0.2;
  private readonly MAX_CONFIDENCE = 1.0;
  private readonly MIN_CONFIDENCE = 0.0;

  constructor(vault: ClawVault) {
    this.vault = vault;
  }

  /**
   * Record thumbs up - increases confidence by +0.1
   */
  async thumbsUp(memoryId: string, context?: string): Promise<boolean> {
    const memory = await this.getMemoryById(memoryId);
    if (!memory) return false;

    const feedback: FeedbackRecord = {
      type: 'thumbs_up',
      timestamp: Date.now(),
      context
    };

    await this.addFeedback(memoryId, feedback);
    await this.adjustConfidence(memoryId, this.THUMBS_UP_BOOST);

    console.log(`✅ Thumbs up recorded for ${memoryId} (+${this.THUMBS_UP_BOOST} confidence)`);
    return true;
  }

  /**
   * Record thumbs down - decreases confidence by -0.2
   */
  async thumbsDown(memoryId: string, context?: string): Promise<boolean> {
    const memory = await this.getMemoryById(memoryId);
    if (!memory) return false;

    const feedback: FeedbackRecord = {
      type: 'thumbs_down',
      timestamp: Date.now(),
      context
    };

    await this.addFeedback(memoryId, feedback);
    await this.adjustConfidence(memoryId, -this.THUMBS_DOWN_PENALTY);

    console.log(`👎 Thumbs down recorded for ${memoryId} (-${this.THUMBS_DOWN_PENALTY} confidence)`);
    return true;
  }

  /**
   * Pin a memory - exempts it from pruning
   */
  async pin(memoryId: string): Promise<boolean> {
    const memory = await this.getMemoryById(memoryId);
    if (!memory) return false;

    const feedback: FeedbackRecord = {
      type: 'pin',
      timestamp: Date.now()
    };

    await this.addFeedback(memoryId, feedback);
    
    // Set special flag that pruner will check
    await this.vault.setMemoryAttribute(memoryId, 'isPinned', true);

    console.log(`⭐ Pinned ${memoryId} (exempt from pruning)`);
    return true;
  }

  /**
   * Unpin a memory
   */
  async unpin(memoryId: string): Promise<boolean> {
    const memory = await this.getMemoryById(memoryId);
    if (!memory) return false;

    const feedback: FeedbackRecord = {
      type: 'unpin',
      timestamp: Date.now()
    };

    await this.addFeedback(memoryId, feedback);
    await this.vault.setMemoryAttribute(memoryId, 'isPinned', false);

    console.log(`🔓 Unpinned ${memoryId}`);
    return true;
  }

  /**
   * Delete a memory immediately (bypasses normal pruning)
   */
  async delete(memoryId: string, reason?: string): Promise<boolean> {
    const memory = await this.getMemoryById(memoryId);
    if (!memory) return false;

    const feedback: FeedbackRecord = {
      type: 'delete',
      timestamp: Date.now(),
      context: reason
    };

    await this.addFeedback(memoryId, feedback);
    await this.vault.deleteMemory(memoryId);

    console.log(`🗑️ Deleted ${memoryId}${reason ? ` (${reason})` : ''}`);
    return true;
  }

  /**
   * Add feedback record to memory metadata
   */
  private async addFeedback(memoryId: string, feedback: FeedbackRecord): Promise<void> {
    // Get current feedback array
    const currentFeedback = await this.getMemoryFeedback(memoryId);
    
    // Append new feedback
    currentFeedback.push(feedback);
    
    // Save back to memory
    await this.vault.setMemoryAttribute(memoryId, 'feedback', currentFeedback);
    await this.vault.setMemoryAttribute(memoryId, 'lastFeedbackAt', feedback.timestamp);
  }

  /**
   * Adjust confidence score based on feedback
   */
  private async adjustConfidence(memoryId: string, delta: number): Promise<void> {
    const memory = await this.getMemoryById(memoryId);
    if (!memory) return;

    const newConfidence = Math.max(
      this.MIN_CONFIDENCE,
      Math.min(this.MAX_CONFIDENCE, memory.confidence + delta)
    );

    await this.vault.updateMemory(memoryId, { confidence: newConfidence });
  }

  /**
   * Get all feedback for a memory
   */
  private async getMemoryFeedback(memoryId: string): Promise<FeedbackRecord[]> {
    const memory = await this.getMemoryById(memoryId);
    return memory?.feedback || [];
  }

  /**
   * Check if memory is pinned
   */
  async isPinned(memoryId: string): Promise<boolean> {
    const memory = await this.getMemoryById(memoryId);
    return !!memory?.isPinned;
  }

  /**
   * Get pinned memories
   */
  async getPinnedMemories(): Promise<MemoryEntry[]> {
    const allMemories = this.vault.getAllMemories();
    return allMemories.filter(m => m.isPinned === true);
  }

  /**
   * Get memory with full feedback data
   */
  private async getMemoryById(memoryId: string): Promise<MemoryWithFeedback | null> {
    try {
      const entry = await this.vault.getMemory(memoryId);
      if (!entry) return null;

      return {
        ...entry,
        feedback: await this.getMemoryFeedback(memoryId),
        isPinned: await this.isPinned(memoryId),
        lastFeedbackAt: entry.lastFeedbackAt
      };
    } catch {
      return null;
    }
  }

  /**
   * Get comprehensive feedback statistics
   */
  async getStats(): Promise<FeedbackStats> {
    const allMemories = this.vault.getAllMemories();
    
    let thumbsUp = 0;
    let thumbsDown = 0;
    let pinned = 0;
    let totalBoost = 0;
    let boostCount = 0;

    for (const memory of allMemories) {
      const feedback = await this.getMemoryFeedback(memory.id);
      
      const upCount = feedback.filter(f => f.type === 'thumbs_up').length;
      const downCount = feedback.filter(f => f.type === 'thumbs_down').length;
      
      if (upCount > 0) thumbsUp++;
      if (downCount > 0) thumbsDown++;
      
      if (memory.isPinned) pinned++;
      
      // Track net confidence changes
      const netChange = (upCount * this.THUMBS_UP_BOOST) - (downCount * this.THUMBS_DOWN_PENALTY);
      if (netChange !== 0) {
        totalBoost += netChange;
        boostCount++;
      }
    }

    return {
      totalMemories: allMemories.length,
      withThumbsUp: thumbsUp,
      withThumbsDown: thumbsDown,
      pinned,
      averageConfidenceBoost: boostCount > 0 ? totalBoost / boostCount : 0,
      lowValueRecommendations: 0 // Will calculate in recommendLowValue()
    };
  }

  /**
   * Recommend low-value memories for review/deletion
   * Based on repeated thumbs_down, low confidence, no access
   */
  async recommendLowValue(limit: number = 20): Promise<MemoryEntry[]> {
    const allMemories = this.vault.getAllMemories();
    const now = Date.now();
    const recommendations: Array<{ memory: MemoryEntry; score: number }> = [];

    for (const memory of allMemories) {
      const feedback = await this.getMemoryFeedback(memory.id);
      
      // Skip pinned memories
      if (memory.isPinned) continue;

      let score = 0;
      
      // Heavy penalty for thumbs down
      const thumbsDown = feedback.filter(f => f.type === 'thumbs_down').length;
      score -= thumbsDown * 2;
      
      // Boost for thumbs up (don't recommend)
      const thumbsUp = feedback.filter(f => f.type === 'thumbs_up').length;
      score += thumbsUp * 1.5;
      
      // Low confidence penalty
      if (memory.confidence < 0.3) score -= 1;
      
      // Old and never accessed penalty
      const createdTime = memory.createdAt || memory.timestamp || now;
      const ageInDays = (now - createdTime) / (1000 * 60 * 60 * 24);
      if ((memory.accessCount || 0) === 0 && ageInDays > 90) score -= 0.5;
      
      // Recently added boost (give new memories time)
      if (ageInDays < 7) score += 2;

      if (score < -1) { // Threshold for recommendation
        recommendations.push({ memory, score });
      }
    }

    return recommendations
      .sort((a, b) => a.score - b.score)
      .slice(0, limit)
      .map(r => r.memory);
  }

  /**
   * Analyze feedback patterns to identify improvement areas
   */
  async analyzePatterns(): Promise<{
    commonNegativeContexts: Array<{ pattern: string; count: number }>;
    avgFeedbackPerMemory: number;
    feedbackTrend: 'improving' | 'stable' | 'declining';
  }> {
    const allMemories = this.vault.getAllMemories();
    const negativeContexts: Map<string, number> = new Map();
    let totalFeedback = 0;

    const thirtyDaysAgo = Date.now() - (30 * 24 * 60 * 60 * 1000);
    let recentUp = 0;
    let recentDown = 0;

    for (const memory of allMemories) {
      const feedback = await this.getMemoryFeedback(memory.id);
      totalFeedback += feedback.length;

      for (const f of feedback) {
        if (f.type === 'thumbs_down' && f.context) {
          // Extract simple pattern from context
          const pattern = f.context.split(' ').slice(0, 3).join(' ');
          negativeContexts.set(pattern, (negativeContexts.get(pattern) || 0) + 1);
        }

        // Trend analysis (last 30 days)
        if (f.timestamp > thirtyDaysAgo) {
          if (f.type === 'thumbs_up') recentUp++;
          if (f.type === 'thumbs_down') recentDown++;
        }
      }
    }

    const topPatterns = Array.from(negativeContexts.entries())
      .sort((a, b) => b[1] - a[1])
      .slice(0, 5)
      .map(([pattern, count]) => ({ pattern, count }));

    const avgFeedback = allMemories.length > 0 ? totalFeedback / allMemories.length : 0;
    
    const trend = recentDown > recentUp * 1.5 
      ? 'declining' 
      : recentUp > recentDown * 1.5 
        ? 'improving' 
        : 'stable';

    return {
      commonNegativeContexts: topPatterns,
      avgFeedbackPerMemory: avgFeedback,
      feedbackTrend: trend
    };
  }

  /**
   * Export feedback data for external analysis
   */
  async exportData(): Promise<Array<{
    id: string;
    content: string;
    type: string;
    confidence: number;
    feedback: FeedbackRecord[];
  }>> {
    const allMemories = this.vault.getAllMemories();
    const exports = [];

    for (const memory of allMemories) {
      const feedback = await this.getMemoryFeedback(memory.id);
      exports.push({
        id: memory.id,
        content: memory.content,
        type: memory.type,
        confidence: memory.confidence,
        feedback
      });
    }

    return exports;
  }
}
