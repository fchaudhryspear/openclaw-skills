#!/bin/bash
# Send daily token report via Telegram

YESTERDAY=$(date -v -1d +%Y-%m-%d) # macOS compatible date command
REPORT_FILE=/Users/faisalshomemacmini/clawd/logs/daily-report-${YESTERDAY}.log

if [ ! -f "$REPORT_FILE" ]; then
  echo "No report found for $YESTERDAY"
  exit 1
fi

# Read report
REPORT=$(cat "$REPORT_FILE")

# Send via openclaw message tool
# Note: Using 'openclaw message send' directly for consistency
# and to avoid 'clawdbot' which might be an alias or older command.
# Ensure your OpenClaw agent has the necessary permissions.
/usr/bin/env openclaw message send --channel telegram --target 7980582930 --message "$REPORT" 2>/dev/null || {
  # Fallback: just log it
  echo "Report generated but couldn't send automatically"
  echo "Report saved to: $REPORT_FILE"
  cat "$REPORT_FILE"
}

rm -f /tmp/report-payload.json # This file is not used with openclaw message send, so safe to remove
