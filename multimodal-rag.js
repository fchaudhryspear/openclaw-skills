#!/usr/bin/env node
/**
 * Multi-Modal RAG - Images + Text + Audio
 * Indexes screenshots, files, voice notes into unified RAG
 * 
 * Usage: node multimodal-rag.js index /path/to/files
 */

const { execSync } = require('child_process');
const fs = require('fs');
const path = require('path');

// Multi-modal sources
const SOURCES = {
  images: {
    glob: '**/*.{jpg,jpeg,png,gif,webp,heic,pdf}',
    processor: 'image',  // OpenClaw image tool
    embed: 'gemini-2.5-flash'  // Vision model
  },
  audio: {
    glob: '**/*.{mp3,m4a,wav,opus,aac}',
    processor: 'tts-reverse',  // STT
    embed: 'deepgram' 
  },
  docs: {
    glob: '**/*.{pdf,docx,txt,md}',
    processor: 'text-extract',
    embed: 'text-embedding-3-small'
  }
};

async function indexMultiModal(dir) {
  console.log(`🔍 Indexing ${dir}...`);
  
  let totalIndexed = 0;
  
  for (const [type, config] of Object.entries(SOURCES)) {
    const files = glob.sync(config.glob, { cwd: dir });
    
    for (const file of files.slice(0, 50)) {  // 50 file limit
      const fullPath = path.join(dir, file);
      
      // Multi-modal processing pipeline
      const content = await processFile(fullPath, config);
      const embedding = await embedContent(content, config.embed);
      
      // Store in unified RAG index
      await storeObservation({
        type,
        path: fullPath,
        content,
        embedding,
        timestamp: new Date().toISOString()
      });
      
      totalIndexed++;
      console.log(`✅ ${type}/${file}`);
    }
  }
  
  console.log(`🎉 ${totalIndexed} multi-modal assets indexed!`);
}

async function processFile(filePath, config) {
  // Delegate to OpenClaw tools
  switch (config.processor) {
    case 'image':
      return execSync(`openclaw image "${filePath}" "Describe this screenshot"`, {encoding: 'utf8'});
    case 'tts-reverse':
      return execSync(`openclaw tts "${filePath}" --stt`, {encoding: 'utf8'});
    case 'text-extract':
      return fs.readFileSync(filePath, 'utf8');
  }
}

async function embedContent(content, model) {
  return execSync(`openclaw memory_search "${content.slice(0,1000)}" --embed-only`, {encoding: 'utf8'});
}

async function storeObservation(obs) {
  const obsDir = './vault/multimodal';
  fs.mkdirSync(obsDir, { recursive: true });
  
  const file = path.join(obsDir, `${obs.type}_${Date.now()}.jsonl`);
  fs.appendFileSync(file, JSON.stringify(obs) + '\\n');
}

// CLI
const [, , action, ...paths] = process.argv;
if (action === 'index') {
  for (const dir of paths) {
    indexMultiModal(dir);
  }
} else {
  console.log('Usage: node multimodal-rag.js index /path/to/screenshots');
}
