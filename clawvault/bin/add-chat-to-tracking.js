#!/usr/bin/env node
/**
 * Add chats to ClawVault auto-tracking
 * Usage: node add-chat-to-tracking.js <chat-id> [description]
 */

const fs = require('fs');
const path = require('path');

const CONFIG_PATH = path.join(process.env.HOME, 'memory', '.clawvault-auto-track.conf');

function loadConfig() {
  try {
    const data = fs.readFileSync(CONFIG_PATH, 'utf8');
    return data.split('\n')
      .map(line => line.trim())
      .filter(line => line && !line.startsWith('#'));
  } catch (err) {
    if (err.code === 'ENOENT') {
      return [];
    }
    throw err;
  }
}

function saveConfig(chatIds) {
  const header = `# ClawVault Auto-Track Configuration
# Chat IDs to automatically save to memory vault
# Updated: ${new Date().toISOString()}

`;
  
  const uniqueIds = [...new Set(chatIds)];
  const content = uniqueIds.map(id => `${id}`).join('\n');
  
  fs.writeFileSync(CONFIG_PATH, header + content + '\n');
}

function addChat(chatId, description = '') {
  const chatIds = loadConfig();
  
  if (chatIds.includes(chatId)) {
    console.log(`⚠️  Chat ${chatId} is already being tracked.`);
    return;
  }
  
  chatIds.push(chatId);
  saveConfig(chatIds);
  
  console.log(`✅ Added chat ${chatId} to auto-tracking.`);
  if (description) {
    console.log(`   Description: ${description}`);
  }
  console.log(`   Total tracked chats: ${chatIds.length}`);
}

function listChats() {
  const chatIds = loadConfig();
  
  console.log('='.repeat(60));
  console.log('📋 ClawVault Auto-Tracked Chats');
  console.log('='.repeat(60));
  console.log();
  
  if (chatIds.length === 0) {
    console.log('No chats currently being auto-tracked.');
    console.log('Add chats with: node add-chat-to-tracking.js <chat-id>');
  } else {
    console.log(`Total: ${chatIds.length} chat(s)\n`);
    chatIds.forEach((id, i) => {
      console.log(`${i + 1}. ${id}`);
    });
  }
  
  console.log();
  console.log('='.repeat(60));
}

function main() {
  const args = process.argv.slice(2);
  
  if (args.length === 0 || args[0] === '--list') {
    listChats();
    return;
  }
  
  if (args[0] === '--help' || args[0] === '-h') {
    console.log('Usage: node add-chat-to-tracking.js <chat-id> [description]');
    console.log('       node add-chat-to-tracking.js --list');
    console.log();
    console.log('Examples:');
    console.log('  node add-chat-to-tracking.js -5275168308 "Coding group"');
    console.log('  node add-chat-to-tracking.js 1003589630000');
    console.log('  node add-chat-to-tracking.js --list');
    return;
  }
  
  const chatId = args[0];
  const description = args.slice(1).join(' ');
  
  addChat(chatId, description);
}

main();
