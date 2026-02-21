/**
 * Sensitive Data Detection Module - Reference-Based Storage
 *
 * Scans content for secrets and stores references to their location
 * instead of the actual secret values. This maintains utility while
 * preventing accidental exposure of sensitive data.
 */
export interface DetectionPattern {
    name: string;
    pattern: RegExp;
    severity: 'low' | 'medium' | 'high' | 'critical';
    description: string;
    referenceTemplate: string;
}
export interface DetectionResult {
    found: boolean;
    processedContent: string;
    references: Array<{
        type: string;
        severity: 'low' | 'medium' | 'high' | 'critical';
        reference: string;
        position: number;
        original: string;
    }>;
}
export declare const DETECTION_PATTERNS: DetectionPattern[];
/**
 * Scans content for sensitive data and replaces with references
 * instead of redacting completely. This maintains utility while
 * preventing storage of actual secrets.
 */
export declare function scanContent(content: string): DetectionResult;
/**
 * Check if content contains sensitive data without processing
 */
export declare function containsSensitiveData(content: string): boolean;
/**
 * Get all patterns that matched in the content
 */
export declare function getMatchedPatterns(content: string): string[];
/**
 * Get reference location for a detected secret type
 */
export declare function getReferenceLocation(secretType: string): string;
/**
 * Legacy redaction mode (for when full redaction is needed)
 */
export declare function scanAndRedact(content: string): DetectionResult;
//# sourceMappingURL=scanner.d.ts.map