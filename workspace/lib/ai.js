// lib/ai.js — AI completions with MO (Model Orchestrator) cascade routing
// Primary: Qwen-Coder (extract) + Qwen-Turbo (draft) — cheapest
// Fallback: Kimi K2.5 → Gemini Flash → Grok (last resort)
// Zero Anthropic usage — all routing through Qwen/Kimi/Gemini/Grok
const https = require('https');
const path = require('path');
const fs = require('fs');

const KEYS_FILE = path.join(__dirname, '..', 'api-keys.json');
const COST_LOG = path.join(__dirname, '..', 'logs', 'ai-costs.jsonl');
const PERF_LOG = path.join(__dirname, '..', 'logs', 'model-performance.jsonl');

// Pricing per 1M tokens
const PRICING = {
  'qwen-turbo':          { input: 0.05, output: 0.40 },   // Tier 1 — dirt cheap
  'qwen-coder':          { input: 0.30, output: 1.50 },   // Tier 2 — great at extraction
  'qwen3.5-122b-a10b':   { input: 0.40, output: 1.20 },   // Tier 2 — general
  'kimi-k2.5':           { input: 0.60, output: 2.50 },   // Tier 3 — long context, reasoning
  'gemini-2.0-flash':    { input: 0.10, output: 0.40 },   // Tier 1 — fallback
  'gemini-2.5-flash':    { input: 0.10, output: 0.40 },   // Tier 1 — fallback
  'grok-3-mini':         { input: 0.30, output: 0.60 },   // Tier 2 — last resort
  'grok-4-1-fast-non-reasoning': { input: 2.00, output: 10.00 } // Tier 4 — expensive last resort
};

// MO Cascade: cheapest first, escalate on failure
const EXTRACT_CASCADE = ['qwen-coder', 'kimi-k2.5', 'gemini-2.0-flash', 'grok-3-mini'];
const DRAFT_CASCADE   = ['qwen-turbo', 'gemini-2.0-flash', 'kimi-k2.5'];

function logCost(script, model, inputTokens, outputTokens) {
  try {
    const pricing = PRICING[model] || { input: 0.10, output: 0.40 };
    const cost = (inputTokens / 1e6) * pricing.input + (outputTokens / 1e6) * pricing.output;
    const entry = {
      ts: new Date().toISOString(),
      date: new Date().toISOString().split('T')[0],
      script,
      model,
      inputTokens,
      outputTokens,
      cost: parseFloat(cost.toFixed(6))
    };
    fs.appendFileSync(COST_LOG, JSON.stringify(entry) + '\n');
  } catch (e) { /* non-fatal */ }
}

function logPerformance(model, task, success, durationMs) {
  try {
    const entry = {
      ts: new Date().toISOString(),
      model,
      task,
      success,
      durationMs
    };
    fs.appendFileSync(PERF_LOG, JSON.stringify(entry) + '\n');
  } catch (e) { /* non-fatal */ }
}

function getKeys() {
  return JSON.parse(fs.readFileSync(KEYS_FILE, 'utf8'));
}

// ── Provider: Qwen (Alibaba SG — Singapore) ─────────────────────────────────
async function qwenComplete(prompt, model = 'qwen-coder') {
  const keys = getKeys();
  const apiKey = keys.providers?.alibaba_sg?.apiKey || keys.alibaba_sg;
  if (!apiKey || apiKey === '[ADD_KEY_HERE]') throw new Error('Qwen API key not configured');

  const body = JSON.stringify({
    model,
    messages: [{ role: 'user', content: prompt }],
    max_tokens: 2048,
    temperature: 0.2
  });

  return new Promise((resolve, reject) => {
    const options = {
      hostname: 'dashscope-intl.aliyuncs.com',
      path: '/compatible-mode/v1/chat/completions',
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${apiKey}`,
        'Content-Type': 'application/json',
        'Content-Length': Buffer.byteLength(body)
      }
    };

    const req = https.request(options, (res) => {
      let data = '';
      res.on('data', chunk => data += chunk);
      res.on('end', () => {
        try {
          const parsed = JSON.parse(data);
          if (res.statusCode !== 200) throw new Error(parsed.error?.message || `HTTP ${res.statusCode}: ${data.substring(0, 200)}`);
          const text = parsed.choices?.[0]?.message?.content || '';
          const usage = parsed.usage || {};
          logCost('ai-qwen', model, usage.prompt_tokens || 0, usage.completion_tokens || 0);
          resolve(text.trim());
        } catch (e) {
          reject(new Error(`Qwen/${model}: ${e.message}`));
        }
      });
    });
    req.on('error', reject);
    req.write(body);
    req.end();
  });
}

// ── Provider: Kimi (Moonshot) ────────────────────────────────────────────────
async function kimiComplete(prompt, model = 'kimi-k2.5') {
  const keys = getKeys();
  const apiKey = keys.providers?.moonshot?.apiKey || keys.moonshot;
  
  // Moonshot disabled until valid key provided
  if (!apiKey || apiKey === '[ADD_KEY_HERE]' || apiKey === null) {
    throw new Error('Moonshot/Kimi disabled — no valid API key');
  }

  const body = JSON.stringify({
    model,
    messages: [{ role: 'user', content: prompt }],
    max_tokens: 2048,
    temperature: 0.2
  });

  return new Promise((resolve, reject) => {
    const options = {
      hostname: 'api.moonshot.ai',  // ✅ Correct (.ai domain)
      path: '/v1/chat/completions',
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${apiKey}`,
        'Content-Type': 'application/json',
        'Content-Length': Buffer.byteLength(body)
      }
    };

    const req = https.request(options, (res) => {
      let data = '';
      res.on('data', chunk => data += chunk);
      res.on('end', () => {
        try {
          const parsed = JSON.parse(data);
          if (res.statusCode !== 200) throw new Error(parsed.error?.message || `HTTP ${res.statusCode}: ${data.substring(0, 200)}`);
          const text = parsed.choices?.[0]?.message?.content || '';
          const usage = parsed.usage || {};
          logCost('ai-kimi', model, usage.prompt_tokens || 0, usage.completion_tokens || 0);
          resolve(text.trim());
        } catch (e) {
          reject(new Error(`Kimi/${model}: ${e.message}`));
        }
      });
    });
    req.on('error', reject);
    req.write(body);
    req.end();
  });
}

// ── Provider: Gemini (Google) ────────────────────────────────────────────────
async function geminiComplete(prompt, model = 'gemini-2.0-flash') {
  const keys = getKeys();
  const apiKey = keys.providers?.google?.apiKey || keys.gemini;
  if (!apiKey || apiKey === '[ADD_KEY_HERE]') throw new Error('Gemini API key not configured');

  const url = new URL(`https://generativelanguage.googleapis.com/v1beta/models/${model}:generateContent?key=${apiKey}`);
  const body = JSON.stringify({
    contents: [{ parts: [{ text: prompt }] }],
    generationConfig: { maxOutputTokens: 2048, temperature: 0.3 }
  });

  return new Promise((resolve, reject) => {
    const options = {
      hostname: url.hostname,
      path: url.pathname + url.search,
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'Content-Length': Buffer.byteLength(body) }
    };

    const req = https.request(options, (res) => {
      let data = '';
      res.on('data', chunk => data += chunk);
      res.on('end', () => {
        try {
          const parsed = JSON.parse(data);
          if (res.statusCode !== 200) throw new Error(parsed.error?.message || `HTTP ${res.statusCode}: ${data.substring(0, 200)}`);
          const text = parsed.candidates?.[0]?.content?.parts?.[0]?.text || '';
          const usage = parsed.usageMetadata || {};
          logCost('ai-gemini', model, usage.promptTokenCount || 0, usage.candidatesTokenCount || 0);
          resolve(text.trim());
        } catch (e) {
          reject(new Error(`Gemini/${model}: ${e.message}`));
        }
      });
    });
    req.on('error', reject);
    req.write(body);
    req.end();
  });
}

// ── Provider: Grok (xAI) — last resort ──────────────────────────────────────
async function grokComplete(prompt, model = 'grok-3-mini') {
  const keys = getKeys();
  const apiKey = keys.providers?.grok_xai?.apiKey || keys.xai;
  if (!apiKey || apiKey === '[ADD_KEY_HERE]') throw new Error('Grok API key not configured');

  const body = JSON.stringify({
    model,
    messages: [{ role: 'user', content: prompt }],
    max_tokens: 2048,
    temperature: 0.2
  });

  return new Promise((resolve, reject) => {
    const options = {
      hostname: 'api.x.ai',
      path: '/v1/chat/completions',
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${apiKey}`,
        'Content-Type': 'application/json',
        'Content-Length': Buffer.byteLength(body)
      }
    };

    const req = https.request(options, (res) => {
      let data = '';
      res.on('data', chunk => data += chunk);
      res.on('end', () => {
        try {
          const parsed = JSON.parse(data);
          if (res.statusCode !== 200) throw new Error(parsed.error?.message || `HTTP ${res.statusCode}: ${data.substring(0, 200)}`);
          const text = parsed.choices?.[0]?.message?.content || '';
          const usage = parsed.usage || {};
          logCost('ai-grok', model, usage.prompt_tokens || 0, usage.completion_tokens || 0);
          resolve(text.trim());
        } catch (e) {
          reject(new Error(`Grok/${model}: ${e.message}`));
        }
      });
    });
    req.on('error', reject);
    req.write(body);
    req.end();
  });
}

// ── Model Dispatcher (maps model name → provider function) ───────────────────
const DISPATCH = {
  'qwen-coder':      (p) => qwenComplete(p, 'qwen-coder'),
  'qwen-turbo':      (p) => qwenComplete(p, 'qwen-turbo'),
  'qwen3.5-122b-a10b': (p) => qwenComplete(p, 'qwen3.5-122b-a10b'),
  'kimi-k2.5':       (p) => kimiComplete(p, 'kimi-k2.5'),
  'gemini-2.0-flash': (p) => geminiComplete(p, 'gemini-2.0-flash'),
  'gemini-2.5-flash': (p) => geminiComplete(p, 'gemini-2.5-flash'),
  'grok-3-mini':     (p) => grokComplete(p, 'grok-3-mini'),
  'grok-4-1-fast-non-reasoning': (p) => grokComplete(p, 'grok-4-1-fast-non-reasoning'),
};

// ── MO Smart Router: cascade through models, cheapest first ──────────────────
async function complete(prompt, task = 'extract') {
  const cascade = task === 'draft' ? DRAFT_CASCADE : EXTRACT_CASCADE;
  const errors = [];

  for (const model of cascade) {
    const fn = DISPATCH[model];
    if (!fn) continue;

    const start = Date.now();
    try {
      const result = await fn(prompt);
      const duration = Date.now() - start;
      logPerformance(model, task, true, duration);
      console.log(`   ✅ ${task} completed by ${model} (${duration}ms) — $${(PRICING[model]?.input || 0).toFixed(2)}/M`);
      return result;
    } catch (err) {
      const duration = Date.now() - start;
      logPerformance(model, task, false, duration);
      errors.push(`${model}: ${err.message}`);
      console.warn(`   ⚠️  ${model} failed (${err.message}), escalating...`);
    }
  }

  throw new Error(`All models failed for task "${task}":\n${errors.join('\n')}`);
}

module.exports = { complete, qwenComplete, kimiComplete, geminiComplete, grokComplete };
