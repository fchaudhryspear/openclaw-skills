/**
 * Sensitive Data Detection Demo
 * 
 * Run with: node examples/sensitive-data-demo.js
 */

const { scanContent, containsSensitiveData } = require('../src/scanner');

console.log('╔════════════════════════════════════════════════════════════╗');
console.log('║     ClawVault Sensitive Data Detection Demo                ║');
console.log('╚════════════════════════════════════════════════════════════╝\n');

// Example 1: PII Detection
console.log('━'.repeat(60));
console.log('Example 1: PII (Personally Identifiable Information)');
console.log('━'.repeat(60));

const piiExample = `
Contact Information:
- Name: John Smith
- Email: john.smith@personal-email.com
- Phone: (555) 123-4567
- Backup: +1-555-987-6543
`;

console.log('\n📝 Original Content:');
console.log(piiExample);

const piiResult = scanContent(piiExample);

console.log('🔒 Redacted Content:');
console.log(piiResult.redactedContent);

console.log('🔍 Detected:');
piiResult.matches.forEach(match => {
  console.log(`   • ${match.type} (${match.severity})`);
});

// Example 2: API Keys and Secrets
console.log('\n' + '━'.repeat(60));
console.log('Example 2: API Keys and Secrets');
console.log('━'.repeat(60));

const secretsExample = `
Configuration:
{
  "openai_api_key": "sk-abcdefghijklmnopqrstuvwxyz1234567890",
  "stripe_secret": "sk_live_abcdefghijklmnopqrstuv",
  "aws_access_key": "AKIAIOSFODNN7EXAMPLE",
  "github_token": "ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
  "database_password": "super_secret_db_password_123",
  "api_secret": "my_api_secret_key_here"
}
`;

console.log('\n📝 Original Content:');
console.log(secretsExample);

const secretsResult = scanContent(secretsExample);

console.log('🔒 Redacted Content:');
console.log(secretsResult.redactedContent);

console.log('🔍 Detected:');
secretsResult.matches.forEach(match => {
  console.log(`   • ${match.type} (${match.severity})`);
});

// Example 3: Financial Data
console.log('\n' + '━'.repeat(60));
console.log('Example 3: Financial Data (CRITICAL)');
console.log('━'.repeat(60));

const financialExample = `
Customer Payment Info:
- Card: 4111 1111 1111 1111
- SSN for verification: 123-45-6789
- Billing contact: billing@company.com
`;

console.log('\n📝 Original Content:');
console.log(financialExample);

const financialResult = scanContent(financialExample);

console.log('🔒 Redacted Content:');
console.log(financialResult.redactedContent);

console.log('🔍 Detected:');
financialResult.matches.forEach(match => {
  const icon = match.severity === 'critical' ? '🔴' : '🟡';
  console.log(`   ${icon} ${match.type} (${match.severity})`);
});

// Example 4: Code with Private Keys
console.log('\n' + '━'.repeat(60));
console.log('Example 4: Private Keys (CRITICAL)');
console.log('━'.repeat(60));

const keyExample = `
// SSH Configuration
const privateKey = \`-----BEGIN OPENSSH PRIVATE KEY-----
b3BlbnNzaC1rZXktdjEAAAAABG5vbmUAAAAEbm9uZQAAAAAAAAABAAAAMwAAAAtzc2gtZW
...base64-encoded-key...
-----END OPENSSH PRIVATE KEY-----\`;

// Database connection
const dbUrl = 'postgres://admin:secretpass123@db.production.internal:5432/app';
`;

console.log('\n📝 Original Content:');
console.log(keyExample);

const keyResult = scanContent(keyExample);

console.log('🔒 Redacted Content:');
console.log(keyResult.redactedContent);

console.log('🔍 Detected:');
keyResult.matches.forEach(match => {
  const icon = match.severity === 'critical' ? '🔴' : '🟡';
  console.log(`   ${icon} ${match.type} (${match.severity})`);
});

// Summary
console.log('\n' + '═'.repeat(60));
console.log('Summary');
console.log('═'.repeat(60));

console.log('\n✅ Detection patterns available:', 20);
console.log('📊 Severity levels: critical, high, medium, low');
console.log('🔧 Redaction token: [REDACTED]');
console.log('\n🛡️  Your memories are now protected!');
