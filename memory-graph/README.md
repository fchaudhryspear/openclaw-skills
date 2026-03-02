# Typed Memory Graph for AI Agents

A secure, typed knowledge graph system designed for AI agents to store, query, and reason over structured memories with strict access controls and audit trails.

## Features

- **Typed Schema**: Strongly-typed nodes and edges with custom type definitions
- **Wiki-Links Support**: Automatic extraction of `[[links]]` and relationships
- **Tag System**: Hierarchical tagging with inheritance
- **Access Controls**: Role-based access control (RBAC) with granular permissions
- **Audit Trail**: Complete logging of all read/write operations
- **Encrypted Storage**: AES-256 encryption at rest
- **Query API**: GraphQL-like query language for complex traversals

## Architecture

```
memory-graph/
├── src/
│   ├── model/         # Data models and schema definitions
│   ├── storage/       # Encrypted storage backend
│   ├── access/        # RBAC and permission system
│   ├── audit/         # Audit trail logging
│   ├── api/           # Query API
│   └── parser/        # Wiki-links and tag extraction
├── tests/
│   ├── unit/          # Unit tests
│   ├── security/      # Security tests
│   └── integration/   # Integration tests
├── docs/              # Documentation
└── scripts/           # Utility scripts
```

## Quick Start

```typescript
import { MemoryGraph } from '@memory-graph/core';

const graph = await MemoryGraph.create({
  path: './memories',
  encryptionKey: 'your-secure-key',
});

// Create a node
await graph.addNode({
  id: 'project-x',
  type: 'project',
  properties: { name: 'Project X', status: 'active' },
  tags: ['work', 'priority'],
});

// Query
const results = await graph.query(`
  MATCH (n:project {status: 'active'})
  RETURN n
`);
```

## Security

- All data encrypted with AES-256-GCM
- HMAC signatures for integrity verification
- Role-based access control with least-privilege defaults
- Complete audit trail of all operations
- Key rotation support
