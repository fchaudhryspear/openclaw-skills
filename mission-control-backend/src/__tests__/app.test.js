'use strict';

// ── Mock variables (must start with 'mock' for Jest hoisting) ────────────────
const mockSecretsSend = jest.fn();
const mockSecurityHubSend = jest.fn();
const mockCognitoSend = jest.fn();
const mockCodeBuildSend = jest.fn();
const mockSesSend = jest.fn();

// ── Mock AWS SDK modules ─────────────────────────────────────────────────────
jest.mock('@aws-sdk/client-secrets-manager', () => ({
  SecretsManagerClient: jest.fn().mockImplementation(() => ({ send: mockSecretsSend })),
  GetSecretValueCommand: jest.fn().mockImplementation((input) => ({ ...input })),
}));

jest.mock('@aws-sdk/client-securityhub', () => ({
  SecurityHubClient: jest.fn().mockImplementation(() => ({ send: mockSecurityHubSend })),
  GetFindingsCommand: jest.fn().mockImplementation((input) => ({ ...input })),
}));

jest.mock('@aws-sdk/client-cognito-identity-provider', () => ({
  CognitoIdentityProviderClient: jest.fn().mockImplementation(() => ({ send: mockCognitoSend })),
  ListUsersCommand: jest.fn().mockImplementation((input) => ({ ...input })),
  AdminEnableUserCommand: jest.fn().mockImplementation((input) => ({ ...input })),
  AdminDisableUserCommand: jest.fn().mockImplementation((input) => ({ ...input })),
  AdminResetUserPasswordCommand: jest.fn().mockImplementation((input) => ({ ...input })),
  AdminSetUserPasswordCommand: jest.fn().mockImplementation((input) => ({ ...input })),
  AdminCreateUserCommand: jest.fn().mockImplementation((input) => ({ ...input })),
  AdminAddUserToGroupCommand: jest.fn().mockImplementation((input) => ({ ...input })),
  AdminDeleteUserCommand: jest.fn().mockImplementation((input) => ({ ...input })),
  AdminGetUserCommand: jest.fn().mockImplementation((input) => ({ ...input })),
}));

jest.mock('@aws-sdk/client-codebuild', () => ({
  CodeBuildClient: jest.fn().mockImplementation(() => ({ send: mockCodeBuildSend })),
  StartBuildCommand: jest.fn().mockImplementation((input) => ({ ...input })),
  BatchGetBuildsCommand: jest.fn().mockImplementation((input) => ({ ...input })),
}));

jest.mock('@aws-sdk/client-ses', () => ({
  SESClient: jest.fn().mockImplementation(() => ({ send: mockSesSend })),
  SendEmailCommand: jest.fn().mockImplementation((input) => ({ ...input })),
}));

// ── Load handler AFTER mocks ─────────────────────────────────────────────────
const { lambdaHandler } = require('../app');

// ── Test helpers ─────────────────────────────────────────────────────────────
const makeEvent = (overrides = {}) => ({
  httpMethod: 'GET',
  path: '/',
  pathParameters: null,
  queryStringParameters: null,
  body: null,
  requestContext: {
    authorizer: { claims: {} },
  },
  ...overrides,
});

const adminClaims = { 'cognito:groups': ['GlobalAdmins'], sub: 'admin-sub-123' };
const adminsClaims = { 'cognito:groups': ['Admins'], sub: 'admins-sub-456' };
const nonAdminClaims = { 'cognito:groups': ['Users'], sub: 'user-sub-789' };

beforeEach(() => {
  mockSecretsSend.mockReset();
  mockSecurityHubSend.mockReset();
  mockCognitoSend.mockReset();
  mockCodeBuildSend.mockReset();
  mockSesSend.mockReset();
});

// ── CORS Preflight ────────────────────────────────────────────────────────────
describe('OPTIONS / CORS Preflight', () => {
  test('returns 200 with all CORS headers and empty body', async () => {
    const res = await lambdaHandler(makeEvent({ httpMethod: 'OPTIONS' }), {});
    expect(res.statusCode).toBe(200);
    expect(res.body).toBe('');
    expect(res.headers['Access-Control-Allow-Origin']).toBe('*');
    expect(res.headers['Access-Control-Allow-Headers']).toBe('Content-Type, Authorization');
    expect(res.headers['Access-Control-Allow-Methods']).toBe('OPTIONS,POST,GET');
  });
});

// ── GET /health ───────────────────────────────────────────────────────────────
describe('GET /health', () => {
  test('returns 200 with healthy status when all services connect', async () => {
    mockCognitoSend.mockResolvedValueOnce({ Users: [] });
    mockSecretsSend.mockResolvedValueOnce({ SecretString: 'my-private-key' });
    mockSecurityHubSend.mockResolvedValueOnce({ Findings: [] });

    const res = await lambdaHandler(makeEvent({ path: '/health' }), {});

    expect(res.statusCode).toBe(200);
    const body = JSON.parse(res.body);
    expect(body.status).toBe('healthy');
    expect(body.services.cognito).toBe('connected');
    expect(body.services.snowflake).toBe('connected');
    expect(body.services.securityhub).toBe('connected');
    expect(body.services.dynamodb).toBeUndefined();
    expect(res.headers['Access-Control-Allow-Origin']).toBeDefined();
  });

  test('returns degraded when a service fails', async () => {
    mockCognitoSend.mockRejectedValueOnce(new Error('error'));
    mockSecretsSend.mockResolvedValueOnce({ SecretString: 'key' });
    mockSecurityHubSend.mockResolvedValueOnce({ Findings: [] });

    const res = await lambdaHandler(makeEvent({ path: '/health' }), {});

    expect(res.statusCode).toBe(200);
    const body = JSON.parse(res.body);
    expect(body.status).toBe('degraded');
    expect(body.services.cognito).toBe('error');
  });
});

// ── GET /flows (Snowflake-first, DynamoDB removed) ────────────────────────────
describe('GET /flows', () => {
  test('returns 200 with today\'s date and snowflake source', async () => {
    const today = new Date().toISOString().split('T')[0];

    const res = await lambdaHandler(makeEvent({ path: '/flows' }), {});

    expect(res.statusCode).toBe(200);
    const body = JSON.parse(res.body);
    expect(body.date).toBe(today);
    expect(body.source).toBe('snowflake');
    expect(body.metrics).toEqual([]);
  });
});

// ── GET /security-alerts ──────────────────────────────────────────────────────
describe('GET /security-alerts', () => {
  test('returns 200 with mapped alert objects (active + resolved)', async () => {
    const activeFindings = [
      {
        Id: 'arn:aws:securityhub:us-east-1:123456789:finding/abc123',
        Types: ['Software and Configuration Checks/Vulnerabilities/CVE'],
        Severity: { Label: 'CRITICAL' },
        Title: 'Critical CVE Found',
        UpdatedAt: '2024-03-01T10:00:00Z',
        CreatedAt: '2024-03-01T09:00:00Z',
        Workflow: { Status: 'NEW' },
      },
    ];
    const resolvedFindings = [
      {
        Id: 'arn:aws:securityhub:us-east-1:123456789:finding/def456',
        Types: ['TTPs/Initial Access/Exploit Public-Facing Application'],
        Severity: { Label: 'HIGH' },
        Title: 'Exploit Detected',
        UpdatedAt: '2024-03-01T11:00:00Z',
        CreatedAt: '2024-03-01T08:00:00Z',
        Workflow: { Status: 'RESOLVED' },
      },
    ];
    mockSecurityHubSend.mockResolvedValueOnce({ Findings: activeFindings });
    mockSecurityHubSend.mockResolvedValueOnce({ Findings: resolvedFindings });

    const res = await lambdaHandler(makeEvent({ path: '/security-alerts' }), {});

    expect(res.statusCode).toBe(200);
    const body = JSON.parse(res.body);
    expect(body.alerts).toHaveLength(2);
    expect(body.alerts[0].id).toBe('abc123');
    expect(body.alerts[0].severity).toBe('CRITICAL');
    expect(body.alerts[0].status).toBe('ACTIVE');
    expect(body.alerts[1].id).toBe('def456');
    expect(body.alerts[1].status).toBe('RESOLVED');
  });

  test('returns empty alerts array when Findings is undefined', async () => {
    mockSecurityHubSend.mockResolvedValueOnce({});
    mockSecurityHubSend.mockResolvedValueOnce({});

    const res = await lambdaHandler(makeEvent({ path: '/security-alerts' }), {});

    expect(res.statusCode).toBe(200);
    const body = JSON.parse(res.body);
    expect(body.alerts).toEqual([]);
  });

  test('falls back to "General Finding" type when Types is undefined', async () => {
    mockSecurityHubSend.mockResolvedValueOnce({
      Findings: [{
        Id: 'arn:x/finding/notype',
        Types: undefined,
        Severity: { Label: 'HIGH' },
        Title: 'Unknown type',
        UpdatedAt: '2024-03-01T00:00:00Z',
        CreatedAt: '2024-03-01T00:00:00Z',
      }],
    });
    mockSecurityHubSend.mockResolvedValueOnce({ Findings: [] });

    const res = await lambdaHandler(makeEvent({ path: '/security-alerts' }), {});
    const body = JSON.parse(res.body);
    expect(body.alerts[0].type).toBe('General Finding');
  });

  test('falls back to "MEDIUM" severity when Severity is undefined', async () => {
    mockSecurityHubSend.mockResolvedValueOnce({
      Findings: [{
        Id: 'arn:x/finding/nosev',
        Types: ['SomeType'],
        Severity: undefined,
        Title: 'No severity',
        CreatedAt: '2024-03-01T00:00:00Z',
      }],
    });
    mockSecurityHubSend.mockResolvedValueOnce({ Findings: [] });

    const res = await lambdaHandler(makeEvent({ path: '/security-alerts' }), {});
    const body = JSON.parse(res.body);
    expect(body.alerts[0].severity).toBe('MEDIUM');
  });

  test('falls back to CreatedAt when UpdatedAt is missing', async () => {
    mockSecurityHubSend.mockResolvedValueOnce({
      Findings: [{
        Id: 'arn:x/finding/nodate',
        Types: ['SomeType'],
        Severity: { Label: 'HIGH' },
        Title: 'Old finding',
        CreatedAt: '2024-01-15T08:00:00Z',
      }],
    });
    mockSecurityHubSend.mockResolvedValueOnce({ Findings: [] });

    const res = await lambdaHandler(makeEvent({ path: '/security-alerts' }), {});
    const body = JSON.parse(res.body);
    expect(body.alerts[0].timestamp).toBe('2024-01-15T08:00:00Z');
  });

  test('returns 500 on SecurityHub error', async () => {
    mockSecurityHubSend.mockRejectedValueOnce(new Error('SecurityHub error'));

    const res = await lambdaHandler(makeEvent({ path: '/security-alerts' }), {});

    expect(res.statusCode).toBe(500);
    const body = JSON.parse(res.body);
    expect(body.error).toBe('SecurityHub error');
  });
});

// ── POST /run-tests ───────────────────────────────────────────────────────────
describe('POST /run-tests', () => {
  test('returns 200 with buildId from CodeBuild', async () => {
    mockCodeBuildSend.mockResolvedValueOnce({ build: { id: 'credologi-tests:build-abc123' } });

    const res = await lambdaHandler(makeEvent({ httpMethod: 'POST', path: '/run-tests' }), {});

    expect(res.statusCode).toBe(200);
    const body = JSON.parse(res.body);
    expect(body.buildId).toBe('credologi-tests:build-abc123');
  });

  test('falls back to inline health checks when CodeBuild fails', async () => {
    mockCodeBuildSend.mockRejectedValueOnce(new Error('CodeBuild not found'));
    // Inline checks: Cognito, SecurityHub, Snowflake
    mockCognitoSend.mockResolvedValueOnce({ Users: [] });
    mockSecurityHubSend.mockResolvedValueOnce({ Findings: [] });
    mockSecretsSend.mockResolvedValueOnce({ SecretString: 'key' });

    const res = await lambdaHandler(makeEvent({ httpMethod: 'POST', path: '/run-tests' }), {});

    expect(res.statusCode).toBe(200);
    const body = JSON.parse(res.body);
    expect(body.mode).toBe('inline-health-checks');
    expect(body.results.length).toBeGreaterThanOrEqual(3);
    expect(body.results.find(r => r.name === 'DynamoDB')).toBeUndefined();
  });
});

// ── GET /test-status ──────────────────────────────────────────────────────────
describe('GET /test-status', () => {
  test('returns 400 when buildId query param is missing', async () => {
    const res = await lambdaHandler(makeEvent({ path: '/test-status' }), {});

    expect(res.statusCode).toBe(400);
    expect(res.body).toBe('Missing buildId');
  });

  test('returns 400 when queryStringParameters is null', async () => {
    const res = await lambdaHandler(makeEvent({
      path: '/test-status',
      queryStringParameters: null,
    }), {});

    expect(res.statusCode).toBe(400);
  });

  test('returns 200 with build status and log link', async () => {
    mockCodeBuildSend.mockResolvedValueOnce({
      builds: [{
        buildStatus: 'SUCCEEDED',
        logs: { deepLink: 'https://console.aws.amazon.com/cloudwatch/logs/build' },
      }],
    });

    const res = await lambdaHandler(makeEvent({
      path: '/test-status',
      queryStringParameters: { buildId: 'credologi-tests:build-abc123' },
    }), {});

    expect(res.statusCode).toBe(200);
    const body = JSON.parse(res.body);
    expect(body.status).toBe('SUCCEEDED');
    expect(body.logs).toBe('https://console.aws.amazon.com/cloudwatch/logs/build');
  });

  test('returns 200 with IN_PROGRESS status', async () => {
    mockCodeBuildSend.mockResolvedValueOnce({
      builds: [{ buildStatus: 'IN_PROGRESS', logs: {} }],
    });

    const res = await lambdaHandler(makeEvent({
      path: '/test-status',
      queryStringParameters: { buildId: 'credologi-tests:build-xyz' },
    }), {});

    expect(res.statusCode).toBe(200);
    const body = JSON.parse(res.body);
    expect(body.status).toBe('IN_PROGRESS');
  });

  test('returns 200 with NOT_FOUND on CodeBuild polling error', async () => {
    mockCodeBuildSend.mockRejectedValueOnce(new Error('Build not found'));

    const res = await lambdaHandler(makeEvent({
      path: '/test-status',
      queryStringParameters: { buildId: 'invalid-build-id' },
    }), {});

    expect(res.statusCode).toBe(200);
    const body = JSON.parse(res.body);
    expect(body.status).toBe('NOT_FOUND');
  });
});

// ── GET /users ────────────────────────────────────────────────────────────────
describe('GET /users', () => {
  test('returns 403 for non-admin user', async () => {
    const res = await lambdaHandler(makeEvent({
      path: '/users',
      requestContext: { authorizer: { claims: nonAdminClaims } },
    }), {});

    expect(res.statusCode).toBe(403);
    const body = JSON.parse(res.body);
    expect(body.error).toBe('Unauthorized');
  });

  test('returns 403 when authorizer is null', async () => {
    const res = await lambdaHandler(makeEvent({
      path: '/users',
      requestContext: { authorizer: null },
    }), {});

    expect(res.statusCode).toBe(403);
  });

  test('returns 403 when claims is null', async () => {
    const res = await lambdaHandler(makeEvent({
      path: '/users',
      requestContext: { authorizer: { claims: null } },
    }), {});

    expect(res.statusCode).toBe(403);
  });

  test('returns 200 with user list for GlobalAdmins', async () => {
    mockCognitoSend.mockResolvedValueOnce({
      Users: [
        {
          Username: 'alice@credologi.com',
          Enabled: true,
          UserStatus: 'CONFIRMED',
          Attributes: [{ Name: 'email', Value: 'alice@credologi.com' }],
        },
        {
          Username: 'bob@credologi.com',
          Enabled: false,
          UserStatus: 'DISABLED',
          Attributes: [{ Name: 'email', Value: 'bob@credologi.com' }],
        },
      ],
    });

    const res = await lambdaHandler(makeEvent({
      path: '/users',
      requestContext: { authorizer: { claims: adminClaims } },
    }), {});

    expect(res.statusCode).toBe(200);
    const body = JSON.parse(res.body);
    expect(body.users).toHaveLength(2);
    expect(body.users[0].Username).toBe('alice@credologi.com');
    expect(body.users[0].email).toBe('alice@credologi.com');
    expect(body.users[0].Enabled).toBe(true);
    expect(body.users[0].UserStatus).toBe('CONFIRMED');
    expect(body.users[1].Enabled).toBe(false);
  });

  test('returns 200 with empty users array when Users is undefined', async () => {
    mockCognitoSend.mockResolvedValueOnce({});

    const res = await lambdaHandler(makeEvent({
      path: '/users',
      requestContext: { authorizer: { claims: adminClaims } },
    }), {});

    expect(res.statusCode).toBe(200);
    const body = JSON.parse(res.body);
    expect(body.users).toEqual([]);
  });

  test('uses empty string when email attribute is missing', async () => {
    mockCognitoSend.mockResolvedValueOnce({
      Users: [{
        Username: 'noemail',
        Enabled: true,
        UserStatus: 'CONFIRMED',
        Attributes: [],
      }],
    });

    const res = await lambdaHandler(makeEvent({
      path: '/users',
      requestContext: { authorizer: { claims: adminClaims } },
    }), {});

    expect(res.statusCode).toBe(200);
    const body = JSON.parse(res.body);
    expect(body.users[0].email).toBe('');
  });

  test('returns 500 on Cognito error', async () => {
    mockCognitoSend.mockRejectedValueOnce(new Error('Cognito unavailable'));

    const res = await lambdaHandler(makeEvent({
      path: '/users',
      requestContext: { authorizer: { claims: adminClaims } },
    }), {});

    expect(res.statusCode).toBe(500);
  });
});

// ── POST /users (create user) ─────────────────────────────────────────────────
describe('POST /users (create user)', () => {
  test('returns 403 for non-admin', async () => {
    const res = await lambdaHandler(makeEvent({
      httpMethod: 'POST',
      path: '/users',
      requestContext: { authorizer: { claims: nonAdminClaims } },
    }), {});

    expect(res.statusCode).toBe(403);
  });

  test('returns 400 when email is missing (null body)', async () => {
    const res = await lambdaHandler(makeEvent({
      httpMethod: 'POST',
      path: '/users',
      body: null,
      requestContext: { authorizer: { claims: adminClaims } },
    }), {});

    expect(res.statusCode).toBe(400);
    const body = JSON.parse(res.body);
    expect(body.error).toBe('Valid email required');
  });

  test('returns 400 when email is missing from body', async () => {
    const res = await lambdaHandler(makeEvent({
      httpMethod: 'POST',
      path: '/users',
      body: JSON.stringify({ givenName: 'John', familyName: 'Doe' }),
      requestContext: { authorizer: { claims: adminClaims } },
    }), {});

    expect(res.statusCode).toBe(400);
    const body = JSON.parse(res.body);
    expect(body.error).toBe('Valid email required');
  });

  test('returns 400 for invalid email format (no @)', async () => {
    const res = await lambdaHandler(makeEvent({
      httpMethod: 'POST',
      path: '/users',
      body: JSON.stringify({ email: 'not-an-email' }),
      requestContext: { authorizer: { claims: adminClaims } },
    }), {});

    expect(res.statusCode).toBe(400);
    const body = JSON.parse(res.body);
    expect(body.error).toBe('Valid email required');
  });

  test('returns 400 for invalid email format (no domain)', async () => {
    const res = await lambdaHandler(makeEvent({
      httpMethod: 'POST',
      path: '/users',
      body: JSON.stringify({ email: 'user@' }),
      requestContext: { authorizer: { claims: adminClaims } },
    }), {});

    expect(res.statusCode).toBe(400);
  });

  test('returns 201 on successful user creation', async () => {
    mockCognitoSend.mockResolvedValueOnce({ User: { Username: 'newuser@credologi.com' } });

    const res = await lambdaHandler(makeEvent({
      httpMethod: 'POST',
      path: '/users',
      body: JSON.stringify({
        email: 'newuser@credologi.com',
        givenName: 'New',
        familyName: 'User',
      }),
      requestContext: { authorizer: { claims: adminClaims } },
    }), {});

    expect(res.statusCode).toBe(201);
    const body = JSON.parse(res.body);
    expect(body.message).toBe('User created');
    expect(body.username).toBe('newuser@credologi.com');
    expect(mockCognitoSend).toHaveBeenCalledTimes(1);
  });

  test('assigns user to group when group is provided', async () => {
    mockCognitoSend.mockResolvedValueOnce({ User: { Username: 'admin@credologi.com' } });
    mockCognitoSend.mockResolvedValueOnce({}); // AdminAddUserToGroupCommand

    const res = await lambdaHandler(makeEvent({
      httpMethod: 'POST',
      path: '/users',
      body: JSON.stringify({
        email: 'admin@credologi.com',
        group: 'GlobalAdmins',
      }),
      requestContext: { authorizer: { claims: adminClaims } },
    }), {});

    expect(res.statusCode).toBe(201);
    expect(mockCognitoSend).toHaveBeenCalledTimes(2);
  });

  test('does not add to group when group is not provided', async () => {
    mockCognitoSend.mockResolvedValueOnce({ User: { Username: 'plain@credologi.com' } });

    const res = await lambdaHandler(makeEvent({
      httpMethod: 'POST',
      path: '/users',
      body: JSON.stringify({ email: 'plain@credologi.com' }),
      requestContext: { authorizer: { claims: adminClaims } },
    }), {});

    expect(res.statusCode).toBe(201);
    expect(mockCognitoSend).toHaveBeenCalledTimes(1);
  });

  test('returns 500 on Cognito create error', async () => {
    mockCognitoSend.mockRejectedValueOnce(new Error('UsernameExistsException'));

    const res = await lambdaHandler(makeEvent({
      httpMethod: 'POST',
      path: '/users',
      body: JSON.stringify({ email: 'exists@credologi.com' }),
      requestContext: { authorizer: { claims: adminClaims } },
    }), {});

    expect(res.statusCode).toBe(500);
    const body = JSON.parse(res.body);
    expect(body.error).toBe('UsernameExistsException');
  });
});

// ── POST /users/{username}/{action} ───────────────────────────────────────────
describe('POST /users/{username}/{action}', () => {
  const makeUserActionEvent = (action, overrides = {}) => makeEvent({
    httpMethod: 'POST',
    path: `/users/testuser/${action}`,
    pathParameters: { username: 'testuser', action },
    requestContext: { authorizer: { claims: adminClaims } },
    ...overrides,
  });

  test('returns 403 for non-admin on enable', async () => {
    const res = await lambdaHandler(makeUserActionEvent('enable', {
      requestContext: { authorizer: { claims: nonAdminClaims } },
    }), {});

    expect(res.statusCode).toBe(403);
    const body = JSON.parse(res.body);
    expect(body.error).toBe('Unauthorized');
  });

  test('enable user returns 200 with success message', async () => {
    mockCognitoSend.mockResolvedValueOnce({});

    const res = await lambdaHandler(makeUserActionEvent('enable'), {});

    expect(res.statusCode).toBe(200);
    const body = JSON.parse(res.body);
    expect(body.message).toBe('enable successful');
  });

  test('disable user returns 200 with success message', async () => {
    mockCognitoSend.mockResolvedValueOnce({});

    const res = await lambdaHandler(makeUserActionEvent('disable'), {});

    expect(res.statusCode).toBe(200);
    const body = JSON.parse(res.body);
    expect(body.message).toBe('disable successful');
  });

  test('reset user password returns 200 with success message', async () => {
    mockCognitoSend.mockResolvedValueOnce({});

    const res = await lambdaHandler(makeUserActionEvent('reset', {
      body: JSON.stringify({ tempPassword: 'NewTemp2026!' }),
    }), {});

    expect(res.statusCode).toBe(200);
    const body = JSON.parse(res.body);
    expect(body.message).toBe('Password reset successful');
  });

  test('delete user returns 200 with success message', async () => {
    mockCognitoSend.mockResolvedValueOnce({});

    const res = await lambdaHandler(makeUserActionEvent('delete'), {});

    expect(res.statusCode).toBe(200);
    const body = JSON.parse(res.body);
    expect(body.message).toBe('delete successful');
  });

  test('returns 400 for unknown action', async () => {
    const res = await lambdaHandler(makeUserActionEvent('activate'), {});

    expect(res.statusCode).toBe(400);
    const body = JSON.parse(res.body);
    expect(body.error).toBe('Invalid action');
  });

  test('returns 400 for empty string action', async () => {
    const res = await lambdaHandler(makeEvent({
      httpMethod: 'POST',
      path: '/users/testuser/ban',
      pathParameters: { username: 'testuser', action: 'ban' },
      requestContext: { authorizer: { claims: adminClaims } },
    }), {});

    expect(res.statusCode).toBe(400);
  });

  test('returns 500 on Cognito error', async () => {
    mockCognitoSend.mockRejectedValueOnce(new Error('UserNotFoundException'));

    const res = await lambdaHandler(makeUserActionEvent('delete'), {});

    expect(res.statusCode).toBe(500);
    const body = JSON.parse(res.body);
    expect(body.error).toBe('UserNotFoundException');
  });
});

// ── isAdmin authorization helper ──────────────────────────────────────────────
describe('isAdmin authorization', () => {
  test('grants access to GlobalAdmins group', async () => {
    mockCognitoSend.mockResolvedValueOnce({ Users: [] });
    const res = await lambdaHandler(makeEvent({
      path: '/users',
      requestContext: { authorizer: { claims: { 'cognito:groups': ['GlobalAdmins'] } } },
    }), {});
    expect(res.statusCode).toBe(200);
  });

  test('grants access to Admins group', async () => {
    mockCognitoSend.mockResolvedValueOnce({ Users: [] });
    const res = await lambdaHandler(makeEvent({
      path: '/users',
      requestContext: { authorizer: { claims: adminsClaims } },
    }), {});
    expect(res.statusCode).toBe(200);
  });

  test('denies access to non-admin group', async () => {
    const res = await lambdaHandler(makeEvent({
      path: '/users',
      requestContext: { authorizer: { claims: { 'cognito:groups': ['ReadOnly'] } } },
    }), {});
    expect(res.statusCode).toBe(403);
  });

  test('denies access when cognito:groups is empty', async () => {
    const res = await lambdaHandler(makeEvent({
      path: '/users',
      requestContext: { authorizer: { claims: { 'cognito:groups': [] } } },
    }), {});
    expect(res.statusCode).toBe(403);
  });

  test('denies access when claims is undefined', async () => {
    const res = await lambdaHandler(makeEvent({
      path: '/users',
      requestContext: { authorizer: {} },
    }), {});
    expect(res.statusCode).toBe(403);
  });
});

// ── 404 Handling ──────────────────────────────────────────────────────────────
describe('404 Not Found', () => {
  test('returns 404 for unknown GET route', async () => {
    const res = await lambdaHandler(makeEvent({ path: '/unknown' }), {});
    expect(res.statusCode).toBe(404);
    expect(res.body).toBe('Not Found');
  });

  test('returns 404 for unknown POST route (no pathParameters)', async () => {
    const res = await lambdaHandler(makeEvent({
      httpMethod: 'POST',
      path: '/unknown',
    }), {});
    expect(res.statusCode).toBe(404);
  });

  test('returns 404 for DELETE method', async () => {
    const res = await lambdaHandler(makeEvent({
      httpMethod: 'DELETE',
      path: '/health',
    }), {});
    expect(res.statusCode).toBe(404);
  });

  test('returns 404 for PUT method', async () => {
    const res = await lambdaHandler(makeEvent({
      httpMethod: 'PUT',
      path: '/users',
    }), {});
    expect(res.statusCode).toBe(404);
  });

  test('CORS headers are present on 404 responses', async () => {
    const res = await lambdaHandler(makeEvent({ path: '/nonexistent' }), {});
    expect(res.statusCode).toBe(404);
    expect(res.headers['Access-Control-Allow-Origin']).toBeDefined();
  });
});
