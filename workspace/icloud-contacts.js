#!/usr/bin/env node
// icloud-contacts.js — CardDAV client for iCloud contacts
// Usage: node icloud-contacts.js search "john"
//        node icloud-contacts.js search "+14084648710"
//        node icloud-contacts.js refresh   (force cache refresh)

const https = require('https');
const fs = require('fs');
const path = require('path');

const CREDS_FILE = path.join(__dirname, 'icloud-creds.json');
const CACHE_FILE = path.join(__dirname, 'icloud-contacts-cache.json');
const CACHE_TTL_MS = 24 * 60 * 60 * 1000; // 24 hours
const CARDDAV_SERVER = 'contacts.icloud.com';

// ── Credentials ───────────────────────────────────────────────────────────────
function loadCreds() {
  if (!fs.existsSync(CREDS_FILE)) {
    console.error('❌ icloud-creds.json not found');
    process.exit(1);
  }
  const creds = JSON.parse(fs.readFileSync(CREDS_FILE, 'utf8'));
  if (!creds.password || creds.password === 'NEEDS_APP_SPECIFIC_PASSWORD') {
    console.error('❌ iCloud app-specific password not configured.');
    console.error('   1. Go to https://appleid.apple.com');
    console.error('   2. Sign In → Security → App-Specific Passwords');
    console.error('   3. Generate one named "Optimus"');
    console.error('   4. Add it to workspace/icloud-creds.json');
    process.exit(1);
  }
  return creds;
}

// ── CardDAV HTTP ──────────────────────────────────────────────────────────────
function cardDavRequest(method, reqPath, body, depth = '1') {
  const creds = loadCreds();
  const auth = Buffer.from(`${creds.username}:${creds.password}`).toString('base64');

  return new Promise((resolve, reject) => {
    const options = {
      hostname: CARDDAV_SERVER,
      port: 443,
      path: reqPath,
      method,
      headers: {
        'Authorization': `Basic ${auth}`,
        'Content-Type': 'application/xml; charset=utf-8',
        'Depth': depth
      }
    };
    if (body) options.headers['Content-Length'] = Buffer.byteLength(body);

    const req = https.request(options, (res) => {
      let data = '';
      res.on('data', c => data += c);
      res.on('end', () => {
        if (res.statusCode === 401) {
          reject(new Error('AUTH_FAILED: Invalid credentials. Check your app-specific password at appleid.apple.com'));
        } else if (res.statusCode >= 200 && res.statusCode < 400) {
          resolve({ status: res.statusCode, data, headers: res.headers });
        } else {
          reject(new Error(`HTTP ${res.statusCode}: ${data.substring(0, 200)}`));
        }
      });
    });
    req.on('error', reject);
    if (body) req.write(body);
    req.end();
  });
}

// ── Discovery ─────────────────────────────────────────────────────────────────
async function discoverPrincipal() {
  const body = `<?xml version="1.0" encoding="utf-8"?>
<d:propfind xmlns:d="DAV:"><d:prop><d:current-user-principal/></d:prop></d:propfind>`;
  try {
    const res = await cardDavRequest('PROPFIND', '/', body, '0');
    const m = res.data.match(/<(?:d:)?current-user-principal>\s*<(?:d:)?href>([^<]+)<\/(?:d:)?href>/);
    return m ? m[1] : '/';
  } catch (e) {
    if (e.message.startsWith('AUTH_FAILED')) throw e;
    return '/';
  }
}

async function discoverAddressbookHome(principalPath) {
  const body = `<?xml version="1.0" encoding="utf-8"?>
<d:propfind xmlns:d="DAV:" xmlns:card="urn:ietf:params:xml:ns:carddav">
  <d:prop><card:addressbook-home-set/></d:prop>
</d:propfind>`;
  try {
    const res = await cardDavRequest('PROPFIND', principalPath, body, '0');
    const m = res.data.match(/<(?:card:)?addressbook-home-set[^>]*>\s*<(?:d:)?href>([^<]+)<\/(?:d:)?href>/);
    if (m) return m[1];
  } catch (e) { /* fall through */ }
  // iCloud fallback
  const uid = principalPath.match(/\/(\d+)\//);
  return uid ? `/${uid[1]}/carddavhome/card/` : principalPath + 'carddav/';
}

async function listAddressbooks(home) {
  const body = `<?xml version="1.0" encoding="utf-8"?>
<d:propfind xmlns:d="DAV:" xmlns:card="urn:ietf:params:xml:ns:carddav">
  <d:prop><d:resourcetype/><d:displayname/></d:prop>
</d:propfind>`;
  try {
    const res = await cardDavRequest('PROPFIND', home, body, '1');
    const books = [];
    const re = /<d:href>([^<]+)<\/d:href>/g;
    let m;
    while ((m = re.exec(res.data)) !== null) {
      if (m[1] !== home && m[1].endsWith('/')) books.push(m[1]);
    }
    return books.length ? books : [home];
  } catch (e) { return [home]; }
}

// ── Contacts ──────────────────────────────────────────────────────────────────
async function fetchContacts(addressbookPath) {
  const body = `<?xml version="1.0" encoding="utf-8"?>
<card:addressbook-query xmlns:d="DAV:" xmlns:card="urn:ietf:params:xml:ns:carddav">
  <d:prop><d:getetag/><card:address-data/></d:prop>
  <card:limit><card:nresults>10000</card:nresults></card:limit>
</card:addressbook-query>`;
  const res = await cardDavRequest('REPORT', addressbookPath, body, '1');
  return parseVCards(res.data);
}

function parseVCards(xml) {
  const contacts = [];
  const re = /<(?:card:)?address-data[^>]*>([\s\S]*?)<\/(?:card:)?address-data>/g;
  let m;
  while ((m = re.exec(xml)) !== null) {
    let vcard = m[1].trim()
      .replace(/&#13;/g, '\r').replace(/&amp;/g, '&')
      .replace(/&lt;/g, '<').replace(/&gt;/g, '>');
    const c = parseVCard(vcard);
    if (c) contacts.push(c);
  }
  return contacts;
}

function parseVCard(vcard) {
  const lines = vcard.split(/\r?\n/);
  const contact = { name: '', phones: [], emails: [] };
  for (const line of lines) {
    if (line.startsWith('FN:')) {
      contact.name = line.substring(3).trim();
    } else if (line.startsWith('TEL')) {
      const m = line.match(/:([\d\s+\-()\\.]+)/);
      if (m) contact.phones.push(m[1].replace(/[\s\-().]/g, ''));
    } else if (line.startsWith('EMAIL')) {
      const m = line.match(/:([^\s]+)/);
      if (m) contact.emails.push(m[1]);
    }
  }
  return contact.name ? contact : null;
}

// ── Cache ─────────────────────────────────────────────────────────────────────
function loadCache() {
  try {
    if (!fs.existsSync(CACHE_FILE)) return null;
    const c = JSON.parse(fs.readFileSync(CACHE_FILE, 'utf8'));
    if (Date.now() - c.ts > CACHE_TTL_MS) return null;
    return c.contacts;
  } catch { return null; }
}

function saveCache(contacts) {
  fs.writeFileSync(CACHE_FILE, JSON.stringify({ ts: Date.now(), contacts }, null, 0));
}

async function getContacts(forceRefresh = false) {
  if (!forceRefresh) {
    const cached = loadCache();
    if (cached) {
      const ageH = Math.round((Date.now() - JSON.parse(fs.readFileSync(CACHE_FILE)).ts) / 3600000);
      console.log(`📇 Using cached contacts (${cached.length} contacts, ${ageH}h old)`);
      return cached;
    }
  }
  console.log('🔍 Fetching contacts from iCloud CardDAV...');
  const principal = await discoverPrincipal();
  const home = await discoverAddressbookHome(principal);
  const books = await listAddressbooks(home);
  console.log(`   Found ${books.length} addressbook(s)`);
  const contacts = await fetchContacts(books[0]);
  console.log(`   ✅ ${contacts.length} contacts fetched`);
  saveCache(contacts);
  return contacts;
}

// ── Search ────────────────────────────────────────────────────────────────────
function normalizePhone(p) { return p.replace(/[\s\-().+]/g, ''); }

function searchContacts(contacts, query) {
  const q = query.toLowerCase();
  const qPhone = normalizePhone(query);
  return contacts.filter(c => {
    if (c.name.toLowerCase().includes(q)) return true;
    for (const p of c.phones) {
      const n = normalizePhone(p);
      if (n.includes(qPhone) || qPhone.includes(n)) return true;
    }
    for (const e of c.emails) {
      if (e.toLowerCase().includes(q)) return true;
    }
    return false;
  });
}

function lookupByPhone(contacts, phone) {
  const n = normalizePhone(phone);
  return contacts.filter(c => c.phones.some(p => {
    const np = normalizePhone(p);
    return np.endsWith(n.slice(-10)) || n.endsWith(np.slice(-10));
  }));
}

function lookupByName(contacts, name) {
  const q = name.toLowerCase();
  return contacts.filter(c => c.name.toLowerCase().includes(q));
}

// ── CLI ───────────────────────────────────────────────────────────────────────
async function main() {
  const [action, query] = process.argv.slice(2);

  if (action === 'refresh') {
    await getContacts(true);
    return;
  }

  const contacts = await getContacts();

  if (action === 'search' && query) {
    const results = searchContacts(contacts, query);
    if (results.length === 0) {
      console.log(`\n🔎 No contacts found for: "${query}"`);
    } else {
      console.log(`\n🔎 ${results.length} result(s) for "${query}":`);
      for (const c of results.slice(0, 20)) {
        console.log(`  📇 ${c.name}`);
        if (c.phones.length) console.log(`     📞 ${c.phones.join(', ')}`);
        if (c.emails.length) console.log(`     📧 ${c.emails.join(', ')}`);
      }
    }
  } else {
    console.log(`\nUsage:`);
    console.log(`  node icloud-contacts.js search "john doe"`);
    console.log(`  node icloud-contacts.js search "+14085551234"`);
    console.log(`  node icloud-contacts.js refresh`);
  }
}

module.exports = { getContacts, searchContacts, lookupByPhone, lookupByName };
if (require.main === module) main().catch(e => { console.error('❌', e.message); process.exit(1); });
