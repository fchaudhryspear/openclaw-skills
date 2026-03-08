#!/bin/bash
# 🔒 Secret Redaction Script for Memory Files
# Scans and redacts API keys, passwords, and credentials from memory/chat archives

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MEMORY_DIR="$HOME/memory"
CHAT_ARCHIVES="$MEMORY_DIR/chat_archives"
LOG_FILE="$MEMORY_DIR/secrets-redaction.log"

echo "=================================================="
echo "🔐 Secret Redaction Script"
echo "=================================================="
echo ""
echo "Scanning: $MEMORY_DIR"
echo "Log: $LOG_FILE"
echo ""

# Initialize log
echo "--- Redaction Session: $(date) ---" >> "$LOG_FILE"

# Define secret patterns (regex)
PATTERNS=(
    # AWS Access Keys
    'AKIA[A-Z0-9]{16}'
    # Anthropic API Keys
    'sk-ant-[A-Za-z0-9_-]+'
    # OpenAI API Keys  
    'sk-(proj|api)-[A-Za-z0-9_-]+'
    # Alibaba/Qwen API Keys
    'sk-[A-Za-z0-9]{32,}'
    # Generic API key assignments
    '(apiKey|api_key|API_KEY|password|PASSWORD|secret|SECRET)[:\s]*["\x27]?[A-Za-z0-9+/=_-]+["\x27]?'
)

REDACTED_COUNT=0

for pattern in "${PATTERNS[@]}"; do
    echo "🔍 Checking pattern: ${pattern:0:40}..."
    
    # Find files matching pattern
    FILES=$(grep -rlE "$pattern" "$MEMORY_DIR" --include="*.md" 2>/dev/null | grep -v ".git" | head -20 || true)
    
    if [[ -n "$FILES" ]]; then
        for file in $FILES; do
            MATCHES=$(grep -cE "$pattern" "$file" 2>/dev/null || echo "0")
            echo "   ⚠️  Found $MATCHES match(es) in: ${file#$HOME/}"
            
            # Backup original
            cp "$file" "${file}.bak.$(date +%Y%m%d%H%M%S)"
            
            # Redact AWS keys
            if [[ "$pattern" == "AKIA[A-Z0-9]{16}" ]]; then
                sed -i.bak2 -E "s/AKIA[A-Z0-9]{16}/AKIA[REDACTED]/g" "$file"
                ((REDACTED_COUNT++)) || true
            fi
            
            # Redact Anthropic keys
            if [[ "$pattern" == "sk-ant-"* ]]; then
                sed -i.bak3 -E "s/sk-ant-[A-Za-z0-9_-]+/sk-ant-[REDACTED]/g" "$file"
                ((REDACTED_COUNT++)) || true
            fi
            
            # Redact OpenAI keys
            if [[ "$pattern" == "sk-(proj|"* ]]; then
                sed -i.bak4 -E "s/sk-(proj|api)-[A-Za-z0-9_-]+/sk-[REDACTED]/g" "$file"
                ((REDACTED_COUNT++)) || true
            fi
            
            # Redact generic sk-* keys (Alibaba)
            if [[ "$pattern" == "sk-"* ]]; then
                sed -i.bak5 -E "s/sk-[A-Za-z0-9]{32,}/sk-[REDACTED]/g" "$file"
                ((REDACTED_COUNT++)) || true
            fi
            
            echo "      ✅ Backed up original to .bak.* files"
        done
    else
        echo "   ✅ No matches found"
    fi
done

echo ""
echo "=================================================="
echo "✅ Redaction Complete"
echo "=================================================="
echo ""
echo "Summary:"
echo "  • Total files scanned: $(find "$MEMORY_DIR" -name "*.md" | wc -l | tr -d ' ')"
echo "  • Secrets redacted: ~$REDACTED_COUNT instances"
echo "  • Backups created: *.bak.* files (review before deleting)"
echo ""
echo "Next Steps:"
echo "  1. Review backup files: ls -la *.bak.* | head -10"
echo "  2. If confident, clean up backups: rm *.bak.*"
echo "  3. Enable automatic scanning on future sessions"
echo ""
echo "Log saved to: $LOG_FILE"
echo ""

# Clean up intermediate backup files (keep only first backup per file)
echo "Cleaning up intermediate backup files..."
find "$MEMORY_DIR" -name "*.bak2*" -o -name "*.bak3*" -o -name "*.bak4*" -o -name "*.bak5*" 2>/dev/null | while read f; do
    rm "$f" 2>/dev/null || true
done

echo "Done!"
