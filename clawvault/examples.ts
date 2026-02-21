/**
 * ClawVault Usage Examples
 * 
 * Demonstrates the sensitive data detection feature.
 */

import { createStore, scanContent, logger } from './src/index';

// Configure logger to show output
logger.configure({ enableConsole: true, minLevel: 'info' });

console.log('=== ClawVault Sensitive Data Detection Demo ===\n');

// Example 1: Direct Scanner Usage
console.log('1. Direct Scanner Usage');
console.log('-----------------------');

const sampleText = `
Hello! My name is John and my email is john.doe@example.com.
You can reach me at 555-123-4567.
My OpenAI API key is sk-abcdefghijklmnopqrstuvwxyz123456789012345678.
`;

const scanResult = scanContent(sampleText);
console.log('Original:');
console.log(sampleText);
console.log('\nRedacted:');
console.log(scanResult.redactedContent);
console.log('\nDetected types:', scanResult.matches.map(m => m.type));
console.log('Highest severity:', scanResult.matches.reduce((h, m) => 
  ['low', 'medium', 'high', 'critical'].indexOf(m.severity) > 
  ['low', 'medium', 'high', 'critical'].indexOf(h) ? m.severity : h, 'low'
));

// Example 2: Memory Store with Auto-Redaction
console.log('\n\n2. Memory Store Example');
console.log('-----------------------');

const store = createStore();

// Safe memory
const safeMemory = store.store({
  content: 'Today I learned about TypeScript generics. Very useful!',
  tags: ['learning', 'typescript']
});
console.log('Safe memory stored:');
console.log('  - Sensitive:', safeMemory.sensitive);
console.log('  - Content:', safeMemory.content.substring(0, 50) + '...');

// Memory with PII
const piiMemory = store.store({
  content: 'Met with Sarah (sarah.j@company.com) at +1-555-987-6543 to discuss the API integration using key sk-test-1234567890abcdef',
  tags: ['meeting', 'work'],
  metadata: { project: 'api-integration' }
});
console.log('\nMemory with PII stored:');
console.log('  - Sensitive:', piiMemory.sensitive);
console.log('  - Redacted types:', piiMemory.redactedTypes?.join(', '));
console.log('  - Severity:', piiMemory.redactionSeverity);
console.log('  - Count:', piiMemory.redactionCount);
console.log('  - Content:', piiMemory.content);

// Example 3: Code Snippet with Secrets
console.log('\n\n3. Code Snippet Example');
console.log('-----------------------');

const codeSnippet = `
const config = {
  database: {
    host: 'prod-db.company.com',
    user: 'admin',
    password: 'SuperSecretDBPass123!'
  },
  stripeKey: 'sk_live_abcdefghijklmnopqrstuv',
  contactEmail: 'support@company.com'
};
`;

const codeMemory = store.store({
  content: codeSnippet,
  tags: ['code', 'config', 'production']
});

console.log('Code snippet stored:');
console.log('  - Sensitive:', codeMemory.sensitive);
console.log('  - Redacted content:');
console.log(codeMemory.content);

// Example 4: Statistics
console.log('\n\n4. Memory Statistics');
console.log('--------------------');
console.log('Total memories:', store.count());
console.log('Sensitive memories:', store.sensitiveCount());
console.log('Non-sensitive memories:', store.getNonSensitive().length);

// Example 5: Searching
console.log('\n\n5. Search by Sensitivity');
console.log('------------------------');
const sensitiveOnly = store.search({ sensitive: true });
console.log('Sensitive memories:', sensitiveOnly.length);
sensitiveOnly.forEach(r => {
  console.log(`  - [${r.memory.redactionSeverity}] ${r.memory.redactedTypes?.join(', ')}`);
});

// Example 6: Reject Critical Data
console.log('\n\n6. Strict Mode (Reject Critical)');
console.log('--------------------------------');

const strictStore = createStore({ rejectCritical: true });

try {
  strictStore.store({
    content: 'User SSN for verification: 123-45-6789'
  });
} catch (error) {
  console.log('Error caught:', (error as Error).message);
}

console.log('\n=== Demo Complete ===');
