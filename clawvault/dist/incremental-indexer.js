/**
 * Incremental Indexer for ClawVault
 * 
 * Manages file watching, hash-based change detection, and incremental updates.
 */

const fs = require('fs');
const path = require('path');
const crypto = require('crypto');
const chokidar = require('chokidar');

class IncrementalIndexer {
  constructor(options = {}) {
    this.memoryPath = options.memoryPath || path.join(process.env.HOME, 'memory');
    this.indexPath = options.indexPath || path.join(this.memoryPath, '.clawvault-index.json');
    this.statePath = options.statePath || path.join(this.memoryPath, '.clawvault', 'indexer-state.json');
    this.categories = options.categories || [];
    this.index = { entries: {}, version: '1.0.0' };
    this.state = { fileHashes: {}, lastRun: null };
    this.watcher = null;
    this.queue = { add: [], remove: [] };
  }

  async initialize() {
    // Ensure directories exist
    await fs.promises.mkdir(path.dirname(this.statePath), { recursive: true });
    
    // Load existing index and state
    await this.loadIndex();
    await this.loadState();
  }

  async loadIndex() {
    try {
      const data = await fs.promises.readFile(this.indexPath, 'utf8');
      this.index = JSON.parse(data);
      // Ensure entries exists
      if (!this.index.entries) {
        this.index.entries = {};
      }
    } catch (err) {
      if (err.code !== 'ENOENT') throw err;
      // Initialize empty index
      this.index = { entries: {}, version: '1.0.0' };
    }
  }

  async loadState() {
    try {
      const data = await fs.promises.readFile(this.statePath, 'utf8');
      this.state = JSON.parse(data);
    } catch (err) {
      if (err.code !== 'ENOENT') throw err;
      // Initialize empty state
      this.state = { fileHashes: {}, lastRun: null };
    }
  }

  async saveIndex() {
    await fs.promises.writeFile(this.indexPath, JSON.stringify(this.index, null, 2));
  }

  async saveState() {
    await fs.promises.writeFile(this.statePath, JSON.stringify(this.state, null, 2));
  }

  calculateHash(content) {
    return crypto.createHash('sha256').update(content).digest('hex');
  }

  async getFileHash(filePath) {
    try {
      const content = await fs.promises.readFile(filePath, 'utf8');
      return this.calculateHash(content);
    } catch (err) {
      return null;
    }
  }

  parseFrontmatter(content) {
    const frontmatterRegex = /^---\s*\n([\s\S]*?)\n---\s*\n([\s\S]*)$/;
    const match = content.match(frontmatterRegex);
    
    if (!match) {
      return { frontmatter: {}, content: content.trim() };
    }

    const frontmatterText = match[1];
    const bodyContent = match[2].trim();
    
    const frontmatter = {};
    const lines = frontmatterText.split('\n');
    
    for (const line of lines) {
      const colonIndex = line.indexOf(':');
      if (colonIndex > 0) {
        const key = line.substring(0, colonIndex).trim();
        const value = line.substring(colonIndex + 1).trim().replace(/^["']|["']$/g, '');
        frontmatter[key] = value;
      }
    }
    
    return { frontmatter, content: bodyContent };
  }

  extractTags(content) {
    const tagRegex = /#(\w+)/g;
    const tags = [];
    let match;
    while ((match = tagRegex.exec(content)) !== null) {
      tags.push(match[1]);
    }
    return [...new Set(tags)]; // Deduplicate
  }

  extractLinks(content) {
    const wikiLinkRegex = /\[\[([^\]]+)\]\]/g;
    const markdownLinkRegex = /\[([^\]]+)\]\(([^)]+)\)/g;
    
    const links = [];
    let match;
    
    // Wiki links [[Page Name]]
    while ((match = wikiLinkRegex.exec(content)) !== null) {
      links.push({ type: 'wiki', target: match[1], text: match[1] });
    }
    
    // Markdown links [text](url)
    while ((match = markdownLinkRegex.exec(content)) !== null) {
      links.push({ type: 'markdown', text: match[1], url: match[2] });
    }
    
    return links;
  }

  async indexFile(filePath) {
    const relativePath = path.relative(this.memoryPath, filePath);
    const content = await fs.promises.readFile(filePath, 'utf8');
    const hash = this.calculateHash(content);
    
    // Parse frontmatter and content
    const { frontmatter, content: bodyContent } = this.parseFrontmatter(content);
    
    // Extract metadata
    const tags = this.extractTags(bodyContent);
    const links = this.extractLinks(bodyContent);
    
    // Determine category from path
    const pathParts = relativePath.split(path.sep);
    const category = pathParts.length > 1 ? pathParts[0] : 'uncategorized';
    
    const entry = {
      id: relativePath,
      path: relativePath,
      hash,
      title: frontmatter.title || path.basename(filePath, '.md'),
      type: frontmatter.type || 'uncategorized',
      scope: frontmatter.scope || 'global',
      tags: [...tags, ...(frontmatter.tags ? frontmatter.tags.split(',').map(t => t.trim()) : [])],
      links,
      created: frontmatter.created || new Date().toISOString().split('T')[0],
      modified: new Date().toISOString(),
      size: content.length,
      excerpt: bodyContent.substring(0, 200).replace(/\n/g, ' ')
    };
    
    this.index.entries[relativePath] = entry;
    this.state.fileHashes[relativePath] = hash;
    
    return entry;
  }

  async removeFile(filePath) {
    const relativePath = path.relative(this.memoryPath, filePath);
    delete this.index.entries[relativePath];
    delete this.state.fileHashes[relativePath];
  }

  async getAllMarkdownFiles() {
    const files = [];
    
    const scanDir = async (dir) => {
      const entries = await fs.promises.readdir(dir, { withFileTypes: true });
      
      for (const entry of entries) {
        const fullPath = path.join(dir, entry.name);
        
        if (entry.isDirectory() && !entry.name.startsWith('.') && entry.name !== 'node_modules') {
          await scanDir(fullPath);
        } else if (entry.isFile() && entry.name.endsWith('.md')) {
          files.push(fullPath);
        }
      }
    };
    
    await scanDir(this.memoryPath);
    return files;
  }

  async performIncrementalIndex() {
    const startTime = Date.now();
    const allFiles = await this.getAllMarkdownFiles();
    
    let added = 0;
    let updated = 0;
    let unchanged = 0;
    let removed = 0;
    
    // Check for new or modified files
    for (const filePath of allFiles) {
      const relativePath = path.relative(this.memoryPath, filePath);
      const currentHash = await this.getFileHash(filePath);
      const previousHash = this.state.fileHashes[relativePath];
      
      if (!previousHash) {
        // New file
        await this.indexFile(filePath);
        added++;
      } else if (currentHash !== previousHash) {
        // Modified file
        await this.indexFile(filePath);
        updated++;
      } else {
        // Unchanged
        unchanged++;
      }
    }
    
    // Check for deleted files
    const currentFiles = new Set(allFiles.map(f => path.relative(this.memoryPath, f)));
    for (const relativePath of Object.keys(this.state.fileHashes)) {
      if (!currentFiles.has(relativePath)) {
        await this.removeFile(path.join(this.memoryPath, relativePath));
        removed++;
      }
    }
    
    // Save index and state
    this.state.lastRun = new Date().toISOString();
    await this.saveIndex();
    await this.saveState();
    
    const duration = Date.now() - startTime;
    
    return {
      duration,
      added,
      updated,
      unchanged,
      removed,
      total: Object.keys(this.index.entries).length
    };
  }

  async performFullIndex() {
    // Clear existing index
    this.index = { entries: {}, version: '1.0.0' };
    this.state.fileHashes = {};
    
    return await this.performIncrementalIndex();
  }

  async startWatching() {
    this.watcher = chokidar.watch(path.join(this.memoryPath, '**/*.md'), {
      ignored: /(^|[\/\\])\../, // ignore dotfiles
      persistent: true
    });
    
    this.watcher
      .on('add', filePath => this.queue.add.push(filePath))
      .on('change', filePath => this.queue.add.push(filePath))
      .on('unlink', filePath => this.queue.remove.push(filePath));
    
    // Process queue every 5 seconds
    setInterval(() => this.processQueue(), 5000);
  }

  async processQueue() {
    if (this.queue.add.length === 0 && this.queue.remove.length === 0) {
      return;
    }
    
    // Deduplicate
    const toAdd = [...new Set(this.queue.add)];
    const toRemove = [...new Set(this.queue.remove)];
    
    // Clear queue
    this.queue.add = [];
    this.queue.remove = [];
    
    // Process additions
    for (const filePath of toAdd) {
      try {
        await this.indexFile(filePath);
      } catch (err) {
        console.error(`Failed to index ${filePath}:`, err.message);
      }
    }
    
    // Process removals
    for (const filePath of toRemove) {
      await this.removeFile(filePath);
    }
    
    // Save
    await this.saveIndex();
    await this.saveState();
  }

  stopWatching() {
    if (this.watcher) {
      this.watcher.close();
      this.watcher = null;
    }
  }

  getStats() {
    const entries = Object.values(this.index.entries);
    const byType = {};
    const byScope = {};
    
    for (const entry of entries) {
      byType[entry.type] = (byType[entry.type] || 0) + 1;
      byScope[entry.scope] = (byScope[entry.scope] || 0) + 1;
    }
    
    return {
      totalEntries: entries.length,
      byType,
      byScope,
      lastIndexed: this.state.lastRun,
      indexVersion: this.index.version
    };
  }

  search(query, options = {}) {
    const results = [];
    const searchTerm = query.toLowerCase();
    
    for (const entry of Object.values(this.index.entries)) {
      let score = 0;
      
      // Title match (highest weight)
      if (entry.title.toLowerCase().includes(searchTerm)) {
        score += 10;
      }
      
      // Content excerpt match
      if (entry.excerpt.toLowerCase().includes(searchTerm)) {
        score += 5;
      }
      
      // Tag match
      if (entry.tags.some(tag => tag.toLowerCase().includes(searchTerm))) {
        score += 8;
      }
      
      // Apply filters
      if (options.type && entry.type !== options.type) {
        continue;
      }
      if (options.scope && entry.scope !== options.scope) {
        continue;
      }
      if (options.tags && !options.tags.every(tag => entry.tags.includes(tag))) {
        continue;
      }
      
      if (score > 0) {
        results.push({ ...entry, score });
      }
    }
    
    // Sort by score
    results.sort((a, b) => b.score - a.score);
    
    return options.limit ? results.slice(0, options.limit) : results;
  }
}

// Helper functions for tests
function calculateHash(content) {
  return crypto.createHash('sha256').update(content).digest('hex');
}

function parseFrontmatter(content) {
  const frontmatterRegex = /^---\s*\n([\s\S]*?)\n---\s*\n([\s\S]*)$/;
  const match = content.match(frontmatterRegex);
  
  if (!match) {
    return { frontmatter: {}, content: content.trim() };
  }

  const frontmatterText = match[1];
  const bodyContent = match[2].trim();
  
  const frontmatter = {};
  const lines = frontmatterText.split('\n');
  
  for (const line of lines) {
    const colonIndex = line.indexOf(':');
    if (colonIndex > 0) {
      const key = line.substring(0, colonIndex).trim();
      const value = line.substring(colonIndex + 1).trim().replace(/^["']|["']$/g, '');
      frontmatter[key] = value;
    }
  }
  
  return { frontmatter, content: bodyContent };
}

function extractTags(content) {
  const tagRegex = /#(\w+)/g;
  const tags = [];
  let match;
  while ((match = tagRegex.exec(content)) !== null) {
    tags.push(match[1]);
  }
  return [...new Set(tags)];
}

function extractLinks(content) {
  const wikiLinkRegex = /\[\[([^\]]+)\]\]/g;
  const markdownLinkRegex = /\[([^\]]+)\]\(([^)]+)\)/g;
  
  const links = [];
  let match;
  
  while ((match = wikiLinkRegex.exec(content)) !== null) {
    links.push({ type: 'wiki', target: match[1], text: match[1] });
  }
  
  while ((match = markdownLinkRegex.exec(content)) !== null) {
    links.push({ type: 'markdown', text: match[1], url: match[2] });
  }
  
  return links;
}

module.exports = {
  IncrementalIndexer,
  calculateHash,
  parseFrontmatter,
  extractTags,
  extractLinks
};
