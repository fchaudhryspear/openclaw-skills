#!/usr/bin/env node
// unifi-monitor.js — UniFi Site Manager API health report
// API docs: https://api.ui.com/v1/

const https = require('https');
const fs = require('fs');
const path = require('path');

const CREDS_FILE = path.join(__dirname, 'unifi-creds.json');
const API_BASE = 'https://api.ui.com/v1';

function loadKey() {
  if (!fs.existsSync(CREDS_FILE)) { console.error('❌ unifi-creds.json not found'); process.exit(1); }
  const { api_key } = JSON.parse(fs.readFileSync(CREDS_FILE, 'utf8'));
  if (!api_key || api_key === 'NEEDS_API_KEY_FROM_USER') {
    console.error('❌ No API key set. Go to https://unifi.ui.com → Settings → API Keys');
    process.exit(1);
  }
  return api_key;
}

function apiFetch(endpoint, apiKey) {
  return new Promise((resolve, reject) => {
    https.get(`${API_BASE}/${endpoint}`, {
      headers: { 'X-API-KEY': apiKey, 'Accept': 'application/json' }
    }, (res) => {
      let d = '';
      res.on('data', c => d += c);
      res.on('end', () => {
        if (res.statusCode === 401) {
          reject(new Error('❌ Invalid API key — go to https://unifi.ui.com → Settings → API Keys'));
          return;
        }
        try { resolve(JSON.parse(d)); } catch (e) { reject(new Error(`Parse error: ${e.message}`)); }
      });
    }).on('error', reject);
  });
}

async function main() {
  const apiKey = loadKey();

  console.log('\n🌐 UniFi Network Health Report');
  console.log('════════════════════════════════════════════════════');

  const [sitesRes, devicesRes] = await Promise.all([
    apiFetch('sites', apiKey),
    apiFetch('devices', apiKey)
  ]);

  const sites = sitesRes.data || [];
  const hosts = devicesRes.data || [];

  // Build flat device list from hosts
  const allDevices = hosts.flatMap(h => (h.devices || []).map(d => ({ ...d, hostName: h.hostName })));

  const summary = [];

  // Build hostId → hostName map
  const hostMap = {};
  for (const h of hosts) hostMap[h.hostId] = h.hostName;

  for (const site of sites) {
    const name = site.meta?.name || site.meta?.desc || site.siteId;
    const hostLabel = hostMap[site.hostId] || null;
    const displayName = hostLabel || (name === 'default' ? (site.meta?.desc || 'Default') : name);
    const isp = site.statistics?.ispInfo?.name || 'Unknown ISP';
    const counts = site.statistics?.counts || {};
    const pcts = site.statistics?.percentages || {};
    const wans = site.statistics?.wans || {};

    const total = counts.totalDevice || 0;
    const offline = counts.offlineDevice || 0;
    const online = total - offline;
    const wifiClients = counts.wifiClient || 0;
    const wiredClients = counts.wiredClient || 0;
    const totalClients = wifiClients + wiredClients;
    const txRetry = pcts.txRetry != null ? pcts.txRetry.toFixed(1) : 'N/A';
    const wanUptime = pcts.wanUptime != null ? pcts.wanUptime.toFixed(1) : 'N/A';
    const criticalAlerts = counts.criticalNotification || 0;
    const pendingUpdates = counts.pendingUpdateDevice || 0;
    const gateway = site.statistics?.gateway?.shortname || 'Unknown';

    // WAN status
    const wanStatus = Object.entries(wans).map(([wan, data]) => {
      const upPct = parseFloat(data.wanUptime ?? 0);
      const up = upPct >= 99.9;
      return `${wan}: ${up ? '✅' : '❌'} (${upPct.toFixed(1)}% uptime)`;
    }).join(' · ');

    // Retry health indicator
    const retryHealth = parseFloat(txRetry) < 5 ? '🟢' : parseFloat(txRetry) < 15 ? '🟡' : '🔴';

    console.log(`\n📍 ${displayName}`);
    console.log(`   Gateway:  ${gateway} · ISP: ${isp}`);
    console.log(`   Devices:  ${online}/${total} online${offline > 0 ? ` ⚠️  ${offline} offline` : ' ✅'}`);
    console.log(`   Clients:  ${totalClients} total (${wifiClients} WiFi · ${wiredClients} wired)`);
    console.log(`   WiFi:     ${retryHealth} TX retry ${txRetry}% · WAN uptime ${wanUptime}%`);
    console.log(`   WAN:      ${wanStatus || 'N/A'}`);
    if (criticalAlerts > 0) console.log(`   🚨 Critical alerts: ${criticalAlerts}`);
    if (pendingUpdates > 0) console.log(`   🔄 Firmware updates pending: ${pendingUpdates}`);

    summary.push({ site: displayName, gateway, isp, devices: { online, total, offline }, clients: totalClients, txRetryPct: parseFloat(txRetry), wanUptime: parseFloat(wanUptime), criticalAlerts, pendingUpdates });
  }

  // Offline devices
  const offlineDevices = allDevices.filter(d => d.status === 'offline');
  if (offlineDevices.length > 0) {
    console.log('\n⚠️  Offline Devices:');
    for (const d of offlineDevices) {
      console.log(`   • ${d.name} (${d.model}) — ${d.hostName} — last seen: ${d.startupTime ? new Date(d.startupTime).toLocaleDateString() : 'unknown'}`);
    }
  }

  console.log('\n════════════════════════════════════════════════════');
  const totalClients = summary.reduce((s, x) => s + x.clients, 0);
  const totalDevices = summary.reduce((s, x) => s + x.devices.total, 0);
  const totalOffline = summary.reduce((s, x) => s + x.devices.offline, 0);
  console.log(`✅ ${sites.length} sites · ${totalDevices} devices · ${totalClients} clients · ${totalOffline} offline\n`);

  return summary;
}

module.exports = { main };
if (require.main === module) main().catch(e => { console.error('❌', e.message); process.exit(1); });
