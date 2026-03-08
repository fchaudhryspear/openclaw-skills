/**
 * Session Manager — Cross-Session Continuity & Tracking
 * 
 * Features:
 * - Track which session created each memory
 * - Enable shared memory access across multiple agents
 * - Prevent duplicate writes from concurrent sessions
 * - Session lifecycle management (start, pause, resume, end)
 */

import * as fs from 'fs';
import * as path from 'path';
import { Memory } from './types';
import { getVectorStore } from './vector-store';

const SESSIONS_FILE = path.join(process.env.HOME || '~', '.openclaw/workspace/clawvault/.sessions.json');
const LOCK_FILE = path.join(process.env.HOME || '~', '.openclaw/workspace/clawvault/.lock');

export interface SessionInfo {
  sessionId: string;
  name: string;
  startedAtMs: number;
  lastActiveAtMs: number;
  memoryCount: number;
  status: 'active' | 'paused' | 'completed';
  metadata?: Record<string, any>;
}

export interface WriteLock {
  lockId: string;
  sessionId: string;
  lockedAtMs: number;
  expiresAtMs: number;
  operation: 'index' | 'delete' | 'bulk';
}

export class SessionManager {
  private currentSession: SessionInfo | null = null;
  private writeLock: WriteLock | null = null;
  private heartbeatInterval: NodeJS.Timeout | null = null;
  private lockTimeoutMs = 30000; // 30 second lock timeout
  private heartbeatIntervalMs = 10000; // 10 second heartbeat

  constructor() {
    this.loadSessions();
  }

  // ── Session Lifecycle ────────────────────────────────────────────────────

  /**
   * Start a new session
   */
  async startSession(name: string, metadata?: Record<string, any>): Promise<SessionInfo> {
    const sessionId = `session-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
    
    const session: SessionInfo = {
      sessionId,
      name,
      startedAtMs: Date.now(),
      lastActiveAtMs: Date.now(),
      memoryCount: 0,
      status: 'active',
      metadata
    };

    this.currentSession = session;
    await this.saveSessions();
    
    // Start heartbeat
    this.startHeartbeat();

    console.log(`✅ Session started: ${sessionId} (${name})`);
    return session;
  }

  /**
   * Pause current session
   */
  async pauseSession(): Promise<void> {
    if (!this.currentSession) return;

    this.currentSession.status = 'paused';
    this.stopHeartbeat();
    await this.releaseLock();
    await this.saveSessions();

    console.log(`⏸️  Session paused: ${this.currentSession.sessionId}`);
  }

  /**
   * Resume a paused session
   */
  async resumeSession(sessionId: string): Promise<boolean> {
    const sessions = this.getOrCreateSessions();
    const session = sessions.find(s => s.sessionId === sessionId);
    
    if (!session || session.status !== 'paused') {
      return false;
    }

    session.status = 'active';
    session.lastActiveAtMs = Date.now();
    this.currentSession = session;
    
    this.startHeartbeat();
    await this.saveSessions();

    console.log(`▶️  Session resumed: ${sessionId}`);
    return true;
  }

  /**
   * End current session
   */
  async endSession(flushToDisk: boolean = true): Promise<void> {
    if (!this.currentSession) return;

    this.currentSession.status = 'completed';
    this.currentSession.lastActiveAtMs = Date.now();
    this.stopHeartbeat();
    
    if (flushToDisk) {
      await this.persistMemoryState();
    }

    await this.releaseLock();
    await this.saveSessions();

    console.log(`✅ Session ended: ${this.currentSession.sessionId}`);
    this.currentSession = null;
  }

  /**
   * Get current active session
   */
  getCurrentSession(): SessionInfo | null {
    if (this.currentSession) {
      this.currentSession.lastActiveAtMs = Date.now();
      this.saveSessions().catch(() => {}); // Non-fatal
    }
    return this.currentSession;
  }

  // ── Concurrent Access Control ────────────────────────────────────────────

  /**
   * Acquire write lock for concurrent operations
   */
  async acquireLock(operation: 'index' | 'delete' | 'bulk'): Promise<boolean> {
    if (!this.currentSession) {
      console.warn('⚠️  No active session to acquire lock');
      return false;
    }

    // Check for existing expired locks
    this.cleanupExpiredLocks();

    const lockPath = LOCK_FILE;
    
    // Try to create exclusive lock
    try {
      if (fs.existsSync(lockPath)) {
        const lockData = JSON.parse(fs.readFileSync(lockPath, 'utf8'));
        
        // Check if lock is still valid
        if (Date.now() < lockData.expiresAtMs) {
          console.warn(`⚠️  Lock already held by ${lockData.sessionId}`);
          return false;
        }
      }

      // Create new lock
      const lock: WriteLock = {
        lockId: `lock-${Date.now()}`,
        sessionId: this.currentSession.sessionId,
        lockedAtMs: Date.now(),
        expiresAtMs: Date.now() + this.lockTimeoutMs,
        operation
      };

      fs.writeFileSync(lockPath, JSON.stringify(lock), 'utf8');
      this.writeLock = lock;

      return true;
    } catch (error) {
      console.error('❌ Failed to acquire lock:', (error as Error).message);
      return false;
    }
  }

  /**
   * Release write lock
   */
  async releaseLock(): Promise<void> {
    const lockPath = LOCK_FILE;
    
    if (fs.existsSync(lockPath)) {
      try {
        fs.unlinkSync(lockPath);
      } catch (e) {
        // Ignore errors
      }
    }

    this.writeLock = null;
  }

  /**
   * Check if we hold current lock
   */
  hasLock(): boolean {
    if (!this.writeLock) return false;
    return Date.now() < this.writeLock.expiresAtMs;
  }

  // ── Cross-Session Coordination ───────────────────────────────────────────

  /**
   * Get all active sessions
   */
  getActiveSessions(): SessionInfo[] {
    const sessions = this.getOrCreateSessions();
    return sessions.filter(s => s.status === 'active' && Date.now() - s.lastActiveAtMs < 5 * 60 * 1000); // Active in last 5min
  }

  /**
   * Find session by ID
   */
  getSession(sessionId: string): SessionInfo | null {
    const sessions = this.getOrCreateSessions();
    return sessions.find(s => s.sessionId === sessionId) || null;
  }

  /**
   * List all sessions (including completed)
   */
  listAllSessions(limit: number = 50): SessionInfo[] {
    const sessions = this.getOrCreateSessions();
    return sessions
      .sort((a, b) => b.startedAtMs - a.startedAtMs)
      .slice(0, limit);
  }

  /**
   * Cleanup stale sessions
   */
  async cleanupStaleSessions(maxAgeMinutes: number = 60): Promise<number> {
    const sessions = this.getOrCreateSessions();
    const now = Date.now();
    const maxAgeMs = maxAgeMinutes * 60 * 1000;

    let cleaned = 0;
    const updated = sessions.filter(s => {
      const isStale = s.status === 'active' && (now - s.lastActiveAtMs > maxAgeMs);
      
      if (isStale) {
        console.log(`🗑️  Cleaning up stale session: ${s.sessionId}`);
        cleaned++;
        return false;
      }
      return true;
    });

    if (updated.length !== sessions.length) {
      this.writeSessions(updated);
    }

    return cleaned;
  }

  // ── Memory Integration ───────────────────────────────────────────────────

  /**
   * Tag memory with session info during creation
   */
  tagMemoryWithSession(memory: Memory): Memory {
    if (!this.currentSession) return memory;

    return {
      ...memory,
      metadata: {
        ...memory.metadata,
        createdBySession: this.currentSession.sessionId,
        createdByAgent: this.currentSession.name,
        createdAt: Date.now()
      }
    };
  }

  /**
   * Get memories created by specific session
   */
  async getMemoriesBySession(sessionId: string): Promise<Memory[]> {
    const vectorStore = getVectorStore();
    const allMemories = await vectorStore.listAll(10000); // Get all
    
    return allMemories.filter(m => m.metadata?.createdBySession === sessionId);
  }

  /**
   * Count memories created by current session
   */
  getSessionMemoryCount(): number {
    if (!this.currentSession) return 0;
    return this.currentSession.memoryCount;
  }

  /**
   * Increment memory count for current session
   */
  incrementMemoryCount(count: number = 1): void {
    if (this.currentSession) {
      this.currentSession.memoryCount += count;
      this.saveSessions().catch(() => {}); // Non-fatal
    }
  }

  // ── Persistence ──────────────────────────────────────────────────────────

  /**
   * Save session state to disk
   */
  private async saveSessions(): Promise<void> {
    const sessions = this.getOrCreateSessions();
    this.writeSessions(sessions);
  }

  /**
   * Load sessions from disk
   */
  private loadSessions(): void {
    try {
      if (!fs.existsSync(SESSIONS_FILE)) {
        console.log('ℹ️  No session file found, starting fresh');
        return;
      }

      const data = JSON.parse(fs.readFileSync(SESSIONS_FILE, 'utf8'));
      console.log(`✅ Loaded ${data.sessions?.length || 0} previous sessions`);
    } catch (error) {
      console.error('❌ Failed to load sessions:', (error as Error).message);
    }
  }

  /**
   * Persist current memory state to disk
   */
  private async persistMemoryState(): Promise<void> {
    if (!this.currentSession) return;

    try {
      const stateFile = path.join(process.env.HOME || '~', `.openclaw/workspace/clawvault/.states/${this.currentSession.sessionId}.json`);
      
      // Ensure states directory exists
      const statesDir = path.dirname(stateFile);
      if (!fs.existsSync(statesDir)) {
        fs.mkdirSync(statesDir, { recursive: true });
      }

      fs.writeFileSync(stateFile, JSON.stringify({
        sessionId: this.currentSession.sessionId,
        lastActiveAtMs: this.currentSession.lastActiveAtMs,
        memoryCount: this.currentSession.memoryCount,
        timestamp: Date.now()
      }, null, 2));
    } catch (error) {
      console.error('❌ Failed to persist state:', (error as Error).message);
    }
  }

  // ── Background Maintenance ───────────────────────────────────────────────

  /**
   * Start heartbeat loop
   */
  private startHeartbeat(): void {
    this.stopHeartbeat(); // Clear any existing interval
    
    this.heartbeatInterval = setInterval(() => {
      if (this.currentSession) {
        this.currentSession.lastActiveAtMs = Date.now();
        this.saveSessions().catch(() => {}); // Non-fatal
      }
    }, this.heartbeatIntervalMs);
  }

  /**
   * Stop heartbeat loop
   */
  private stopHeartbeat(): void {
    if (this.heartbeatInterval) {
      clearInterval(this.heartbeatInterval);
      this.heartbeatInterval = null;
    }
  }

  /**
   * Remove expired locks from other sessions
   */
  private cleanupExpiredLocks(): void {
    const lockPath = LOCK_FILE;
    
    if (!fs.existsSync(lockPath)) return;

    try {
      const lockData = JSON.parse(fs.readFileSync(lockPath, 'utf8'));
      
      if (Date.now() > lockData.expiresAtMs) {
        fs.unlinkSync(lockPath);
        console.log(`✅ Released expired lock from ${lockData.sessionId}`);
      }
    } catch (e) {
      // Ignore parse errors
    }
  }

  // ── Internal Helpers ─────────────────────────────────────────────────────

  private getOrCreateSessions(): SessionInfo[] {
    try {
      if (!fs.existsSync(SESSIONS_FILE)) {
        return [];
      }

      const data = JSON.parse(fs.readFileSync(SESSIONS_FILE, 'utf8'));
      return data.sessions || [];
    } catch (error) {
      return [];
    }
  }

  private writeSessions(sessions: SessionInfo[]): void {
    try {
      const data = {
        lastUpdated: Date.now(),
        sessions
      };
      fs.writeFileSync(SESSIONS_FILE, JSON.stringify(data, null, 2));
    } catch (error) {
      console.error('❌ Failed to write sessions:', (error as Error).message);
    }
  }
}

// Export singleton instance
export const sessionManager = new SessionManager();

// Convenience functions
export async function startSession(name: string, metadata?: Record<string, any>): Promise<SessionInfo> {
  return sessionManager.startSession(name, metadata);
}

export async function endSession(): Promise<void> {
  await sessionManager.endSession();
}

export async function acquireLock(operation: 'index' | 'delete' | 'bulk'): Promise<boolean> {
  return sessionManager.acquireLock(operation);
}

export function getCurrentSession(): SessionInfo | null {
  return sessionManager.getCurrentSession();
}
