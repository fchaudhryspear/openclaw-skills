# Sensitive Data Detection - Phase 1

## Overview

ClawVault now includes automatic sensitive data detection and redaction. Before any memory is stored, it's scanned for PII (Personally Identifiable Information), API keys, secrets, and other sensitive data. Matches are automatically replaced with `[REDACTED]`.

## Quick Start

```javascript
const { scanContent, containsSensitiveData } = require('clawvault');

// Scan and redact
const result = scanContent('Email: user@example.com');
console.log(result.redactedContent); // "Email: [REDACTED]"
console.log(result.found);           // true
console.log(result.matches);         // [{ type: 'Email Address', severity: 'medium' }]

// Just check
const hasPII = containsSensitiveData('some content');
```

## What Gets Detected

### 🔴 Critical Severity

| Type | Pattern Example |
|------|-----------------|
| OpenAI API Key | `sk-abcdefghijklmnopqrstuvwxyz1234567890` |
| Stripe API Key | `sk_live_abcdefghijklmnopqrstuv` |
| AWS Access Key ID | `AKIAIOSFODNN7EXAMPLE` |
| GitHub Token | `ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx` |
| Slack Token | `xoxb-1234567890123-AbCdEfGhIjKlMnOpQrStUvWx` |
| US Social Security Number | `123-45-6789` |
| Credit Card Number | `4111 1111 1111 1111` |
| RSA/SSH/EC Private Keys | `-----BEGIN RSA PRIVATE KEY-----` |
| Database Connection Strings | `postgres://user:pass@host/db` |

### 🟡 High Severity

| Type | Pattern Example |
|------|-----------------|
| Generic API Keys | `api_key = "secret_value_here"` |
| Bearer Tokens | `Bearer eyJhbG...` (JWT format) |
| Password Fields | `"password": "secret123"` |
| Secret Fields | `"api_secret": "value"` |

### 🟢 Medium Severity

| Type | Pattern Example |
|------|-----------------|
| Email Addresses | `user@example.com` |
| US Phone Numbers | `555-123-4567`, `(555) 123-4567` |
| International Phones | `+1-555-123-4567`, `+44 20 7946 0958` |

## API Reference

### `scanContent(content)`

Scans content and returns detection results.

**Returns:**
```javascript
{
  found: boolean,              // Whether sensitive data was found
  redactedContent: string,     // Content with [REDACTED] replacements
  matches: Array<{
    type: string,              // Pattern name (e.g., 'Email Address')
    severity: string,          // 'low' | 'medium' | 'high' | 'critical'
    original: string,          // The matched text (for audit)
    position: number           // Position in original string
  }>
}
```

### `containsSensitiveData(content)`

Quick check if content contains any sensitive data.

**Returns:** `boolean`

### `getMatchedPatterns(content)`

Get list of all pattern names that matched.

**Returns:** `string[]`

## Integration with Memory Store

The scanner integrates with the existing ClawVault memory system:

```javascript
const { ClawVault } = require('clawvault');
const vault = new ClawVault();

// Memories are automatically scanned before storage
// (Integration in progress - will be available in next update)
```

## Demo

Run the demo to see detection in action:

```bash
node examples/sensitive-data-demo.js
```

## Testing

```bash
npm test
```

The scanner has comprehensive tests covering:
- All 20+ detection patterns
- Multiple simultaneous detections
- Edge cases and false positives
- Safe content (no false flags)

## Security Notes

1. **Better safe than sorry**: We prefer false positives over false negatives
2. **Regex-based**: Pattern matching has limitations; novel secret formats may not be detected
3. **No validation**: We don't verify if a credit card passes Luhn check or if an API key is valid
4. **Audit trail**: Consider logging redaction events for security review

## Future Enhancements

Phase 2 may include:
- Entropy-based secret detection (high-randomness strings)
- Configurable custom patterns
- Whitelist for known-safe patterns
- Integration with secret scanning services
