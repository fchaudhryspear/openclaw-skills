const fs = require('fs');
const path = require('path');
const { ConfidentialClientApplication } = require('@azure/msal-node');

const creds = JSON.parse(fs.readFileSync(path.join(__dirname, 'office365-creds.json'))).accounts;

async function testAccount(name, account) {
  try {
    const cca = new ConfidentialClientApplication({
      auth: {
        clientId: account.clientId,
        authority: `https://login.microsoftonline.com/${account.tenantId}`,
        clientSecret: account.secretValue
      }
    });

    const result = await cca.acquireTokenByClientCredential({
      scopes: ['https://graph.microsoft.com/.default']
    });

    if (result && result.accessToken) {
      const expires = result.expiresOn ? result.expiresOn.toISOString() : 'unknown';
      console.log(`✅ ${name.padEnd(14)} | ${account.email.padEnd(35)} | expires ${expires}`);
    } else {
      console.log(`❌ ${name.padEnd(14)} | ${account.email.padEnd(35)} | No token returned`);
    }
  } catch (err) {
    console.log(`❌ ${name.padEnd(14)} | ${account.email.padEnd(35)} | ${err.errorCode || err.message}`);
  }
}

(async () => {
  console.log('🔐 Testing all Microsoft Graph accounts...\n');
  for (const [name, account] of Object.entries(creds)) {
    await testAccount(name, account);
  }
  console.log('\nDone.');
})();
