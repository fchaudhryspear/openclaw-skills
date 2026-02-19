#!/usr/bin/env node
// email-to-tasks.js — Scan all inboxes → extract tasks → create in Credologi To Do
// Ported from clawd old/skills/msgraph/email-to-tasks.js to use client credentials

const { GraphClient, listAccounts } = require('./lib/graph');
const { complete } = require('./lib/ai');

const TASK_ACCOUNT = 'credologi'; // All tasks land here
const DEFAULT_HOURS = 12;

const args = Object.fromEntries(
  process.argv.slice(2).reduce((acc, v, i, arr) => {
    if (v.startsWith('--')) acc.push([v.slice(2), arr[i + 1] || true]);
    return acc;
  }, [])
);
const HOURS = parseInt(args.hours) || DEFAULT_HOURS;
const DRY_RUN = args['dry-run'] === true || args['dry-run'] === 'true';
const VERBOSE = args.verbose === true || args.verbose === 'true';
const ACCOUNT_FILTER = args.account || null;

function htmlToText(html) {
  return (html || '')
    .replace(/<style[^>]*>[\s\S]*?<\/style>/gi, '')
    .replace(/<script[^>]*>[\s\S]*?<\/script>/gi, '')
    .replace(/<[^>]*>/g, ' ')
    .replace(/&nbsp;/g, ' ').replace(/&amp;/g, '&').replace(/&lt;/g, '<').replace(/&gt;/g, '>')
    .replace(/\s+/g, ' ').trim();
}

function levenshtein(a, b) {
  const m = [], al = a.length, bl = b.length;
  for (let i = 0; i <= bl; i++) m[i] = [i];
  for (let j = 0; j <= al; j++) m[0][j] = j;
  for (let i = 1; i <= bl; i++)
    for (let j = 1; j <= al; j++)
      m[i][j] = a[j - 1] === b[i - 1] ? m[i - 1][j - 1] : 1 + Math.min(m[i - 1][j - 1], m[i][j - 1], m[i - 1][j]);
  return m[bl][al];
}

function similarity(a, b) {
  const longer = a.length > b.length ? a : b;
  return longer.length === 0 ? 1 : (longer.length - levenshtein(longer, a.length > b.length ? b : a)) / longer.length;
}

async function extractTasks(subject, body, from) {
  const prompt = `Analyze this email and extract ONLY genuine actionable items requiring Faisal's direct action.

From: ${from}
Subject: ${subject}
Body: ${body.substring(0, 2000)}

Return ONLY a JSON array (or [] if none). Format:
[{"title":"Brief task","notes":"Context","dueDate":"YYYY-MM-DD or null","priority":"high or normal"}]

✅ CREATE tasks for: scheduling requests, document review, deliverables, follow-ups, client work, legal/compliance items
❌ SKIP: cold outreach, newsletters, FYI notifications, marketing, automated alerts, "can I send you a proposal"

JSON only, no other text:`;

  try {
    const raw = await complete(prompt, 'extract');
    const match = raw.match(/\[[\s\S]*\]/);
    if (!match) return [];
    const tasks = JSON.parse(match[0]);
    return Array.isArray(tasks) ? tasks : [];
  } catch (e) {
    console.error(`   ⚠️  Task extraction failed: ${e.message}`);
    return [];
  }
}

async function main() {
  console.log('\n📧 Email-to-Tasks Scanner');
  console.log('════════════════════════════════════════════════════');
  console.log(`🕐 Looking back: ${HOURS}h | Tasks → ${TASK_ACCOUNT}${DRY_RUN ? ' | DRY RUN' : ''}`);
  console.log('');

  // Load existing tasks for duplicate detection
  console.log('🔍 Loading existing tasks...');
  const taskClient = new GraphClient(TASK_ACCOUNT);
  let existingTasks = new Set();
  try {
    const tasks = await taskClient.listTasks(100);
    existingTasks = new Set(tasks.map(t => t.title.toLowerCase().replace(/[^\w\s]/g, '').replace(/\s+/g, ' ').trim()));
    console.log(`   Found ${existingTasks.size} existing tasks\n`);
  } catch (e) {
    console.warn(`   ⚠️  Could not load existing tasks: ${e.message}\n`);
  }

  const accounts = listAccounts().filter(a => !ACCOUNT_FILTER || a.account === ACCOUNT_FILTER);
  const since = new Date(Date.now() - HOURS * 3600000).toISOString();
  let totalEmails = 0, totalTasks = 0;

  for (const acc of accounts) {
    console.log(`📬 ${acc.account} (${acc.email})`);
    console.log('────────────────────────────────────────────────────');

    try {
      const client = new GraphClient(acc.account);
      const result = await client.getMessages('Inbox', `receivedDateTime ge ${since} and isRead eq false`, 20);
      const emails = result.value || [];

      if (emails.length === 0) {
        console.log(`   No unread emails in last ${HOURS}h\n`);
        continue;
      }
      console.log(`   Found ${emails.length} unread email(s)\n`);

      for (const email of emails) {
        const from = email.from?.emailAddress?.address || 'unknown';
        const subject = email.subject || '(no subject)';
        const body = htmlToText(email.body?.content || email.bodyPreview || '');
        if (body.length < 50) continue;

        if (VERBOSE) console.log(`   📧 "${subject}" | ${from}`);

        const tasks = await extractTasks(subject, body, from);
        if (tasks.length === 0) {
          if (VERBOSE) console.log(`      → no tasks\n`);
          totalEmails++;
          continue;
        }

        console.log(`   ✨ "${subject}" → ${tasks.length} task(s):`);

        for (const task of tasks) {
          const norm = task.title.toLowerCase().replace(/[^\w\s]/g, '').replace(/\s+/g, ' ').trim();
          if (existingTasks.has(norm)) { console.log(`      ⊘ "${task.title}" (duplicate)`); continue; }

          let isDupe = false;
          for (const ex of existingTasks) {
            if (similarity(norm, ex) > 0.82) { isDupe = true; break; }
          }
          if (isDupe) { console.log(`      ⊘ "${task.title}" (similar exists)`); continue; }

          console.log(`      • ${task.title}${task.priority === 'high' ? ' ❗' : ''}`);

          if (!DRY_RUN) {
            try {
              await taskClient.createTask(task);
              existingTasks.add(norm);
              totalTasks++;
              console.log(`        ✓ Created in ${TASK_ACCOUNT}`);
            } catch (e) {
              console.log(`        ❌ Failed: ${e.message}`);
            }
          } else {
            console.log(`        [DRY RUN]`);
          }
        }
        console.log('');
        totalEmails++;
      }
    } catch (e) {
      console.error(`   ❌ Error scanning ${acc.account}: ${e.message}\n`);
    }
  }

  console.log('════════════════════════════════════════════════════');
  console.log(`✅ Done — ${accounts.length} accounts, ${totalEmails} emails processed, ${totalTasks} tasks created\n`);
  return { emails: totalEmails, tasks: totalTasks };
}

module.exports = { main };
if (require.main === module) main().catch(e => { console.error('Fatal:', e.message); process.exit(1); });
