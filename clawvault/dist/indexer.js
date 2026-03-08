"use strict";
/**
 * Phase 1: Incremental Indexing
 * Manages efficient indexing of memory entries
 */
Object.defineProperty(exports, "__esModule", { value: true });
exports.IncrementalIndexer = exports.VAULT_PATH = exports.CLAWVAULT_DIR = exports.MEMORY_ROOT = exports.HOME = void 0;
// Shared constants for file paths
exports.HOME = process.env.HOME || '~';
exports.MEMORY_ROOT = `${exports.HOME}/memory`;
exports.CLAWVAULT_DIR = `${exports.HOME}/.openclaw/workspace/clawvault`;
exports.VAULT_PATH = `${exports.CLAWVAULT_DIR}/vault`;
class IncrementalIndexer {
    entries = new Map();
    typeIndex = new Map();
    scopeIndex = new Map();
    tagIndex = new Map();
    timeIndex = new Map(); // YYYY-MM-DD
    pendingUpdates = new Set();
    lastIndexed = 0;
    constructor() {
        // Initialize type indices
        for (const type of ['episodic', 'semantic', 'procedural', 'working']) {
            this.typeIndex.set(type, new Set());
        }
        // Initialize scope indices
        for (const scope of ['session', 'user', 'global']) {
            this.scopeIndex.set(scope, new Set());
        }
    }
    index(entry) {
        const existing = this.entries.get(entry.id);
        if (existing) {
            // Remove from old indices
            this.removeFromIndices(existing);
        }
        // Add to main storage
        this.entries.set(entry.id, entry);
        // Add to indices
        this.addToIndices(entry);
        // Track update
        this.pendingUpdates.add(entry.id);
        this.lastIndexed = Date.now();
    }
    remove(id) {
        const entry = this.entries.get(id);
        if (!entry)
            return false;
        this.removeFromIndices(entry);
        this.entries.delete(id);
        this.pendingUpdates.delete(id);
        return true;
    }
    get(id) {
        return this.entries.get(id);
    }
    getByType(type) {
        const ids = this.typeIndex.get(type) || new Set();
        return Array.from(ids).map(id => this.entries.get(id)).filter(Boolean);
    }
    getByScope(scope) {
        const ids = this.scopeIndex.get(scope) || new Set();
        return Array.from(ids).map(id => this.entries.get(id)).filter(Boolean);
    }
    getByTags(tags) {
        const result = new Set();
        for (const tag of tags) {
            const ids = this.tagIndex.get(tag);
            if (ids) {
                for (const id of ids) {
                    result.add(id);
                }
            }
        }
        return Array.from(result).map(id => this.entries.get(id)).filter(Boolean);
    }
    getByTimeRange(start, end) {
        const results = [];
        for (const entry of this.entries.values()) {
            if (entry.timestamp >= start && entry.timestamp <= end) {
                results.push(entry);
            }
        }
        return results;
    }
    getRecent(limit = 10) {
        return Array.from(this.entries.values())
            .sort((a, b) => b.timestamp - a.timestamp)
            .slice(0, limit);
    }
    getAll() {
        return Array.from(this.entries.values());
    }
    addToIndices(entry) {
        // Type index
        this.typeIndex.get(entry.type)?.add(entry.id);
        // Scope index
        this.scopeIndex.get(entry.scope)?.add(entry.id);
        // Tag index
        for (const tag of entry.metadata.tags) {
            if (!this.tagIndex.has(tag)) {
                this.tagIndex.set(tag, new Set());
            }
            this.tagIndex.get(tag).add(entry.id);
        }
        // Time index (YYYY-MM-DD)
        const dateKey = new Date(entry.timestamp).toISOString().split('T')[0];
        if (!this.timeIndex.has(dateKey)) {
            this.timeIndex.set(dateKey, new Set());
        }
        this.timeIndex.get(dateKey).add(entry.id);
    }
    removeFromIndices(entry) {
        this.typeIndex.get(entry.type)?.delete(entry.id);
        this.scopeIndex.get(entry.scope)?.delete(entry.id);
        for (const tag of entry.metadata.tags) {
            this.tagIndex.get(tag)?.delete(entry.id);
        }
        const dateKey = new Date(entry.timestamp).toISOString().split('T')[0];
        this.timeIndex.get(dateKey)?.delete(entry.id);
    }
    getStats() {
        const byType = {
            episodic: this.typeIndex.get('episodic')?.size || 0,
            semantic: this.typeIndex.get('semantic')?.size || 0,
            procedural: this.typeIndex.get('procedural')?.size || 0,
            working: this.typeIndex.get('working')?.size || 0
        };
        const byScope = {
            session: this.scopeIndex.get('session')?.size || 0,
            user: this.scopeIndex.get('user')?.size || 0,
            global: this.scopeIndex.get('global')?.size || 0
        };
        return {
            totalEntries: this.entries.size,
            byType,
            byScope,
            lastIndexed: this.lastIndexed,
            pendingUpdates: this.pendingUpdates.size
        };
    }
    flushPending() {
        const updates = Array.from(this.pendingUpdates);
        this.pendingUpdates.clear();
        return updates;
    }
    searchByText(text) {
        const query = text.toLowerCase();
        return Array.from(this.entries.values()).filter(entry => entry.content.toLowerCase().includes(query) ||
            entry.metadata.tags.some(tag => tag.toLowerCase().includes(query)));
    }
}
exports.IncrementalIndexer = IncrementalIndexer;
//# sourceMappingURL=indexer.js.map