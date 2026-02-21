#!/usr/bin/env node

/**
 * ClawVault CLI
 * 
 * Commands:
 *   clawvault reindex [--full|--incremental]
 *   clawvault watch
 *   clawvault search <query>
 *   clawvault status
 *   clawvault resume
 */

const path = require('path');
const { IncrementalIndexer } = require('../dist/incremental-indexer');

const MEMORY_PATH = process.env.CLAWVAULT_PATH || path.join(process.env.HOME, 'memory');
const INDEX_PATH = path.join(MEMORY_PATH, '.clawvault-index.json');

async function main() {
  const args = process.argv.slice(2);
  const command = args[0];
  
  switch (command) {
    case 'reindex':
      await reindex(args.slice(1));
      break;
      
    case 'watch':
      await watch();
      break;
      
    case 'search':
      await search(args.slice(1).join(' '));
      break;
      
    case 'status':
      await status();
      break;
      
    case 'resume':
      await resume();
      break;
      
    case 'help':
    case '--help':
    case '-h':
      showHelp();
      break;
      
    default:
      console.error(`Unknown command: ${command}`);
      showHelp();
      process.exit(1);
  }
}

async function reindex(args) {
  const isFull = args.includes('--full');
  const isIncremental = args.includes('--incremental');
  
  const indexer = new IncrementalIndexer({
    memoryPath: MEMORY_PATH,
    indexPath: INDEX_PATH
  });
  
  await indexer.initialize();
  
  let result;
  if (isFull) {
    result = await indexer.performFullIndex();
  } else if (isIncremental) {
    result = await indexer.performIncrementalIndex();
  } else {
    // Default to incremental
    console.log('No flag specified, defaulting to incremental reindex.');
    console.log('Use --full for full reindex or --incremental for incremental.');
    result = await indexer.performIncrementalIndex();
  }
  
  console.log(`\nIndexing complete!`);
  console.log(`  Duration: ${result.duration}ms`);
  console.log(`  Added: ${result.added}`);
  console.log(`  Updated: ${result.updated}`);
  console.log(`  Unchanged: ${result.unchanged}`);
  console.log(`  Removed: ${result.removed}`);
  console.log(`  Total: ${result.total} documents`);
}

async function watch() {
  const indexer = new IncrementalIndexer({
    memoryPath: MEMORY_PATH,
    indexPath: INDEX_PATH
  });
  
  await indexer.initialize();
  await indexer.startWatching();
}

async function search(query) {
  if (!query) {
    console.error('Please provide a search query');
    process.exit(1);
  }

  const indexer = new IncrementalIndexer({
    memoryPath: MEMORY_PATH,
    indexPath: INDEX_PATH
  });

  await indexer.initialize();
  const results = indexer.search(query, { limit: 20 });

  console.log(`\nSearch results for "${query}":\n`);

  if (results.length === 0) {
    console.log('No results found.');
    return;
  }

  results.forEach((result, i) => {
    console.log(`${i + 1}. ${result.title} (${result.type})`);
    console.log(`   Score: ${result.score}`);
    console.log(`   Path: ${result.path}`);
    if (result.tags?.length) {
      console.log(`   Tags: ${result.tags.join(', ')}`);
    }
    console.log(`   Excerpt: ${result.excerpt?.substring(0, 100)}...`);
    console.log();
  });
}

async function status() {
  const indexer = new IncrementalIndexer({
    memoryPath: MEMORY_PATH,
    indexPath: INDEX_PATH
  });
  
  await indexer.initialize();
  
  console.log('\n=== ClawVault Status ===\n');
  console.log(`Memory path: ${MEMORY_PATH}`);
  console.log(`Index path: ${INDEX_PATH}`);
  console.log(`State path: ${indexer.statePath}`);
  console.log();
  
  const stats = indexer.getStats();
  if (stats.totalEntries > 0) {
    console.log(`Index version: ${stats.indexVersion || '1.0.0'}`);
    console.log(`Documents indexed: ${stats.totalEntries}`);
    console.log(`Last indexed: ${stats.lastIndexed || 'Unknown'}`);
  } else {
    console.log('No index found. Run "clawvault reindex" to create one.');
  }
  
  console.log();
  console.log(`Last full index: ${indexer.state.lastFullIndex || 'Never'}`);
  console.log(`Indexing in progress: ${indexer.state.inProgress ? 'Yes' : 'No'}`);
  console.log(`Tracked files: ${Object.keys(indexer.state.fileHashes).length}`);
  console.log();
}

async function resume() {
  const indexer = new IncrementalIndexer({
    memoryPath: MEMORY_PATH,
    indexPath: INDEX_PATH
  });
  
  await indexer.initialize();
  const documents = await indexer.resume();
  
  if (documents) {
    console.log(`\nResume complete! ${documents.length} documents indexed.`);
  }
}

function showHelp() {
  console.log(`
ClawVault - AI Memory System

Usage: clawvault <command> [options]

Commands:
  reindex [--full|--incremental]   Reindex the vault
    --full                         Perform full reindex
    --incremental                  Perform incremental reindex (default)
  
  watch                            Start file watcher for real-time updates
  
  search <query>                   Search the vault
  
  status                           Show vault status
  
  resume                           Resume interrupted indexing
  
  help                             Show this help message

Environment Variables:
  CLAWVAULT_PATH                   Path to memory directory (default: ~/memory)

Examples:
  clawvault reindex --incremental
  clawvault watch
  clawvault search "project planning"
  clawvault status
`);
}

main().catch(err => {
  console.error('Error:', err.message);
  process.exit(1);
});
