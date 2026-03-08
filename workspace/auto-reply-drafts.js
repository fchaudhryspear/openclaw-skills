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
  const subjectLower = (subject || '').toLowerCase();
  const bodyLower = (body || '').toLowerCase();
  
  // PRE-FILTER: Auto-skip common non-actionable email types BEFORE AI analysis
  const skipPatterns = [
    // Bank/Financial Statements
    'statement is now available',
    'paperless statement',
    'your statement',
    'account summary',
    'transaction alert',
    'payment received',
    'payment confirmation',
    'receipt for your purchase',
    'invoice #',
    
    // Marketing/Sales
    'exclusive offer',
    'limited time',
    'special promotion',
    'meetings availability',
    'schedule a call',
    'introductory call',
    'discovery call',
    'partnership opportunity',
    'we would love to connect',
    'would you be interested',
    
    // Automated Notifications
    'no reply needed',
    'this is an automated',
    'please do not reply',
    'newsletter',
    'digest',
    'weekly roundup',
    'unsubscribe',
    
    // Informational Only
    'fyi',
    'for your information',
    'just sharing',
    ' heads up'
  ];
  
  for (const pattern of skipPatterns) {
    if (subjectLower.includes(pattern) || bodyLower.includes(pattern)) {
      console.log(`   → Skipped (pattern match: "${pattern}")`);
      return { requiresResponse: false };
    }
  }
  
  // AI ANALYSIS: Check for actual questions requiring response
  const prompt = `Does this email contain direct questions or requests that require an action/response from Faisal?

Subject: ${subject}
Body: ${body.substring(0, 1500)}

STRICT SKIP LIST - Return requiresResponse: false for:
- Bank statements, transaction confirmations, receipts
- Marketing/sales emails, meeting solicitations from strangers
- Newsletters, automated notifications, "no reply needed"
- Purely informational emails (FYI, just sharing, heads up)
- Cold outreach, sponsorship requests, partnership pitches

Return JSON only (no explanation):
{"requiresResponse":true/false,"questions":["q1","q2"],"context":"brief context if true"}

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

async function generateDraft(subject, body, senderName, stylesamples, questions, context, accountName) {
  const prompt = `Draft an email reply on behalf of Faisal (Fas). Match his writing style EXACTLY.

=== FAISAL'S WRITING STYLE (ANALYZE THESE PATTERNS) ===
${stylesamples.substring(0, 3000)}
=== END SAMPLES ===

Key patterns to match:
1. EXTREMELY CONCISE - 1-3 lines max, often just 1 sentence
2. NO FLUFF - No "Hope you're doing well", "Thanks for reaching out", etc.
3. DIRECT START - Often begins immediately with answer/action (no formal greeting)
4. SHORT SENTENCES - Use fragments, not complete sentences where possible
5. ACTION-ORIENTED - "Approved.", "We need...", "Send it to...", "I can't do..."
6. CASUAL TONE - "Really sorry bro", "LOVE THAT!!!", "Got it. Thanks."
7. SIGN-OFF: Just "Faisal" or "Faisal Chaudhry" followed by company signature block
8. NO EXCESSIVE PUNCTUATION beyond what's in samples

Responding to:
From: ${senderName}
Subject: ${subject}
Body: ${body.substring(0, 1500)}

Questions to address (be brief):
${questions.map((q, i) => `${i + 1}. ${q}`).join('\n')}
Context: ${context}

Account: ${accountName}

CRITICAL INSTRUCTIONS:
- MAXIMUM 2-3 sentences total
- NO greeting like "Hi" or "Hello" unless absolutely necessary
- Get straight to the point
- Use "Approved." or "Confirmed." for approvals
- Use "I can't do [day]. How does [other day] look?" for scheduling conflicts
- Match the exact sign-off format from the samples for ${accountName}
- Return ONLY the plain text email body (no subject line):

EXAMPLE GOOD RESPONSES:
"Approved.\n\nFaisal"
"I can't do Friday we can do Thursday or we can do Monday.\n\nFaisal Chaudhry"
"LOVE THAT!!!\n\nCongrats!!\n\nFaisal Chaudhry"
"Got it. Thanks.\n\nFaisal"
"What's the flight number details?\n\nFaisal"
"Really sorry bro; can you send me all of 2011 for revenue and expenses.\n\nFaisal"
"Documents evidencing the commissions received from AT&T, Avant, Coresite, CRT, Intelysis, Telrus, Verizon, and Redstorm for the period of time April 1, 2024 to the present.\n\nThis is the doc, but I don't think we should share it.\n\nFaisal"
"Send it to dallas partners LLC\nAs an ACH\n\nUse the 1700 Pacific Dallas address.\n\nFaisal Chaudhry"
"Hi,\n\nWe need someone from the Snowflake API team to help us create an API to snowflake. We are ready to build it. We want to use the Client ID as the identifier to pull data. We will be passing multiple clients on one API call.\n\nThanks.\n\nFaisal Chaudhry"
"Ramadan Mubarak guys!\n\nFaisal Chaudhry"
"I apologize; my YPO forum has our retreat from May 29-June 1st. I didn't realize it overlapped. I will not able to attend.\n\nFaisal"
"My Monday is wide open.\n\nFaisal"
"I'm on depo all day tomorrow. How does Monday look?\n\nFaisal"
"Do you have this bank account linked to my quickbooks?\nOnline Banking transfer from CHK 2560\n\nFaisal"
"Yes approved to remove.\n\nFaisal Chaudhry"
"We can remove it.\n\nFaisal Chaudhry"
"update to percentages in RPM system for referral champions - email key shows in writing she said her commission was 25% down from 50%. She is suing for 50%.Re- June Paycheck.eml Re- please send Dig.io sub agent contracts.eml Re- marketing requests for Di\n\nFaisal"

Return ONLY the plain text email body:`;

  const response = await complete(prompt, 'draft');
  
  // Create HTML reply with original email appended below
  const replyHtml = '<p>' + response.replace(/\n\n/g, '</p><p>').replace(/\n/g, '<br>') + '</p>';
  
  // Original email separator and content
  const originalHtml = `
<hr style="border: none; border-top: 1px solid #ccc; margin: 20px 0;">
<div style="background-color: #f5f5f5; padding: 15px; border-left: 3px solid #ddd; margin-top: 20px;">
<p style="margin: 0 0 10px 0; font-size: 13px; color: #666;"><strong>Original Message:</strong></p>
<p style="margin: 0 0 5px 0; font-size: 13px;"><strong>From:</strong> ${senderName}</p>
<p style="margin: 0 0 5px 0; font-size: 13px;"><strong>Subject:</strong> ${subject}</p>
<p style="margin: 0 0 10px 0; font-size: 13px;"><strong>Date:</strong> ${(new Date()).toLocaleString()}</p>
<hr style="border: none; border-top: 1px dashed #ccc; margin: 10px 0;">
<div style="font-size: 14px; line-height: 1.6; color: #333; white-space: pre-wrap;">${body}</div>
</div>`;

  return replyHtml + originalHtml;
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
        const html = await generateDraft(subject, body, from, style, analysis.questions, analysis.context || '', acc.account);
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
