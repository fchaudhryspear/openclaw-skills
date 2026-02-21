# OpenClaw Disaster Recovery System

A comprehensive backup and restore system for OpenClaw that captures EVERYTHING needed to restore your complete installation after an uninstall/reinstall.

## ⚡ Quick Reference

```bash
# Run backup manually
cd ~/.openclaw/workspace/backup && ./backup.sh

# Check backup integrity
./check.sh ~/openclaw-backups/openclaw-backup-YYYY-MM-DD-HHMMSS.tar.gz

# Restore from backup
./restore.sh ~/openclaw-backups/openclaw-backup-YYYY-MM-DD-HHMMSS.tar.gz

# Install nightly backup cron job
./setup-cron.sh
```

**Latest Backup:** `~/openclaw-backups/openclaw-backup-2026-02-20-175246.tar.gz` (488 MB)

## Overview

This system provides:
- **Automated nightly backups** at 12:00 AM
- **Complete restoration** of all OpenClaw data and configuration
- **Integrity verification** before restore
- **Backup rotation** (7 days, 4 weeks, 12 months)
- **One-command restore** operation

## What Gets Backed Up

### Core Workspace Files
- `SOUL.md` - Your agent's identity
- `USER.md` - User preferences and context
- `MEMORY.md` - Long-term curated memory
- `AGENTS.md` - Agent behavior guidelines
- `TOOLS.md` - Environment-specific tool configurations
- `HEARTBEAT.md` - Periodic check instructions
- `memory/` - Daily memory files and logs
- All custom scripts, tools, and files in workspace

### OpenClaw Configuration
- `~/.openclaw/openclaw.json` - Main configuration
- API keys and model configurations
- Update check settings
- Patch files

### Automation & Scheduling
- `~/.openclaw/cron/` - All scheduled jobs
- Cron run history
- System crontab reference

### Agents & Sessions
- `~/.openclaw/agents/` - Agent configurations
- Session labels and settings
- Excludes: Session logs (too large, not critical)

### Skills
- `~/.openclaw/skills/` - All installed skills
- Skill configurations and customizations

### Credentials (Secured)
- `~/.openclaw/credentials/` - API keys, tokens
- Telegram pairing data
- Encrypted with 700 permissions

### ClawVault
- `~/clawvault/` - Complete ClawVault project
- Data index and search capabilities
- Source code and build artifacts
- Excludes: node_modules (rebuilt on restore)

### Telegram
- `~/.openclaw/telegram/` - Telegram bot configuration

### Global Memory
- `~/.openclaw/memory/` - Global memory files

## Quick Start

### Run Backup Manually

```bash
cd ~/.openclaw/workspace/backup
./backup.sh
```

The backup will be created in `~/openclaw-backups/` with a timestamped filename like:
```
openclaw-backup-2026-02-20-174430.tar.gz
```

### Check Backup Integrity

Before restoring, verify the backup:

```bash
./check.sh ~/openclaw-backups/openclaw-backup-2026-02-20-174430.tar.gz
```

This checks:
- Tarball integrity
- Manifest completeness
- Checksum verification
- Disk space requirements
- What will be restored

### Restore from Backup

**Interactive restore (recommended):**
```bash
./restore.sh ~/openclaw-backups/openclaw-backup-2026-02-20-174430.tar.gz
```

**Force restore (no confirmation):**
```bash
./restore.sh --force ~/openclaw-backups/openclaw-backup-2026-02-20-174430.tar.gz
```

**Dry run (see what would happen):**
```bash
./restore.sh --dry-run ~/openclaw-backups/openclaw-backup-2026-02-20-174430.tar.gz
```

## Backup Retention Policy

Backups are automatically rotated according to this schedule:

### Daily Backups
- **Keep:** Last 7 days
- **Schedule:** Every night at 12:00 AM
- **Example:** Mon, Tue, Wed, Thu, Fri, Sat, Sun (current week)

### Weekly Backups
- **Keep:** 4 weeks (Sunday backups)
- **Identified by:** Day of week = Sunday
- **Example:** Last 4 Sundays

### Monthly Backups
- **Keep:** 12 months (1st of each month)
- **Identified by:** Day of month = 1st
- **Example:** Jan 1, Feb 1, Mar 1, etc.

### Total Retention
Maximum backups stored: ~23 (7 daily + 4 weekly + 12 monthly)

## File Locations

| Component | Source | Backup Location |
|-----------|--------|-----------------|
| Backup Archives | `~/openclaw-backups/` | N/A |
| Backup Scripts | `~/.openclaw/workspace/backup/` | In workspace.tar.gz |
| Scripts | `backup.sh`, `restore.sh`, `check.sh`, `README.md` | Self-contained |

## Disaster Recovery Procedures

### Scenario 1: Complete OpenClaw Uninstall/Reinstall

1. **Before uninstall:** Ensure you have a recent backup
   ```bash
   ls -la ~/openclaw-backups/
   ```

2. **Uninstall OpenClaw:**
   ```bash
   openclaw uninstall
   # or remove manually
   ```

3. **Reinstall OpenClaw:**
   ```bash
   # Follow OpenClaw installation instructions
   ```

4. **Restore from backup:**
   ```bash
   cd ~/.openclaw/workspace/backup
   ./restore.sh ~/openclaw-backups/openclaw-backup-YYYY-MM-DD-HHMMSS.tar.gz
   ```

5. **Verify restoration:**
   ```bash
   openclaw doctor
   openclaw cron list
   ```

### Scenario 2: Workspace Corruption

1. **Check latest backup:**
   ```bash
   ls -lt ~/openclaw-backups/openclaw-backup-*.tar.gz | head -5
   ```

2. **Verify backup integrity:**
   ```bash
   ./check.sh ~/openclaw-backups/openclaw-backup-YYYY-MM-DD-HHMMSS.tar.gz
   ```

3. **Restore:**
   ```bash
   ./restore.sh ~/openclaw-backups/openclaw-backup-YYYY-MM-DD-HHMMSS.tar.gz
   ```

### Scenario 3: Accidental File Deletion

If you accidentally deleted a file (e.g., SOUL.md):

1. **Find the backup:**
   ```bash
   ls ~/openclaw-backups/
   ```

2. **Extract specific file:**
   ```bash
   cd /tmp
   tar xzf ~/openclaw-backups/openclaw-backup-YYYY-MM-DD-HHMMSS.tar.gz
   cd openclaw-backup-YYYY-MM-DD-HHMMSS
   
   # Extract just the file you need
   tar xzf workspace.tar.gz
   cp workspace/SOUL.md ~/.openclaw/workspace/
   ```

## Troubleshooting

### Backup Fails: Insufficient Disk Space

**Problem:** Backup fails with "No space left on device"

**Solution:**
1. Check available space: `df -h ~`
2. Clean old backups manually: `ls -lt ~/openclaw-backups/`
3. Remove old backups: `rm ~/openclaw-backups/openclaw-backup-OLD.tar.gz`
4. Run backup again

### Restore Fails: Checksum Mismatch

**Problem:** `check.sh` reports checksum mismatch

**Solution:**
1. The backup file may be corrupted
2. Try an older backup
3. If critical, attempt restore with `--force` flag (proceed with caution)

### Restore Fails: Permission Denied

**Problem:** Cannot write to ~/.openclaw

**Solution:**
1. Check permissions: `ls -la ~ | grep openclaw`
2. Fix ownership: `sudo chown -R $(whoami) ~/.openclaw`
3. Retry restore

### Cron Jobs Not Restored

**Problem:** After restore, `openclaw cron list` shows no jobs

**Solution:**
1. Verify cron directory was restored: `ls -la ~/.openclaw/cron/`
2. Check jobs.json: `cat ~/.openclaw/cron/jobs.json`
3. Restart OpenClaw gateway: `openclaw gateway restart`
4. Re-register jobs if needed

### ClawVault Not Working

**Problem:** ClawVault commands fail after restore

**Solution:**
1. The restore script attempts to rebuild ClawVault automatically
2. If it fails, manually rebuild:
   ```bash
   cd ~/.openclaw/workspace/clawvault
   npm install
   npm run build
   ```

## Security Considerations

### Backup File Permissions
- Backup files are created with `600` permissions (owner read/write only)
- Checksums are generated for integrity verification
- Credentials are included but with restricted permissions

### Sensitive Data
Backups contain:
- API keys (in openclaw.json)
- Telegram tokens
- Private credentials

**Store backups securely:**
- Keep backups on encrypted drives
- Use secure backup locations (encrypted cloud, external drive)
- Do not share backup files

### Checksum Verification
Always verify checksums before restore:
```bash
shasum -a 256 -c openclaw-backup-YYYY-MM-DD-HHMMSS.tar.gz.sha256
```

## Script Reference

### backup.sh

**Purpose:** Create a complete backup of OpenClaw

**Usage:**
```bash
./backup.sh
```

**Output:**
- `~/openclaw-backups/openclaw-backup-YYYY-MM-DD-HHMMSS.tar.gz`
- `~/openclaw-backups/openclaw-backup-YYYY-MM-DD-HHMMSS.tar.gz.sha256`

### restore.sh

**Purpose:** Restore OpenClaw from backup

**Usage:**
```bash
./restore.sh [OPTIONS] <backup-file>

Options:
  -h, --help     Show help
  -d, --dry-run  Show what would be restored
  -f, --force    Skip confirmation
  -c, --check    Verify only, don't restore
```

### check.sh

**Purpose:** Verify backup integrity before restore

**Usage:**
```bash
./check.sh <backup-file>
```

**Checks:**
- Tarball validity
- Manifest completeness
- Checksum verification
- Disk space
- Component availability

## Maintenance

### Manual Backup Cleanup

If you need to free space:

```bash
# List all backups by date
ls -lt ~/openclaw-backups/openclaw-backup-*.tar.gz

# Remove specific old backup
rm ~/openclaw-backups/openclaw-backup-2026-01-01-120000.tar.gz
rm ~/openclaw-backups/openclaw-backup-2026-01-01-120000.tar.gz.sha256

# Keep only last 7 days
ls -1t ~/openclaw-backups/openclaw-backup-*.tar.gz | tail -n +8 | xargs rm -f
```

### Monitoring Backup Success

Check backup status:
```bash
# List recent backups
ls -lt ~/openclaw-backups/ | head -10

# Check backup log (if cron is set up)
cat ~/.openclaw/workspace/backup/backup.log 2>/dev/null || echo "No log file"
```

## Support

If you encounter issues:

1. Check the backup log for errors
2. Run `check.sh` to diagnose backup integrity
3. Verify disk space: `df -h ~`
4. Check file permissions: `ls -la ~/.openclaw/`

---

**Last Updated:** 2026-02-20  
**Backup Version:** 1.0
