# Memory Graph Design Document

**Version:** 1.0
**Date:** 2024-07-30
**Author:** Optimus (OpenClaw Subagent)
**Purpose:** To design a secure Memory Graph that adapts graph structure concepts from ClawVault, ensuring strict access controls, audit trails, and adherence to security policy for data linkage and integrity.

---

## 1. Core Concepts

The Memory Graph will represent knowledge as a network of interconnected entities (Nodes) and relationships (Edges). This structure will allow for more sophisticated querying, reasoning, and context understanding than a flat memory store.

### 1.1 Nodes (Entities)

Nodes represent discrete pieces of information or entities within the memory graph. Each node will have a unique identifier and a set of properties.

**Node Properties:**

*   **`id` (UUID):** Unique identifier for the node.
*   **`type` (Enum):** Classification of the node (e.g., `Person`, `Organization`, `Project`, `Concept`, `Event`, `ProceduralStep`, `Fact`).
*   **`content` (String):** The primary data or description of the node. This can be a summary, a key fact, or a snippet of information.
*   **`confidence` (Float):** A score (0.0-1.0) indicating the reliability of the information, adapted from ClawVault's Memory Confidence Scoring.
*   **`semantic_type` (Enum):** Adapts ClawVault's Semantic Memory Layers (`Episodic`, `Procedural`, `Declarative`). This helps in decay management and querying.
*   **`created_at` (Timestamp):** When the node was first added.
*   **`updated_at` (Timestamp):** Last time the node's content or properties were updated.
*   **`accessed_at` (Timestamp):** Last time the node was accessed/retrieved.
*   **`source` (String):** Origin of the information (e.g., `user_explicit`, `inferred`, `auto_extracted`, `web_search`).
*   **`tags` (Array of Strings):** Keywords or labels for filtering and categorization.
*   **`access_control` (JSON/Array of Objects):** Defines who can read/write/delete this node. This is a critical security feature.
    *   Example: `[{ "user_id": "fas", "permission": ["read", "write"] }, { "group_id": "team-x", "permission": ["read"] }]`
*   **`sensitive_data_ref` (Boolean):** Flag indicating if the `content` contains a reference to sensitive data (e.g., `$OPENAI_API_KEY`), rather than the data itself. Adapts ClawVault's Sensitive Data Detection.
*   **`sensitive_data_context` (Array of Strings):** List of contexts or templates related to sensitive data if `sensitive_data_ref` is true (e.g., `["OpenAI API Key"]`).
*   **`audit_log` (Array of Objects):** Immutable record of significant changes to the node (creation, updates, access attempts, permission changes).
    *   Example: `[{ "timestamp": "...", "action": "create", "actor": "system/optimus", "details": {...} }]`

### 1.2 Edges (Relationships)

Edges define the connections and relationships between nodes. Each edge will have a source node, a target node, and a type describing the relationship.

**Edge Properties:**

*   **`id` (UUID):** Unique identifier for the edge.
*   **`source_node_id` (UUID):** ID of the node initiating the relationship.
*   **`target_node_id` (UUID):** ID of the node receiving the relationship.
*   **`type` (Enum):** Describes the nature of the relationship (e.g., `HAS_PROPERTY`, `IS_RELATED_TO`, `PART_OF`, `PERFORMS`, `TRIGGERED_BY`, `RESPONSIBLE_FOR`).
*   **`weight` (Float):** Numerical strength of the relationship (e.g., relevance, importance). Can be influenced by time decay.
*   **`created_at` (Timestamp):** When the edge was first created.
*   **`updated_at` (Timestamp):** Last time the edge's properties were updated.
*   **`confidence` (Float):** Confidence in the accuracy of this specific relationship.
*   **`access_control` (JSON/Array of Objects):** Similar to nodes, defines access for this specific relationship.
*   **`audit_log` (Array of Objects):** Immutable record of changes to the edge.

---

## 2. Security and Access Controls

Security is paramount for the Memory Graph.

### 2.1 Principle of Least Privilege

Access to nodes and edges will be granted on a need-to-know basis. Default access will be highly restrictive.

### 2.2 Granular Access Control

Each node and edge will carry its own `access_control` property. This allows for fine-grained permissions down to the individual data point.

*   **Read:** Ability to view the node/edge content and properties.
*   **Write:** Ability to modify the node/edge content or properties.
*   **Delete:** Ability to remove the node/edge.
*   **Admin:** Ability to modify `access_control` properties.

### 2.3 Authentication and Authorization

*   **Authentication:** All interactions with the Memory Graph API will require robust authentication (e.g., API keys, OAuth tokens tied to specific users/services).
*   **Authorization:** The system will check the `access_control` lists on each node/edge for every read/write/delete operation.

### 2.4 Sensitive Data Handling

*   **Reference-Based Storage:** As per ClawVault, sensitive data will never be stored directly in the graph. Instead, references (e.g., environment variables, 1Password entries) will be stored in the `content` field, flagged by `sensitive_data_ref`.
*   **Redaction on Access:** If an unauthorized attempt is made to access a node flagged with `sensitive_data_ref`, the content will be automatically redacted or an access denied error will be returned.
*   **Encrypted Storage:** The underlying graph database will ensure data at rest is encrypted.

### 2.5 Audit Trails

All significant actions (creation, modification, deletion, access attempts - especially failed ones) on nodes and edges will be logged in their respective `audit_log` properties. This provides an immutable record for security monitoring and compliance.

*   **Timestamp:** When the action occurred.
*   **Action:** Type of action (e.g., `create`, `update`, `delete`, `read_attempt`, `permission_change`).
*   **Actor:** User or system agent performing the action.
*   **Details:** Specifics of the change (e.g., old/new values for updates, reason for deletion).

---

## 3. Data Integrity and Consistency

### 3.1 Transactions

All modifications to the graph (creating nodes/edges, updating properties) will be performed within transactions to ensure atomicity.

### 3.2 Schema Validation

Nodes and edges will adhere to predefined schemas to ensure consistency and prevent malformed data.

### 3.3 Conflict Resolution

Strategies for handling concurrent modifications will be implemented (e.g., last-write-wins, optimistic locking).

---

## 4. Integration with ClawVault Concepts

### 4.1 Incremental Graph Updates

Similar to ClawVault's Incremental Indexing, the Memory Graph will support efficient updates. Changes to source data will trigger targeted updates to relevant nodes and edges, minimizing re-processing.

### 4.2 Semantic Layers and Time Decay

*   Node `semantic_type` will directly leverage ClawVault's Episodic, Procedural, and Declarative classifications.
*   Edge `weight` and node `confidence` will be influenced by ClawVault's Time-Decay Weighting, allowing less relevant connections or facts to naturally fade.

### 4.3 Memory Consolidation and Pruning

The Memory Graph will integrate with ClawVault's lifecycle management:

*   **Consolidation:** Similar or redundant nodes/edges can be identified and merged or linked, potentially increasing edge weights.
*   **Pruning:** Low-confidence nodes/edges, or those rarely accessed, can be flagged for review or soft deletion, preventing graph bloat.

### 4.4 Feedback Loop

User feedback (👍/👎) can directly influence node and edge `confidence` scores, improving the graph's accuracy and relevance over time.

---

## 5. Proposed Technologies (Conceptual)

*   **Graph Database:** Neo4j, ArangoDB, Amazon Neptune, or a custom in-memory graph solution for smaller scale.
*   **API Framework:** Node.js (TypeScript) with GraphQL or REST.
*   **Authentication:** JWT, OAuth2.
*   **Data Storage:** Encrypted object storage (e.g., S3) for backups, underlying database for active data.
*   **Auditing:** Dedicated logging service (e.g., Elastic Stack, Splunk) for collecting and analyzing audit logs.

---

## 6. Future Considerations

*   **Query Language:** Development of a graph-specific query language or integration with existing ones (Cypher for Neo4j, AQL for ArangoDB).
*   **Visualization:** Tools for visualizing the graph structure and relationships.
*   **Reasoning Engine:** Capabilities to infer new facts or relationships based on existing graph data.
*   **Conflict-free Replicated Data Types (CRDTs):** For highly distributed, eventually consistent graph synchronization.
