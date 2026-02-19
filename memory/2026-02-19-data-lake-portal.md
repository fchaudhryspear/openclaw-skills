# Data Lake Operations Portal - 2026-02-19

## Overview
Complete operations dashboard for the Real-Time Financial Data Lake with real-time monitoring, user management, and alerting.

## Portal URL
**Primary**: https://portal.credologi.com  
**CloudFront**: https://d13ermioqnr3qb.cloudfront.net

## Authentication
- **User Pool**: us-east-1_M6lTgVQaw (credologi-users)
- **Admin User**: faisal@credologi.com
- **Login URL**: https://portal.credologi.com

## Features

### 1. Dashboard
- **Real-time API Health Checks** - Auto-refresh every 30 seconds
- **CloudWatch Metrics** - Request counts, error rates, latency
- **Data Volume Tracking** - Records received/processed/failed by source
- **Throughput Metrics** - Records per minute

### 2. Applications
- List all loan applications
- View application details
- Update loan status (Approve/Reject/Pending)
- Create new applications

### 3. User Management
- List all Cognito users
- Create new users with groups
- Enable/disable users
- Reset passwords (sends email)
- Delete users

### 4. Data Flow (NEW)
- Visual architecture diagram
- CRM ↔ Data Lake ↔ LOS workflow
- API endpoints documentation
- Benefits explanation

### 5. Snowflake Monitoring (NEW)
- Database health status
- Table statistics
- Query performance metrics
- Query error tracking
- Security status (failed logins, MFA)

### 6. AWS Security (NEW)
- Security Hub findings
- GuardDuty threats
- IAM security report
- Compliance standards

### 7. Alerts
- View alert configuration
- Test alerts (SNS + Slack)
- Run health checks with auto-alerts
- Alert channels: Email (SNS) + Slack

### 8. Test Runner
- Execute pytest remotely
- View test results
- Console output viewer

## Architecture

```
┌─────────────┐      ┌──────────────────┐      ┌─────────────────┐
│   Portal    │──────│  Monitoring API  │──────│  CloudWatch     │
│  (React)    │      │  (Lambda)        │      │  (Metrics/Logs) │
└─────────────┘      └──────────────────┘      └─────────────────┘
                            │
                            ├──────────────────┐
                            │                  │
                     ┌──────▼──────┐   ┌──────▼──────┐
                     │  DynamoDB   │   │  Cognito    │
                     │  (Counts)   │   │  (Users)    │
                     └─────────────┘   └─────────────┘
```

## Data Flow Architecture

**CRM → Data Lake → LOS → Data Lake → CRM**

### 4-Step Workflow:
1. **Ingestion** - CRMs feed customer data to Data Lake
2. **Transmission** - Data Lake pushes to LOS for processing
3. **Processing** - LOS processes and returns status
4. **Synchronization** - Data Lake syncs status back to CRMs

### Benefits:
- Switch LOS without changing CRM integrations
- Add new CRMs without modifying the LOS
- Centralized data for reporting
- Complete audit trail

## API Endpoints

### Monitoring API
**Base URL**: https://o6whnf80tb.execute-api.us-east-1.amazonaws.com/Prod

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Service health checks |
| `/metrics` | GET | CloudWatch metrics (24h) |
| `/data-volumes` | GET | DynamoDB record counts |
| `/errors` | GET | Recent error logs |
| `/run-tests` | POST | Execute pytest |
| `/users` | GET | List Cognito users |
| `/users` | POST | Create user |
| `/users/{username}/disable` | POST | Disable user |
| `/users/{username}/enable` | POST | Enable user |
| `/users/{username}/reset-password` | POST | Reset password |
| `/users/{username}` | DELETE | Delete user |
| `/alerts/config` | GET | Alert configuration |
| `/alerts/test` | POST | Send test alerts |
| `/alerts/trigger-health-check` | POST | Run health check + alerts |
| `/snowflake/health` | GET | Snowflake health status |
| `/snowflake/metrics` | GET | Snowflake usage metrics |
| `/snowflake/errors` | GET | Snowflake query errors |
| `/snowflake/security` | GET | Snowflake security status |
| `/security/summary` | GET | Comprehensive security summary |
| `/security/findings` | GET | Security Hub findings |
| `/security/guardduty` | GET | GuardDuty findings |
| `/security/iam` | GET | IAM security report |

## Alert Configuration

To enable alerts, set these environment variables on the MonitoringApiFunction:

```bash
ALERT_TOPIC_ARN=arn:aws:sns:us-east-1:386757865833:data-lake-alerts
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK/URL
ALERTS_ENABLED=true
```

### Setting up SNS Topic
```bash
aws sns create-topic --name data-lake-alerts
aws sns subscribe \
  --topic-arn arn:aws:sns:us-east-1:386757865833:data-lake-alerts \
  --protocol email \
  --notification-endpoint faisal@credologi.com
```

### Setting up Slack Webhook
1. Go to https://api.slack.com/apps
2. Create New App → From Scratch
3. Add Incoming Webhooks
4. Activate Incoming Webhooks
5. Add New Webhook to Workspace
6. Copy webhook URL

## Deployment

### Portal (S3 + CloudFront)
```bash
cd portal
npm run build
aws s3 sync dist/ s3://portal.credologi.com/ --delete
aws cloudfront create-invalidation --distribution-id E2QA9DG4SSZ3NU --paths "/*"
```

### Monitoring API (SAM)
```bash
sam build -t monitoring-template.yaml
sam deploy -t monitoring-template.yaml \
  --stack-name data-lake-monitoring \
  --region us-east-1 \
  --capabilities CAPABILITY_IAM
```

## Cognito Configuration

### User Pool: us-east-1_M6lTgVQaw
- **Pool Name**: credologi-users
- **Groups**: GlobalAdmins, Admins, Users, ReadOnly
- **MFA**: Optional (SMS)
- **Password Policy**: 12+ chars, symbols, numbers

### Existing Users
- faisal@credologi.com (GlobalAdmins)
- rakesh@credologi.com (GlobalAdmins)

## Stack Information

| Stack | Resource | ID/ARN |
|-------|----------|--------|
| data-lake-monitoring | API Gateway | o6whnf80tb |
| data-lake-monitoring | Lambda | MonitoringApiFunction |
| real-time-data-lake | API Gateway | pe6rxp3vtd |
| real-time-data-lake | DynamoDB | real-time-data-lake-loan-applications |
| real-time-data-lake | Cognito | us-east-1_M6lTgVQaw |
| Portal | S3 Bucket | portal.credologi.com |
| Portal | CloudFront | d13ermioqnr3qb.cloudfront.net |

## Documentation

- **README.md**: https://github.com/fchaudhryspear/real-time-financial-data-lake/blob/main/README.md
- **ARCHITECTURE.md**: https://github.com/fchaudhryspear/real-time-financial-data-lake/blob/main/docs/ARCHITECTURE.md
- **USER_GUIDE.md**: https://github.com/fchaudhryspear/real-time-financial-data-lake/blob/main/User%20Guides/USER_GUIDE.md
- **CHANGELOG.md**: https://github.com/fchaudhryspear/real-time-financial-data-lake/blob/main/CHANGELOG.md

## Last Updated
2026-02-19 08:45 CST
