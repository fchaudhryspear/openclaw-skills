'use strict';

const { DynamoDBClient } = require('@aws-sdk/client-dynamodb');
const { DynamoDBDocumentClient, QueryCommand } = require('@aws-sdk/lib-dynamodb');
const { SecurityHubClient, GetFindingsCommand } = require('@aws-sdk/client-securityhub');
const { CognitoIdentityProviderClient, AdminListUsersCommand, AdminEnableUserCommand, AdminDisableUserCommand, AdminResetUserPasswordCommand, AdminCreateUserCommand, AdminAddUserToGroupCommand, AdminDeleteUserCommand } = require('@aws-sdk/client-cognito-identity-provider');
const { CodeBuildClient, StartBuildCommand, BatchGetBuildsCommand } = require('@aws-sdk/client-codebuild');
const { SecretsManagerClient, GetSecretValueCommand } = require('@aws-sdk/client-secrets-manager');

const region = 'us-east-1';
const docClient = DynamoDBDocumentClient.from(new DynamoDBClient({ region }));
const securityHub = new SecurityHubClient({ region });
const cognito = new CognitoIdentityProviderClient({ region });
const codebuild = new CodeBuildClient({ region });
const secrets = new SecretsManagerClient({ region });

const corsHeaders = {
  'Access-Control-Allow-Origin': 'https://missioncontrol.credologi.com',
  'Access-Control-Allow-Headers': 'Content-Type, Authorization',
  'Access-Control-Allow-Methods': 'OPTIONS,POST,GET'
};

const isAdmin = (claims) => {
  const groups = claims?.['cognito:groups'] || [];
  return groups.includes('GlobalAdmins') || groups.includes('Admins');
};

exports.lambdaHandler = async (event, context) => {
  // 1. CORS Preflight Interceptor
  if (event.httpMethod === 'OPTIONS') {
    return { statusCode: 200, headers: corsHeaders, body: '' };
  }

  try {
    // 2. Health Check (Validates Snowflake Secret)
    if (event.httpMethod === 'GET' && event.path === '/health') {
      const command = new GetSecretValueCommand({ SecretId: 'snowflake-private-key' });
      await secrets.send(command);
      return { statusCode: 200, headers: corsHeaders, body: JSON.stringify({ status: 'healthy', warehouse: 'COMPUTE_WH' }) };
    }

    // 3. Data Lake Flows
    if (event.httpMethod === 'GET' && event.path === '/flows') {
      const today = new Date().toISOString().split('T')[0];
      const command = new QueryCommand({
        TableName: process.env.AGGREGATES_TABLE,
        KeyConditionExpression: '#dt = :today',
        ExpressionAttributeNames: { '#dt': 'Date', '#cnt': 'Count' },
        ExpressionAttributeValues: { ':today': today },
        ProjectionExpression: '#dt, FlowType, #cnt'
      });
      const { Items } = await docClient.send(command);
      return { statusCode: 200, headers: corsHeaders, body: JSON.stringify({ date: today, metrics: Items || [] }) };
    }

    // 4. Security Alerts
    if (event.httpMethod === 'GET' && event.path === '/security-alerts') {
      const command = new GetFindingsCommand({
        Filters: {
          RecordState: [{ Value: 'ACTIVE', Comparison: 'EQUALS' }],
          SeverityLabel: [ { Value: 'CRITICAL', Comparison: 'EQUALS' }, { Value: 'HIGH', Comparison: 'EQUALS' } ]
        },
        MaxResults: 50
      });
      const { Findings } = await securityHub.send(command);
      const alerts = (Findings || []).map(f => ({
        id: f.Id.split('/').pop(),
        type: f.Types?.[0] || 'General Finding',
        severity: f.Severity?.Label || 'MEDIUM',
        description: f.Title,
        timestamp: f.UpdatedAt || f.CreatedAt
      }));
      return { statusCode: 200, headers: corsHeaders, body: JSON.stringify({ alerts }) };
    }

    // 5. Test Runner (CodeBuild)
    if (event.httpMethod === 'POST' && event.path === '/run-tests') {
      const command = new StartBuildCommand({ projectName: process.env.CODEBUILD_PROJECT_NAME });
      const response = await codebuild.send(command);
      return { statusCode: 200, headers: corsHeaders, body: JSON.stringify({ buildId: response.build.id }) };
    }

    if (event.httpMethod === 'GET' && event.path === '/test-status') {
      const buildId = event.queryStringParameters?.buildId;
      if (!buildId) return { statusCode: 400, headers: corsHeaders, body: 'Missing buildId' };
      const command = new BatchGetBuildsCommand({ ids: [buildId] });
      const response = await codebuild.send(command);
      const build = response.builds[0];
      return { statusCode: 200, headers: corsHeaders, body: JSON.stringify({ status: build.buildStatus, logs: build.logs?.deepLink }) };
    }

    // 6. User Management (GET /users)
    const userPoolId = process.env.USER_POOL_ID;
    if (event.httpMethod === 'GET' && event.path === '/users') {
      if (!isAdmin(event.requestContext.authorizer?.claims)) return { statusCode: 403, headers: corsHeaders, body: JSON.stringify({ error: 'Unauthorized' }) };
      
      const command = new AdminListUsersCommand({ UserPoolId: userPoolId, Limit: 60 });
      const { Users } = await cognito.send(command);
      const users = (Users || []).map(u => ({
        Username: u.Username,
        Enabled: u.Enabled,
        UserStatus: u.UserStatus,
        email: u.Attributes.find(a => a.Name === 'email')?.Value || ''
      }));
      return { statusCode: 200, headers: corsHeaders, body: JSON.stringify({ users }) };
    }

    // 7. User Management (POST /users - Create)
    if (event.httpMethod === 'POST' && event.path === '/users') {
      if (!isAdmin(event.requestContext.authorizer?.claims)) return { statusCode: 403, headers: corsHeaders, body: JSON.stringify({ error: 'Unauthorized' }) };
      
      const body = JSON.parse(event.body || ''{}}');
      if (!body.email || !/\S+@\S+\.\S+/.test(body.email)) return { statusCode: 400, headers: corsHeaders, body: JSON.stringify({ error: 'Valid email required' }) };
      
      const createCommand = new AdminCreateUserCommand({
        UserPoolId: userPoolId,
        Username: body.email,
        UserAttributes: [
          { Name: 'email', Value: body.email },
          { Name: 'given_name', Value: body.givenName || '' },
          { Name: 'family_name', Value: body.familyName || '' },
          { Name: 'email_verified', Value: 'true' }
        ],
        MessageAction: 'SUPPRESS'
      });
      const { User } = await cognito.send(createCommand);

      if (body.group) {
        await cognito.send(new AdminAddUserToGroupCommand({ UserPoolId: userPoolId, Username: User.Username, GroupName: body.group }));
      }
      console.log(`Created user ${User.Username} by admin ${event.requestContext.authorizer?.claims.sub}`);
      return { statusCode: 201, headers: corsHeaders, body: JSON.stringify({ message: 'User created', username: User.Username }) };
    }

    // 8. User Management Actions (/users/{username}/{action})
    if (event.httpMethod === 'POST' && event.pathParameters?.username && event.pathParameters?.action) {
      if (!isAdmin(event.requestContext.authorizer?.claims)) return { statusCode: 403, headers: corsHeaders, body: JSON.stringify({ error: 'Unauthorized' }) };
      
      const { username, action } = event.pathParameters;
      let command;
      switch (action) {
        case 'enable': command = new AdminEnableUserCommand({ UserPoolId: userPoolId, Username: username }); break;
        case 'disable': command = new AdminDisableUserCommand({ UserPoolId: userPoolId, Username: username }); break;
        case 'reset': command = new AdminResetUserPasswordCommand({ UserPoolId: userPoolId, Username: username }); break;
        case 'delete': command = new AdminDeleteUserCommand({ UserPoolId: userPoolId, Username: username }); break;
        default: return { statusCode: 400, headers: corsHeaders, body: JSON.stringify({ error: 'Invalid action' }) };
      }
      await cognito.send(command);
      console.log(`Performed ${action} on ${username} by admin ${event.requestContext.authorizer?.claims.sub}`);
      return { statusCode: 200, headers: corsHeaders, body: JSON.stringify({ message: `${action} successful` }) };
    }

    return { statusCode: 404, headers: corsHeaders, body: 'Not Found' };
  } catch (error) {
    console.error("Handler Error:", error);
    return { statusCode: 500, headers: corsHeaders, body: JSON.stringify({ error: error.message }) };
  }
};
