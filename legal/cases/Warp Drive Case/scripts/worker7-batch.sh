#!/usr/bin/env bash
# Worker 7 - WDE Discovery Batch Processing (Batches 533-614)
# Fast text extraction via pdftotext, flags forge/jacqueline hits
# Saves per-batch summaries to notes/batch-summaries/

set -uo pipefail

CASE_DIR="/Users/faisalshomemacmini/.openclaw/workspace/legal/cases/Warp Drive Case"
DISCOVERY_DIR="$CASE_DIR/Discovery"
SUMMARIES_DIR="$CASE_DIR/notes/batch-summaries"
BATCH_SIZE=100
START_BATCH=533
END_BATCH=614
SEARCH_TERMS="forgeadvisors|jacqueline@forge|forge advisors|jacqueline.*forge|forge.*jacqueline"

mkdir -p "$SUMMARIES_DIR"

# Generate sorted file list
FILE_LIST="/tmp/wde-worker7-files.txt"
ls "$DISCOVERY_DIR"/*.pdf 2>/dev/null | sort > "$FILE_LIST"
TOTAL_FILES=$(wc -l < "$FILE_LIST" | tr -d ' ')

echo "Worker 7 - WDE Discovery Processing"
echo "Batches: $START_BATCH - $END_BATCH"
echo "Total Discovery files: $TOTAL_FILES"
echo "=========================================="

ALL_HITS_FILE="$SUMMARIES_DIR/worker7-all-hits.txt"
> "$ALL_HITS_FILE"

TOTAL_PROCESSED=0
TOTAL_HITS=0
TOTAL_ERRORS=0

for ((BATCH=START_BATCH; BATCH<=END_BATCH; BATCH++)); do
    START_IDX=$(( (BATCH-1) * BATCH_SIZE + 1 ))
    END_IDX=$(( BATCH * BATCH_SIZE ))

    # Don't exceed total files
    if [ "$START_IDX" -gt "$TOTAL_FILES" ]; then
        echo "Batch $BATCH: beyond file count, stopping."
        break
    fi
    if [ "$END_IDX" -gt "$TOTAL_FILES" ]; then
        END_IDX=$TOTAL_FILES
    fi

    BATCH_COUNT=$(( END_IDX - START_IDX + 1 ))
    BATCH_HITS=0
    BATCH_ERRORS=0
    BATCH_START_TIME=$(date +%s)
    HIT_FILES=""

    # Get files for this batch
    BATCH_FILES=$(sed -n "${START_IDX},${END_IDX}p" "$FILE_LIST")

    while IFS= read -r PDF_PATH; do
        [ -z "$PDF_PATH" ] && continue
        BASENAME=$(basename "$PDF_PATH" .pdf)

        # Fast text extraction via pdftotext
        TEXT=$(pdftotext "$PDF_PATH" - 2>/dev/null) || {
            # Fallback: try pymupdf
            TEXT=$(python3 -c "
import fitz, sys
try:
    doc = fitz.open('$PDF_PATH')
    for p in doc: print(p.get_text())
    doc.close()
except: pass
" 2>/dev/null) || {
                BATCH_ERRORS=$((BATCH_ERRORS + 1))
                continue
            }
        }

        # Search for hits (case-insensitive)
        if echo "$TEXT" | grep -qiE "$SEARCH_TERMS" 2>/dev/null; then
            BATCH_HITS=$((BATCH_HITS + 1))
            HIT_FILES="$HIT_FILES\n  - $BASENAME"
            # Log the matching lines
            MATCH_LINES=$(echo "$TEXT" | grep -iE "$SEARCH_TERMS" 2>/dev/null | head -5)
            echo "Batch $BATCH | $BASENAME | $(echo "$MATCH_LINES" | head -1)" >> "$ALL_HITS_FILE"
        fi

    done <<< "$BATCH_FILES"

    BATCH_END_TIME=$(date +%s)
    DURATION=$(( BATCH_END_TIME - BATCH_START_TIME ))
    TOTAL_PROCESSED=$((TOTAL_PROCESSED + BATCH_COUNT))
    TOTAL_HITS=$((TOTAL_HITS + BATCH_HITS))
    TOTAL_ERRORS=$((TOTAL_ERRORS + BATCH_ERRORS))

    # Write batch summary
    SUMMARY_FILE="$SUMMARIES_DIR/batch-${BATCH}-summary.md"
    cat > "$SUMMARY_FILE" << BATCHEOF
# Batch $BATCH Summary (Worker 7)
**Date:** $(date '+%Y-%m-%d %H:%M:%S')
**Files:** $START_IDX - $END_IDX ($BATCH_COUNT files)
**Duration:** ${DURATION}s
**Errors:** $BATCH_ERRORS

## Forge/Jacqueline Hits: $BATCH_HITS
$(if [ "$BATCH_HITS" -gt 0 ]; then echo -e "$HIT_FILES"; else echo "No hits in this batch."; fi)
BATCHEOF

    # Write hits file (matching existing format)
    if [ "$BATCH_HITS" -gt 0 ]; then
        echo "WORKER 7 - SMOKING GUN Batch $BATCH: $BATCH_HITS files" > "$SUMMARIES_DIR/batch-${BATCH}-hits.txt"
    fi

    # Progress output
    PCT=$(( (TOTAL_PROCESSED * 100) / ((END_BATCH - START_BATCH + 1) * BATCH_SIZE) ))
    echo "Batch $BATCH: ${BATCH_COUNT} files, ${BATCH_HITS} hits, ${DURATION}s [${PCT}%]"

done

echo ""
echo "=========================================="
echo "WORKER 7 COMPLETE"
echo "Batches: $START_BATCH - $END_BATCH"
echo "Files processed: $TOTAL_PROCESSED"
echo "Total hits: $TOTAL_HITS"
echo "Total errors: $TOTAL_ERRORS"
echo "All hits saved to: $ALL_HITS_FILE"
echo "=========================================="
