/**
 * ClawVault Scheduler
 * 
 * Automated scheduling for memory lifecycle operations:
 * - Nightly consolidation (3 AM)
 * - Weekly pruning (Sunday 4 AM)
 * - Daily trash cleanup (5 AM)
 */

import { ClawVault } from './index.js';
import { MemoryConsolidator } from './consolidation.js';
import { MemoryPruner } from './pruning.js';
import * as fs from 'fs';
import * as path from 'path';

export interface SchedulerConfig {
  /** Enable nightly consolidation (default: true) */
  enableConsolidation?: boolean;
  /** Consolidation time in 24h format (default: "03:00") */
  consolidationTime?: string;
  
  /** Enable weekly pruning (default: true) */
  enablePruning?: boolean;
  /** Pruning day of week (0 = Sunday, default: 0) */
  pruningDayOfWeek?: number;
  /** Pruning time in 24h format (default: "04:00") */
  pruningTime?: string;
  
  /** Enable daily trash cleanup (default: true) */
  enableTrashCleanup?: boolean;
  /** Trash cleanup time (default: "05:00") */
  trashCleanupTime?: string;
  
  /** Log file path */
  logFile?: string;
  
  /** Dry run mode (no actual changes) */
  dryRun?: boolean;
}

export interface SchedulerStats {
  lastConsolidation?: { timestamp: number; result: any };
  lastPruning?: { timestamp: number; result: any };
  lastTrashCleanup?: { timestamp: number; result: any };
  totalRuns: number;
  errors: number;
}

export class ClawVaultScheduler {
  private vault: ClawVault;
  private config: SchedulerConfig;
  private statsPath: string;
  private stats: SchedulerStats;
  private timers: NodeJS.Timeout[] = [];

  constructor(vault: ClawVault, config: SchedulerConfig = {}) {
    this.vault = vault;
    this.config = {
      enableConsolidation: true,
      consolidationTime: '03:00',
      enablePruning: true,
      pruningDayOfWeek: 0, // Sunday
      pruningTime: '04:00',
      enableTrashCleanup: true,
      trashCleanupTime: '05:00',
      logFile: '~/memory/.clawvault-scheduler.log',
      dryRun: false,
      ...config
    };

    this.statsPath = path.join(
      process.env.HOME || require('os').homedir(),
      'memory',
      '.clawvault-scheduler-stats.json'
    );

    this.stats = this.loadStats();
  }

  /**
   * Start all scheduled tasks
   */
  start(): void {
    console.log('🕐 Starting ClawVault Scheduler...');

    if (this.config.enableConsolidation) {
      const timer = this.scheduleDaily(this.config.consolidationTime!, () => {
        this.runConsolidation().catch(err => this.logError('Consolidation', err));
      });
      this.timers.push(timer);
      console.log(`   ✅ Consolidation scheduled for ${this.config.consolidationTime}`);
    }

    if (this.config.enablePruning) {
      const timer = this.scheduleWeekly(this.config.pruningDayOfWeek!, this.config.pruningTime!, () => {
        this.runPruning().catch(err => this.logError('Pruning', err));
      });
      this.timers.push(timer);
      console.log(`   ✅ Pruning scheduled for Sundays at ${this.config.pruningTime}`);
    }

    if (this.config.enableTrashCleanup) {
      const timer = this.scheduleDaily(this.config.trashCleanupTime!, () => {
        this.runTrashCleanup().catch(err => this.logError('Trash Cleanup', err));
      });
      this.timers.push(timer);
      console.log(`   ✅ Trash cleanup scheduled for ${this.config.trashCleanupTime}`);
    }

    this.log('Scheduler started');
  }

  /**
   * Stop all scheduled tasks
   */
  stop(): void {
    for (const timer of this.timers) {
      clearTimeout(timer);
    }
    this.timers = [];
    console.log('🛑 Scheduler stopped');
    this.log('Scheduler stopped');
  }

  /**
   * Run consolidation immediately
   */
  async runConsolidation(): Promise<any> {
    console.log('\n🔄 Running manual consolidation...');
    
    const consolidator = new MemoryConsolidator(this.vault, {
      createBackup: true
    });

    const result = await consolidator.consolidate();
    
    this.stats.lastConsolidation = {
      timestamp: Date.now(),
      result: {
        clustersProcessed: result.clustersProcessed,
        memoriesMerged: result.memoriesMerged
      }
    };
    
    this.saveStats();
    this.log(`Consolidation completed: ${result.memoriesMerged} memories merged`);
    
    return result;
  }

  /**
   * Run pruning immediately
   */
  async runPruning(): Promise<any> {
    console.log('\n🗑️ Running manual pruning...');
    
    const pruner = new MemoryPruner(this.vault, {
      mode: this.config.dryRun ? 'dry-run' : 'auto',
      maxDeletePercentage: 0.10,
      minTotalMemories: 100
    });

    const result = await pruner.prune();
    
    this.stats.lastPruning = {
      timestamp: Date.now(),
      result: {
        flagged: result.flaggedForDeletion,
        deleted: result.deleted,
        preserved: Object.values(result.preserved).reduce((a, b) => a + b, 0)
      }
    };
    
    this.saveStats();
    this.log(`Pruning completed: ${result.deleted} deleted, ${result.preserved.belowThreshold} preserved`);
    
    return result;
  }

  /**
   * Run trash cleanup immediately
   */
  async runTrashCleanup(): Promise<number> {
    console.log('\n🧹 Running manual trash cleanup...');
    
    // Create pruner just for trash cleanup
    const pruner = new MemoryPruner(this.vault, {
      mode: 'auto',
      maxDeletePercentage: 0.10,
      minTotalMemories: 100
    });

    const cleared = await pruner.clearOldTrash();
    
    this.stats.lastTrashCleanup = {
      timestamp: Date.now(),
      result: { cleared }
    };
    
    this.saveStats();
    this.log(`Trash cleanup completed: ${cleared} items removed`);
    
    return cleared;
  }

  /**
   * Get scheduler statistics
   */
  getStats(): SchedulerStats {
    return this.stats;
  }

  /**
   * Manual trigger from CLI
   */
  async trigger(type: 'consolidation' | 'pruning' | 'trash'): Promise<any> {
    this.stats.totalRuns++;
    
    switch (type) {
      case 'consolidation':
        return this.runConsolidation();
      case 'pruning':
        return this.runPruning();
      case 'trash':
        return this.runTrashCleanup();
      default:
        throw new Error(`Unknown trigger type: ${type}`);
    }
  }

  /**
   * Schedule a task to run daily at specified time
   */
  private scheduleDaily(time: string, callback: () => void): NodeJS.Timeout {
    const [hours, minutes] = time.split(':').map(Number);
    
    const nextRun = this.getNextRun(hours, minutes);
    const delay = nextRun.getTime() - Date.now();
    
    console.log(`   📅 Next ${time}: ${nextRun.toLocaleString()}`);
    
    // Set timeout (will reset after each execution via setInterval)
    const initialTimer = setTimeout(() => {
      callback();
      // Then repeat every 24 hours
      setInterval(callback, 24 * 60 * 60 * 1000);
    }, delay);
    
    return initialTimer;
  }

  /**
   * Schedule a task to run weekly on specified day at time
   */
  private scheduleWeekly(dayOfWeek: number, time: string, callback: () => void): NodeJS.Timeout {
    const [hours, minutes] = time.split(':').map(Number);
    
    const nextRun = this.getNextWeekdayRun(dayOfWeek, hours, minutes);
    const delay = nextRun.getTime() - Date.now();
    
    console.log(`   📅 Next Sunday ${time}: ${nextRun.toLocaleString()}`);
    
    const initialTimer = setTimeout(() => {
      callback();
      // Then repeat every 7 days
      setInterval(callback, 7 * 24 * 60 * 60 * 1000);
    }, delay);
    
    return initialTimer;
  }

  /**
   * Get next run time for daily schedule
   */
  private getNextRun(hours: number, minutes: number): Date {
    const now = new Date();
    const next = new Date(now);
    next.setHours(hours, minutes, 0, 0);
    
    if (next <= now) {
      next.setDate(next.getDate() + 1);
    }
    
    return next;
  }

  /**
   * Get next run time for weekly schedule
   */
  private getNextWeekdayRun(dayOfWeek: number, hours: number, minutes: number): Date {
    const now = new Date();
    const next = new Date(now);
    next.setHours(hours, minutes, 0, 0);
    
    const currentDay = now.getDay();
    const daysUntilTarget = (dayOfWeek - currentDay + 7) % 7;
    
    if (daysUntilTarget === 0 && next <= now) {
      next.setDate(next.getDate() + 7);
    } else if (daysUntilTarget > 0) {
      next.setDate(next.getDate() + daysUntilTarget);
    }
    
    return next;
  }

  /**
   * Load statistics from file
   */
  private loadStats(): SchedulerStats {
    try {
      const data = fs.readFileSync(this.statsPath, 'utf8');
      return JSON.parse(data);
    } catch {
      return {
        totalRuns: 0,
        errors: 0
      };
    }
  }

  /**
   * Save statistics to file
   */
  private saveStats(): void {
    try {
      const dir = path.dirname(this.statsPath);
      if (!fs.existsSync(dir)) {
        fs.mkdirSync(dir, { recursive: true });
      }
      fs.writeFileSync(this.statsPath, JSON.stringify(this.stats, null, 2));
    } catch (err) {
      console.error('Failed to save scheduler stats:', err);
    }
  }

  /**
   * Log message to file
   */
  private log(message: string): void {
    try {
      const logPath = this.config.logFile!.replace('~', process.env.HOME || require('os').homedir());
      const dir = path.dirname(logPath);
      
      if (!fs.existsSync(dir)) {
        fs.mkdirSync(dir, { recursive: true });
      }
      
      const timestamp = new Date().toISOString();
      const line = `[${timestamp}] ${message}\n`;
      
      fs.appendFileSync(logPath, line);
    } catch (err) {
      console.error('Failed to write log:', err);
    }
  }

  /**
   * Log error and update stats
   */
  private logError(operation: string, error: Error): void {
    this.stats.errors++;
    this.saveStats();
    this.log(`ERROR ${operation}: ${error.message}`);
    console.error(`❌ ${operation} failed:`, error.message);
  }
}

// CLI entry point for scheduler
if (require.main === module) {
  import('./index.js').then(async ({ ClawVault }) => {
    const vault = new ClawVault();
    const scheduler = new ClawVaultScheduler(vault, {
      dryRun: process.argv.includes('--dry-run')
    });

    const command = process.argv[2];

    switch (command) {
      case 'start':
        scheduler.start();
        break;
      case 'stop':
        scheduler.stop();
        break;
      case 'consolidate':
        await scheduler.runConsolidation();
        break;
      case 'prune':
        await scheduler.runPruning();
        break;
      case 'trash':
        await scheduler.runTrashCleanup();
        break;
      case 'stats':
        console.log(JSON.stringify(scheduler.getStats(), null, 2));
        break;
      default:
        console.log(`
ClawVault Scheduler

Usage: node scheduler.js <command>

Commands:
  start       Start all scheduled tasks
  stop        Stop all scheduled tasks
  consolidate Run consolidation immediately
  prune       Run pruning immediately
  trash       Run trash cleanup immediately
  stats       Show scheduler statistics

Options:
  --dry-run   Preview changes without applying

Examples:
  node scheduler.js start
  node scheduler.js consolidate
  node scheduler.js prune --dry-run
`);
    }
  }).catch(err => {
    console.error('Failed to initialize:', err);
    process.exit(1);
  });
}
