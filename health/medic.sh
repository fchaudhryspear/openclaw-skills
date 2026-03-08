#!/bin/bash
# Medic Health Monitor — Continuous system health checks
# Runs every 10 minutes, alerts on failures
# Inspired by: Antfarm medic workflow

CHECK_INTERVAL=${CHECK_INTERVAL:-600} # 10 minutes default
TELEGRAM_CHAT_ID="7980582930"
LOG_FILE="$HOME/.openclaw/workspace/health/medic.log"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> "$LOG_FILE"
}

send_alert() {
    local severity=$1
    local message=$2
    
    case $severity in
        critical) icon="🔴" ;;
        warning)  icon="🟡" ;;
        info)     icon="🟢" ;;
    esac
    
    if command -v openclaw &>/dev/null; then
        openclaw message send --channel telegram --target "$TELEGRAM_CHAT_ID" \
            --message "${icon} **System Health Alert**\n\n${message}" 2>/dev/null
    fi
    log "${icon} ${message}"
}

# ── Health Checks ─────────────────────────────────────────────────────────────

check_openclaw_gateway() {
    if curl -s http://localhost:18789 >/dev/null 2>&1; then
        return 0
    else
        send_alert "critical" "OpenClaw Gateway DOWN on port 18789"
        return 1
    fi
}

check_session_count() {
    local count=$(openclaw sessions --json 2>/dev/null | python3 -c "import json,sys; print(len(json.load(sys.stdin).get('sessions',[])))")
    
    if [[ $count -gt 100 ]]; then
        send_alert "warning" "Session count high: $count sessions (cleanup recommended)"
        return 1
    fi
    return 0
}

check_cron_jobs() {
    local failed=$(openclaw cron list 2>/dev/null | grep -c "err" || echo 0)
    
    if [[ $failed -gt 0 ]]; then
        send_alert "warning" "$failed cron jobs failed or errored"
        return 1
    fi
    return 0
}

check_keychain_secrets() {
    local missing=0
    
    for key in anthropic-api-key qwen-sg-api-key aws-access-key-id moonshot-api-key google-api-key; do
        if ! security find-generic-password -a 'optimus' -s "$key" -w >/dev/null 2>&1; then
            ((missing++))
        fi
    done
    
    if [[ $missing -gt 0 ]]; then
        send_alert "warning" "$missing API keys missing from Keychain"
        return 1
    fi
    return 0
}

check_cost_threshold() {
    if [[ -f "$HOME/.openclaw/workspace/ai-cost-tracker/logs/ai-costs.jsonl" ]]; then
        local daily_cost=$(python3 << 'EOF'
import json
from datetime import datetime
today = datetime.now().strftime('%Y-%m-%d')
total = 0
with open('/Users/faisalshomemacmini/.openclaw/workspace/ai-cost-tracker/logs/ai-costs.jsonl') as f:
    for line in f:
        entry = json.loads(line.strip())
        if entry.get('date') == today:
            total += entry.get('cost', 0)
print(f"{total:.2f}")
EOF
)
        
        if (( $(echo "$daily_cost > 20.00" | bc -l) )); then
            send_alert "warning" "Daily AI costs exceeded \$20: \$$daily_cost"
            return 1
        fi
    fi
    return 0
}

check_stale_projects() {
    if [[ -f "$HOME/memory/active_projects.json" ]]; then
        local stale=$(python3 << 'EOF'
import json
from datetime import datetime, timedelta
with open('/Users/faisalshomemacmini/memory/active_projects.json') as f:
    projects = json.load(f)
stale = []
now = datetime.now()
for name, proj in projects.items():
    started = datetime.fromisoformat(proj['started'].split('.')[0]) if isinstance(proj.get('started'), str) else now
    idle = (now - started).days
    if idle > 7:
        stale.append((name, idle))
print(','.join([f"{n}:{i}d" for n,i in stale]))
EOF
)
        if [[ -n "$stale" ]]; then
            send_alert "info" "Stale projects detected: $stale"
        fi
    fi
    return 0
}

# ── Main Monitoring Loop ───────────────────────────────────────────────────────

run_all_checks() {
    log "Running health checks..."
    
    local issues=0
    
    check_openclaw_gateway || ((issues++))
    check_session_count || ((issues++))
    check_cron_jobs || ((issues++))
    check_keychain_secrets || ((issues++))
    check_cost_threshold || ((issues++))
    check_stale_projects || ((issues++))
    
    if [[ $issues -eq 0 ]]; then
        log "✅ All health checks passed"
    else
        log "⚠️  $issues health check(s) flagged"
    fi
    
    return $issues
}

case "$1" in
    --once)
        run_all_checks
        ;;
    --watch)
        echo "🩺 Medic Health Monitor starting (interval: ${CHECK_INTERVAL}s)"
        echo "   Log file: $LOG_FILE"
        while true; do
            run_all_checks
            sleep $CHECK_INTERVAL
        done
        ;;
    --help)
        echo "Medic Health Monitor
Usage:
  ./medic.sh --once      Run all checks once
  ./medic.sh --watch     Continuous monitoring loop
  ./medic.sh --help      Show this help"
        ;;
    *)
        run_all_checks
        ;;
esac
