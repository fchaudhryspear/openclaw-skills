"use strict";
/**
 * Phase 1: Sensitive Data Detection
 * Detects and handles sensitive information in memory entries
 */
Object.defineProperty(exports, "__esModule", { value: true });
exports.SensitiveDataDetector = void 0;
class SensitiveDataDetector {
    patterns = [
        // PII - High severity
        { type: 'pii', regex: /\b\d{3}-\d{2}-\d{4}\b/g, severity: 'high' }, // SSN
        { type: 'pii', regex: /\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b/g, severity: 'high' }, // Credit card
        { type: 'pii', regex: /\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b/g, severity: 'medium' }, // Email
        { type: 'pii', regex: /\b\d{3}-\d{3}-\d{4}\b/g, severity: 'medium' }, // Phone
        { type: 'pii', regex: /\b\d{5}(-\d{4})?\b/g, severity: 'low' }, // ZIP code
        // Credentials - High severity
        { type: 'credential', regex: /\b(password|passwd|pwd)\s*[:=]\s*\S+/gi, severity: 'high' },
        { type: 'credential', regex: /\b(api[_-]?key|apikey)\s*[:=]\s*[\w-]+/gi, severity: 'high' },
        { type: 'credential', regex: /\b(secret[_-]?key|secretkey)\s*[:=]\s*[\w-]+/gi, severity: 'high' },
        { type: 'credential', regex: /\b(token|bearer)\s+["']?[\w-]+["']?/gi, severity: 'high' },
        { type: 'credential', regex: /sk-[a-zA-Z0-9]{32,}/g, severity: 'high' }, // OpenAI-style keys
        { type: 'credential', regex: /\b[A-Za-z0-9/+=]{40,}\b/g, severity: 'medium' }, // AWS keys, etc.
        // Financial - Medium to High
        { type: 'financial', regex: /\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b/g, severity: 'high' }, // Credit card
        { type: 'financial', regex: /\b(routing|account)\s+(number|#|no)?\s*:?\s*\d{9,}\b/gi, severity: 'high' },
        { type: 'financial', regex: /\$\d{1,3}(,\d{3})*(\.\d{2})?/g, severity: 'low' }, // Dollar amounts
        // Health - High severity
        { type: 'health', regex: /\b\d{3}-\d{2}-\d{4}\b/g, severity: 'high' }, // SSN (also health)
        { type: 'health', regex: /\b(medical|health|diagnosis|patient)\s+(id|record|number)\s*:?\s*\w+/gi, severity: 'high' },
        // Location - Low to Medium
        { type: 'location', regex: /\b\d+\s+[A-Za-z]+\s+(St|Street|Ave|Avenue|Rd|Road|Blvd|Boulevard|Dr|Drive|Ln|Lane)\b/gi, severity: 'medium' },
        { type: 'location', regex: /\b(ip|address)\s*:?\s*\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b/gi, severity: 'low' }
    ];
    detect(content) {
        const detectedTypes = [];
        const foundRanges = [];
        for (const { type, regex, severity } of this.patterns) {
            const matches = content.matchAll(regex);
            for (const match of matches) {
                if (match.index !== undefined) {
                    const start = match.index;
                    const end = start + match[0].length;
                    // Avoid overlapping detections
                    if (!this.hasOverlap(start, end, foundRanges)) {
                        foundRanges.push([start, end]);
                        detectedTypes.push({
                            type,
                            pattern: match[0],
                            position: [start, end],
                            severity
                        });
                    }
                }
            }
        }
        const hasSensitiveData = detectedTypes.length > 0;
        // Sort by position and remove duplicates
        detectedTypes.sort((a, b) => a.position[0] - b.position[0]);
        // Calculate overall confidence based on severity
        const severityScores = { high: 1.0, medium: 0.7, low: 0.4 };
        const confidence = detectedTypes.length > 0
            ? detectedTypes.reduce((sum, dt) => sum + severityScores[dt.severity], 0) / detectedTypes.length
            : 0;
        // Generate redacted content if sensitive data found
        let redactedContent;
        if (hasSensitiveData) {
            redactedContent = this.redactContent(content, detectedTypes);
        }
        return {
            hasSensitiveData,
            detectedTypes,
            redactedContent,
            confidence: Math.round(confidence * 100) / 100
        };
    }
    hasOverlap(start, end, ranges) {
        return ranges.some(([rStart, rEnd]) => (start >= rStart && start < rEnd) ||
            (end > rStart && end <= rEnd) ||
            (start <= rStart && end >= rEnd));
    }
    redactContent(content, detectedTypes) {
        let redacted = content;
        // Process in reverse order to maintain positions
        const sorted = [...detectedTypes].sort((a, b) => b.position[0] - a.position[0]);
        for (const dt of sorted) {
            const [start, end] = dt.position;
            const replacement = `[${dt.type.toUpperCase()}_REDACTED]`;
            redacted = redacted.slice(0, start) + replacement + redacted.slice(end);
        }
        return redacted;
    }
    determineSensitivityLevel(detection) {
        if (!detection.hasSensitiveData)
            return 'public';
        const hasHigh = detection.detectedTypes.some(dt => dt.severity === 'high');
        const hasMedium = detection.detectedTypes.some(dt => dt.severity === 'medium');
        if (hasHigh)
            return 'restricted';
        if (hasMedium)
            return 'confidential';
        return 'internal';
    }
    sanitize(content, targetLevel = 'public') {
        const detection = this.detect(content);
        if (!detection.hasSensitiveData)
            return content;
        const currentLevel = this.determineSensitivityLevel(detection);
        const levels = ['public', 'internal', 'confidential', 'restricted'];
        if (levels.indexOf(currentLevel) <= levels.indexOf(targetLevel)) {
            return content; // Current level is acceptable
        }
        return detection.redactedContent || content;
    }
}
exports.SensitiveDataDetector = SensitiveDataDetector;
//# sourceMappingURL=sensitive.js.map