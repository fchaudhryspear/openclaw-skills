// lib/ai.js — AI completions: Gemini Flash (cheap) + Grok (fast)
const https = require('https');
const path = require('path');
const fs = require('fs');

const KEYS_FILE = path.join(__dirname, '..', 'api-keys.json');
const COST_LOG = path.join(__dirname, '..', 'logs', 'ai-costs.jsonl');

// Pricing per 1M tokens
const PRICING = {
  'gemini-2.0-flash':      { input: 0.10, output: 0.40 },
  'gemini-2.0-flash-lite': { input: 0.075, output: 0.30 },
  'gemini-2.5-flash':      { input: 0.10, output: 0.40 },
  'grok-4-1-fast-non-reasoning': { input: 2.00, output: 10.00 },
  'grok-3-mini':           { input: 0.30, output: 0.60 }
};

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

function getKeys() {
  return JSON.parse(fs.readFileSync(KEYS_FILE, 'utf8'));
}

// Gemini Flash via REST — cheapest option ($0.10/M input)
async function geminiComplete(prompt, model = 'gemini-2.0-flash') {
  const keys = getKeys();
  const apiKey = keys.gemini;
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
          if (res.statusCode !== 200) throw new Error(parsed.error?.message || data);
          const text = parsed.candidates?.[0]?.content?.parts?.[0]?.text || '';
          // Log cost
          const usage = parsed.usageMetadata || {};
          logCost('ai-gemini', model, usage.promptTokenCount || 0, usage.candidatesTokenCount || 0);
          resolve(text.trim());
        } catch (e) {
          reject(new Error(`Gemini error: ${e.message}`));
        }
      });
    });
    req.on('error', reject);
    req.write(body);
    req.end();
  });
}

// Grok via OpenAI-compatible API — fast, great at extraction
async function grokComplete(prompt, model = 'grok-4-1-fast-non-reasoning') {
  const keys = getKeys();
  const apiKey = keys.xai;

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
          if (res.statusCode !== 200) throw new Error(parsed.error?.message || data);
          const text = parsed.choices?.[0]?.message?.content || '';
          // Log cost
          const usage = parsed.usage || {};
          logCost('ai-grok', model, usage.prompt_tokens || 0, usage.completion_tokens || 0);
          resolve(text.trim());
        } catch (e) {
          reject(new Error(`Grok error: ${e.message}`));
        }
      });
    });
    req.on('error', reject);
    req.write(body);
    req.end();
  });
}

// Smart router: Gemini for drafts (style), Grok for extraction/classification
async function complete(prompt, task = 'extract') {
  // task: 'extract' | 'draft'
  try {
    if (task === 'draft') {
      return await geminiComplete(prompt, 'gemini-2.0-flash'); // Good at style
    } else {
      return await grokComplete(prompt); // Fast, cheap extraction
    }
  } catch (err) {
    // Fallback to Gemini if Grok fails
    if (task !== 'draft') {
      console.warn(`   ⚠️  Grok failed (${err.message}), falling back to Gemini`);
      return await geminiComplete(prompt);
    }
    throw err;
  }
}

module.exports = { complete, geminiComplete, grokComplete };
