/**
 * Audit Trail System - Complete logging of all operations
 */

import { AuditEntry, AuditAction, Node, Edge } from '../model/types';
import { EncryptedStore } from '../storage/encrypted-store';

export interface AuditOptions {
  logReads: boolean;
  logWrites: boolean;
  logDeletes: boolean;
  logAccessDenied: boolean;
  retentionDays: number;
}

export class Auditor {
  private store: EncryptedStore;
  private options: AuditOptions;
  private buffer: AuditEntry[];
  private bufferFlushInterval: NodeJS.Timeout | null;

  constructor(
    store: EncryptedStore,
    options: Partial<AuditOptions> = {}
  ) {
    this.store = store;
    this.options = {
      logReads: options.logReads ?? true,
      logWrites: options.logWrites ?? true,
      logDeletes: options.logDeletes ?? true,
      logAccessDenied: options.logAccessDenied ?? true,
      retentionDays: options.retentionDays ?? 90,
      ...options,
    };
    this.buffer = [];
    
    // Flush buffer every 5 minutes
    this.bufferFlushInterval = setInterval(() => this.flushBuffer(), 5 * 60 * 1000);
  }

  /**
   * Generate unique ID for audit entry
   */
  private generateId(): string {
    return `audit_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }

  /**
   * Log a node operation
   */
  async logNodeOperation(
    action: AuditAction,
    nodeId: string,
    userId: string,
    changes?: { before?: Node; after?: Node },
    metadata?: Record<string, unknown>
  ): Promise<void> {
    if (!this.shouldLog(action)) return;

    const entry: AuditEntry = {
      id: this.generateId(),
      timestamp: new Date(),
      action,
      userId,
      entityType: 'node',
      entityId: nodeId,
      changes,
      metadata,
    };

    await this.addEntry(entry);
  }

  /**
   * Log an edge operation
   */
  async logEdgeOperation(
    action: AuditAction,
    edgeId: string,
    userId: string,
    changes?: { before?: Edge; after?: Edge },
    metadata?: Record<string, unknown>
  ): Promise<void> {
    if (!this.shouldLog(action)) return;

    const entry: AuditEntry = {
      id: this.generateId(),
      timestamp: new Date(),
      action,
      userId,
      entityType: 'edge',
      entityId: edgeId,
      changes,
      metadata,
    };

    await this.addEntry(entry);
  }

  /**
   * Log an access denial
   */
  async logAccessDenial(
    nodeId: string,
    userId: string,
    action: string,
    ipAddress?: string
  ): Promise<void> {
    if (!this.options.logAccessDenied) return;

    const entry: AuditEntry = {
      id: this.generateId(),
      timestamp: new Date(),
      action: AuditAction.AUTH_FAILED,
      userId,
      entityType: 'node',
      entityId: nodeId,
      ipAddress,
      metadata: { deniedAction: action },
    };

    await this.addEntry(entry);
  }

  /**
   * Log permission change
   */
  async logPermissionChange(
    nodeId: string,
    userId: string,
    targetUserId: string,
    granted: boolean,
    ipAddress?: string
  ): Promise<void> {
    const action = granted 
      ? AuditAction.ACCESS_GRANTED 
      : AuditAction.ACCESS_REVOKED;

    const entry: AuditEntry = {
      id: this.generateId(),
      timestamp: new Date(),
      action,
      userId,
      entityType: 'permission',
      entityId: nodeId,
      ipAddress,
      metadata: { targetUserId, granted },
    };

    await this.addEntry(entry);
  }

  /**
   * Log schema change
   */
  async logSchemaChange(
    userId: string,
    entityType: 'node' | 'edge',
    typeName: string,
    changes: Record<string, unknown>,
    ipAddress?: string
  ): Promise<void> {
    const entry: AuditEntry = {
      id: this.generateId(),
      timestamp: new Date(),
      action: AuditAction.SCHEMA_CHANGE,
      userId,
      entityType: 'schema',
      entityId: `${entityType}_${typeName}`,
      ipAddress,
      changes: { after: changes },
    };

    await this.addEntry(entry);
  }

  /**
   * Check if action should be logged
   */
  private shouldLog(action: AuditAction): boolean {
    switch (action) {
      case AuditAction.READ:
        return this.options.logReads;
      case AuditAction.CREATE:
      case AuditAction.UPDATE:
        return this.options.logWrites;
      case AuditAction.DELETE:
        return this.options.logDeletes;
      default:
        return true;
    }
  }

  /**
   * Add entry to buffer or directly to storage
   */
  private async addEntry(entry: AuditEntry): Promise<void> {
    // Buffer small entries for batch write
    this.buffer.push(entry);
    
    // Flush if buffer gets too large
    if (this.buffer.length >= 100) {
      await this.flushBuffer();
    }
  }

  /**
   * Flush buffer to persistent storage
   */
  async flushBuffer(): Promise<void> {
    if (this.buffer.length === 0) return;

    try {
      const entries = [...this.buffer];
      this.buffer = [];
      
      for (const entry of entries) {
        await this.store.appendAudit(entry);
      }
    } catch (error) {
      console.error('Failed to flush audit buffer:', error);
      // Re-add entries to buffer on failure
      this.buffer.unshift(...this.buffer);
    }
  }

  /**
   * Query audit log
   */
  async queryAuditLog(options: {
    userId?: string;
    entityType?: string;
    entityId?: string;
    action?: AuditAction;
    since?: Date;
    until?: Date;
    limit?: number;
  }): Promise<AuditEntry[]> {
    const entries = await this.store.readAudit();
    
    let filtered = entries.filter(entry => {
      if (options.userId && entry.userId !== options.userId) return false;
      if (options.entityType && entry.entityType !== options.entityType) return false;
      if (options.entityId && entry.entityId !== options.entityId) return false;
      if (options.action && entry.action !== options.action) return false;
      if (options.since && entry.timestamp < options.since) return false;
      if (options.until && entry.timestamp > options.until) return false;
      return true;
    });

    // Sort by timestamp descending
    filtered.sort((a, b) => b.timestamp.getTime() - a.timestamp.getTime());

    // Apply limit
    if (options.limit) {
      filtered = filtered.slice(0, options.limit);
    }

    return filtered;
  }

  /**
   * Get user activity summary
   */
  async getUserActivity(userId: string, days: number = 7): Promise<{
    totalOperations: number;
    nodesCreated: number;
    nodesUpdated: number;
    nodesDeleted: number;
    accessesDenied: number;
    lastActivity: Date | null;
  }> {
    const since = new Date();
    since.setDate(since.getDate() - days);

    const entries = await this.queryAuditLog({
      userId,
      since,
    });

    const summary = {
      totalOperations: 0,
      nodesCreated: 0,
      nodesUpdated: 0,
      nodesDeleted: 0,
      accessesDenied: 0,
      lastActivity: null,
    };

    for (const entry of entries) {
      summary.totalOperations++;
      
      switch (entry.action) {
        case AuditAction.CREATE:
          if (entry.entityType === 'node') summary.nodesCreated++;
          break;
        case AuditAction.UPDATE:
          if (entry.entityType === 'node') summary.nodesUpdated++;
          break;
        case AuditAction.DELETE:
          if (entry.entityType === 'node') summary.nodesDeleted++;
          break;
        case AuditAction.AUTH_FAILED:
          summary.accessesDenied++;
          break;
      }

      if (!summary.lastActivity || entry.timestamp > summary.lastActivity) {
        summary.lastActivity = entry.timestamp;
      }
    }

    return summary;
  }

  /**
   * Export audit log for compliance
   */
  async exportAuditLog(options: {
    format: 'json' | 'csv';
    since?: Date;
    until?: Date;
  }): Promise<string> {
    const entries = await this.queryAuditLog({
      since: options.since,
      until: options.until,
    });

    if (options.format === 'json') {
      return JSON.stringify(entries, null, 2);
    }

    // CSV format
    const headers = [
      'Timestamp',
      'ID',
      'User',
      'Action',
      'Entity Type',
      'Entity ID',
      'IP Address',
    ];
    
    const rows = entries.map(entry => [
      entry.timestamp.toISOString(),
      entry.id,
      entry.userId,
      entry.action,
      entry.entityType,
      entry.entityId,
      entry.ipAddress || '',
    ]);

    return [headers, ...rows].map(row => row.join(',')).join('\n');
  }

  /**
   * Clean old audit entries based on retention policy
   */
  async cleanupOldEntries(): Promise<number> {
    const cutoffDate = new Date();
    cutoffDate.setDate(cutoffDate.getDate() - this.options.retentionDays);

    const entries = await this.store.readAudit();
    const retained = entries.filter(entry => entry.timestamp > cutoffDate);
    const removed = entries.length - retained.length;

    if (removed > 0) {
      await this.store.writeAudit(retained);
    }

    return removed;
  }

  /**
   * Get security anomalies
   */
  async detectAnomalies(options: {
    failedAttemptsThreshold: number;
    timeWindowMinutes: number;
  }): Promise<Array<{
    userId: string;
    anomalyType: 'brute_force' | 'unusual_access' | 'data_exfiltration';
    details: Record<string, unknown>;
    severity: 'low' | 'medium' | 'high';
  }>> {
    const since = new Date();
    since.setMinutes(since.getMinutes() - options.timeWindowMinutes);

    const entries = await this.queryAuditLog({
      since,
      action: AuditAction.AUTH_FAILED,
    });

    // Count failed attempts per user
    const failedByUser = new Map<string, number>();
    for (const entry of entries) {
      failedByUser.set(
        entry.userId,
        (failedByUser.get(entry.userId) || 0) + 1
      );
    }

    const anomalies: Array<{
      userId: string;
      anomalyType: string;
      details: Record<string, unknown>;
      severity: string;
    }> = [];

    for (const [userId, count] of failedByUser.entries()) {
      if (count >= options.failedAttemptsThreshold) {
        anomalies.push({
          userId,
          anomalyType: 'brute_force',
          details: { attemptCount: count, window: `${options.timeWindowMinutes}m` },
          severity: count > options.failedAttemptsThreshold * 2 ? 'high' : 'medium',
        });
      }
    }

    return anomalies;
  }

  /**
   * Shutdown and flush remaining entries
   */
  async shutdown(): Promise<void> {
    if (this.bufferFlushInterval) {
      clearInterval(this.bufferFlushInterval);
      this.bufferFlushInterval = null;
    }
    await this.flushBuffer();
  }

  /**
   * Create auditor instance from config
   */
  static create(store: EncryptedStore, options?: Partial<AuditOptions>): Auditor {
    return new Auditor(store, options);
  }
}
