#!/bin/bash
# Parallel WDE Discovery Batch Processing
# Uses GNU parallel if available, otherwise sequential with progress tracking

DISCOVERY_DIR="/Users/faisalshomemacmini/.openclaw/workspace/legal/cases/Warp Drive Case/Discovery"
OCR_SCRIPT="/Users/faisalshomemacmini/.openclaw/workspace/legal/scripts/ocr.py"
NOTES_DIR="/Users/faisalshomemacmini/.openclaw/workspace/legal/cases/Warp Drive Case/notes"
PROGRESS_FILE="$NOTES_DIR/batch-progress.json"
BATCH_SIZE=100

# Ensure directories exist
mkdir -p "$NOTES_DIR/batch-summaries"
mkdir -p "/tmp/wde-ocr-batches"

# Get all PDF files, sorted
ALL_FILES="$NOTES_DIR/all-files-sorted.txt"
ls "$DISCOVERY_DIR"/*.pdf 2>/dev/null | sort > "$ALL_FILES"
TOTAL=$(wc -l < "$ALL_FILES")

# Get starting batch (from progress or default to 3 since 1-2 done)
START_BATCH=3
if [ -f "$PROGRESS_FILE" ]; then
    START_BATCH=$(jq -r '.last_completed_batch + 1 // 3' "$PROGRESS_FILE" 2>/dev/null || echo "3")
fi

echo "Total files: $TOTAL"
echo "Starting from batch: $START_BATCH"
echo "Batches remaining: $(( (TOTAL / BATCH_SIZE) - START_BATCH + 1 ))"

# Function to process a single file
process_file() {
    local FILE="$1"
    local BATCH="$2"
    local BASENAME=$(basename "$FILE" .pdf)
    local OUTPUT_DIR="/tmp/wde-ocr-batches/batch_$BATCH"
    mkdir -p "$OUTPUT_DIR"
    python3 "$OCR_SCRIPT" "$FILE" --output "$OUTPUT_DIR/${BASENAME}.md" 2>/dev/null
}
export -f process_file
export OCR_SCRIPT

# Process batches
for ((BATCH=START_BATCH; BATCH<=10000; BATCH++)); do
    START_IDX=$(( ($BATCH-1) * BATCH_SIZE + 1 ))
    END_IDX=$(( $BATCH * BATCH_SIZE ))
    
    echo ""
    echo "╔════════════════════════════════════════════════════════════╗"
    echo "║  BATCH $BATCH (Files $START_IDX - $END_IDX)                      ║"
    echo "║  Progress: $END_IDX / $TOTAL                          ║"
    echo "╚════════════════════════════════════════════════════════════╝"
    
    BATCH_START=$(date +%s)
    BATCH_DIR="/tmp/wde-ocr-batches/batch_$BATCH"
    mkdir -p "$BATCH_DIR"
    
    # Get files for this batch
    sed -n "${START_IDX},${END_IDX}p" "$ALL_FILES" > "/tmp/batch_${BATCH}_list.txt"
    
    # Process batch (sequential for stability, or use parallel if available)
    while read -r FILE; do
        if [ -f "$FILE" ]; then
            BASENAME=$(basename "$FILE" .pdf)
            python3 "$OCR_SCRIPT" "$FILE" --output "$BATCH_DIR/${BASENAME}.md" 2>/dev/null
            echo -n "."
        fi
    done < "/tmp/batch_${BATCH}_list.txt"
    
    # Count results
    OCR_COUNT=$(ls "$BATCH_DIR"/*.md 2>/dev/null | wc -l)
    
    # Generate batch summary
    SUMMARY_FILE="$NOTES_DIR/batch-summaries/Batch-$BATCH-Summary.md"
    BATCH_END=$(date +%s)
    DURATION=$((BATCH_END - BATCH_START))
    
    echo "" > "$SUMMARY_FILE"
    echo "# Batch $BATCH Summary" >> "$SUMMARY_FILE"
    echo "**Date:** $(date)" >> "$SUMMARY_FILE"
    echo "**Files Processed:** $OCR_COUNT" >> "$SUMMARY_FILE"
    echo "**Duration:** ${DURATION}s" >> "$SUMMARY_FILE"
    echo "" >> "$SUMMARY_FILE"
    
    # Quick scan for key terms
    echo "## Key Term Matches:" >> "$SUMMARY_FILE"
    grep -l -i "jacqueline@forge\|forgeadvisors\|warp drive engage" "$BATCH_DIR"/*.md 2>/dev/null | while read -r HIT; do
        echo "- $(basename $HIT)" >> "$SUMMARY_FILE"
    done
    
    # Update progress
    echo "{\"last_completed_batch\": $BATCH, \"total_files\": $TOTAL, \"processed\": $END_IDX, \"last_run\": \"$(date -u +%Y-%m-%dT%H:%M:%SZ)\"}" > "$PROGRESS_FILE"
    
    # Cleanup batch OCR files (keep summary)
    rm -rf "$BATCH_DIR"
    
    echo ""
    echo "✓ Batch $BATCH complete: $OCR_COUNT files in ${DURATION}s"
    echo "  Progress: $(( (END_IDX * 100) / TOTAL ))% complete"
    
    # Every 10 batches, show cumulative stats
    if [ $((BATCH % 10)) -eq 0 ]; then
        echo ""
        echo "═══════════════════════════════════════════════════════════════"
        echo "  MILESTONE: $BATCH batches complete"
        echo "  Files processed: $END_IDX / $TOTAL"
        echo "  Estimated remaining: $(( (TOTAL - END_IDX) / BATCH_SIZE )) batches"
        echo "═══════════════════════════════════════════════════════════════"
    fi
    
done

echo ""
echo "═══════════════════════════════════════════════════════════════"
echo "  ALL BATCHES COMPLETE"
echo "═══════════════════════════════════════════════════════════════"
