/**
 * Scanner Tests
 * 
 * Tests for sensitive data detection and redaction.
 */

const { describe, it } = require('node:test');
const assert = require('node:assert');
const {
  scanContent,
  containsSensitiveData,
  getMatchedPatterns,
  DETECTION_PATTERNS
} = require('../src/scanner');

describe('Scanner', () => {
  describe('API Keys', () => {
    it('should detect OpenAI API key', () => {
      const content = 'My OpenAI key is sk-abcdefghijklmnopqrstuvwxyz123456789012345678';
      const result = scanContent(content);
      
      assert.strictEqual(result.found, true);
      assert.ok(result.matches.some(m => m.type === 'OpenAI API Key'));
      assert.ok(result.redactedContent.includes('[REDACTED]'));
      assert.ok(!result.redactedContent.includes('sk-abc'));
    });

    it('should detect Stripe secret key', () => {
      const content = 'Stripe key: sk_live_abcdefghijklmnopqrstuv';
      const result = scanContent(content);
      
      assert.strictEqual(result.found, true);
      assert.ok(result.matches.some(m => m.type === 'Stripe API Key'));
    });

    it('should detect AWS Access Key ID', () => {
      const content = 'AWS Access Key: AKIAIOSFODNN7EXAMPLE';
      const result = scanContent(content);
      
      assert.strictEqual(result.found, true);
      assert.ok(result.matches.some(m => m.type === 'AWS Access Key ID'));
    });

    it('should detect GitHub token', () => {
      const content = 'ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx';
      const result = scanContent(content);
      
      assert.strictEqual(result.found, true);
      assert.ok(result.matches.some(m => m.type === 'GitHub Token'));
    });
  });

  describe('Passwords', () => {
    it('should detect password in JSON', () => {
      const content = '{"username": "admin", "password": "super_secret_password123"}';
      const result = scanContent(content);
      
      assert.strictEqual(result.found, true);
      assert.ok(result.matches.some(m => m.type === 'Password in JSON'));
      assert.ok(!result.redactedContent.includes('super_secret_password'));
    });

    it('should detect secret field', () => {
      const content = '{"api_secret": "this_is_a_long_secret_key"}';
      const result = scanContent(content);
      
      assert.strictEqual(result.found, true);
      assert.ok(result.matches.some(m => m.type === 'Secret Field'));
    });
  });

  describe('Email Addresses', () => {
    it('should detect standard email', () => {
      const content = 'Contact me at john.doe@example.com for more info';
      const result = scanContent(content);
      
      assert.strictEqual(result.found, true);
      assert.ok(result.matches.some(m => m.type === 'Email Address'));
      assert.ok(!result.redactedContent.includes('john.doe@example.com'));
    });

    it('should detect multiple emails', () => {
      const content = 'Emails: alice@test.com, bob@example.org';
      const result = scanContent(content);
      
      assert.strictEqual(result.found, true);
      assert.ok(result.matches.length >= 2);
    });
  });

  describe('Phone Numbers', () => {
    it('should detect US phone number with dashes', () => {
      const content = 'Call me at 555-123-4567';
      const result = scanContent(content);
      
      assert.strictEqual(result.found, true);
      assert.ok(result.matches.some(m => m.type === 'US Phone Number'));
    });

    it('should detect international phone number', () => {
      const content = 'International: +44-20-7946-0958';
      const result = scanContent(content);
      
      assert.strictEqual(result.found, true);
      // Should detect at least one phone pattern
      assert.ok(result.matches.some(m => 
        m.type === 'International Phone' || 
        m.type === 'E.164 Phone'
      ));
    });
  });

  describe('SSN and Credit Cards', () => {
    it('should detect US SSN', () => {
      const content = 'SSN: 123-45-6789';
      const result = scanContent(content);
      
      assert.strictEqual(result.found, true);
      assert.ok(result.matches.some(m => m.type === 'US SSN'));
      assert.strictEqual(result.matches[0].severity, 'critical');
    });

    it('should detect credit card', () => {
      const content = 'Card: 4111 1111 1111 1111';
      const result = scanContent(content);
      
      assert.strictEqual(result.found, true);
      assert.ok(result.matches.some(m => m.type === 'Credit Card'));
    });
  });

  describe('Private Keys', () => {
    it('should detect RSA private key', () => {
      const content = `-----BEGIN RSA PRIVATE KEY-----
MIIEpAIBAAKCAQEA0Z3VS5JJcds3xfn/ygWyF8PbnGy0AHB7MhgwMbRvI0MBZhpI
...
-----END RSA PRIVATE KEY-----`;
      const result = scanContent(content);
      
      assert.strictEqual(result.found, true);
      assert.ok(result.matches.some(m => m.type === 'RSA Private Key'));
    });
  });

  describe('Database URLs', () => {
    it('should detect PostgreSQL connection string', () => {
      const content = 'DATABASE_URL=postgres://user:password@localhost:5432/mydb';
      const result = scanContent(content);
      
      assert.strictEqual(result.found, true);
      assert.ok(result.matches.some(m => m.type === 'Database URL'));
    });
  });

  describe('Multiple Detections', () => {
    it('should detect multiple types in one content', () => {
      const content = `
        User: john.doe@example.com
        Phone: 555-123-4567
        API Key: sk-abcdefghijklmnopqrstuvwxyz123456789012345678
      `;
      const result = scanContent(content);
      
      assert.strictEqual(result.found, true);
      assert.ok(result.matches.length >= 3);
      
      const types = result.matches.map(m => m.type);
      assert.ok(types.includes('Email Address'));
      assert.ok(types.includes('US Phone Number'));
      assert.ok(types.includes('OpenAI API Key'));
    });

    it('should redact all occurrences', () => {
      const content = 'Email: test1@example.com and test2@example.com';
      const result = scanContent(content);
      
      const redactedCount = (result.redactedContent.match(/\[REDACTED\]/g) || []).length;
      assert.strictEqual(redactedCount, 2);
    });
  });

  describe('containsSensitiveData', () => {
    it('should return true for sensitive content', () => {
      assert.strictEqual(
        containsSensitiveData('sk-abcdefghijklmnopqrstuvwxyz123456789012345678'),
        true
      );
      assert.strictEqual(containsSensitiveData('test@example.com'), true);
    });

    it('should return false for safe content', () => {
      assert.strictEqual(containsSensitiveData('Hello world'), false);
    });
  });

  describe('getMatchedPatterns', () => {
    it('should return matched pattern names', () => {
      const content = 'API: sk-abcdefghijklmnopqrstuvwxyz123456789012345678 Email: test@example.com';
      const patterns = getMatchedPatterns(content);
      
      assert.ok(patterns.includes('OpenAI API Key'));
      assert.ok(patterns.includes('Email Address'));
    });

    it('should return empty array for safe content', () => {
      const patterns = getMatchedPatterns('Just regular text');
      assert.deepStrictEqual(patterns, []);
    });
  });

  describe('Safe Content', () => {
    it('should not flag safe content', () => {
      const content = 'This is a normal memory about my day.';
      const result = scanContent(content);
      
      assert.strictEqual(result.found, false);
      assert.strictEqual(result.redactedContent, content);
      assert.deepStrictEqual(result.matches, []);
    });
  });

  describe('Pattern Validation', () => {
    it('should have detection patterns defined', () => {
      assert.ok(DETECTION_PATTERNS.length > 0);
    });

    it('each pattern should have required properties', () => {
      for (const pattern of DETECTION_PATTERNS) {
        assert.ok(pattern.name, 'Pattern should have a name');
        assert.ok(pattern.pattern instanceof RegExp, 'Pattern should be a RegExp');
        assert.ok(/^(low|medium|high|critical)$/.test(pattern.severity), 'Pattern should have valid severity');
        assert.ok(pattern.description, 'Pattern should have a description');
      }
    });
  });
});
