/**
 * Tests for IncrementalIndexer
 */

const assert = require('assert');
const fs = require('fs');
const path = require('path');
const { test, describe, beforeEach, afterEach } = require('node:test');
const { 
  IncrementalIndexer, 
  calculateHash, 
  parseFrontmatter, 
  extractLinks, 
  extractTags 
} = require('../src/incremental-indexer');

const TEST_DIR = path.join(__dirname, 'test-memory');
const TEST_STATE_DIR = path.join(TEST_DIR, '.clawvault');
const TEST_INDEX_PATH = path.join(TEST_DIR, '.clawvault-index.json');
const TEST_STATE_PATH = path.join(TEST_STATE_DIR, 'indexer-state.json');

describe('IncrementalIndexer', () => {
  let indexer;

  beforeEach(async () => {
    // Create test directory
    await fs.promises.mkdir(TEST_DIR, { recursive: true });
    await fs.promises.mkdir(TEST_STATE_DIR, { recursive: true });
    
    // Create test files
    await createTestFile('test1.md', '# Test 1\n\nThis is test content.');
    await createTestFile('category1/file1.md', '# File 1\n\nContent with #tag1 and #tag2');
    await createTestFile('category2/file2.md', '# File 2\n\nLink to [[test1]] and [external](http://example.com)');
    
    indexer = new IncrementalIndexer({
      memoryPath: TEST_DIR,
      indexPath: TEST_INDEX_PATH,
      statePath: TEST_STATE_PATH,
      categories: ['category1', 'category2']
    });
    
    await indexer.initialize();
  });

  afterEach(async () => {
    // Clean up test directory
    await fs.promises.rm(TEST_DIR, { recursive: true, force: true });
  });

  async function createTestFile(relativePath, content) {
    const fullPath = path.join(TEST_DIR, relativePath);
    const dir = path.dirname(fullPath);
    await fs.promises.mkdir(dir, { recursive: true });
    await fs.promises.writeFile(fullPath, content);
    return fullPath;
  }

  describe('Utility Functions', () => {
    test('calculateHash generates consistent hashes', () => {
      const content = 'test content';
      const hash1 = calculateHash(content);
      const hash2 = calculateHash(content);
      
      assert.strictEqual(hash1, hash2);
      assert.strictEqual(hash1.length, 64); // SHA256 hex length
    });

    test('calculateHash produces different hashes for different content', () => {
      const hash1 = calculateHash('content1');
      const hash2 = calculateHash('content2');
      
      assert.notStrictEqual(hash1, hash2);
    });

    test('parseFrontmatter extracts frontmatter correctly', () => {
      const content = `---
title: Test Title
status: active
---
# Main Content

Body here.`;
      
      const result = parseFrontmatter(content);
      
      assert.strictEqual(result.frontmatter.title, 'Test Title');
      assert.strictEqual(result.frontmatter.status, 'active');
      assert.ok(result.content.includes('# Main Content'));
    });

    test('parseFrontmatter handles content without frontmatter', () => {
      const content = '# Just Content\n\nNo frontmatter here.';
      
      const result = parseFrontmatter(content);
      
      assert.deepStrictEqual(result.frontmatter, {});
      assert.ok(result.content.includes('Just Content'));
    });

    test('extractLinks finds wiki links', () => {
      const content = 'See [[document1]] and [[document2]] for more info.';
      const links = extractLinks(content);
      
      assert.deepStrictEqual(links, ['document1', 'document2']);
    });

    test('extractLinks finds markdown links', () => {
      const content = 'Check [this doc](other.md) and [external](http://example.com).';
      const links = extractLinks(content);
      
      assert.deepStrictEqual(links, ['other']);
    });

    test('extractLinks ignores external URLs', () => {
      const content = '[Google](https://google.com) [Local](page.md)';
      const links = extractLinks(content);
      
      assert.deepStrictEqual(links, ['page']);
    });

    test('extractTags finds hashtags', () => {
      const content = 'This has #tag1 and #tag2-content.';
      const tags = extractTags(content);
      
      assert.deepStrictEqual(tags, ['tag1', 'tag2-content']);
    });
  });

  describe('File Indexing', () => {
    test('indexFile indexes a markdown file', async () => {
      const filePath = path.join(TEST_DIR, 'test1.md');
      const doc = await indexer.indexFile(filePath);
      
      assert.ok(doc);
      assert.strictEqual(doc.id, 'test1');
      assert.strictEqual(doc.category, 'root');
      assert.ok(doc.content.includes('test content'));
      assert.ok(doc.hash);
      assert.ok(doc.modified);
    });

    test('indexFile extracts category from path', async () => {
      const filePath = path.join(TEST_DIR, 'category1/file1.md');
      const doc = await indexer.indexFile(filePath);
      
      assert.strictEqual(doc.category, 'category1');
    });

    test('indexFile extracts tags', async () => {
      const filePath = path.join(TEST_DIR, 'category1/file1.md');
      const doc = await indexer.indexFile(filePath);
      
      assert.deepStrictEqual(doc.tags, ['tag1', 'tag2']);
    });

    test('indexFile extracts links', async () => {
      const filePath = path.join(TEST_DIR, 'category2/file2.md');
      const doc = await indexer.indexFile(filePath);
      
      assert.deepStrictEqual(doc.links, ['test1']);
    });

    test('indexFile skips unchanged files', async () => {
      const filePath = path.join(TEST_DIR, 'test1.md');
      
      // First index
      await indexer.indexFile(filePath);
      await indexer.saveState();
      
      // Second index (should be skipped)
      const doc = await indexer.indexFile(filePath);
      
      assert.strictEqual(doc, null);
      assert.strictEqual(indexer.metrics.filesSkipped, 1);
    });

    test('indexFile detects changed files', async () => {
      const filePath = path.join(TEST_DIR, 'test1.md');
      
      // First index
      await indexer.indexFile(filePath);
      await indexer.saveState();
      
      // Modify file
      await fs.promises.writeFile(filePath, '# Updated Test\n\nNew content.');
      
      // Update file hash in state manually to simulate changed file detection
      const content = await fs.promises.readFile(filePath, 'utf8');
      const relativePath = path.relative(TEST_DIR, filePath);
      indexer.state.fileHashes[relativePath] = 'old-hash'; // Set wrong hash
      
      // Second index (should detect change)
      const doc = await indexer.indexFile(filePath);
      
      assert.ok(doc);
      assert.strictEqual(indexer.metrics.filesUpdated, 1);
    });
  });

  describe('Full Reindex', () => {
    test('fullReindex indexes all files', async () => {
      const documents = await indexer.fullReindex();
      
      assert.strictEqual(documents.length, 3);
      assert.ok(documents.some(d => d.id === 'test1'));
      assert.ok(documents.some(d => d.id === 'file1'));
      assert.ok(documents.some(d => d.id === 'file2'));
    });

    test('fullReindex clears previous state', async () => {
      // Add some initial state
      indexer.state.fileHashes['old-file'] = 'old-hash';
      
      await indexer.fullReindex();
      
      assert.strictEqual(indexer.state.fileHashes['old-file'], undefined);
    });

    test('fullReindex saves state correctly', async () => {
      await indexer.fullReindex();
      
      const stateData = await fs.promises.readFile(TEST_STATE_PATH, 'utf8');
      const state = JSON.parse(stateData);
      
      assert.ok(state.lastFullIndex);
      assert.strictEqual(Object.keys(state.fileHashes).length, 3);
      assert.strictEqual(state.indexedPaths.length, 3);
    });
  });

  describe('Incremental Reindex', () => {
    test('incrementalReindex skips unchanged files', async () => {
      // First full index
      await indexer.fullReindex();
      
      // Reset metrics for incremental test
      indexer.metrics.filesSkipped = 0;
      indexer.metrics.filesIndexed = 0;
      indexer.metrics.filesUpdated = 0;
      
      // Incremental reindex
      await indexer.incrementalReindex();
      
      assert.strictEqual(indexer.metrics.filesSkipped, 3);
      assert.strictEqual(indexer.metrics.filesIndexed, 0);
      assert.strictEqual(indexer.metrics.filesUpdated, 0);
    });

    test('incrementalReindex detects new files', async () => {
      // First full index
      const docs = await indexer.fullReindex();
      const initialCount = docs.length;
      
      // Add new file
      await createTestFile('newfile.md', '# New File\n\nNew content.');
      
      // Incremental reindex
      const documents = await indexer.incrementalReindex();
      
      assert.strictEqual(documents.length, initialCount + 1);
      assert.ok(documents.some(d => d.id === 'newfile'));
    });

    test('incrementalReindex detects deleted files', async () => {
      // First full index
      const docs = await indexer.fullReindex();
      const initialCount = docs.length;
      
      // Delete a file
      await fs.promises.unlink(path.join(TEST_DIR, 'test1.md'));
      
      // Incremental reindex
      const documents = await indexer.incrementalReindex();
      
      assert.strictEqual(documents.length, initialCount - 1);
      assert.ok(!documents.some(d => d.id === 'test1'));
    });

    test('incrementalReindex updates modified files', async () => {
      // First full index
      await indexer.fullReindex();
      
      // Modify a file
      await fs.promises.writeFile(
        path.join(TEST_DIR, 'test1.md'),
        '# Modified\n\nUpdated content.'
      );
      
      // Incremental reindex
      const documents = await indexer.incrementalReindex();
      
      const doc = documents.find(d => d.id === 'test1');
      assert.ok(doc.content.includes('Updated content'));
    });
  });

  describe('State Management', () => {
    test('saveState and loadState work correctly', async () => {
      indexer.state.fileHashes['test'] = 'abc123';
      indexer.state.indexedPaths.add('/test/path');
      
      await indexer.saveState();
      
      // Create new indexer to test loading
      const newIndexer = new IncrementalIndexer({
        memoryPath: TEST_DIR,
        indexPath: TEST_INDEX_PATH,
        statePath: TEST_STATE_PATH
      });
      
      await newIndexer.loadState();
      
      assert.strictEqual(newIndexer.state.fileHashes['test'], 'abc123');
      assert.ok(newIndexer.state.indexedPaths.has('/test/path'));
    });

    test('resume continues interrupted indexing', async () => {
      // Simulate interrupted state
      indexer.state.inProgress = true;
      indexer.state.lastFullIndex = new Date().toISOString();
      await indexer.saveState();
      
      // Resume should do incremental reindex
      const documents = await indexer.resume();
      
      assert.ok(documents);
      assert.strictEqual(documents.length, 3);
    });

    test('resume returns null when not interrupted', async () => {
      indexer.state.inProgress = false;
      await indexer.saveState();
      
      const result = await indexer.resume();
      
      assert.strictEqual(result, null);
    });
  });

  describe('Metrics', () => {
    test('metrics are tracked correctly', async () => {
      await indexer.fullReindex();
      
      const metrics = indexer.getMetrics();
      
      // Full reindex indexes new files
      assert.ok(metrics.filesIndexed > 0);
      assert.ok(metrics.startTime);
      assert.ok(metrics.endTime);
      assert.ok(metrics.tokensSaved >= 0);
    });
  });
});
