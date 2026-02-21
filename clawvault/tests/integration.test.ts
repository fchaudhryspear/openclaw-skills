/**
 * Integration Tests
 * 
 * End-to-end tests demonstrating the full ClawVault flow.
 */

import { createStore, scanContent, logger } from '../src/index';

describe('ClawVault Integration', () => {
  beforeEach(() => {
    logger.configure({ enableConsole: false, minLevel: 'error' });
  });

  test('complete flow: store and retrieve safe memory', () => {
    const store = createStore();
    
    const memory = store.store({
      content: 'I learned about TypeScript today',
      tags: ['learning', 'typescript']
    });

    expect(memory.sensitive).toBe(false);
    expect(memory.content).toBe('I learned about TypeScript today');

    const retrieved = store.get(memory.id);
    expect(retrieved).toEqual(memory);
  });

  test('complete flow: store memory with PII and verify redaction', () => {
    const store = createStore();
    
    const originalContent = `
      Met with John today. His email is john.doe@example.com.
      We discussed the project at 555-123-4567.
      He shared their API key: sk-abcdefghijklmnopqrstuvwxyz123456789012345678
    `;

    const memory = store.store({
      content: originalContent,
      tags: ['meeting', 'work']
    });

    // Verify sensitive flag
    expect(memory.sensitive).toBe(true);
    
    // Verify redaction
    expect(memory.content).toContain('[REDACTED]');
    expect(memory.content).not.toContain('john.doe@example.com');
    expect(memory.content).not.toContain('555-123-4567');
    expect(memory.content).not.toContain('sk-abc');
    
    // Verify metadata
    expect(memory.redactionCount).toBeGreaterThanOrEqual(3);
    expect(memory.redactionTypes).toContain('Email Address');
    expect(memory.redactionTypes).toContain('US Phone Number');
    expect(memory.redactionTypes).toContain('OpenAI API Key');
    expect(memory.redactionSeverity).toBe('critical');
  });

  test('real-world scenario: storing code snippet with secrets', () => {
    const store = createStore();
    
    const codeSnippet = `
      const config = {
        database: {
          host: 'localhost',
          password: 'super_secret_db_password_123',
          user: 'admin'
        },
        apiKey: 'sk-abcdefghijklmnopqrstuvwxyz123456789012345678',
        email: 'admin@company.com'
      };
    `;

    const memory = store.store({
      content: codeSnippet,
      tags: ['code', 'config'],
      metadata: { source: 'development' }
    });

    expect(memory.sensitive).toBe(true);
    expect(memory.content).not.toContain('super_secret_db_password');
    expect(memory.content).not.toContain('sk-abc');
    expect(memory.content).not.toContain('admin@company.com');
    expect(memory.metadata.source).toBe('development');
  });

  test('real-world scenario: conversation log with PII', () => {
    const store = createStore();
    
    const conversation = `
      Customer Support Log #12345
      
      Customer: Sarah Johnson
      Email: sarah.j@customer.com
      Phone: +1-555-987-6543
      
      Issue: Unable to access account
      
      Notes: Customer provided SSN for verification: 987-65-4321
      Payment method on file: 4111 1111 1111 1111
      
      Resolution: Account unlocked
    `;

    const memory = store.store({
      content: conversation,
      tags: ['support', 'customer-service']
    });

    expect(memory.sensitive).toBe(true);
    expect(memory.redactionSeverity).toBe('critical');
    expect(memory.content).not.toContain('987-65-4321');
    expect(memory.content).not.toContain('4111 1111 1111 1111');
    expect(memory.content).not.toContain('sarah.j@customer.com');
    expect(memory.content).not.toContain('+1-555-987-6543');
  });

  test('search and filter sensitive memories', () => {
    const store = createStore();
    
    // Store mixed content
    store.store({ content: 'Regular work notes', tags: ['work'] });
    store.store({ content: 'Email contact: boss@company.com', tags: ['work', 'contact'] });
    store.store({ content: 'Personal diary entry', tags: ['personal'] });
    store.store({ content: 'API config: sk-abc123...', tags: ['dev'] });

    // Search for sensitive memories
    const sensitiveResults = store.search({ sensitive: true });
    expect(sensitiveResults.length).toBe(2);

    // Search for work-related memories
    const workResults = store.search({ tags: ['work'] });
    expect(workResults.length).toBe(2);

    // Search for non-sensitive work memories
    const safeWorkResults = store.search({ tags: ['work'], sensitive: false });
    expect(safeWorkResults.length).toBe(1);
    expect(safeWorkResults[0].memory.content).toBe('Regular work notes');
  });

  test('direct scanner usage without store', () => {
    const content = 'Contact: jane@example.com, Phone: 555-555-5555';
    const result = scanContent(content);

    expect(result.found).toBe(true);
    expect(result.matches).toHaveLength(2);
    expect(result.redactedContent).toBe('Contact: [REDACTED], Phone: [REDACTED]');
  });

  test('statistics tracking', () => {
    const store = createStore();
    
    store.store({ content: 'Safe memory 1' });
    store.store({ content: 'Safe memory 2' });
    store.store({ content: 'Email: test1@example.com' });
    store.store({ content: 'Email: test2@example.com' });
    store.store({ content: 'API: sk-abc123...' });

    expect(store.count()).toBe(5);
    expect(store.sensitiveCount()).toBe(3);
    expect(store.getSensitive().length).toBe(3);
    expect(store.getNonSensitive().length).toBe(2);
  });

  test('config option: reject critical data', () => {
    const strictStore = createStore({ rejectCritical: true });

    // This should be rejected
    expect(() => {
      strictStore.store({
        content: 'SSN: 123-45-6789'
      });
    }).toThrow();

    // This should be allowed (medium severity)
    const memory = strictStore.store({
      content: 'Email: test@example.com'
    });
    expect(memory.sensitive).toBe(true);
  });
});
