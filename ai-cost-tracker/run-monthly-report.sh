#!/bin/bash
# Monthly Token Report Wrapper (1st of month)

LOG_FILE=/Users/faisalshomemacmini/clawd/logs/monthly-report-$(date +%Y-%m-%d).log

{
  echo ""
  echo "========================================"
  echo "Monthly Token Report: $(date)"
  echo "========================================"
  cd /Users/faisalshomemacmini/clawd/reports/
  /usr/bin/env node monthly-token-report.js
} >> "$LOG_FILE" 2>&1