/**
 * Audit Logger Module
 *
 * Logs warnings when sensitive data redaction occurs for security auditing.
 */
export type LogLevel = 'debug' | 'info' | 'warn' | 'error';
export interface LogEntry {
    timestamp: string;
    level: LogLevel;
    message: string;
    metadata?: Record<string, unknown>;
}
export interface LoggerConfig {
    minLevel: LogLevel;
    enableConsole: boolean;
    logCallback?: (entry: LogEntry) => void;
}
declare class Logger {
    private config;
    configure(config: Partial<LoggerConfig>): void;
    private shouldLog;
    private log;
    debug(message: string, metadata?: Record<string, unknown>): void;
    info(message: string, metadata?: Record<string, unknown>): void;
    warn(message: string, metadata?: Record<string, unknown>): void;
    error(message: string, metadata?: Record<string, unknown>): void;
    /**
     * Log a redaction event for audit purposes
     */
    logRedaction(memoryId: string, types: string[], severity: 'low' | 'medium' | 'high' | 'critical', matchCount: number): void;
}
export declare const logger: Logger;
export { Logger };
//# sourceMappingURL=logger.d.ts.map