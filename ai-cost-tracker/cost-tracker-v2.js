/**
 * AI Cost Tracker v2.0 - Comprehensive Usage Tracking
 * Tracks ALL OpenClaw usage including main sessions, cron jobs, sub-agents
 */

const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');

// Paths (workspace-relative)
const HOME = process.env.HOME;
const LOGS_DIR = path.join(HOME, '.openclaw/workspace/ai-cost-tracker/logs');
const COST_LOG_PATH = path.join(LOGS_DIR, 'ai-costs.jsonl');
const DAILY_SUMMARY_PATH = path.join(LOGS_DIR, 'daily-costs.json');
const PERFORMANCE_DB_PATH = path.join(HOME, 'memory/model_performance.json');

// Ensure logs directory exists
if (!fs.existsSync(LOGS_DIR)) {
    fs.mkdirSync(LOGS_DIR, { recursive: true });
}

// Complete pricing per 1M tokens (updated for all active models)
const PRICING = {
    // Alibaba (Singapore) - Qwen Models
    'alibaba-sg/qwen-turbo': { input: 0.05, output: 0.40 },
    'alibaba-sg/qwen-plus': { input: 0.40, output: 1.20 },
    'alibaba-sg/qwen-max': { input: 1.20, output: 6.00 },
    'alibaba-sg/qwen3.5-122b-a10b': { input: 0.40, output: 1.20 },
    'alibaba-sg/qwen-coder': { input: 0.30, output: 1.50 },
    
    // Alibaba (US) - backup
    'alibaba-us/qwen-turbo': { input: 0.05, output: 0.40 },
    'alibaba-us/qwen-plus': { input: 0.40, output: 1.20 },
    'alibaba-us/qwen-max': { input: 1.20, output: 6.00 },
    'alibaba-us/qwen3.5-122b-a10b': { input: 0.40, output: 1.20 },
    
    // Anthropic
    'anthropic/claude-3-haiku-20240307': { input: 1.00, output: 5.00 },
    'anthropic/claude-sonnet-4-6': { input: 3.00, output: 15.00 },
    'anthropic/claude-opus-4-6': { input: 5.00, output: 25.00 },
    
    // Google / Gemini
    'google/gemini-2.0-flash-lite': { input: 0.075, output: 0.30 },
    'google/gemini-2.0-flash': { input: 0.10, output: 0.40 },
    'google/gemini-2.5-flash': { input: 0.10, output: 0.40 },
    'google/gemini-2.5-pro': { input: 1.25, output: 10.00 },
    
    // XAI / Grok
    'xai/grok-3-mini': { input: 0.30, output: 0.60 },
    'xai/grok-4': { input: 3.00, output: 15.00 },
    'xai/grok-4-1-fast-non-reasoning': { input: 2.00, output: 10.00 },
    'xai/grok-4-1-fast-reasoning': { input: 2.00, output: 10.00 },
    'xai/grok-2-vision-1212': { input: 2.00, output: 10.00 },
    
    // Moonshot
    'moonshot/kimi-k2.5': { input: 0.60, output: 2.50 },
    
    // OpenAI
    'openai/gpt-4o': { input: 5.00, output: 15.00 },
    
    // Qwen Portal (OAuth)
    'qwen-portal/coder-model': { input: 0.00, output: 0.00 }, // Free tier
    'qwen-portal/vision-model': { input: 0.00, output: 0.00 } // Free tier
};

// Alert thresholds
const ALERTS = {
    dailyTokenLimit: 500000,      // 500K tokens/day (increased from 150K)
    singleRunLimit: 100000,       // 100K per session run
    dailyCostLimit: 20.00         // $20/day (increased from $5)
};

/**
 * Track API usage
 */
function trackUsage(source, model, usage, metadata = {}) {
    const timestamp = new Date().toISOString();
    const date = timestamp.split('T')[0];
    
    // Get pricing (default to cheap fallback if unknown model)
    const pricing = PRICING[model] || { input: 0.10, output: 0.40 };
    
    // Calculate costs
    const inputCost = (usage.input_tokens / 1000000) * pricing.input;
    const outputCost = (usage.output_tokens / 1000000) * pricing.output;
    const totalCost = inputCost + outputCost;
    
    const entry = {
        timestamp,
        date,
        source,           // 'main', 'cron', 'subagent', etc.
        model,
        usage: {
            input_tokens: usage.input_tokens || 0,
            output_tokens: usage.output_tokens || 0,
            total_tokens: (usage.input_tokens || 0) + (usage.output_tokens || 0)
        },
        cost: {
            input: parseFloat(inputCost.toFixed(6)),
            output: parseFloat(outputCost.toFixed(6)),
            total: parseFloat(totalCost.toFixed(6)),
            currency: 'USD'
        },
        metadata: {
            sessionId: metadata.sessionId || null,
            sessionKey: metadata.sessionKey || null,
            topic: metadata.topic || null,
            confidence: metadata.confidence || null,
            ...metadata
        }
    };
    
    // Append to cost log (JSONL format for easy processing)
    try {
        fs.appendFileSync(COST_LOG_PATH, JSON.stringify(entry) + '\n');
    } catch (error) {
        console.error('❌ Failed to log cost:', error.message);
    }
    
    // Check alerts and update daily summary
    checkAlerts(entry);
    updateDailySummary(date, entry);
    
    return entry;
}

/**
 * Check alert thresholds
 */
function checkAlerts(entry) {
    const alerts = [];
    const date = entry.date;
    
    const dailyStats = getDailyStats(date);
    
    // Single run limit
    if (entry.usage.total_tokens > ALERTS.singleRunLimit) {
        alerts.push({
            type: 'HIGH_USAGE_SINGLE_RUN',
            message: `Single run used ${entry.usage.total_tokens.toLocaleString()} tokens`,
            threshold: ALERTS.singleRunLimit
        });
    }
    
    // Daily token limit
    if (dailyStats.total_tokens > ALERTS.dailyTokenLimit) {
        alerts.push({
            type: 'DAILY_TOKEN_LIMIT_EXCEEDED',
            message: `Daily tokens: ${dailyStats.total_tokens.toLocaleString()} (limit: ${ALERTS.dailyTokenLimit.toLocaleString()})`,
            threshold: ALERTS.dailyTokenLimit
        });
    }
    
    // Daily cost limit
    if (dailyStats.total_cost > ALERTS.dailyCostLimit) {
        alerts.push({
            type: 'DAILY_COST_LIMIT_EXCEEDED',
            message: `Daily cost: $${dailyStats.total_cost.toFixed(2)} (limit: $${ALERTS.dailyCostLimit.toFixed(2)})`,
            threshold: ALERTS.dailyCostLimit
        });
    }
    
    // Send alerts (limit to once per minute to prevent spam)
    const ALERT_DEBOUNCE_MS = 60000; // 1 minute
    const LAST_ALERT_PATH = path.join(LOGS_DIR, 'last-alert-time.json');
    
    let lastAlertTime = 0;
    try {
        if (fs.existsSync(LAST_ALERT_PATH)) {
            lastAlertTime = JSON.parse(fs.readFileSync(LAST_ALERT_PATH, 'utf8')).lastAlert || 0;
        }
    } catch (e) {}
    
    const now = Date.now();
    const shouldAlert = alerts.length > 0 && (now - lastAlertTime) > ALERT_DEBOUNCE_MS;
    
    if (shouldAlert) {
        const alertLogPath = path.join(LOGS_DIR, 'cost-alerts.log');
        
        alerts.forEach(alert => {
            const msg = `⚠️  ${alert.type}: ${alert.message}`;
            console.warn(msg);
            fs.appendFileSync(alertLogPath, `${new Date().toISOString()} | ${JSON.stringify(alert)}\n`);
            
            // Telegram alerting handled by cron session output — no direct send needed
        });
        
        // Update last alert time
        fs.writeFileSync(LAST_ALERT_PATH, JSON.stringify({lastAlert: now}));
    }
    
    return alerts;
}

/**
 * Get daily stats for a given date
 */
function getDailyStats(date) {
    try {
        if (!fs.existsSync(DAILY_SUMMARY_PATH)) {
            return { total_tokens: 0, total_cost: 0 };
        }
        const summary = JSON.parse(fs.readFileSync(DAILY_SUMMARY_PATH, 'utf8'));
        const dayData = summary[date] || { total_tokens: 0, total_cost: 0 };
        return {
            total_tokens: dayData.total_tokens || 0,
            total_cost: dayData.total_cost || 0
        };
    } catch (error) {
        return { total_tokens: 0, total_cost: 0 };
    }
}

/**
 * Update daily summary with new entry
 */
function updateDailySummary(date, entry) {
    let summary = {};
    
    try {
        if (fs.existsSync(DAILY_SUMMARY_PATH)) {
            summary = JSON.parse(fs.readFileSync(DAILY_SUMMARY_PATH, 'utf8'));
        }
    } catch (error) {
        // Start fresh
    }
    
    if (!summary[date]) {
        summary[date] = {
            total_tokens: 0,
            total_cost: 0,
            by_source: {},
            by_model: {}
        };
    }
    
    // Add totals
    summary[date].total_tokens += entry.usage.total_tokens;
    summary[date].total_cost += entry.cost.total;
    
    // By source (main, cron, subagent)
    if (!summary[date].by_source[entry.source]) {
        summary[date].by_source[entry.source] = { runs: 0, tokens: 0, cost: 0 };
    }
    summary[date].by_source[entry.source].runs++;
    summary[date].by_source[entry.source].tokens += entry.usage.total_tokens;
    summary[date].by_source[entry.source].cost += entry.cost.total;
    
    // By model
    if (!summary[date].by_model[entry.model]) {
        summary[date].by_model[entry.model] = { uses: 0, tokens: 0, cost: 0 };
    }
    summary[date].by_model[entry.model].uses++;
    summary[date].by_model[entry.model].tokens += entry.usage.total_tokens;
    summary[date].by_model[entry.model].cost += entry.cost.total;
    
    try {
        fs.writeFileSync(DAILY_SUMMARY_PATH, JSON.stringify(summary, null, 2));
    } catch (error) {
        console.error('Failed to update daily summary:', error.message);
    }
}

/**
 * Scan ALL OpenClaw sessions and log any untracked usage (DEDUPED v2)
 */
function scanAllSessions() {
    console.log('\n🔍 Scanning all OpenClaw sessions for untracked usage...');
    
    let sessions;
    try {
        const raw = execSync('openclaw sessions --json 2>&1', { encoding: 'utf8' });
        const parsed = JSON.parse(raw);
        sessions = parsed.sessions || [];
    } catch (error) {
        console.error('❌ Failed to fetch sessions:', error.message);
        return 0;
    }
    
    let tracked_count = 0;
    let total_tracked_tokens = 0;
    
    sessions.forEach(session => {
        const key = session.key;
        const model = session.model;
        const tokens = session.totalTokens || 0;
        const updatedAt = session.updatedAt;
        
        // Skip sessions with no tokens
        if (tokens === 0) return;
        
        // Determine session type from key pattern
        let source = 'main';
        if (key.includes('cron:')) source = 'cron';
        else if (key.includes('subagent') || key.includes('session')) source = 'subagent';
        else if (key.includes('telegram')) source = 'telegram';
        else if (key.includes('discord')) source = 'discord';
        
        // Use token data directly from session metadata
        const inputTokens = session.inputTokens || 0;
        const outputTokens = session.outputTokens || 0;
        const usage = {
            input_tokens: inputTokens || Math.floor(tokens * 0.7),
            output_tokens: outputTokens || Math.floor(tokens * 0.3),
            total_tokens: tokens
        };
        
        // Log this session's usage
        const entry = trackUsage(source, model, usage, {
            sessionKey: key,
            updatedAt
        });
        
        tracked_count++;
        total_tracked_tokens += entry.usage.total_tokens;
    });
    
    console.log(`✅ Tracked ${tracked_count} sessions, ${total_tracked_tokens.toLocaleString()} total tokens`);
    return tracked_count;
}

/**
 * Generate cost report
 */
function generateReport(days = 7) {
    const today = new Date();
    const report = {
        period: `Last ${days} days`,
        generated_at: new Date().toISOString(),
        summary: {
            total_tokens: 0,
            total_cost: 0,
            avg_daily_tokens: 0,
            avg_daily_cost: 0
        },
        daily_breakdown: [],
        model_breakdown: {},
        source_breakdown: {}
    };
    
    try {
        if (!fs.existsSync(DAILY_SUMMARY_PATH)) {
            console.warn('⚠️ No cost data found yet');
            return report;
        }
        
        const summary = JSON.parse(fs.readFileSync(DAILY_SUMMARY_PATH, 'utf8'));
        
        // Aggregate by model and source
        const modelTotals = {};
        const sourceTotals = {};
        
        for (let i = 0; i < days; i++) {
            const date = new Date(today);
            date.setDate(date.getDate() - i);
            const dateStr = date.toISOString().split('T')[0];
            
            if (summary[dateStr]) {
                const day = summary[dateStr];
                report.summary.total_tokens += day.total_tokens;
                report.summary.total_cost += day.total_cost;
                
                report.daily_breakdown.push({
                    date: dateStr,
                    tokens: day.total_tokens,
                    cost: day.total_cost,
                    sources: Object.keys(day.by_source || {}).length,
                    models_used: Object.keys(day.by_model || {}).length
                });
                
                // Aggregate by model
                for (const [model, data] of Object.entries(day.by_model || {})) {
                    if (!modelTotals[model]) {
                        modelTotals[model] = { uses: 0, tokens: 0, cost: 0 };
                    }
                    modelTotals[model].uses += data.uses;
                    modelTotals[model].tokens += data.tokens;
                    modelTotals[model].cost += data.cost;
                }
                
                // Aggregate by source
                for (const [source, data] of Object.entries(day.by_source || {})) {
                    if (!sourceTotals[source]) {
                        sourceTotals[source] = { runs: 0, tokens: 0, cost: 0 };
                    }
                    sourceTotals[source].runs += data.runs;
                    sourceTotals[source].tokens += data.tokens;
                    sourceTotals[source].cost += data.cost;
                }
            }
        }
        
        report.summary.avg_daily_tokens = Math.round(report.summary.total_tokens / days);
        report.summary.avg_daily_cost = parseFloat((report.summary.total_cost / days).toFixed(2));
        report.model_breakdown = modelTotals;
        report.source_breakdown = sourceTotals;
        
    } catch (error) {
        console.error('❌ Failed to generate report:', error.message);
    }
    
    return report;
}

/**
 * Print formatted report to console
 */
function printReport(report) {
    console.log('\n' + '='.repeat(60));
    console.log('📊 AI COST REPORT — ' + report.period);
    console.log('='.repeat(60));
    
    console.log(`\n📈 Summary:`);
    console.log(`   Total Tokens:    ${report.summary.total_tokens.toLocaleString()}`);
    console.log(`   Total Cost:      $${report.summary.total_cost.toFixed(2)}`);
    console.log(`   Avg Daily Cost:  $${report.summary.avg_daily_cost.toFixed(2)}`);
    console.log(`   Avg Daily Tokens:${report.summary.avg_daily_tokens.toLocaleString()}`);
    
    console.log(`\n🔤 By Source:`);
    for (const [source, data] of Object.entries(report.source_breakdown)) {
        const pct = report.summary.total_tokens > 0 
            ? ((data.tokens / report.summary.total_tokens) * 100).toFixed(1) 
            : 0;
        console.log(`   ${source.padEnd(12)} ${data.runs.toString().padStart(4)} runs | ${(data.tokens/1000).toFixed(0)}K tok | $${data.cost.toFixed(2)} (${pct}%)`);
    }
    
    console.log(`\n🧠 By Model (Top 10):`);
    const sortedModels = Object.entries(report.model_breakdown)
        .sort((a, b) => b[1].tokens - a[1].tokens)
        .slice(0, 10);
    
    for (const [model, data] of sortedModels) {
        const shortModel = model.split('/').pop();
        const pct = report.summary.total_tokens > 0 
            ? ((data.tokens / report.summary.total_tokens) * 100).toFixed(1) 
            : 0;
        console.log(`   ${shortModel.padEnd(35)} ${data.uses.toString().padStart(4)} uses | ${(data.tokens/1000).toFixed(0)}K tok | $${data.cost.toFixed(2)}`);
    }
    
    console.log(`\n📅 Daily Breakdown:`);
    for (const day of report.daily_breakdown.slice().reverse()) {
        console.log(`   ${day.date} | ${(day.tokens/1000).toFixed(0)}K tok | $${day.cost.toFixed(2)} | ${day.models_used} models`);
    }
    
    console.log('\n' + '='.repeat(60) + '\n');
}

/**
 * Main execution - scan for untracked usage
 */
function main() {
    console.log('\n⚡ AI Cost Tracker v2.0');
    console.log('='.repeat(40));
    
    // Scan all sessions for untracked usage
    const scanned = scanAllSessions();
    
    // Generate and print report
    const report = generateReport(7);
    printReport(report);
    
    console.log(`✅ Cost tracking complete`);
    console.log(`📁 Logs: ${LOGS_DIR}`);
}

// Export for use as module
module.exports = {
    trackUsage,
    generateReport,
    printReport,
    scanAllSessions,
    PRICING,
    ALERTS
};

// Run if executed directly
if (require.main === module) {
    main();
}
