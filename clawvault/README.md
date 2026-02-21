# ClawVault

AI Agent Memory System with Context-Aware Search

[![Tests](https://img.shields.io/badge/tests-passing-brightgreen)]()
[![Version](https://img.shields.io/badge/version-2.0.0-blue)]()

## Features

### Phase 1: Core Memory System
- ✅ **Incremental Indexing** - Efficient memory storage with type/scope/tag indices
- ✅ **Confidence Scoring** - Multi-factor confidence calculation for memory reliability
- ✅ **Sensitive Data Detection** - Automatic PII/credential detection and redaction
- ✅ **Semantic Memory Layers** - Entity extraction, categorization, and sentiment analysis

### Phase 2: Context-Aware Search
- ✅ **Hybrid Search** - Combines vector similarity, keyword matching, and temporal relevance
- ✅ **Re-ranking Layer** - Weighted score combination (Vector 60%, Keyword 25%, Temporal 15%)
- ✅ **Context Injection** - Boosts relevance using recent conversation context
- ✅ **Result Caching** - LRU cache for top-5 results per query
- ✅ **Advanced Filtering** - By type, scope, tags, confidence, age

## Installation

```bash
npm install clawvault
```

## Quick Start

```typescript
import { ClawVault } from 'clawvault';

// Initialize
const vault = new ClawVault({
  enableSensitiveDetection: true,
  minConfidenceThreshold: 0.3
});

// Store a memory
const entry = vault.store('React is a JavaScript library for building UIs', {
  type: 'semantic',
  tags: ['frontend', 'react', 'javascript'],
  scope: 'user'
});

// Search with context
const contextMessages = [
  { role: 'user', content: 'What should I use for frontend?', timestamp: Date.now() }
];

const results = vault.search('frontend framework', contextMessages, {
  limit: 5,
  minConfidence: 0.5
});

console.log(results[0].entry.content);
console.log('Relevance:', results[0].scores.combined);
```

## API Documentation

### Core Methods

| Method | Description |
|--------|-------------|
| `store(content, options)` | Store a new memory entry |
| `retrieve(id)` | Get a memory by ID |
| `update(id, updates)` | Update an existing memory |
| `delete(id)` | Remove a memory |
| `search(query, context, options)` | Context-aware search |

### Search Options

```typescript
interface SearchOptions {
  limit?: number;              // Max results (default: 10)
  offset?: number;             // Pagination offset
  weights?: {                  // Custom signal weights
    vector: number;            // Semantic similarity (default: 0.6)
    keyword: number;           // TF-IDF matching (default: 0.25)
    temporal: number;          // Recency boost (default: 0.15)
  };
  types?: MemoryType[];        // Filter by type
  scopes?: MemoryScope[];      // Filter by scope
  tags?: string[];             // Filter by tags
  minConfidence?: number;      // Minimum confidence threshold
  excludeSensitive?: boolean;  // Exclude sensitive memories
}
```

## Search Algorithm

ClawVault uses a hybrid search algorithm combining three signals:

```
Final Score = (Vector × 0.6 + Keyword × 0.25 + Temporal × 0.15) × ContextBoost
```

### Signal Details

1. **Vector Similarity** (60%): Cosine similarity on 128-dim embeddings
2. **Keyword Matching** (25%): TF-IDF scoring for lexical matches
3. **Temporal Relevance** (15%): Exponential decay (7-day half-life)
4. **Context Boost** (up to 20%): Conversation context relevance

See [docs/SEARCH.md](docs/SEARCH.md) for detailed algorithm documentation.

## Running Tests

```bash
# Install dependencies
npm install

# Run tests
npm test

# Run with coverage
npm test -- --coverage
```

## Project Structure

```
clawvault/
├── src/
│   ├── index.ts          # Main ClawVault class
│   ├── types.ts          # TypeScript definitions
│   ├── embeddings.ts     # Vector utilities
│   ├── confidence.ts     # Phase 1: Confidence scoring
│   ├── sensitive.ts      # Phase 1: Sensitive data detection
│   ├── semantic.ts       # Phase 1: Semantic layer
│   ├── indexer.ts        # Phase 1: Incremental indexing
│   └── search.ts         # Phase 2: Context-aware search
├── test/
│   └── clawvault.test.ts # Comprehensive test suite
├── docs/
│   └── SEARCH.md         # Search algorithm documentation
└── package.json
```

## License

MIT

## Changelog

### v2.0.0 - Phase 2 Release
- Added Context-Aware Search with hybrid scoring
- Implemented re-ranking layer with configurable weights
- Added conversation context injection
- Implemented LRU result caching
- Added comprehensive search filtering

### v1.0.0 - Phase 1 Release
- Core memory storage and retrieval
- Incremental indexing system
- Confidence scoring algorithm
- Sensitive data detection
- Semantic layer extraction
