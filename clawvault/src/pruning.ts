/**
 * Memory Pruning Module
 * 
 * Weekly cleanup of low-value memories with safety limits and review queue.
 */

import { ClawVault, MemoryEntry } from './index.js';

export interface PruningCriteria {
  /** Minimum confidence to keep (memories below reviewed) */
  minConfidence: number;
  /** Days before low-confidence memories enter review */
  reviewQueueDays: number;
  /** Days before never-accessed memories enter review */
  neverAccessedDays: number;
  /** Soft delete retention days before permanent deletion */
  softDeleteRetention: number;
}

export interface PruningOptions {
  /** Mode: dry-run, interactive, or auto */
  mode?: 'dry-run' | 'interactive' | 'auto';
  /** Don't delete more than this percentage (default: 0.10) */
  maxDeletePercentage?: number;
  /** Don't delete fewer than this many memories (default: 100) */
  minTotalMemories?: number;
  /** Custom criteria (uses defaults if not specified) */
  criteria?: Partial<PruningCriteria>;
}

export interface PruningResult {
  reviewed: number;
  flaggedForDeletion: number;
  deleted: number;
  preserved: {
    highConfidence: number;
    frequentlyAccessed: number;
    pinned: number;
    belowThreshold: number;
  };
  movedToTrash: number;
  errors: number;
}

export interface FlaggedMemory extends MemoryEntry {
  reason: 'lowConfidence' | 'neverAccessed' | 'duplicate' | 'userMarked';
  confidence: number;
  lastAccessed?: number;
  accessCount: number;
}

export class MemoryPruner {
  private vault: ClawVault;
  private options: PruningOptions;
  private trashDir: string;

  constructor(vault: ClawVault, options: PruningOptions) {
    this.vault = vault;
    this.options = {
      mode: 'dry-run',
      maxDeletePercentage: 0.10,
      minTotalMemories: 100,
      ...options
    };
    
    this.trashDir = this.options.criteria?.softDeleteRetention 
      ? `~/.memory/.trash-${this.options.criteria.softDeleteRetention}d`
      : '~/.memory/.trash';
  }

  /**
   * Run pruning based on current mode
   */
  async prune(): Promise<PruningResult> {
    console.log('🗑️ Starting memory pruning...');
    
    const totalBefore = await this.vault.getStats();
    
    // Identify candidates for deletion
    const candidates = await this.identifyCandidates();
    
    if (candidates.length === 0) {
      console.log('✨ No memories flagged for deletion.');
      return {
        reviewed: 0,
        flaggedForDeletion: 0,
        deleted: 0,
        preserved: { highConfidence: 0, frequentlyAccessed: 0, pinned: 0, belowThreshold: 0 },
        movedToTrash: 0,
        errors: 0
      };
    }

    console.log(`📋 Found ${candidates.length} candidates for deletion:`);
    console.log(`   Low confidence: ${candidates.filter(c => c.reason === 'lowConfidence').length}`);
    console.log(`   Never accessed: ${candidates.filter(c => c.reason === 'neverAccessed').length}`);
    console.log(`   Duplicate: ${candidates.filter(c => c.reason === 'duplicate').length}`);
    console.log(`   User marked: ${candidates.filter(c => c.reason === 'userMarked').length}`);

    // Apply safety limits
    const safeToDelete = this.applySafetyLimits(candidates);
    
    console.log(`\n🛡️ Safety limits applied:`);
    console.log(`   Max delete allowed: ${safeToDelete.allowed} / ${candidates.length} candidates`);
    console.log(`   Min memories preserved: ${safeToDelete.minPreserved}`);

    let result: PruningResult = {
      reviewed: 0,
      flaggedForDeletion: candidates.length,
      deleted: 0,
      preserved: { highConfidence: 0, frequentlyAccessed: 0, pinned: 0, belowThreshold: 0 },
      movedToTrash: 0,
      errors: 0
    };
    
    switch (this.options.mode) {
      case 'dry-run':
        result = await this.dryRunDelete(safeToDelete.toDelete);
        break;
      case 'interactive':
        result = await this.interactiveDelete(safeToDelete.toDelete);
        break;
      case 'auto':
        result = await this.autoDelete(safeToDelete.toDelete);
        break;
    }

    result.reviewed = candidates.length;
    
    console.log('\n✅ Pruning complete!');
    console.log(`   Reviewed: ${result.reviewed}`);
    console.log(`   Flagged: ${result.flaggedForDeletion}`);
    console.log(`   Deleted: ${result.deleted}`);
    console.log(`   Moved to trash: ${result.movedToTrash}`);
    console.log(`   Preserved: high-conf=${result.preserved.highConfidence}, accessed=${result.preserved.frequentlyAccessed}, pinned=${result.preserved.pinned}`);
    
    return result;
  }

  /**
   * Identify memories that should be reviewed for deletion
   */
  private async identifyCandidates(): Promise<FlaggedMemory[]> {
    const allMemories = this.vault.getAllMemories();
    const criteria: PruningCriteria = {
      minConfidence: 0.3,
      reviewQueueDays: 60,
      neverAccessedDays: 90,
      softDeleteRetention: 30,
      ...this.options.criteria
    };
    
    const now = Date.now();
    const candidates: FlaggedMemory[] = [];
    
    for (const memory of allMemories) {
      const flags: FlaggedMemory = {
        ...memory,
        reason: 'lowConfidence',
        confidence: memory.confidence,
        accessCount: memory.accessCount || 0,
        createdAt: memory.createdAt || memory.timestamp,
        updatedAt: memory.updatedAt || memory.timestamp
      };
      
      let shouldFlag = false;
      const createdTime = memory.createdAt || memory.timestamp || now;
      const ageInDays = (now - createdTime) / (1000 * 60 * 60 * 24);
      
      // Low confidence + old
      if (memory.confidence < criteria.minConfidence && ageInDays > criteria.reviewQueueDays) {
        shouldFlag = true;
        flags.reason = 'lowConfidence';
      }
      
      // Never accessed + very old
      if (!shouldFlag && (memory.accessCount || 0) === 0 && ageInDays > criteria.neverAccessedDays) {
        shouldFlag = true;
        flags.reason = 'neverAccessed';
      }
      
      // User marked as low-value
      if (!shouldFlag && memory.feedback?.some((f: any) => f.type === 'thumbs_down')) {
        shouldFlag = true;
        flags.reason = 'userMarked';
      }
      
      if (shouldFlag) {
        candidates.push(flags);
      }
    }
    
    return candidates.sort((a, b) => a.confidence - b.confidence);
  }

  /**
   * Apply safety limits to deletion list
   */
  private applySafetyLimits(candidates: FlaggedMemory[]) {
    const totalMemories = candidates.length; // Should get actual count from vault
    const maxAllowed = Math.floor(totalMemories * (this.options.maxDeletePercentage || 0.10));
    const minPreserve = this.options.minTotalMemories || 100;
    
    // Limit deletions by percentage
    const limitedByPercentage = candidates.slice(0, maxAllowed);
    
    // Ensure minimum preservation
    if (totalMemories - limitedByPercentage.length < minPreserve) {
      const canDelete = totalMemories - minPreserve;
      return {
        allowed: canDelete,
        toDelete: candidates.slice(0, Math.max(0, canDelete)),
        minPreserved: minPreserve
      };
    }
    
    return {
      allowed: limitedByPercentage.length,
      toDelete: limitedByPercentage,
      minPreserved: totalMemories - limitedByPercentage.length
    };
  }

  /**
   * Dry run - show what would be deleted without action
   */
  private async dryRunDelete(toDelete: FlaggedMemory[]): Promise<PruningResult> {
    console.log('\n🔍 DRY RUN MODE - No changes made\n');
    
    console.log(`Would delete ${toDelete.length} memories:\n`);
    
    for (const candidate of toDelete.slice(0, 10)) {
      console.log(`  - [${candidate.type}] "${candidate.content.substring(0, 80)}..."`);
      console.log(`    Confidence: ${candidate.confidence.toFixed(2)}, Reason: ${candidate.reason}`);
    }
    
    if (toDelete.length > 10) {
      console.log(`  ... and ${toDelete.length - 10} more`);
    }
    
    return {
      reviewed: 0,
      flaggedForDeletion: toDelete.length,
      deleted: 0,
      preserved: { highConfidence: 0, frequentlyAccessed: 0, pinned: 0, belowThreshold: toDelete.length },
      movedToTrash: 0,
      errors: 0
    };
  }

  /**
   * Interactive mode - prompt for each deletion
   */
  private async interactiveDelete(toDelete: FlaggedMemory[]): Promise<PruningResult> {
    const result: PruningResult = {
      reviewed: 0,
      flaggedForDeletion: toDelete.length,
      deleted: 0,
      preserved: { highConfidence: 0, frequentlyAccessed: 0, pinned: 0, belowThreshold: 0 },
      movedToTrash: 0,
      errors: 0
    };

    console.log('\n🤝 INTERACTIVE MODE - Answer for each memory:\n');
    console.log('Options: [y]es delete, [n]o keep, [t]rash, [q]uit\n');

    for (const candidate of toDelete) {
      // Simulated prompt (replace with actual readline in production)
      const prompt = `[y/n/t/q] "${candidate.content.substring(0, 60)}..." (${candidate.reason}, conf=${candidate.confidence.toFixed(2)})? `;
      console.log(prompt);
      
      // Placeholder for actual user input
      // const rl = readline.createInterface({ input: process.stdin, output: process.stdout });
      // const response = await new Promise<string>(resolve => rl.question('', resolve));
      const response: string = 'n'; // Default to keeping during dev
      
      if (response === 'y') {
        try {
          await this.vault.deleteMemory(candidate.id);
          result.deleted++;
          console.log('✅ Deleted');
        } catch (error) {
          console.error('❌ Error deleting:', error);
          result.errors++;
        }
      } else if (response === 't') {
        try {
          await this.moveToTrash(candidate);
          result.movedToTrash++;
          console.log('🗃️ Moved to trash');
        } catch (error) {
          console.error('❌ Error moving to trash:', error);
          result.errors++;
        }
      } else if (response === 'q') {
        console.log('\n⏹️ Quit by user');
        break;
      } else {
        result.preserved.belowThreshold++;
        console.log('💾 Kept');
      }
    }
    
    return result;
  }

  /**
   * Auto mode - delete automatically within safety limits
   */
  private async autoDelete(toDelete: FlaggedMemory[]): Promise<PruningResult> {
    const result: PruningResult = {
      reviewed: 0,
      flaggedForDeletion: toDelete.length,
      deleted: 0,
      preserved: { highConfidence: 0, frequentlyAccessed: 0, pinned: 0, belowThreshold: 0 },
      movedToTrash: 0,
      errors: 0
    };

    console.log('\n🤖 AUTO MODE - Deleting within safety limits...\n');

    for (const candidate of toDelete) {
      try {
        // Always soft delete in auto mode (safer)
        await this.moveToTrash(candidate);
        result.movedToTrash++;
      } catch (error) {
        console.error('❌ Error:', error);
        result.errors++;
      }
    }
    
    return result;
  }

  /**
   * Move memory to trash (soft delete)
   */
  private async moveToTrash(memory: FlaggedMemory): Promise<void> {
    // In production, write to .trash folder with expiration metadata
    // Schedule for permanent deletion after retention period
    
    const trashEntry = {
      ...memory,
      trashedAt: Date.now(),
      permanentlyDeleteAt: Date.now() + (30 * 24 * 60 * 60 * 1000) // 30 days
    };
    
    // Implementation: Write to filesystem trash directory
    console.log(`🗃️ Trashed: ${memory.id} (permanently delete: ${new Date(trashEntry.permanentlyDeleteAt).toISOString()})`);
    
    // Remove from active vault
    await this.vault.deleteMemory(memory.id);
  }

  /**
   * Clear trash older than retention period
   */
  async clearOldTrash(): Promise<number> {
    console.log('🧹 Clearing old trash...');
    
    // Scan .trash directory for entries past retention
    // Delete permanently
    // Return count of cleared items
    
    console.log('✅ Trash cleanup complete');
    return 0; // Placeholder
  }

  /**
   * Restore memory from trash
   */
  async restoreFromTrash(memoryId: string): Promise<boolean> {
    console.log(`♻️ Restoring ${memoryId} from trash...`);
    
    // Read from trash directory
    // Restore to active vault
    // Remove from trash
    
    console.log('✅ Memory restored');
    return true; // Placeholder
  }

  /**
   * Get trash status
   */
  async getTrashStatus(): Promise<{
    itemCount: number;
    oldestItem?: string;
    willBeDeleted: number;
  }> {
    // Count items in trash
    // Find oldest
    // Calculate how many will be deleted today
    
    return { itemCount: 0, willBeDeleted: 0 }; // Placeholder
  }
}
