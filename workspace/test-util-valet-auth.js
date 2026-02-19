const { ConfidentialClientApplication } = require('@azure/msal-node');

const cca = new ConfidentialClientApplication({
  auth: {
    clientId: 'f9da90a6-046c-410d-95c6-6dcb1d5d6523',
    authority: 'https://login.microsoftonline.com/fd036b44-5db1-45c7-a55a-711bee087e49',
    clientSecret: '1L.8Q~yq0qsTMGmZBlc91Tp.qDklPDUkIakHhdna'
  }
});

cca.acquireTokenByClientCredential({ scopes: ['https://graph.microsoft.com/.default'] })
  .then(result => {
    console.log('✅ Utility Valet TOKEN OK:', result.accessToken.substring(0, 20) + '...');
    console.log('Expires:', result.expiresOn ? result.expiresOn.toISOString() : 'unknown');
  })
  .catch(error => {
    console.error('❌ Auth Error:', error.message);
    console.error('Details:', error.errorCode, error.errorMessage);
  });
