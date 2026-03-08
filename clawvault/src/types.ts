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
  tags?: string[];
  confidenceMin?: number;
  dateRange?: { from: number; to: number };
}

export interface SearchOptions {
  limit?: number;
  offset?: number;
  sortBy?: 'relevance' | 'date' | 'confidence';
  sortOrder?: 'asc' | 'desc';
}

// Legacy interfaces (for backward compatibility)
export interface QueryOptions {
  limit?: number;
  offset?: number;
  sort?: 'asc' | 'desc';
}

export interface SearchOptionsLegacy {
  limit?: number;
  offset?: number;
  sort?: 'asc' | 'desc';
}
