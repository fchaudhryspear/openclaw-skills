# Lesson: OpenClaw `openclaw.json` Editing Restrictions

**Date:** March 1st, 2026

**Lesson Learned:** OpenClaw's security sandbox prevents direct modification (writing or editing) of files outside the designated workspace root (`/Users/faisalshomemacmini/.openclaw/workspace`). This includes critical configuration files like `~/.openclaw/openclaw.json`.

**Context:** Attempts to add a new model (`Qwen3.5-122B-A10B`) to the `openclaw.json` file on behalf of the user resulted in "Path escapes workspace root" errors from the `write` tool and "File not found" errors from the `edit` tool (even with absolute paths), highlighting a core security feature.

**Implication:** For any modifications to `openclaw.json` or other protected system files, direct user intervention is required. The assistant can provide instructions or the full content for the user to copy-paste, but cannot execute the write/edit operation itself.

**Related Concepts:**
*   [[OpenClaw Security Sandbox]]
*   [[Workspace Root]]
*   [[openclaw.json Configuration]]
