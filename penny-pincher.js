#!/usr/bin/env node
/**
 * Penny-Pincher Orchestration Architecture v2
 * Routes tasks to optimal model based on complexity/cost
 * 
 * Usage: node penny-pincher.js &quot;your task here&quot; [model]
 */

const { execSync } = require('child_process');
const fs = require('fs');

// Model routing matrix
const ROUTING = {
  simple: {
    models: ['xai/grok-4-1-fast-non-reasoning'],
    percent: 60,
    useCases: ['extraction', 'Q&A', 'summaries', 'lists', 'facts']
  },
  creative: {
    models: ['moonshot/kimi-k2.5'],
    percent: 30,
    useCases: ['writing', 'style matching', 'long context', 'creative']
  },
  complex: {
    models: ['google/gemini-2.5-flash'],
    percent: 10,
    useCases: ['reasoning', 'code', 'orchestration', 'planning', 'analysis']
  }
};

const STYLE_CACHE = './penny-pincher-style-cache.json';

// Heuristics for task classification
function classifyTask(prompt) {
  const lower = prompt.toLowerCase();
  
  if (lower.includes('write') || lower.includes('email') || lower.includes('style')) {
    return 'creative';
  }
  if (lower.includes('code') || lower.includes('reason') || lower.includes('plan') || 
      lower.includes('analyze') || prompt.length > 2000) {
    return 'complex';
  }
  return 'simple';
}

// Load style cache
function loadStyleCache() {
  try {
    return JSON.parse(fs.readFileSync(STYLE_CACHE, 'utf8'));
  } catch {
    return {};
  }
}

// Save style cache
function saveStyleCache(cache) {
  fs.writeFileSync(STYLE_CACHE, JSON.stringify(cache, null, 2));
}

// Route to model + execute
async function executeTask(prompt, overrideModel) {
  const cache = loadStyleCache();
  const taskType = overrideModel || classifyTask(prompt);
  const route = ROUTING[taskType];
  
  console.log(`🪙 Penny-Pincher: ${taskType} → ${route.models[0]} (${route.percent}%)`);
  
  // Check style cache first
  const cacheKey = `style_${taskType}_${prompt.slice(0, 50).replace(/\\s+/g, '_')}`;
  if (cache[cacheKey]) {
    console.log('📝 Using style cache');
    return cache[cacheKey];
  }
  
  // Execute via OpenClaw
  const modelArg = route.models[0];
  const result = execSync(`openclaw --model ${modelArg} "${prompt}"`, 
    { encoding: 'utf8', timeout: 60000 });
  
  // Cache creative responses for 7 days
  if (taskType === 'creative') {
    cache[cacheKey] = result.trim();
    saveStyleCache(cache);
  }
  
  return result;
}

// CLI
if (require.main === module) {
  const [, , prompt, model] = process.argv;
  if (!prompt) {
    console.log('Usage: node penny-pincher.js "your task" [model]');
    process.exit(1);
  }
  executeTask(prompt, model).then(console.log);
}

module.exports = { executeTask, classifyTask, ROUTING };
