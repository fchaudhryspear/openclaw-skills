"use strict";

/**
 * Credologi Mission Control API — Lambda Handler
 * 
 * Routes:
 *   GET  /              -> API info (public)
 *   GET  /health        -> Service health check (public)
 *   GET  /flows         -> Data lake flow metrics
 *   GET  /security-alerts -> SecurityHub findings
 *   POST /run-tests     -> Trigger CodeBuild or inline health checks
 *   GET  /test-status   -> Check CodeBuild status
 *   GET  /users         -> List Cognito users (admin only)
 *   POST /users         -> Create user (admin only)
 *   POST /users/{username}/{action} -> User actions (admin only)
 * 
 * @module MissionControlAPI
 * @version 2.2.0
 */

const { SecurityHubClient, GetFindingsCommand, BatchUpdateFindingsCommand } = require("@aws-sdk/client-securityhub");
const { CognitoIdentityProviderClient, ListUsersCommand, AdminEnableUserCommand, AdminDisableUserCommand, AdminResetUserPasswordCommand, AdminSetUserPasswordCommand, AdminCreateUserCommand, AdminAddUserToGroupCommand, AdminDeleteUserCommand, AdminGetUserCommand, AdminSetUserMFAPreferenceCommand } = require("@aws-sdk/client-cognito-identity-provider");
const { SESClient, SendEmailCommand } = require("@aws-sdk/client-ses");
const { CodeBuildClient, StartBuildCommand, BatchGetBuildsCommand } = require("@aws-sdk/client-codebuild");
const { SecretsManagerClient, GetSecretValueCommand } = require("@aws-sdk/client-secrets-manager");

// == Constants ================================================================

const AWS_REGION = "us-east-1";
const API_VERSION = "2.2.0";
const API_NAME = "Credologi Mission Control API";

/** Max active SecurityHub findings to fetch */
const MAX_ACTIVE_FINDINGS = 50;
/** Max resolved findings to fetch */
const MAX_RESOLVED_FINDINGS = 25;
/** Cognito user list page size */
const MAX_USERS_PER_PAGE = 60;
/** Minimum temp password length */
const MIN_PASSWORD_LENGTH = 8;
/** Minimal query for health checks */
const HEALTH_CHECK_LIMIT = 1;
/** Cache TTL in milliseconds (5 min) */
const CACHE_TTL_MS = 5 * 60 * 1000;

const SNOWFLAKE_SECRET_ID = "snowflake-lambda-key";
const EMAIL_FROM = "noreply@credologi.com";
const CODEBUILD_PROJECT = process.env.CODEBUILD_PROJECT_NAME || "credologi-test-suite";
const CORS_ORIGIN = process.env.CORS_ORIGIN || "https://missioncontrol.credologi.com";

const CRITICAL_SEVERITIES = [
  { Value: "CRITICAL", Comparison: "EQUALS" },
  { Value: "HIGH", Comparison: "EQUALS" },
];

const API_ENDPOINTS = ["/health", "/flows", "/security-alerts", "/security-alerts/resolve", "/users", "/run-tests", "/test-status"];

// == SDK Clients ==============================================================

const securityHub = new SecurityHubClient({ region: AWS_REGION });
const cognito = new CognitoIdentityProviderClient({ region: AWS_REGION });
const codebuild = new CodeBuildClient({ region: AWS_REGION });
const secretsManager = new SecretsManagerClient({ region: AWS_REGION });
const ses = new SESClient({ region: AWS_REGION });

// == In-memory Cache (Lambda warm-start optimization) =========================

const _cache = {};

/**
 * Get or set cached value with TTL.
 * @param {string} key - Cache key
 * @param {Function} fetcher - Async function to call on miss
 * @returns {Promise<any>}
 */
async function cached(key, fetcher) {
  const now = Date.now();
  if (_cache[key] && now - _cache[key].ts < CACHE_TTL_MS) {
    return _cache[key].data;
  }
  const data = await fetcher();
  _cache[key] = { data, ts: now };
  return data;
}

// == CORS Headers =============================================================

const corsHeaders = {
  "Access-Control-Allow-Origin": CORS_ORIGIN,
  "Access-Control-Allow-Headers": "Content-Type, Authorization",
  "Access-Control-Allow-Methods": "OPTIONS,POST,GET",
};

// == Helpers ==================================================================

/** Build a standard JSON response. */
function jsonResponse(statusCode, body) {
  return { statusCode, headers: corsHeaders, body: JSON.stringify(body) };
}

/** Check if caller has admin role. */
function isAdmin(claims) {
  const groups = claims?.["cognito:groups"] || [];
  return groups.includes("GlobalAdmins") || groups.includes("Admins");
}

/**
 * Structured audit log (no sensitive data ever).
 * @param {string} action
 * @param {string} actor - Admin sub/username
 * @param {string} target - Target resource
 */
function auditLog(action, actor, target) {
  console.log(JSON.stringify({
    type: "AUDIT",
    action,
    actor: actor || "unknown",
    target,
    timestamp: new Date().toISOString(),
  }));
}

// == Route Handlers ===========================================================

/** GET / */
async function handleRoot() {
  return jsonResponse(200, {
    name: API_NAME,
    version: API_VERSION,
    status: "operational",
    endpoints: API_ENDPOINTS,
  });
}

/** GET /health */
async function handleHealth() {
  const services = { cognito: "unknown", securityhub: "unknown", snowflake: "unknown" };

  try {
    await cognito.send(new ListUsersCommand({ UserPoolId: process.env.USER_POOL_ID, Limit: HEALTH_CHECK_LIMIT }));
    services.cognito = "connected";
  } catch { services.cognito = "error"; }

  try {
    await secretsManager.send(new GetSecretValueCommand({ SecretId: SNOWFLAKE_SECRET_ID }));
    services.snowflake = "connected";
  } catch { services.snowflake = "not_configured"; }

  try {
    await securityHub.send(new GetFindingsCommand({ MaxResults: HEALTH_CHECK_LIMIT }));
    services.securityhub = "connected";
  } catch { services.securityhub = "error"; }

  const allOk = Object.values(services).every(v => v === "connected" || v === "not_configured");
  return jsonResponse(200, { status: allOk ? "healthy" : "degraded", timestamp: new Date().toISOString(), services });
}

/** GET /flows */
async function handleFlows() {
  return jsonResponse(200, {
    date: new Date().toISOString().split("T")[0],
    source: "snowflake",
    metrics: [],
    message: "Snowflake flow metrics - pending E2E integration",
  });
}

/** Map a SecurityHub finding to our API shape. */
function mapFinding(f, status) {
  return {
    id: f.Id.split("/").pop(),
    type: f.Types?.[0] || "General Finding",
    severity: f.Severity?.Label || "MEDIUM",
    description: f.Title,
    timestamp: f.UpdatedAt || f.CreatedAt,
    createdAt: f.CreatedAt,
    status,
    workflowStatus: f.Workflow?.Status || "UNKNOWN",
    resolutionDate: status === "RESOLVED" ? (f.UpdatedAt || null) : null,
  };
}

/** GET /security-alerts */
async function handleSecurityAlerts() {
  const [activeResult, resolvedResult] = await Promise.all([
    securityHub.send(new GetFindingsCommand({
      Filters: { RecordState: [{ Value: "ACTIVE", Comparison: "EQUALS" }], SeverityLabel: CRITICAL_SEVERITIES },
      MaxResults: MAX_ACTIVE_FINDINGS,
    })),
    securityHub.send(new GetFindingsCommand({
      Filters: { RecordState: [{ Value: "ARCHIVED", Comparison: "EQUALS" }], SeverityLabel: CRITICAL_SEVERITIES },
      MaxResults: MAX_RESOLVED_FINDINGS,
    })),
  ]);

  const alerts = [
    ...(activeResult.Findings || []).map(f => mapFinding(f, "ACTIVE")),
    ...(resolvedResult.Findings || []).map(f => mapFinding(f, "RESOLVED")),
  ];

  return jsonResponse(200, { alerts });
}

/** POST /run-tests */
async function handleRunTests() {
  try {
    const response = await codebuild.send(new StartBuildCommand({ projectName: CODEBUILD_PROJECT }));
    return jsonResponse(200, { buildId: response.build.id, status: "STARTED" });
  } catch {
    // CodeBuild not configured - run inline health checks
    const checks = [];

    try {
      await cognito.send(new ListUsersCommand({ UserPoolId: process.env.USER_POOL_ID, Limit: HEALTH_CHECK_LIMIT }));
      checks.push({ name: "Cognito", status: "PASS" });
    } catch { checks.push({ name: "Cognito", status: "FAIL", reason: "Connection failed" }); }

    try {
      await securityHub.send(new GetFindingsCommand({ MaxResults: HEALTH_CHECK_LIMIT }));
      checks.push({ name: "SecurityHub", status: "PASS" });
    } catch { checks.push({ name: "SecurityHub", status: "FAIL", reason: "Connection failed" }); }

    try {
      await secretsManager.send(new GetSecretValueCommand({ SecretId: SNOWFLAKE_SECRET_ID }));
      checks.push({ name: "Snowflake", status: "PASS" });
    } catch { checks.push({ name: "Snowflake", status: "SKIP", reason: "Not configured" }); }

    const passed = checks.filter(c => c.status === "PASS").length;
    const runnable = checks.filter(c => c.status !== "SKIP").length;

    return jsonResponse(200, {
      status: "COMPLETED",
      mode: "inline-health-checks",
      tests_run: checks.length,
      passed,
      failed: runnable - passed,
      skipped: checks.length - runnable,
      results: checks,
      timestamp: new Date().toISOString(),
    });
  }
}

/** GET /test-status */
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

/** GET /users (admin only) */
async function handleListUsers(event) {
  const claims = event.requestContext.authorizer?.claims;
  if (!isAdmin(claims)) return jsonResponse(403, { error: "Unauthorized" });

  const { Users } = await cached("users_list", () =>
    cognito.send(new ListUsersCommand({ UserPoolId: process.env.USER_POOL_ID, Limit: MAX_USERS_PER_PAGE }))
  );

  const users = (Users || []).map(u => ({
    Username: u.Username,
    Enabled: u.Enabled,
    UserStatus: u.UserStatus,
    email: u.Attributes.find(a => a.Name === "email")?.Value || "",
  }));

  return jsonResponse(200, { users });
}

/** POST /users (admin only) */
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
    Username: body.email,
    UserAttributes: [
      { Name: "email", Value: body.email },
      { Name: "given_name", Value: body.givenName || "" },
      { Name: "family_name", Value: body.familyName || "" },
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

/** POST /users/{username}/{action} (admin only) */
async function handleUserAction(event) {
  const claims = event.requestContext.authorizer?.claims;
  if (!isAdmin(claims)) return jsonResponse(403, { error: "Unauthorized" });

  const { username, action } = event.pathParameters;
  const body = event.body ? JSON.parse(event.body) : {};
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


/** POST /security-alerts/resolve — Resolve/remediate a SecurityHub finding */
async function handleResolveAlert(event) {
  const claims = event.requestContext.authorizer?.claims;
  if (!isAdmin(claims)) return jsonResponse(403, { error: "Unauthorized" });

  const body = JSON.parse(event.body || "{}");
  const { findingId, action, note } = body;

  if (!findingId) return jsonResponse(400, { error: "findingId is required" });
  if (!action || !["RESOLVED", "SUPPRESSED", "NOTIFIED"].includes(action)) {
    return jsonResponse(400, { error: "action must be RESOLVED, SUPPRESSED, or NOTIFIED" });
  }

  // SecurityHub requires the full FindingIdentifier (Id + ProductArn)
  // findingId from our API is the short ID; we need to look up the full finding first
  const lookupResult = await securityHub.send(new GetFindingsCommand({
    Filters: { Id: [{ Value: findingId, Comparison: "SUFFIX" }] },
    MaxResults: 1,
  }));

  if (!lookupResult.Findings?.length) {
    return jsonResponse(404, { error: "Finding not found" });
  }

  const finding = lookupResult.Findings[0];
  const findingIdentifier = { Id: finding.Id, ProductArn: finding.ProductArn };

  const updateParams = {
    FindingIdentifiers: [findingIdentifier],
    Workflow: { Status: action },
    Note: {
      Text: note || `${action} via Mission Control by ${claims?.email || claims?.sub || "admin"}`,
      UpdatedBy: claims?.sub || "mission-control",
    },
  };

  await securityHub.send(new BatchUpdateFindingsCommand(updateParams));

  auditLog("RESOLVE_ALERT", claims?.sub, `${findingId}:${action}`);

  return jsonResponse(200, {
    message: `Finding ${action.toLowerCase()} successfully`,
    findingId,
    action,
    resolvedBy: claims?.email || claims?.sub || "admin",
    timestamp: new Date().toISOString(),
  });
}

// == Main Router ==============================================================

exports.lambdaHandler = async (event) => {
  if (event.httpMethod === "OPTIONS") {
    return { statusCode: 200, headers: corsHeaders, body: "" };
  }

  try {
    const { httpMethod, path } = event;

    if (httpMethod === "GET" && path === "/") return handleRoot();
    if (httpMethod === "GET" && path === "/health") return handleHealth();
    if (httpMethod === "GET" && path === "/flows") return handleFlows();
    if (httpMethod === "GET" && path === "/security-alerts") return handleSecurityAlerts();
    if (httpMethod === "POST" && path === "/security-alerts/resolve") return handleResolveAlert(event);
    if (httpMethod === "POST" && path === "/run-tests") return handleRunTests();
    if (httpMethod === "GET" && path === "/test-status") return handleTestStatus(event);
    if (httpMethod === "GET" && path === "/users") return handleListUsers(event);
    if (httpMethod === "POST" && path === "/users") return handleCreateUser(event);

    if (httpMethod === "POST" && event.pathParameters?.username && event.pathParameters?.action) {
      return handleUserAction(event);
    }

    return jsonResponse(404, { error: "Not Found" });
  } catch (error) {
    console.error(JSON.stringify({ type: "ERROR", message: error.message, path: event.path, method: event.httpMethod, timestamp: new Date().toISOString() }));
    return jsonResponse(500, { error: "Internal server error" });
  }
};
