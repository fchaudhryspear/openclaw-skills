#!/usr/bin/env node
// daily-summary.js — Morning summary email to faisal@credologi.com
// Sends: tasks, today's meetings, auto-reply draft count, injection schedule

const { GraphClient, listAccounts } = require('./lib/graph');

const SUMMARY_ACCOUNT = 'credologi';
const RECIPIENT = 'faisal@credologi.com';

// ── Injection Schedule ────────────────────────────────────────────────────────
const INJECTION_SCHEDULE = {
  Monday:    'MOTS-C (0.4mL) + AOD-9604 (0.4mL)',
  Tuesday:   'MOTS-C (0.4mL) + AOD-9604 (0.4mL)',
  Wednesday: 'Retatrutide (0.15mL) + AOD-9604 (0.4mL)',
  Thursday:  'MOTS-C (0.4mL) + AOD-9604 (0.4mL)',
  Friday:    'MOTS-C (0.4mL) + AOD-9604 (0.4mL)',
  Saturday:  'Retatrutide (0.15mL) + AOD-9604 (0.4mL)',
  Sunday:    'MOTS-C (0.4mL) + AOD-9604 (0.4mL)'
};

function toCST(date) {
  return new Date(date).toLocaleString('en-US', { timeZone: 'America/Chicago' });
}
function formatTime(dt) {
  return new Date(dt).toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit', hour12: true, timeZone: 'America/Chicago' });
}
function formatDate(dt) {
  return new Date(dt).toLocaleDateString('en-US', { weekday: 'long', month: 'long', day: 'numeric', year: 'numeric', timeZone: 'America/Chicago' });
}
function getDayOfWeek() {
  return new Date().toLocaleDateString('en-US', { weekday: 'long', timeZone: 'America/Chicago' });
}

// ── Data Collectors ───────────────────────────────────────────────────────────
async function getTasks() {
  try {
    const client = new GraphClient(SUMMARY_ACCOUNT);
    const tasks = await client.listTasks(50);
    const incomplete = tasks.filter(t => t.status !== 'completed');
    const high = incomplete.filter(t => t.importance === 'high');
    const normal = incomplete.filter(t => t.importance !== 'high');
    // Sort: high priority first, then by due date
    const sorted = [
      ...high.sort((a, b) => (a.dueDateTime?.dateTime || 'z') < (b.dueDateTime?.dateTime || 'z') ? -1 : 1),
      ...normal.sort((a, b) => (a.dueDateTime?.dateTime || 'z') < (b.dueDateTime?.dateTime || 'z') ? -1 : 1)
    ];
    return { tasks: sorted, total: incomplete.length };
  } catch (e) {
    console.error('Tasks error:', e.message);
    return { tasks: [], total: 0 };
  }
}

async function getMeetings() {
  const meetings = [];
  const accounts = listAccounts();
  const todayStart = new Date(); todayStart.setHours(0,0,0,0);
  const todayEnd = new Date(); todayEnd.setHours(23,59,59,999);

  for (const acc of accounts) {
    try {
      const client = new GraphClient(acc.account);
      const result = await client.request('GET',
        `/me/calendar/calendarView?startDateTime=${todayStart.toISOString()}&endDateTime=${todayEnd.toISOString()}&$top=20&$select=subject,start,end,location,isAllDay&$orderby=start/dateTime`
      );
      for (const e of (result.value || [])) {
        if (e.subject === 'X' || e.subject?.startsWith('X ')) continue; // skip busy blockers
        if (e.isAllDay) continue;
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

async function getDraftCount() {
  let total = 0;
  const accounts = listAccounts();
  for (const acc of accounts) {
    try {
      const client = new GraphClient(acc.account);
      const result = await client.request('GET', `/me/mailFolders/Drafts/messages?$top=1&$count=true&$select=id`);
      total += result['@odata.count'] || (result.value?.length || 0);
    } catch (e) { /* skip */ }
  }
  return total;
}

// ── HTML Generator ────────────────────────────────────────────────────────────
function buildHTML(day, tasks, meetings, draftCount) {
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
    const start = formatTime(m.start.dateTime);
    const end = formatTime(m.end.dateTime);
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
  <h2 style="color:#34495e;margin:0 0 15px;font-size:18px;border-left:4px solid #3498db;padding-left:12px">✅ Active Tasks (${tasks.total})</h2>
  ${tasks.tasks.length === 0 ? '<div style="color:#95a5a6;font-style:italic">No active tasks 🎉</div>' : taskRows}
  ${tasks.total > 15 ? `<div style="color:#999;font-size:13px;margin-top:10px">+ ${tasks.total - 15} more tasks</div>` : ''}
</div>

<!-- MEETINGS -->
<div style="background:#f8f9fa;border-radius:10px;padding:20px;margin:20px 0">
  <h2 style="color:#34495e;margin:0 0 15px;font-size:18px;border-left:4px solid #9b59b6;padding-left:12px">📅 Today's Meetings (${meetings.length})</h2>
  ${meetings.length === 0 ? '<div style="color:#95a5a6;font-style:italic">No meetings today 🎉</div>' : meetingRows}
</div>

<!-- DRAFTS -->
<div style="background:#f8f9fa;border-radius:10px;padding:20px;margin:20px 0">
  <h2 style="color:#34495e;margin:0 0 10px;font-size:18px;border-left:4px solid #2ecc71;padding-left:12px">✍️ Draft Emails in Mailboxes</h2>
  <div style="font-size:40px;font-weight:bold;color:#3498db">${draftCount}</div>
  <div style="color:#7f8c8d;font-size:13px">across all 7 accounts — review & send what's ready</div>
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

  console.log('✍️  Counting drafts...');
  const draftCount = await getDraftCount();
  console.log(`   ✓ ${draftCount} drafts across all accounts`);

  console.log('📝 Building email...');
  const html = buildHTML(day, tasks, meetings, draftCount);
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
