#!/bin/bash

# ClawVault Scheduler Setup Script
# Installs cron jobs for automated memory lifecycle management

set -e

CLAWVAULT_DIR="$HOME/.openclaw/workspace/clawvault"
CRON_JOB_SCRIPT="$CLAWVAULT_DIR/bin/clawvault-addons.js"
LOG_DIR="$HOME/memory/.scheduler-logs"

echo "🕐 Setting up ClawVault Scheduler..."

# Create log directory
mkdir -p "$LOG_DIR"

# Backup existing crontab if not already done
if [ ! -f ~/.crontab.backup ]; then
    crontab -l > ~/.crontab.backup 2>/dev/null || true
    echo "💾 Backed up existing crontab to ~/.crontab.backup"
else
    echo "⚠️  Existing backup found at ~/.crontab.backup"
fi

# Read current crontab into file
TEMP_CRON=$(mktemp)
crontab -l 2>/dev/null > "$TEMP_CRON" || true

# Remove old ClawVault cron jobs (if any)
grep -v "clawvault\|ClawVault" "$TEMP_CRON" > "${TEMP_CRON}.filtered" 2>/dev/null || cp "$TEMP_CRON" "${TEMP_CRON}.filtered"

# Add new cron jobs
cat >> "${TEMP_CRON}.filtered" << 'CRONEOF'

# ─── ClawVault Memory Lifecycle Scheduler ───
# Consolidation: Daily at 3 AM
0 3 * * * cd $HOME/.openclaw/workspace/clawvault && node bin/clawvault-addons.js consolidate >> $HOME/memory/.scheduler-logs/consolidation.log 2>&1

# Pruning: Weekly on Sunday at 4 AM
0 4 * * 0 cd $HOME/.openclaw/workspace/clawvault && node bin/clawvault-addons.js prune --mode auto >> $HOME/memory/.scheduler-logs/pruning.log 2>&1

# Trash Cleanup: Daily at 5 AM
0 5 * * * cd $HOME/.openclaw/workspace/clawvault && node bin/clawvault-addons.js cleartrash >> $HOME/memory/.scheduler-logs/trash-cleanup.log 2>&1
CRONEOF

# Install updated crontab
crontab "${TEMP_CRON}.filtered"

# Cleanup temp files
rm -f "$TEMP_CRON" "${TEMP_CRON}.filtered"

echo ""
echo "✅ Scheduler installed successfully!"
echo ""
echo "📅 Cron Schedule:"
echo "   • Consolidation: Daily at 3:00 AM CST"
echo "   • Pruning: Sundays at 4:00 AM CST"  
echo "   • Trash Cleanup: Daily at 5:00 AM CST"
echo ""
echo "📝 Log files in: $LOG_DIR/"
echo ""
echo "🔍 Verify installation:"
echo "   crontab -l | grep clawvault"
echo ""
echo "📊 View logs:"
echo "   tail -f $LOG_DIR/consolidation.log"
echo "   tail -f $LOG_DIR/pruning.log"
echo "   tail -f $LOG_DIR/trash-cleanup.log"
echo ""
echo "⏹️  To uninstall:"
echo "   $CLAWVAULT_DIR/bin/uninstall-scheduler.sh"
echo ""
