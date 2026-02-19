#!/usr/bin/env node
// kimi-swarm.js — Multi-agent task decomposition + parallel execution via Kimi K2.5
// Usage: node kimi-swarm.js "Research solid state batteries and write a summary"
//        node kimi-swarm.js "Plan a CI/CD pipeline for a Next.js app"

const https = require('https');
const fs = require('fs');
const path = require('path');

const KEYS_FILE = path.join(__dirname, 'api-keys.json');
const LOG_DIR = path.join(__dirname, 'logs');
const MODEL = 'kimi-k2.5';
const BASE = 'api.moonshot.ai';

function getKey() {
  return JSON.parse(fs.readFileSync(KEYS_FILE, 'utf8')).moonshot;
}

// ── API ───────────────────────────────────────────────────────────────────────
function kimiChat(messages, json = false) {
  const key = getKey();
  const body = JSON.stringify({
    model: MODEL,
    messages,
    ...(json ? { response_format: { type: 'json_object' } } : {})
  });

  return new Promise((resolve, reject) => {
    const req = https.request({
      hostname: BASE,
      path: '/v1/chat/completions',
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${key}`,
        'Content-Type': 'application/json',
        'Content-Length': Buffer.byteLength(body)
      }
    }, (res) => {
      let d = '';
      res.on('data', c => d += c);
      res.on('end', () => {
        try {
          const parsed = JSON.parse(d);
          if (res.statusCode !== 200) throw new Error(parsed.error?.message || d);
          resolve(parsed.choices[0].message.content);
        } catch (e) { reject(e); }
      });
    });
    req.on('error', reject);
    req.write(body);
    req.end();
  });
}

// ── Steps ─────────────────────────────────────────────────────────────────────
async function decompose(objective) {
  console.log('🧠 Decomposing task...');
  const content = await kimiChat([
    {
      role: 'system',
      content: 'You are the Swarm Orchestrator. Break the user\'s objective into distinct, parallelizable sub-tasks. Return a JSON object with a "tasks" array, each having: "role" (specialist type e.g. Researcher/Coder/Analyst/Reviewer), "instruction" (specific task), "priority" (1-10). Max 6 sub-tasks. Optimize for parallel execution.'
    },
    { role: 'user', content: objective }
  ], true);

  const plan = JSON.parse(content);
  const tasks = plan.tasks || [];
  console.log(`   ✓ ${tasks.length} sub-tasks planned\n`);
  return tasks;
}

async function executeOne(num, role, instruction) {
  try {
    const output = await kimiChat([
      { role: 'system', content: `You are a ${role}. Execute this task precisely and concisely.` },
      { role: 'user', content: instruction }
    ]);
    console.log(`   ✅ Agent ${num} (${role}) done`);
    return { role, instruction, output, success: true };
  } catch (e) {
    console.log(`   ❌ Agent ${num} (${role}) failed: ${e.message}`);
    return { role, instruction, output: `ERROR: ${e.message}`, success: false };
  }
}

async function executeParallel(tasks) {
  console.log(`⚡ Running ${tasks.length} agents in parallel...`);
  const results = await Promise.all(
    tasks.map((t, i) => executeOne(i + 1, t.role, t.instruction))
  );
  console.log('');
  return results;
}

async function synthesize(objective, results) {
  console.log('🔗 Synthesizing final answer...');
  const resultsText = results
    .map(r => `**${r.role}:**\n${r.output}`)
    .join('\n\n---\n\n');

  const final = await kimiChat([
    {
      role: 'system',
      content: 'You are the Final Synthesizer. Combine the following specialist reports into a coherent, comprehensive answer to the original objective. Be concise but complete. Use clear headings.'
    },
    {
      role: 'user',
      content: `**Original Objective:**\n${objective}\n\n**Specialist Reports:**\n${resultsText}`
    }
  ]);

  console.log('   ✓ Done\n');
  return final;
}

// ── Main ──────────────────────────────────────────────────────────────────────
async function run(objective) {
  const ts = new Date().toISOString().replace(/[:.]/g, '-').slice(0, 19);
  const logFile = path.join(LOG_DIR, `kimi-swarm-${ts}.log`);
  if (!fs.existsSync(LOG_DIR)) fs.mkdirSync(LOG_DIR, { recursive: true });

  console.log('\n🐜 Kimi K2.5 Swarm');
  console.log('════════════════════════════════════════════════════');
  console.log(`📋 Objective: ${objective}\n`);

  const log = [];
  const addLog = (msg) => { log.push(msg); };

  try {
    const tasks = await decompose(objective);
    addLog(`Tasks: ${JSON.stringify(tasks, null, 2)}`);

    const results = await executeParallel(tasks);
    addLog(`Results: ${JSON.stringify(results.map(r => ({ role: r.role, success: r.success })))}`);

    const final = await synthesize(objective, results);

    // Write log
    fs.writeFileSync(logFile, `Objective: ${objective}\n\n${log.join('\n\n')}\n\nFINAL:\n${final}`);

    console.log('════════════════════════════════════════════════════');
    console.log('📝 FINAL ANSWER:');
    console.log('════════════════════════════════════════════════════\n');
    console.log(final);
    console.log(`\n📁 Log: ${logFile}`);

    return { success: true, objective, tasks, results, final, logFile };
  } catch (e) {
    console.error(`\n❌ Swarm failed: ${e.message}`);
    fs.writeFileSync(logFile, `FAILED: ${e.message}\n\n${log.join('\n\n')}`);
    return { success: false, error: e.message, logFile };
  }
}

module.exports = { run };
if (require.main === module) {
  const objective = process.argv.slice(2).join(' ');
  if (!objective) {
    console.log('Usage: node kimi-swarm.js "Your objective here"');
    console.log('Example: node kimi-swarm.js "Plan a CI/CD pipeline for Next.js"');
    process.exit(1);
  }
  run(objective).then(r => process.exit(r.success ? 0 : 1));
}
