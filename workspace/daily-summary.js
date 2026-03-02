#!/usr/bin/env node
// daily-summary.js — Morning summary email to faisal@credologi.com
// Sends: tasks, today's meetings, auto-reply draft count, injection schedule

const { GraphClient, listAccounts } = require('./lib/graph');
const { generateReport, formatReportForTelegram } = require('/Users/faisalshomemacmini/.openclaw/workspace/ai-cost-tracker/daily-token-report.js');

const SUMMARY_ACCOUNT = 'credologi';
const RECIPIENT = 'faisal@credologi.com';

// ── Injection Schedule ────────────────────────────────────────────────────────
const INJECTION_SCHEDULE = {
  Monday:    'MOTS-c (0.4 mL) + AOD-9604 (0.4 mL) + NAD+ (0.5 mL)',
  Tuesday:   'MOTS-c (0.4 mL) + AOD-9604 (0.4 mL)',
  Wednesday: 'Retatrutide (0.2 mL) + AOD-9604 (0.4 mL) + NAD+ (0.5 mL)',
  Thursday:  'MOTS-c (0.4 mL) + AOD-9604 (0.4 mL)',
  Friday:    'MOTS-c (0.4 mL) + AOD-9604 (0.4 mL) + NAD+ (0.5 mL)',
  Saturday:  'Retatrutide (0.2 mL) + AOD-9604 (0.4 mL)',
  Sunday:    'MOTS-c (0.4 mL) + AOD-9604 (0.4 mL)'
};

function toCST(date) {
  return new Date(date).toLocaleString('en-US', { timeZone: 'America/Chicago' });
}
function formatTime(dt, timeZone = 'UTC') {
  // Handle UTC datetimes from Graph API properly
  // The datetime string may not have timezone info, so we explicitly treat it as UTC
  const dateStr = dt.endsWith('Z') ? dt : dt + 'Z';
  return new Date(dateStr).toLocaleTimeString('en-US', {
    hour: 'numeric',
    minute: '2-digit',
    hour12: true,
    timeZone: 'America/Chicago'
  });
}
function formatDate(dt) {
  return new Date(dt).toLocaleDateString('en-US', { weekday: 'long', month: 'long', day: 'numeric', year: 'numeric', timeZone: 'America/Chicago' });
}
function getDayOfWeek() {
  return new Date().toLocaleDateString('en-US', { weekday: 'long', timeZone: 'America/Chicago' });
}

// ── Data Collectors ───────────────────────────────────────────────────────────
function isTodayInCST(dateTimeStr) {
  // Check if a given ISO datetime falls on "today" in CST timezone
  const date = new Date(dateTimeStr);
  const now = new Date();

  // Format both dates as YYYY-MM-DD in CST
  const cstOptions = { timeZone: 'America/Chicago', year: 'numeric', month: '2-digit', day: '2-digit' };
  const dateStr = date.toLocaleDateString('en-US', cstOptions);
  const todayStr = now.toLocaleDateString('en-US', cstOptions);

  return dateStr === todayStr;
}

async function getTasks() {
  try {
    const client = new GraphClient(SUMMARY_ACCOUNT);
    const tasks = await client.listTasks(100);

    // Filter for: new tasks created today OR tasks due today
    const todaysTasks = tasks.filter(t => {
      if (t.status === 'completed') return false;

      // Check if created today
      const createdToday = t.createdDateTime && isTodayInCST(t.createdDateTime);

      // Check if due today
      const dueToday = t.dueDateTime?.dateTime && isTodayInCST(t.dueDateTime.dateTime);

      return createdToday || dueToday;
    });

    // Sort: high priority first, then by due date
    const sorted = todaysTasks.sort((a, b) => {
      const aHigh = a.importance === 'high' ? 1 : 0;
      const bHigh = b.importance === 'high' ? 1 : 0;
      if (aHigh !== bHigh) return bHigh - aHigh;
      return (a.dueDateTime?.dateTime || 'z') < (b.dueDateTime?.dateTime || 'z') ? -1 : 1;
    });

    return { tasks: sorted, total: sorted.length };
  } catch (e) {
    console.error('Tasks error:', e.message);
    return { tasks: [], total: 0 };
  }
}

function getCSTDateRange() {
  // Query a 48-hour window to ensure we capture all of "today" in CST
  // Then we'll filter results to only include actual "today" meetings
  const now = new Date();

  // Start: 24 hours ago
  const start = new Date(now);
  start.setHours(start.getHours() - 24);

  // End: 24 hours from now
  const end = new Date(now);
  end.setHours(end.getHours() + 24);

  return { start: start.toISOString(), end: end.toISOString() };
}

async function getMeetings() {
  const meetings = [];
  const accounts = listAccounts();
  const { start: todayStart, end: todayEnd } = getCSTDateRange();

  for (const acc of accounts) {
    try {
      const client = new GraphClient(acc.account);
      const result = await client.request('GET',
        `/me/calendar/calendarView?startDateTime=${todayStart}&endDateTime=${todayEnd}&$top=50&$select=subject,start,end,location,isAllDay&$orderby=start/dateTime`
      );
      for (const e of (result.value || [])) {
        if (e.subject === 'X' || e.subject?.startsWith('X ')) continue; // skip busy blockers
        if (e.isAllDay) continue;
        // Only include meetings that are actually "today" in CST
        if (!isTodayInCST(e.start?.dateTime)) continue;
        meetings.push({ ...e, account: acc.account });
      }
    } catch (e) { /* skip failed accounts */ }
  }

  // Deduplicate by subject+start across accounts
  const seen = new Set();
  const deduped = meetings.filter(m => {
    const key = `${m.subject}|${m.start?.dateTime}`;
    if (seen.has(key)) return false;
    seen.add(key); return true;
  });

  return deduped.sort((a, b) => new Date(a.start.dateTime) - new Date(b.start.dateTime));
}

async function getNewDraftsToday() {
  let total = 0;
  const accounts = listAccounts();

  // Get today's date range in CST for filtering
  const now = new Date();
  const cstDateStr = now.toLocaleDateString('en-US', { timeZone: 'America/Chicago', year: 'numeric', month: '2-digit', day: '2-digit' });
  const [month, day, year] = cstDateStr.split('/').map(Number);

  // Create start of day in CST (00:00:00) as ISO string
  const startOfDayCST = new Date(Date.UTC(year, month - 1, day, 6, 0, 0)); // 6am UTC = midnight CST
  const startOfDayISO = startOfDayCST.toISOString();

  for (const acc of accounts) {
    try {
      const client = new GraphClient(acc.account);
      // Filter drafts created today using createdDateTime
      const result = await client.request('GET',
        `/me/mailFolders/Drafts/messages?$filter=createdDateTime ge ${startOfDayISO}&$count=true&$select=id&$top=50`
      );
      total += result['@odata.count'] || (result.value?.length || 0);
    } catch (e) { /* skip */ }
  }
  return total;
}

async function getAICostSummary() {
  try {
    const report = generateReport();
    return formatReportForTelegram(report);
  } catch (e) {
    console.error('AI Cost Report error:', e.message);
    return 'Error generating AI Cost Report.';
  }
}

// ── HTML Generator ────────────────────────────────────────────────────────────
function buildHTML(day, tasks, meetings, draftCount, aiCostReport) {
  const injection = INJECTION_SCHEDULE[day] || 'No schedule';
  const today = formatDate(new Date());

  const taskRows = tasks.tasks.slice(0, 15).map(t => {
    const high = t.importance === 'high';
    const due = t.dueDateTime ? `<span style="color:#999;font-size:12px"> · Due ${new Date(t.dueDateTime.dateTime).toLocaleDateString('en-US',{month:'short',day:'numeric',timeZone:'America/Chicago'})}</span>` : '';
    return `<div style="padding:10px 12px;margin:6px 0;background:white;border-left:3px solid ${high?'#e74c3c':'#3498db'};border-radius:4px">
      ${high?'<span style="color:#e74c3c;font-weight:bold">❗</span> ':''}
      <span style="font-weight:${high?'bold':'normal'}">${t.title}</span>${due}
    </div>`;
  }).join('');

  const meetingRows = meetings.map(m => {
    const start = formatTime(m.start.dateTime, m.start.timeZone);
    const end = formatTime(m.end.dateTime, m.end.timeZone);
    const loc = m.location?.displayName ? `<div style="color:#999;font-size:12px;margin-top:3px">📍 ${m.location.displayName}</div>` : '';
    return `<div style="padding:12px;margin:8px 0;background:white;border-left:4px solid #9b59b6;border-radius:4px">
      <div style="font-weight:bold">${m.subject || '(No subject)'}</div>
      <div style="color:#3498db;font-weight:bold;margin-top:3px">🕐 ${start} – ${end}</div>
      ${loc}
      <span style="display:inline-block;background:#ecf0f1;color:#666;padding:2px 7px;border-radius:4px;font-size:11px;margin-top:5px">${m.account}</span>
    </div>`;
  }).join('');

  return `<!DOCTYPE html><html><head><meta charset="utf-8"></head><body style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;line-height:1.6;color:#333;max-width:750px;margin:0 auto;padding:20px;background:#f5f6fa">

<h1 style="color:#2c3e50;border-bottom:3px solid #3498db;padding-bottom:10px;margin-bottom:5px">📊 Daily Summary</h1>
<div style="color:#7f8c8d;margin-bottom:25px">${today}</div>

<!-- INJECTION -->
<div style="background:linear-gradient(135deg,#667eea,#764ba2);color:white;border-radius:10px;padding:20px;margin:20px 0">
  <h2 style="margin:0 0 10px;color:white;font-size:18px">💉 Today's Injections</h2>
  <div style="font-size:13px;opacity:0.85;margin-bottom:8px">⏰ 7:00 AM · Empty stomach</div>
  <div style="font-size:20px;font-weight:bold;background:rgba(255,255,255,0.2);padding:12px 16px;border-radius:8px">${injection}</div>
</div>

<!-- TASKS -->
<div style="background:#f8f9fa;border-radius:10px;padding:20px;margin:20px 0">
  <h2 style="color:#34495e;margin:0 0 15px;font-size:18px;border-left:4px solid #3498db;padding-left:12px">✅ Today's Tasks (${tasks.total})</h2>
  <div style="color:#7f8c8d;font-size:12px;margin-bottom:10px">New today or due today</div>
  ${tasks.tasks.length === 0 ? '<div style="color:#95a5a6;font-style:italic">No new tasks or tasks due today 🎉</div>' : taskRows}
</div>

<!-- MEETINGS -->
<div style="background:#f8f9fa;border-radius:10px;padding:20px;margin:20px 0">
  <h2 style="color:#34495e;margin:0 0 15px;font-size:18px;border-left:4px solid #9b59b6;padding-left:12px">📅 Today's Meetings (${meetings.length})</h2>
  ${meetings.length === 0 ? '<div style="color:#95a5a6;font-style:italic">No meetings today 🎉</div>' : meetingRows}
</div>

<!-- DRAFTS -->
<div style="background:#f8f9fa;border-radius:10px;padding:20px;margin:20px 0">
  <h2 style="color:#34495e;margin:0 0 10px;font-size:18px;border-left:4px solid #2ecc71;padding-left:12px">✍️ New Drafts Today</h2>
  <div style="font-size:40px;font-weight:bold;color:#3498db">${draftCount}</div>
  <div style="color:#7f8c8d;font-size:13px">draft emails created today across all accounts</div>
</div>

<div style="background:#f8f9fa;border-radius:10px;padding:20px;margin:20px 0">
  <h2 style="color:#34495e;margin:0 0 10px;font-size:18px;border-left:4px solid #f39c12;padding-left:12px">🤖 AI Cost & Token Usage</h2>
  <pre style="background:#ecf0f1;padding:15px;border-radius:8px;white-space:pre-wrap;word-wrap:break-word;font-size:12px;color:#333;">${aiCostReport}</pre>
</div>

<div style="margin-top:30px;padding-top:15px;border-top:1px solid #ddd;color:#aaa;font-size:12px;text-align:center">
  Generated by Optimus · ${toCST(new Date())} CST · Have a productive day 🚀
</div>
</body></html>`;
}

// ── Main ──────────────────────────────────────────────────────────────────────
async function main() {
  console.log('\n📊 Daily Summary Generator');
  console.log('════════════════════════════════════════════════════');

  const day = getDayOfWeek();
  console.log(`📅 Day: ${day}`);

  console.log('📋 Fetching tasks...');
  const tasks = await getTasks();
  console.log(`   ✓ ${tasks.total} active tasks`);

  console.log('📅 Fetching today\'s meetings...');
  const meetings = await getMeetings();
  console.log(`   ✓ ${meetings.length} meetings`);

  console.log('✍️  Counting new drafts today...');
  const draftCount = await getNewDraftsToday();
  console.log(`   ✓ ${draftCount} new drafts today`);

  console.log('🧠 Fetching AI Cost Report...');
  const aiCostReport = await getAICostSummary();
  console.log('   ✓ AI Cost Report generated');

  console.log('📝 Building email...');
  const html = buildHTML(day, tasks, meetings, draftCount, aiCostReport);
  const subject = `📊 Daily Summary – ${formatDate(new Date())}`;

  console.log('📤 Sending to', RECIPIENT, '...');
  const client = new GraphClient(SUMMARY_ACCOUNT);
  await client.request('POST', '/me/sendMail', {
    message: {
      subject,
      body: { contentType: 'HTML', content: html },
      toRecipients: [{ emailAddress: { address: RECIPIENT } }]
    },
    saveToSentItems: true
  });

  console.log('✅ Summary sent!\n');
  console.log(`   Tasks: ${tasks.total} | Meetings: ${meetings.length} | Drafts: ${draftCount}`);
}

module.exports = { main };
if (require.main === module) main().catch(e => { console.error('❌', e.message); process.exit(1); });
