#!/usr/bin/env node
// office365-runner.js — Master orchestrator: email-to-tasks + calendar-sync + auto-reply-drafts
// Run: node office365-runner.js [--dry-run] [--skip-tasks] [--skip-calendar] [--skip-drafts]

const args = process.argv.slice(2);
const DRY_RUN = args.includes('--dry-run');
const SKIP_TASKS = args.includes('--skip-tasks');
const SKIP_CALENDAR = args.includes('--skip-calendar');
const SKIP_DRAFTS = args.includes('--skip-drafts');

async function run() {
  const start = Date.now();
  const timestamp = new Date().toLocaleString('en-US', { timeZone: 'America/Chicago' });
  console.log('\n╔════════════════════════════════════════════════════╗');
  console.log('║         Office 365 Automation Runner               ║');
  console.log('╚════════════════════════════════════════════════════╝');
  console.log(`⏱  Started: ${timestamp} CST${DRY_RUN ? ' [DRY RUN]' : ''}`);
  console.log('');

  const results = { tasks: null, calendar: null, drafts: null };

  // ── 1. Email to Tasks ────────────────────────────────────────────────────────
  if (!SKIP_TASKS) {
    console.log('\n[1/3] EMAIL → TASKS');
    try {
      const { main } = require('./email-to-tasks');
      results.tasks = await main();
    } catch (e) {
      console.error(`❌ Email-to-tasks failed: ${e.message}`);
      results.tasks = { error: e.message };
    }
  } else {
    console.log('\n[1/3] EMAIL → TASKS (skipped)');
  }

  // ── 2. Calendar Sync ─────────────────────────────────────────────────────────
  if (!SKIP_CALENDAR) {
    console.log('\n[2/3] CALENDAR SYNC');
    try {
      const { main } = require('./calendar-sync');
      results.calendar = await main();
    } catch (e) {
      console.error(`❌ Calendar sync failed: ${e.message}`);
      results.calendar = { error: e.message };
    }
  } else {
    console.log('\n[2/3] CALENDAR SYNC (skipped)');
  }

  // ── 3. Auto-Reply Drafts ─────────────────────────────────────────────────────
  if (!SKIP_DRAFTS) {
    console.log('\n[3/3] AUTO-REPLY DRAFTS');
    try {
      const { main } = require('./auto-reply-drafts');
      results.drafts = await main();
    } catch (e) {
      console.error(`❌ Auto-reply drafts failed: ${e.message}`);
      results.drafts = { error: e.message };
    }
  } else {
    console.log('\n[3/3] AUTO-REPLY DRAFTS (skipped)');
  }

  // ── Summary ──────────────────────────────────────────────────────────────────
  const elapsed = Math.round((Date.now() - start) / 1000);
  console.log('\n╔════════════════════════════════════════════════════╗');
  console.log('║                    SUMMARY                         ║');
  console.log('╚════════════════════════════════════════════════════╝');
  if (results.tasks) {
    if (results.tasks.error) console.log(`📧 Email→Tasks:    ❌ ${results.tasks.error}`);
    else console.log(`📧 Email→Tasks:    ${results.tasks.tasks} task(s) created from ${results.tasks.emails} emails`);
  }
  if (results.calendar) {
    if (results.calendar.error) console.log(`📅 Calendar Sync:  ❌ ${results.calendar.error}`);
    else console.log(`📅 Calendar Sync:  ${results.calendar.created} blocker(s) created, ${results.calendar.deleted} removed`);
  }
  if (results.drafts) {
    if (results.drafts.error) console.log(`✉️  Auto-Drafts:    ❌ ${results.drafts.error}`);
    else console.log(`✉️  Auto-Drafts:    ${results.drafts.drafts} draft(s) created`);
  }
  console.log(`⏱  Completed in ${elapsed}s\n`);
}

run().catch(e => { console.error('\n❌ Runner failed:', e.message); process.exit(1); });
