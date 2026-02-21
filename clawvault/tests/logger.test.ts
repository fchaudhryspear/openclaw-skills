/**
 * Logger Tests
 * 
 * Tests for the audit logging functionality.
 */

import { logger, Logger } from '../src/logger';

describe('Logger', () => {
  let testLogger: Logger;
  let logEntries: any[] = [];

  beforeEach(() => {
    testLogger = new Logger();
    logEntries = [];
    testLogger.configure({
      enableConsole: false,
      minLevel: 'debug',
      logCallback: (entry) => logEntries.push(entry)
    });
  });

  describe('Log Levels', () => {
    test('should log debug messages', () => {
      testLogger.debug('Debug message');
      expect(logEntries).toHaveLength(1);
      expect(logEntries[0].level).toBe('debug');
      expect(logEntries[0].message).toBe('Debug message');
    });

    test('should log info messages', () => {
      testLogger.info('Info message');
      expect(logEntries).toHaveLength(1);
      expect(logEntries[0].level).toBe('info');
    });

    test('should log warning messages', () => {
      testLogger.warn('Warning message');
      expect(logEntries).toHaveLength(1);
      expect(logEntries[0].level).toBe('warn');
    });

    test('should log error messages', () => {
      testLogger.error('Error message');
      expect(logEntries).toHaveLength(1);
      expect(logEntries[0].level).toBe('error');
    });
  });

  describe('Log Filtering', () => {
    test('should filter by minimum level', () => {
      testLogger.configure({ enableConsole: false, minLevel: 'warn' });
      
      testLogger.debug('Debug');
      testLogger.info('Info');
      testLogger.warn('Warn');
      testLogger.error('Error');

      expect(logEntries).toHaveLength(2);
      expect(logEntries[0].level).toBe('warn');
      expect(logEntries[1].level).toBe('error');
    });

    test('should include metadata in log entries', () => {
      testLogger.info('Message with metadata', { userId: '123', action: 'login' });
      
      expect(logEntries[0].metadata).toEqual({ userId: '123', action: 'login' });
    });

    test('should include timestamp in log entries', () => {
      testLogger.info('Test');
      
      expect(logEntries[0].timestamp).toBeDefined();
      expect(new Date(logEntries[0].timestamp)).toBeInstanceOf(Date);
    });
  });

  describe('Redaction Logging', () => {
    test('should log redaction events', () => {
      testLogger.logRedaction('mem_123', ['Email Address'], 'medium', 1);

      expect(logEntries).toHaveLength(1);
      expect(logEntries[0].level).toBe('warn');
      expect(logEntries[0].message).toBe('Sensitive data redacted from memory');
      expect(logEntries[0].metadata).toEqual({
        memoryId: 'mem_123',
        redactedTypes: ['Email Address'],
        highestSeverity: 'medium',
        matchCount: 1,
        action: 'REDACTED'
      });
    });

    test('should handle multiple redaction types', () => {
      testLogger.logRedaction(
        'mem_456',
        ['Email Address', 'Phone Number', 'API Key'],
        'critical',
        5
      );

      expect(logEntries[0].metadata.redactedTypes).toHaveLength(3);
      expect(logEntries[0].metadata.highestSeverity).toBe('critical');
      expect(logEntries[0].metadata.matchCount).toBe(5);
    });
  });

  describe('Global Logger', () => {
    test('global logger should be configured', () => {
      expect(logger).toBeDefined();
      expect(typeof logger.info).toBe('function');
      expect(typeof logger.warn).toBe('function');
      expect(typeof logger.error).toBe('function');
      expect(typeof logger.logRedaction).toBe('function');
    });
  });
});
