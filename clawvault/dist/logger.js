"use strict";
/**
 * Audit Logger Module
 *
 * Logs warnings when sensitive data redaction occurs for security auditing.
 */
Object.defineProperty(exports, "__esModule", { value: true });
exports.Logger = exports.logger = void 0;
const LOG_LEVELS = {
    debug: 0,
    info: 1,
    warn: 2,
    error: 3
};
class Logger {
    config = {
        minLevel: 'info',
        enableConsole: true
    };
    configure(config) {
        this.config = { ...this.config, ...config };
    }
    shouldLog(level) {
        return LOG_LEVELS[level] >= LOG_LEVELS[this.config.minLevel];
    }
    log(level, message, metadata) {
        if (!this.shouldLog(level))
            return;
        const entry = {
            timestamp: new Date().toISOString(),
            level,
            message,
            metadata
        };
        if (this.config.enableConsole) {
            const consoleMethod = level === 'error' ? console.error :
                level === 'warn' ? console.warn :
                    level === 'debug' ? console.debug : console.log;
            if (metadata) {
                consoleMethod(`[${entry.timestamp}] [${level.toUpperCase()}] ${message}`, metadata);
            }
            else {
                consoleMethod(`[${entry.timestamp}] [${level.toUpperCase()}] ${message}`);
            }
        }
        if (this.config.logCallback) {
            this.config.logCallback(entry);
        }
    }
    debug(message, metadata) {
        this.log('debug', message, metadata);
    }
    info(message, metadata) {
        this.log('info', message, metadata);
    }
    warn(message, metadata) {
        this.log('warn', message, metadata);
    }
    error(message, metadata) {
        this.log('error', message, metadata);
    }
    /**
     * Log a redaction event for audit purposes
     */
    logRedaction(memoryId, types, severity, matchCount) {
        this.warn('Sensitive data redacted from memory', {
            memoryId,
            redactedTypes: types,
            highestSeverity: severity,
            matchCount,
            action: 'REDACTED'
        });
    }
}
exports.Logger = Logger;
exports.logger = new Logger();
//# sourceMappingURL=logger.js.map