/**
 * Memory Cache Module — LRU + In-Memory Performance Layer
 * 
 * Features:
 * - Least Recently Used (LRU) eviction policy
 * - Configurable max size and TTL
 * - Hit/miss rate tracking for monitoring
 * - Integrates with vector store for fast reads
 */

import * as fs from 'fs';
import * as path from 'path';
import { Memory } from './types';

const CACHE_DIR = path.join(process.env.HOME || '~', '.openclaw/workspace/clawvault/.cache');
const CACHE_STATS_FILE = path.join(CACHE_DIR, 'stats.json');

export interface CacheConfig {
  maxSize?: number;           // Maximum number of entries (default: 1000)
  maxBytes?: number;          // Maximum memory in bytes (default: 50MB)
  ttlMs?: number;             // Time-to-live in milliseconds (default: 30min)
  persistToDisk?: boolean;    // Save cache to disk on shutdown
}

export interface CacheStats {
  hits: number;
  misses: number;
  evictions: number;
  currentSize: number;
  currentBytes: number;
  hitRate: number;
}

class LRUCacheEntry<T> {
  constructor(
    public key: string,
    public value: T,
    public timestamp: number,
    public sizeBytes: number
  ) {}

  isExpired(ttlMs: number): boolean {
    return Date.now() - this.timestamp > ttlMs;
  }
}

export class MemoryCache {
  private cache: Map<string, LRUCacheEntry<any>> = new Map();
  private stats: CacheStats = {
    hits: 0,
    misses: 0,
    evictions: 0,
    currentSize: 0,
    currentBytes: 0,
    hitRate: 0
  };

  private config: Required<CacheConfig>;
  private cleanupInterval: NodeJS.Timeout | null = null;

  constructor(config: CacheConfig = {}) {
    this.config = {
      maxSize: config.maxSize ?? 1000,
      maxBytes: config.maxBytes ?? 50 * 1024 * 1024, // 50MB
      ttlMs: config.ttlMs ?? 30 * 60 * 1000, // 30 minutes
      persistToDisk: config.persistToDisk ?? true
    };

    // Ensure cache directory exists
    if (!fs.existsSync(CACHE_DIR)) {
      fs.mkdirSync(CACHE_DIR, { recursive: true });
    }

    // Load existing stats
    this.loadStats();

    // Start background cleanup
    this.startCleanup();
  }

  // ── Core Operations ───────────────────────────────────────────────────────

  /**
   * Get a cached value by key
   */
  get<T>(key: string): T | null {
    const entry = this.cache.get(key);
    
    if (!entry) {
      this.stats.misses++;
      this.updateHitRate();
      return null;
    }

    if (entry.isExpired(this.config.ttlMs)) {
      this.delete(key);
      this.stats.misses++;
      this.updateHitRate();
      return null;
    }

    // Move to end of LRU list (most recently used)
    this.cache.delete(key);
    this.cache.set(key, entry);
    
    this.stats.hits++;
    this.updateHitRate();
    return entry.value as T;
  }

  /**
   * Set a value in cache
   */
  set<T>(key: string, value: T): void {
    const serialized = JSON.stringify(value);
    const sizeBytes = Buffer.byteLength(serialized, 'utf8');

    // Evict if needed
    while (this.cache.size >= this.config.maxSize || 
           this.stats.currentBytes + sizeBytes >= this.config.maxBytes) {
      this.evictOldest();
    }

    // Remove old entry if updating
    if (this.cache.has(key)) {
      const oldEntry = this.cache.get(key)!;
      this.stats.currentBytes -= oldEntry.sizeBytes;
    }

    // Add new entry
    const entry = new LRUCacheEntry(key, value, Date.now(), sizeBytes);
    this.cache.set(key, entry);
    this.stats.currentBytes += sizeBytes;
    this.stats.currentSize = this.cache.size;

    this.saveStats();
  }

  /**
   * Delete a specific key from cache
   */
  delete(key: string): boolean {
    const entry = this.cache.get(key);
    if (!entry) return false;

    this.cache.delete(key);
    this.stats.currentBytes -= entry.sizeBytes;
    this.stats.currentSize = this.cache.size;
    
    this.saveStats();
    return true;
  }

  /**
   * Clear entire cache
   */
  clear(): void {
    this.cache.clear();
    this.stats.currentSize = 0;
    this.stats.currentBytes = 0;
    this.stats.evictions = 0;
    
    this.saveStats();
  }

  /**
   * Check if key exists (not expired)
   */
  has(key: string): boolean {
    const entry = this.cache.get(key);
    if (!entry) return false;
    
    if (entry.isExpired(this.config.ttlMs)) {
      this.delete(key);
      return false;
    }
    
    return true;
  }

  // ── Bulk Operations ──────────────────────────────────────────────────────

  /**
   * Get multiple values by keys
   */
  getMany<T>(keys: string[]): Map<string, T> {
    const results = new Map<string, T>();
    
    for (const key of keys) {
      const value = this.get<T>(key);
      if (value !== null) {
        results.set(key, value);
      }
    }
    
    return results;
  }

  /**
   * Set multiple values
   */
  setMany(entries: Array<{ key: string; value: any }>): void {
    for (const { key, value } of entries) {
      this.set(key, value);
    }
  }

  /**
   * Filter cache by predicate function
   */
  filter<T>(predicate: (key: string, value: T) => boolean): Map<string, T> {
    const result = new Map<string, T>();
    
    for (const [key, entry] of this.cache.entries()) {
      if (predicate(key, entry.value)) {
        result.set(key, entry.value);
      }
    }
    
    return result;
  }

  // ── Utility Methods ──────────────────────────────────────────────────────

  /**
   * Get cache statistics
   */
  getStats(): CacheStats {
    return { ...this.stats };
  }

  /**
   * Get all keys currently in cache
   */
  keys(): string[] {
    return Array.from(this.cache.keys());
  }

  /**
   * Get cache size (number of entries)
   */
  size(): number {
    return this.cache.size;
  }

  /**
   * Calculate approximate memory usage
   */
  memoryUsage(): number {
    return this.stats.currentBytes;
  }

  /**
   * Persist cache to disk
   */
  async persist(): Promise<void> {
    try {
      const data = Array.from(this.cache.entries()).map(([key, entry]) => ({
        key: entry.key,
        value: entry.value,
        timestamp: entry.timestamp,
        sizeBytes: entry.sizeBytes
      }));

      const serialized = JSON.stringify(data);
      fs.writeFileSync(path.join(CACHE_DIR, 'cache.json'), serialized);
      console.log(`✅ Cache persisted (${data.length} entries, ${this.formatBytes(this.stats.currentBytes)})`);
    } catch (error) {
      console.error('❌ Cache persist failed:', (error as Error).message);
    }
  }

  /**
   * Load cache from disk
   */
  async restore(): Promise<void> {
    try {
      const cacheFile = path.join(CACHE_DIR, 'cache.json');
      if (!fs.existsSync(cacheFile)) {
        console.log('ℹ️  No cache file found, starting fresh');
        return;
      }

      const serialized = fs.readFileSync(cacheFile, 'utf8');
      const data = JSON.parse(serialized);

      for (const entry of data) {
        this.cache.set(entry.key, new LRUCacheEntry(
          entry.key,
          entry.value,
          entry.timestamp,
          entry.sizeBytes
        ));
      }

      this.stats.currentSize = this.cache.size;
      this.stats.currentBytes = data.reduce((sum: number, e: any) => sum + e.sizeBytes, 0);
      
      console.log(`✅ Cache restored (${this.cache.size} entries)`);
    } catch (error) {
      console.error('❌ Cache restore failed:', (error as Error).message);
    }
  }

  /**
   * Graceful shutdown
   */
  async close(): Promise<void> {
    if (this.cleanupInterval) {
      clearInterval(this.cleanupInterval);
    }

    if (this.config.persistToDisk) {
      await this.persist();
    }

    this.saveStats();
  }

  // ── Background Cleanup ───────────────────────────────────────────────────

  private startCleanup(): void {
    // Run cleanup every minute
    this.cleanupInterval = setInterval(() => {
      this.cleanup();
    }, 60000);
  }

  /**
   * Remove expired entries
   */
  private cleanup(): void {
    let expiredCount = 0;
    
    for (const [key, entry] of this.cache.entries()) {
      if (entry.isExpired(this.config.ttlMs)) {
        this.cache.delete(key);
        this.stats.currentBytes -= entry.sizeBytes;
        expiredCount++;
      }
    }

    if (expiredCount > 0) {
      this.stats.currentSize = this.cache.size;
      this.saveStats();
    }
  }

  // ── Internal Helpers ─────────────────────────────────────────────────────

  private evictOldest(): void {
    // Get first entry (oldest due to LRU ordering)
    const firstKey = this.cache.keys()[0];
    if (!firstKey) return;

    const entry = this.cache.get(firstKey)!;
    this.cache.delete(firstKey);
    this.stats.currentBytes -= entry.sizeBytes;
    this.stats.evictions++;
    this.stats.currentSize = this.cache.size;

    this.saveStats();
  }

  private updateHitRate(): void {
    const total = this.stats.hits + this.stats.misses;
    this.stats.hitRate = total > 0 ? this.stats.hits / total : 0;
  }

  private saveStats(): void {
    try {
      fs.writeFileSync(
        CACHE_STATS_FILE,
        JSON.stringify(this.stats, null, 2)
      );
    } catch (error) {
      // Non-fatal
    }
  }

  private loadStats(): void {
    try {
      if (fs.existsSync(CACHE_STATS_FILE)) {
        this.stats = JSON.parse(fs.readFileSync(CACHE_STATS_FILE, 'utf8'));
      }
    } catch (error) {
      // Start with fresh stats
    }
  }

  private formatBytes(bytes: number): string {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(2)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
  }
}

// Export singleton instance for global use
export const globalCache = new MemoryCache({
  maxSize: 1000,
  maxBytes: 50 * 1024 * 1024, // 50MB
  ttlMs: 30 * 60 * 1000, // 30 minutes
  persistToDisk: true
});

// Convenience wrappers
export function getCached<T>(key: string, fetcher: () => T, cache: MemoryCache = globalCache): T {
  const cached = cache.get<T>(key);
  if (cached !== null) return cached;

  const value = fetcher();
  cache.set(key, value);
  return value;
}
