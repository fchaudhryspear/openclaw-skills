/**
 * Vector Store Module — Semantic Search with SQLite
 * 
 * Features:
 * - Embedded SQLite database (no external service needed)
 * - Cosine similarity search with k-nearest neighbors
 * - Incremental indexing (add/remove/update on the fly)
 * - Persistent storage across sessions
 */

import Database from 'better-sqlite3';
import * as path from 'path';
import { MEMORY_ROOT } from './indexer';
import { generateEmbedding, cosineSimilarity, extractKeywords } from './embeddings';
import { Memory } from './types';

const DB_PATH = path.join(MEMORY_ROOT, '.clawvault.db');
const EMBEDDING_DIM = 128; // Matches our embedding dimension

export class VectorStore {
  private db: Database.Database;
  private cache: Map<string, number[]> = new Map();
  private maxCacheSize = 5000;

  constructor() {
    this.db = new Database(DB_PATH);
    this.db.pragma('journal_mode = WAL');
    this.db.pragma('synchronous = NORMAL');
    
    this.initSchema();
  }

  private initSchema(): void {
    this.db.exec(`
      CREATE TABLE IF NOT EXISTS memory_vectors (
        id TEXT PRIMARY KEY,
        content TEXT NOT NULL,
        embedding BLOB NOT NULL,
        keywords TEXT NOT NULL,
        created_at INTEGER NOT NULL,
        score REAL DEFAULT 0
      )
    `);

    this.db.exec(`
      CREATE INDEX IF NOT EXISTS idx_created_at ON memory_vectors(created_at)
    `);

    this.db.exec(`
      CREATE VIRTUAL TABLE IF NOT EXISTS memory_fts USING fts5(
        content,
        keywords,
        tokenize='porter'
      )
    `);

    console.log('✅ Vector store initialized');
  }

  // ── Core Operations ───────────────────────────────────────────────────────

  async index(memory: Memory): Promise<void> {
    const embed = this.getEmbeddingMemory(memory.content);
    const stmt = this.db.prepare(`
      INSERT OR REPLACE INTO memory_vectors (id, content, embedding, keywords, created_at)
      VALUES (?, ?, ?, ?, ?)
    `);

    const keywords = extractKeywords(memory.content).join(',');
    stmt.run(memory.id, memory.content, Buffer.from(embed), keywords, Date.now());

    // Also update FTS index
    const ftsStmt = this.db.prepare(`
      INSERT OR REPLACE INTO memory_fts (rowid, content, keywords)
      VALUES (?, ?, ?)
    `);
    ftsStmt.run(memory.id, memory.content, keywords);

    // Invalidate LRU cache if needed
    if (this.cache.size > this.maxCacheSize) {
      const keys = Array.from(this.cache.keys()).slice(0, Math.floor(this.maxCacheSize * 0.2));
      keys.forEach(k => this.cache.delete(k));
    }
  }

  async query(queryText: string, topK: number = 10, filter?: { type?: string; scope?: string }): Promise<{ memory: Memory; score: number }[]> {
    const queryEmbedding = this.getEmbeddingMemory(queryText);

    // Get all vectors and calculate similarity
    const stmt = this.db.prepare('SELECT id, content, created_at FROM memory_vectors');
    const rows: any[] = stmt.all();

    const scored: { id: string; content: string; score: number }[] = [];

    for (const row of rows) {
      const storedEmbedding = new Float64Array(new Uint8Array(row.embedding).buffer);
      const sim = cosineSimilarity(Array.from(storedEmbedding), queryEmbedding);
      
      // Apply time decay bonus
      const recencyBoost = this.calculateRecencyBoost(row.created_at);
      const finalScore = sim * 0.7 + recencyBoost * 0.3;
      
      scored.push({
        id: row.id,
        content: row.content,
        score: finalScore
      });
    }

    // Sort by score descending
    scored.sort((a, b) => b.score - a.score);

    // Convert back to Memory objects
    const results: { memory: Memory; score: number }[] = scored.slice(0, topK).map(item => ({
      memory: {
        id: item.id,
        content: item.content,
        type: 'declarative',
        createdAtMs: Date.now()
      },
      score: item.score
    }));

    return results;
  }

  async queryByKeywords(keywords: string[], threshold: number = 0.5): Promise<Memory[]> {
    const keywordSet = new Set(keywords.map(k => k.toLowerCase()));
    
    const stmt = this.db.prepare(`
      SELECT id, content, created_at FROM memory_vectors
      WHERE keywords LIKE ?
    `);

    const matchPattern = `%${keywordSet.values().next().value}%`;
    const rows: any[] = stmt.all(matchPattern);

    return rows.map(row => ({
      id: row.id,
      content: row.content,
      type: 'declarative',
      createdAtMs: row.created_at
    }));
  }

  async delete(memoryId: string): Promise<boolean> {
    const stmt = this.db.prepare(`DELETE FROM memory_vectors WHERE id = ?`);
    const result = stmt.run(memoryId);
    
    // Remove from cache
    this.cache.delete(memoryId);
    
    // Remove from FTS
    const ftsStmt = this.db.prepare(`DELETE FROM memory_fts WHERE rowid = ?`);
    ftsStmt.run(memoryId);

    return result.changes > 0;
  }

  async getById(id: string): Promise<Memory | null> {
    const stmt = this.db.prepare(`SELECT id, content, created_at FROM memory_vectors WHERE id = ?`);
    const row: any = stmt.get(id);
    
    if (!row) return null;

    return {
      id: row.id,
      content: row.content,
      type: 'declarative',
      createdAtMs: row.created_at
    };
  }

  async listAll(limit: number = 100, offset: number = 0): Promise<Memory[]> {
    const stmt = this.db.prepare(`
      SELECT id, content, created_at FROM memory_vectors
      ORDER BY created_at DESC
      LIMIT ? OFFSET ?
    `);

    const rows: any[] = stmt.all(limit, offset);
    return rows.map(row => ({
      id: row.id,
      content: row.content,
      type: 'declarative',
      createdAtMs: row.created_at
    }));
  }

  async getCount(): Promise<number> {
    const stmt = this.db.prepare('SELECT COUNT(*) as count FROM memory_vectors');
    const row: any = stmt.get();
    return row.count;
  }

  // ── Utility Methods ──────────────────────────────────────────────────────

  /**
   * Bulk insert for import operations
   */
  async bulkInsert(memories: Memory[]): Promise<void> {
    const stmt = this.db.prepare(`
      INSERT OR REPLACE INTO memory_vectors (id, content, embedding, keywords, created_at)
      VALUES (?, ?, ?, ?, ?)
    `);

    const ftsStmt = this.db.prepare(`
      INSERT OR REPLACE INTO memory_fts (rowid, content, keywords)
      VALUES (?, ?, ?)
    `);

    this.db.transaction(() => {
      for (const m of memories) {
        const embed = this.getEmbeddingMemory(m.content);
        const keywords = extractKeywords(m.content).join(',');
        
        stmt.run(m.id, m.content, Buffer.from(embed), keywords, Date.now());
        ftsStmt.run(m.id, m.content, keywords);
      }
    })();
  }

  /**
   * Export all memories for backup
   */
  async exportToJson(): Promise<string> {
    const stmt = this.db.prepare(`SELECT * FROM memory_vectors ORDER BY created_at ASC`);
    const rows: any[] = stmt.all();
    return JSON.stringify(rows, null, 2);
  }

  /**
   * Close database connection
   */
  close(): void {
    this.cache.clear();
    this.db.close();
  }

  // ── Internal Helpers ─────────────────────────────────────────────────────

  private getEmbeddingMemory(text: string): number[] {
    // Check cache first
    if (this.cache.has(text)) {
      return this.cache.get(text)!;
    }

    const embedding = generateEmbedding(text);
    
    // Add to cache with LRU
    if (this.cache.size < this.maxCacheSize) {
      this.cache.set(text, embedding);
    }

    return embedding;
  }

  private calculateRecencyBoost(timestamp: number, halfLife: number = 86400000): number {
    const age = Date.now() - timestamp;
    return Math.exp(-age / halfLife);
  }
}

// Singleton instance for reuse
let vectorStoreInstance: VectorStore | null = null;

export function getVectorStore(): VectorStore {
  if (!vectorStoreInstance) {
    vectorStoreInstance = new VectorStore();
  }
  return vectorStoreInstance;
}
