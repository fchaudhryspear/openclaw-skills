/**
 * Tests for Confidence Scoring Module
 * 
 * Tests the confidence scoring algorithm including:
 * - Source reliability scoring
 * - Recency decay calculations
 * - User feedback adjustments
 * - End-to-end confidence calculation
 */

const { describe, it } = require('node:test');
const assert = require('node:assert');

const {
  getSourceBaseConfidence,
  calculateRecencyDecay,
  getFeedbackAdjustment,
  calculateConfidence,
  recalculateConfidence,
  updateMemoryConfidence,
  DEFAULT_CONFIDENCE_CONFIG,
} = require('../dist/confidence');

describe('Confidence Scoring', () => {
  
  describe('getSourceBaseConfidence', () => {
    it('should return 1.0 for user_explicit source', () => {
      const result = getSourceBaseConfidence('user_explicit');
      assert.strictEqual(result, 1.0);
    });

    it('should return 0.7 for inferred source', () => {
      const result = getSourceBaseConfidence('inferred');
      assert.strictEqual(result, 0.7);
    });

    it('should return 0.5 for auto_extracted source', () => {
      const result = getSourceBaseConfidence('auto_extracted');
      assert.strictEqual(result, 0.5);
    });

    it('should use custom config values', () => {
      const customConfig = {
        ...DEFAULT_CONFIDENCE_CONFIG,
        userExplicitBase: 0.95,
        inferredBase: 0.65,
        autoExtractedBase: 0.45,
      };
      assert.strictEqual(getSourceBaseConfidence('user_explicit', customConfig), 0.95);
      assert.strictEqual(getSourceBaseConfidence('inferred', customConfig), 0.65);
      assert.strictEqual(getSourceBaseConfidence('auto_extracted', customConfig), 0.45);
    });
  });

  describe('calculateRecencyDecay', () => {
    it('should return ~1.0 for memories created today', () => {
      const now = new Date();
      const result = calculateRecencyDecay(now);
      assert.ok(Math.abs(result - 1.0) < 0.0001, `Expected ~1.0, got ${result}`);
    });

    it('should return ~1.0 for memories created in the future', () => {
      const future = new Date(Date.now() + 86400000); // Tomorrow
      const result = calculateRecencyDecay(future);
      assert.ok(Math.abs(result - 1.0) < 0.0001, `Expected ~1.0, got ${result}`);
    });

    it('should decay linearly to 0.7 over 30 days', () => {
      const now = new Date();
      const days15 = new Date(now.getTime() - 15 * 24 * 60 * 60 * 1000);
      const days30 = new Date(now.getTime() - 30 * 24 * 60 * 60 * 1000);
      
      const result15 = calculateRecencyDecay(days15);
      const result30 = calculateRecencyDecay(days30);
      
      // At 15 days, should be halfway between 1.0 and 0.7
      assert.ok(result15 > 0.8 && result15 < 0.9, `Expected ~0.85, got ${result15}`);
      assert.strictEqual(result30, 0.7);
    });

    it('should decay from 0.7 to 0.5 between 30 and 90 days', () => {
      const now = new Date();
      const days60 = new Date(now.getTime() - 60 * 24 * 60 * 60 * 1000);
      const days90 = new Date(now.getTime() - 90 * 24 * 60 * 60 * 1000);
      
      const result60 = calculateRecencyDecay(days60);
      const result90 = calculateRecencyDecay(days90);
      
      // At 60 days (midpoint), should be halfway between 0.7 and 0.5
      assert.ok(result60 > 0.55 && result60 < 0.65, `Expected ~0.6, got ${result60}`);
      assert.strictEqual(result90, 0.5);
    });

    it('should stay at 0.5 beyond 90 days', () => {
      const now = new Date();
      const days120 = new Date(now.getTime() - 120 * 24 * 60 * 60 * 1000);
      const days365 = new Date(now.getTime() - 365 * 24 * 60 * 60 * 1000);
      
      const result120 = calculateRecencyDecay(days120);
      const result365 = calculateRecencyDecay(days365);
      
      assert.strictEqual(result120, 0.5);
      assert.strictEqual(result365, 0.5);
    });
  });

  describe('getFeedbackAdjustment', () => {
    it('should return +0.1 for thumbs_up', () => {
      const result = getFeedbackAdjustment('thumbs_up');
      assert.strictEqual(result, 0.1);
    });

    it('should return -0.2 for thumbs_down', () => {
      const result = getFeedbackAdjustment('thumbs_down');
      assert.strictEqual(result, -0.2);
    });

    it('should return 0 for no feedback', () => {
      const result = getFeedbackAdjustment(null);
      assert.strictEqual(result, 0);
    });

    it('should use custom config values', () => {
      const customConfig = {
        ...DEFAULT_CONFIDENCE_CONFIG,
        thumbsUpBonus: 0.15,
        thumbsDownPenalty: -0.25,
      };
      assert.strictEqual(getFeedbackAdjustment('thumbs_up', customConfig), 0.15);
      assert.strictEqual(getFeedbackAdjustment('thumbs_down', customConfig), -0.25);
    });
  });

  describe('calculateConfidence', () => {
    it('should calculate confidence for new user_explicit memory', () => {
      const result = calculateConfidence({
        source: 'user_explicit',
        createdAt: new Date(),
        feedback: null,
      });
      assert.ok(Math.abs(result - 1.0) < 0.0001, `Expected ~1.0, got ${result}`);
    });

    it('should calculate confidence for new auto_extracted memory', () => {
      const result = calculateConfidence({
        source: 'auto_extracted',
        createdAt: new Date(),
        feedback: null,
      });
      assert.strictEqual(result, 0.5);
    });

    it('should boost confidence with thumbs_up', () => {
      const result = calculateConfidence({
        source: 'inferred',
        createdAt: new Date(),
        feedback: 'thumbs_up',
      });
      // 0.7 (base) * 1.0 (recency) + 0.1 (feedback) = 0.8
      assert.ok(Math.abs(result - 0.8) < 0.0001, `Expected ~0.8, got ${result}`);
    });

    it('should reduce confidence with thumbs_down', () => {
      const result = calculateConfidence({
        source: 'user_explicit',
        createdAt: new Date(),
        feedback: 'thumbs_down',
      });
      // 1.0 (base) * 1.0 (recency) - 0.2 (feedback) = 0.8
      assert.strictEqual(result, 0.8);
    });

    it('should combine recency decay and feedback', () => {
      const now = new Date();
      const days30 = new Date(now.getTime() - 30 * 24 * 60 * 60 * 1000);
      
      const result = calculateConfidence({
        source: 'user_explicit',
        createdAt: days30,
        feedback: 'thumbs_up',
      });
      // 1.0 (base) * 0.7 (30-day decay) + 0.1 (feedback) = 0.8
      assert.ok(Math.abs(result - 0.8) < 0.0001, `Expected ~0.8, got ${result}`);
    });

    it('should clamp confidence to minimum 0.0', () => {
      const result = calculateConfidence({
        source: 'auto_extracted',
        createdAt: new Date(),
        feedback: 'thumbs_down',
      });
      // 0.5 (base) - 0.2 (feedback) = 0.3, should be 0.3
      assert.strictEqual(result, 0.3);
    });

    it('should clamp confidence to maximum 1.0', () => {
      // Create a scenario that would exceed 1.0
      const customConfig = {
        ...DEFAULT_CONFIDENCE_CONFIG,
        userExplicitBase: 1.0,
        thumbsUpBonus: 0.2,
      };
      const result = calculateConfidence({
        source: 'user_explicit',
        createdAt: new Date(),
        feedback: 'thumbs_up',
        config: customConfig,
      });
      // Would be 1.2, but clamped to 1.0
      assert.strictEqual(result, 1.0);
    });

    it('should handle very old memories correctly', () => {
      const now = new Date();
      const days100 = new Date(now.getTime() - 100 * 24 * 60 * 60 * 1000);
      
      const result = calculateConfidence({
        source: 'inferred',
        createdAt: days100,
        feedback: null,
      });
      // 0.7 (base) * 0.5 (90+ day decay) = 0.35
      assert.strictEqual(result, 0.35);
    });
  });

  describe('recalculateConfidence', () => {
    it('should recalculate confidence from memory object', () => {
      const memory = {
        id: 'test1',
        content: 'Test memory',
        sensitive: false,
        metadata: {
          createdAt: new Date().toISOString(),
          updatedAt: new Date().toISOString(),
          source: 'user_explicit',
          feedback: null,
        },
      };
      
      const result = recalculateConfidence(memory);
      assert.ok(Math.abs(result - 1.0) < 0.0001, `Expected ~1.0, got ${result}`);
    });

    it('should use auto_extracted as default source', () => {
      const memory = {
        id: 'test1',
        content: 'Test memory',
        sensitive: false,
        metadata: {
          createdAt: new Date().toISOString(),
          updatedAt: new Date().toISOString(),
          source: undefined,
          feedback: null,
        },
      };
      
      const result = recalculateConfidence(memory);
      assert.strictEqual(result, 0.5);
    });
  });

  describe('updateMemoryConfidence', () => {
    it('should update memory metadata with new confidence', () => {
      const memory = {
        id: 'test1',
        content: 'Test memory',
        sensitive: false,
        metadata: {
          createdAt: new Date().toISOString(),
          updatedAt: new Date().toISOString(),
          source: 'user_explicit',
          feedback: null,
        },
      };
      
      const result = updateMemoryConfidence(memory);
      
      assert.strictEqual(result, 1.0);
      assert.strictEqual(memory.metadata.confidence, 1.0);
    });
  });
});
