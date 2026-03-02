# Cross-Service Monitor - Deployment Guide

## Quick Start

### 1. Install Dependencies

```bash
cd cross-service-monitor
pip install -r requirements.txt
```

### 2. Configure Environment Variables

Create a `.env` file:

```bash
# AWS (optional - for monitoring)
AWS_REGION=us-east-1

# Snowflake (required for Snowflake monitoring)
SNOWFLAKE_ACCOUNT=your-account
SNOWFLAKE_USER=your-user
SNOWFLAKE_PRIVATE_KEY="-----BEGIN ENCRYPTED PRIVATE KEY-----..."
# OR use password authentication
SNOWFLAKE_PASSWORD=your-password

# Telegram Alerts (optional)
TELEGRAM_BOT_TOKEN=your-bot-token
ALERT_EMAIL=faisal@credologi.com
EMAIL_USERNAME=your-email@gmail.com
EMAIL_PASSWORD=your-app-password

# Dashboard
DASHBOARD_PORT=8080
DASHBOARD_HOST=0.0.0.0
```

### 3. Run the Monitor

```bash
# With dashboard
python main.py

# Without dashboard (monitoring only)
python main.py --no-dashboard

# Custom config file
python main.py -c /path/to/config.yaml

# Custom port
python main.py --port 9000
```

### 4. Access Dashboard

Open your browser to `http://localhost:8080`

## API Endpoints

### Health & Status
- `GET /api/v1/health` - Basic health check
- `GET /api/v1/health/detailed` - Detailed service status
- `GET /api/v1/dashboard/summary` - Full dashboard data

### Pipelines
- `GET /api/v1/pipelines` - List all pipelines
- `GET /api/v1/pipelines/status` - All pipeline statuses
- `GET /api/v1/pipelines/{name}/status` - Specific pipeline status

### Metrics
- `GET /api/v1/metrics/aws` - AWS Lambda metrics
- `GET /api/v1/metrics/snowflake` - Snowflake query/warehouse metrics
- `GET /api/v1/metrics/crm` - CRM API health

### Alerts
- `GET /api/v1/alerts` - Active alerts
- `GET /api/v1/alerts/issues` - Correlated issues
- `POST /api/v1/alerts/acknowledge/{id}` - Acknowledge alert
- `POST /api/v1/alerts/resolve/{id}` - Resolve alert
- `POST /api/v1/alerts/test` - Send test alert

## Configuration

See `config.yaml` for full configuration options:

```yaml
# Service configurations
services:
  aws:
    region: us-east-1
    enabled: true
    
  snowflake:
    account: credologi-dev
    warehouse: COMPUTE_WH
    enabled: true
    
  crm:
    hubspot:
      enabled: true
      api_key: your-api-key
      
# Pipeline definitions
pipeline_definitions:
  - name: "aws-to-snowflake-load"
    schedule: "0 */6 * * *"
    steps:
      - service: aws
        resource: lambda:data-loader
      - service: snowflake
        resource: pipeline:load_data

# Alerting rules
alerting:
  telegram_chat_id: "-1002381931352"
  threshold_lag_minutes: 15
```

## Docker Deployment

### Build Image

```bash
docker build -t cross-service-monitor .
```

### Run Container

```bash
docker run -d \
  --name csm-monitor \
  -p 8080:8080 \
  -v $(pwd)/config.yaml:/app/config.yaml \
  -e SNOWFLAKE_ACCOUNT=your-account \
  -e SNOWFLAKE_USER=your-user \
  -e TELEGRAM_BOT_TOKEN=your-token \
  cross-service-monitor
```

### Docker Compose

```yaml
version: '3.8'

services:
  monitor:
    build: .
    ports:
      - "8080:8080"
    environment:
      - SNOWFLAKE_ACCOUNT=${SNOWFLAKE_ACCOUNT}
      - SNOWFLAKE_USER=${SNOWFLAKE_USER}
      - TELEGRAM_BOT_TOKEN=${TELEGRAM_BOT_TOKEN}
    volumes:
      - ./config.yaml:/app/config.yaml:ro
      - ./metrics.db:/app/metrics.db
    restart: unless-stopped
```

## Kubernetes Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: cross-service-monitor
spec:
  replicas: 1
  selector:
    matchLabels:
      app: cross-service-monitor
  template:
    metadata:
      labels:
        app: cross-service-monitor
    spec:
      containers:
      - name: monitor
        image: cross-service-monitor:latest
        ports:
        - containerPort: 8080
        env:
        - name: SNOWFLAKE_ACCOUNT
          valueFrom:
            secretKeyRef:
              name: csm-secrets
              key: snowflake-account
        - name: SNOWFLAKE_USER
          valueFrom:
            secretKeyRef:
              name: csm-secrets
              key: snowflake-user
        - name: TELEGRAM_BOT_TOKEN
          valueFrom:
            secretKeyRef:
              name: csm-secrets
              key: telegram-token
        volumeMounts:
        - name: config
          mountPath: /app/config.yaml
          subPath: config.yaml
      volumes:
      - name: config
        configMap:
          name: csm-config
---
apiVersion: v1
kind: Service
metadata:
  name: cross-service-monitor
spec:
  selector:
    app: cross-service-monitor
  ports:
  - port: 80
    targetPort: 8080
  type: ClusterIP
```

## Monitoring Integration

### Prometheus Metrics

The monitor exposes Prometheus-compatible metrics at `/metrics`:

```prometheus
csm_service_health{service="aws"} 1
csm_service_health{service="snowflake"} 1
csm_service_health{service="crm"} 0
csm_active_alerts{severity="critical"} 2
csm_active_alerts{severity="warning"} 5
csm_pipeline_lag_seconds{pipeline="aws-to-snowflake"} 3600
```

### Grafana Dashboard

Import dashboard ID `XXXXX` (create from dashboard export):

Key panels:
- Overall system health gauge
- Service availability by source
- Pipeline execution timeline
- Alert severity distribution
- Data freshness by dataset

## Scheduled Checks (Cron)

Add to crontab for periodic checks:

```bash
# Check every 5 minutes
*/5 * * * * curl -s http://localhost:8080/api/v1/health > /dev/null

# Export metrics every hour
0 * * * * curl -s http://localhost:8080/api/v1/dashboard/summary > /var/log/csm-metrics-$(date +\%Y-\%m).json
```

## Troubleshooting

### Common Issues

**Snowflake Connection Fails:**
```bash
# Test connection manually
python -c "
from monitors.snowflake_monitor import SnowflakeMonitor
import os
m = SnowflakeMonitor(
    account=os.getenv('SNOWFLAKE_ACCOUNT'),
    user=os.getenv('SNOWFLAKE_USER'),
    private_key=os.getenv('SNOWFLAKE_PRIVATE_KEY')
)
print(m.check_query_health())
"
```

**Telegram Alerts Not Working:**
- Verify bot token is correct
- Ensure bot was added to the chat/channel
- Chat ID must include the leading `-` for groups/channels

**Dashboard Not Loading:**
```bash
# Check if server is running
curl http://localhost:8080/api/v1/health

# View logs
tail -f ~/cross-service-monitor.log
```

### Log Files

Default log location: `/var/log/cross-service-monitor/monitor.log`

Configure in `config.yaml`:
```yaml
logging:
  level: DEBUG  # or INFO, WARNING, ERROR
  file: /path/to/logfile.log
```

## Security

### API Authentication

Add API key authentication:

```python
# In dashboard/app.py
from fastapi.security import APIKeyHeader

API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)

@app.get("/api/v1/...")
async def protected_endpoint(api_key: str = Depends(API_KEY_HEADER)):
    if api_key != os.getenv("API_KEY"):
        raise HTTPException(status_code=403, detail="Invalid API key")
    # ... rest of endpoint
```

### Network Policies

Restrict access:
```bash
# Only allow from specific IP
ufw allow from 10.0.0.0/8 to any port 8080

# Or via firewall rules
iptables -A INPUT -p tcp --dport 8080 -s 10.0.0.0/8 -j ACCEPT
```

## Upgrading

```bash
# Pull latest changes
cd cross-service-monitor
git pull origin main

# Update dependencies
pip install -r requirements.txt --upgrade

# Restart service
sudo systemctl restart cross-service-monitor
```

## Support

For issues or questions:
- Check logs: `journalctl -u cross-service-monitor`
- Review config: `cat config.yaml`
- Test components: `python tests/test_monitor.py`
