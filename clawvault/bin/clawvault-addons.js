#!/usr/bin/env node

/**
 * ClawVault Addons CLI
 * 
 * Commands for memory consolidation, pruning, and feedback management.
 */

const fs = require('fs');
const path = require('path');
const readline = require('readline');

// Default paths
const DEFAULT_VAULT_PATH = path.join(require('os').homedir(), 'memory');
const CLAWVAULT_MODULE = '../dist/index.js';

let vault;
let consolidator;
let pruner;
let feedbackManager;

async function initVault(vaultPath) {
  const ClawVault = (await import(CLAWVAULT_MODULE)).ClawVault;
  vault = new ClawVault({
    dataDir: vaultPath || DEFAULT_VAULT_PATH,
    enableSensitiveDetection: true
  });
  
  // Initialize addons
  const { MemoryConsolidator } = await import('../dist/consolidation.js');
  const { MemoryPruner } = await import('../dist/pruning.js');
  const { FeedbackManager } = await import('../dist/feedback.js');
  
  consolidator = new MemoryConsolidator(vault);
  pruner = new MemoryPruner(vault, { mode: 'dry-run' });
  feedbackManager = new FeedbackManager(vault);
}

// Command handlers
const commands = {
  async consolidate(argv) {
    await initVault(argv.vault);
    
    console.log('🔄 Memory Consolidation\n');
    
    if (argv['dry-run']) {
      const result = await consolidator.dryRun();
      console.log(`\nWould merge ${result.estimatedReduction} memories into ${result.clusters.length} consolidated entries`);
    } else {
      const result = await consolidator.consolidate();
      console.log(`\n✅ Consolidated ${result.memoriesMerged} memories`);
    }
  },

  async prune(argv) {
    await initVault(argv.vault);
    
    console.log('🗑️ Memory Pruning\n');
    
    const mode = argv.mode || 'dry-run';
    pruner = new MemoryPruner(vault, {
      mode,
      maxDeletePercentage: parseFloat(argv.max || '0.10'),
      minTotalMemories: parseInt(argv.min || '100')
    });
    
    const result = await pruner.prune();
    console.log(`\n${mode === 'dry-run' ? '🔍 DRY RUN:' : '✅ RESULT:'}`);
    console.log(`   Flagged: ${result.flaggedForDeletion}`);
    console.log(`   Deleted: ${result.deleted}`);
    console.log(`   Preserved: ${Object.values(result.preserved).reduce((a, b) => a + b, 0)}`);
  },

  async cleartrash(argv) {
    await initVault(argv.vault);
    const cleared = await pruner.clearOldTrash();
    console.log(`✅ Cleared ${cleared} items from trash`);
  },

  async restore(argv) {
    await initVault(argv.vault);
    if (!argv.id) {
      console.error('❌ --id <memory-id> required');
      process.exit(1);
    }
    const success = await pruner.restoreFromTrash(argv.id);
    console.log(success ? '✅ Restored' : '❌ Failed');
  },

  async feedback(argv) {
    await initVault(argv.vault);
    
    if (!argv.id) {
      console.error('❌ --id <memory-id> required');
      process.exit(1);
    }
    
    switch (argv.type) {
      case 'up':
        await feedbackManager.thumbsUp(argv.id, argv.context);
        break;
      case 'down':
        await feedbackManager.thumbsDown(argv.id, argv.context);
        break;
      case 'pin':
        await feedbackManager.pin(argv.id);
        break;
      case 'unpin':
        await feedbackManager.unpin(argv.id);
        break;
      case 'delete':
        await feedbackManager.delete(argv.id, argv.context);
        break;
      default:
        console.error('❌ Unknown type. Use: up|down|pin|unpin|delete');
        process.exit(1);
    }
  },

  async feedbackStats(argv) {
    await initVault(argv.vault);
    const stats = await feedbackManager.getStats();
    
    console.log('\n📊 Feedback Statistics\n');
    console.log(`   Total Memories: ${stats.totalMemories}`);
    console.log(`   👍 Thumbs Up: ${stats.withThumbsUp}`);
    console.log(`   👎 Thumbs Down: ${stats.withThumbsDown}`);
    console.log(`   ⭐ Pinned: ${stats.pinned}`);
    console.log(`   📈 Avg Confidence Boost: ${stats.averageConfidenceBoost.toFixed(2)}`);
  },

  async recommendLowValue(argv) {
    await initVault(argv.vault);
    const limit = parseInt(argv.limit || '20');
    const recommendations = await feedbackManager.recommendLowValue(limit);
    
    console.log(`\n📋 Low-Value Memory Recommendations (top ${recommendations.length})\n`);
    
    recommendations.forEach((mem, i) => {
      console.log(`${i + 1}. [${mem.type}] conf=${mem.confidence.toFixed(2)}`);
      console.log(`   "${mem.content.substring(0, 100)}..."`);
      console.log(`   ID: ${mem.id}\n`);
    });
    
    console.log('💡 Run: clawvault-addons feedback --id <id> --type down/delete\n');
  },

  async pinned(argv) {
    await initVault(argv.vault);
    const pinned = await feedbackManager.getPinnedMemories();
    
    console.log(`\n⭐ Pinned Memories (${pinned.length})\n`);
    
    if (pinned.length === 0) {
      console.log('   No pinned memories.');
      return;
    }
    
    pinned.forEach((mem, i) => {
      console.log(`${i + 1}. "${mem.content.substring(0, 80)}..."`);
      console.log(`   ID: ${mem.id}`);
    });
  },

  async analyzePatterns(argv) {
    await initVault(argv.vault);
    const patterns = await feedbackManager.analyzePatterns();
    
    console.log('\n🔍 Feedback Pattern Analysis\n');
    console.log(`   Avg Feedback/Memory: ${patterns.avgFeedbackPerMemory.toFixed(2)}`);
    console.log(`   Trend: ${patterns.feedbackTrend.toUpperCase()}\n`);
    
    if (patterns.commonNegativeContexts.length > 0) {
      console.log('   Common Negative Contexts:');
      patterns.commonNegativeContexts.forEach(({ pattern, count }) => {
        console.log(`   - "${pattern}..." (${count}x)`);
      });
    }
  },

  async exportData(argv) {
    await initVault(argv.vault);
    const outputPath = argv.output || './clawvault-feedback-export.json';
    
    const data = await feedbackManager.exportData();
    fs.writeFileSync(outputPath, JSON.stringify(data, null, 2));
    
    console.log(`✅ Exported ${data.length} records to ${outputPath}`);
  },

  async stats(argv) {
    await initVault(argv.vault);
    
    const allMemories = vault.getAllMemories();
    const byType = {};
    const byScope = {};
    let totalConfidence = 0;
    
    for (const mem of allMemories) {
      byType[mem.type] = (byType[mem.type] || 0) + 1;
      byScope[mem.scope] = (byScope[mem.scope] || 0) + 1;
      totalConfidence += mem.confidence;
    }
    
    console.log('\n📊 ClawVault Statistics\n');
    console.log(`   Total Memories: ${allMemories.length}`);
    console.log(`   Avg Confidence: ${(totalConfidence / allMemories.length).toFixed(2)}\n`);
    
    console.log('   By Type:');
    Object.entries(byType).forEach(([type, count]) => {
      console.log(`   - ${type}: ${count}`);
    });
    
    console.log('\n   By Scope:');
    Object.entries(byScope).forEach(([scope, count]) => {
      console.log(`   - ${scope}: ${count}`);
    });
  },

  async info() {
    console.log(`
ClawVault Addons v2.0

Usage: clawvault-addons <command> [options]

Commands:
  consolidate       Merge similar memories
  prune             Clean up low-value memories
  cleartrash        Permanently delete old trash items
  restore           Restore from trash (--id required)
  feedback          Record feedback (--id, --type required)
  feedback-stats    View feedback statistics
  recommend-low     Get low-value memory recommendations
  pinned            List pinned memories
  analyze-patterns  Analyze feedback patterns
  export-data       Export feedback data
  stats             General vault statistics

Options:
  --vault <path>    Vault directory (default: ~/memory)
  --dry-run         Preview changes without applying
  --mode <mode>     prune mode: dry-run|interactive|auto
  --max <percent>   Max deletion percentage (default: 0.10)
  --min <count>     Min memories to preserve (default: 100)
  --limit <num>     Limit results (default: 20)
  --id <id>         Memory ID (required for feedback, restore)
  --type <type>     Feedback type: up|down|pin|unpin|delete
  --context <text>  Feedback context/description
  --output <path>   Export output file path
  --help            Show this help

Examples:
  clawvault-addons consolidate --dry-run
  clawvault-addons prune --mode interactive
  clawvault-addons feedback --id abc123 --type up --context "Helpful!"
  clawvault-addons recommend-low --limit 10
`);
  }
};

// Parse arguments
const args = process.argv.slice(2);
const command = args[0];
const options = {};

for (let i = 1; i < args.length; i++) {
  if (args[i].startsWith('--')) {
    const key = args[i].slice(2);
    const value = args[i + 1] && !args[i + 1].startsWith('--') ? args[++i] : true;
    options[key] = value;
  }
}

// Execute command
(async () => {
  try {
    if (!command || command === 'help' || command === '--help') {
      await commands.info();
      return;
    }

    if (!commands[command]) {
      console.error(`❌ Unknown command: ${command}`);
      console.error('Run: clawvault-addons --help');
      process.exit(1);
    }

    await commands[command](options);
  } catch (error) {
    console.error('❌ Error:', error.message);
    process.exit(1);
  }
})();
