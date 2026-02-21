# ClawVault Memory Confidence Scoring

## Overview

The Memory Confidence Scoring feature provides a heuristic scoring system for memories stored in ClawVault. Each memory receives a confidence score between 0.0 and 1.0 based on three factors:

1. **Source Reliability** - How trustworthy the source of the memory is
2. **Recency Decay** - How recently the memory was created
3. **User Feedback** - Explicit validation or invalidation from users

## Confidence Score Formula

```
confidence = (source_base_score × recency_multiplier) + feedback_adjustment
```

The result is clamped to the range [0.0, 1.0].

## Scoring Components

### 1. Source Reliability (Base Score)

| Source Type | Base Score | Description |
|-------------|------------|-------------|
| `user_explicit` | 1.0 | Directly stated by the user - highest reliability |
| `inferred` | 0.7 | Derived from context or patterns - medium reliability |
| `auto_extracted` | 0.5 | Automatically extracted from data - lowest reliability |

### 2. Recency Decay

Memories fade in confidence over time using a linear decay model:

- **0 days (today)**: 1.0 (no decay)
- **30 days**: 0.7 (30% decay)
- **90 days**: 0.5 (50% decay)
- **>90 days**: Stays at 0.5 (minimum floor)

The decay is linear between these points:
- Days 0-30: Linear decay from 1.0 to 0.7
- Days 30-90: Linear decay from 0.7 to 0.5

### 3. User Feedback Adjustment

| Feedback | Adjustment | Effect |
|----------|------------|--------|
| `thumbs_up` | +0.1 | Validates memory, boosts confidence |
| `thumbs_down` | -0.2 | Invalidates memory, reduces confidence |
| `null` (none) | 0 | No adjustment |

## Usage Examples

### Storing Memories with Confidence

```typescript
import { MemoryStore } from 'clawvault';

const store = new MemoryStore();

// High confidence - user explicitly stated
const explicit = store.store({
  content: "User prefers dark mode",
  source: "user_explicit",
  tags: ["preferences", "ui"]
});
// confidence: 1.0

// Medium confidence - inferred from context
const inferred = store.store({
  content: "User probably likes coffee",
  source: "inferred",
  tags: ["preferences"]
});
// confidence: 0.7

// Lower confidence - auto-extracted
const extracted = store.store({
  content: "Detected configuration value",
  source: "auto_extracted"
});
// confidence: 0.5
```

### Querying by Confidence Threshold

```typescript
// Get only high-confidence memories
const highConfidence = store.query({ minConfidence: 0.8 });

// Get medium confidence and above
const mediumAndAbove = store.query({ minConfidence: 0.6 });

// Query with combined filters
const filtered = store.query({
  minConfidence: 0.7,
  source: "user_explicit",
  tags: ["preferences"]
});
```

### User Feedback

```typescript
// Store initial memory
const memory = store.store({
  content: "User likes jazz music",
  source: "inferred"
});
// confidence: 0.7

// User confirms this is correct
store.setFeedback(memory.id, "thumbs_up");
// confidence: 0.8 (0.7 + 0.1)

// User says this is incorrect
store.setFeedback(memory.id, "thumbs_down");
// confidence: 0.5 (0.7 - 0.2)
```

### Custom Configuration

```typescript
import { MemoryStore, DEFAULT_CONFIDENCE_CONFIG } from 'clawvault';

const customStore = new MemoryStore({
  userExplicitBase: 0.95,
  inferredBase: 0.65,
  autoExtractedBase: 0.45,
  decay30Days: 0.65,
  decay90Days: 0.40,
  thumbsUpBonus: 0.15,
  thumbsDownPenalty: -0.25
});
```

## Configuration Options

| Option | Default | Description |
|--------|---------|-------------|
| `userExplicitBase` | 1.0 | Base score for user_explicit source |
| `inferredBase` | 0.7 | Base score for inferred source |
| `autoExtractedBase` | 0.5 | Base score for auto_extracted source |
| `decay30Days` | 0.7 | Multiplier at 30 days |
| `decay90Days` | 0.5 | Multiplier at 90 days and beyond |
| `thumbsUpBonus` | +0.1 | Confidence boost for positive feedback |
| `thumbsDownPenalty` | -0.2 | Confidence reduction for negative feedback |

## Confidence Recalculation

Confidence is automatically recalculated in two scenarios:

1. **At retrieval time** - When a memory is fetched, its confidence is refreshed to account for time decay
2. **On feedback** - When user feedback is set, confidence is immediately recalculated

## Statistics

Get insights into your memory store:

```typescript
const stats = store.getStats();

// Example output:
{
  total: 150,
  bySource: {
    user_explicit: 50,
    inferred: 70,
    auto_extracted: 30
  },
  averageConfidence: 0.74,
  minConfidence: 0.35,
  maxConfidence: 1.0,
  withFeedback: 25
}
```

## Implementation Details

### TypeScript Types

```typescript
interface Memory {
  id: string;
  content: string;
  metadata: {
    source: MemorySource;       // 'user_explicit' | 'inferred' | 'auto_extracted'
    confidence: number;         // 0.0 to 1.0
    feedback: UserFeedback;     // 'thumbs_up' | 'thumbs_down' | null
    createdAt: string;          // ISO date
    updatedAt: string;          // ISO date
    tags?: string[];
  };
}

interface MemoryQuery {
  minConfidence?: number;       // Filter by confidence threshold
  source?: MemorySource;        // Filter by source type
  tags?: string[];              // Filter by tags
  text?: string;                // Text search
  limit?: number;               // Result limit
  offset?: number;              // Result offset
}
```

## Best Practices

1. **Always specify source type** when storing memories to get accurate confidence scores
2. **Set appropriate thresholds** based on your use case:
   - Critical decisions: `minConfidence: 0.8`
   - General queries: `minConfidence: 0.5`
3. **Encourage user feedback** to improve confidence accuracy over time
4. **Review low-confidence memories** periodically for potential cleanup

## Algorithm Rationale

### Why These Values?

- **Source hierarchy**: Explicit user statements are more reliable than inferences, which are more reliable than automated extraction
- **30/90 day decay**: Balances recency importance without making old memories worthless
- **Feedback weights**: Thumbs down (-0.2) weighted more than thumbs up (+0.1) because incorrect information is more harmful than correct information is helpful
- **50% floor**: Even very old memories retain some value

### Future Enhancements

Potential improvements to consider:
- Usage-based confidence boost (frequently accessed memories)
- Cross-validation between multiple sources
- Machine learning-based confidence prediction
- Context-aware confidence adjustment
