#!/bin/bash
# System Health Check Script
# Quick diagnostic tool for system monitoring

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_FILE="$SCRIPT_DIR/config.yaml"
LOG_DIR="$HOME/.openclaw/workspace/logs"
DATA_DIR="$HOME/.openclaw/workspace/data/monitoring"

# Colors for output
RED='\033[0;31m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Ensure directories exist
mkdir -p "$LOG_DIR" "$DATA_DIR"

log() {
    echo -e "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

print_header() {
    echo -e "\n${BLUE}=== $1 ===${NC}\n"
}

check_cpu() {
    print_header "CPU Usage"
    
    if [[ "$OSTYPE" == "darwin"* ]]; then
        cpu_percent=$(ps -A -stat,%cpu | awk '{s+=$1} END {print s/NR}' 2>/dev/null || echo "N/A")
        load_avg=$(sysctl -n vm.loadavg | awk '{print $2}')
    else
        cpu_percent=$(top -bn1 | grep "Cpu(s)" | sed "s/.*, *\([0-9.]*\)%* id.*/\1/" | awk '{print 100 - $1}')
        load_avg=$(cat /proc/loadavg | awk '{print $1}')
    fi
    
    echo -e "CPU Load: ${GREEN}$cpu_percent%${NC}"
    echo -e "Load Average: $load_avg"
    
    # Check thresholds
    threshold=90
    if [[ $(echo "$cpu_percent > $threshold" | bc -l 2>/dev/null || echo "0") -eq 1 ]]; then
        echo -e "${RED}[ALERT] CPU usage above ${threshold}%!${NC}"
        return 1
    fi
    
    return 0
}

check_memory() {
    print_header "Memory Usage"
    
    if command -v free &> /dev/null; then
        mem_info=$(free -h | grep Mem)
        total=$(echo $mem_info | awk '{print $2}')
        used=$(echo $mem_info | awk '{print $3}')
        available=$(echo $mem_info | awk '{print $7}')
        percent=$(echo $mem_info | awk '{print $4}')
        
        echo -e "Total: ${BLUE}$total${NC}"
        echo -e "Used: ${YELLOW}$used${NC}"
        echo -e "Available: ${GREEN}$available${NC}"
        echo -e "Usage: $percent"
    else
        echo "Memory info not available on this system"
    fi
}

check_disk() {
    print_header "Disk Space"
    
    disk_info=$(df -h / | tail -1)
    filesystem=$(echo $disk_info | awk '{print $1}')
    total=$(echo $disk_info | awk '{print $2}')
    used=$(echo $disk_info | awk '{print $3}')
    available=$(echo $disk_info | awk '{print $4}')
    percent_used=$(echo $disk_info | awk '{print $5}')
    mount=$(echo $disk_info | awk '{print $6}')
    
    echo -e "Filesystem: ${BLUE}$filesystem${NC}"
    echo -e "Size: ${BLUE}$total${NC}"
    echo -e "Used: ${YELLOW}$used${NC}"
    echo -e "Available: ${GREEN}$available${NC}"
    echo -e "Use: $percent_used on $mount"
    
    # Parse percentage and check threshold
    percent_num=$(echo $percent_used | tr -d '%')
    threshold_free=10
    
    if (( percent_num > (100 - threshold_free) )); then
        echo -e "${RED}[ALERT] Disk space below ${threshold_free}% free!${NC}"
        return 1
    fi
    
    return 0
}

check_processes() {
    print_header "Top Processes by CPU/Memory"
    
    echo -e "\n${YELLOW}Top 5 by CPU:${NC}"
    ps aux --sort=-%cpu | head -6 | awk '{printf "%-15s %s %6.1f%% %6.1f%%\n", $1, $11, $3, $4}'
    
    echo -e "\n${YELLOW}Top 5 by Memory:${NC}"
    ps aux --sort=-%mem | head -6 | awk '{printf "%-15s %s %6.1f%% %6.1f%%\n", $1, $11, $3, $4}'
}

check_network() {
    print_header "Network Statistics"
    
    echo -e "Active connections:"
    netstat -an 2>/dev/null | grep ESTABLISHED | wc -l | xargs -I {} echo "  Established: {}" || \
    ss -tun | grep ESTAB | wc -l | xargs -I {} echo "  Established: {}"
    
    echo -e "\nListening ports:"
    netstat -tuln 2>/dev/null | grep LISTEN | head -10 || \
    ss -tuln | grep LISTEN | head -10
    
    # Traffic stats if available
    if [[ "$OSTYPE" == "darwin"* ]]; then
        echo -e "\nInterface statistics:"
        netstat -i 2>/dev/null | grep -E "(Name|en)" || echo "Not available"
    fi
}

check_logs() {
    print_header "Recent System Logs"
    
    echo -e "Last 10 error/warning entries:\n"
    
    if [[ "$OSTYPE" == "darwin"* ]]; then
        log show --last 15m --predicate 'severity >= warning' --info 2>/dev/null | tail -10 || \
        echo "Log access not available"
    else
        sudo journalctl -p 3 -n 10 --no-pager 2>/dev/null || \
        tail -10 /var/log/syslog 2>/dev/null || \
        echo "Log access not available"
    fi
}

check_open_ports() {
    print_header "Open Ports & Services"
    
    echo -e "Port scanning..."
    
    if command -v lsof &> /dev/null; then
        echo -e "\nProcesses with open network connections:"
        lsof -i -P -n | grep LISTEN | head -15
    elif command -v ss &> /dev/null; then
        echo -e "\nListening services:"
        ss -tulnp | head -15
    elif command -v netstat &> /dev/null; then
        echo -e "\nListening services:"
        netstat -tulnp 2>/dev/null | head -15 || netstat -tuln | head -15
    fi
}

send_telegram_alert() {
    local message="$1"
    local chat_id="${TELEGRAM_CHAT_ID:-}"
    local bot_token="${TELEGRAM_BOT_TOKEN:-}"
    
    if [[ -z "$chat_id" || -z "$bot_token" ]]; then
        echo "[WARN] Telegram credentials not set"
        return 1
    fi
    
    local url="https://api.telegram.org/bot${bot_token}/sendMessage"
    local payload="{\"chat_id\": \"${chat_id}\", \"text\": \"${message}\", \"parse_mode\": \"Markdown\"}"
    
    curl -s -X POST "$url" -H "Content-Type: application/json" -d "$payload" > /dev/null
    
    echo "[NOTIFY] Alert sent to Telegram"
}

run_full_check() {
    print_header "Full System Health Check"
    log "Starting comprehensive health check..."
    
    local exit_code=0
    
    check_cpu || exit_code=1
    check_memory
    check_disk || exit_code=1
    check_processes
    check_network
    check_open_ports
    check_logs
    
    log "Health check completed with exit code: $exit_code"
    
    # Save results
    save_health_report "$exit_code"
    
    return $exit_code
}

save_health_report() {
    local exit_code=$1
    local report_file="$DATA_DIR/health_$(date +%Y%m%d_%H%M%S).json"
    
    cat > "$report_file" << EOF
{
    "timestamp": "$(date -Iseconds)",
    "status": $([ $exit_code -eq 0 ] && echo "ok" || echo "issues_detected"),
    "checks": {
        "cpu": $(check_cpu_value),
        "memory": $(check_memory_value),
        "disk": $(check_disk_value)
    }
}
EOF
    
    echo -e "\nReport saved to: $report_file"
}

# Helper functions for JSON reporting
check_cpu_value() {
    ps -A -stat,%cpu | awk '{s+=$1} END {printf "%.1f", s/NR}' 2>/dev/null || echo "null"
}

check_memory_value() {
    free -m 2>/dev/null | awk '/Mem/ {printf "{\"total\": %d, \"used\": %d, \"percent\": %.1f}", $2, $3, ($3/$2)*100}' || echo "null"
}

check_disk_value() {
    df / 2>/dev/null | tail -1 | awk '{printf "{\"total\": \"%s\", \"used\": \"%s\", \"percent\": %d}", $2, $3, $5}' || echo "null"
}

# Main entry point
main() {
    case "${1:-full}" in
        cpu)
            check_cpu
            ;;
        memory)
            check_memory
            ;;
        disk)
            check_disk
            ;;
        processes)
            check_processes
            ;;
        network)
            check_network
            ;;
        logs)
            check_logs
            ;;
        ports)
            check_open_ports
            ;;
        full|*)
            run_full_check
            ;;
        alert)
            # Send test alert
            send_telegram_alert "🧪 Test alert from health-check.sh"
            ;;
        help)
            echo "Usage: $0 [command]"
            echo ""
            echo "Commands:"
            echo "  cpu       - Check CPU usage"
            echo "  memory    - Check memory usage"
            echo "  disk      - Check disk space"
            echo "  processes - Show top processes"
            echo "  network   - Network statistics"
            echo "  logs      - Recent system logs"
            echo "  ports     - Open ports and services"
            echo "  full      - Run complete health check (default)"
            echo "  alert     - Send test Telegram alert"
            echo "  help      - Show this help"
            ;;
    esac
}

main "$@"
