#!/bin/bash
# Quick Redaction for Today's Security Incident (2026-03-02)
# Redacts AWS and Anthropic keys mentioned in today's debugging session

set -e

echo "===================================================="
echo "🔒 Quick Secret Redaction — Today's Session"
echo "===================================================="
echo ""

MEMORY_DIR="$HOME/memory"
REDIRECTED=0

# Known leaked keys from today's session
declare -a KEYS=(
    # AWS Key IDs (AKIA pattern)
    "AKIA-REDACTED"
    "AKIA-REDACTED"
    # Anthropic key (partial match - last 8 chars we saw)
    "...Mo0-AklNfDQcRy91rkMupGB11g..."
    # Partial secret key reference
    "cnTKRZ26ANABaMuGB+qbkkg0VMi0KROJSRg5Sy4R"
)

for key in "${KEYS[@]}"; do
    if [[ -z "$key" || "$key" == *"REDACTED"* ]]; then
        continue
    fi
    
    echo "🔍 Checking for: ${key:0:20}..."
    
    FILES=$(grep -rlF "$key" "$MEMORY_DIR" --include="*.md" 2>/dev/null | grep -v ".git" || true)
    
    if [[ -n "$FILES" ]]; then
        for file in $FILES; do
            COUNT=$(grep -cF "$key" "$file")
            FILE_REL="${file#$HOME/}"
            echo "   ⚠️  Found $COUNT instance(s) in: $FILE_REL"
            
            # Create backup
            cp "$file" "${file}.bak.security.$(date +%Y%m%d%H%M%S)"
            
            # Replace with [REDACTED]
            sed -i.bak2 "s/$key/[REDACTED]/g" "$file"
            
            ((REDIRECTED++)) || true
            echo "      ✅ Redacted + backed up original"
        done
    else
        echo "   ✅ Not found"
    fi
done

echo ""
echo "===================================================="
echo "✅ Redaction Complete"
echo "===================================================="
echo ""
echo "Files modified: ~$REDIRECTED instances"
echo ""
echo "Review backups:"
ls -la "$MEMORY_DIR"/*.bak.security.* 2>/dev/null | tail -5 || echo "(no backups found)"
echo ""
echo "Next run: ./redact-secrets.sh for comprehensive scan"
echo ""
