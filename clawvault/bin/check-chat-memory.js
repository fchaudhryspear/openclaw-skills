#!/usr/bin/env node
/**
 * ClawVault Chat Memory Checker
 * 
 * Checks if a specific chat/session is being tracked in ClawVault.
 * Usage: node check-chat-memory.js [chat-id]
 */

const fs = require('fs');
const path = require('path');

const MEMORY_PATH = process.env.CLAWVAULT_PATH || path.join(process.env.HOME, 'memory');
const INDEX_PATH = path.join(MEMORY_PATH, '.clawvault-index.json');

function loadIndex() {
  try {
    const data = fs.readFileSync(INDEX_PATH, 'utf8');
    return JSON.parse(data);
  } catch (err) {
    console.error('❌ No index found. Run: clawvault reindex');
    process.exit(1);
  }
}

function searchForChat(index, chatId) {
  const results = [];
  
  for (const [id, entry] of Object.entries(index.entries || {})) {
    // Check if chat ID appears in content or tags
    if (entry.content?.toLowerCase().includes(chatId.toLowerCase()) ||
        entry.tags?.some(tag => tag.toLowerCase().includes(chatId.toLowerCase())) ||
        entry.path?.includes(chatId)) {
      results.push(entry);
    }
    
    // Check for session references
    if (entry.content?.includes('session') && entry.content?.includes(chatId)) {
      results.push(entry);
    }
  }
  
  return results;
}

function findRecentObservations(index, hours = 24) {
  const cutoff = Date.now() - (hours * 60 * 60 * 1000);
  const results = [];
  
  for (const [id, entry] of Object.entries(index.entries || {})) {
    const entryDate = new Date(entry.modified || entry.created).getTime();
    if (entryDate > cutoff) {
      results.push({
        ...entry,
        age: Math.round((Date.now() - entryDate) / (1000 * 60)) // minutes
      });
    }
  }
  
  return results.sort((a, b) => b.age - a.age);
}

function findByType(index, type) {
  return Object.values(index.entries || {})
    .filter(e => e.type === type)
    .sort((a, b) => new Date(b.modified) - new Date(a.modified));
}

function main() {
  const args = process.argv.slice(2);
  const chatId = args[0];
  
  console.log('='.repeat(70));
  console.log('🔍 ClawVault Chat Memory Checker');
  console.log('='.repeat(70));
  console.log();
  
  // Load index
  const index = loadIndex();
  const totalEntries = Object.keys(index.entries || {}).length;
  
  console.log(`📊 Vault Statistics`);
  console.log(`   Total memories indexed: ${totalEntries}`);
  console.log(`   Index version: ${index.version || '1.0.0'}`);
  console.log(`   Last updated: ${index.lastIndexed || 'Unknown'}`);
  console.log();
  
  // If no chat ID provided, show general info
  if (!chatId) {
    console.log('⚠️  No chat ID provided. Usage:');
    console.log('   node check-chat-memory.js <chat-id>');
    console.log();
    console.log('Examples:');
    console.log('   node check-chat-memory.js telegram-12345');
    console.log('   node check-chat-memory.js 7980582930');
    console.log('   node check-chat-memory.js session-abc123');
    console.log();
    
    // Show recent activity
    console.log('='.repeat(70));
    console.log('📅 Recent Activity (Last 24 hours)');
    console.log('='.repeat(70));
    
    const recent = findRecentObservations(index, 24);
    if (recent.length === 0) {
      console.log('   No recent entries found.');
    } else {
      console.log(`   Found ${recent.length} entries in last 24h:`);
      recent.slice(0, 10).forEach(entry => {
        console.log(`   • ${entry.title || entry.id} (${entry.age}m ago)`);
      });
      if (recent.length > 10) {
        console.log(`   ... and ${recent.length - 10} more`);
      }
    }
    console.log();
    
    // Show by type
    console.log('='.repeat(70));
    console.log('📁 Memories by Type');
    console.log('='.repeat(70));
    
    const types = {};
    Object.values(index.entries || {}).forEach(e => {
      types[e.type || 'uncategorized'] = (types[e.type || 'uncategorized'] || 0) + 1;
    });
    
    Object.entries(types)
      .sort((a, b) => b[1] - a[1])
      .forEach(([type, count]) => {
        console.log(`   ${type}: ${count}`);
      });
    
    return;
  }
  
  // Search for specific chat
  console.log(`🔎 Searching for chat: "${chatId}"`);
  console.log();
  
  const matches = searchForChat(index, chatId);
  
  if (matches.length === 0) {
    console.log('❌ No memories found for this chat ID.');
    console.log();
    console.log('Possible reasons:');
    console.log('   • Chat hasn\'t been indexed yet');
    console.log('   • Run: clawvault reindex --incremental');
    console.log('   • The chat ID format is different');
    console.log();
    console.log('💡 Try searching for partial matches:');
    console.log(`   clawvault search "${chatId}"`);
  } else {
    console.log(`✅ Found ${matches.length} memory entries for this chat:`);
    console.log();
    
    matches.forEach((entry, i) => {
      console.log(`${i + 1}. ${entry.title || entry.id}`);
      console.log(`   Path: ${entry.path}`);
      console.log(`   Type: ${entry.type || 'uncategorized'}`);
      console.log(`   Modified: ${entry.modified || 'Unknown'}`);
      if (entry.tags?.length) {
        console.log(`   Tags: ${entry.tags.join(', ')}`);
      }
      console.log(`   Excerpt: ${entry.excerpt?.substring(0, 100)}...`);
      console.log();
    });
  }
  
  console.log('='.repeat(70));
  console.log('🛠️  Next Steps');
  console.log('='.repeat(70));
  console.log();
  console.log('If chat is NOT being tracked:');
  console.log('   1. Ensure ClawVault Session Observer is running');
  console.log('   2. Check: clawvault status');
  console.log('   3. Reindex: clawvault reindex --incremental');
  console.log();
  console.log('If chat IS being tracked:');
  console.log('   • Use: clawvault search "<query>" to find memories');
  console.log('   • Check: clawvault-addons feedback-stats');
  console.log();
}

main();
