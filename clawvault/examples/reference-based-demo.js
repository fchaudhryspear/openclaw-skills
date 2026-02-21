#!/usr/bin/env node
/**
 * Reference-Based Secret Storage Demo
 * 
 * This demo shows how ClawVault stores references to secrets
 * instead of the actual secret values.
 */

const { scanContent, containsSensitiveData, getReferenceLocation } = require('../src/scanner');

console.log('='.repeat(70));
console.log('Reference-Based Secret Storage Demo');
console.log('='.repeat(70));
console.log();
console.log('Instead of storing secrets in the vault, we store REFERENCES');
console.log('pointing to where the secret should be kept (1Password, env vars, etc.)');
console.log();
console.log('='.repeat(70));
console.log();

const examples = [
  {
    name: 'OpenAI API Key',
    input: 'My OpenAI API key is sk-abc123def456ghi789jkl012mno345pqr678stu901vwx234yz',
    description: 'OpenAI API key for GPT-4 access'
  },
  {
    name: 'AWS Credentials',
    input: 'Using AWS key AKIAIOSFODNN7EXAMPLE for the deployment',
    description: 'AWS Access Key ID'
  },
  {
    name: 'GitHub Token',
    input: 'ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx',
    description: 'GitHub Personal Access Token'
  },
  {
    name: 'Database Connection',
    input: 'Connecting to postgres://admin:secret123@db.example.com:5432/production',
    description: 'PostgreSQL connection string with credentials'
  },
  {
    name: 'Email Address',
    input: 'Contact me at faisal@credologi.com for updates',
    description: 'Business email address'
  },
  {
    name: 'Password',
    input: 'The password is "Hunter2!Secure" for the server',
    description: 'Server password'
  }
];

for (const example of examples) {
  console.log(`\n${'─'.repeat(70)}`);
  console.log(`Example: ${example.name}`);
  console.log(`${'─'.repeat(70)}`);
  console.log(`Description: ${example.description}`);
  console.log();
  console.log('Original Input:');
  console.log(`  ${example.input}`);
  console.log();
  
  const result = scanContent(example.input);
  
  console.log('Stored in Vault (Reference-Based):');
  console.log(`  ${result.processedContent}`);
  console.log();
  
  if (result.references.length > 0) {
    console.log('References Detected:');
    for (const ref of result.references) {
      console.log(`  • Type: ${ref.type}`);
      console.log(`    Severity: ${ref.severity}`);
      console.log(`    Reference: ${ref.reference}`);
      console.log();
    }
  }
  
  console.log('Utility Preserved: ✅');
  console.log('  → You know WHERE to find the secret');
  console.log('  → Secret stays in proper secret manager');
  console.log('  → No actual values stored in vault');
}

console.log('\n' + '='.repeat(70));
console.log('Benefits of Reference-Based Storage');
console.log('='.repeat(70));
console.log();
console.log('1. SECURITY: Secrets stay in proper secret managers (1Password, env vars)');
console.log('2. UTILITY: You know where to find secrets when needed');
console.log('3. COMPLIANCE: Audit trail in secret manager, not scattered in vault');
console.log('4. RECOVERY: If vault is compromised, secrets are not exposed');
console.log();
console.log('='.repeat(70));
console.log();

// Show reference lookup
console.log('Reference Lookup Examples:');
console.log();
console.log('Where is my OpenAI key stored?');
console.log(`  ${getReferenceLocation('OpenAI API Key')}`);
console.log();
console.log('Where are my AWS credentials?');
console.log(`  ${getReferenceLocation('AWS Access Key ID')}`);
console.log();
console.log('Where is my database password?');
console.log(`  ${getReferenceLocation('Database URL')}`);
console.log();
