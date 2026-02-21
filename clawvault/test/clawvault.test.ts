/**
 * ClawVault Test Suite
 * Tests for Phase 1 and Phase 2 features
 */

import { ClawVault } from '../src/index';
import { MemoryType, MemoryScope, ContextMessage } from '../src/types';

describe('ClawVault', () => {
  let vault: ClawVault;

  beforeEach(() => {
    vault = new ClawVault({ enableSensitiveDetection: true });
  });

  afterEach(() => {
    vault.clear();
  });

  describe('Phase 1: Basic Memory Operations', () => {
    test('should store and retrieve a memory', () => {
      const entry = vault.store('Test memory content', {
        type: 'semantic',
        tags: ['test', 'memory']
      });

      expect(entry.id).toBeDefined();
      expect(entry.content).toBe('Test memory content');
      expect(entry.type).toBe('semantic');
      expect(entry.metadata.tags).toContain('test');

      const retrieved = vault.retrieve(entry.id);
      expect(retrieved).toBeDefined();
      expect(retrieved!.content).toBe('Test memory content');
    });

    test('should update a memory', () => {
      const entry = vault.store('Original content');
      const updated = vault.update(entry.id, { content: 'Updated content' });

      expect(updated).toBeDefined();
      expect(updated!.content).toBe('Updated content');
      expect(updated!.version).toBe(2);
    });

    test('should delete a memory', () => {
      const entry = vault.store('To be deleted');
      const deleted = vault.delete(entry.id);

      expect(deleted).toBe(true);
      expect(vault.retrieve(entry.id)).toBeUndefined();
    });

    test('should filter by type and scope', () => {
      vault.store('Episodic memory', { type: 'episodic', scope: 'user' });
      vault.store('Semantic memory', { type: 'semantic', scope: 'global' });
      vault.store('Procedural memory', { type: 'procedural', scope: 'session' });

      expect(vault.getByType('episodic')).toHaveLength(1);
      expect(vault.getByType('semantic')).toHaveLength(1);
      expect(vault.getByScope('global')).toHaveLength(1);
    });
  });

  describe('Phase 1: Confidence Scoring', () => {
    test('should calculate confidence score', () => {
      const entry = vault.store('High confidence memory', {
        source: 'user_explicit',
        tags: ['verified', 'important']
      });

      const confidence = vault.getConfidence(entry.id);
      expect(confidence).toBeDefined();
      expect(confidence!.overall).toBeGreaterThan(0);
      expect(confidence!.factors.sourceReliability).toBeGreaterThan(0);
    });

    test('should have lower confidence for unverified content', () => {
      const entry1 = vault.store('User explicit', { source: 'user_explicit' });
      const entry2 = vault.store('System inferred', { source: 'system_inferred' });

      const conf1 = vault.getConfidence(entry1.id)!;
      const conf2 = vault.getConfidence(entry2.id)!;

      expect(conf1.factors.sourceReliability).toBeGreaterThan(conf2.factors.sourceReliability);
    });
  });

  describe('Phase 1: Sensitive Data Detection', () => {
    test('should detect email addresses', () => {
      const result = vault.checkSensitive('Contact me at user@example.com');
      expect(result.hasSensitiveData).toBe(true);
      expect(result.detectedTypes.some(d => d.type === 'pii')).toBe(true);
    });

    test('should detect API keys', () => {
      const result = vault.checkSensitive('API key: sk-abc123def456ghi78901234567890abcdef');
      expect(result.hasSensitiveData).toBe(true);
      expect(result.detectedTypes.some(d => d.type === 'credential')).toBe(true);
    });

    test('should redact sensitive content when storing', () => {
      const entry = vault.store('My email is user@example.com and password: secret123');
      expect(entry.content).toContain('[PII_REDACTED]');
      expect(entry.content).toContain('[CREDENTIAL_REDACTED]');
      expect(entry.sensitivity).toBe('restricted');
    });
  });

  describe('Phase 1: Semantic Layer', () => {
    test('should extract entities from content', () => {
      const entry = vault.store('Meeting with Alice and Bob in New York on January 15th');
      
      expect(entry.semanticLayer.entities.length).toBeGreaterThan(0);
      expect(entry.semanticLayer.category).toBeDefined();
    });

    test('should categorize technical content', () => {
      const entry = vault.store('The API endpoint returns a JSON response with user data');
      
      expect(entry.semanticLayer.category).toBe('technical');
      expect(entry.semanticLayer.concepts.length).toBeGreaterThan(0);
    });
  });

  describe('Phase 2: Context-Aware Search', () => {
    beforeEach(() => {
      // Seed with diverse memories
      vault.store('The project uses React for frontend development', {
        type: 'semantic',
        tags: ['tech', 'frontend'],
        source: 'user_explicit'
      });
      
      vault.store('Database migration completed using PostgreSQL', {
        type: 'semantic', 
        tags: ['tech', 'database'],
        source: 'user_explicit'
      });
      
      vault.store('Team meeting scheduled for Tuesday at 2pm', {
        type: 'episodic',
        tags: ['meeting', 'schedule'],
        source: 'user_explicit'
      });
      
      vault.store('React hooks provide a way to use state in functional components', {
        type: 'semantic',
        tags: ['tech', 'react', 'frontend'],
        source: 'user_explicit'
      });
      
      vault.store('User authentication implemented with JWT tokens', {
        type: 'procedural',
        tags: ['auth', 'security'],
        source: 'user_explicit'
      });
    });

    test('should perform basic search', () => {
      const results = vault.search('React frontend');
      
      expect(results.length).toBeGreaterThan(0);
      expect(results[0].scores.combined).toBeGreaterThan(0);
    });

    test('should return individual scores', () => {
      const results = vault.search('React');
      
      expect(results.length).toBeGreaterThan(0);
      expect(results[0].scores.vector).toBeDefined();
      expect(results[0].scores.keyword).toBeDefined();
      expect(results[0].scores.temporal).toBeDefined();
      expect(results[0].scores.combined).toBeDefined();
    });

    test('should filter by memory type', () => {
      const semanticResults = vault.search('meeting', [], { types: ['semantic'] });
      const episodicResults = vault.search('meeting', [], { types: ['episodic'] });
      
      expect(episodicResults.length).toBeGreaterThan(0);
      expect(episodicResults[0].entry.type).toBe('episodic');
    });

    test('should filter by minimum confidence', () => {
      const results = vault.search('database', [], { minConfidence: 0.5 });
      
      for (const result of results) {
        expect(result.entry.confidence).toBeGreaterThanOrEqual(0.5);
      }
    });

    test('should apply context injection for relevance boost', () => {
      const contextMessages: ContextMessage[] = [
        { role: 'user', content: 'I need help with frontend development', timestamp: Date.now() },
        { role: 'assistant', content: 'What technology are you using?', timestamp: Date.now() }
      ];
      
      const resultsWithContext = vault.search('development', contextMessages);
      const resultsWithoutContext = vault.search('development');
      
      // With context, frontend-related results should rank higher
      expect(resultsWithContext.length).toBeGreaterThan(0);
    });

    test('should cache repeated queries', () => {
      // First search
      vault.search('React');
      
      // Second search (should hit cache)
      vault.search('React');
      
      const stats = vault.getStats();
      expect(stats.search.cacheHits).toBeGreaterThan(0);
    });

    test('should apply custom weights', () => {
      const results = vault.search('database', [], {
        weights: { vector: 0.8, keyword: 0.1, temporal: 0.1 }
      });
      
      expect(results.length).toBeGreaterThan(0);
    });

    test('should respect limit parameter', () => {
      const results = vault.search('the', [], { limit: 2 });
      
      expect(results.length).toBeLessThanOrEqual(2);
    });

    test('should filter by tags', () => {
      const results = vault.search('implementation', [], { tags: ['auth'] });
      
      for (const result of results) {
        expect(result.entry.metadata.tags).toContain('auth');
      }
    });

    test('should handle temporal relevance', () => {
      // Add old memory
      const oldEntry = vault.store('Legacy system documentation');
      // Manually set old timestamp
      oldEntry.timestamp = Date.now() - 30 * 24 * 60 * 60 * 1000; // 30 days ago
      
      // Add recent memory
      vault.store('New system architecture');
      
      const results = vault.search('system');
      
      // Recent entries should have higher temporal scores
      expect(results.length).toBeGreaterThan(0);
    });
  });

  describe('Phase 2: Hybrid Search Algorithm', () => {
    beforeEach(() => {
      // Create memories with different characteristics for algorithm testing
      vault.store('JavaScript async/await patterns for API calls', {
        type: 'semantic',
        tags: ['javascript', 'async', 'api']
      });
      
      vault.store('Python asyncio library documentation', {
        type: 'semantic',
        tags: ['python', 'async', 'documentation']
      });
      
      vault.store('REST API design best practices', {
        type: 'semantic',
        tags: ['api', 'rest', 'design']
      });
    });

    test('vector and keyword scores should be non-zero for matches', () => {
      const results = vault.search('async api');
      
      // At least top results should have non-zero scores
      expect(results.length).toBeGreaterThan(0);
      const topResult = results[0];
      const maxScore = Math.max(topResult.scores.vector, topResult.scores.keyword);
      expect(maxScore).toBeGreaterThan(0);
    });

    test('combined score should weight components correctly', () => {
      const results = vault.search('async');
      
      for (const result of results) {
        // Combined score should be between 0 and 1
        expect(result.scores.combined).toBeGreaterThanOrEqual(0);
        expect(result.scores.combined).toBeLessThanOrEqual(1);
      }
    });

    test('search should rank most relevant first', () => {
      const results = vault.search('javascript async');
      
      if (results.length >= 2) {
        // Results should be sorted by combined score descending
        expect(results[0].scores.combined).toBeGreaterThanOrEqual(results[1].scores.combined);
      }
    });
  });

  describe('Search Statistics', () => {
    test('should track search statistics', () => {
      vault.store('Test memory');
      
      vault.search('test');
      vault.search('memory');
      vault.search('test'); // Cache hit
      
      const stats = vault.getStats();
      
      expect(stats.search.totalSearches).toBe(3);
      expect(stats.search.cacheHits).toBe(1);
      expect(stats.search.cacheHitRate).toBeGreaterThan(0);
    });

    test('should track indexed entries', () => {
      vault.store('Memory 1');
      vault.store('Memory 2');
      
      const stats = vault.getStats();
      expect(stats.index.totalEntries).toBe(2);
    });
  });
});
