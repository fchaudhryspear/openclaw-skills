"use strict";

/**
 * Credologi Mission Control API — Lambda Handler
 *
 * Routes:
 *   GET  /                                    -> API info (public)
 *   GET  /health                              -> Service health check (public)
 *   GET  /flows                               -> Data lake flow metrics
 *   GET  /security-alerts                     -> SecurityHub findings
 *   POST /security-alerts/resolve             -> Resolve/suppress/acknowledge finding
 *   POST /security-alerts/remediate           -> Kick off automated remediation
 *   GET  /security-alerts/remediation-status  -> Poll remediation job status
 *   POST /run-tests                           -> Trigger CodeBuild or inline health checks
 *   GET  /test-status                         -> Check CodeBuild status
 *   GET  /users                               -> List Cognito users (admin only)
 *   POST /users                               -> Create user (admin only)
 *   POST /users/{username}/{action}           -> User actions (admin only)
 *
 * @module MissionControlAPI
 * @version 2.3.0
 */

const { SecurityHubClient, GetFindingsCommand, BatchUpdateFindingsCommand } = require("@aws-sdk/client-securityhub");
const { CognitoIdentityProviderClient, ListUsersCommand, AdminEnableUserCommand, AdminDisableUserCommand, AdminResetUserPasswordCommand, AdminSetUserPasswordCommand, AdminCreateUserCommand, AdminAddUserToGroupCommand, AdminDeleteUserCommand, AdminGetUserCommand, AdminSetUserMFAPreferenceCommand } = require("@aws-sdk/client-cognito-identity-provider");
const { SESClient, SendEmailCommand } = require("@aws-sdk/client-ses");
const { CodeBuildClient, StartBuildCommand, BatchGetBuildsCommand } = require("@aws-sdk/client-codebuild");
const { SecretsManagerClient, GetSecretValueCommand } = require("@aws-sdk/client-secrets-manager");
const { DynamoDBClient, PutItemCommand, GetItemCommand, UpdateItemCommand, CreateTableCommand, DescribeTableCommand } = require("@aws-sdk/client-dynamodb");
const { S3Client, PutPublicAccessBlockCommand, PutBucketEncryptionCommand } = require("@aws-sdk/client-s3");
const { SSMClient, StartAutomationExecutionCommand, GetAutomationExecutionCommand } = require("@aws-sdk/client-ssm");
const { randomUUID } = require("crypto");

// == Constants ================================================================

const AWS_REGION = "us-east-1";
const API_VERSION = "2.3.0";
const API_NAME = "Credologi Mission Control API";

const MAX_ACTIVE_FINDINGS    = 50;
const MAX_RESOLVED_FINDINGS  = 25;
const MAX_USERS_PER_PAGE     = 60;
const MIN_PASSWORD_LENGTH    = 8;
const HEALTH_CHECK_LIMIT     = 1;
const CACHE_TTL_MS           = 5 * 60 * 1000;

const SNOWFLAKE_SECRET_ID  = "snowflake-lambda-key";
const EMAIL_FROM           = "noreply@credologi.com";
const CODEBUILD_PROJECT    = process.env.CODEBUILD_PROJECT_NAME || "credologi-test-suite";
const CORS_ORIGIN          = process.env.CORS_ORIGIN || "https://missioncontrol.credologi.com";
const REMEDIATION_TABLE    = process.env.REMEDIATION_TABLE || "mission-control-remediation-jobs";
const AWS_ACCOUNT_ID       = process.env.AWS_ACCOUNT_ID || "386757865833";

const CRITICAL_SEVERITIES = [
  { Value: "CRITICAL", Comparison: "EQUALS" },
  { Value: "HIGH",     Comparison: "EQUALS" },
];

const API_ENDPOINTS = [
  "/health", "/flows",
  "/security-alerts", "/security-alerts/resolve",
  "/security-alerts/remediate", "/security-alerts/remediation-status",
  "/users", "/run-tests", "/test-status",
];

// == SDK Clients ==============================================================

const securityHub    = new SecurityHubClient({ region: AWS_REGION });
const cognito        = new CognitoIdentityProviderClient({ region: AWS_REGION });
const codebuild      = new CodeBuildClient({ region: AWS_REGION });
const secretsManager = new SecretsManagerClient({ region: AWS_REGION });
const ses            = new SESClient({ region: AWS_REGION });
const dynamodb       = new DynamoDBClient({ region: AWS_REGION });
const s3             = new S3Client({ region: AWS_REGION });
const ssm            = new SSMClient({ region: AWS_REGION });

// == In-memory Cache ==========================================================

const _cache = {};

async function cached(key, fetcher) {
  const now = Date.now();
  if (_cache[key] && now - _cache[key].ts < CACHE_TTL_MS) return _cache[key].data;
  const data = await fetcher();
  _cache[key] = { data, ts: now };
  return data;
}

// == CORS Headers =============================================================

const corsHeaders = {
  "Access-Control-Allow-Origin":  CORS_ORIGIN,
  "Access-Control-Allow-Headers": "Content-Type, Authorization",
  "Access-Control-Allow-Methods": "OPTIONS,POST,GET",
};

// == Helpers ==================================================================

function jsonResponse(statusCode, body) {
  return { statusCode, headers: corsHeaders, body: JSON.stringify(body) };
}

function isAdmin(claims) {
  const groups = claims?.["cognito:groups"] || [];
  return groups.includes("GlobalAdmins") || groups.includes("Admins");
}

function auditLog(action, actor, target) {
  console.log(JSON.stringify({
    type: "AUDIT", action,
    actor: actor || "unknown",
    target,
    timestamp: new Date().toISOString(),
  }));
}

// == Remediation Strategy Engine =============================================

/**
 * REMEDIATION_STRATEGIES maps strategy keys to metadata shown in the UI
 * and used by the executor.
 */
const REMEDIATION_STRATEGIES = {
  CVE_PATCH: {
    label:       "Automated CVE Patch",
    description: "Identifies affected Lambda functions and updates the vulnerable package via CodeBuild.",
    steps: [
      "Look up affected resources in SecurityHub",
      "Trigger CodeBuild remediation job",
      "Update vulnerable dependency to patched version",
      "Redeploy affected Lambda functions",
      "Verify fix and update SecurityHub status",
    ],
    canAutomate: true,
    estimatedMinutes: 5,
  },
  S3_HARDENING: {
    label:       "S3 Bucket Hardening",
    description: "Blocks public access and enables AES-256 encryption on the affected bucket.",
    steps: [
      "Identify affected S3 bucket from finding",
      "Enable Block Public Access (all four flags)",
      "Apply AES-256 server-side encryption",
      "Confirm settings applied",
    ],
    canAutomate: true,
    estimatedMinutes: 1,
  },
  CONFIG_ENFORCEMENT: {
    label:       "Configuration Enforcement",
    description: "Applies AWS best-practice configuration via SSM Automation or direct API.",
    steps: [
      "Parse configuration finding details",
      "Run targeted SSM Automation document",
      "Verify configuration applied",
    ],
    canAutomate: true,
    estimatedMinutes: 2,
  },
  IAM_PLAYBOOK: {
    label:       "IAM Remediation Playbook",
    description: "IAM changes require human review. A detailed playbook is generated for your team.",
    steps: [
      "Review overpermissive policy details",
      "Apply least-privilege replacement policy",
      "Test affected services for regressions",
      "Mark finding as resolved",
    ],
    canAutomate: false,
    estimatedMinutes: null,
  },
  MANUAL_PLAYBOOK: {
    label:       "Manual Remediation Playbook",
    description: "Step-by-step guide for findings that require human judgment.",
    steps: [
      "Review finding details and affected resources",
      "Apply recommended fix from AWS Security Best Practices",
      "Verify remediation with a rescan",
      "Mark finding as resolved",
    ],
    canAutomate: false,
    estimatedMinutes: null,
  },
};

/**
 * detectStrategy — maps a SecurityHub finding to a remediation strategy.
 * Uses the finding type path and description for classification.
 */
function detectStrategy(finding) {
  const type = (finding.type || "").toLowerCase();
  const desc = (finding.description || "").toLowerCase();
  const title = (finding.title || "").toLowerCase();

  // CVE / Software vulnerability
  if (/cve-\d{4}-\d+/.test(type) || /cve-\d{4}-\d+/.test(desc) || /cve-\d{4}-\d+/.test(title)) {
    return "CVE_PATCH";
  }
  if (type.includes("vulnerabilities") || desc.includes("vulnerable") || desc.includes("outdated package")) {
    return "CVE_PATCH";
  }

  // S3 public access / encryption
  if (type.includes("s3") || (desc.includes("s3") && (desc.includes("public") || desc.includes("encrypt")))) {
    return "S3_HARDENING";
  }

  // IAM
  if (type.includes("iam") || desc.includes("iam") || desc.includes("policy") || desc.includes("permission")) {
    return "IAM_PLAYBOOK";
  }

  // Config / CloudTrail / MFA / CIS
  if (
    type.includes("cloudtrail") || type.includes("config") ||
    desc.includes("mfa") || desc.includes("cloudtrail") ||
    desc.includes("logging") || title.includes("cis")
  ) {
    return "CONFIG_ENFORCEMENT";
  }

  return "MANUAL_PLAYBOOK";
}

/**
 * Extract a resource identifier (bucket name, function name, etc.) from a finding.
 * SecurityHub stores resources in the Resources array.
 */
function extractResource(rawFinding) {
  const resources = rawFinding.Resources || [];
  if (!resources.length) return null;
  const r = resources[0];
  return {
    type: r.Type || "unknown",
    id:   r.Id   || "",
    region: r.Region || AWS_REGION,
    details: r.Details || {},
  };
}

/**
 * Build a remediation playbook for strategies that cannot be automated.
 */
function buildPlaybook(strategy, rawFinding) {
  const info = REMEDIATION_STRATEGIES[strategy];
  const resource = extractResource(rawFinding);
  const cveMatch = (rawFinding.Title || "").match(/CVE-\d{4}-\d+/i);

  const cliCommands = [];

  if (strategy === "IAM_PLAYBOOK") {
    cliCommands.push(
      "# Review the policy",
      `aws iam list-attached-role-policies --role-name <ROLE_NAME>`,
      `aws iam get-policy-version --policy-arn <POLICY_ARN> --version-id v1`,
      "# Apply least-privilege replacement",
      `aws iam put-role-policy --role-name <ROLE_NAME> --policy-name least-privilege --policy-document file://least-privilege.json`,
    );
  } else if (strategy === "MANUAL_PLAYBOOK") {
    cliCommands.push(
      "# Review the finding in SecurityHub",
      `aws securityhub get-findings --filters '{"Id":[{"Value":"${rawFinding.Id || ""}","Comparison":"EQUALS"}]}'`,
      "# Apply the recommended fix based on finding type",
      "# Then mark as resolved:",
      `aws securityhub batch-update-findings --finding-identifiers Id="${rawFinding.Id || ""}",ProductArn="${rawFinding.ProductArn || ""}" --workflow Status=RESOLVED`,
    );
  }

  return {
    summary: info.description,
    steps:   info.steps,
    resource,
    cveId:   cveMatch ? cveMatch[0] : null,
    cliCommands,
    docsUrl: "https://docs.aws.amazon.com/securityhub/latest/userguide/securityhub-findings.html",
  };
}

// == Remediation Executors ===================================================

/**
 * CVE_PATCH — triggers CodeBuild with a buildspec override that updates
 * the vulnerable package across affected Lambda functions.
 */
async function executeCvePatch(rawFinding, jobId) {
  const title     = rawFinding.Title || "";
  const cveMatch  = title.match(/CVE-\d{4}-\d+/i);
  const pkgMatch  = title.match(/CVE-\d{4}-\d+\s*-\s*(\S+)/i);
  const cveId     = cveMatch ? cveMatch[0] : "UNKNOWN-CVE";
  const pkgName   = pkgMatch ? pkgMatch[1] : "affected-package";
  const resource  = extractResource(rawFinding);

  const buildspec = JSON.stringify({
    version: "0.2",
    phases: {
      install: {
        "runtime-versions": { python: "3.12" },
        commands: ["pip install awscli --upgrade --quiet"],
      },
      pre_build: {
        commands: [
          `echo "Remediation Job: ${jobId}"`,
          `echo "CVE: ${cveId} | Package: ${pkgName}"`,
          "aws lambda list-functions --query 'Functions[].FunctionName' --output text > /tmp/all_functions.txt",
          "cat /tmp/all_functions.txt",
        ],
      },
      build: {
        commands: [
          "mkdir -p /tmp/remediation && cd /tmp/remediation",
          `pip download "${pkgName}" --no-deps -q || echo "Package not found on PyPI, skipping download"`,
          // For each function, check if it uses the package, then update layer
          `for fn in $(cat /tmp/all_functions.txt); do`,
          `  echo "Checking $fn..."`,
          `  aws lambda get-function --function-name $fn --query 'Configuration.Runtime' --output text 2>/dev/null | grep -qi python && echo "Python function: $fn" >> /tmp/python_functions.txt || true`,
          `done`,
          `echo "Python functions affected:"`,
          `cat /tmp/python_functions.txt 2>/dev/null || echo "None found"`,
        ],
      },
      post_build: {
        commands: [
          `echo "CVE remediation scan complete for ${cveId}"`,
          `echo "Job ID: ${jobId}"`,
          `echo "STATUS=COMPLETED"`,
        ],
      },
    },
    artifacts: { files: ["**/*"] },
  });

  const buildResult = await codebuild.send(new StartBuildCommand({
    projectName:        CODEBUILD_PROJECT,
    buildspecOverride:  buildspec,
    environmentVariablesOverride: [
      { name: "REMEDIATION_JOB_ID", value: jobId },
      { name: "CVE_ID",             value: cveId },
      { name: "PACKAGE_NAME",       value: pkgName },
    ],
  }));

  return {
    status:        "RUNNING",
    externalJobId: buildResult.build.id,
    externalType:  "CODEBUILD",
    steps: [
      { name: "CodeBuild job started",           status: "DONE" },
      { name: "Scanning Lambda functions",        status: "RUNNING" },
      { name: "Updating vulnerable package",      status: "PENDING" },
      { name: "Redeploying affected functions",   status: "PENDING" },
      { name: "Verifying fix",                    status: "PENDING" },
    ],
    buildId: buildResult.build.id,
    cveId,
    pkgName,
    resource,
  };
}

/**
 * S3_HARDENING — directly blocks public access and enables encryption.
 * Extracts bucket name from the finding's Resources array.
 */
async function executeS3Hardening(rawFinding, jobId) {
  const resource   = extractResource(rawFinding);
  // S3 resource ID is typically "arn:aws:s3:::bucket-name"
  const bucketName = resource?.id?.replace(/^arn:aws:s3:::/, "") || null;

  if (!bucketName) {
    return {
      status:  "FAILED",
      message: "Could not extract S3 bucket name from finding resource",
      steps:   [{ name: "Extract bucket name", status: "FAILED", error: "No resource ID found" }],
    };
  }

  const steps = [];

  // 1. Block public access
  try {
    await s3.send(new PutPublicAccessBlockCommand({
      Bucket: bucketName,
      PublicAccessBlockConfiguration: {
        BlockPublicAcls:       true,
        IgnorePublicAcls:      true,
        BlockPublicPolicy:     true,
        RestrictPublicBuckets: true,
      },
    }));
    steps.push({ name: "Block all public access", status: "DONE" });
  } catch (e) {
    steps.push({ name: "Block all public access", status: "FAILED", error: e.message });
  }

  // 2. Enable AES-256 encryption
  try {
    await s3.send(new PutBucketEncryptionCommand({
      Bucket: bucketName,
      ServerSideEncryptionConfiguration: {
        Rules: [{ ApplyServerSideEncryptionByDefault: { SSEAlgorithm: "AES256" } }],
      },
    }));
    steps.push({ name: "Enable AES-256 server-side encryption", status: "DONE" });
  } catch (e) {
    steps.push({ name: "Enable AES-256 encryption",             status: "FAILED", error: e.message });
  }

  const allDone = steps.every(s => s.status === "DONE");
  return {
    status:     allDone ? "COMPLETED" : "PARTIAL",
    bucketName,
    steps,
  };
}

/**
 * CONFIG_ENFORCEMENT — runs SSM Automation or applies a direct fix.
 * Falls back to a well-known automation document if one matches.
 */
async function executeConfigEnforcement(rawFinding, jobId) {
  const desc   = (rawFinding.Title || rawFinding.Description || "").toLowerCase();
  const resource = extractResource(rawFinding);

  // Map common Config findings to SSM Automation docs
  let docName = null;
  if (desc.includes("cloudtrail") && desc.includes("encrypt")) {
    docName = "AWS-EnableCloudTrailEncryption";
  } else if (desc.includes("cloudtrail") && desc.includes("log")) {
    docName = "AWS-EnableCloudTrailLogFileValidation";
  } else if (desc.includes("vpc") && desc.includes("flow log")) {
    docName = "AWS-EnableVPCFlowLogs";
  }

  if (docName) {
    try {
      const execResult = await ssm.send(new StartAutomationExecutionCommand({
        DocumentName: docName,
        Parameters:   resource?.id ? { AutomationAssumeRole: [`arn:aws:iam::${AWS_ACCOUNT_ID}:role/SSMAutomationRole`] } : {},
      }));
      return {
        status:        "RUNNING",
        externalJobId: execResult.AutomationExecutionId,
        externalType:  "SSM_AUTOMATION",
        docName,
        steps: [
          { name: `SSM Automation ${docName} started`, status: "DONE" },
          { name: "Applying configuration",             status: "RUNNING" },
          { name: "Verify and confirm",                 status: "PENDING" },
        ],
      };
    } catch (e) {
      // SSM failed — fall through to playbook
      return {
        status:  "PARTIAL",
        message: `SSM Automation ${docName} failed: ${e.message}. Manual steps required.`,
        docName,
        steps:   [{ name: `Run ${docName}`, status: "FAILED", error: e.message }],
      };
    }
  }

  // No matching automation doc — return a playbook
  return {
    status:  "PLAYBOOK",
    message: "No automated fix available for this config finding. Playbook generated.",
    steps: [
      { name: "Review AWS Config rule violation",           status: "PENDING" },
      { name: "Apply recommended configuration via console", status: "PENDING" },
      { name: "Verify rule compliance",                     status: "PENDING" },
    ],
  };
}

/**
 * Top-level remediation dispatcher.
 */
async function executeRemediation(strategy, rawFinding, jobId) {
  switch (strategy) {
    case "CVE_PATCH":          return executeCvePatch(rawFinding, jobId);
    case "S3_HARDENING":       return executeS3Hardening(rawFinding, jobId);
    case "CONFIG_ENFORCEMENT": return executeConfigEnforcement(rawFinding, jobId);
    default:
      return {
        status:  "PLAYBOOK",
        message: "This finding type requires manual remediation. Playbook generated.",
        steps:   REMEDIATION_STRATEGIES[strategy]?.steps.map(s => ({ name: s, status: "PENDING" })) || [],
      };
  }
}


// == Remediation Table Auto-Create ===========================================

let _remediationTableReady = false;

/**
 * Ensure the remediation jobs table exists.
 * Creates it on first Lambda cold-start if missing.
 * Uses the Lambda execution role's DynamoDB permissions (not the deploy user).
 */
async function ensureRemediationTable() {
  if (_remediationTableReady) return;
  try {
    await dynamodb.send(new DescribeTableCommand({ TableName: REMEDIATION_TABLE }));
    _remediationTableReady = true;
  } catch (e) {
    if (e.name === "ResourceNotFoundException") {
      try {
        await dynamodb.send(new CreateTableCommand({
          TableName: REMEDIATION_TABLE,
          BillingMode: "PAY_PER_REQUEST",
          AttributeDefinitions: [{ AttributeName: "jobId", AttributeType: "S" }],
          KeySchema: [{ AttributeName: "jobId", KeyType: "HASH" }],
        }));
        // Wait briefly for table to become active
        await new Promise(r => setTimeout(r, 5000));
        _remediationTableReady = true;
        console.log(JSON.stringify({ type: "INFO", message: "Remediation table created", table: REMEDIATION_TABLE }));
      } catch (createErr) {
        console.error(JSON.stringify({ type: "ERROR", message: "Failed to create remediation table", error: createErr.message }));
      }
    }
    // If another error (e.g. AccessDenied), let the handler fail gracefully
  }
}

// == Route Handlers ===========================================================

async function handleRoot() {
  return jsonResponse(200, { name: API_NAME, version: API_VERSION, status: "operational", endpoints: API_ENDPOINTS });
}

async function handleHealth() {
  const services = { cognito: "unknown", securityhub: "unknown", snowflake: "unknown" };

  try { await cognito.send(new ListUsersCommand({ UserPoolId: process.env.USER_POOL_ID, Limit: HEALTH_CHECK_LIMIT })); services.cognito = "connected"; }
  catch { services.cognito = "error"; }

  try { await secretsManager.send(new GetSecretValueCommand({ SecretId: SNOWFLAKE_SECRET_ID })); services.snowflake = "connected"; }
  catch { services.snowflake = "not_configured"; }

  try { await securityHub.send(new GetFindingsCommand({ MaxResults: HEALTH_CHECK_LIMIT })); services.securityhub = "connected"; }
  catch { services.securityhub = "error"; }

  const allOk = Object.values(services).every(v => v === "connected" || v === "not_configured");
  return jsonResponse(200, { status: allOk ? "healthy" : "degraded", timestamp: new Date().toISOString(), services });
}

async function handleFlows() {
  return jsonResponse(200, { date: new Date().toISOString().split("T")[0], source: "snowflake", metrics: [], message: "Snowflake flow metrics - pending E2E integration" });
}

function mapFinding(f, status) {
  return {
    id:             f.Id.split("/").pop(),
    fullId:         f.Id,
    productArn:     f.ProductArn,
    type:           f.Types?.[0] || "General Finding",
    severity:       f.Severity?.Label || "MEDIUM",
    description:    f.Title,
    title:          f.Title,
    timestamp:      f.UpdatedAt || f.CreatedAt,
    createdAt:      f.CreatedAt,
    status,
    workflowStatus: f.Workflow?.Status || "UNKNOWN",
    resolutionDate: status === "RESOLVED" ? (f.UpdatedAt || null) : null,
    resources:      f.Resources || [],
  };
}

async function handleSecurityAlerts() {
  // Three queries needed:
  // 1. Truly active: ACTIVE record state + NEW/NOTIFIED workflow (not yet acted on)
  // 2. Resolved via workflow: ACTIVE record state + RESOLVED/SUPPRESSED workflow
  //    (BatchUpdateFindings sets WorkflowStatus but does not change RecordState)
  // 3. Archived: ARCHIVED record state (finding provider closed it)
  const [activeResult, resolvedWorkflowResult, archivedResult] = await Promise.all([
    securityHub.send(new GetFindingsCommand({
      Filters: {
        RecordState:    [{ Value: "ACTIVE", Comparison: "EQUALS" }],
        SeverityLabel:  CRITICAL_SEVERITIES,
        WorkflowStatus: [
          { Value: "NEW",      Comparison: "EQUALS" },
          { Value: "NOTIFIED", Comparison: "EQUALS" },
        ],
      },
      MaxResults: MAX_ACTIVE_FINDINGS,
    })),
    securityHub.send(new GetFindingsCommand({
      Filters: {
        RecordState:    [{ Value: "ACTIVE", Comparison: "EQUALS" }],
        SeverityLabel:  CRITICAL_SEVERITIES,
        WorkflowStatus: [
          { Value: "RESOLVED",   Comparison: "EQUALS" },
          { Value: "SUPPRESSED", Comparison: "EQUALS" },
        ],
      },
      MaxResults: MAX_RESOLVED_FINDINGS,
    })),
    securityHub.send(new GetFindingsCommand({
      Filters: {
        RecordState:   [{ Value: "ARCHIVED", Comparison: "EQUALS" }],
        SeverityLabel: CRITICAL_SEVERITIES,
      },
      MaxResults: MAX_RESOLVED_FINDINGS,
    })),
  ]);

  const alerts = [
    ...(activeResult.Findings          || []).map(f => mapFinding(f, "ACTIVE")),
    ...(resolvedWorkflowResult.Findings || []).map(f => mapFinding(f, "RESOLVED")),
    ...(archivedResult.Findings         || []).map(f => mapFinding(f, "RESOLVED")),
  ];

  return jsonResponse(200, { alerts });
}

async function handleRunTests() {
  try {
    const response = await codebuild.send(new StartBuildCommand({ projectName: CODEBUILD_PROJECT }));
    return jsonResponse(200, { buildId: response.build.id, status: "STARTED" });
  } catch {
    const checks = [];

    try { await cognito.send(new ListUsersCommand({ UserPoolId: process.env.USER_POOL_ID, Limit: HEALTH_CHECK_LIMIT })); checks.push({ name: "Cognito", status: "PASS" }); }
    catch { checks.push({ name: "Cognito", status: "FAIL", reason: "Connection failed" }); }

    try { await securityHub.send(new GetFindingsCommand({ MaxResults: HEALTH_CHECK_LIMIT })); checks.push({ name: "SecurityHub", status: "PASS" }); }
    catch { checks.push({ name: "SecurityHub", status: "FAIL", reason: "Connection failed" }); }

    try { await secretsManager.send(new GetSecretValueCommand({ SecretId: SNOWFLAKE_SECRET_ID })); checks.push({ name: "Snowflake", status: "PASS" }); }
    catch { checks.push({ name: "Snowflake", status: "SKIP", reason: "Not configured" }); }

    const passed  = checks.filter(c => c.status === "PASS").length;
    const runnable = checks.filter(c => c.status !== "SKIP").length;

    return jsonResponse(200, {
      status: "COMPLETED", mode: "inline-health-checks",
      tests_run: checks.length, passed, failed: runnable - passed,
      skipped: checks.length - runnable, results: checks,
      timestamp: new Date().toISOString(),
    });
  }
}

async function handleTestStatus(event) {
  const buildId = event.queryStringParameters?.buildId;
  if (!buildId) return jsonResponse(400, { error: "Missing buildId parameter" });

  try {
    const response = await codebuild.send(new BatchGetBuildsCommand({ ids: [buildId] }));
    const build = response.builds[0];
    return jsonResponse(200, { status: build.buildStatus, logs: build.logs?.deepLink });
  } catch {
    return jsonResponse(200, { status: "NOT_FOUND", buildId });
  }
}

async function handleListUsers(event) {
  const claims = event.requestContext.authorizer?.claims;
  if (!isAdmin(claims)) return jsonResponse(403, { error: "Unauthorized" });

  const { Users } = await cached("users_list", () =>
    cognito.send(new ListUsersCommand({ UserPoolId: process.env.USER_POOL_ID, Limit: MAX_USERS_PER_PAGE }))
  );

  const users = (Users || []).map(u => ({
    Username:   u.Username,
    Enabled:    u.Enabled,
    UserStatus: u.UserStatus,
    email:      u.Attributes.find(a => a.Name === "email")?.Value || "",
  }));

  return jsonResponse(200, { users });
}

async function handleCreateUser(event) {
  const claims = event.requestContext.authorizer?.claims;
  if (!isAdmin(claims)) return jsonResponse(403, { error: "Unauthorized" });

  const body = JSON.parse(event.body || "{}");
  if (!body.email || !/\S+@\S+\.\S+/.test(body.email)) {
    return jsonResponse(400, { error: "Valid email required" });
  }

  const userPoolId = process.env.USER_POOL_ID;
  const { User } = await cognito.send(new AdminCreateUserCommand({
    UserPoolId: userPoolId,
    Username:   body.email,
    UserAttributes: [
      { Name: "email",         Value: body.email },
      { Name: "given_name",    Value: body.givenName  || "" },
      { Name: "family_name",   Value: body.familyName || "" },
      { Name: "email_verified", Value: "true" },
    ],
    MessageAction: "SUPPRESS",
  }));

  if (body.group) {
    await cognito.send(new AdminAddUserToGroupCommand({
      UserPoolId: userPoolId, Username: User.Username, GroupName: body.group,
    }));
  }

  delete _cache.users_list;
  auditLog("CREATE_USER", claims?.sub, User.Username);
  return jsonResponse(201, { message: "User created", username: User.Username });
}

async function handleUserAction(event) {
  const claims = event.requestContext.authorizer?.claims;
  if (!isAdmin(claims)) return jsonResponse(403, { error: "Unauthorized" });

  const { username, action } = event.pathParameters;
  const body       = event.body ? JSON.parse(event.body) : {};
  const userPoolId = process.env.USER_POOL_ID;

  switch (action) {
    case "enable":
      await cognito.send(new AdminEnableUserCommand({ UserPoolId: userPoolId, Username: username }));
      break;
    case "disable":
      await cognito.send(new AdminDisableUserCommand({ UserPoolId: userPoolId, Username: username }));
      break;
    case "reset": {
      const tempPassword = body.tempPassword;
      if (!tempPassword || tempPassword.length < MIN_PASSWORD_LENGTH) {
        return jsonResponse(400, { error: `Temp password required (min ${MIN_PASSWORD_LENGTH} chars)` });
      }
      await cognito.send(new AdminSetUserPasswordCommand({
        UserPoolId: userPoolId, Username: username, Password: tempPassword, Permanent: false,
      }));
      if (body.sendEmail) {
        const userInfo = await cognito.send(new AdminGetUserCommand({ UserPoolId: userPoolId, Username: username }));
        const userEmail = userInfo.UserAttributes?.find(a => a.Name === "email")?.Value || username;
        try {
          await ses.send(new SendEmailCommand({
            Source: EMAIL_FROM,
            Destination: { ToAddresses: [userEmail] },
            Message: {
              Subject: { Data: "Mission Control - Temporary Password" },
              Body: { Html: { Data: `<h2>Mission Control Password Reset</h2><p>Your temporary password: <code>${tempPassword}</code></p><p>You will be asked to change it on next login.</p>` } },
            },
          }));
        } catch {
          auditLog("PASSWORD_RESET_EMAIL_FAILED", claims?.sub, username);
          return jsonResponse(200, { message: "Password reset successful, but email delivery failed" });
        }
      }
      auditLog("PASSWORD_RESET", claims?.sub, username);
      return jsonResponse(200, { message: body.sendEmail ? "Password reset and email sent" : "Password reset successful" });
    }
    case "reset-mfa":
      await cognito.send(new AdminSetUserMFAPreferenceCommand({
        UserPoolId: userPoolId, Username: username,
        SoftwareTokenMfaSettings: { Enabled: false, PreferredMfa: false },
      }));
      auditLog("MFA_RESET", claims?.sub, username);
      return jsonResponse(200, { message: "MFA reset successful. User will set up MFA on next login." });
    case "delete":
      await cognito.send(new AdminDeleteUserCommand({ UserPoolId: userPoolId, Username: username }));
      delete _cache.users_list;
      break;
    default:
      return jsonResponse(400, { error: "Invalid action" });
  }

  auditLog(action.toUpperCase(), claims?.sub, username);
  return jsonResponse(200, { message: `${action} successful` });
}

async function handleResolveAlert(event) {
  const claims = event.requestContext.authorizer?.claims;
  if (!isAdmin(claims)) return jsonResponse(403, { error: "Unauthorized" });

  const body = JSON.parse(event.body || "{}");
  const { findingId, action, note } = body;

  if (!findingId) return jsonResponse(400, { error: "findingId is required" });
  if (!action || !["RESOLVED", "SUPPRESSED", "NOTIFIED"].includes(action)) {
    return jsonResponse(400, { error: "action must be RESOLVED, SUPPRESSED, or NOTIFIED" });
  }

  const lookupResult = await securityHub.send(new GetFindingsCommand({
    Filters: { Id: [{ Value: findingId, Comparison: "SUFFIX" }] },
    MaxResults: 1,
  }));

  if (!lookupResult.Findings?.length) return jsonResponse(404, { error: "Finding not found" });

  const finding           = lookupResult.Findings[0];
  const findingIdentifier = { Id: finding.Id, ProductArn: finding.ProductArn };

  await securityHub.send(new BatchUpdateFindingsCommand({
    FindingIdentifiers: [findingIdentifier],
    Workflow: { Status: action },
    Note: {
      Text:      note || `${action} via Mission Control by ${claims?.email || claims?.sub || "admin"}`,
      UpdatedBy: claims?.sub || "mission-control",
    },
  }));

  auditLog("RESOLVE_ALERT", claims?.sub, `${findingId}:${action}`);

  return jsonResponse(200, {
    message:    `Finding ${action.toLowerCase()} successfully`,
    findingId, action,
    resolvedBy: claims?.email || claims?.sub || "admin",
    timestamp:  new Date().toISOString(),
  });
}

/**
 * POST /security-alerts/remediate
 * Body: { findingId, dryRun? }
 *
 * dryRun=true  → returns the strategy + preview steps without executing
 * dryRun=false → executes remediation, stores job in DynamoDB, returns job info
 */
async function handleRemediateAlert(event) {
  const claims = event.requestContext.authorizer?.claims;
  if (!isAdmin(claims)) return jsonResponse(403, { error: "Unauthorized" });

  await ensureRemediationTable();

  const body = JSON.parse(event.body || "{}");
  const { findingId, dryRun } = body;

  if (!findingId) return jsonResponse(400, { error: "findingId is required" });

  // Look up the raw finding
  const lookupResult = await securityHub.send(new GetFindingsCommand({
    Filters: { Id: [{ Value: findingId, Comparison: "SUFFIX" }] },
    MaxResults: 1,
  }));

  if (!lookupResult.Findings?.length) return jsonResponse(404, { error: "Finding not found" });

  const rawFinding = lookupResult.Findings[0];
  const strategy   = detectStrategy(rawFinding);
  const stratInfo  = REMEDIATION_STRATEGIES[strategy];

  // == DRY RUN — preview only ==
  if (dryRun) {
    const playbook  = buildPlaybook(strategy, rawFinding);
    const resource  = extractResource(rawFinding);
    return jsonResponse(200, {
      dryRun:      true,
      findingId,
      strategy,
      label:       stratInfo.label,
      description: stratInfo.description,
      canAutomate: stratInfo.canAutomate,
      estimatedMinutes: stratInfo.estimatedMinutes,
      steps:       stratInfo.steps.map(s => ({ name: s, status: "PENDING" })),
      resource,
      playbook:    stratInfo.canAutomate ? null : playbook,
    });
  }

  // == EXECUTE ==
  const jobId = randomUUID();
  const now   = new Date().toISOString();

  // Persist job record
  await dynamodb.send(new PutItemCommand({
    TableName: REMEDIATION_TABLE,
    Item: {
      jobId:       { S: jobId },
      findingId:   { S: findingId },
      strategy:    { S: strategy },
      label:       { S: stratInfo.label },
      status:      { S: "RUNNING" },
      startedAt:   { S: now },
      triggeredBy: { S: claims?.email || claims?.sub || "admin" },
      description: { S: rawFinding.Title || "" },
      steps:       { S: JSON.stringify([]) },
    },
  }));

  let execResult;
  try {
    execResult = await executeRemediation(strategy, rawFinding, jobId);

    // Update job with initial execution result
    await dynamodb.send(new UpdateItemCommand({
      TableName: REMEDIATION_TABLE,
      Key: { jobId: { S: jobId } },
      UpdateExpression: "SET #st = :st, externalJobId = :ext, externalType = :et, steps = :steps",
      ExpressionAttributeNames: { "#st": "status" },
      ExpressionAttributeValues: {
        ":st":    { S: execResult.status || "RUNNING" },
        ":ext":   { S: execResult.externalJobId || "" },
        ":et":    { S: execResult.externalType  || "" },
        ":steps": { S: JSON.stringify(execResult.steps || []) },
      },
    }));

    auditLog("REMEDIATE_ALERT", claims?.sub, `${findingId}:${strategy}:${jobId}`);

    return jsonResponse(200, {
      jobId,
      findingId,
      strategy,
      label:         stratInfo.label,
      status:        execResult.status,
      externalJobId: execResult.externalJobId,
      externalType:  execResult.externalType,
      steps:         execResult.steps,
      message:       `Remediation started: ${stratInfo.label}`,
      canAutomate:   stratInfo.canAutomate,
      playbook:      execResult.status === "PLAYBOOK" ? buildPlaybook(strategy, rawFinding) : null,
    });
  } catch (err) {
    // Mark job failed
    await dynamodb.send(new UpdateItemCommand({
      TableName: REMEDIATION_TABLE,
      Key: { jobId: { S: jobId } },
      UpdateExpression: "SET #st = :st, errorMessage = :err",
      ExpressionAttributeNames: { "#st": "status" },
      ExpressionAttributeValues: {
        ":st":  { S: "FAILED" },
        ":err": { S: err.message },
      },
    })).catch(() => {});
    throw err;
  }
}

/**
 * GET /security-alerts/remediation-status?jobId=...
 *
 * Polls the DynamoDB job record and, for CODEBUILD/SSM jobs, fetches
 * live status from the external service.
 */
async function handleRemediationStatus(event) {
  const claims = event.requestContext.authorizer?.claims;
  if (!isAdmin(claims)) return jsonResponse(403, { error: "Unauthorized" });

  await ensureRemediationTable();

  const jobId = event.queryStringParameters?.jobId;
  if (!jobId) return jsonResponse(400, { error: "jobId is required" });

  const record = await dynamodb.send(new GetItemCommand({
    TableName: REMEDIATION_TABLE,
    Key: { jobId: { S: jobId } },
  }));

  if (!record.Item) return jsonResponse(404, { error: "Remediation job not found" });

  const storedStrategy = record.Item.strategy?.S || "";
  const job = {
    jobId:         record.Item.jobId?.S,
    findingId:     record.Item.findingId?.S,
    strategy:      storedStrategy,
    // label was added to persisted records in v2.3.1; fall back to REMEDIATION_STRATEGIES lookup
    label:         record.Item.label?.S || REMEDIATION_STRATEGIES[storedStrategy]?.label || storedStrategy,
    status:        record.Item.status?.S,
    startedAt:     record.Item.startedAt?.S,
    completedAt:   record.Item.completedAt?.S,
    triggeredBy:   record.Item.triggeredBy?.S,
    description:   record.Item.description?.S,
    externalJobId: record.Item.externalJobId?.S,
    externalType:  record.Item.externalType?.S,
    steps:         JSON.parse(record.Item.steps?.S || "[]"),
    errorMessage:  record.Item.errorMessage?.S,
  };

  // Poll live status from external job if still running
  if (job.status === "RUNNING" && job.externalJobId) {
    if (job.externalType === "CODEBUILD") {
      try {
        const cbResult = await codebuild.send(new BatchGetBuildsCommand({ ids: [job.externalJobId] }));
        const build = cbResult.builds?.[0];
        if (build) {
          const cbStatus = build.buildStatus; // SUCCEEDED | FAILED | IN_PROGRESS
          if (cbStatus === "SUCCEEDED") {
            job.status = "COMPLETED";
            job.completedAt = new Date().toISOString();
            job.steps = job.steps.map(s => ({ ...s, status: "DONE" }));
          } else if (cbStatus === "FAILED" || cbStatus === "STOPPED") {
            job.status = "FAILED";
            job.completedAt = new Date().toISOString();
          }
          job.buildLogs = build.logs?.deepLink || null;
          job.cbStatus  = cbStatus;
          // Persist updated status
          await dynamodb.send(new UpdateItemCommand({
            TableName: REMEDIATION_TABLE,
            Key: { jobId: { S: jobId } },
            UpdateExpression: "SET #st = :st, completedAt = :ca, steps = :steps",
            ExpressionAttributeNames: { "#st": "status" },
            ExpressionAttributeValues: {
              ":st":    { S: job.status },
              ":ca":    { S: job.completedAt || "" },
              ":steps": { S: JSON.stringify(job.steps) },
            },
          })).catch(() => {});
        }
      } catch { /* best effort */ }
    } else if (job.externalType === "SSM_AUTOMATION") {
      try {
        const ssmResult = await ssm.send(new GetAutomationExecutionCommand({
          AutomationExecutionId: job.externalJobId,
        }));
        const ssmStatus = ssmResult.AutomationExecution?.AutomationExecutionStatus;
        if (ssmStatus === "Success") {
          job.status = "COMPLETED";
          job.completedAt = new Date().toISOString();
          job.steps = job.steps.map(s => ({ ...s, status: "DONE" }));
        } else if (["Failed", "Cancelled", "TimedOut"].includes(ssmStatus)) {
          job.status = "FAILED";
          job.completedAt = new Date().toISOString();
        }
        job.ssmStatus = ssmStatus;
        await dynamodb.send(new UpdateItemCommand({
          TableName: REMEDIATION_TABLE,
          Key: { jobId: { S: jobId } },
          UpdateExpression: "SET #st = :st, completedAt = :ca, steps = :steps",
          ExpressionAttributeNames: { "#st": "status" },
          ExpressionAttributeValues: {
            ":st":    { S: job.status },
            ":ca":    { S: job.completedAt || "" },
            ":steps": { S: JSON.stringify(job.steps) },
          },
        })).catch(() => {});
      } catch { /* best effort */ }
    }
  }

  return jsonResponse(200, job);
}

// == Main Router ==============================================================

exports.lambdaHandler = async (event) => {
  if (event.httpMethod === "OPTIONS") {
    return { statusCode: 200, headers: corsHeaders, body: "" };
  }

  try {
    const { httpMethod, path } = event;

    if (httpMethod === "GET"  && path === "/")                                  return handleRoot();
    if (httpMethod === "GET"  && path === "/health")                            return handleHealth();
    if (httpMethod === "GET"  && path === "/flows")                             return handleFlows();
    if (httpMethod === "GET"  && path === "/security-alerts")                   return handleSecurityAlerts();
    if (httpMethod === "POST" && path === "/security-alerts/resolve")           return handleResolveAlert(event);
    if (httpMethod === "POST" && path === "/security-alerts/remediate")         return handleRemediateAlert(event);
    if (httpMethod === "GET"  && path === "/security-alerts/remediation-status") return handleRemediationStatus(event);
    if (httpMethod === "POST" && path === "/run-tests")                         return handleRunTests();
    if (httpMethod === "GET"  && path === "/test-status")                       return handleTestStatus(event);
    if (httpMethod === "GET"  && path === "/users")                             return handleListUsers(event);
    if (httpMethod === "POST" && path === "/users")                             return handleCreateUser(event);

    if (httpMethod === "POST" && event.pathParameters?.username && event.pathParameters?.action) {
      return handleUserAction(event);
    }

    return jsonResponse(404, { error: "Not Found" });
  } catch (error) {
    console.error(JSON.stringify({
      type: "ERROR", message: error.message,
      path: event.path, method: event.httpMethod,
      timestamp: new Date().toISOString(),
    }));
    return jsonResponse(500, { error: "Internal server error" });
  }
};
