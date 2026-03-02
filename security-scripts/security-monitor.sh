#!/bin/bash
# Run this daily via cron

LOG_FILE=~/clawd/logs/security-monitor.log
echo "=== Security Monitor $(date) ===" >> $LOG_FILE

# Check for credential access attempts
if grep -i "\.aws\|\.ssh\|\.env\|credentials" ~/clawd/logs/webhook-server.log 2>/dev/null | tail -5; then
    echo "⚠️ Credential access detected in logs" >> $LOG_FILE
fi

# Check for suspicious external requests
if grep -i "curl.*http\|wget.*http" ~/clawd/logs/*.log 2>/dev/null | tail -5; then
    echo "⚠️ External HTTP requests detected" >> $LOG_FILE
fi

# Check fail2ban bans
BANNED=$(sudo fail2ban-client status sshd 2>/dev/null | grep "Currently banned" | awk '{print $4}')
if [ "$BANNED" -gt 0 ]; then
    echo "⚠️ $BANNED IP(s) banned by fail2ban" >> $LOG_FILE
fi

# Email summary if issues found
if grep -q "⚠️" $LOG_FILE; then
    echo "Security issues detected. Check $LOG_FILE"
fi
