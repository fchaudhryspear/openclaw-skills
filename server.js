const express = require('express');
const { execSync } = require('child_process');
const path = require('path');
const cors = require('cors');

const app = express();
app.use(cors());
app.use(express.json());
app.use(express.static(path.join(__dirname, 'web')));

app.get('/health', (req, res) => {
  try {
    const model = execSync('openclaw session_status', {encoding: 'utf8'}).match(/Model: ([^\\s]+)/)?.[1] || 'unknown';
    res.json({
      status: 'Optimus_macmini ✅',
      model: model,
      timestamp: new Date().toISOString(),
      uptime: Math.floor(process.uptime()),
      workspace: process.cwd()
    });
  } catch (e) {
    res.status(500).json({ error: 'OpenClaw unavailable', details: e.message });
  }
});

app.post('/chat', async (req, res) => {
  try {
    const { message } = req.body;
    const reply = execSync(`echo "${message}" | openclaw`, {encoding: 'utf8'});
    res.json({ reply: reply.trim() });
  } catch (e) {
    res.status(500).json({ error: 'Chat failed' });
  }
});

app.get('/crons', (req, res) => {
  try {
    const crons = execSync('openclaw cron list', {encoding: 'utf8'});
    res.json({ crons: crons.trim().split('\\n').length });
  } catch (e) {
    res.json({ crons: 0 });
  }
});

const PORT = 3000;
app.listen(PORT, 'localhost', () => {
  console.log(`🔒 Private Optimus: http://localhost:${PORT}`);
  console.log(`🩺 Health: http://localhost:${PORT}/health`);
});
