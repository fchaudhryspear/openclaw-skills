#!/usr/bin/env node
/**
 * Daily Token Usage Report
 * Generates comprehensive breakdown of token usage by model and task
 */

const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');

const COST_LOG = path.join(process.env.HOME, '.openclaw/workspace/ai-cost-tracker/logs/ai-costs.jsonl');
const DAILY_SUMMARY = path.join(process.env.HOME, '.openclaw/workspace/ai-cost-tracker/logs/daily-costs.json');

// Model pricing per 1M tokens
const PRICING = {
  'anthropic/claude-sonnet-4-5': { input: 3.00, output: 15.00, name: 'Claude Sonnet 4.5' },
  'kimi-k2.5': { input: 0.50, output: 2.00, name: 'Kimi K2.5' },
  'grok-4-fast-non-reasoning': { input: 0.10, output: 0.30, name: 'Grok Fast' },
  'google/gemini-2.0-flash-exp': { input: 0.15, output: 0.60, name: 'Gemini Flash' }
};

// Business-focused task categories
const TASK_CATEGORIES = {
  'email-to-tasks': { name: 'Office 365', emoji: '📧', category: 'office365' },
  'auto-reply-drafts-detect': { name: 'Office 365', emoji: '📧', category: 'office365' },
  'auto-reply-drafts-generate': { name: 'Office 365', emoji: '📧', category: 'office365' },
  'calendar-sync': { name: 'Office 365', emoji: '📅', category: 'office365' },
  'daily-summary': { name: 'Office 365', emoji: '📊', category: 'office365' },
  'conversation': { name: 'Conversations', emoji: '💬', category: 'conversations' },
  'crestron': { name: 'Crestron', emoji: '🏠', category: 'crestron' },
  'network': { name: 'Network', emoji: '🌐', category: 'network' },
  'unifi': { name: 'Network', emoji: '🌐', category: 'network' },
  'security-monitor': { name: 'Security', emoji: '🔒', category: 'security' }
};

function getTaskCategory(taskName) {
  if (TASK_CATEGORIES[taskName]) {
    return TASK_CATEGORIES[taskName];
  }
  // Check if task name contains keywords
  if (taskName.includes('crestron')) return { name: 'Crestron', emoji: '🏠', category: 'crestron' };
  if (taskName.includes('network') || taskName.includes('unifi')) return { name: 'Network', emoji: '🌐', category: 'network' };
  if (taskName.includes('email') || taskName.includes('calendar')) return { name: 'Office 365', emoji: '📧', category: 'office365' };
  return { name: taskName, emoji: '🔧', category: 'other' };
}

function getYesterday() {
  const d = new Date();
  d.setDate(d.getDate() - 1);
  return d.toISOString().split('T')[0];
}

function getDateDaysAgo(days) {
  const d = new Date();
  d.setDate(d.getDate() - days);
  return d.toISOString().split('T')[0];
}

function formatTokens(tokens) {
  if (tokens >= 1000000) return `${(tokens / 1000000).toFixed(2)}M`;
  if (tokens >= 1000) return `${(tokens / 1000).toFixed(1)}K`;
  return tokens.toString();
}

function formatCost(cost) {
  return `$${cost.toFixed(3)}`;
}

function getPercentChange(current, previous) {
  if (!previous || previous === 0) return null;
  const change = ((current - previous) / previous) * 100;
  if (Math.abs(change) < 0.1) return null;
  const arrow = change > 0 ? '📈' : '📉';
  return `${arrow} ${Math.abs(change).toFixed(0)}%`;
}

function readDailySummary() {
  try {
    if (!fs.existsSync(DAILY_SUMMARY)) return {};
    return JSON.parse(fs.readFileSync(DAILY_SUMMARY, 'utf8'));
  } catch (err) {
    console.error('Failed to read daily summary:', err.message);
    return {};
  }
}

function aggregateByModel(entries) {
  const byModel = {};
  
  entries.forEach(entry => {
    const model = entry.model || 'unknown';
    if (!byModel[model]) {
      byModel[model] = {
        input_tokens: 0,
        output_tokens: 0,
        total_tokens: 0,
        cost: 0,
        calls: 0
      };
    }
    
    byModel[model].input_tokens += entry.usage?.prompt_tokens || 0;
    byModel[model].output_tokens += entry.usage?.completion_tokens || 0;
    byModel[model].total_tokens += entry.usage?.total_tokens || 0;
    byModel[model].cost += entry.cost?.total || 0;
    byModel[model].calls += 1;
  });
  
  return byModel;
}

function aggregateByTask(entries) {
  const byTask = {};
  
  entries.forEach(entry => {
    const task = entry.script || 'unknown';
    if (!byTask[task]) {
      byTask[task] = {
        tokens: 0,
        cost: 0,
        calls: 0,
        models: {}
      };
    }
    
    byTask[task].tokens += entry.usage?.total_tokens || 0;
    byTask[task].cost += entry.cost?.total || 0;
    byTask[task].calls += 1;
    
    const model = entry.model || 'unknown';
    if (!byTask[task].models[model]) {
      byTask[task].models[model] = { tokens: 0, cost: 0 };
    }
    byTask[task].models[model].tokens += entry.usage?.total_tokens || 0;
    byTask[task].models[model].cost += entry.cost?.total || 0;
  });
  
  return byTask;
}

function getEntriesForDate(date) {
  if (!fs.existsSync(COST_LOG)) return [];
  
  const lines = fs.readFileSync(COST_LOG, 'utf8').split('\n').filter(l => l.trim());
  const entries = [];
  
  for (const line of lines) {
    try {
      const entry = JSON.parse(line);
      if (entry.date === date) {
        entries.push(entry);
      }
    } catch (err) {
      // Skip invalid lines
    }
  }
  
  return entries;
}

function generateReport() {
  const yesterday = getYesterday();
  const dayBefore = getDateDaysAgo(2);
  
  console.log('📊 Generating daily token usage report...');
  console.log(`   Date: ${yesterday}`);
  
  const summary = readDailySummary();
  const todayData = summary[yesterday];
  const yesterdayData = summary[dayBefore];
  
  if (!todayData) {
    return {
      date: yesterday,
      noData: true,
      message: 'No usage data recorded for yesterday. This is normal if no AI tasks ran.'
    };
  }
  
  // Get detailed entries
  const entries = getEntriesForDate(yesterday);
  const byModel = aggregateByModel(entries);
  const byTask = aggregateByTask(entries);
  
  // Calculate totals
  const totalTokens = todayData.total_tokens || 0;
  const totalCost = todayData.total_cost || 0;
  
  // Previous day comparison
  const prevTokens = yesterdayData?.total_tokens || 0;
  const prevCost = yesterdayData?.total_cost || 0;
  
  // 7-day average
  let weekTokens = 0;
  let weekCost = 0;
  let weekDays = 0;
  
  for (let i = 1; i <= 7; i++) {
    const date = getDateDaysAgo(i);
    if (summary[date]) {
      weekTokens += summary[date].total_tokens || 0;
      weekCost += summary[date].total_cost || 0;
      weekDays++;
    }
  }
  
  const avgTokens = weekDays > 0 ? weekTokens / weekDays : 0;
  const avgCost = weekDays > 0 ? weekCost / weekDays : 0;
  
  return {
    date: yesterday,
    total: {
      tokens: totalTokens,
      cost: totalCost,
      calls: entries.length
    },
    comparison: {
      previous_day: {
        tokens: prevTokens,
        cost: prevCost,
        change_pct: getPercentChange(totalTokens, prevTokens)
      },
      weekly_avg: {
        tokens: avgTokens,
        cost: avgCost,
        vs_avg: getPercentChange(totalTokens, avgTokens)
      }
    },
    by_model: byModel,
    by_task: byTask,
    scripts: todayData.scripts || {}
  };
}

function makeProgressBar(percentage, width = 15) {
  const filled = Math.round((percentage / 100) * width);
  const empty = width - filled;
  return '█'.repeat(filled) + '░'.repeat(empty);
}

function formatReportForTelegram(report) {
  if (report.noData) {
    return `📊 Daily Token Report - ${report.date}\n\n${report.message}`;
  }
  
  const lines = [];
  
  // Header
  const date = new Date(report.date + 'T00:00:00Z');
  const dateStr = date.toLocaleDateString('en-US', { 
    weekday: 'long', 
    year: 'numeric', 
    month: 'long', 
    day: 'numeric' 
  });
  
  lines.push(`📊 Daily Token Usage Report`);
  lines.push(`${dateStr}`);
  lines.push(`⏰ Last 24 Hours`);
  lines.push('');
  lines.push('━━━━━━━━━━━━━━━━━━━');
  lines.push('');
  
  // Overall Usage
  lines.push(`📈 Overall Usage`);
  lines.push(`Total Tokens: ${report.total.tokens.toLocaleString()}`);
  lines.push(`Estimated Cost: ${formatCost(report.total.cost)}`);
  lines.push('');
  
  // By Task/Category - Grouped by business area
  lines.push(`🎯 By Task`);
  lines.push('');
  
  // Aggregate by category
  const categoryData = {};
  for (const [task, data] of Object.entries(report.by_task)) {
    const cat = getTaskCategory(task);
    const catKey = cat.category;
    
    if (!categoryData[catKey]) {
      categoryData[catKey] = {
        name: cat.name,
        emoji: cat.emoji,
        tokens: 0,
        calls: 0,
        cost: 0
      };
    }
    
    categoryData[catKey].tokens += data.tokens;
    categoryData[catKey].calls += data.calls;
    categoryData[catKey].cost += data.cost;
  }
  
  const categories = Object.entries(categoryData)
    .sort((a, b) => b[1].tokens - a[1].tokens);
  
  for (const [catKey, data] of categories) {
    const pct = ((data.tokens / report.total.tokens) * 100).toFixed(0);
    const bar = makeProgressBar(parseInt(pct));
    lines.push(`${data.emoji} ${data.name}`);
    lines.push(`  ${bar} ${pct}%`);
    lines.push(`  ${data.tokens.toLocaleString()} tokens (${data.calls} messages)`);
    lines.push('');
  }
  
  // By Model
  lines.push(`🤖 By Model`);
  lines.push('');
  const models = Object.entries(report.by_model)
    .sort((a, b) => b[1].total_tokens - a[1].total_tokens);
  
  for (const [model, data] of models) {
    const name = PRICING[model]?.name || model;
    const pct = ((data.total_tokens / report.total.tokens) * 100).toFixed(0);
    const bar = makeProgressBar(parseInt(pct));
    lines.push(name);
    lines.push(`  ${bar} ${pct}%`);
    lines.push(`  ${data.total_tokens.toLocaleString()} tokens → ${formatCost(data.cost)}`);
    lines.push('');
  }
  
  // Insights & Recommendations
  lines.push(`💡 Insights`);
  
  // Largest category
  const largestCat = categories[0];
  if (largestCat) {
    const catPct = ((largestCat[1].tokens / report.total.tokens) * 100).toFixed(0);
    lines.push(`• Largest: ${largestCat[1].emoji} ${largestCat[1].name} (${catPct}%)`);
  }
  
  // Daily average trend
  const avgCost = report.comparison.weekly_avg.cost;
  const trend = report.total.cost > avgCost ? '↗' : report.total.cost < avgCost ? '↘' : '→';
  lines.push(`• Daily average trending at ${trend}${formatCost(avgCost)}`);
  
  // Avg tokens per message
  const avgTokensPerMsg = Math.round(report.total.tokens / report.total.calls);
  lines.push(`• Avg tokens/message: ${avgTokensPerMsg.toLocaleString()}`);
  
  // Efficiency check
  const mostEfficientModel = Object.entries(report.by_model)
    .map(([model, data]) => ({
      model,
      name: PRICING[model]?.name || model,
      efficiency: data.total_tokens / (data.cost || 0.001)
    }))
    .sort((a, b) => b.efficiency - a.efficiency)[0];
  
  if (mostEfficientModel) {
    lines.push(`• Most efficient: ${mostEfficientModel.name}`);
  }
  
  // Recommendations
  if (report.total.cost > 5.0) {
    lines.push(`\n⚠️ Recommendation: High daily cost detected`);
  } else if (report.total.cost < avgCost * 0.5) {
    lines.push(`\n✅ Well optimized: 50% below average`);
  }
  
  lines.push('');
  lines.push('━━━━━━━━━━━━━━━━━━━');
  
  return lines.join('\n');
}

function sendToTelegram(message) {
  try {
    // Use clawdbot message tool - proper syntax
    const cmd = `clawdbot message send --channel telegram --target 7980582930 --message ${JSON.stringify(message)}`;
    
    execSync(cmd, {
      stdio: 'pipe',
      encoding: 'utf8'
    });
    
    console.log('✅ Report sent to Telegram');
  } catch (err) {
    console.error('❌ Failed to send to Telegram:', err.message);
    
    // Fallback: Create a pending file
    const pendingFile = path.join(process.env.HOME, 'clawd/logs/report-pending.txt');
    fs.writeFileSync(pendingFile, message);
    console.log(`⚠️  Message saved to: ${pendingFile}`);
    console.log('   Run: clawdbot message send --channel telegram --target 7980582930 --message "$(cat ~/clawd/logs/report-pending.txt)"');
  }
}

function main() {
  console.log('');
  console.log('========================================');
  console.log('Daily Token Usage Report Generator');
  console.log('========================================');
  console.log('');
  
  const report = generateReport();
  const message = formatReportForTelegram(report);
  
  // Save to file
  const reportFile = path.join(process.env.HOME, `clawd/logs/token-report-${report.date}.txt`);
  fs.writeFileSync(reportFile, message);
  console.log(`✅ Report saved: ${reportFile}`);
  
  // Send to Telegram
  sendToTelegram(message);
  
  console.log('');
  console.log('✅ Daily report complete');
}

if (require.main === module) {
  main();
}

module.exports = { generateReport, formatReportForTelegram };
