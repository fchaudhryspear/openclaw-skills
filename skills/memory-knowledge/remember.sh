#!/bin/bash
# Knowledge Retention - /remember and /recall commands
# Usage: ./skills/memory-knowledge/remember.sh "topic" [context] [outcome]

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
MEMORY_DIR="/Users/faisalshomemacmini/.openclaw/workspace/memory/lessons"

mkdir -p "$MEMORY_DIR"

if [ $# -lt 1 ]; then
    echo "Usage: remember.sh <topic> [context] [outcome:success|failure|partial]"
    exit 1
fi

TOPIC="$1"
CONTEXT="${2:-}"
OUTCOME="${3:-manual}"
DATE=$(date +%Y-%m-%d_%H%M)
FILENAME=$(echo "$TOPIC" | tr ' ' '-' | tr -cd 'a-zA-Z0-9_-')

cat > "$MEMORY_DIR/$DATE-$FILENAME.md" << EOF
# $TOPIC

- **Date:** $(date)
- **Outcome:** $OUTCOME
- **Context:** $CONTEXT
- **Tags:** [auto-generated]

## Details

Write lesson details here...

## Resolution Steps

- Step 1
- Step 2

---

Session ID: $(uuidgen 2>/dev/null || echo "unknown")
EOF

echo "✅ Lesson saved: memory/lessons/$DATE-$FILENAME.md"
echo "📝 Content:"
cat "$MEMORY_DIR/$DATE-$FILENAME.md"
