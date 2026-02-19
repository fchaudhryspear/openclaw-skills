#!/usr/bin/env node
/**
 * Telegram History Reader - Full Chat Export
 * Exports ALL Telegram chats + messages to JSON/Markdown
 * 
 * Usage: node telegram-history-reader.js [chat_id] [limit]
 */

const { execSync } = require('child_process');
const fs = require('fs');
const path = require('path');

// Your Telegram ID from inbound meta
const YOUR_ID = '7980582930';

// Default options
const DEFAULTS = {
  chunkSize: 1000,    // Messages per chunk
  maxChunks: 50,      // Max chunks per chat (50k total)
  output: './telegram-history',
  format: 'both'      // json, md, both
};

async function exportChat(chatId, options = {}) {
  const opts = { ...DEFAULTS, ...options };
  const cmd = `openclaw message action=send channel=telegram message="Exporting ${chatId}..."`;
  
  console.log(`📱 Exporting Telegram chat ${chatId}...`);
  
  // Paginated export for large histories
  const chunks = [];
  let offset = 0;
  let hasMore = true;
  
  while (hasMore && chunks.length < opts.maxChunks) {
    const chunk = execSync(
      `openclaw sessions_history "${chatId}" ${opts.chunkSize} offset=${offset}`,
      { encoding: 'utf8' }
    );
    
    if (!chunk.trim()) {
      hasMore = false;
      break;
    }
    
    chunks.push(JSON.parse(chunk));
    offset += opts.chunkSize;
    
    console.log(`📦 Chunk ${chunks.length}: offset ${offset}`);
  }
  
  const chatDir = path.join(opts.output, chatId);
  fs.mkdirSync(chatDir, { recursive: true });
  
  // Save raw JSON
  fs.writeFileSync(path.join(chatDir, 'history.json'), history);
  
  // Flatten chunks and save Markdown
  const allMessages = chunks.flatMap(chunk => chunk.messages || chunk);
  const mdContent = allMessages.map(msg => 
    `[${new Date(msg.timestamp).toLocaleString('en-US', {timeZone: 'America/Chicago'})} CST] ${msg.role || msg.author}: ${msg.content}`
  ).join('\\n\\n');
  
  fs.writeFileSync(path.join(chatDir, 'history.md'), mdContent);
  
  console.log(`✅ Exported ${messages.length} messages to ${chatDir}`);
  return messages.length;
}

async function exportAll() {
  console.log('🌐 Exporting ALL Telegram history...');
  
  // Get all sessions
  const sessions = execSync('openclaw sessions_list', { encoding: 'utf8' });
  const telegramSessions = sessions.split('\\n')
    .filter(line => line.includes('telegram'))
    .map(line => line.split(' ')[0]);
  
  let total = 0;
  for (const session of telegramSessions.slice(0, 10)) { // Limit to 10 chats
    total += await exportChat(session);
    console.log(`Progress: ${total} messages`);
  }
  
  console.log(`🎉 Complete! ${total} messages across ${telegramSessions.length} chats`);
}

// CLI
const [, , chatId, limit] = process.argv;
if (chatId === 'all') {
  exportAll();
} else if (chatId) {
  exportChat(chatId, { limit: parseInt(limit) || DEFAULTS.limit });
} else {
  console.log('Usage:');
  console.log('  node telegram-history-reader.js all              # All chats');
  console.log('  node telegram-history-reader.js 7980582930 5000  # Specific chat');
}

module.exports = { exportChat, exportAll };
