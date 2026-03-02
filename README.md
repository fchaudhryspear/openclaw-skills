# Credologi Mission Control Portal

Central dashboard for Real-Time Financial Data Lake management. See [full design spec](docs/architecture.md) for details.

## Setup & Deployment

### Prerequisites
- AWS CLI configured with admin access.
- Node.js 20+, SAM CLI, npm.
- Cognito User Pool: us-east-1_M6lTgVQaw (with GlobalAdmins/Admins groups).

### Backend (SAM)
1. Clone repo: `git clone https://github.com/versatly/credologi-portal.git` (assuming repo).
2. `cd backend`
3. `npm install`
4. `sam build`
5. `sam deploy --guided` (enter CognitoUserPoolId: us-east-1_M6lTgVQaw, etc.).
6. Note the ApiUrl output for frontend.

### Frontend (React/Amplify)
1. `cd frontend`
2. Update `.env`: `REACT_APP_API_URL=<ApiUrl from deploy>`
3. `npm install`
4. `amplify init` (if new) or `amplify pull`.
5. `npm run dev` for local; `amplify publish` for hosting.

### Testing
- Sign in with GlobalAdmins user.
- Create/test user via /users.
- Trace a mock app with CloudWatch queries (see design doc).

### Troubleshooting
- Errors? Check CloudWatch Logs with saved queries.
- Contact: faisal@credologi.com

For full architecture, see docs/.
