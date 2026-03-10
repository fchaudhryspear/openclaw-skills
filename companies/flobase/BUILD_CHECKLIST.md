# Flobase Capital Platform — Build Checklist
## What's Built (Reusable from Real-Time Data Lake) vs What's Missing

**Last Updated:** 2026-03-10

---

## ✅ BUILT — Reusable from Real-Time Data Lake

### AWS Infrastructure
- [x] **AWS Account** — `386757865833`, us-east-1
- [x] **VPC** — `vpc-061e4256723c5130d` (172.31.0.0/16) with private subnets, NAT Gateway, S3+DDB endpoints
- [x] **API Gateway** — `pe6rxp3vtd` (real-time-data-lake) — can extend or create new
- [x] **Cognito User Pool** — `us-east-1_p8zDDh0py` (MFA capable, 1 user) — needs MFA enforcement + new user roles
- [x] **WAF** — `credologi-waf-prod` (4 rules, protects 4 APIs) — can add Flobase APIs
- [x] **KMS Keys** — `alias/data-lake-logs` for encryption at rest
- [x] **CloudTrail** — `OrganizationTrail` with KMS encryption (just configured today)
- [x] **IAM Password Policy** — 14 char min, complexity, 90-day rotation (just configured today)
- [x] **S3 Bucket** — `prod-lending-data-lake` (SSE-KMS, versioned, lifecycle)
- [x] **DynamoDB** — `real-time-data-lake-loan-applications` (KMS, PITR) + idempotency table

### Lambda Functions (Reusable Patterns)
- [x] **Application Webhook** — Snowflake ingestion pattern (reads from Snowflake, writes to DynamoDB/S3)
- [x] **Batch Merge** — Snowflake batch operations with security logging
- [x] **Variance Check** — Data comparison/reconciliation pattern (good template for 2% fee variance check)
- [x] **Data Quality Check** — Validation rules engine (good template for eligibility/knock-out rules)
- [x] **Snowflake Key Rotation** — Automated RSA key rotation via Secrets Manager
- [x] **DLQ Replay** — Dead letter queue replay for failed events
- [x] **JWT Authorizer** — Cognito JWT validation (just rewritten with proper JWKS)

### Snowflake Connection
- [x] **Snowflake account** — `SBUBJHD-TY50972`
- [x] **Service user** — `FCHAUDHRY_SVC` with RSA key auth (just created)
- [x] **Role** — `DATA_LAKE_ROLE` with `INGESTION_WH` access
- [x] **Existing roles** — `LAMBDA_INGESTION_ROLE`, `LENDING_DB_LAMBDA`
- [x] **Secrets Manager** — `snowflake-lambda-key` (private key, public key, account, user, role, warehouse)
- [x] **SSM Parameters** — `/data-lake/snowflake/account`, `/data-lake/snowflake/user`
- [x] **Snowflake Lambda Layer** — `snowflake-dependencies:1` (~60MB with snowflake-connector-python)
- [x] **Database** — `APPLICATIONS` database, `PUBLIC` schema (may need new schema for Flobase)

### Security (Just Fixed Today)
- [x] **JWT Authorizer** — Proper Cognito JWKS validation
- [x] **.gitignore** — Fixed (was broken from merge conflict)
- [x] **Secrets purged** — Private keys and .env removed from git history
- [x] **SSE-KMS** — S3 encryption upgraded from SSE-S3
- [x] **SQS encryption** — KMS enabled on all queues
- [x] **Runtime** — Upgraded to Python 3.12

### Monitoring & Ops
- [x] **CloudWatch Logs** — Structured JSON logging on all functions
- [x] **Security event logging** — Dedicated security logger in all Lambda functions
- [x] **SNS Alert Topic** — `SecurityAlertTopic` (needs subscriptions)
- [x] **DLQ** — Dead letter queues on SQS for failed events
- [x] **Mission Control** — Security alerts dashboard at missioncontrol.credologi.com

---

## 🔲 MISSING — Needs to Be Built for Flobase

### Database
- [ ] **RDS PostgreSQL** — NOT provisioned yet (Data Lake uses DynamoDB, Flobase needs relational)
  - Tables needed: `users`, `dsc_settings`, `tranche_master`, `waterfall_ledger`, `payment_ledger`, `pii_vault`, `clients`
  - Need: VPC security group, subnet group, parameter group
- [ ] **Database backups** — 2 backups, every 24 hours, integrity verification
- [ ] **PII Vault** — Separate encrypted table for names/addresses/phones with CloudTrail reveal logging

### Lambda Functions (New)
- [ ] **Snowflake → RDS Ingestion** — Lambda to pull from Forth's Snowflake view and load into RDS
  - Pattern exists (application_webhook), needs RDS target instead of DynamoDB
- [ ] **Forth API Write-back** — Lambda to POST purchased client_id records back to Forth
  - Marks: INVESTOR = "Flobase", PURCHASE_DATE
- [ ] **Eligibility Engine** — Knock-out rules processor
  - Template: Data Quality Check function (validation logic pattern)
  - Rules: debt < $15K, EPF < 25%, < 1 cleared payment, inactive status
- [ ] **Waterfall Calculator** — Monthly fee split computation
  - 125% hurdle, 75/25 pre-hurdle, 50/50 post-hurdle
  - Lender repayment tracking
- [ ] **IRR/MOIC Calculator** — SQL views + Lambda for return metrics
  - Levered IRR on 15% equity, net of interest + principal
- [ ] **Comp Template ID Checker** — Daily 2AM scheduled Lambda
  - Forth API pull, compare, flag, bulk export
- [ ] **Fee Reconciliation** — Gross vs expected vs received with 2% variance flag
- [ ] **SOFR Rate Feed** — Lambda to pull from Federal Reserve API

### Frontend
- [ ] **Retool App** — Official UI (React prototype exists but needs Retool rebuild)
  - Dashboard (3 tiers: Portfolio → DSC → Vintage)
  - Purchase Criteria engine
  - Reporting & exports
  - Performance monitoring (curves, IRR, guarantees)
- [ ] **DSC Client Portal** — Retool Portals for external DSC access
  - DSC Admin view (metrics + user management)
  - DSC View Only (read-only dashboard)
  - RLS enforced by dsc_id
- [ ] **Vintage Library** — Browse by vintage, client-level detail, export
- [ ] **Investor Snapshot** — Editable card (facility capacity, SOFR, haircut %)
- [ ] **DSC Onboarding Flow** — Self-service link for DSC profile completion

### Auth & Security
- [ ] **MFA enforcement** — Cognito MFA for all users (template says OFF, need ON)
- [ ] **Role-based access** — Admin, Manager, DSC User, Affiliate User, Investor
- [ ] **Bank account hashing** — Hash all digits except last 4
- [ ] **MFA re-auth for bank changes** — Step-up authentication
- [ ] **Banking change alerts** — Notification to Flobase admin

### API & Integration
- [ ] **Forth API integration** — REST API pull for client data (currently CSV only)
- [ ] **Forth API write-back** — Tag purchased accounts
- [ ] **Comp Template ID API** — Check/change capability
- [ ] **SOFR API** — Federal Reserve rate feed
- [ ] **Export engine** — CSV/Excel for all views

### Scheduled Jobs
- [ ] **Snowflake sync** — Periodic pull from Forth's Snowflake
- [ ] **Comp Template ID check** — Daily @ 2:00 AM
- [ ] **Fee reconciliation** — Periodic comparison
- [ ] **Database backup verification** — Daily integrity check

---

## 🔄 PARTIALLY BUILT — Needs Modification

| Component | Current State | What's Needed |
|-----------|--------------|---------------|
| Cognito User Pool | 1 user, MFA OFF | Add roles, enforce MFA, DSC portal auth |
| Snowflake Connection | Connected to APPLICATIONS.PUBLIC | Need Flobase-specific schema/view |
| Application Webhook | Writes to DynamoDB | Adapt pattern for RDS PostgreSQL |
| Variance Check | Compares Snowflake data | Adapt for fee reconciliation (2% threshold) |
| Data Quality Check | Validates loan status | Adapt for eligibility knock-out rules |
| WAF | Protects 4 APIs | Add Flobase API endpoints |
| SNS Alerts | Topic exists, no subscribers | Add email/Slack subscriptions |
| JWT Authorizer | Validates Cognito tokens | Add role-based claims checking |

---

## Priority Build Order

### Phase 1 — Foundation (Week 1-2)
1. Provision RDS PostgreSQL + schema (all 7 tables)
2. Create Snowflake → RDS ingestion Lambda (adapt webhook pattern)
3. Configure Cognito: MFA ON, roles, DSC user groups
4. Set up database backup automation

### Phase 2 — Purchase Engine (Week 2-3)
5. Build eligibility engine Lambda (adapt data quality check)
6. Vintage creation workflow
7. Forth write-back Lambda
8. Retool Purchase Criteria UI

### Phase 3 — Dashboard (Week 3-4)
9. Dashboard views (all 3 tiers) in Retool
10. Waterfall performance fee table
11. Investor Snapshot card

### Phase 4 — Financial Engine (Week 5-6)
12. Waterfall calculator (split logic)
13. IRR/MOIC SQL views
14. Performance curves
15. Guarantee monitoring + split adjustment

### Phase 5 — Ops & Polish (Week 6-7)
16. Comp Template ID daily checker
17. Fee reconciliation with 2% variance flag
18. Export engine
19. DSC Portal (Retool Portals)
20. DSC onboarding self-service flow
21. Banking security (hashing, MFA re-auth, alerts)
22. SOFR rate feed

---

## Estimated Reuse Savings

| Category | Total Items | Reusable | New Build | Reuse % |
|----------|------------|----------|-----------|---------|
| Infrastructure (VPC, WAF, KMS, CloudTrail) | 8 | 8 | 0 | 100% |
| Auth (Cognito, JWT) | 3 | 2 | 1 | 67% |
| Lambda Patterns | 7 | 5 | 2 | 71% |
| Snowflake Connection | 6 | 6 | 0 | 100% |
| Database | 8 | 0 | 8 | 0% |
| Frontend | 8 | 0 | 8 | 0% |
| **Total** | **40** | **21** | **19** | **53%** |

> ~53% of the infrastructure/backend is already built. The main gaps are RDS PostgreSQL, Retool frontend, and the financial calculation engine (waterfall, IRR, MOIC).
