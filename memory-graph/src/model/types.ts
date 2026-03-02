/**
 * Typed Memory Graph - Core Type Definitions
 */

// Node types with specific schemas
export type NodeType = 
  | 'person' 
  | 'project' 
  | 'task' 
  | 'meeting' 
  | 'document' 
  | 'idea' 
  | 'note'
  | 'resource'
  | 'concept';

export interface NodeSchema {
  required: string[];
  properties: Record<string, PropertyType>;
}

export enum PropertyType {
  STRING = 'string',
  NUMBER = 'number',
  BOOLEAN = 'boolean',
  DATE = 'date',
  ARRAY = 'array',
  OBJECT = 'object',
}

// Edge types defining relationships
export type EdgeType = 
  | 'related_to'
  | 'part_of'
  | 'depends_on'
  | 'created_by'
  | 'references'
  | 'tags'
  | 'similar_to'
  | 'contradicts'
  | 'updates';

export interface PropertyDefinition {
  type: PropertyType;
  required?: boolean;
  defaultValue?: unknown;
  validator?: (value: unknown) => boolean;
}

// Core node structure
export interface Node {
  id: string;
  type: NodeType;
  properties: Record<string, unknown>;
  tags: string[];
  createdAt: Date;
  updatedAt: Date;
  createdBy: string;
  accessLevel: AccessLevel;
  version: number;
}

// Edge/relationship structure
export interface Edge {
  id: string;
  from: string; // node id
  to: string;   // node id
  type: EdgeType;
  properties: Record<string, unknown>;
  createdAt: Date;
  createdBy: string;
}

// Access control levels
export enum AccessLevel {
  PUBLIC = 'public',
  PRIVATE = 'private',
  TEAM = 'team',
  RESTRICTED = 'restricted',
}

// Role-based permissions
export enum Role {
  ADMIN = 'admin',
  EDITOR = 'editor',
  VIEWER = 'viewer',
  GUEST = 'guest',
}

export interface Permission {
  role: Role;
  canRead: boolean;
  canWrite: boolean;
  canDelete: boolean;
  canShare: boolean;
  canManageAccess: boolean;
}

// Audit log entry
export interface AuditEntry {
  id: string;
  timestamp: Date;
  action: AuditAction;
  userId: string;
  entityType: 'node' | 'edge' | 'schema' | 'permission';
  entityId: string;
  changes?: {
    before?: unknown;
    after?: unknown;
  };
  ipAddress?: string;
  metadata?: Record<string, unknown>;
}

export enum AuditAction {
  CREATE = 'create',
  READ = 'read',
  UPDATE = 'update',
  DELETE = 'delete',
  SHARE = 'share',
  ACCESS_GRANTED = 'access_granted',
  ACCESS_REVOKED = 'access_revoked',
  SCHEMA_CHANGE = 'schema_change',
  AUTH_FAILED = 'auth_failed',
}

// Query structures
export interface QueryParams {
  match?: QueryMatch;
  where?: Record<string, unknown>;
  orderBy?: { field: string; direction: 'asc' | 'desc' };
  limit?: number;
  offset?: number;
  depth?: number; // for traversals
}

export interface QueryMatch {
  labels?: NodeType[];
  ids?: string[];
  tags?: string[];
}

export interface QueryResult<T = Node> {
  nodes: T[];
  edges: Edge[];
  metadata: {
    totalNodes: number;
    totalEdges: number;
    executionTime: number;
  };
}

// Encryption configuration
export interface EncryptionConfig {
  algorithm: 'aes-256-gcm';
  keyRotationDays: number;
  ivLength: number;
  tagLength: number;
}

// Storage configuration
export interface StorageConfig {
  path: string;
  encryptionKey: string;
  compression: boolean;
  backupInterval: number; // in hours
}

// Wiki-link extraction result
export interface WikiLink {
  target: string; // The [[linked]] page name
  context: string; // Surrounding text
  position: { start: number; end: number };
  type: 'link' | 'tag' | 'query';
}

// Tag hierarchy definition
export interface TagDefinition {
  name: string;
  parent?: string;
  aliases: string[];
  description?: string;
}
