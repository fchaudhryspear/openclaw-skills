/**
 * Safety Module — Memory Vault Protection & Size Limits
 * 
 * Features:
 * - Automatic size limit enforcement (prevents unbounded growth)
 * - Soft delete with trash recovery
 * - Integrity checks for corruption detection
 * - Automatic backup before destructive operations
 */

import * as fs from 'fs';
import * as path from 'path';
import { Memory } from './types';
import { getVectorStore } from './vector-store';

const TRASH_DIR = path.join(process.env.HOME || '~', '.openclaw/workspace/clawvault/.trash');
const BACKUP_DIR = path.join(process.env.HOME || '~', '.openclaw/workspace/clawvault/.backups');
const INGESTION_LOG = path.join(process.env.HOME || '~', '.openclaw/workspace/memory/ingestion-log.jsonl');

export interface SafetyConfig {
  maxVaultSizeBytes?: number;      // Default: 1GB
  maxMemoryCount?: number;         // Default: 50000 memories
  retentionDays?: number;          // Auto-delete after X days (default: 365)
  autoBackup?: boolean;            // Backup before deletes (default: true)
  enableTrash?: boolean;           // Keep deleted items recoverable (default: true)
}

export interface SafetyStats {
  totalBytes: number;
  memoryCount: number;
  oldestMemoryAge: number; // milliseconds
  newestMemoryAge: number; // milliseconds
  trashSize: number;
  backupSize: number;
  healthScore: number; // 0-100
}

export class SafetyModule {
  private config: Required<SafetyConfig>;
  private lastHealthCheck: number = 0;

  constructor(config: SafetyConfig = {}) {
    this.config = {
      maxVaultSizeBytes: config.maxVaultSizeBytes ?? 1024 * 1024 * 1024, // 1GB
      maxMemoryCount: config.maxMemoryCount ?? 50000,
      retentionDays: config.retentionDays ?? 365,
      autoBackup: config.autoBackup ?? true,
      enableTrash: config.enableTrash ?? true
    };

    // Ensure directories exist
    [TRASH_DIR, BACKUP_DIR].forEach(dir => {
      if (!fs.existsSync(dir)) {
        fs.mkdirSync(dir, { recursive: true });
      }
    });

    console.log(`✅ Safety module initialized (max ${this.formatBytes(this.config.maxVaultSizeBytes)}, ${this.config.maxMemoryCount} memories)`);
  }

  // ── Core Safety Operations ────────────────────────────────────────────────

  /**
   * Check if new memory can be safely added
   */
  async canAddMemory(content: string): Promise<{ allowed: boolean; reason: string }> {
    const stats = await this.getStats();

    // Check size limits
    const estimatedSize = Buffer.byteLength(content, 'utf8') * 1.5; // Estimate including metadata
    
    if (stats.totalBytes + estimatedSize > this.config.maxVaultSizeBytes) {
      return {
        allowed: false,
        reason: `Vault would exceed size limit (${this.formatBytes(stats.totalBytes)} / ${this.formatBytes(this.config.maxVaultSizeBytes)})`
      };
    }

    // Check count limits
    if (stats.memoryCount >= this.config.maxMemoryCount) {
      return {
        allowed: false,
        reason: `Memory count limit reached (${stats.memoryCount}/${this.config.maxMemoryCount})`
      };
    }

    return { allowed: true, reason: 'OK' };
  }

  /**
   * Enforce size limits by deleting oldest memories
   */
  async enforceSizeLimits(): Promise<{ deleted: number; freedBytes: number }> {
    const vectorStore = getVectorStore();
    let currentBytes = await this.getDirSize(path.join(process.env.HOME || '~', '.openclaw/workspace/clawvault/vault'));
    
    const deleted: string[] = [];
    let freedBytes = 0;

    while (currentBytes > this.config.maxVaultSizeBytes * 0.9) { // Target 90% of limit
      // Get oldest memories
      const oldest = await vectorStore.listAll(10, 0);
      
      if (oldest.length === 0) break; // No more memories to delete

      // Delete oldest ones
      for (const memory of oldest) {
        await this.deleteMemory(memory.id);
        deleted.push(memory.id);
        
        const memSize = Buffer.byteLength(memory.content, 'utf8');
        freedBytes += memSize;
        currentBytes -= memSize;

        if (currentBytes <= this.config.maxVaultSizeBytes * 0.9) break;
      }
    }

    console.log(`🗑️  Enforced size limits: deleted ${deleted.length} memories, freed ${this.formatBytes(freedBytes)}`);
    return { deleted: deleted.length, freedBytes };
  }

  /**
   * Soft delete a memory (move to trash, not permanent)
   */
  async deleteMemory(memoryId: string): Promise<boolean> {
    try {
      // Create backup first
      if (this.config.autoBackup) {
        await this.backupMemory(memoryId);
      }

      // Read memory content
      const vaultPath = path.join(process.env.HOME || '~', '.openclaw/workspace/clawvault/vault');
      const memoryFile = path.join(vaultPath, `${memoryId}.json`);
      
      if (!fs.existsSync(memoryFile)) {
        return false;
      }

      const content = fs.readFileSync(memoryFile, 'utf8');
      const memory: Memory = JSON.parse(content);

      // Move to trash
      if (this.config.enableTrash) {
        const trashPath = path.join(TRASH_DIR, `${memoryId}.json`);
        fs.writeFileSync(trashPath, content);
        fs.unlinkSync(memoryFile);
      } else {
        fs.unlinkSync(memoryFile);
      }

      // Remove from vector store
      const vectorStore = getVectorStore();
      await vectorStore.delete(memoryId);

      // Log deletion
      this.logIngestion('delete', memoryId, null);

      return true;
    } catch (error) {
      console.error(`❌ Failed to delete memory ${memoryId}: ${(error as Error).message}`);
      return false;
    }
  }

  /**
   * Hard delete (permanent removal from trash)
   */
  async hardDelete(memoryId: string): Promise<boolean> {
    const trashPath = path.join(TRASH_DIR, `${memoryId}.json`);
    const vaultPath = path.join(process.env.HOME || '~', '.openclaw/workspace/clawvault/vault', `${memoryId}.json`);

    let deleted = false;
    let hardDeleted = false;
    
    if (fs.existsSync(trashPath)) {
      fs.unlinkSync(trashPath);
      deleted = true;
    }
    
    if (fs.existsSync(vaultPath)) {
      fs.unlinkSync(vaultPath);
      hardDeleted = true;
    }

    return deleted || hardDeleted;
  }

  /**
   * Restore a deleted memory from trash
   */
  async restoreMemory(memoryId: string): Promise<boolean> {
    try {
      const trashPath = path.join(TRASH_DIR, `${memoryId}.json`);
      const vaultPath = path.join(process.env.HOME || '~', '.openclaw/workspace/clawvault/vault', `${memoryId}.json`);

      if (!fs.existsSync(trashPath)) {
        return false;
      }

      const content = fs.readFileSync(trashPath, 'utf8');
      fs.writeFileSync(vaultPath, content);
      fs.unlinkSync(trashPath);

      // Re-index in vector store
      const memory: Memory = JSON.parse(content);
      const vectorStore = getVectorStore();
      await vectorStore.index(memory);

      // Log restoration
      this.logIngestion('restore', memoryId, null);

      return true;
    } catch (error) {
      console.error(`❌ Failed to restore memory ${memoryId}: ${(error as Error).message}`);
      return false;
    }
  }

  // ── Health & Integrity Checks ────────────────────────────────────────────

  /**
   * Comprehensive health check
   */
  async healthCheck(): Promise<{ score: number; issues: string[]; recommendations: string[] }> {
    const issues: string[] = [];
    const recommendations: string[] = [];

    // Check 1: Disk space usage
    const stats = await this.getStats();
    
    const usagePercent = (stats.totalBytes / this.config.maxVaultSizeBytes) * 100;
    if (usagePercent > 90) {
      issues.push(`⚠️  Vault at ${Math.round(usagePercent)}% capacity (${this.formatBytes(stats.totalBytes)} / ${this.formatBytes(this.config.maxVaultSizeBytes)})`);
      recommendations.push('Run cleanup or increase size limit');
    }

    // Check 2: Trash accumulation
    const trashStats = await this.getDirSize(TRASH_DIR);
    if (trashStats > 50 * 1024 * 1024) { // >50MB in trash
      issues.push(`⚠️  Trash contains ${this.formatBytes(trashStats)} - consider emptying`);
      recommendations.push('Empty trash to reclaim disk space');
    }

    // Check 3: Old backups
    const backupFiles = fs.readdirSync(BACKUP_DIR).filter(f => f.endsWith('.bak'));
    const oldBackups = backupFiles.filter(f => {
      const filePath = path.join(BACKUP_DIR, f);
      const mtime = fs.statSync(filePath).mtimeMs;
      return Date.now() - mtime > 7 * 24 * 60 * 60 * 1000; // Older than 7 days
    });

    if (oldBackups.length > 10) {
      issues.push(`⚠️  ${oldBackups.length} old backups (>7 days) consuming disk space`);
      recommendations.push('Run backup cleanup: rm ~/.openclaw/workspace/clawvault/.backups/*.bak');
    }

    // Check 4: Vector store integrity
    try {
      const vectorStore = getVectorStore();
      const count = await vectorStore.getCount();
      if (count > stats.memoryCount * 1.5 || count < stats.memoryCount * 0.5) {
        issues.push(`⚠️  Vector store count mismatch: ${count} vs ${stats.memoryCount} file-based`);
        recommendations.push('Rebuild vector index');
      }
    } catch (error) {
      issues.push(`❌ Vector store error: ${(error as Error).message}`);
    }

    // Calculate health score (0-100)
    let score = 100;
    score -= Math.min(30, Math.floor(usagePercent - 80)); // Up to 30 points off for high usage
    score -= Math.min(20, Math.floor(trashStats / (1024 * 1024))); // Up to 20 points for trash
    score -= Math.min(20, oldBackups.length * 2); // Up to 20 points for old backups
    score -= issues.filter(i => i.startsWith('❌')).length * 20; // 20 points per critical issue
    score = Math.max(0, score);

    this.lastHealthCheck = Date.now();

    return { score, issues, recommendations };
  }

  /**
   * Get detailed vault statistics
   */
  async getStats(): Promise<SafetyStats> {
    const vaultPath = path.join(process.env.HOME || '~', '.openclaw/workspace/clawvault/vault');
    const vectorStore = getVectorStore();

    // Count files and bytes
    let memoryCount = 0;
    let totalBytes = 0;
    let oldestTs = Date.now();
    let newestTs = 0;

    if (fs.existsSync(vaultPath)) {
      const files = fs.readdirSync(vaultPath).filter(f => f.endsWith('.json'));
      memoryCount = files.length;

      for (const file of files) {
        const filePath = path.join(vaultPath, file);
        const stats = fs.statSync(filePath);
        totalBytes += stats.size;

        // Parse timestamp from filename or content
        try {
          const content = fs.readFileSync(filePath, 'utf8');
          const memory = JSON.parse(content);
          const ts = memory.createdAtMs || stats.mtimeMs;
          oldestTs = Math.min(oldestTs, ts);
          newestTs = Math.max(newestTs, ts);
        } catch (e) {
          // Skip corrupted files
        }
      }
    }

    // Vector store count for comparison
    let vectorCount = 0;
    try {
      vectorCount = await vectorStore.getCount();
    } catch (e) {
      // Non-fatal
    }

    return {
      totalBytes,
      memoryCount,
      oldestMemoryAge: Date.now() - oldestTs,
      newestMemoryAge: Date.now() - newestTs,
      trashSize: await this.getDirSize(TRASH_DIR),
      backupSize: await this.getDirSize(BACKUP_DIR),
      healthScore: 0 // Will be calculated by healthCheck()
    };
  }

  // ── Backup & Recovery ────────────────────────────────────────────────────

  /**
   * Create full vault backup
   */
  async createBackup(): Promise<string> {
    const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
    const backupPath = path.join(BACKUP_DIR, `vault-backup-${timestamp}.tar.gz`);

    try {
      const { execSync } = require('child_process');
      const vaultPath = path.join(process.env.HOME || '~', '.openclaw/workspace/clawvault/vault');
      
      execSync(`tar -czf "${backupPath}" -C "${path.dirname(vaultPath)}" "vault"`, { stdio: 'pipe' });
      
      console.log(`✅ Backup created: ${backupPath}`);
      return backupPath;
    } catch (error) {
      console.error('❌ Backup creation failed:', (error as Error).message);
      throw error;
    }
  }

  /**
   * Backup single memory
   */
  private async backupMemory(memoryId: string): Promise<void> {
    const vaultPath = path.join(process.env.HOME || '~', '.openclaw/workspace/clawvault/vault', `${memoryId}.json`);
    const backupPath = path.join(BACKUP_DIR, `${memoryId}.${Date.now()}.bak`);

    if (fs.existsSync(vaultPath)) {
      fs.copyFileSync(vaultPath, backupPath);
    }
  }

  /**
   * Cleanup old backups (keep last 10)
   */
  async cleanupBackups(keepCount: number = 10): Promise<number> {
    const files = fs.readdirSync(BACKUP_DIR)
      .filter(f => f.endsWith('.bak'))
      .sort()
      .reverse();

    const toDelete = files.slice(keepCount);
    let deleted = 0;

    for (const file of toDelete) {
      try {
        fs.unlinkSync(path.join(BACKUP_DIR, file));
        deleted++;
      } catch (e) {
        // Skip failures
      }
    }

    return deleted;
  }

  // ── Utility Methods ──────────────────────────────────────────────────────

  /**
   * Empty trash permanently
   */
  async emptyTrash(): Promise<number> {
    const files = fs.readdirSync(TRASH_DIR).filter(f => f.endsWith('.json'));
    
    for (const file of files) {
      try {
        fs.unlinkSync(path.join(TRASH_DIR, file));
      } catch (e) {
        // Skip failures
      }
    }

    return files.length;
  }

  /**
   * Log ingestion events for auditing
   */
  private logIngestion(action: string, memoryId: string, data: any | null): void {
    try {
      const entry = {
        ts: new Date().toISOString(),
        action,
        memoryId,
        data: data || {}
      };
      fs.appendFileSync(INGESTION_LOG, JSON.stringify(entry) + '\n');
    } catch (e) {
      // Non-fatal
    }
  }

  /**
   * Get directory size recursively
   */
  private async getDirSize(dirPath: string): Promise<number> {
    if (!fs.existsSync(dirPath)) return 0;

    let total = 0;
    const files = fs.readdirSync(dirPath);
    
    for (const file of files) {
      const filePath = path.join(dirPath, file);
      const stats = fs.statSync(filePath);
      
      if (stats.isDirectory()) {
        total += await this.getDirSize(filePath);
      } else {
        total += stats.size;
      }
    }

    return total;
  }

  private formatBytes(bytes: number): string {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(2)} KB`;
    if (bytes < 1024 * 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
    return `${(bytes / (1024 * 1024 * 1024)).toFixed(2)} GB`;
  }
}

// Export singleton instance
export const safetyModule = new SafetyModule();

// Convenience functions
export async function canAddMemory(content: string): Promise<{ allowed: boolean; reason: string }> {
  return safetyModule.canAddMemory(content);
}

export async function enforceSizeLimits(): Promise<{ deleted: number; freedBytes: number }> {
  return safetyModule.enforceSizeLimits();
}

export async function getSafetyStats(): Promise<SafetyStats> {
  return safetyModule.getStats();
}

export async function healthCheck(): Promise<{ score: number; issues: string[]; recommendations: string[] }> {
  return safetyModule.healthCheck();
}
