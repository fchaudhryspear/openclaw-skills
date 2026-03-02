#!/bin/bash
# Knowledge Retention - /recall (search) command
# Usage: ./skills/memory-knowledge/recall.sh <search-query>

MEMORY_DIR="/Users/faisalshomemacmini/.openclaw/workspace/memory/lessons"

if [ $# -lt 1 ]; then
    echo "Usage: recall.sh <search-query>"
    exit 1
fi

QUERY="$*"
echo "🔍 Searching for: $QUERY"
echo "================================"

grep -rl -i "$QUERY" "$MEMORY_DIR"/*.md 2>/dev/null | while read FILE; do
    echo ""
    echo "📄 $(basename $FILE)"
    head -10 "$FILE"
    echo "..."
done

echo ""
echo "================================"
FOUND=$(grep -rl -i "$QUERY" "$MEMORY_DIR"/*.md 2>/dev/null | wc -l)
if [ "$FOUND" -eq 0 ]; then
    echo "ℹ️  No lessons found matching '$QUERY'"
else
    echo "✅ Found $FOUND matching lesson(s)"
fi
