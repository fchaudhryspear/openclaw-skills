---
id: mission-control-portal-summary
created: 2026-02-24
type: project-overview
confidence: 1.0
tags: [mission-control, credologi, fintech, serverless, react, amplify, sam, production, critical]
---
# Credologi Mission Control Portal - Critical Project Overview

**Status**: Production Live
**Importance**: CRITICAL - Core operational dashboard for debt settlement workflow (CRM ↔ Data Lake ↔ LOS).

## Project Locations:
- **Backend Root**: `/Users/faisalshomemacmini/.openclaw/workspace/mission-control-backend/mission-control`
- **Frontend Root**: `/Users/faisalshomemacmini/dev/mission-control-frontend`

## Backend Architecture (AWS SAM)
- **Stack Name**: `mission-control` (us-east-1)
- **API Gateway**: `MissionApi` (secured with Cognito Authorizer)
- **Lambda Function**: `MonitoringFunction` (`app.js` in `src/`)
  - **Runtime**: Node.js 20.x, ARM64
  - **Key Handlers**:
    - `/health` (GET): Validates Snowflake secret via Secrets Manager.
    - `/flows` (GET): Queries DynamoDB `AggregatesTable` for daily metrics (ProjectionExpression for cost optimization).
    - `/security-alerts` (GET): Fetches active `HIGH`/`CRITICAL` findings from AWS Security Hub.
    - `/run-tests` (POST): Initiates AWS CodeBuild project (`CODEBUILD_PROJECT_NAME` env var).
    - `/test-status` (GET): Polls CodeBuild for test run status.
    - `/users` (GET/POST, `/users/{username}/{action}` POST): Zero-Trust User Management (Cognito AdminList/Create/Enable/Disable/Reset/Delete) with in-Lambda JWT group authorization (`isAdmin` check for `GlobalAdmins`/`Admins` groups).
- **DynamoDB**: `AggregatesTable` (PAY_PER_REQUEST, `Date` HASH, `FlowType` RANGE, streams enabled).
- **IAM Policies**: `AmazonCognitoPowerUser`, `AWSSecurityHubReadOnlyAccess`, `SecretsManager` access, `CodeBuild` access, `DynamoDB` specific actions.
- **Environment Variables**:
  - `USER_POOL_ID`: `us-east-1_M6lTgVQaw`
  - `AGGREGATES_TABLE`: `AggregatesTable`
  - `CODEBUILD_PROJECT_NAME`: `credologi-test-suite` (example).

## Frontend Architecture (React/Amplify)
- **Technology Stack**: React 18, TypeScript, Vite, AWS Amplify v6, Material-UI (MUI), @tanstack/react-query.
- **Authentication**: AWS Amplify `fetchAuthSession` with Cognito (`us-east-1_M6lTgVQaw`).
- **Hosting**: AWS Amplify Console (CloudFront/S3) with custom domain `missioncontrol.credologi.com`.
- **Environment Variables (VITE_ prefixes)**:
  - `VITE_API_URL`: Backend API Gateway Endpoint.
  - `VITE_REGION`: `us-east-1`.
  - `VITE_USER_POOL_ID`: `us-east-1_M6lTgVQaw`.
  - `VITE_CLIENT_ID`: Cognito App Client ID.
- **Key Components**:
  - `Users.tsx`: Frontend for Zero-Trust User Management (list, create modal, enable/disable/reset/delete actions) with TanStack Query mutations.
  - `DataFlows.tsx`: Displays daily data lake metrics from `/flows` endpoint.
  - `SecurityAlerts.tsx`: Displays Security Hub findings from `/security-alerts` endpoint.
  - `TestRunner.tsx`: UI to trigger and monitor backend test runs.

## DNS & SSL Configuration
- **Domain**: `missioncontrol.credologi.com`
- **Registrar**: GoDaddy
- **DNS Records**:
  - **CNAME (Traffic)**: `missioncontrol` pointing to `dxxxxxxxxx.amplifyapp.com` (Amplify-generated CloudFront domain).
  - **CNAME (ACM Validation)**: `_f06af5762db5e0319049249ebdb1755b.missioncontrol` pointing to `_a43243624bb5ffeb644e7036bf6579d5.jkddzztszm.acm-validations.aws.` (for SSL certificate issuance).
- **SSL Certificate**: ACM issued for `missioncontrol.credologi.com`.

## Monitoring & Ops
- **CloudWatch Dashboard**: `Credologi-Data-Lake-Monitor` (metrics for API Gateway, Lambda, DynamoDB, and custom Logs Insights queries).
- **CloudWatch Alarms**: Configured for API 5XX errors and Lambda errors (linked to SNS for email alerts).

This project is considered of **CRITICAL** importance due to its role in the core financial debt settlement workflow and its adherence to stringent security and compliance requirements. All changes and operational procedures must be handled with the utmost care.