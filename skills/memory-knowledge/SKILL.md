# memory-knowledge Skill - Knowledge Retention System

A secure knowledge retention system for capturing lessons learned from failed/succeeded attempts. Provides `/remember` and `/recall` commands for storing and retrieving knowledge.

## Usage

### Store Knowledge
```bash
/remember <topic> [context] [outcome: success|failure|partial] [link-to-project]
```

Example:
```bash
/remember "JSON editing restrictions" "OpenClaw has limitations on inline JSON edits" outcome:failure link:checkpoint_system
```

### Search/Retrieve Knowledge
```bash
/realmind <search-query>
```
Also aliased as `/recall <search-query>`

Examples:
```bash
/realmind "telegram group privacy"
/realmind "snowflake connection errors"
```

### Manual Lesson Capture
```bash
/openclaw knowledge save [--outcome success|failure|partial] [--project <name>] [--tags <tag1,tag2>]
```
This captures the current session context into a lesson file.

## File Structure

- `memory/lessons/` - Individual lesson files (one per learning event)
- `memory/knowledge-index.jsonl` - Searchable index of all knowledge
- `memory/access-logs.jsonl` - Audit trail of all read/write operations
- `memory/knowledge-vault/` - Encrypted storage via ClawVault (sensitive lessons)

## Lesson File Format

Each lesson is stored in `memory/lessons/YYYY-MM-DD-<sanitized-topic>.md`:

```markdown
# <Topic Title>

- **Date:** YYYY-MM-DD HH:MM TZ
- **Outcome:** success|failure|partial
- **Project:** <linked project or null>
- **Tags:** [tag1, tag2, tag3]
- **Context:** Brief description of the situation
- **Lesson Learned:** The key insight or mistake discovered
- **Resolution Steps:** Actionable steps taken to resolve
- **Related:** Links to related lessons or projects

**Session ID:** <session id if applicable>
**Actor:** <who created this>
```

## Security

- All lessons are logged in access-logs.jsonl with timestamp and operation type
- Sensitive lessons can be marked with `[SENSITIVE]` tag and stored encrypted in knowledge-vault/
- Access logs include: timestamp, operation, user, topic accessed, outcome
- Encryption uses ClawVault infrastructure with AES-256-GCM

## Integration Points

### Automatic Capture Hooks
Lessons should be automatically captured when:
1. A checkpoint fails after multiple retries
2. A significant error occurs during task execution
3. A successful solution is found for a novel problem
4. User explicitly triggers via `/remember` command

### Project Linking
Lessons can be linked to active projects by including project path or name. The system maintains bidirectional links for easy navigation.

## Commands Reference

| Command | Description |
|---------|-------------|
| `/remember <topic>` | Store new knowledge/lesson |
| `/recall <query>` | Search and retrieve relevant lessons |
| `/knowledge list` | List all stored lessons |
| `/knowledge stats` | Show knowledge base statistics |
| `/knowledge export` | Export all lessons (optionally encrypted) |
| `/knowledge import <file>` | Import lessons from file |
