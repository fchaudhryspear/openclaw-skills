// lib/graph.js — Graph API client using client credentials (no /me, uses /users/{email})
const https = require('https');
const path = require('path');
const fs = require('fs');
const { ConfidentialClientApplication } = require('@azure/msal-node');

const CREDS_FILE = path.join(__dirname, '..', 'office365-creds.json');

function loadCreds() {
  return JSON.parse(fs.readFileSync(CREDS_FILE, 'utf8')).accounts;
}

function listAccounts() {
  const creds = loadCreds();
  return Object.keys(creds).map(name => ({ account: name, ...creds[name] }));
}

// Token cache: { [clientId+tenantId]: { token, expiresAt } }
const tokenCache = {};

async function getToken(cred) {
  const cacheKey = `${cred.clientId}:${cred.tenantId}`;
  const cached = tokenCache[cacheKey];
  if (cached && cached.expiresAt > Date.now() + 60000) {
    return cached.token;
  }

  const cca = new ConfidentialClientApplication({
    auth: {
      clientId: cred.clientId,
      authority: `https://login.microsoftonline.com/${cred.tenantId}`,
      clientSecret: cred.secretValue  // plain string
    }
  });

  const result = await cca.acquireTokenByClientCredential({
    scopes: ['https://graph.microsoft.com/.default']
  });

  if (!result || !result.accessToken) throw new Error('Failed to acquire token');

  tokenCache[cacheKey] = {
    token: result.accessToken,
    expiresAt: result.expiresOn ? result.expiresOn.getTime() : Date.now() + 3500000
  };

  return tokenCache[cacheKey].token;
}

class GraphClient {
  constructor(accountName) {
    const creds = loadCreds();
    const cred = creds[accountName];
    if (!cred) throw new Error(`Unknown account: ${accountName}`);
    this.cred = cred;
    this.email = cred.email;
    this.baseUrl = 'https://graph.microsoft.com/v1.0';
  }

  async request(method, urlPath, body = null) {
    const token = await getToken(this.cred);
    // Replace /me/ with /users/{email}/
    const resolvedPath = urlPath.replace(/^\/me\//, `/users/${this.email}/`).replace(/^\/me$/, `/users/${this.email}`);
    const fullUrl = resolvedPath.startsWith('http') ? resolvedPath : `${this.baseUrl}${resolvedPath}`;
    const url = new URL(fullUrl);

    return new Promise((resolve, reject) => {
      const options = {
        hostname: url.hostname,
        path: url.pathname + url.search,
        method,
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      };

      const req = https.request(options, (res) => {
        let data = '';
        res.on('data', chunk => data += chunk);
        res.on('end', () => {
          if (res.statusCode === 204) return resolve(null); // No content
          try {
            const parsed = JSON.parse(data);
            if (res.statusCode >= 200 && res.statusCode < 300) {
              resolve(parsed);
            } else {
              const msg = parsed.error?.message || data;
              const err = new Error(`Graph API ${res.statusCode}: ${msg}`);
              err.statusCode = res.statusCode;
              err.code = parsed.error?.code;
              reject(err);
            }
          } catch (e) {
            if (res.statusCode >= 200 && res.statusCode < 300) resolve(data);
            else reject(new Error(`HTTP ${res.statusCode}: ${data}`));
          }
        });
      });

      req.on('error', reject);
      if (body) req.write(JSON.stringify(body));
      req.end();
    });
  }

  // ── Mail ────────────────────────────────────────────────────────────────────
  async listMessages(limit = 10, folder = 'Inbox') {
    return this.request('GET', `/me/mailFolders/${folder}/messages?$top=${limit}&$select=id,subject,from,receivedDateTime,isRead,bodyPreview&$orderby=receivedDateTime DESC`);
  }

  async getMessages(folder, filter, limit = 20) {
    let url = `/me/mailFolders/${folder}/messages?$top=${limit}&$select=id,subject,from,receivedDateTime,body,isRead&$orderby=receivedDateTime DESC`;
    if (filter) url += `&$filter=${encodeURIComponent(filter)}`;
    return this.request('GET', url);
  }

  async getMessage(id) {
    return this.request('GET', `/me/messages/${id}?$select=id,subject,from,receivedDateTime,body,isRead`);
  }

  async markAsRead(messageId, isRead = true) {
    return this.request('PATCH', `/me/messages/${messageId}`, { isRead });
  }

  async getSentMessages(limit = 30) {
    return this.request('GET', `/me/mailFolders/SentItems/messages?$top=${limit}&$select=id,subject,from,body,receivedDateTime&$orderby=receivedDateTime DESC`);
  }

  async createDraftReply(messageId, htmlBody) {
    // Create draft reply linked to original
    const draft = await this.request('POST', `/me/messages/${messageId}/createReply`, {});
    // Update the draft body
    await this.request('PATCH', `/me/messages/${draft.id}`, {
      body: { contentType: 'HTML', content: htmlBody }
    });
    return draft;
  }

  // ── Calendar ─────────────────────────────────────────────────────────────────
  async getUpcomingEvents(days = 14) {
    const start = new Date().toISOString();
    const end = new Date(Date.now() + days * 86400000).toISOString();
    return this.request('GET', `/me/calendar/calendarView?startDateTime=${start}&endDateTime=${end}&$top=100&$select=id,subject,start,end,showAs,isAllDay&$orderby=start/dateTime`);
  }

  async createEvent(eventData) {
    return this.request('POST', `/me/calendar/events`, eventData);
  }

  async deleteEvent(eventId) {
    return this.request('DELETE', `/me/calendar/events/${eventId}`);
  }

  // ── Tasks (To Do) ────────────────────────────────────────────────────────────
  async getTaskLists() {
    return this.request('GET', `/me/todo/lists`);
  }

  async getDefaultTaskList() {
    const result = await this.getTaskLists();
    const lists = result.value || [];
    return lists.find(l => l.wellknownListName === 'defaultList') || lists[0];
  }

  async createTask(taskData) {
    const list = await this.getDefaultTaskList();
    if (!list) throw new Error('No task list found');
    const task = {
      title: taskData.title,
      body: { content: taskData.notes || '', contentType: 'text' },
      importance: taskData.priority === 'high' ? 'high' : 'normal'
    };
    if (taskData.dueDate) {
      task.dueDateTime = { dateTime: taskData.dueDate + 'T00:00:00', timeZone: 'UTC' };
    }
    return this.request('POST', `/me/todo/lists/${list.id}/tasks`, task);
  }

  async listTasks(limit = 50) {
    const list = await this.getDefaultTaskList();
    if (!list) return [];
    const result = await this.request('GET', `/me/todo/lists/${list.id}/tasks?$top=${limit}&$filter=status ne 'completed'&$orderby=createdDateTime DESC`);
    return result.value || [];
  }
}

module.exports = { GraphClient, listAccounts };
