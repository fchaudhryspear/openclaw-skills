#!/bin/bash
#
# OpenClaw Backup Cron Job Setup
# Run this script to install the nightly backup cron job
#

set -euo pipefail

echo "=============================================="
echo "  OpenClaw Backup Cron Job Setup"
echo "=============================================="
echo ""

# Backup script location
BACKUP_SCRIPT="/Users/faisalshomemacmini/.openclaw/workspace/backup/backup.sh"
LOG_FILE="/Users/faisalshomemacmini/.openclaw/workspace/backup/backup.log"

# Check if backup script exists
if [[ ! -f "$BACKUP_SCRIPT" ]]; then
    echo "❌ Error: Backup script not found at $BACKUP_SCRIPT"
    exit 1
fi

# Check if backup script is executable
if [[ ! -x "$BACKUP_SCRIPT" ]]; then
    echo "Making backup script executable..."
    chmod +x "$BACKUP_SCRIPT"
fi

echo "Current crontab entries:"
echo "----------------------------------------------"
crontab -l 2>/dev/null | grep -v "^$" | grep -v "^#" | head -10 || echo "(no crontab set)"
echo "----------------------------------------------"
echo ""

# Check if already installed
if crontab -l 2>/dev/null | grep -q "openclaw-backup"; then
    echo "⚠️  OpenClaw backup cron job is already installed."
    echo ""
    read -p "Do you want to reinstall? (y/N): " confirm
    if [[ "$confirm" != "y" && "$confirm" != "Y" ]]; then
        echo "Cancelled."
        exit 0
    fi
    # Remove existing entry
    crontab -l 2>/dev/null | grep -v "openclaw-backup" | crontab -
fi

echo ""
echo "Installing nightly backup cron job..."
echo "Schedule: Every day at 12:00 AM (midnight)"
echo "Command: $BACKUP_SCRIPT"
echo "Log: $LOG_FILE"
echo ""

# Add the cron job
crontab -l 2>/dev/null | {
    cat
    echo ""
    echo "# OpenClaw Disaster Recovery Backup - Nightly at 12:00 AM"
    echo "0 0 * * * $BACKUP_SCRIPT >> $LOG_FILE 2>&1"
} | crontab -

echo "✅ Cron job installed successfully!"
echo ""
echo "To verify, run: crontab -l"
echo "To test manually, run: $BACKUP_SCRIPT"
echo ""
echo "Backup will run automatically every night at midnight."
echo "Backups are stored in: ~/openclaw-backups/"
