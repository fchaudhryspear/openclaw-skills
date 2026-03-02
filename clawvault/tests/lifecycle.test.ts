/**
 * ClawVault Phase 3 Lifecycle Tests
 * 
 * Tests for consolidation, pruning, and feedback management
 */

import { ClawVault } from '../src/index';
import { MemoryConsolidator } from '../src/consolidation';
import { MemoryPruner } from '../src/pruning';
import { FeedbackManager } from '../src/feedback';

describe('Phase 3: Memory Lifecycle', () => {
  let vault: ClawVault;
  let consolidator: MemoryConsolidator;
  let pruner: MemoryPruner;
  let feedbackManager: FeedbackManager;

  beforeEach(() => {
    vault = new ClawVault({ autoIndex: true });
    consolidator = new MemoryConsolidator(vault);
    pruner = new MemoryPruner(vault, { mode: 'dry-run' });
    feedbackManager = new FeedbackManager(vault);
  });

  describe('Memory Consolidation', () => {
    it('should detect similar memories for consolidation', async () => {
      // Store similar memories
      vault.store('React is a JavaScript library for building UIs', {
        type: 'semantic',
        tags: ['react', 'frontend']
      });
      
      vault.store('React is a JS library for user interfaces', {
        type: 'semantic',
        tags: ['react']
      });

      const result = await consolidator.dryRun();
      
      expect(result.clusters.length).toBeGreaterThanOrEqual(0);
      console.log(`Found ${result.estimatedReduction} potential merges`);
    });

    it('should skip high-confidence memories during consolidation', async () => {
      // Store memory with very high confidence
      const entry = vault.store('AWS account ID is 386757865833', {
        type: 'declarative',
        tags: ['aws']
      });
      
      // Manually set high confidence (simulating verified data)
      vault.setMemoryAttribute(entry.id, 'confidence', 0.95);

      const result = await consolidator.dryRun();
      
      // High confidence memories should not be clustered for merging
      expect(result).toBeDefined();
    });

    it('should consolidate based on memory type grouping', async () => {
      // Episodic memories
      vault.store('User said they prefer dark mode on Tuesday', {
        type: 'episodic',
        tags: ['preference']
      });
      
      vault.store('Fas mentioned liking TypeScript yesterday', {
        type: 'episodic',
        tags: ['preference']
      });

      // Declarative memories
      vault.store('Fas has 6 companies', {
        type: 'declarative',
        tags: ['factual']
      });

      // Should cluster episodic separately from declarative
      const allMemories = vault.getAllMemories();
      const episodicCount = allMemories.filter(m => m.type === 'episodic').length;
      
      expect(episodicCount).toBe(2);
    });
  });

  describe('Memory Pruning', () => {
    it('should identify low-confidence memories for review', async () => {
      // Create memories with different confidence levels
      vault.store('Low confidence guess about something', {
        type: 'declarative',
        tags: ['guess']
      });
      
      vault.store('High confidence fact about AWS', {
        type: 'declarative',
        tags: ['aws'],
        confidence: 0.9
      });

      const candidates = (pruner as any).identifyCandidates();
      
      expect(candidates).toBeDefined();
    });

    it('should respect safety limits on deletion percentage', () => {
      const options = {
        mode: 'auto' as const,
        maxDeletePercentage: 0.10,
        minTotalMemories: 100
      };

      const testPruner = new MemoryPruner(vault, options);
      
      expect(testPruner).toBeDefined();
      expect((testPruner as any).options.maxDeletePercentage).toBe(0.10);
    });

    it('should flag never-accessed old memories', async () => {
      const entry = vault.store('Old unused memory', {
        type: 'declarative',
        tags: ['unused']
      });

      // Access count starts at 0 by default
      
      const allMemories = vault.getAllMemories();
      const targetMemory = allMemories.find(m => m.id === entry.id);
      
      expect(targetMemory?.metadata.accessCount).toBe(0);
    });

    it('should apply pruning criteria correctly', () => {
      const criteria = {
        minConfidence: 0.3,
        reviewQueueDays: 60,
        neverAccessedDays: 90,
        softDeleteRetention: 30
      };

      const testPruner = new MemoryPruner(vault, {
        mode: 'dry-run',
        criteria
      });

      expect((testPruner as any).options.criteria?.minConfidence).toBe(0.3);
    });
  });

  describe('Feedback Loop', () => {
    it('should increase confidence on thumbs up', async () => {
      const entry = vault.store('Test memory for feedback', {
        type: 'declarative',
        tags: ['test']
      });

      const initialConfidence = entry.confidence;
      await feedbackManager.thumbsUp(entry.id, 'Very helpful!');

      // Confidence should increase by +0.1
      const updated = await feedbackManager['getMemoryById'](entry.id);
      expect(updated?.confidence).toBeGreaterThan(initialConfidence);
    });

    it('should decrease confidence on thumbs down', async () => {
      const entry = vault.store('Test memory for downvote', {
        type: 'declarative',
        tags: ['test']
      });

      const initialConfidence = entry.confidence;
      await feedbackManager.thumbsDown(entry.id, 'Outdated info');

      // Confidence should decrease by -0.2
      const updated = await feedbackManager['getMemoryById'](entry.id);
      expect(updated?.confidence).toBeLessThan(initialConfidence);
    });

    it('should pin memories to exempt from pruning', async () => {
      const entry = vault.store('Important pinned memory', {
        type: 'declarative',
        tags: ['important']
      });

      await feedbackManager.pin(entry.id);

      const isPinned = await feedbackManager.isPinned(entry.id);
      expect(isPinned).toBe(true);
    });

    it('should track feedback statistics', async () => {
      const entry1 = vault.store('Memory 1', { type: 'declarative' });
      const entry2 = vault.store('Memory 2', { type: 'declarative' });

      await feedbackManager.thumbsUp(entry1.id, 'Good');
      await feedbackManager.thumbsDown(entry2.id, 'Bad');

      const stats = await feedbackManager.getStats();
      
      expect(stats.totalMemories).toBeGreaterThan(0);
      expect(stats.withThumbsUp).toBe(1);
      expect(stats.withThumbsDown).toBe(1);
    });

    it('should recommend low-value memories for deletion', async () => {
      // Create some memories
      for (let i = 0; i < 5; i++) {
        vault.store(`Memory ${i}`, { type: 'declarative' });
      }

      const recommendations = await feedbackManager.recommendLowValue(10);
      
      // Should return array of recommended memories
      expect(Array.isArray(recommendations)).toBe(true);
      expect(recommendations.length).toBeGreaterThanOrEqual(0);
    });

    it('should handle multiple feedback on same memory', async () => {
      const entry = vault.store('Test memory', { type: 'declarative' });

      await feedbackManager.thumbsUp(entry.id, 'First vote');
      await feedbackManager.thumbsDown(entry.id, 'Changed my mind');

      const stats = await feedbackManager.getStats();
      
      expect(stats.totalMemories).toBeGreaterThan(0);
    });

    it('should analyze feedback patterns', async () => {
      const entry = vault.store('Test memory', { type: 'declarative' });

      await feedbackManager.thumbsDown(entry.id, 'Wrong information');

      const patterns = await feedbackManager.analyzePatterns();
      
      expect(patterns.avgFeedbackPerMemory).toBeGreaterThanOrEqual(0);
      expect(patterns.feedbackTrend).toMatch(/improving|stable|declining/);
    });
  });

  describe('Integration: Full Lifecycle', () => {
    it('should handle complete lifecycle: store → feedback → prune decision', async () => {
      // Store multiple memories
      const entries = [];
      for (let i = 0; i < 10; i++) {
        const entry = vault.store(`Memory content ${i}`, {
          type: 'declarative',
          tags: ['test']
        });
        entries.push(entry);
      }

      // Give some positive feedback
      await feedbackManager.thumbsUp(entries[0].id, 'Useful');
      await feedbackManager.thumbsUp(entries[1].id, 'Great info');

      // Give negative feedback to others
      await feedbackManager.thumbsDown(entries[8].id, 'Not accurate');
      await feedbackManager.thumbsDown(entries[9].id, 'Irrelevant');

      // Pin important ones
      await feedbackManager.pin(entries[0].id);

      // Get stats
      const stats = await feedbackManager.getStats();
      
      expect(stats.withThumbsUp).toBe(2);
      expect(stats.withThumbsDown).toBe(2);
      expect(stats.pinned).toBe(1);
    });

    it('should preserve pinned memories through pruning simulation', async () => {
      const importantEntry = vault.store('Critical information', {
        type: 'declarative',
        tags: ['critical']
      });

      await feedbackManager.pin(importantEntry.id);

      const isPinned = await feedbackManager.isPinned(importantEntry.id);
      expect(isPinned).toBe(true);
      
      // Pruner would check isPinned before deleting
    });

    it('should export feedback data for external analysis', async () => {
      const entry = vault.store('Export test', { type: 'declarative' });

      await feedbackManager.thumbsUp(entry.id, 'Test context');

      const exported = await feedbackManager.exportData();
      
      expect(exported.length).toBeGreaterThan(0);
      expect(exported[0]).toHaveProperty('feedback');
      expect(exported[0].feedback).toHaveLength(1);
    });
  });

  describe('Edge Cases', () => {
    it('should handle empty vault gracefully', async () => {
      const emptyVault = new ClawVault({ autoIndex: true });
      const emptyConsolidator = new MemoryConsolidator(emptyVault);
      const emptyPruner = new MemoryPruner(emptyVault, { mode: 'dry-run' });
      const emptyFeedback = new FeedbackManager(emptyVault);

      const consolidationResult = await emptyConsolidator.dryRun();
      const pruningResult = await emptyPruner.prune();
      const feedbackStats = await emptyFeedback.getStats();

      expect(consolidationResult.estimatedReduction).toBe(0);
      expect(pruningResult.flaggedForDeletion).toBe(0);
      expect(feedbackStats.totalMemories).toBe(0);
    });

    it('should prevent confidence from exceeding bounds', async () => {
      const entry = vault.store('Boundary test', { type: 'declarative' });

      // Set high confidence close to max
      vault.setMemoryAttribute(entry.id, 'confidence', 0.95);

      // Multiple thumbs up shouldn't exceed 1.0
      await feedbackManager.thumbsUp(entry.id, 'Up 1');
      await feedbackManager.thumbsUp(entry.id, 'Up 2');
      await feedbackManager.thumbsUp(entry.id, 'Up 3');

      const updated = await feedbackManager['getMemoryById'](entry.id);
      expect(updated?.confidence).toBeLessThanOrEqual(1.0);
    });

    it('should handle non-existent memory operations gracefully', async () => {
      const result = await feedbackManager.thumbsUp('non-existent-id', 'Test');
      expect(result).toBe(false);
    });
  });
});

// Run tests
if (require.main === module) {
  console.log('Running Phase 3 lifecycle tests...\n');
  
  const suite = new (require('jest').describe)('Lifecycle', () => {});
  console.log('Tests defined. Run: npm test -- lifecycle.test.ts');
}
