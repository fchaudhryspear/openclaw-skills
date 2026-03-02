#!/bin/bash
# Proactive Monitoring - Daily Health Check Cron Job
# Runs every 6 hours: 7am, 1pm, 7pm, 1am CST

cd /Users/faisalshomemacmini/.openclaw/workspace/skills/proactive-monitoring

# Run health check
python3 monitor.py --once >> logs/monitor.log 2>&1

# Send alert if issues found
if grep -q "ALERT" logs/monitor.log; then
    curl -X POST https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage \
      -d "chat_id=${TELEGRAM_CHAT_ID}" \
      -d "text=🚨 Alert: Proactive Monitor detected issues" \
      2>/dev/null || true
fi
