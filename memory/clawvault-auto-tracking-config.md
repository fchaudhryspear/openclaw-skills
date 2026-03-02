---
id: clawvault-auto-tracking-configuration
created: 2026-02-20
type: procedural
confidence: 1.0
tags: [clawvault, memory, configuration, auto-tracking, chat-ids]
---

# ClawVault Auto-Tracking Configuration

## Overview

These are the chat IDs that are automatically saved to the ClawVault memory system. Conversations from these chats are indexed and made searchable.

## Active Tracked Chats

| Chat ID | Description | Platform |
|---------|-------------|----------|
| 1003589630000 | User workspace | Telegram |
| 1003807261956 | User workspace 2 | Telegram |
| -5275168308 | Coding & Optimus_macmini | Telegram Group |
| -1003735686198 | Group chat | Telegram Group |
| -5215079081 | Current group | Telegram Group |

**Total:** 5 chats

## Configuration Location

File: `~/memory/.clawvault-auto-track.conf`

Format:
```
# One chat ID per line
-5275168308
1003589630000
```

## Management Commands

### Add a Chat
```bash
cd ~/.openclaw/workspace/clawvault
node bin/add-chat-to-tracking.js <chat-id> "description"
```

### List Tracked Chats
```bash
node bin/add-chat-to-tracking.js --list
```

### Check if Chat is Tracked
```bash
node bin/check-chat-memory.js <chat-id>
```

### Reindex All Chats
```bash
clawvault reindex --incremental
```

## How It Works

The ClawVault Session Observer runs every ~30 minutes and:
1. Checks all sessions for new messages
2. If the chat ID matches the auto-track list, the conversation is saved
3. Memories are indexed and made searchable
4. References are extracted and linked

## Search Across All Tracked Chats

```bash
# Search for specific topic
clawvault search "lambda deployment"

# Search with filters
clawvault search "api key" --scope work

# Check recent activity
clawvault status
```

## Related Systems

- **ClawVault Session Observer** — Cron job that monitors chats
- **Incremental Indexer** — Only indexes new/changed content
- **Memory Confidence Scoring** — Tracks reliability of extracted info
- **Semantic Memory Layers** — Categorizes by episodic/procedural/declarative
