# ⚡ Cross-Service Correlation Monitor

**Track data pipelines across AWS → Snowflake → CRMs. Alert when pipelines fail or lag. Unified view of tech stack status.**

![Status](https://img.shields.io/badge/status-wip-yellow)
![Python](https://img.shields.io/badge/python-3.11+-blue)
![License](https://img.shields.io/badge/license-MIT-green)

## 🎯 Overview

This system provides end-to-end visibility into your data infrastructure:

- **Pipeline Monitoring**: Track executions from AWS Lambda → Snowflake → CRM systems
- **Correlation Engine**: Detect cascading failures and identify root causes
- **Alerting**: Multi-channel alerts (Slack, Telegram, Email) with deduplication
- **Dashboard**: Real-time health visualization with historical trends

## 📁 Project Structure

```
cross-service-monitor/
├── monitors/              # Service-specific monitors
│   ├── aws_monitor.py     # AWS Lambda, S3, SQS monitoring
│   ├── snowflake_monitor.py # Query performance, warehouse status
│   └── crm_monitor.py      # HubSpot, Salesforce API health
├── engine/                # Core intelligence
│   ├── correlator.py      # Event correlation & pattern detection
│   └── alert_manager.py   # Alert routing & delivery
├── dashboard/             # Web interface
│   ├── app.py             # FastAPI backend
│   └── static/index.html  # React-style frontend
├── tests/                 # Test suite
├── config.yaml            # Configuration
├── main.py                # Orchestrator
└── DEPLOY.md              # Deployment guide
```

## 🚀 Quick Start

### Installation

```bash
cd cross-service-monitor
pip install -r requirements.txt
```

### Configuration

Set environment variables:

```bash
export SNOWFLAKE_ACCOUNT="your-account"
export SNOWFLAKE_USER="your-user"
export SNOWFLAKE_PRIVATE_KEY="-----BEGIN PRIVATE KEY-----..."
export TELEGRAM_BOT_TOKEN="your-bot-token"
export TELEGRAM_CHAT_ID="-1002381931352"
```

Or edit `config.yaml` directly.

### Run

```bash
# Start with web dashboard
python main.py

# Access at http://localhost:8080
```

## 📊 Features

### Pipeline Monitors

| Service | Metrics Tracked | Alert Conditions |
|---------|----------------|------------------|
| **AWS** | Lambda invocations, errors, duration, throttles | Error rate >5%, Throttling |
| **Snowflake** | Query success rate, warehouse state, storage | Failure rate >10%, Warehouse suspended |
| **CRM** | API availability, latency, rate limits | API down, High latency (>5s) |

### Correlation Engine

Detects:
- **Cascading Failures**: When upstream failure causes downstream issues
- **Service Outages**: Widespread failures in single service
- **Pipeline Blockage**: Stuck pipeline steps blocking downstream work
- **Latency Propagation**: Latency spikes propagating through dependencies

### Alerting

Supports multiple channels with intelligent routing:

| Severity | Channels | Rate Limit |
|----------|----------|------------|
| Critical | Slack, Telegram, Email | 1/min |
| Warning | Slack, Telegram | 5/min |
| Info | Slack | 10/min |

Deduplication prevents alert fatigue - same issue won't repeat within 5 minutes.

### Dashboard

Real-time metrics including:
- Service health overview
- Pipeline execution timeline
- Active alerts with acknowledgment
- Historical trends

## 🔌 APIs

All endpoints available at `/api/v1/*`:

```bash
# Health check
curl http://localhost:8080/api/v1/health

# Get all metrics
curl http://localhost:8080/api/v1/metrics/snowflake

# View active alerts
curl http://localhost:8080/api/v1/alerts

# Send test alert
curl -X POST http://localhost:8080/api/v1/alerts/test
```

See [DEPLOY.md](DEPLOY.md) for full API reference.

## 🐳 Docker

```bash
# Build
docker build -t cross-service-monitor .

# Run
docker run -d \
  -p 8080:8080 \
  -e SNOWFLAKE_ACCOUNT=$SNOWFLAKE_ACCOUNT \
  -e SNOWFLAKE_USER=$SNOWFLAKE_USER \
  -e TELEGRAM_BOT_TOKEN=$TELEGRAM_BOT_TOKEN \
  cross-service-monitor
```

## 🧪 Testing

```bash
python tests/test_monitor.py
```

Tests cover:
- AWS Lambda health checks
- Snowflake query monitoring
- Correlation engine logic
- Alert manager delivery

## 📈 Architecture

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│    AWS      │────▶│   Snowflake  │────▶│    CRMs     │
│ (Lambda,S3) │     │  (Data Lake) │     │(HubSpot,SF) │
└─────────────┘     └──────────────┘     └─────────────┘
       │                   │                    │
       └───────────────────┼────────────────────┘
                           ▼
                 ┌─────────────────┐
                 │ Correlation     │
                 │ Engine          │
                 │ • Event Buffer  │
                 │ • Pattern Match │
                 │ • Root Cause    │
                 └─────────────────┘
                           ▼
                 ┌─────────────────┐
                 │ Alert Manager   │
                 │ • Routing Rules │
                 │ • Deduplication │
                 │ • Multi-channel │
                 └─────────────────┘
                           ▼
                 ┌─────────────────┐
                 │ Dashboard API   │
                 │ • REST Endpoints│
                 │ • Real-time UI  │
                 └─────────────────┘
```

## 🛠️ Extending

### Adding a New Service Monitor

Create `monitors/new_service.py`:

```python
from monitors.base import BaseMonitor

class NewServiceMonitor(BaseMonitor):
    async def check_health(self) -> Dict:
        # Implement health check
        pass
    
    async def get_metrics(self) -> Dict:
        # Return metrics dict
        pass
```

Register in `main.py`:

```python
from monitors.new_service import NewServiceMonitor
monitors['new_service'] = NewServiceMonitor(config)
```

### Adding Alert Channels

In `engine/alert_manager.py`, add method:

```python
async def _send_custom(self, alert: Alert) -> bool:
    # Your custom channel logic
    pass
```

Update routing rules in `config.yaml`.

## 📝 Contributing

1. Fork repository
2. Create feature branch
3. Make changes with tests
4. Submit PR

## 📄 License

MIT License - See LICENSE file

## 🤝 Support

For issues or questions:
- Review logs: `journalctl -u csm` 
- Check docs: `DEPLOY.md`
- Test components: `python tests/test_monitor.py`

## Architecture

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│    AWS      │────▶│   Snowflake  │────▶│    CRMs     │
│ (S3, Lambda)│     │  (Data Lake) │     │(HubSpot,SF) │
└─────────────┘     └──────────────┘     └─────────────┘
       │                   │                    │
       └───────────────────┼────────────────────┘
                           ▼
                 ┌─────────────────┐
                 │ Correlation     │
                 │ Engine          │
                 │ (Detect Issues) │
                 └─────────────────┘
                           ▼
                 ┌─────────────────┐
                 │ Dashboard &     │
                 │ Alerting        │
                 └─────────────────┘
```

## Components

### 1. Pipeline Monitors (`monitors/`)
- `aws_monitor.py` - CloudWatch metrics, Lambda invocations, S3 objects
- `snowflake_monitor.py` - Query performance, warehouse status, storage
- `crm_monitor.py` - API health, sync jobs, webhook delivery

### 2. Correlation Engine (`engine/`)
- `correlator.py` - Cross-service event correlation
- `anomaly_detector.py` - Lag detection, pattern recognition
- `alert_manager.py` - Alert routing and deduplication

### 3. Dashboard (`dashboard/`)
- `app.py` - FastAPI backend
- `static/` - React/Vue frontend
- Health overview, pipeline timelines, alert history

### 4. Data Storage (`storage/`)
- SQLite/PostgreSQL for metrics storage
- Time-series optimization

## Quick Start

```bash
cd cross-service-monitor
pip install -r requirements.txt
python -m dashboard.app  # Start dashboard on port 8080
```

## APIs

### Health Check
```
GET /api/v1/health
```

### Pipeline Status
```
GET /api/v1/pipelines/{name}/status
GET /api/v1/pipelines/all
```

### Alerts
```
GET /api/v1/alerts?severity=critical&active=true
POST /api/v1/alerts/test
```

### Metrics
```
GET /api/v1/metrics/aws
GET /api/v1/metrics/snowflake
GET /api/v1/metrics/crm
```

## Configuration

Edit `config.yaml`:
```yaml
services:
  aws:
    region: us-east-1
    check_interval: 60
  snowflake:
    account: your-account
    warehouse: COMPUTE_WH
    check_interval: 300
  crm:
    hubspot:
      enabled: true
    salesforce:
      enabled: false

alerts:
  slack_webhook: https://hooks.slack.com/...
  email: faisal@credologi.com
  threshold_lag_minutes: 15
```

## Monitoring Checklist

- [ ] AWS Lambda health
- [ ] S3 bucket access patterns
- [ ] Snowflake warehouse usage
- [ ] Query failure rates
- [ ] CRM API rate limits
- [ ] ETL pipeline completion times
- [ ] Data freshness SLA compliance
