"use strict";
/**
 * Sensitive Data Detection Module - Reference-Based Storage
 *
 * Scans content for secrets and stores references to their location
 * instead of the actual secret values. This maintains utility while
 * preventing accidental exposure of sensitive data.
 */
Object.defineProperty(exports, "__esModule", { value: true });
exports.DETECTION_PATTERNS = void 0;
exports.scanContent = scanContent;
exports.containsSensitiveData = containsSensitiveData;
exports.getMatchedPatterns = getMatchedPatterns;
exports.getReferenceLocation = getReferenceLocation;
exports.scanAndRedact = scanAndRedact;
// Reference templates for common secret locations
const REFERENCE_TEMPLATES = {
    'OpenAI API Key': 'OpenAI API key stored in: environment variable $OPENAI_API_KEY or 1Password "OpenAI"',
    'Stripe API Key': 'Stripe API key stored in: environment variable $STRIPE_API_KEY or 1Password "Stripe"',
    'AWS Access Key ID': 'AWS credentials stored in: ~/.aws/credentials [profile: default] or 1Password "AWS"',
    'AWS Secret Access Key': 'AWS credentials stored in: ~/.aws/credentials [profile: default] or 1Password "AWS"',
    'GitHub Token': 'GitHub token stored in: environment variable $GITHUB_TOKEN or 1Password "GitHub"',
    'Slack Token': 'Slack token stored in: environment variable $SLACK_TOKEN or 1Password "Slack"',
    'Generic API Key': 'API key stored in: environment variable or secret manager (1Password, Bitwarden)',
    'Bearer Token': 'Bearer token stored in: environment variable $BEARER_TOKEN or secret manager',
    'Password in JSON': 'Password stored in: environment variable or secret manager (1Password)',
    'Password in Config': 'Password stored in: environment variable or secret manager (1Password)',
    'Password Field': 'Password stored in: environment variable or secret manager (1Password)',
    'Secret Field': 'Secret stored in: environment variable or secret manager (1Password)',
    'Email Address': 'Email stored in: contacts or secure address book',
    'US Phone Number': 'Phone number stored in: contacts or address book',
    'International Phone': 'Phone number stored in: contacts or address book',
    'E.164 Phone': 'Phone number stored in: contacts or address book',
    'US SSN': 'SSN stored in: secure document storage (1Password, encrypted file)',
    'Credit Card': 'Credit card stored in: secure wallet (1Password, Apple Wallet)',
    'Credit Card (No Spaces)': 'Credit card stored in: secure wallet (1Password, Apple Wallet)',
    'RSA Private Key': 'Private key stored in: ~/.ssh/ or secure key vault (1Password)',
    'SSH Private Key': 'Private key stored in: ~/.ssh/ or secure key vault (1Password)',
    'EC Private Key': 'Private key stored in: ~/.ssh/ or secure key vault (1Password)',
    'Database URL': 'Database credentials stored in: environment variable $DATABASE_URL or secret manager'
};
// Detection patterns for various types of sensitive data
exports.DETECTION_PATTERNS = [
    // API Keys - Various formats
    {
        name: 'OpenAI API Key',
        pattern: /\bsk-[a-zA-Z0-9]{48}\b/g,
        severity: 'critical',
        description: 'OpenAI API key format (sk-*)',
        referenceTemplate: REFERENCE_TEMPLATES['OpenAI API Key']
    },
    {
        name: 'Stripe API Key',
        pattern: /\b(sk|pk)_(live|test)_[a-zA-Z0-9]{24,}\b/g,
        severity: 'critical',
        description: 'Stripe API key format',
        referenceTemplate: REFERENCE_TEMPLATES['Stripe API Key']
    },
    {
        name: 'AWS Access Key ID',
        pattern: /\bAKIA[0-9A-Z]{16}\b/g,
        severity: 'critical',
        description: 'AWS Access Key ID format (AKIA*)',
        referenceTemplate: REFERENCE_TEMPLATES['AWS Access Key ID']
    },
    {
        name: 'AWS Secret Access Key',
        pattern: /\b[A-Za-z0-9/+=]{40}\b/g,
        severity: 'critical',
        description: 'Potential AWS Secret Access Key',
        referenceTemplate: REFERENCE_TEMPLATES['AWS Secret Access Key']
    },
    {
        name: 'GitHub Token',
        pattern: /\bghp_[a-zA-Z0-9]{36}\b/g,
        severity: 'critical',
        description: 'GitHub Personal Access Token',
        referenceTemplate: REFERENCE_TEMPLATES['GitHub Token']
    },
    {
        name: 'Slack Token',
        pattern: /\bxox[baprs]-[a-zA-Z0-9-]+\b/g,
        severity: 'critical',
        description: 'Slack API token format',
        referenceTemplate: REFERENCE_TEMPLATES['Slack Token']
    },
    {
        name: 'Generic API Key',
        pattern: /\b(api[_-]?key|apikey)[\s]*[=:]+[\s]*['"]?[a-zA-Z0-9_-]{16,}['"]?/gi,
        severity: 'high',
        description: 'Generic API key pattern',
        referenceTemplate: REFERENCE_TEMPLATES['Generic API Key']
    },
    {
        name: 'Bearer Token',
        pattern: /\bBearer\s+[a-zA-Z0-9_-]+\.[a-zA-Z0-9_-]+\.[a-zA-Z0-9_-]+\b/g,
        severity: 'high',
        description: 'JWT Bearer token',
        referenceTemplate: REFERENCE_TEMPLATES['Bearer Token']
    },
    // Passwords
    {
        name: 'Password in JSON',
        pattern: /["']password["']\s*:\s*["'][^"']{4,}["']/gi,
        severity: 'high',
        description: 'Password field in JSON',
        referenceTemplate: REFERENCE_TEMPLATES['Password in JSON']
    },
    {
        name: 'Password in Config',
        pattern: /password\s*=\s*[^\s]+/gi,
        severity: 'high',
        description: 'Password assignment in config',
        referenceTemplate: REFERENCE_TEMPLATES['Password in Config']
    },
    {
        name: 'Password Field',
        pattern: /["']pwd["']\s*:\s*["'][^"']{4,}["']/gi,
        severity: 'high',
        description: 'Password field (pwd) in JSON',
        referenceTemplate: REFERENCE_TEMPLATES['Password Field']
    },
    {
        name: 'Secret Field',
        pattern: /["']secret["']\s*:\s*["'][^"']{8,}["']/gi,
        severity: 'high',
        description: 'Secret field in JSON',
        referenceTemplate: REFERENCE_TEMPLATES['Secret Field']
    },
    // Email Addresses
    {
        name: 'Email Address',
        pattern: /\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b/g,
        severity: 'medium',
        description: 'Standard email address format',
        referenceTemplate: REFERENCE_TEMPLATES['Email Address']
    },
    // Phone Numbers
    {
        name: 'US Phone Number',
        pattern: /\b\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b/g,
        severity: 'medium',
        description: 'US phone number format',
        referenceTemplate: REFERENCE_TEMPLATES['US Phone Number']
    },
    {
        name: 'International Phone',
        pattern: /\+\d{1,3}[-.\s]?\(?\d{1,4}\)?[-.\s]?\d{1,4}[-.\s]?\d{1,9}/g,
        severity: 'medium',
        description: 'International phone number format',
        referenceTemplate: REFERENCE_TEMPLATES['International Phone']
    },
    {
        name: 'E.164 Phone',
        pattern: /\+\d{10,15}\b/g,
        severity: 'medium',
        description: 'E.164 phone number format',
        referenceTemplate: REFERENCE_TEMPLATES['E.164 Phone']
    },
    // Social Security Numbers
    {
        name: 'US SSN',
        pattern: /\b\d{3}[-\s]?\d{2}[-\s]?\d{4}\b/g,
        severity: 'critical',
        description: 'US Social Security Number format',
        referenceTemplate: REFERENCE_TEMPLATES['US SSN']
    },
    // Credit Cards
    {
        name: 'Credit Card',
        pattern: /\b(?:\d{4}[-\s]?){3}\d{4}\b/g,
        severity: 'critical',
        description: 'Credit card number format (16 digits)',
        referenceTemplate: REFERENCE_TEMPLATES['Credit Card']
    },
    {
        name: 'Credit Card (No Spaces)',
        pattern: /\b\d{4}\d{4}\d{4}\d{4}\b/g,
        severity: 'critical',
        description: 'Credit card number (no spaces)',
        referenceTemplate: REFERENCE_TEMPLATES['Credit Card (No Spaces)']
    },
    // Private Keys
    {
        name: 'RSA Private Key',
        pattern: /-----BEGIN RSA PRIVATE KEY-----[\s\S]*?-----END RSA PRIVATE KEY-----/g,
        severity: 'critical',
        description: 'RSA private key block',
        referenceTemplate: REFERENCE_TEMPLATES['RSA Private Key']
    },
    {
        name: 'SSH Private Key',
        pattern: /-----BEGIN OPENSSH PRIVATE KEY-----[\s\S]*?-----END OPENSSH PRIVATE KEY-----/g,
        severity: 'critical',
        description: 'OpenSSH private key block',
        referenceTemplate: REFERENCE_TEMPLATES['SSH Private Key']
    },
    {
        name: 'EC Private Key',
        pattern: /-----BEGIN EC PRIVATE KEY-----[\s\S]*?-----END EC PRIVATE KEY-----/g,
        severity: 'critical',
        description: 'EC private key block',
        referenceTemplate: REFERENCE_TEMPLATES['EC Private Key']
    },
    // Database Connection Strings
    {
        name: 'Database URL',
        pattern: /\b(postgres|mysql|mongodb|redis):\/\/[^:]+:[^@]+@[^/]+\//gi,
        severity: 'critical',
        description: 'Database connection string with credentials',
        referenceTemplate: REFERENCE_TEMPLATES['Database URL']
    }
];
/**
 * Scans content for sensitive data and replaces with references
 * instead of redacting completely. This maintains utility while
 * preventing storage of actual secrets.
 */
function scanContent(content) {
    const references = [];
    let processedContent = content;
    // Track all matches with their positions
    const allMatches = [];
    for (const detection of exports.DETECTION_PATTERNS) {
        const regex = new RegExp(detection.pattern.source, detection.pattern.flags);
        let match;
        while ((match = regex.exec(content)) !== null) {
            allMatches.push({
                type: detection.name,
                severity: detection.severity,
                reference: `[${detection.name}: ${detection.referenceTemplate}]`,
                original: match[0],
                position: match.index,
                length: match[0].length
            });
        }
    }
    // Sort matches by position (descending) to replace from end to start
    allMatches.sort((a, b) => b.position - a.position);
    // Remove duplicate/overlapping matches (keep the longer one)
    const uniqueMatches = [];
    for (const match of allMatches) {
        const isOverlapping = uniqueMatches.some(um => (match.position >= um.position && match.position < um.position + um.length) ||
            (um.position >= match.position && um.position < match.position + match.length));
        if (!isOverlapping) {
            uniqueMatches.push(match);
        }
    }
    // Perform replacements with references
    for (const match of uniqueMatches) {
        processedContent =
            processedContent.substring(0, match.position) +
                match.reference +
                processedContent.substring(match.position + match.length);
    }
    // Sort matches by position ascending for the result
    uniqueMatches.sort((a, b) => a.position - b.position);
    return {
        found: uniqueMatches.length > 0,
        processedContent,
        references: uniqueMatches.map(m => ({
            type: m.type,
            severity: m.severity,
            reference: m.reference,
            position: m.position,
            original: m.original
        }))
    };
}
/**
 * Check if content contains sensitive data without processing
 */
function containsSensitiveData(content) {
    for (const detection of exports.DETECTION_PATTERNS) {
        if (detection.pattern.test(content)) {
            return true;
        }
    }
    return false;
}
/**
 * Get all patterns that matched in the content
 */
function getMatchedPatterns(content) {
    const matched = new Set();
    for (const detection of exports.DETECTION_PATTERNS) {
        const regex = new RegExp(detection.pattern.source, detection.pattern.flags);
        if (regex.test(content)) {
            matched.add(detection.name);
        }
    }
    return Array.from(matched);
}
/**
 * Get reference location for a detected secret type
 */
function getReferenceLocation(secretType) {
    return REFERENCE_TEMPLATES[secretType] || 'Stored in: secure vault or environment variable';
}
/**
 * Legacy redaction mode (for when full redaction is needed)
 */
function scanAndRedact(content) {
    const result = scanContent(content);
    // Replace all references with [REDACTED]
    const redactedContent = result.processedContent.replace(/\[[^\]]+: [^\]]+\]/g, '[REDACTED]');
    return {
        ...result,
        processedContent: redactedContent
    };
}
//# sourceMappingURL=scanner.js.map