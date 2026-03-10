# Flobase Capital Platform — Complete Platform Plan v3.0

**Version:** 3.0
**Created:** 2026-03-10
**Author:** Fas + Optimus
**Status:** Pre-Build — Requirements Finalized

───────────────────────────────────────────────────────

## The Business in Plain English

Flobase Capital is an asset-backed lender to Debt Settlement Companies (DSCs). DSCs enroll consumers with large credit card debt (avg. $15K–$100K+) into 3–5 year programs. They negotiate settlements with creditors and charge the consumer a performance fee (25–35% of enrolled debt) when each debt is settled. Problem: the DSC does all the work upfront but only gets paid on results — months or years later. They need cash now.

**Flobase's deal:** We advance 6.5–8% of a DSC's total enrolled debt as a lump sum. In return, we get the right to collect a large share of those future performance fees until we're repaid 125% of our advance (the "preferred return"). After that, we drop to a smaller residual share. We fund 85% of the advance from a warehouse credit line (SOFR + 15.5%), and put in 15% of our own equity. Typical breakeven: month 13. Typical return: ~1.35x MoIC, ~20%+ levered IRR.

───────────────────────────────────────────────────────

## How the Money Flows (The Business Model)

### Step 1 — Flobase evaluates a DSC's client portfolio

• The DSC shares their client data (client IDs, enrolled debt, payment history, credit scores, EPF %, etc.) — pull data from Snowflake; backup is upload spreadsheet
• Flobase runs an eligibility engine to filter out bad accounts (Knock-outs: debt < $15K, EPF < 25%, < 1 cleared payment, inactive status)
• Remaining accounts are "eligible" to be purchased

### Step 2 — Flobase advances capital

• Flobase pays the DSC a lump sum = typically 5–10% of total enrolled debt on the eligible accounts
• Example: $10M in enrolled debt → Flobase wires ~$700K to the DSC at 7% advance rate
• This creates a **Vintage** — a dated batch of purchased accounts (e.g., CLG-OCT-2025)
• Flobase borrows 85% of the purchase price from its credit facility (SOFR + 10.5%) and puts in 15% equity

### Step 3 — Cash comes back over time (Fee Waterfall)

• As the DSC settles debts month by month, performance fees are generated
• Those fees flow through a **waterfall**:
  — **First:** Flobase recovers 125% of its purchase price (the "Hurdle" / "Pre-Pref")
  — **Pre-Hurdle:** Flobase keeps 75% of fees, DSC keeps 25%
  — **Post-Hurdle:** Split flips — Flobase keeps 50%, DSC keeps 50%
• Flobase also pays its lender back principal + interest from its share

Cash flow per vintage per month:
  Net = Earned_Performance_Fee_Paid_By_Month − Interest_On_Warehouse_Line

Levered IRR cash flows:
  Month 0: (−) Equity_Contribution
  Month 1–N: EPF_post_split − Interest_expense − Principal_repayment

### Step 4 — Returns are tracked by vintage

• **MOIC** (Multiple on Invested Capital): total cash collected ÷ purchase price
• **Levered IRR**: calculated only on equity deployed (15%), net of interest + principal payments
• **Target levered IRR:** ~20%+
• **DPI** (Distributions to Paid-In): cumulative distributions ÷ equity invested

───────────────────────────────────────────────────────

## Platform Architecture — 6 Modules + Data Layer + Security

───────────────────────────────────────────────────────

## Data Layer (The Plumbing)

### Database Requirements
• Database must always have **2 backups** available at all times
• Automated backup runs **every 24 hours**
• Verify backup integrity on each run; alert on failure

### Source → RDS Flow

1. AWS Lambda runs a query against Forth's Snowflake on a schedule (or on-demand trigger from Retool)
2. Lambda transforms and loads records into RDS PostgreSQL
3. RDS uses an append-only model — no deletions, full audit trail
4. Records tagged by: DSC_ID, Tranche_ID, Ingest_Date

### Core RDS Tables

| Table | Purpose |
|-------|---------|
| users | Platform users and roles |
| dsc_settings | DSC profiles — rates, splits, hurdles, guarantee schedules, banking info |
| tranche_master | Each vintage (purchase batch) — date, purchase price, accounts, terms snapshot |
| waterfall_ledger | Monthly fee flows per vintage per account with Effective_Start_Date / Effective_End_Date |
| payment_ledger | Raw payment events from DSC CRM |
| pii_vault | Encrypted client PII (separate from main DB, CloudTrail reveal logging) |
| clients | One row per consumer file (all Snowflake fields) |

### Key Computed Fields
• flobase_receivable_purchase_price — created field (doesn't exist in DSC data, Flobase creates it)
• Effective_Start_Date / Effective_End_Date — for tracking when split adjustments are active

### Write-Back
After purchase is finalized, Lambda fires a POST to Forth's API tagging the purchased client_id records with INVESTOR = "Flobase" and PURCHASE_DATE.

### Snowflake Collateral View — Confirmed Fields

**Partner Info:** CLIENT_ID, DSC_ID, COMPANY_NAME, ACCOUNT_NAME

**Purchase Info (Flobase adds):** INVESTOR (= "Flobase"), PURCHASE_DATE, Purchase_Amount, Advance_Rate, FIRST_PAYMENT_CLEAR_DATE, NUMBER_OF_CLEARED_PAYMENTS

**PII (separate vault):** FIRST_NAME, LAST_NAME

**Debt Info:** ENROLLED_DATE, CREDIT_SCORE, ENROLLED_DEBT, SETTLED_DEBT, SETTLEMENT_DATE, CANCELLED_DEBT, CANCELLED_DATE, EPF_PERCENTAGE, TOTAL_EXPECTED_FEE, PROGRAM_LENGTH, NUMBER_OF_DEBTS, NUMBER_OF_SETTLED_DEBTS, COMP_TEMPLATE, GRADUATION_DATE, PAYMENT_FREQUENCY, CONTACT_STATUS, NUMBER_OF_NSFS, CURRENT_ESCROW_BALANCE

**Performance Fee:** EPF_OPEN, EPF_PENDING, EPF_CLEARED, EPF_CLEARED_DATE

Fields marked ADD TO VIEW = need to be added to the existing Snowflake view by the DSC.

───────────────────────────────────────────────────────

## Module 1: Dashboard (3 Tiers + Sub-Pages)

### Tier 1 — Portfolio Level
Single row per DSC showing aggregate portfolio performance:

• **Cancelled Debt by Client ID**
• **Added Debt by Client ID**
• Capital Deployed (total flobase_receivable_purchase_price)
• Target IRR vs Actual IRR
• ROI, DPI (Distributions to Paid-In), MoIC (Multiple on Invested Capital)
• Default/Cancellation Rate
• Existing Balance = enrolled_debt − settled_debt − cancelled_debt
• Debt Balance Delta = original_debt − cancelled_debt
• Vintage count, account count

### Tier 2 — DSC Level (click into a DSC)
Each row = one vintage for that DSC:

• **Cancelled Debt by Client ID**
• **Added Debt by Client ID**
• Vintage name, purchase date, enrolled debt, advance paid, advance %
• Current pre/post hurdle status
• Performance fee collected (cumulative), breakeven progress %
• Benchmark vs Actual vs Delta (manual benchmark input per vintage)
• Performance Guarantee status flag (🟢/🟡/🔴)

### Tier 3 — Vintage Level (click into a vintage)

• **Cancelled Debt by Client ID**
• **Added Debt by Client ID**
• Purchase price, enrolled debt, pref hurdle ($), current split %
• Performance curves (all 3 — see Module 4)
• Guarantee monitoring + split adjustment controls
• IRR return profile chart
• Client-level ledger (each account's EPF payments by month)

### Vintage Library
• Browse each **Client ID** and data purchased under a vintage
• View by vintage name (e.g., CLG-OCT-2025)
• Client-level detail: enrolled debt, EPF %, payment history, status
• **Export functionality** — download vintage data as CSV/Excel

### Dashboard Sub-Pages

**Main Page:**
• Existing Balance = enrolled_debt − settled_debt − cancelled_debt
• Debt Balance Delta = original_debt − cancelled_debt
• Total Funded = sum of all flobase_receivable_purchase_price
• Total Cancellations = total cancelled_debt across portfolio
• Performance Fee = earned_performance_fee_paid_by_month (cumulative)
• Debt Enrollment by Monthly Vintage — chart
• Capital Deployed by Monthly Vintage — chart
• Filter levels: Portfolio → DSC → Vintage → Affiliate
• Where do the names come from: Snowflake

**Total Funded Sub-Page:**
• Enrolled Debt (Cleared) — only accounts with ≥ 1 cleared payment
• Advance Payment (flobase_receivable_purchase_price)
• DSC Fees = enrolled_debt × settlement_fee_percentage
• Advance Percentage = purchase price ÷ enrolled debt
• Table format: one row per vintage, sortable, exportable

**Total Cancellations Sub-Page:**
• Table by vintage: Total Debt Funded | Cancelled Debt | Change %
• Shows attrition rate — critical for underwriting future vintages

**Performance Fee Sub-Page (Waterfall Table):**
• Rows = enrollment month/vintage
• Columns = calendar months
• Each cell = earned_performance_fee_paid_by_month for that vintage in that month
• Three header rows: Benchmark (manual input) | Actual (calculated) | Delta
• This is how Flobase monitors whether DSC performance matches expectations

### Investor Snapshot
Editable card view (similar to DSC card) showing:
• Facility total capacity
• Cost
• SOFR rate
• SOFR floor
• Used capacity
• Available capacity
• Haircut capital percentage
• All fields editable by authorized users (Admin + Manager)

### Affiliate View
• Cancelled Debt by Client ID
• Added Debt by Client ID
• Aggregate performance across DSCs under affiliate

───────────────────────────────────────────────────────

## Module 2: Purchase Criteria (Underwriting Engine)

### DSC Onboarding — Add/Change Process

1. Flobase creates the DSC record: name, email, deal terms (performance guarantees, purchase requirements)
2. A **link is sent to the DSC** to complete their profile:
   • Phone, title
   • Banking section: account details for funding vintage purchases
   • **Hash all bank account numbers** except last 4 of account number
   • Flobase Manager and Admin roles have **full view** of account numbers
3. **MFA required** for all users
4. If DSC wants to **change bank account info**:
   • Must first authenticate using MFA before changes can be saved
   • **Alert generated** when DSC changes banking info (notifies Flobase admin)

### Step 1 — Select DSC
Pick from existing DSC profiles or add new one. Each profile stores: name, code (e.g., CLG), advance rate %, preferred capital return %, pre/post-hurdle splits, cost of capital (SOFR + 10.5%), chargeback policy, performance guarantee milestones.

### Step 2 — Load Portfolio Data
Two modes:
• **API pull:** Lambda queries Forth Snowflake live for that DSC's current eligible client population
• **CSV fallback:** Manual upload if Snowflake connection is down (up to 10MB)

Key fields ingested: client_id, credit_score, enrolled_debt, settlement_fee_percentage, first_payment_cleared_date, status, cancelled_debt, settled_debt, etc.

### Step 3 — Eligibility Engine (Knock-Out Rules)
Automatic disqualifiers:
• Enrolled debt < $15,000
• Performance fee % < 25%
• Client status = Inactive / Cancelled
• Cleared payments ≤ 0 (no cleared payment yet) or ≤ 2 for bi-weekly payment plans
• First payment cleared date = null

Configurable thresholds — admin can adjust cutoffs per DSC.

### Step 4 — Review Results
• Split view: Eligible accounts | Knock-out accounts
• Show all key attributes for each account
• Allow manual override (include/exclude specific accounts)
• Export full list

### Step 5 — Execute Purchase
• Name the vintage (convention: YYYY_MM_DD or DSC-MON-YEAR)
• Set advance rate % (can deviate from DSC default)
• Set chargeback reduction if applicable
• Calculate: effective purchase price, advance %, DSC fee total
• Tag accounts as purchased (eventually: push back to Forth via API to mark receivable_purchase_date and Flobase Name on File)
• Lock the vintage — terms are captured at point of purchase

### Post-Purchase: Split Adjustment
• If DSC underperforms against guarantee schedule, Flobase can adjust the pre/post-split % for that vintage
• System tracks: base split, current split, adjustment history with dates and reasons
• Contractual mechanism — if 6-month cumulative cash < 90% of target → trigger adjustment
• All adjustments logged with date + reason → reflected in future waterfall_ledger entries

### Comp Template ID Tracking Workflow

**Purpose:** Track and flag changes to compensation template IDs from Forth.

**Daily Workflow (Scheduled 2:00 AM):**
1. **Capture ID** from first buy file — API pull from Forth
2. **Ping to verify** template has not changed by checking ID name
3. If different → **create a flag** (alert Flobase team)
4. Check: Can we change the comp template ID via API?
   • If **yes** → auto-correct via API
   • If **no** → generate a **Bulk ID Change Export** to send to DSCs
5. Run once daily at 2:00 AM

**Audit & Fee Reconciliation (when comp ID changes):**
• Look at **gross settlement amount**
• Compare to what was actually collected
• Compare to deal terms percentages
• Identify missing fees from splits
• **Summary table:** gross payments vs. total fees expected vs. fees received
• **Flag** if variance exceeds **2%**

### Performance Guarantee Schedule (example: Cordoba Law Group)
• Month 6: ≥ 21.2% cumulative cash collected
• Month 9: ≥ 37.7%
• Month 12: ≥ 50.1%
• Month 18: ≥ 66.8%
• 90% threshold = trigger, 95% threshold = warning zone

───────────────────────────────────────────────────────

## Module 3: Reporting

**What it does:** Generates clean reports for lenders (credit facility providers), partners, and internal review. This is the compliance and transparency layer.

### Key Attributes Exported
• client_id, dsc_id, created_date, status, enrolled_debt, unsettled_debt, settled_debt
• settlement_%_of_original_debt, settlement_%_of_current_debt
• settlements_by_month, earned_performance_fee_paid_by_month
• flobase_receivable_purchase_price, purchase_receivable_date (= receivable funded date)
• settlement_fee_percentage, contact_id, affiliate_name

Filter levels: Portfolio → DSC → Vintage → Affiliate

### Data Collection — Low Priority
• Creditor names
• Settlement percentages
• Speed of settlement (date enrolled → date settlement occurred)
• Average balance by creditor
• Credit card debt by zip code
• Credit card debt by gender

### Notes
• Creditor name is NOT shown in the UI but IS included in exports
• Affiliate Name field appears after Contact ID in tables
• Column labels: "Receivable Date" → "Receivable Funded Date"
• Reports are sent to lenders to verify collateral performance

### Fee Reconciliation Reports
• Gross settlement amounts per vintage
• Expected fees (based on deal terms)
• Actual fees received
• Variance tracking with **2% threshold flag**
• Summary table: gross payments vs total fees expected vs fees received

───────────────────────────────────────────────────────

## Module 4: Performance Monitoring

### Three Performance Curves Per Vintage

**1. Cash Collections (% of Purchase Price)**
• Y = cumulative earned_performance_fee_paid_by_month ÷ purchase price
• Target: 100% (full repayment of advance)
• CLG-OCT-2025 at 5 months: 19.1% → 46.4% latest reading

**2. Settlements (% of Enrolled Debt)**
• Y = cumulative settled_debt ÷ enrolled_debt
• Typical range: 55–65% by program end
• CLG-OCT-2025 at 5 months: 32%

**3. Cancellations (% of Enrolled Debt)**
• Y = cumulative cancelled_debt ÷ enrolled_debt
• Threshold: < 20% healthy; historical avg: ~38.6%
• CLG-OCT-2025 at 5 months: 11.2% ✅

### Return Profile (IRR Calculator)
• Plots cash flow stream: (−Equity) + (EPF_post_split − interest − principal) per month
• IRR calculated on equity-only basis (15% of advance)
• Benchmark line = manually set target IRR per vintage
• DPI = cumulative distributions ÷ equity invested
• MoIC = (cumulative + projected remaining) ÷ equity invested

### Waterfall Engine
• Track 125% hurdle (Pre-Pref) per vintage
• Pre-Hurdle split: 75% Flobase / 25% DSC
• Post-Hurdle split: 50% Flobase / 50% DSC
• Automatic split calculation on each fee collection
• Lender repayment tracking (principal + interest from Flobase share)

### Performance Guarantee Monitoring
• At M6, M9, M12, M18: compare actual cumulative cash % vs guarantee target
• 🟢 ≥ 95% of target = On Track
• 🟡 90–95% of target = Warning zone
• 🔴 < 90% of target = Triggered → show split adjustment controls
• All adjustments logged with date + reason → reflected in future waterfall_ledger entries

───────────────────────────────────────────────────────

## Module 5: DSC Client Portal (Retool Portals)

Separate external portal — DSC partners only.

### DSC Admin View
• Full Detailed Metrics dashboard for their dsc_id (all vintages, all charts, all performance curves)
• User Management module: create / delete / reset passwords for their team's View Only users
• Cannot see any other DSC's data (RLS enforced)

### DSC View Only View
• Read-only Detailed Metrics dashboard
• Lands directly on their portfolio view
• No admin controls, no user management

### Authentication
• Retool Portals (External Apps) — separate from internal Retool auth
• dsc_id injected into every query via Retool session token
• RLS enforced at RDS level

───────────────────────────────────────────────────────

## Module 6: Global User Management (Flobase Admin)

### Flobase Admin Manages
• Create / edit / deactivate Flobase Admin accounts
• Create DSC Admin accounts (one per DSC, linked to dsc_id)
• Reset any user's password
• View full user audit log (logins, actions, exports)

### DSC Admin Manages (within their portal)
• Create / delete / reset passwords for their own DSC View Only users
• Cannot create other DSC Admins or modify users outside their dsc_id

───────────────────────────────────────────────────────

## Security & Access Control

• **MFA required** for all users (Cognito)
• Bank account numbers **hashed** (last 4 visible only)
• Full account view: Flobase Manager + Admin only
• Bank info change requires **MFA re-authentication**
• **Alert on banking info changes** (Slack/email notification to Flobase admin)
• Role-based access: Admin, Manager, DSC User, Affiliate User, Investor
• PII vault with encryption + CloudTrail reveal logging
• JWT authorization with Cognito JWKS validation
• WAF protection on all API endpoints
• SSE-KMS encryption on all data at rest

───────────────────────────────────────────────────────

## Scheduled Jobs

| Job | Schedule | Description |
|-----|----------|-------------|
| Database Backup | Every 24 hours | Maintain 2 backups at all times, verify integrity |
| Snowflake Sync | Configurable | Pull latest client data from Forth's Snowflake |
| Comp Template ID Check | Daily @ 2:00 AM | Pull from Forth API, verify unchanged, flag/export if changed |
| Fee Reconciliation | Weekly (TBD) | Compare expected vs received fees, flag >2% variance |
| SOFR Rate Update | Daily | Pull latest SOFR from Federal Reserve API |

───────────────────────────────────────────────────────

## Confirmed Technical Stack

| Component | Technology |
|-----------|-----------|
| Data Source | DSC CRM (Forth system) — CSV export + REST API pull |
| Backend | AWS Lambda (Python 3.12), API Gateway |
| Database | RDS PostgreSQL (to be provisioned) |
| Frontend | Retool (internal) + Retool Portals (DSC external) |
| Auth | Cognito (MFA enforced) + JWT Authorizer |
| Snowflake | Lambda → Snowflake connector (existing layer) |
| Interest Rate | SOFR API from Federal Reserve |
| Secrets | AWS Secrets Manager + SSM Parameter Store |
| Encryption | KMS (data at rest), TLS (in transit) |
| WAF | credologi-waf-prod |
| Monitoring | CloudWatch + Mission Control dashboard |
| Hosting | AWS (us-east-1, account 386757865833) |

───────────────────────────────────────────────────────

## Development Roadmap — 7 Weeks

| Phase | Timeline | Deliverables |
|-------|----------|-------------|
| 1 — Backend & Data Infrastructure | Week 1–2 | Provision RDS PostgreSQL + full schema (7 tables). Lambda → Snowflake ingestion. Lambda → Forth API write-back. Secrets Manager config. Database backup automation. PII vault setup. |
| 2 — Admin UI, User Management & Purchase Engine | Week 2–3 | Global User Management module. DSC onboarding flow (self-service link, banking, MFA). Purchase Analyzer: DSC dropdown, sliders, Eligible/Knock-Out tables, live calc banner, CSV upload fallback. Finalize Purchase action + Forth write-back trigger. |
| 3 — Financial Ledger & Waterfall Logic | Week 4 | SQL views for breakeven tracking. Versioned waterfall engine (payment_ledger join to waterfall_ledger). 125% hurdle logic, 75/25 → 50/50 split. Adjust Future Splits modal with Effective Date. Adjustment log. |
| 4 — Dashboards & Performance Monitoring | Week 5–6 | All 3 tier dashboards. Vintage Library with export. Investor Snapshot card. Performance curves (cash, settlement, cancellation). IRR/MOIC/DPI calculator. Performance guarantee monitoring (🟢🟡🔴). Comp Template ID daily checker. Fee reconciliation with 2% variance flag. |
| 5 — Reporting, Portals & Security | Week 6–7 | Export engine (CSV/Excel). Lender reports. DSC Client Portal (Retool Portals with RLS). Affiliate View. Bank account hashing + MFA re-auth + change alerts. SOFR API feed. |

───────────────────────────────────────────────────────

## What's Already Built vs What Needs Building

| Component | Status |
|-----------|--------|
| AWS Infrastructure (VPC, WAF, KMS, CloudTrail, IAM) | ✅ Built — 100% reusable |
| Snowflake connection + service user + RSA auth | ✅ Built — 100% reusable |
| Cognito User Pool + JWT Authorizer | ✅ Built — needs MFA + roles |
| Lambda → Snowflake ingestion pattern | ✅ Built — retarget to RDS |
| Data validation / knock-out pattern | ✅ Built — adapt eligibility rules |
| Variance check / reconciliation pattern | ✅ Built — adapt for fee reconciliation |
| Security logging + CloudWatch | ✅ Built — 100% reusable |
| React prototype (full UI) | ✅ Built — needs Retool rebuild |
| RDS PostgreSQL + schema | 🔲 Needs provisioning |
| Waterfall calculator engine | 🔲 Needs building |
| IRR/MOIC/DPI calculator (SQL views) | 🔲 Needs building |
| Comp Template ID daily checker | 🔲 Needs building |
| Fee reconciliation engine | 🔲 Needs building |
| Retool app (official UI) | 🔲 Needs building |
| DSC Client Portal (Retool Portals) | 🔲 Needs building |
| DSC onboarding self-service flow | 🔲 Needs building |
| Forth API write-back Lambda | 🔲 Needs building |
| SOFR rate feed | 🔲 Needs building |
| Export engine | 🔲 Needs building |
| PII vault + masking | 🔲 Needs building |
| Bank account hashing + MFA re-auth | 🔲 Needs building |

**Reuse estimate: ~53% of infrastructure/backend already exists.**

───────────────────────────────────────────────────────

## Open Questions

1. Can Forth API accept comp template ID changes? (determines auto-fix vs bulk export flow)
2. Which Snowflake tables/schemas for Flobase-specific client data pull?
3. Investor snapshot — who can edit? Admin only or Manager+Admin?
4. Fee reconciliation — how far back should audit go when comp ID changes?
5. Creditor data collection — what's the source? DSC-provided or scraped from settlement records?
6. RDS instance size — start with db.t3.medium or larger?
7. Retool licensing — how many seats needed (Flobase team + DSC portals)?

───────────────────────────────────────────────────────

*This document is the source of truth for the Flobase Capital Platform build. Update as requirements evolve.*
