#!/usr/bin/env node
// calendar-sync.js — Sync busy blocks across all 7 calendars
// Ported from clawd old/skills/msgraph/calendar-sync.js

const { GraphClient, listAccounts } = require('./lib/graph');

const SYNC_MARKER = 'X'; // Subject prefix for busy blockers
const SYNC_DAYS = 14;

const args = process.argv.slice(2);
const DRY_RUN = args.includes('--dry-run');
const VERBOSE = args.includes('--verbose') || args.includes('-v');
const DAYS = (() => { const i = args.indexOf('--days'); return i !== -1 ? parseInt(args[i + 1]) : SYNC_DAYS; })();

const ACCOUNT_NAMES = {
  credologi: 'Credologi', flobase: 'Flobase', fcrpcapital: 'FCR Capital',
  utilityvalet: 'Utility Valet', starship: 'Starship', dallaspartners: 'Dallas Partners', spearhead: 'Spearhead'
};

function mergeSlots(events) {
  if (!events.length) return [];
  const sorted = [...events].sort((a, b) => new Date(a.start) - new Date(b.start));
  const merged = [{
    ...sorted[0],
    eventIds: sorted[0].id ? [sorted[0].id] : []
  }];
  for (let i = 1; i < sorted.length; i++) {
    const cur = merged[merged.length - 1];
    const next = sorted[i];
    if (new Date(next.start) <= new Date(cur.end)) {
      if (new Date(next.end) > new Date(cur.end)) cur.end = next.end;
      if (!cur.sources.includes(next.source)) cur.sources.push(next.source);
      if (next.id && !cur.eventIds.includes(next.id)) cur.eventIds.push(next.id);
    } else {
      merged.push({
        ...next,
        eventIds: next.id ? [next.id] : []
      });
    }
  }
  return merged;
}

async function main() {
  console.log('\n📅 Calendar Sync');
  console.log('════════════════════════════════════════════════════');
  console.log(`📆 Syncing ${DAYS} days ahead across all accounts${DRY_RUN ? ' | DRY RUN' : ''}`);
  console.log('');

  const accounts = listAccounts();
  const allEvents = []; // { account, start, end }

  // Step 1: Collect all real events from all accounts
  console.log('📥 Collecting events...');
  for (const acc of accounts) {
    try {
      const client = new GraphClient(acc.account);
      const result = await client.getUpcomingEvents(DAYS);
      const events = (result.value || []).filter(e => !e.subject?.startsWith(SYNC_MARKER) && !e.isAllDay);

      for (const e of events) {
        if (e.start?.dateTime && e.end?.dateTime && e.id) {
          allEvents.push({ account: acc.account, start: e.start.dateTime, end: e.end.dateTime, id: e.id });
        }
      }
      console.log(`   ✓ ${acc.account}: ${events.length} real event(s)`);
    } catch (e) {
      console.error(`   ❌ ${acc.account}: ${e.message}`);
    }
  }
  console.log('');

  let created = 0, deleted = 0;

  // Step 2: For each account, sync busy blockers from other accounts
  for (const acc of accounts) {
    console.log(`────────────────────────────────────────────────────`);
    console.log(`🔄 ${ACCOUNT_NAMES[acc.account] || acc.account}`);

    const client = new GraphClient(acc.account);

    // Get events from OTHER accounts, build merged slots
    const otherEvents = allEvents
      .filter(e => e.account !== acc.account)
      .map(e => ({ start: e.start, end: e.end, source: ACCOUNT_NAMES[e.account] || e.account, sources: [ACCOUNT_NAMES[e.account] || e.account] }));

    const slots = mergeSlots(otherEvents);

    // Remove existing sync blockers
    try {
      const existing = await client.getUpcomingEvents(DAYS);
      const blockers = (existing.value || []).filter(e => e.subject === SYNC_MARKER || e.subject?.startsWith(SYNC_MARKER + ' '));
      if (blockers.length > 0) {
        if (!DRY_RUN) {
          for (const b of blockers) {
            await client.deleteEvent(b.id);
            deleted++;
          }
        } else {
          deleted += blockers.length;
        }
        console.log(`   🗑  Removed ${blockers.length} old blocker(s)`);
      }
    } catch (e) {
      console.error(`   ⚠️  Could not clean old blockers: ${e.message}`);
    }

    if (slots.length === 0) {
      console.log(`   ℹ️  No busy slots from other accounts\n`);
      continue;
    }

    // Create fresh blockers
    for (const slot of slots) {
      if (VERBOSE) {
        const start = new Date(slot.start).toLocaleString('en-US', { timeZone: 'America/Chicago' });
        const end = new Date(slot.end).toLocaleString('en-US', { timeZone: 'America/Chicago' });
        console.log(`   📌 ${start} → ${end} (from ${slot.sources.join(', ')})`);
      }

      if (!DRY_RUN) {
        try {
          await client.createEvent({
            subject: SYNC_MARKER,
            start: { dateTime: slot.start, timeZone: 'UTC' },
            end: { dateTime: slot.end, timeZone: 'UTC' },
            showAs: 'busy',
            isReminderOn: false,
            sensitivity: 'normal',
            body: { contentType: 'text', content: `Busy in: ${slot.sources.join(', ')}` }
          });
          created++;
        } catch (e) {
          console.error(`   ❌ Failed to create blocker: ${e.message}`);
        }
      } else {
        created++;
      }
    }
    console.log(`   ✅ ${slots.length} busy blocker(s) ${DRY_RUN ? 'would be created' : 'created'}\n`);
  }

  console.log('════════════════════════════════════════════════════');
  console.log(`✅ Done — Created: ${created}, Deleted: ${deleted}\n`);
  return { created, deleted };
}

module.exports = { main };
if (require.main === module) main().catch(e => { console.error('Fatal:', e.message); process.exit(1); });
