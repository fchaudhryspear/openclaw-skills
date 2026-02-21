# Sensitive Data Detection Reference

This document details what data ClawVault detects and redacts, along with the rationale for each pattern.

## Detection Philosophy

ClawVault uses a **better-safe-than-sorry** approach. When in doubt, we redact. False positives (safe content marked as sensitive) are preferred over false negatives (sensitive data stored unredacted).

## Pattern Categories

### 1. API Keys & Tokens (Critical Severity)

#### OpenAI API Keys
- **Pattern**: `sk-[a-zA-Z0-9]{48}`
- **Rationale**: OpenAI keys grant access to GPT models and billing. Leakage can result in significant financial loss and API abuse.
- **Example**: `sk-abcdefghijklmnopqrstuvwxyz123456789012345678`

#### Stripe API Keys
- **Pattern**: `(sk|pk)_(live|test)_[a-zA-Z0-9]{24,}`
- **Rationale**: Stripe keys control payment processing. Live keys can process real transactions.
- **Example**: `sk_live_abcdefghijklmnopqrstuv`, `pk_test_abcdefghijklmnopqrstuv`

#### AWS Access Keys
- **Pattern**: `AKIA[0-9A-Z]{16}` (Access Key ID)
- **Rationale**: AWS credentials can incur massive charges and expose all AWS resources.
- **Example**: `AKIAIOSFODNN7EXAMPLE`

#### GitHub Tokens
- **Pattern**: `ghp_[a-zA-Z0-9]{36}`
- **Rationale**: GitHub tokens can access private repos, modify code, and trigger actions.
- **Example**: `ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx`

#### Slack Tokens
- **Pattern**: `xox[baprs]-[a-zA-Z0-9-]+`
- **Rationale**: Slack tokens can read messages, post as users, and access workspace data.
- **Example**: `xoxb-1234567890123-1234567890123-AbCdEfGhIjKlMnOpQrStUvWx`

#### Generic API Keys
- **Pattern**: `(api[_-]?key|apikey)[\s]*[=:]+[\s]*['"]?[a-zA-Z0-9_-]{16,}['"]?`
- **Rationale**: Catches various API key formats in config files and code.
- **Example**: `api_key = "my_secret_key_12345"`, `APIKEY: secret123`

### 2. Authentication Credentials (High/Critical Severity)

#### Bearer Tokens / JWTs
- **Pattern**: `Bearer\s+[a-zA-Z0-9_-]+\.[a-zA-Z0-9_-]+\.[a-zA-Z0-9_-]+`
- **Rationale**: JWTs encode authentication claims. While they expire, they should still be protected.
- **Example**: `Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.dozjgNryP4J3jVmNHl0w5N_XgL0n3I9PlFUP0THsR8U`

#### Passwords
- **Patterns**:
  - `"password": "..."` (JSON)
  - `password = ...` (Config)
  - `"pwd": "..."` (Abbreviated)
  - `"secret": "..."` (Secret fields)
- **Rationale**: Passwords in code/configs are security anti-patterns. Must never be stored in memory.
- **Examples**:
  - `{"password": "super_secret_123"}`
  - `DB_PASSWORD=secret123`
  - `{"secret": "api_secret_key"}`

### 3. Personal Identifiable Information (PII) (Medium Severity)

#### Email Addresses
- **Pattern**: Standard RFC 5322 simplified pattern
- **Rationale**: Email addresses are primary identifiers. Combined with other data, they enable identity theft.
- **Example**: `john.doe@example.com`, `user+tag@company.co.uk`

#### Phone Numbers
- **Patterns**:
  - US: `\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}`
  - International: `\+\d{1,3}[-.\s]?...`
  - E.164: `\+\d{10,15}`
- **Rationale**: Phone numbers are highly personal. Often used for 2FA and account recovery.
- **Examples**:
  - `555-123-4567`
  - `(555) 123-4567`
  - `+1-555-123-4567`
  - `+15551234567`

#### US Social Security Numbers
- **Pattern**: `\d{3}[-\s]?\d{2}[-\s]?\d{4}`
- **Rationale**: SSNs are the primary identity token in the US. Theft enables financial fraud.
- **Example**: `123-45-6789`, `123 45 6789`
- **Note**: This can have false positives (random numbers matching the pattern). Consider enabling `rejectCritical` for SSN handling.

### 4. Financial Data (Critical Severity)

#### Credit Card Numbers
- **Patterns**:
  - With separators: `(?:\d{4}[-\s]?){3}\d{4}`
  - Without separators: `\d{4}\d{4}\d{4}\d{4}`
- **Rationale**: PCI DSS requirement. Credit card leakage is a major compliance violation.
- **Examples**:
  - `4111 1111 1111 1111`
  - `4111-1111-1111-1111`
  - `4111111111111111`
- **Note**: These patterns match 16-digit numbers that *look* like credit cards. Luhn validation is not performed.

### 5. Cryptographic Keys (Critical Severity)

#### RSA Private Keys
- **Pattern**: `-----BEGIN RSA PRIVATE KEY-----...-----END RSA PRIVATE KEY-----`
- **Rationale**: RSA private keys enable decryption, impersonation, and authentication bypass.

#### OpenSSH Private Keys
- **Pattern**: `-----BEGIN OPENSSH PRIVATE KEY-----...-----END OPENSSH PRIVATE KEY-----`
- **Rationale**: SSH keys provide server access. Compromise = full system access.

#### EC Private Keys
- **Pattern**: `-----BEGIN EC PRIVATE KEY-----...-----END EC PRIVATE KEY-----`
- **Rationale**: Elliptic curve keys are used for modern cryptography.

### 6. Connection Strings (Critical Severity)

#### Database URLs
- **Pattern**: `(postgres|mysql|mongodb|redis):\/\/[^:]+:[^@]+@[^/]+\/`
- **Rationale**: Database URLs contain passwords and expose infrastructure details.
- **Examples**:
  - `postgres://user:password@localhost:5432/mydb`
  - `mongodb://admin:secret@mongodb.example.com:27017/`
  - `mysql://root:pass123@db.internal:3306/production`

## Severity Levels Explained

| Level | Description | Action |
|-------|-------------|--------|
| **Critical** | Immediate security risk if exposed | Redact + Strong warning |
| **High** | Significant risk, could enable attacks | Redact + Warning |
| **Medium** | PII that could enable identity theft | Redact + Log |
| **Low** | Minor sensitivity | Redact + Log |

## Why Redact Instead of Reject?

ClawVault defaults to redaction rather than rejection for several reasons:

1. **Context Preservation**: The non-sensitive parts of the memory are still useful.
2. **User Experience**: The application continues to work even with PII present.
3. **Audit Trail**: Redaction events are logged for security review.

Use `rejectCritical: true` when you want to block critical data entirely.

## Limitations

1. **Regex-based**: Pattern matching isn't perfect. Novel secret formats may not be detected.
2. **False Positives**: 16-digit numbers may include non-credit-card data. SSN pattern matches some legitimate numbers.
3. **No Validation**: We don't verify if a credit card passes Luhn check or if an API key is valid.
4. **Context Blind**: We don't understand context. A "password" field in a documentation example gets redacted too.

## Future Enhancements

Potential improvements for Phase 2:

- [ ] Entropy-based secret detection (high-randomness strings)
- [ ] Machine learning for context-aware detection
- [ ] Luhn validation for credit cards
- [ ] SSN area/group validation
- [ ] Integration with secret scanning services (GitHub Token Scanning, etc.)
- [ ] Configurable custom patterns
- [ ] Whitelist for known-safe patterns

## Compliance Notes

### GDPR
- Email addresses and phone numbers are personal data under GDPR
- Redaction helps with "data minimization" principle
- Audit logs support accountability requirements

### CCPA
- Similar considerations to GDPR
- Redaction limits "personal information" collection

### PCI DSS
- Credit card redaction is essential for PCI compliance
- Consider `rejectCritical: true` for payment card data

### HIPAA
- PHI (Protected Health Information) includes many of these patterns
- Additional healthcare-specific patterns may be needed
