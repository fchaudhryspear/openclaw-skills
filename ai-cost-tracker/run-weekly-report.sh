#!/bin/bash
# Weekly Token Report Wrapper (Fridays)

LOG_FILE=/Users/faisalshomemacmini/clawd/logs/weekly-report-$(date +%Y-%m-%d).log

{
  echo ""
  echo "========================================"
  echo "Weekly Token Report: $(date)"
  echo "========================================"
  cd /Users/faisalshomemacmini/clawd/reports/
  /usr/bin/env node weekly-token-report.js
} >> "$LOG_FILE" 2>&1