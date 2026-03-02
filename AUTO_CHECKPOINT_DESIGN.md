# Auto-Checkpoint & Wake System Design

## 1. Executive Summary

This document outlines the design for a reliable Auto-Checkpoint & Wake system for OpenClaw agents. The system will leverage ClawVault's concepts for efficient context saving, incorporating robust encryption and integrity checks to meet security policy requirements. The goal is to enable agents to pause their work and seamlessly resume from the last valid checkpoint, ensuring continuity and resilience against interruptions.

## 2. Core Concepts

### 2.1 Agent Context Definition

An agent's context will be defined as the essential state required for it to resume its operation accurately. This includes:

*   **Agent's internal state:** Model memory, current task plan, active sub-goals.
*   **Workspace modifications:** Changes to files, new files created, deleted files (or references to them).
*   **Tool session states:** Open `exec` sessions (if resumable), `process` sessions, `browser` sessions (if applicable and resumable).
*   **User interactions:** Recent chat history, pending user prompts.

### 2.2 Checkpoint Triggers

Checkpoints will be triggered by a combination of factors:

*   **Time-based:** Every `N` minutes (configurable, e.g., 5-10 minutes).
*   **Event-based:** Before executing a potentially long-running or critical tool call (e.g., `exec` with a long `timeoutMs`, `subagents` spawn).
*   **Token-limit-based:** When the agent's internal context approaches a predefined token limit, to prevent context overflow and enable a clean restart.
*   **Manual:** An explicit `/checkpoint` command from the user or another agent.

### 2.3 Checkpoint Storage

Checkpoints will be stored in a dedicated, versioned directory within the agent's workspace, e.g., `.checkpoints/{agent_id}/{timestamp}/`. Each checkpoint will consist of:

*   **Context metadata file (`context.json`):** Contains agent's internal state, task plan, tool session IDs, and other critical metadata.
*   **Workspace diff/snapshot:** A mechanism to capture changes to the workspace. This could be:
    *   **Full snapshot:** Simple but inefficient for large workspaces. Not preferred.
    *   **Incremental diff:** Store only changes since the last checkpoint (e.g., using `git diff` or a custom file hashing/comparison mechanism similar to ClawVault's incremental indexing).

### 2.4 Encryption and Integrity Checks

#### Encryption

*   **Mechanism:** AES-256 GCM (Authenticated Encryption with Associated Data).
*   **Key Management:**
    *   A unique encryption key will be generated per agent session, derived from a master key (stored securely, e.g., in `1Password` or as an environment variable) and a per-session nonce.
    *   The key will be ephemeral and only exist in memory during active operation.
    *   Encryption will apply to all `context.json` files and sensitive parts of the workspace diff.

#### Integrity Checks

*   **Mechanism:** SHA-256 HMAC (Hash-based Message Authentication Code).
*   **Purpose:** To detect any unauthorized alteration or corruption of checkpoint data.
*   **Implementation:** An HMAC will be generated for the encrypted checkpoint data using the same session-derived key and stored alongside the encrypted data.

### 2.5 Wake Process

1.  **Detection:** On agent startup or explicit `/wake` command, the system will check for the latest valid checkpoint.
2.  **Verification:** The system will verify the integrity of the checkpoint using the stored HMAC. If integrity fails, the checkpoint is rejected.
3.  **Decryption:** The `context.json` and workspace diff are decrypted.
4.  **Restoration:**
    *   The agent's internal state is reloaded from `context.json`.
    *   The workspace is restored using the diff/snapshot (applying changes in reverse for diffs or replacing files for snapshots).
    *   Tool sessions are re-established if their IDs were saved and the tools support resuming.
5.  **Continuation:** The agent resumes its operation from the point of the checkpoint, continuing its task plan.

## 3. Technical Implementation Details

### 3.1 Checkpoint Module

A central module (`checkpoint_manager.py`) will handle:

*   Triggering checkpoints.
*   Serializing/deserializing agent context.
*   Managing workspace diffs/snapshots.
*   Invoking encryption/decryption and integrity checks.
*   Storing/retrieving checkpoints.

### 3.2 Encryption Module

A separate `security_utils.py` module will provide functions for:

*   Key generation (from master key + nonce).
*   AES-256 GCM encryption/decryption.
*   SHA-256 HMAC generation/verification.

### 3.3 Workspace Snapshot/Diff

Leveraging concepts from ClawVault's incremental indexing, a file hashing mechanism will be used to detect changes. Instead of re-indexing, the system will:

1.  Calculate hashes of all tracked files at checkpoint time.
2.  Compare with previous checkpoint's hashes to identify added, modified, or deleted files.
3.  Store only the changed files (or their inverse operations) in the checkpoint.

## 4. Testing Strategy

*   **Unit Tests:** For each component (serialization, encryption, integrity, file diffing).
*   **Integration Tests:** End-to-end tests for checkpointing and waking up, including scenarios with file changes, tool calls, and simulated interruptions.
*   **Security Tests:** Attempting to tamper with checkpoints to ensure integrity checks catch the modifications.
*   **Performance Tests:** Measure the time and resources (CPU, memory, disk I/O) required for checkpointing and waking up, especially with large workspaces.

## 5. Future Considerations

*   **Tool-specific checkpointing:** Deeper integration with specific tools (e.g., `exec` sessions with TTYs) to capture their exact state for more seamless resumption.
*   **Rollback capability:** Ability to revert to an earlier checkpoint.
*   **Distributed checkpoints:** For agents running across multiple nodes.

