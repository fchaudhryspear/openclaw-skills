#!/bin/bash
# Daily Token Usage Report Wrapper

LOG_FILE=/Users/faisalshomemacmini/clawd/logs/daily-report-$(date +%Y-%m-%d).log

{
  echo ""
  echo "========================================"
  echo "Daily Token Report: $(date)"
  echo "========================================"
  cd /Users/faisalshomemacmini/clawd/reports/ # Changed to specific script dir
  /usr/bin/env node daily-token-report.js # Execute the Node.js script
} >> "$LOG_FILE" 2>&1