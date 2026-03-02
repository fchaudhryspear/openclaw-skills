#!/bin/bash
echo "💰 SECURITY & COST AUDIT"
echo "========================"
echo ""

ISSUES=0
COST_ISSUES=0

Security Checks (Quick overview from audit-part1)

echo "1️⃣ Quick Security Overview"
if grep -q "^PasswordAuthentication yes" /etc/ssh/sshd_config 2>/dev/null; then
echo " ❌ SSH Password Auth: ENABLED"
ISSUES=$((ISSUES + 1))
else
echo " ✅ SSH Password Auth: DISABLED"
fi

GATEWAY_BIND=$(grep -A5 '"gateway"' ~/.openclaw/openclaw.json | grep '"bind"' | cut -d'"' -f4)
if [ "$GATEWAY_BIND" == "loopback" ]  [ "$GATEWAY_BIND" == "localhost" ]  [ "$GATEWAY_BIND" == "127.0.0.1" ]; then
echo " ✅ Gateway Binding: LOCALHOST"
else
echo " ❌ Gateway Binding: EXPOSED"
ISSUES=$((ISSUES + 1))
fi

if /usr/libexec/ApplicationFirewall/socketfilterfw --getglobalstate | grep -q "Firewall is enabled"; then
echo " ✅ Firewall: ACTIVE"
else
echo " ❌ Firewall: INACTIVE"
ISSUES=$((ISSUES + 1))
fi
echo ""

Cost Checks (Simplified)

echo "2️⃣ Cost Overview (Based on Clawdbot Cost Tracker)"

This script assumes clawd/lib/cost-tracker.js is already configured and running

LAST_DAILY_COST_REPORT=$(cat /Users/faisalshomemacmini/clawd/reports/daily-token-report.md 2>/dev/null | grep "Daily Total Cost" | awk '{print $NF}')

if [ -z "$LAST_DAILY_COST_REPORT" ]; then
echo " ⚠️ WARNING: Daily cost report not found or empty."
echo " Ensure clawd/lib/cost-tracker.js is running daily."
COST_ISSUES=$((COST_ISSUES + 1))
else
echo " 📈 Yesterday's AI Cost: $LAST_DAILY_COST_REPORT"

Simple threshold check for cost anomalies

You might want to customize this logic further

COST_VALUE=$(echo "$LAST_DAILY_COST_REPORT" | sed 's/$//')
if (( $(echo "$COST_VALUE > 10.0" | bc -l) )); then # Alert if daily cost > $10
echo " ❌ CRITICAL: Daily AI cost ($LAST_DAILY_COST_REPORT) is higher than expected (> $10.00)!"
COST_ISSUES=$((COST_ISSUES + 1))
else
echo " ✅ Daily AI cost within expected limits."
fi
fi
echo ""

echo "========================================"
echo "AUDIT SUMMARY"
echo "========================================"
echo "❌ Security Issues: $ISSUES"
echo "💰 Cost Anomalies: $COST_ISSUES"
echo ""

if [ "$ISSUES" -eq 0 ] && [ "$COST_ISSUES" -eq 0 ]; then
echo "🎉 EXCELLENT! No security or cost issues found!"
exit 0
elif [ "$ISSUES" -eq 0 ]; then
echo "✅ GOOD! No security issues, but $COST_ISSUES cost anomaly(ies)"
exit 0
else
echo "🚨 ACTION REQUIRED! $ISSUES security issue(s) or $COST_ISSUES cost anomaly(ies) found!"
exit 1
fi
