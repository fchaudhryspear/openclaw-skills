/**
 * Cost Tracking System
 * Track token usage and estimate costs across all AI API calls
 */

const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');

const COST_LOG_PATH = path.join(process.env.HOME, '.openclaw/workspace/ai-cost-tracker/logs/ai-costs.jsonl');
const DAILY_SUMMARY_PATH = path.join(process.env.HOME, '.openclaw/workspace/ai-cost-tracker/logs/daily-costs.json');
const LAST_PROCESSED_PATH = path.join(process.env.HOME, '.openclaw/workspace/ai-cost-tracker/logs/last-processed-timestamps.json');

// Cost per 1M tokens (approximate)
const PRICING = {
  'anthropic/claude-sonnet-4-5': {
    input: 3.00,
    output: 15.00
  },
  'kimi-k2.5': {
    input: 0.50,
    output: 2.00
  },
  'grok-4-fast-non-reasoning': {
    input: 0.10,  // xAI pricing
    output: 0.30  // xAI pricing
  },
  'google/gemini-2.0-flash-exp': {
    input: 0.15,
    output: 0.60
  }
};

// Alert thresholds
const ALERTS = {
  dailyTokenLimit: 150000,      // 150K tokens/day
  singleScriptLimit: 50000,     // 50K tokens per run
  dailyCostLimit: 5.00          // $5/day
};

/**
 * Track API usage
 */
function trackUsage(scriptName, model, usage, metadata = {}) {
  const timestamp = new Date().toISOString();
  const date = timestamp.split('T')[0];
  
  // Calculate cost
  const pricing = PRICING[model] || { input: 0, output: 0 };
  const inputCost = (usage.prompt_tokens / 1000000) * pricing.input;
  const outputCost = (usage.completion_tokens / 1000000) * pricing.output;
  const totalCost = inputCost + outputCost;
  
  const entry = {
    timestamp,
    date,
    script: scriptName,
    model,
    usage: {
      prompt_tokens: usage.prompt_tokens,
      completion_tokens: usage.completion_tokens,
      total_tokens: usage.total_tokens
    },
    cost: {
      input: inputCost,
      output: outputCost,
      total: totalCost,
      currency: 'USD'
    },
    metadata
  };
  
  // Append to log
  try {
    fs.appendFileSync(COST_LOG_PATH, JSON.stringify(entry) + '\n');
  } catch (error) {
    console.error('Failed to log cost:', error.message);
  }
  
  // Check alerts
  checkAlerts(scriptName, usage.total_tokens, totalCost, date);
  
  // Update daily summary
  updateDailySummary(date, entry);
  
  return entry;
}

/**
 * Check if usage exceeds alert thresholds
 */
function checkAlerts(scriptName, tokens, cost, date) {
  const alerts = [];
  
  // Single script limit
  if (tokens > ALERTS.singleScriptLimit) {
    alerts.push({
      type: 'HIGH_USAGE',
      script: scriptName,
      tokens,
      limit: ALERTS.singleScriptLimit,
      message: `Script ${scriptName} used ${tokens} tokens (limit: ${ALERTS.singleScriptLimit})`
    });
  }
  
  // Daily token limit
  const dailyTokens = getDailyTokens(date);
  if (dailyTokens > ALERTS.dailyTokenLimit) {
    alerts.push({
      type: 'DAILY_LIMIT',
      date,
      tokens: dailyTokens,
      limit: ALERTS.dailyTokenLimit,
      message: `Daily token usage ${dailyTokens} exceeds limit ${ALERTS.dailyTokenLimit}`
    });
  }
  
  // Daily cost limit
  const dailyCost = getDailyCost(date);
  if (dailyCost > ALERTS.dailyCostLimit) {
    alerts.push({
      type: 'COST_LIMIT',
      date,
      cost: dailyCost,
      limit: ALERTS.dailyCostLimit,
      message: `Daily cost $${dailyCost.toFixed(2)} exceeds limit $${ALERTS.dailyCostLimit.toFixed(2)}`
    });
  }
  
  // Log alerts
  if (alerts.length > 0) {
    const alertLogPath = path.join(process.env.HOME, '.openclaw/workspace/ai-cost-tracker/logs/cost-alerts.log');
    const timestamp = new Date().toISOString();
    
    alerts.forEach(alert => {
      console.warn(`⚠️  COST ALERT: ${alert.message}`);
      fs.appendFileSync(alertLogPath, `${timestamp} ${JSON.stringify(alert)}\n`);
    });
  }
  
  return alerts;
}

/**
 * Get total tokens used today
 */
function getDailyTokens(date) {
  try {
    const summary = JSON.parse(fs.readFileSync(DAILY_SUMMARY_PATH, 'utf8'));
    return summary[date]?.total_tokens || 0;
  } catch (error) {
    return 0;
  }
}

/**
 * Get total cost today
 */
function getDailyCost(date) {
  try {
    const summary = JSON.parse(fs.readFileSync(DAILY_SUMMARY_PATH, 'utf8'));
    return summary[date]?.total_cost || 0;
  } catch (error) {
    return 0;
  }
}

/**
 * Update daily summary
 */
function updateDailySummary(date, entry) {
  let summary = {};
  
  try {
    if (fs.existsSync(DAILY_SUMMARY_PATH)) {
      summary = JSON.parse(fs.readFileSync(DAILY_SUMMARY_PATH, 'utf8'));
    }
  } catch (error) {
    // Start fresh if can't read
  }
  
  if (!summary[date]) {
    summary[date] = {
      total_tokens: 0,
      total_cost: 0,
      scripts: {}
    };
  }
  
  summary[date].total_tokens += entry.usage.total_tokens;
  summary[date].total_cost += entry.cost.total;
  
  if (!summary[date].scripts[entry.script]) {
    summary[date].scripts[entry.script] = {
      runs: 0,
      tokens: 0,
      cost: 0
    };
  }
  
  summary[date].scripts[entry.script].runs += 1;
  summary[date].scripts[entry.script].tokens += entry.usage.total_tokens;
  summary[date].scripts[entry.script].cost += entry.cost.total;
  
  try {
    fs.writeFileSync(DAILY_SUMMARY_PATH, JSON.stringify(summary, null, 2));
  } catch (error) {
    console.error('Failed to update daily summary:', error.message);
  }
}

/**
 * Load last processed timestamps
 */
function loadLastProcessedTimestamps() {
  try {
    if (fs.existsSync(LAST_PROCESSED_PATH)) {
      return JSON.parse(fs.readFileSync(LAST_PROCESSED_PATH, 'utf8'));
    }
  } catch (error) {
    console.error('Failed to load last processed timestamps:', error.message);
  }
  return {};
}

/**
 * Save last processed timestamps
 */
function saveLastProcessedTimestamps(timestamps) {
  try {
    fs.writeFileSync(LAST_PROCESSED_PATH, JSON.stringify(timestamps, null, 2));
  } catch (error) {
    console.error('Failed to save last processed timestamps:', error.message);
  }
}

/**
 * Poll OpenClaw sessions and log usage
 */
function pollAndLogOpenClawSessions() {
  const lastProcessedTimestamps = loadLastProcessedTimestamps();
  let sessions;
  try {
    console.log('🛠️ Polling OpenClaw sessions...');
    const sessionsJson = execSync('openclaw sessions --json', { encoding: 'utf8' });
    sessions = JSON.parse(sessionsJson).sessions;
  } catch (error) {
    console.error('Failed to poll sessions:', error.message);
    return;
  }

  sessions.forEach(session => {
    const { key, updatedAt, model, totalTokens } = session;
    const lastProcessed = lastProcessedTimestamps[key] || 0;

    if (updatedAt > lastProcessed && totalTokens > 0) {
      // Fetch and process session history
      let history;
      try {
        const historyJson = execSync(`openclaw sessions history --session ${key} --include-tools --limit 10 --json`, { encoding: 'utf8' });
        history = JSON.parse(historyJson);
      } catch (error) {
        console.error(`Failed to poll session history for ${key}:`, error.message);
        return;
      }

      history.messages.reverse().forEach(message => {
        if (message.role === 'assistant' && message.usage && message.timestamp > lastProcessed) {
          const usage = {
            prompt_tokens: message.usage.prompt_tokens || 0,
            completion_tokens: message.usage.completion_tokens || 0,
            total_tokens: message.usage.total_tokens || 0
          };
          trackUsage(key, model, usage, { sessionId: session.sessionId });
          lastProcessedTimestamps[key] = message.timestamp;
        }
      });
    }
  });

  // Save updated timestamps
  saveLastProcessedTimestamps(lastProcessedTimestamps);
}

/**
 * Get cost report
 */
function getReport(days = 7) {
  const today = new Date();
  const report = {
    period: `Last ${days} days`,
    total_tokens: 0,
    total_cost: 0,
    daily: []
  };
  
  try {
    const summary = JSON.parse(fs.readFileSync(DAILY_SUMMARY_PATH, 'utf8'));
    
    for (let i = 0; i < days; i++) {
      const date = new Date(today);
      date.setDate(date.getDate() - i);
      const dateStr = date.toISOString().split('T')[0];
      
      if (summary[dateStr]) {
        report.total_tokens += summary[dateStr].total_tokens;
        report.total_cost += summary[dateStr].total_cost;
        report.daily.push({
          date: dateStr,
          tokens: summary[dateStr].total_tokens,
          cost: summary[dateStr].total_cost,
          scripts: summary[dateStr].scripts
        });
      }
    }
  } catch (error) {
    console.error('Failed to generate report:', error.message);
  }
  
  return report;
}

/**
 * Main execution
 */
function main() {
  console.log('\n⚡ Starting AI Cost Tracker');
  pollAndLogOpenClawSessions();
  console.log('✅ Completed AI Cost Tracker Run\n');
}

if (require.main === module) {
  main();
}

module.exports = {
  trackUsage,
  getReport,
  PRICING,
  ALERTS,
  pollAndLogOpenClawSessions
};
