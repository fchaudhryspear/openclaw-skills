# Mission Control — Remediation Workflow Fixes

**Date:** 2026-03-10
**Scope:** End-to-end remediation flow audit and bug fixes
**Files changed:**
- `mission-control-backend/mission-control/src/app.js`
- `mission-control-frontend/src/components/SecurityAlerts.tsx`
- `mission-control-backend/mission-control/template.yaml`

---

## What Was Working

- Backend route structure for all four remediation endpoints (POST /remediate, GET /remediation-status, POST /resolve, GET /security-alerts) was complete and correctly wired.
- `REMEDIATION_STRATEGIES` mapping, `detectStrategy`, `buildPlaybook`, and all three executors (`executeCvePatch`, `executeS3Hardening`, `executeConfigEnforcement`) were fully implemented.
- DynamoDB table was defined in the SAM template with TTL and correct key schema.
- Frontend state machine (`idle → loading-preview → preview → confirming → tracking`) and polling loop were correctly structured.
- `PreviewPanel` and `JobTracker` sub-components rendered the right content for their phases.
- `resolveAlert` mutation and resolve dialog were complete.
- CORS headers were applied to all Lambda responses.

---

## Bugs Fixed

### 1. Resolved findings reappearing as ACTIVE after workflow update (`app.js`)

**Root cause:** `handleSecurityAlerts` queried SecurityHub by `RecordState` only (`ACTIVE` vs `ARCHIVED`). When a user calls `BatchUpdateFindings` to set `WorkflowStatus = RESOLVED`, SecurityHub updates the workflow status but does **not** change the `RecordState` to `ARCHIVED`. The finding continued to appear in the ACTIVE query on next page load.

**Fix:** Split the SecurityHub query into three parallel calls:
1. `RecordState=ACTIVE` + `WorkflowStatus IN (NEW, NOTIFIED)` → mapped as `ACTIVE`
2. `RecordState=ACTIVE` + `WorkflowStatus IN (RESOLVED, SUPPRESSED)` → mapped as `RESOLVED`
3. `RecordState=ARCHIVED` → mapped as `RESOLVED`

```js
// Before (app.js ~571)
const [activeResult, resolvedResult] = await Promise.all([
  securityHub.send(new GetFindingsCommand({
    Filters: { RecordState: [{ Value: "ACTIVE", ... }], ... }
  })),
  securityHub.send(new GetFindingsCommand({
    Filters: { RecordState: [{ Value: "ARCHIVED", ... }], ... }
  })),
]);

// After
const [activeResult, resolvedWorkflowResult, archivedResult] = await Promise.all([
  // ACTIVE + NEW/NOTIFIED workflow
  // ACTIVE + RESOLVED/SUPPRESSED workflow
  // ARCHIVED record state
]);
```

---

### 2. `label` not stored in DynamoDB → status polling returns unlabelled jobs (`app.js`)

**Root cause:** `handleRemediateAlert` persisted the remediation job to DynamoDB without the `label` field. The initial POST response included `label`, but subsequent calls to `GET /remediation-status` read from DynamoDB and returned a job without `label`. The frontend `JobTracker` snackbar message and any label displays would show `undefined`.

**Fix:** Added `label: { S: stratInfo.label }` to the `PutItemCommand` in `handleRemediateAlert`, and updated `handleRemediationStatus` to read it back with a fallback to `REMEDIATION_STRATEGIES[strategy].label` for any pre-existing records in the table.

---

### 3. `JobTracker` Logs tab never visible when no playbook (`SecurityAlerts.tsx`)

**Root cause:** The tab content for "Playbook" used `activeTab === (job.buildLogs ? 1 : 1)` — a ternary where both branches evaluate to `1`, so the condition is always `activeTab === 1` regardless of whether `buildLogs` is present. The "Logs" content was hardcoded at `activeTab === 2`. When a job has `buildLogs` but no `playbook`, the Tabs component renders "Logs" as Tab 1, but the content block checked `activeTab === 2` — so the logs panel would never display.

**Fix:**
```tsx
// Before (SecurityAlerts.tsx ~294)
{activeTab === (job.buildLogs ? 1 : 1) && job.playbook && (...)}  // always 1 — bug
{activeTab === 2 && job.buildLogs && (...)}                         // never 1 — broken for logs-only

// After
{activeTab === 1 && job.playbook && (...)}                          // Playbook at 1
{job.buildLogs && activeTab === (job.playbook ? 2 : 1) && (...)}   // Logs at dynamic index
```

---

### 4. `RemediationJob.label` required type caused TypeScript errors (`SecurityAlerts.tsx`)

**Root cause:** The `RemediationJob` interface declared `label: string` as required, but the status polling endpoint did not previously return `label` (fixed above). Even after the backend fix, older DynamoDB records may not have the field.

**Fix:** Changed `label: string` → `label?: string` and similarly `canAutomate: boolean` → `canAutomate?: boolean` in the `RemediationJob` interface.

---

### 5. `PreviewPanel loading` prop always `false` (`SecurityAlerts.tsx`)

**Root cause:** `loading={false}` was hardcoded, so the "Run Remediation" button never showed its loading spinner. While functionally harmless (the phase transitions away from `preview` immediately when confirm fires), the prop value was incorrect.

**Fix:** Changed to `loading={remediatePhase === 'confirming'}` to correctly reflect state.

---

### 6. No Cognito Authorizer in SAM template → `claims` always undefined (`template.yaml`)

**Root cause:** The SAM template did not define a `Globals.Api.Auth` section. Without a configured Cognito Authorizer, API Gateway passes requests to Lambda with an empty `requestContext.authorizer`. The Lambda's `isAdmin(claims)` function receives `undefined` and always returns `false`, causing every call to an admin route (`/security-alerts/resolve`, `/security-alerts/remediate`, `/security-alerts/remediation-status`, `/users`, `/run-tests`) to return **403 Forbidden**.

**Fix:** Added `Globals.Api.Auth` with a `CognitoAuthorizer` backed by `UserPoolArn`. Also set `AddDefaultAuthorizerToCorsPreflight: false` so OPTIONS preflight requests are not blocked by auth.

Explicit `Auth: Authorizer: NONE` events were added for the truly public routes (`GET /`, `GET /health`, `GET /flows`) while the protected `/{proxy+}` catch-all inherits the Cognito default.

---

### 7. No API Gateway CORS configuration (`template.yaml`)

**Root cause:** CORS was handled entirely inside Lambda (via `corsHeaders` on every response and an `OPTIONS` early-return). This works but means Lambda is invoked for every preflight request, adding latency. API Gateway-level CORS is more correct and handles preflight without touching Lambda.

**Fix:** Added `Globals.Api.Cors` with `AllowOrigin`, `AllowHeaders`, and `AllowMethods` matching the Lambda's existing `corsHeaders`. Both layers are now consistent.

---

## Summary Table

| # | File | Area | Severity | Type |
|---|------|------|----------|------|
| 1 | app.js | `handleSecurityAlerts` WorkflowStatus filter | High | Functional bug |
| 2 | app.js | `label` missing from DynamoDB PutItem | Medium | Data bug |
| 3 | app.js | `handleRemediationStatus` missing `label` | Medium | Data bug |
| 4 | SecurityAlerts.tsx | `JobTracker` tab index `(logs ? 1 : 1)` | High | UI bug |
| 5 | SecurityAlerts.tsx | `RemediationJob.label` required type | Low | TypeScript type error |
| 6 | SecurityAlerts.tsx | `loading={false}` hardcoded | Low | UX issue |
| 7 | template.yaml | Missing Cognito Authorizer | Critical | Auth / infrastructure |
| 8 | template.yaml | No API Gateway CORS | Medium | Infrastructure |

---

## No Changes Needed

- `REMEDIATION_STRATEGIES` mapping — complete and correct
- `detectStrategy` — correct classification logic
- `buildPlaybook` — correct CLI command generation
- `executeS3Hardening` / `executeCvePatch` / `executeConfigEnforcement` — correctly implemented
- `ensureRemediationTable` — correct auto-create logic
- `handleResolveAlert` — correct `BatchUpdateFindings` usage with `SUFFIX` lookup
- `handleRemediateAlert` dryRun/execute split — correct
- Frontend polling loop (`startPolling` / `useEffect` cleanup) — correct
- Frontend `resolveAlert` mutation — correct
- Frontend `fetchRemediationPreview` / `startRemediation` / `fetchRemediationStatus` functions — correct
- `VITE_API_URL` ends with `/` in `.env` — consistent with all fetch calls
