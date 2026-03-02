# Cross-Service Correlation Monitor - Design Document

## Executive Summary

This system provides unified monitoring and alerting across data pipelines spanning AWS → Snowflake → CRM systems. It detects failures, identifies root causes through correlation, and provides real-time visibility via a web dashboard.

## Problem Statement

Modern data architectures span multiple services:
- **AWS**: Lambda functions process data, S3 stores files, SQS queues messages
- **Snowflake**: Data warehouse for analytics and transformation
- **CRMs**: HubSpot, Salesforce for customer data sync

When something breaks, it's hard to tell:
- Is it AWS, Snowflake, or the CRM?
- Did one failure cause others (cascading)?
- How stale is the data?
- Which pipeline is affected?

This system solves those problems.

## Components

### 1. Service Monitors (`monitors/`)

Each monitor queries its service's health metrics:

#### AWS Monitor
- Queries CloudWatch for Lambda metrics (invocations, errors, duration)
- Checks SQS queue backlogs
- Monitors CloudWatch alarms
- Fetches recent error logs from CloudWatch Logs

**Key Metrics:**
```python
LambdaMetrics:
  - invocations: int
  - errors: int
  - error_rate: float (errors / invocations)
  - duration_avg_ms: float
  - throttle_count: int
```

**Alerts When:**
- Error rate > 5%
- Throttling detected
- Queue backlog > 1000 messages

#### Snowflake Monitor
- Queries `SNOWFLAKE.ACCOUNT_USAGE` views
- Tracks query success/failure rates
- Monitors warehouse states
- Checks storage usage
- Detects failed login attempts

**Key Metrics:**
```python
QueryMetrics:
  - total_queries: int
  - successful_queries: int
  - failed_queries: int
  - success_rate: float
  - avg_execution_time_ms: float
  - credits_used: float
```

**Alerts When:**
- Query failure rate > 10%
- Warehouse suspended too long
- Failed logins spike

#### CRM Monitor
- Tests API availability with sample requests
- Tracks response latency
- Checks data freshness in objects
- Monitors webhook delivery

**Key Metrics:**
```python
CRMAPIHealth:
  - status: 'healthy' | 'degraded' | 'down'
  - success_rate: float
  - avg_latency_ms: float
  - last_successful_request: datetime
```

**Alerts When:**
- API returns non-200 status
- Latency exceeds threshold
- Data older than SLA

### 2. Correlation Engine (`engine/correlator.py`)

The intelligence layer that connects events across services:

#### Event Model
```python
CorrelationEvent:
  - timestamp: datetime
  - source: str ('aws', 'snowflake', 'crm')
  - resource: str ('lambda:name', 'table:name')
  - event_type: str ('error', 'failure', 'latency_spike')
  - severity: str ('info', 'warning', 'critical')
  - details: Dict
```

#### Correlation Patterns

**Cascading Failures:**
```
AWS Lambda fails → Snowflake load fails → CRM sync stalls
   ↓                    ↓                       ↓
[Error]            [Error]                 [Warning]
```
Detected when: Upstream failure followed by downstream errors within correlation window (5 min default).

**Service Outage:**
Multiple errors from same source in short time → likely outage vs. random glitches.
Threshold: ≥5 errors in window.

**Pipeline Blockage:**
Pipeline step A fails, step B hasn't started → blocked pipeline.
Uses `pipeline_definitions` from config to know expected flow.

**Latency Propagation:**
Slow AWS → Slow Snowflake queries → Slow CRM responses
Detected when: Latency spikes propagate downstream.

#### Issue Model
```python
CorrelatedIssue:
  - issue_id: str (e.g., "ISSUE-0001")
  - title: str
  - severity: str
  - status: 'active' | 'acknowledged' | 'resolved'
  - events: List[CorrelationEvent]
  - affected_services: List[str]
  - root_cause_hypothesis: Optional[str]
  - impact_score: float
```

Impact score calculation:
```
impact = severity_weight * affected_service_count
severity_weight: info=1, warning=3, critical=10
```

### 3. Alert Manager (`engine/alert_manager.py`)

Handles alert delivery with smart routing:

#### Routing Rules
```yaml
critical: [slack, telegram, email]
warning: [slack, telegram]
info: [slack]
```

#### Deduplication
Same alert won't repeat within configured window (default 5 minutes).
Dedup key based on: `source:resource:title` hash.

#### Rate Limiting
Prevents alert fatigue during outages:
- Critical: 1 alert/min per source/resource
- Warning: 5 alerts/min
- Info: 10 alerts/min

#### Channels Implemented

**Slack:**
- Webhook integration
- Rich formatting with colors by severity
- Action buttons (Acknowledge, View Details)

**Telegram:**
- Bot API integration
- Markdown formatting
- Inline keyboards for quick actions

**Email:**
- SMTP integration
- Plain text (compatible with all clients)
- HTML option available

### 4. Dashboard API (`dashboard/app.py`)

FastAPI-based REST interface:

#### Endpoints

**Health & Status:**
- `GET /api/v1/health` - Basic health
- `GET /api/v1/health/detailed` - Full system status
- `GET /api/v1/dashboard/summary` - Dashboard data

**Pipelines:**
- `GET /api/v1/pipelines` - List pipelines
- `GET /api/v1/pipelines/status` - All statuses
- `GET /api/v1/pipelines/{name}/status` - Specific

**Metrics:**
- `GET /api/v1/metrics/aws`
- `GET /api/v1/metrics/snowflake`
- `GET /api/v1/metrics/crm`

**Alerts:**
- `GET /api/v1/alerts` - Active alerts
- `POST /api/v1/alerts/acknowledge/{id}`
- `POST /api/v1/alerts/resolve/{id}`
- `POST /api/v1/alerts/test`

**Events:**
- `POST /api/v1/events` - Ingest external events

#### Frontend (`dashboard/static/index.html`)

Pure HTML + vanilla JavaScript (no build step needed):
- Auto-refresh every 30 seconds
- Color-coded status indicators
- Real-time alert display
- Responsive design (Tailwind CSS)

## Configuration

### Pipeline Definitions

Define your data flow:

```yaml
pipeline_definitions:
  - name: "daily-data-load"
    schedule: "0 6 * * *"  # Daily at 6 AM
    timeout_minutes: 30
    steps:
      - service: aws
        resource: lambda:extract_data
      - service: snowflake
        resource: table:staging_raw
      - service: crm
        resource: hubspot:contacts
    depends_on: []
    
  - name: "realtime-sync"
    schedule: "*/15 * * * *"  # Every 15 minutes
    steps:
      - service: snowflake
        resource: view:customer_master
      - service: crm
        resource: salesforce:accounts
    depends_on: ["daily-data-load"]
```

### Alert Thresholds

Configure in `config.yaml`:

```yaml
services:
  aws:
    alarms:
      lambda_error_threshold: 5     # Triggers warning alert
      lambda_duration_p99_ms: 5000  # Triggers if P99 > 5s
      
  snowflake:
    alerts:
      query_failure_rate_threshold: 0.1  # 10%
      
alerting:
  rules:
    - name: "pipeline_lag"
      condition: "pipeline.lag_minutes > threshold"
      threshold_minutes: 15
```

## Deployment Options

### Option 1: Direct Python

```bash
pip install -r requirements.txt
python main.py
```

Best for: Development, small deployments

### Option 2: Docker

```bash
docker build -t csm .
docker run -p 8080:8080 -e SNOWFLAKE_ACCOUNT=xxx csm
```

Best for: Production containers

### Option 3: Kubernetes

See `DEPLOY.md` for full K8s manifests.

Best for: Enterprise deployments

### Option 4: Serverless

Adapt monitors to run as:
- AWS Lambda (scheduled with EventBridge)
- Google Cloud Functions
- Azure Functions

## Data Flow

```
┌─────────────────────────────────────────────────────────────┐
│                   MONITORING LOOP                           │
│                                                             │
│  ┌──────────┐  every 60s   ┌────────────────────────────┐  │
│  │  Timer   │─────────────▶│  Health Checker           │  │
│  └──────────┘              │                           │  │
│                            │  ┌─────────────────────┐  │  │
│                            │  │ Check AWS Lambdas   │──┼──┤
│                            │  │ (error rates, etc.) │  │  │
│                            │  └─────────────────────┘  │  │
│                            │                           │  │
│                            │  ┌─────────────────────┐  │  │
│                            │  │ Check Snowflake     │──┼──┤
│                            │  │ (query failures)    │  │  │
│                            │  └─────────────────────┘  │  │
│                            │                           │  │
│                            │  ┌─────────────────────┐  │  │
│                            │  │ Check CRM APIs      │──┼──┤
│                            │  │ (availability)      │  │  │
│                            │  └─────────────────────┘  │  │
│                            └──────────┬────────────────┘  │
│                                       │                   │
│                               issues found?               │
│                                       │                   │
│                              ┌────────┴────────┐         │
│                              ▼                 ▼         │
│                      ┌────────────┐    ┌────────────┐   │
│                      │ Correlator │    │ Alert Mgr  │   │
│                      │ • Group    │    │ • Route    │   │
│                      │ • Identify │    │ • Send     │   │
│                      └────────────┘    └────────────┘   │
└─────────────────────────────────────────────────────────┘
                         │                        │
                         ▼                        ▼
                  ┌──────────────┐        ┌──────────────┐
                  │ Issues Table │        │ Slack/       │
                  │ (Active)     │        │ Telegram/    │
                  └──────────────┘        │ Email        │
                                          └──────────────┘
                                                   │
                                          User acknowledges
                                                   │
                                                   ▼
                                          ┌──────────────┐
                                          │ Dashboard    │
                                          │ (Real-time)  │
                                          └──────────────┘
```

## Security Considerations

### Secrets Management

**DO NOT commit secrets to Git!**

Recommended approaches:

1. **Environment Variables:**
```bash
export SNOWFLAKE_PRIVATE_KEY="-----BEGIN..."
export TELEGRAM_BOT_TOKEN="123456:...
```

2. **AWS Secrets Manager:**
```python
import boto3
client = boto3.client('secretsmanager')
secret = client.get_secret_value(SecretId='snowflake-key')
```

3. **Kubernetes Secrets:**
```yaml
env:
  - name: SNOWFLAKE_PASSWORD
    valueFrom:
      secretKeyRef:
        name: sf-secrets
        key: password
```

### Network Security

- Run behind reverse proxy (nginx, ALB)
- Add authentication layer
- Restrict network access (VPC, firewall rules)
- Use TLS for all external communications

### API Authentication (Optional)

Add API key middleware:

```python
from fastapi import HTTPException, Header

@app.get("/api/v1/...")
async def protected(x_api_key: str = Header(None)):
    if x_api_key != os.getenv("API_KEY"):
        raise HTTPException(status_code=403)
```

## Performance Considerations

### Scalability

**Horizontal Scaling:**
- Dashboard can be load-balanced
- Each monitor instance independent
- Consider shared state store (Redis) for clustering

**Data Volume:**
- Event buffer limited to 10,000 events
- Old events pruned automatically
- Historical data can be exported to time-series DB

### Resource Usage

Typical resource consumption:
- CPU: ~10% (one core)
- Memory: ~200MB
- Network: Minimal (periodic API calls)

## Testing Strategy

### Unit Tests
- Test each monitor independently
- Mock external API responses
- Verify alert generation logic

### Integration Tests
- End-to-end flow simulation
- Test correlation patterns
- Verify alert delivery (to test channels)

### Load Tests
- Simulate high event volume
- Test dashboard under load
- Verify no memory leaks

Run tests:
```bash
python tests/test_monitor.py
```

## Future Enhancements

### Phase 2 (Next Quarter)

1. **Historical Analytics**
   - Store metrics in time-series DB (Prometheus/Timescale)
   - Build trend analysis
   - Predictive alerting (ML-based anomaly detection)

2. **More Services**
   - GCP BigQuery
   - Azure Data Factory
   - Additional CRMs (Pipedrive, Zoho)

3. **Advanced Correlation**
   - Graph-based dependency mapping
   - Automatic root cause identification
   - Machine learning for pattern recognition

4. **Mobile App**
   - iOS/Android app for alerts
   - Push notifications
   - Quick action controls

5. **Automation**
   - Auto-remediation scripts
   - Self-healing workflows
   - Incident playbooks

### Metrics Export

Integration with observability platforms:

```python
# Prometheus exporter
from prometheus_client import Counter, Gauge

SERVICE_HEALTH = Gauge('csm_service_health', 'Service health', ['service'])
ACTIVE_ALERTS = Gauge('csm_active_alerts', 'Active alerts', ['severity'])

# Expose at /metrics endpoint
```

## Cost Analysis

### Infrastructure Costs

**Minimum Setup (Development):**
- Single VM/tiny container: $5-10/month
- No additional cloud costs

**Production Setup:**
- Container orchestration (ECS/EKS): $50-100/month
- Managed database (if used): $20-50/month
- Total: ~$100-150/month

### API Costs

**Snowflake:**
- Account_USAGE queries are free (metadata)
- Minimal compute for lightweight checks

**AWS:**
- CloudWatch API calls: Minimal cost
- Logs API: Based on data scanned

**CRMs:**
- HubSpot: Standard API limits (100 req/sec)
- Salesforce: Standard limits
- Should stay well within free tiers

## Maintenance

### Regular Tasks

**Daily:**
- Monitor alert volume
- Review new correlated issues
- Verify dashboard accessibility

**Weekly:**
- Review alert thresholds (false positives?)
- Check for new service failures
- Update pipeline definitions if changed

**Monthly:**
- Audit active integrations
- Rotate credentials if needed
- Review and archive old issues

### Version Updates

```bash
# Update to latest version
git pull origin main
pip install -r requirements.txt --upgrade
systemctl restart cross-service-monitor
```

### Backup Strategy

Backup essential configuration:
- `config.yaml` - All settings
- `.env` - Environment variables (keep secure!)
- Custom monitors/scripts

**NOT required:**
- Generated metrics (re-collectable)
- Event buffer (transient)
- Alert history (can be re-fetched from channels)

## Conclusion

This system provides comprehensive visibility into cross-service data pipelines. Key benefits:

✅ **Single Pane of Glass** - One dashboard for all services
✅ **Intelligent Correlation** - Find root causes quickly  
✅ **Multi-Channel Alerts** - Reach teams wherever they are
✅ **Extensible Architecture** - Easy to add new services
✅ **Production Ready** - Tested, documented, deployable

Total codebase: ~3,450 lines of Python + HTML
Development time: ~1 week

Ready for production deployment.
