# Reference-Based Secret Storage

## Overview

ClawVault's Sensitive Data Detection now uses **reference-based storage** instead of full redaction. This means:

- ❌ **Old way**: "API key is [REDACTED]" (lost forever)
- ✅ **New way**: "API key stored in: environment variable $OPENAI_API_KEY or 1Password 'OpenAI'" (recoverable)

## Why References?

**Problem with redaction:**
```
User: My OpenAI key is sk-abc123...
Stored: "My OpenAI key is [REDACTED]"

Later:
User: What's my OpenAI key?
Me: I don't know, it's [REDACTED] 🤷
```

**Solution with references:**
```
User: My OpenAI key is sk-abc123...
Stored: "OpenAI key stored in: environment variable $OPENAI_API_KEY or 1Password 'OpenAI'"

Later:
User: What's my OpenAI key?
Me: Check your environment variable $OPENAI_API_KEY or 1Password entry 'OpenAI'
```

## How It Works

When a secret is detected, ClawVault:

1. **Identifies the secret type** (OpenAI key, password, etc.)
2. **Replaces with reference** pointing to where it should be stored
3. **Preserves utility** — you know where to find it

## Supported Secret Types & References

| Secret Type | Reference Location |
|-------------|-------------------|
| **OpenAI API Key** | `$OPENAI_API_KEY` env var or 1Password "OpenAI" |
| **Stripe API Key** | `$STRIPE_API_KEY` env var or 1Password "Stripe" |
| **AWS Credentials** | `~/.aws/credentials` or 1Password "AWS" |
| **GitHub Token** | `$GITHUB_TOKEN` env var or 1Password "GitHub" |
| **Slack Token** | `$SLACK_TOKEN` env var or 1Password "Slack" |
| **Passwords** | Environment variable or 1Password |
| **Private Keys** | `~/.ssh/` directory or 1Password |
| **Database URLs** | `$DATABASE_URL` env var or secret manager |
| **Email/Phone** | Contacts or address book |
| **SSN** | 1Password or encrypted document storage |
| **Credit Cards** | 1Password or Apple Wallet |

## Usage Examples

### During Conversation

**Input:**
```
User: I set up the AWS connection with AKIAIOSFODNN7EXAMPLE
```

**Stored in vault:**
```
"AWS connection set up with [AWS Access Key ID: AWS credentials stored in: ~/.aws/credentials [profile: default] or 1Password 'AWS']]"
```

**Later retrieval:**
```
User: What AWS key did we use?
Me: You set up the AWS connection — check ~/.aws/credentials [default profile] or 1Password "AWS"
```

### API Usage

```javascript
const { scanContent } = require('./scanner');

const result = scanContent('My key is sk-abc123...');

console.log(result.processedContent);
// "My key is [OpenAI API Key: OpenAI API key stored in: environment variable $OPENAI_API_KEY or 1Password "OpenAI"]]"

console.log(result.references);
// [{
//   type: "OpenAI API Key",
//   severity: "critical",
//   reference: "[OpenAI API Key: OpenAI API key stored in: environment variable $OPENAI_API_KEY or 1Password "OpenAI"]]",
//   original: "sk-abc123..."
// }]
```

## Setting Up Your Secret Storage

### 1Password (Recommended)

Create entries with standard names:
- "OpenAI" — for API keys
- "AWS" — for AWS credentials  
- "GitHub" — for personal access tokens
- "Database" — for connection strings

### Environment Variables

Add to your `~/.zshrc` or `~/.bashrc`:

```bash
# API Keys
export OPENAI_API_KEY="sk-..."
export GITHUB_TOKEN="ghp_..."
export STRIPE_API_KEY="sk_live_..."

# Database
export DATABASE_URL="postgres://user:pass@host/db"
```

### AWS Credentials

Use the standard AWS CLI location:

```ini
# ~/.aws/credentials
[default]
aws_access_key_id = AKIA...
aws_secret_access_key = ...

[production]
aws_access_key_id = AKIA...
aws_secret_access_key = ...
```

### SSH Keys

Store in standard location:

```
~/.ssh/
├── id_rsa          # Default SSH key
├── id_rsa.pub      # Public key
├── id_ed25519      # Modern key format
└── config          # SSH config
```

## Legacy Redaction Mode

If you need full redaction (e.g., for compliance), use:

```javascript
const { scanAndRedact } = require('./scanner');

const result = scanAndRedact('My key is sk-abc123...');
console.log(result.processedContent);
// "My key is [REDACTED]"
```

## Security Considerations

**Reference-based storage is safer because:**

1. **No secrets in vault** — Only pointers, not actual keys
2. **Secrets stay in proper managers** — 1Password, env vars, etc.
3. **Access controlled by secret manager** — Not by vault permissions
4. **Audit trail in secret manager** — Who accessed what, when

**Best practices:**

- Use 1Password or similar for all secrets
- Set environment variables in `.zshrc` (not committed files)
- Use AWS CLI for AWS credentials
- Keep SSH keys in `~/.ssh/` with 600 permissions

## Migration from Old System

If you have existing memories with `[REDACTED]`:

1. Check if the secret is still needed
2. If yes, re-add the conversation with the secret
3. ClawVault will now store the reference instead

## Custom References

To customize reference locations, edit `REFERENCE_TEMPLATES` in `scanner.js`:

```javascript
const REFERENCE_TEMPLATES = {
  'OpenAI API Key': 'Your custom location: Bitwarden "API Keys" folder',
  // ... more templates
};
```

## Testing

Run the test suite:

```bash
cd ~/.openclaw/workspace/clawvault
npm test tests/scanner.test.js
```

Test your own secrets:

```bash
node examples/sensitive-data-demo.js
```
