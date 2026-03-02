#!/bin/bash

# ClawVault Scheduler Uninstall Script
# Removes cron jobs and restores backup

set -e

echo "⏹️  Uninstalling ClawVault Scheduler..."

# Restore backup
if [ -f ~/.crontab.backup ]; then
    crontab ~/.crontab.backup
    rm ~/.crontab.backup
    echo "✅ Crontab restored from backup"
else
    echo "⚠️  No backup found, removing ClawVault jobs only"
    crontab -l 2>/dev/null | grep -v "clawvault" | crontab - || echo "No cron jobs to remove"
fi

echo ""
echo "❌ Scheduler uninstalled"
echo ""
echo "💡 Logs retained in ~/memory/.scheduler-logs/"
echo "   Delete manually if no longer needed:"
echo "   rm -rf ~/memory/.scheduler-logs"
