/**
 * Tests for MemoryStore
 * 
 * Tests memory storage, confidence calculation, querying, and feedback.
 */

const { describe, it, beforeEach } = require('node:test');
const assert = require('node:assert');

const { MemoryStore } = require('../dist/store');

describe('MemoryStore', () => {
  let store;

  beforeEach(() => {
    store = new MemoryStore();
  });

  describe('store', () => {
    it('should store a memory with calculated confidence', () => {
      const memory = store.store({
        content: 'User prefers dark mode',
        source: 'user_explicit',
      });

      assert.ok(memory.id);
      assert.strictEqual(memory.content, 'User prefers dark mode');
      assert.strictEqual(memory.metadata.source, 'user_explicit');
      assert.ok(Math.abs(memory.metadata.confidence - 1.0) < 0.0001, `Expected ~1.0, got ${memory.metadata.confidence}`);
      assert.ok(memory.metadata.createdAt);
      assert.ok(memory.metadata.updatedAt);
    });

    it('should store memory with tags', () => {
      const memory = store.store({
        content: 'User likes coffee',
        source: 'inferred',
        tags: ['preferences', 'food'],
      });

      assert.deepStrictEqual(memory.metadata.tags, ['preferences', 'food']);
    });

    it('should default to auto_extracted source', () => {
      const memory = store.store({
        content: 'Some extracted fact',
      });

      assert.strictEqual(memory.metadata.source, 'auto_extracted');
      assert.strictEqual(memory.metadata.confidence, 0.5);
    });

    it('should calculate lower confidence for inferred source', () => {
      const memory = store.store({
        content: 'User probably likes tea',
        source: 'inferred',
      });

      assert.strictEqual(memory.metadata.confidence, 0.7);
    });
  });

  describe('get', () => {
    it('should retrieve a memory by id', () => {
      const stored = store.store({
        content: 'Test memory',
        source: 'user_explicit',
      });

      const retrieved = store.get(stored.id);

      assert.ok(retrieved);
      assert.strictEqual(retrieved.id, stored.id);
      assert.strictEqual(retrieved.content, 'Test memory');
    });

    it('should return undefined for non-existent id', () => {
      const result = store.get('non-existent-id');
      assert.strictEqual(result, undefined);
    });

    it('should refresh confidence on retrieval', () => {
      // This is harder to test without mocking time
      // But we can verify the memory is returned with confidence
      const stored = store.store({
        content: 'Test memory',
        source: 'user_explicit',
      });

      const retrieved = store.get(stored.id);
      assert.ok(typeof retrieved.metadata.confidence === 'number');
    });
  });

  describe('setFeedback', () => {
    it('should update feedback and recalculate confidence', () => {
      const memory = store.store({
        content: 'User likes pizza',
        source: 'inferred',
      });

      assert.strictEqual(memory.metadata.confidence, 0.7);

      const updated = store.setFeedback(memory.id, 'thumbs_up');

      assert.ok(updated);
      assert.strictEqual(updated.metadata.feedback, 'thumbs_up');
      assert.ok(Math.abs(updated.metadata.confidence - 0.8) < 0.0001); // ~0.8
    });

    it('should decrease confidence with thumbs_down', () => {
      const memory = store.store({
        content: 'Wrong fact',
        source: 'user_explicit',
      });

      const updated = store.setFeedback(memory.id, 'thumbs_down');

      assert.ok(Math.abs(updated.metadata.confidence - 0.8) < 0.0001); // ~0.8
    });

    it('should return undefined for non-existent memory', () => {
      const result = store.setFeedback('non-existent', 'thumbs_up');
      assert.strictEqual(result, undefined);
    });
  });

  describe('query with minConfidence', () => {
    beforeEach(() => {
      // Create memories with different confidence levels
      store.store({ content: 'High confidence fact', source: 'user_explicit' }); // 1.0
      store.store({ content: 'Medium confidence', source: 'inferred' }); // 0.7
      store.store({ content: 'Low confidence', source: 'auto_extracted' }); // 0.5
    });

    it('should filter by minimum confidence', () => {
      const highConfidence = store.query({ minConfidence: 0.8 });
      
      assert.strictEqual(highConfidence.length, 1);
      assert.strictEqual(highConfidence[0].content, 'High confidence fact');
    });

    it('should return memories above threshold', () => {
      const mediumAndAbove = store.query({ minConfidence: 0.6 });
      
      assert.strictEqual(mediumAndAbove.length, 2);
    });

    it('should return all memories when threshold is 0', () => {
      const all = store.query({ minConfidence: 0 });
      
      assert.strictEqual(all.length, 3);
    });

    it('should return empty array when threshold is too high', () => {
      const none = store.query({ minConfidence: 1.1 });
      
      assert.strictEqual(none.length, 0);
    });
  });

  describe('query with source filter', () => {
    beforeEach(() => {
      store.store({ content: 'Explicit 1', source: 'user_explicit' });
      store.store({ content: 'Explicit 2', source: 'user_explicit' });
      store.store({ content: 'Inferred 1', source: 'inferred' });
      store.store({ content: 'Auto 1', source: 'auto_extracted' });
    });

    it('should filter by source type', () => {
      const explicit = store.query({ source: 'user_explicit' });
      
      assert.strictEqual(explicit.length, 2);
      assert.ok(explicit.every(m => m.metadata.source === 'user_explicit'));
    });

    it('should filter by inferred source', () => {
      const inferred = store.query({ source: 'inferred' });
      
      assert.strictEqual(inferred.length, 1);
      assert.strictEqual(inferred[0].content, 'Inferred 1');
    });
  });

  describe('query with tags filter', () => {
    beforeEach(() => {
      store.store({ 
        content: 'Pref 1', 
        source: 'user_explicit',
        tags: ['preferences', 'ui'],
      });
      store.store({ 
        content: 'Pref 2', 
        source: 'user_explicit',
        tags: ['preferences'],
      });
      store.store({ 
        content: 'Fact 1', 
        source: 'inferred',
        tags: ['facts'],
      });
    });

    it('should filter by single tag', () => {
      const preferences = store.query({ tags: ['preferences'] });
      
      assert.strictEqual(preferences.length, 2);
    });

    it('should filter by multiple tags (AND)', () => {
      const uiPrefs = store.query({ tags: ['preferences', 'ui'] });
      
      assert.strictEqual(uiPrefs.length, 1);
      assert.strictEqual(uiPrefs[0].content, 'Pref 1');
    });

    it('should return empty for non-matching tags', () => {
      const none = store.query({ tags: ['nonexistent'] });
      
      assert.strictEqual(none.length, 0);
    });
  });

  describe('query with text search', () => {
    beforeEach(() => {
      store.store({ content: 'User likes dark mode', source: 'user_explicit' });
      store.store({ content: 'User prefers coffee', source: 'user_explicit' });
      store.store({ content: 'System configuration', source: 'auto_extracted' });
    });

    it('should search by text content', () => {
      const results = store.query({ text: 'user' });
      
      assert.strictEqual(results.length, 2);
    });

    it('should be case insensitive', () => {
      const results = store.query({ text: 'USER' });
      
      assert.strictEqual(results.length, 2);
    });

    it('should return all when text is empty', () => {
      const results = store.query({ text: '' });
      
      assert.strictEqual(results.length, 3);
    });
  });

  describe('query with limit and offset', () => {
    beforeEach(() => {
      for (let i = 0; i < 10; i++) {
        store.store({ 
          content: `Memory ${i}`, 
          source: 'user_explicit',
        });
      }
    });

    it('should limit results', () => {
      const limited = store.query({ limit: 3 });
      
      assert.strictEqual(limited.length, 3);
    });

    it('should apply offset', () => {
      const offset = store.query({ offset: 5 });
      
      assert.strictEqual(offset.length, 5);
    });

    it('should combine limit and offset', () => {
      const paginated = store.query({ offset: 3, limit: 3 });
      
      assert.strictEqual(paginated.length, 3);
    });
  });

  describe('getAll', () => {
    it('should return all memories', () => {
      store.store({ content: 'Memory 1', source: 'user_explicit' });
      store.store({ content: 'Memory 2', source: 'inferred' });

      const all = store.getAll();

      assert.strictEqual(all.length, 2);
    });

    it('should return empty array when no memories', () => {
      const all = store.getAll();

      assert.deepStrictEqual(all, []);
    });
  });

  describe('delete', () => {
    it('should delete a memory', () => {
      const memory = store.store({ content: 'To delete', source: 'user_explicit' });

      const deleted = store.delete(memory.id);

      assert.strictEqual(deleted, true);
      assert.strictEqual(store.get(memory.id), undefined);
    });

    it('should return false for non-existent memory', () => {
      const result = store.delete('non-existent');

      assert.strictEqual(result, false);
    });
  });

  describe('count', () => {
    it('should return number of memories', () => {
      assert.strictEqual(store.count(), 0);

      store.store({ content: '1', source: 'user_explicit' });
      assert.strictEqual(store.count(), 1);

      store.store({ content: '2', source: 'user_explicit' });
      assert.strictEqual(store.count(), 2);
    });
  });

  describe('clear', () => {
    it('should remove all memories', () => {
      store.store({ content: '1', source: 'user_explicit' });
      store.store({ content: '2', source: 'user_explicit' });

      store.clear();

      assert.strictEqual(store.count(), 0);
    });
  });

  describe('getStats', () => {
    it('should return statistics', () => {
      store.store({ content: '1', source: 'user_explicit' });
      store.store({ content: '2', source: 'inferred' });
      store.store({ content: '3', source: 'auto_extracted' });

      const stats = store.getStats();

      assert.strictEqual(stats.total, 3);
      assert.strictEqual(stats.bySource.user_explicit, 1);
      assert.strictEqual(stats.bySource.inferred, 1);
      assert.strictEqual(stats.bySource.auto_extracted, 1);
      assert.ok(stats.averageConfidence > 0);
      assert.ok(stats.minConfidence >= 0);
      assert.ok(stats.maxConfidence <= 1);
      assert.strictEqual(stats.withFeedback, 0);
    });

    it('should count memories with feedback', () => {
      const m1 = store.store({ content: '1', source: 'user_explicit' });
      store.store({ content: '2', source: 'user_explicit' });
      store.setFeedback(m1.id, 'thumbs_up');

      const stats = store.getStats();

      assert.strictEqual(stats.withFeedback, 1);
    });

    it('should handle empty store', () => {
      const stats = store.getStats();

      assert.strictEqual(stats.total, 0);
      assert.strictEqual(stats.averageConfidence, 0);
      assert.strictEqual(stats.minConfidence, 0);
      assert.strictEqual(stats.maxConfidence, 0);
    });
  });

  describe('custom confidence config', () => {
    it('should use custom config values', () => {
      const customStore = new MemoryStore({
        userExplicitBase: 0.95,
        inferredBase: 0.6,
        autoExtractedBase: 0.4,
        decay30Days: 0.6,
        decay90Days: 0.4,
        thumbsUpBonus: 0.15,
        thumbsDownPenalty: -0.25,
      });

      const memory = customStore.store({
        content: 'Test',
        source: 'user_explicit',
      });

      assert.strictEqual(memory.metadata.confidence, 0.95);
    });
  });
});
