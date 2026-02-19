// Office365 Email → Microsoft To Do v1.2 (Utility Valet FIXED)
// Client Credentials flow — no delegated /me, uses /users/{email}

const fs = require('fs');
const path = require('path');
const { ConfidentialClientApplication } = require('@azure/msal-node');
const { Client: GraphClient } = require('@microsoft/microsoft-graph-client');

// Load creds relative to this file's directory
const credsPath = path.join(__dirname, 'office365-creds.json');
const creds = JSON.parse(fs.readFileSync(credsPath)).accounts.utilityvalet;

async function getAccessToken() {
  const cca = new ConfidentialClientApplication({
    auth: {
      clientId: creds.clientId,
      authority: `https://login.microsoftonline.com/${creds.tenantId}`,
      clientSecret: creds.secretValue  // plain string, NOT { secret: ... }
    }
  });

  const tokenResponse = await cca.acquireTokenByClientCredential({
    scopes: ['https://graph.microsoft.com/.default']
  });

  if (!tokenResponse || !tokenResponse.accessToken) {
    throw new Error('Failed to acquire token');
  }

  return tokenResponse.accessToken;
}

async function getGraphClient() {
  const token = await getAccessToken();

  const graph = GraphClient.init({
    authProvider: (done) => done(null, token)
  });

  return graph;
}

async function scanInbox() {
  try {
    console.log(`🔑 Authenticating as ${creds.email}...`);
    const graph = await getGraphClient();
    console.log('✅ Graph client ready');

    // Client credentials flow: use /users/{email} not /me
    const messages = await graph
      .api(`/users/${creds.email}/mailFolders/Inbox/messages`)
      .filter('isRead eq false')
      .select('id,subject,from,receivedDateTime,bodyPreview,webLink,isRead')
      .top(10)
      .get();

    console.log(`📧 Found ${messages.value.length} unread Inbox emails:`);

    for (const msg of messages.value) {
      const preview = (msg.bodyPreview || '').substring(0, 80);
      const sender = msg.from?.emailAddress?.address || 'unknown';
      console.log(`  📄 "${msg.subject}" | From: ${sender}`);
      console.log(`     Preview: ${preview}...`);

      // Junk filter
      const bodyLower = (msg.bodyPreview || '').toLowerCase();
      const isJunk = bodyLower.includes('unsubscribe') || bodyLower.includes('sale') ||
                     bodyLower.includes('offer') || bodyLower.includes('discount');

      if (isJunk) {
        console.log(`   → 🚮 Junk filtered, skipping`);
        continue;
      }

      // Task detection
      const isTask = sender.toLowerCase().includes('faisal') ||
                     bodyLower.includes('can you') ||
                     bodyLower.includes('please') ||
                     bodyLower.includes('handle');

      if (isTask) {
        console.log(`   → ✅ TASK DETECTED`);
        // TODO: Microsoft To Do API integration
      }

      // Mark read
      await graph.api(`/users/${creds.email}/messages/${msg.id}`).patch({ isRead: true });
      console.log(`   → ✅ Marked READ`);
    }

    console.log('\n🎉 Inbox scan complete');
  } catch (error) {
    console.error('❌ Error:', error.message);
    if (error.statusCode) console.error('HTTP Status:', error.statusCode);
    if (error.code) console.error('Error Code:', error.code);
  }
}

scanInbox();
