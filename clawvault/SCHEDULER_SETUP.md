# ClawVault Scheduler Setup Guide

## Automated Installation (Recommended)

Run the setup script:

```bash
cd ~/.openclaw/workspace/clawvault
./bin/setup-scheduler.sh
```

This will:
1. Backup your existing crontab to `~/.crontab.backup`
2. Install 3 scheduled tasks for memory lifecycle management
3. Create log directory at `~/memory/.scheduler-logs/`

## Manual Installation

If the automated install fails, run these commands manually:

```bash
# Create log directory
mkdir -p ~/memory/.scheduler-logs

# Add cron jobs
(crontab -l 2>/dev/null | grep -v "clawvault"; cat << 'EOF'

# ─── ClawVault Memory Lifecycle Scheduler ───
# Consolidation: Daily at 3 AM
0 3 * * * cd $HOME/.openclaw/workspace/clawvault && node bin/clawvault-addons.js consolidate >> $HOME/memory/.scheduler-logs/consolidation.log 2>&1

# Pruning: Weekly on Sunday at 4 AM
0 4 * * 0 cd $HOME/.openclaw/workspace/clawvault && node bin/clawvault-addons.js prune --mode auto >> $HOME/memory/.scheduler-logs/pruning.log 2>&1

# Trash Cleanup: Daily at 5 AM  
0 5 * * * cd $HOME/.openclaw/workspace/clawvault && node bin/clawvault-addons.js cleartrash >> $HOME/memory/.scheduler-logs/trash-cleanup.log 2>&1
EOF
) | crontab -
```

## Verify Installation

```bash
crontab -l | grep clawvault
```

Expected output:
```
0 3 * * * cd ... clawvault && node bin/clawvault-addons.js consolidate ...
0 4 * * 0 cd ... clawvault && node bin/clawvault-addons.js prune ...
0 5 * * * cd ... clawvault && node bin/clawvault-addons.js cleartrash ...
```

## Cron Schedule

| Task | Schedule | Description |
|------|----------|-------------|
| **Consolidation** | Daily 3:00 AM | Merge similar memories |
| **Pruning** | Sunday 4:00 AM | Clean up low-value memories |
| **Trash Cleanup** | Daily 5:00 AM | Permanently delete old trash |

## Log Files

All scheduler activity is logged to:

```
~/memory/.scheduler-logs/
├── consolidation.log
├── pruning.log
└── trash-cleanup.log
```

View logs in real-time:

```bash
tail -f ~/memory/.scheduler-logs/consolidation.log
tail -f ~/memory/.scheduler-logs/pruning.log
tail -f ~/memory/.scheduler-logs/trash-cleanup.log
```

## Uninstall

Restore original crontab:

```bash
crontab ~/.crontab.backup
rm ~/.crontab.backup
```

Or run the uninstall script:

```bash
./bin/uninstall-scheduler.sh
```

Delete log files:

```bash
rm -rf ~/memory/.scheduler-logs
```

## Manual Execution

Run any task immediately without waiting for schedule:

```bash
# Consolidate now
node bin/clawvault-addons.js consolidate

# Prune now (dry-run mode)
node bin/clawvault-addons.js prune --dry-run

# Prune now (auto mode)
node bin/clawvault-addons.js prune --mode auto

# Clear trash now
node bin/clawvault-addons.js cleartrash
```

## Troubleshooting

### Crontab hangs or fails

macOS may have issues with `sudo crontab`. Try:

```bash
# Kill any hanging crontab processes
killall -9 crontab

# Then retry installation
/bin/bash bin/setup-scheduler.sh
```

### Jobs not running

Check if cron daemon is running:

```bash
# macOS: Check launchd
launchctl list | grep cron

# Start cron if needed (usually auto-starts)
sudo launchctl load -w /System/Library/LaunchDaemons/com.vix.cron.plist
```

### Logs are empty

Jobs ran but produced no output. This is normal if:
- No memories needed consolidation
- No memories flagged for pruning
- Trash was already empty

### Permission denied errors

Ensure Node can access the workspace:

```bash
chmod -R u+rwx ~/.openclaw/workspace/clawvault
chmod +x bin/clawvault-addons.js
```

## Configuration

Edit scheduler behavior in `src/scheduler.ts`:

```typescript
const scheduler = new ClawVaultScheduler(vault, {
  enableConsolidation: true,   // Set false to disable
  consolidationTime: '03:00',  // Change time
  enablePruning: true,
  pruningDayOfWeek: 0,         // 0=Sun, 1=Mon, etc.
  pruningTime: '04:00',
  enableTrashCleanup: true,
  trashCleanupTime: '05:00',
  dryRun: false,               // Set true for preview-only mode
});
```

Recompile after changes:

```bash
npm run build
```

## What Each Task Does

### Consolidation (3 AM Daily)

Groups similar memories and merges them:
- Finds clusters with embedding similarity < 0.15
- Combines redundant information
- Preserves highest confidence scores
- Skips high-confidence (>0.9) memories

**Result**: Cleaner vault, fewer duplicate memories

### Pruning (Sunday 4 AM)

Removes low-value memories:
- Confidences < 0.3 older than 60 days
- Never-accessed memories older than 90 days
- Memories with repeated thumbs_down feedback

**Safety Limits**:
- Max 10% deletion per run
- Min 100 memories preserved
- Soft delete first (30-day recovery window)

**Result**: Smaller, more relevant memory base

### Trash Cleanup (5 AM Daily)

Permanently deletes soft-deleted items:
- Scans `.trash/` folder
- Removes items older than 30 days
- Frees disk space

**Result**: Reclaimed storage, cleaner filesystem

---

**Built by Optimus** ⚡
