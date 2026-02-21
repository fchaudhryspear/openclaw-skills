/**
 * Phase 1: Sensitive Data Detection
 * Detects and handles sensitive information in memory entries
 */
import { SensitiveDataDetection, SensitivityLevel } from './types';
export declare class SensitiveDataDetector {
    private patterns;
    detect(content: string): SensitiveDataDetection;
    private hasOverlap;
    private redactContent;
    determineSensitivityLevel(detection: SensitiveDataDetection): SensitivityLevel;
    sanitize(content: string, targetLevel?: SensitivityLevel): string;
}
//# sourceMappingURL=sensitive.d.ts.map