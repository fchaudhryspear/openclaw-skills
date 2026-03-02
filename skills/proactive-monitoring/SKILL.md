# Proactive Monitoring Skill

Real-time cost anomaly detection, system health checks, and security posture monitoring with Telegram alerting.

## Overview

This skill provides comprehensive monitoring for:
- **Cost Anomaly Detection**: Tracks daily AI/API spending, alerts when >$10/day
- **System Health**: Monitors CPU (>90% critical), memory (>95%), disk (<10% free)
- **Security Posture**: SSH brute force detection, firewall status, network traffic analysis
- **Real-time Dashboard**: Web-based dashboard with live metrics
- **Telegram Integration**: Instant alerts to your Telegram channel

## Installation

```bash
cd ~/.openclaw/workspace/skills/proactive-monitoring

# Install Python dependencies
pip3 install psutil pyyaml requests

# Make scripts executable
chmod +x monitor.py health-check.sh

# Set Telegram credentials (required for alerts)
export TELEGRAM_CHAT_ID="your_chat_id"
export TELEGRAM_BOT_TOKEN="your_bot_token"
```

## Usage

### Single Health Check
```bash
python3 monitor.py --once
./health-check.sh full
```

### Continuous Monitoring
```bash
python3 monitor.py --continuous --interval 300
```
Runs every 5 minutes by default. Adjust `--interval` as needed.

### Individual Checks (Shell Script)
```bash
./health-check.sh cpu
./health-check.sh memory
./health-check.sh disk
./health-check.sh processes
./health-check.sh network
./health-check.sh ports
./health-check.sh logs
```

### View Dashboard
```bash
# Open in browser
open dashboard.html

# Or serve via simple HTTP server
python3 -m http.server 8080
# Visit: http://localhost:8080/dashboard.html
```

## Alert Thresholds

### Cost Alerts
- **Threshold**: $10.00/day
- **Check Interval**: Every 60 minutes
- **Notification**: Telegram with overspent amount

### System Alerts
- **CPU Critical**: >90% for 2+ minutes
- **CPU Warning**: >75% for 5+ minutes
- **Memory Critical**: >95% for 2+ minutes
- **Disk Critical**: <10% free space
- **Disk Warning**: <20% free space

### Security Alerts
- **SSH Brute Force**: >5 failed attempts in 1 hour
- **Unusual Traffic**: >100MB outbound in 1 hour

## Configuration

Edit `config.yaml` to customize:

```yaml
alerts:
  cost:
    threshold_daily: 10.00  # Change alert threshold
    check_interval_minutes: 60
    
  system:
    cpu_critical: 90  # Adjust CPU thresholds
    disk_critical_percent_free: 10
    memory_critical: 95
    check_interval_minutes: 5

notification:
  channel: telegram
  chat_id: "${TELEGRAM_CHAT_ID}"
```

## Data Storage

All metrics are stored in:
```
~/.openclaw/workspace/data/monitoring/
├── daily_costs.json       # Daily cost tracking
├── api_usage.log          # API usage logs
└── metrics_YYYY-MM-DD.json # Daily metrics snapshots
```

## Integration Examples

### Log API Costs
When using AI APIs, append costs to the log:
```bash
echo "$(date -Iseconds)|$(model_name)|${cost_usd}" >> ~/.openclaw/workspace/data/monitoring/api_usage.log
```

### Schedule Periodic Checks
Add to crontab (`crontab -e`):
```cron
# Check system health every 5 minutes
*/5 * * * * /Users/faisalshomemacmini/.openclaw/workspace/skills/proactive-monitoring/health-check.sh full >> /dev/null 2>&1

# Run cost check hourly
0 * * * * python3 /Users/faisalshomemacmini/.openclaw/workspace/skills/proactive-monitoring/monitor.py --once >> /dev/null 2>&1
```

### Docker Container Health
Monitor container stats (add to `health-check.sh`):
```bash
docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemPerc}}" | grep -v NAME
```

## Troubleshooting

### Telegram Notifications Not Working
1. Verify bot token is correct
2. Ensure chat ID is correct (bot must be added to group/chat first)
3. Test with: `./health-check.sh alert`

### High CPU Alerts Too Frequent
Adjust threshold in `config.yaml`:
```yaml
system:
  cpu_critical: 95  # Increase from 90
```

### Disk Space Tracking
By default monitors `/` (root). For macOS, this is the main volume. Add additional volumes:
```python
# In monitor.py, add more disk checks:
for mount in ['/Volumes/Data', '/home']:
    if os.path.exists(mount):
        disk = psutil.disk_usage(mount)
        # ... process result
```

## Files

- `monitor.py` - Main Python monitoring daemon
- `health-check.sh` - Shell script for quick diagnostics
- `dashboard.html` - Real-time web dashboard
- `config.yaml` - Configuration file
- `alerts.yaml` - Alert rules definition
- `SKILL.md` - This documentation

## Dependencies

**Python**: psutil, pyyaml, requests
**Shell**: Standard Unix utilities (ps, df, netstat, etc.)

No external API keys required (except optional Telegram bot).
