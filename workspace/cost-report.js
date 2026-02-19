#!/usr/bin/env node
// cost-report.js — Daily/weekly AI cost report from automation runs
// Usage: node cost-report.js [daily|weekly|monthly]

const fs = require('fs');
const path = require('path');

const COST_LOG = path.join(__dirname, 'logs', 'ai-costs.jsonl');

// Current model pricing per 1M tokens
const PRICING = {
  'gemini-2.0-flash':            { input: 0.10,  output: 0.40,  name: 'Gemini Flash' },
  'gemini-2.0-flash-lite':       { input: 0.075, output: 0.30,  name: 'Gemini Lite' },
  'gemini-2.5-flash':            { input: 0.10,  output: 0.40,  name: 'Gemini 2.5 Flash' },
  'grok-4-1-fast-non-reasoning': { input: 2.00,  output: 10.00, name: 'Grok Fast' },
  'grok-3-mini':                 { input: 0.30,  output: 0.60,  name: 'Grok Mini' },
  'claude-sonnet-4-6':           { input: 3.00,  output: 15.00, name: 'Claude Sonnet' },
  'claude-opus-4-6':             { input: 5.00,  output: 25.00, name: 'Claude Opus' },
  'kimi-k2.5':                   { input: 0.60,  output: 2.50,  name: 'Kimi K2.5' },
};

function daysAgo(n) {
  const d = new Date();
  d.setDate(d.getDate() - n);
  return d.toISOString().split('T')[0];
}

function loadEntries(fromDate, toDate) {
  if (!fs.existsSync(COST_LOG)) return [];
  return fs.readFileSync(COST_LOG, 'utf8')
    .split('\n').filter(Boolean)
    .map(l => { try { return JSON.parse(l); } catch { return null; } })
    .filter(e => e && e.date >= fromDate && e.date <= toDate);
}

function aggregate(entries) {
  const byModel = {}, byScript = {};
  let totalCost = 0, totalIn = 0, totalOut = 0;

  for (const e of entries) {
    totalCost += e.cost || 0;
    totalIn += e.inputTokens || 0;
    totalOut += e.outputTokens || 0;

    const modelName = PRICING[e.model]?.name || e.model;
    if (!byModel[modelName]) byModel[modelName] = { cost: 0, calls: 0 };
    byModel[modelName].cost += e.cost || 0;
    byModel[modelName].calls++;

    const script = e.script?.replace('ai-', '') || 'unknown';
    if (!byScript[script]) byScript[script] = { cost: 0, calls: 0 };
    byScript[script].cost += e.cost || 0;
    byScript[script].calls++;
  }

  return { totalCost, totalIn, totalOut, byModel, byScript, count: entries.length };
}

function bar(pct, width = 12) {
  const f = Math.round((pct / 100) * width);
  return '█'.repeat(f) + '░'.repeat(width - f);
}

function fmt(n) { return `$${n.toFixed(4)}`; }
function fmtTokens(n) {
  if (n >= 1e6) return `${(n/1e6).toFixed(2)}M`;
  if (n >= 1e3) return `${(n/1e3).toFixed(1)}K`;
  return n.toString();
}

function buildReport(title, entries, dateRange) {
  if (entries.length === 0) {
    return `📊 ${title}\n${dateRange}\n\nNo automation runs logged yet. Costs will appear after the next email/calendar/reply run.`;
  }

  const agg = aggregate(entries);
  const lines = [`📊 ${title}`, dateRange, ''];

  // Totals
  lines.push(`💰 Total: ${fmt(agg.totalCost)}  |  ${fmtTokens(agg.totalIn + agg.totalOut)} tokens (${fmtTokens(agg.totalIn)} in / ${fmtTokens(agg.totalOut)} out)  |  ${agg.count} calls`);
  lines.push('');

  // By model
  lines.push('By Model:');
  const models = Object.entries(agg.byModel).sort((a, b) => b[1].cost - a[1].cost);
  for (const [model, data] of models) {
    const pct = agg.totalCost > 0 ? (data.cost / agg.totalCost) * 100 : 0;
    lines.push(`  ${bar(pct)} ${model.padEnd(18)} ${fmt(data.cost).padStart(9)}  (${data.calls} calls)`);
  }
  lines.push('');

  // By script/task
  lines.push('By Task:');
  const scripts = Object.entries(agg.byScript).sort((a, b) => b[1].cost - a[1].cost);
  for (const [script, data] of scripts) {
    const label = {
      'gemini': 'Email/Calendar AI', 'grok': 'Extraction/Draft AI',
      'email-to-tasks': 'Email→Tasks', 'auto-reply': 'Auto-Reply Drafts',
      'calendar-sync': 'Calendar Sync'
    }[script] || script;
    lines.push(`  ${label.padEnd(22)} ${fmt(data.cost).padStart(9)}  (${data.calls} calls)`);
  }

  // Monthly projection (from daily avg)
  if (agg.totalCost > 0) {
    const days = entries.reduce((s, e) => { s.add(e.date); return s; }, new Set()).size || 1;
    const dailyAvg = agg.totalCost / days;
    const projection = dailyAvg * 30;
    lines.push('');
    lines.push(`📈 Daily avg: ${fmt(dailyAvg)}  →  Monthly projection: $${projection.toFixed(2)}`);
  }

  return lines.join('\n');
}

function main() {
  const mode = process.argv[2] || 'daily';
  const today = new Date().toISOString().split('T')[0];
  let report;

  if (mode === 'weekly') {
    const from = daysAgo(7);
    const entries = loadEntries(from, today);
    report = buildReport('Weekly Cost Report', entries, `${from} → ${today}`);
  } else if (mode === 'monthly') {
    const now = new Date();
    const from = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-01`;
    const entries = loadEntries(from, today);
    const monthName = now.toLocaleDateString('en-US', { month: 'long', year: 'numeric' });
    report = buildReport(`Monthly Cost Report — ${monthName}`, entries, `${from} → ${today}`);
  } else {
    // Daily = yesterday's data
    const yesterday = daysAgo(1);
    const entries = loadEntries(yesterday, yesterday);
    report = buildReport(`Daily Cost Report — ${yesterday}`, entries, `Automation runs on ${yesterday}`);
  }

  console.log(report);
  return report;
}

module.exports = { main };
if (require.main === module) main();
