/**
 * Scanner Tests
 * 
 * Comprehensive tests for sensitive data detection and redaction.
 */

import {
  scanContent,
  containsSensitiveData,
  getMatchedPatterns,
  DETECTION_PATTERNS
} from '../src/scanner';

describe('Scanner', () => {
  describe('API Keys', () => {
    test('should detect OpenAI API key', () => {
      const content = 'My OpenAI key is sk-abcdefghijklmnopqrstuvwxyz123456789012345678';
      const result = scanContent(content);
      
      expect(result.found).toBe(true);
      expect(result.matches.some(m => m.type === 'OpenAI API Key')).toBe(true);
      expect(result.redactedContent).toContain('[REDACTED]');
      expect(result.redactedContent).not.toContain('sk-abc');
    });

    test('should detect Stripe secret key', () => {
      const content = 'Stripe key: sk_live_abcdefghijklmnopqrstuv';
      const result = scanContent(content);
      
      expect(result.found).toBe(true);
      expect(result.matches.some(m => m.type === 'Stripe API Key')).toBe(true);
    });

    test('should detect Stripe publishable key', () => {
      const content = 'pk_test_abcdefghijklmnopqrstuv';
      const result = scanContent(content);
      
      expect(result.found).toBe(true);
      expect(result.matches.some(m => m.type === 'Stripe API Key')).toBe(true);
    });

    test('should detect AWS Access Key ID', () => {
      const content = 'AWS Access Key: AKIAIOSFODNN7EXAMPLE';
      const result = scanContent(content);
      
      expect(result.found).toBe(true);
      expect(result.matches.some(m => m.type === 'AWS Access Key ID')).toBe(true);
    });

    test('should detect GitHub token', () => {
      const content = 'ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx';
      const result = scanContent(content);
      
      expect(result.found).toBe(true);
      expect(result.matches.some(m => m.type === 'GitHub Token')).toBe(true);
    });

    test('should detect Slack token', () => {
      const content = 'xoxb-1234567890123-1234567890123-AbCdEfGhIjKlMnOpQrStUvWx';
      const result = scanContent(content);
      
      expect(result.found).toBe(true);
      expect(result.matches.some(m => m.type === 'Slack Token')).toBe(true);
    });

    test('should detect generic API key', () => {
      const content = 'api_key = "this_is_a_secret_api_key_12345"';
      const result = scanContent(content);
      
      expect(result.found).toBe(true);
      expect(result.matches.some(m => m.type === 'Generic API Key')).toBe(true);
    });
  });

  describe('Passwords', () => {
    test('should detect password in JSON', () => {
      const content = '{"username": "admin", "password": "super_secret_password123"}';
      const result = scanContent(content);
      
      expect(result.found).toBe(true);
      expect(result.matches.some(m => m.type === 'Password in JSON')).toBe(true);
      expect(result.redactedContent).not.toContain('super_secret_password');
    });

    test('should detect password field with single quotes', () => {
      const content = "{'password': 'my_password_here'}";
      const result = scanContent(content);
      
      expect(result.found).toBe(true);
    });

    test('should detect pwd field', () => {
      const content = '{"user": "john", "pwd": "secret123"}';
      const result = scanContent(content);
      
      expect(result.found).toBe(true);
      expect(result.matches.some(m => m.type === 'Password Field')).toBe(true);
    });

    test('should detect password in config format', () => {
      const content = 'DB_PASSWORD=secret_password_here';
      const result = scanContent(content);
      
      expect(result.found).toBe(true);
    });

    test('should detect secret field', () => {
      const content = '{"api_secret": "this_is_a_long_secret_key"}';
      const result = scanContent(content);
      
      expect(result.found).toBe(true);
      expect(result.matches.some(m => m.type === 'Secret Field')).toBe(true);
    });
  });

  describe('Email Addresses', () => {
    test('should detect standard email', () => {
      const content = 'Contact me at john.doe@example.com for more info';
      const result = scanContent(content);
      
      expect(result.found).toBe(true);
      expect(result.matches.some(m => m.type === 'Email Address')).toBe(true);
      expect(result.redactedContent).not.toContain('john.doe@example.com');
    });

    test('should detect email with plus sign', () => {
      const content = 'user+tag@example.com';
      const result = scanContent(content);
      
      expect(result.found).toBe(true);
    });

    test('should detect multiple emails', () => {
      const content = 'Emails: alice@test.com, bob@example.org, charlie@company.net';
      const result = scanContent(content);
      
      expect(result.found).toBe(true);
      expect(result.redactionCount).toBeGreaterThanOrEqual(3);
    });
  });

  describe('Phone Numbers', () => {
    test('should detect US phone number with dashes', () => {
      const content = 'Call me at 555-123-4567';
      const result = scanContent(content);
      
      expect(result.found).toBe(true);
      expect(result.matches.some(m => m.type === 'US Phone Number')).toBe(true);
    });

    test('should detect US phone number with parentheses', () => {
      const content = 'Office: (555) 123-4567';
      const result = scanContent(content);
      
      expect(result.found).toBe(true);
    });

    test('should detect US phone number with dots', () => {
      const content = '555.123.4567';
      const result = scanContent(content);
      
      expect(result.found).toBe(true);
    });

    test('should detect international phone number', () => {
      const content = 'International: +1-555-123-4567';
      const result = scanContent(content);
      
      expect(result.found).toBe(true);
      expect(result.matches.some(m => m.type === 'International Phone')).toBe(true);
    });

    test('should detect E.164 format', () => {
      const content = 'E164: +15551234567';
      const result = scanContent(content);
      
      expect(result.found).toBe(true);
      expect(result.matches.some(m => m.type === 'E.164 Phone')).toBe(true);
    });
  });

  describe('Social Security Numbers', () => {
    test('should detect SSN with dashes', () => {
      const content = 'SSN: 123-45-6789';
      const result = scanContent(content);
      
      expect(result.found).toBe(true);
      expect(result.matches.some(m => m.type === 'US SSN')).toBe(true);
      expect(result.matches[0].severity).toBe('critical');
    });

    test('should detect SSN with spaces', () => {
      const content = 'SSN is 123 45 6789 for the record';
      const result = scanContent(content);
      
      expect(result.found).toBe(true);
    });
  });

  describe('Credit Cards', () => {
    test('should detect credit card with spaces', () => {
      const content = 'Card: 4111 1111 1111 1111';
      const result = scanContent(content);
      
      expect(result.found).toBe(true);
      expect(result.matches.some(m => m.type === 'Credit Card')).toBe(true);
      expect(result.matches[0].severity).toBe('critical');
    });

    test('should detect credit card with dashes', () => {
      const content = 'Card number is 4111-1111-1111-1111';
      const result = scanContent(content);
      
      expect(result.found).toBe(true);
    });

    test('should detect credit card without separators', () => {
      const content = 'Card: 4111111111111111';
      const result = scanContent(content);
      
      expect(result.found).toBe(true);
      expect(result.matches.some(m => m.type === 'Credit Card (No Spaces)')).toBe(true);
    });
  });

  describe('Private Keys', () => {
    test('should detect RSA private key', () => {
      const content = `-----BEGIN RSA PRIVATE KEY-----
MIIEpAIBAAKCAQEA0Z3VS5JJcds3xfn/ygWyF8PbnGy0AHB7MhgwMbRvI0MBZhpI
...
-----END RSA PRIVATE KEY-----`;
      const result = scanContent(content);
      
      expect(result.found).toBe(true);
      expect(result.matches.some(m => m.type === 'RSA Private Key')).toBe(true);
    });

    test('should detect OpenSSH private key', () => {
      const content = `-----BEGIN OPENSSH PRIVATE KEY-----
b3BlbnNzaC1rZXktdjEAAAAABG5vbmUAAAAEbm9uZQAAAAAAAAABAAAAMwAAAAtzc2gtZW
...
-----END OPENSSH PRIVATE KEY-----`;
      const result = scanContent(content);
      
      expect(result.found).toBe(true);
      expect(result.matches.some(m => m.type === 'SSH Private Key')).toBe(true);
    });
  });

  describe('Database URLs', () => {
    test('should detect PostgreSQL connection string', () => {
      const content = 'DATABASE_URL=postgres://user:password@localhost:5432/mydb';
      const result = scanContent(content);
      
      expect(result.found).toBe(true);
      expect(result.matches.some(m => m.type === 'Database URL')).toBe(true);
    });

    test('should detect MongoDB connection string', () => {
      const content = 'mongodb://admin:secret123@mongodb.example.com:27017/';
      const result = scanContent(content);
      
      expect(result.found).toBe(true);
    });
  });

  describe('Multiple Detections', () => {
    test('should detect multiple types in one content', () => {
      const content = `
        User: john.doe@example.com
        Phone: 555-123-4567
        API Key: sk-abcdefghijklmnopqrstuvwxyz123456789012345678
        Password: "secret123"
      `;
      const result = scanContent(content);
      
      expect(result.found).toBe(true);
      expect(result.matches.length).toBeGreaterThanOrEqual(4);
      
      const types = result.matches.map(m => m.type);
      expect(types).toContain('Email Address');
      expect(types).toContain('US Phone Number');
      expect(types).toContain('OpenAI API Key');
      expect(types).toContain('Password in JSON');
    });

    test('should redact all occurrences', () => {
      const content = 'Email: test1@example.com and test2@example.com';
      const result = scanContent(content);
      
      const redactedCount = (result.redactedContent.match(/\[REDACTED\]/g) || []).length;
      expect(redactedCount).toBe(2);
    });
  });

  describe('containsSensitiveData', () => {
    test('should return true for sensitive content', () => {
      expect(containsSensitiveData('sk-abcdefghijklmnopqrstuvwxyz123456789012345678')).toBe(true);
      expect(containsSensitiveData('test@example.com')).toBe(true);
    });

    test('should return false for safe content', () => {
      expect(containsSensitiveData('Hello world')).toBe(false);
      expect(containsSensitiveData('This is a normal memory without secrets')).toBe(false);
    });
  });

  describe('getMatchedPatterns', () => {
    test('should return matched pattern names', () => {
      const content = 'API: sk-abcdefghijklmnopqrstuvwxyz123456789012345678 Email: test@example.com';
      const patterns = getMatchedPatterns(content);
      
      expect(patterns).toContain('OpenAI API Key');
      expect(patterns).toContain('Email Address');
    });

    test('should return empty array for safe content', () => {
      const patterns = getMatchedPatterns('Just regular text');
      expect(patterns).toEqual([]);
    });
  });

  describe('Safe Content', () => {
    test('should not flag safe content', () => {
      const content = 'This is a normal memory about my day. I went to the park.';
      const result = scanContent(content);
      
      expect(result.found).toBe(false);
      expect(result.redactedContent).toBe(content);
      expect(result.matches).toEqual([]);
    });

    test('should handle empty content', () => {
      const result = scanContent('');
      
      expect(result.found).toBe(false);
      expect(result.redactedContent).toBe('');
    });
  });

  describe('Pattern Count', () => {
    test('should have detection patterns defined', () => {
      expect(DETECTION_PATTERNS.length).toBeGreaterThan(0);
    });

    test('each pattern should have required properties', () => {
      for (const pattern of DETECTION_PATTERNS) {
        expect(pattern.name).toBeDefined();
        expect(pattern.pattern).toBeInstanceOf(RegExp);
        expect(pattern.severity).toMatch(/^(low|medium|high|critical)$/);
        expect(pattern.description).toBeDefined();
      }
    });
  });
});
