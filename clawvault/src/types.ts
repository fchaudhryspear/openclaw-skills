/**
 * ClawVault - Memory System Types
 * Phase 1 + Phase 2 Type Definitions
 */

export type MemoryType = 'episodic' | 'semantic' | 'procedural' | 'working';
export type MemoryScope = 'session' | 'user' | 'global';
export type SensitivityLevel = 'public' | 'internal' | 'confidential' | 'restricted';

// New Memory interface for vector store and safety modules
export interface Memory {
  id: string;
  content: string;
  type?: MemoryType;
  createdAtMs?: number;
  metadata?: Record<string, any>;
}

export interface MemoryEntry {
  id: string;
  content: string;
  type: MemoryType;
  scope: MemoryScope;
  timestamp: number;
  confidence: number;
  embedding?: number[];
  metadata: MemoryMetadata;
  semanticLayer: SemanticLayer;
  sensitivity: SensitivityLevel;
  version: number;
}

export interface MemoryMetadata {
  source?: string;
  tags: string[];
  relationships: string[];
  accessCount: number;
  lastAccessed: number;
  createdBy: string;
  modifiedAt: number;
}

export interface SemanticLayer {
  category: string;
  entities: string[];
  concepts: string[];
  sentiment: number;
  importance: number;
}

export interface ConfidenceScore {
  overall: number;
  factors: {
    sourceReliability: number;
    consistency: number;
    verificationStatus: number;
    age: number;
    accessPatterns: number;
  };
}

export interface SensitiveDataDetection {
  hasSensitiveData: boolean;
  detectedTypes: SensitiveDataType[];
  redactedContent?: string;
  confidence: number;
}

export interface SensitiveDataType {
  type: 'pii' | 'credential' | 'financial' | 'health' | 'location';
  pattern: string;
  position: [number, number];
  severity: 'low' | 'medium' | 'high';
}

// Phase 2: Search Types
export interface SearchQuery {
  query: string;
  contextMessages?: ContextMessage[];
  filters?: SearchFilters;
  options?: SearchOptions;
}

export interface ContextMessage {
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: number;
}

export interface SearchFilters {
  types?: MemoryType[];
  scopes?: MemoryScope[];
  minConfidence?: number;
  maxAge?: number;
  tags?: string[];
  excludeSensitive?: boolean;
}

export interface SearchOptions {
  limit?: number;
  offset?: number;
  includeScores?: boolean;
  rerank?: boolean;
  weights?: SearchWeights;
}

export interface SearchWeights {
  vector: number;
  keyword: number;
  temporal: number;
}

export interface SearchResult {
  entry: MemoryEntry;
  scores: {
    vector: number;
    keyword: number;
    temporal: number;
    context: number;
    combined: number;
  };
  highlights?: string[];
}

export interface SearchCache {
  key: string;
  results: SearchResult[];
  timestamp: number;
  hitCount: number;
}

export interface HybridSearchIndex {
  tfidf: Map<string, Map<string, number>>;
  documentFrequency: Map<string, number>;
  documentCount: number;
  idf: Map<string, number>;
}

export interface SearchStats {
  totalSearches: number;
  cacheHits: number;
  averageLatency: number;
  topQueries: Map<string, number>;
}
