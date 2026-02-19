#!/usr/bin/env node
// auto-reply-drafts.js — Detect emails needing replies → generate drafts (not sent)
// Ported from clawd old/skills/msgraph/auto-reply-drafts.js

const fs = require('fs');
const path = require('path');
const { GraphClient, listAccounts } = require('./lib/graph');
const { complete } = require('./lib/ai');

const CACHE_FILE = path.join(__dirname, 'style-cache.json');
const CACHE_TTL_MS = 7 * 24 * 3600 * 1000; // 7 days
const DEFAULT_HOURS = 48;

const args = process.argv.slice(2);
const DRY_RUN = args.includes('--dry-run');
const VERBOSE = args.includes('--verbose') || args.includes('-v');
const HOURS = (() => { const i = args.indexOf('--hours'); return i !== -1 ? parseInt(args[i + 1]) : DEFAULT_HOURS; })();
const LIMIT = (() => { const i = args.indexOf('--limit'); return i !== -1 ? parseInt(args[i + 1]) : 10; })();
const ACCOUNT_FILTER = (() => { const i = args.indexOf('--account'); return i !== -1 ? args[i + 1] : null; })();

function htmlToText(html) {
  return (html || '')
    .replace(/<style[^>]*>[\s\S]*?<\/style>/gi, '')
    .replace(/<script[^>]*>[\s\S]*?<\/script>/gi, '')
    .replace(/<[^>]*>/g, ' ')
    .replace(/&nbsp;/g, ' ').replace(/&amp;/g, '&').replace(/&lt;/g, '<').replace(/&gt;/g, '>')
    .replace(/\s+/g, ' ').trim();
}

function loadStyleCache() {
  try {
    if (!fs.existsSync(CACHE_FILE)) return {};
    return JSON.parse(fs.readFileSync(CACHE_FILE, 'utf8'));
  } catch { return {}; }
}

function saveStyleCache(cache) {
  fs.writeFileSync(CACHE_FILE, JSON.stringify(cache, null, 2));
}

async function getWritingStyle(accountName) {
  const cache = loadStyleCache();
  const cached = cache[accountName];
  if (cached && Date.now() - cached.ts < CACHE_TTL_MS) {
    console.log(`   ✓ Using cached style (${Math.floor((Date.now() - cached.ts) / 86400000)}d old)`);
    return cached.style;
  }

  console.log(`   📚 Analyzing sent emails for style...`);
  const client = new GraphClient(accountName);
  let sentEmails;
  try {
    const result = await client.getSentMessages(30);
    sentEmails = result.value || [];
  } catch (e) {
    console.warn(`   ⚠️  Could not fetch sent emails: ${e.message}`);
    return null;
  }

  const samples = sentEmails
    .map(m => htmlToText(m.body?.content || ''))
    .filter(s => s.length > 100)
    .slice(0, 10)
    .map(s => s.substring(0, 800));

  if (!samples.length) { console.warn('   ⚠️  No sent email samples found'); return null; }

  const style = samples.join('\n\n---\n\n');
  const newCache = loadStyleCache();
  newCache[accountName] = { style, ts: Date.now() };
  saveStyleCache(newCache);
  console.log(`   ✓ Style analyzed from ${samples.length} sent emails (cached 7d)`);
  return style;
}

async function detectQuestions(subject, body) {
  const prompt = `Does this email contain direct questions that require a response from the recipient?

Subject: ${subject}
Body: ${body.substring(0, 1500)}

Return JSON only:
{"requiresResponse":true/false,"questions":["q1","q2"],"context":"what they're asking about"}

Skip: FYI emails, automated notifications, newsletters, cold outreach.
JSON only:`;

  try {
    const raw = await complete(prompt, 'extract');
    const match = raw.match(/\{[\s\S]*\}/);
    if (!match) return { requiresResponse: false };
    return JSON.parse(match[0]);
  } catch (e) {
    return { requiresResponse: false };
  }
}

async function generateDraft(subject, body, senderName, stylesamples, questions, context) {
  const prompt = `Draft an email reply on behalf of Faisal (Fas). Match his writing style from these samples:

=== WRITING STYLE SAMPLES ===
${stylesamples.substring(0, 3000)}
=== END SAMPLES ===

Responding to:
From: ${senderName}
Subject: ${subject}
Body: ${body.substring(0, 1500)}

Questions to address:
${questions.map((q, i) => `${i + 1}. ${q}`).join('\n')}
Context: ${context}

Instructions:
- Match Fas's tone exactly (casual, direct, no fluff)
- Address all questions concisely
- Use appropriate greeting and sign-off
- Return ONLY the plain text email body (no subject line):`;

  const response = await complete(prompt, 'draft');
  // Wrap in simple HTML
  const html = '<p>' + response.replace(/\n\n/g, '</p><p>').replace(/\n/g, '<br>') + '</p>';
  return html;
}

async function main() {
  console.log('\n✉️  Auto-Reply Drafts Generator');
  console.log('════════════════════════════════════════════════════');
  console.log(`🕐 Looking back: ${HOURS}h | Max ${LIMIT} per account${DRY_RUN ? ' | DRY RUN' : ''}`);
  console.log('');

  const accounts = listAccounts().filter(a => !ACCOUNT_FILTER || a.account === ACCOUNT_FILTER);
  const since = new Date(Date.now() - HOURS * 3600000).toISOString();
  let totalDrafts = 0;

  for (const acc of accounts) {
    console.log(`\n📬 ${acc.account} (${acc.email})`);
    console.log('────────────────────────────────────────────────────');

    // Get writing style for this account
    const style = await getWritingStyle(acc.account);
    if (!style) { console.log('   ⏭  Skipping (no writing style available)\n'); continue; }

    const client = new GraphClient(acc.account);
    let emails;
    try {
      const result = await client.getMessages('Inbox', `receivedDateTime ge ${since} and isRead eq false`, LIMIT);
      emails = result.value || [];
    } catch (e) {
      console.error(`   ❌ Could not fetch emails: ${e.message}\n`); continue;
    }

    if (emails.length === 0) { console.log(`   No unread emails in last ${HOURS}h\n`); continue; }
    console.log(`   Found ${emails.length} unread email(s)\n`);

    for (const email of emails) {
      const from = email.from?.emailAddress?.name || email.from?.emailAddress?.address || 'Unknown';
      const subject = email.subject || '(no subject)';
      const body = htmlToText(email.body?.content || '');
      if (body.length < 80) continue;

      if (VERBOSE) console.log(`   📧 "${subject}" | ${from}`);

      const analysis = await detectQuestions(subject, body);
      if (!analysis.requiresResponse || !analysis.questions?.length) {
        if (VERBOSE) console.log(`      → no response needed\n`);
        continue;
      }

      console.log(`   ✨ "${subject}"`);
      console.log(`      From: ${from}`);
      console.log(`      Questions: ${analysis.questions.map((q, i) => `${i + 1}. ${q}`).join(' | ')}`);

      if (DRY_RUN) {
        console.log(`      [DRY RUN] Would create draft\n`);
        totalDrafts++;
        continue;
      }

      try {
        console.log(`      🤖 Generating draft...`);
        const html = await generateDraft(subject, body, from, style, analysis.questions, analysis.context || '');
        await client.createDraftReply(email.id, html);
        totalDrafts++;
        console.log(`      ✓ Draft saved to Drafts folder\n`);
      } catch (e) {
        console.log(`      ❌ Failed: ${e.message}\n`);
      }
    }
  }

  console.log('════════════════════════════════════════════════════');
  console.log(`✅ Done — ${totalDrafts} draft(s) created\n`);
  if (totalDrafts > 0) console.log('💡 Check Drafts folder in each mailbox to review before sending.\n');
  return { drafts: totalDrafts };
}

module.exports = { main };
if (require.main === module) main().catch(e => { console.error('Fatal:', e.message); process.exit(1); });
