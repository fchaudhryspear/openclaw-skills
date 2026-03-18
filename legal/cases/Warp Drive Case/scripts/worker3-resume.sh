#!/bin/bash
# Worker 3 Resume: Process batches 205-286
# Files 20401-28600 of 61,340 discovery documents

DISCOVERY_DIR="/Users/faisalshomemacmini/.openclaw/workspace/legal/cases/Warp Drive Case/Discovery"
OCR_SCRIPT="/Users/faisalshomemacmini/.openclaw/workspace/legal/scripts/ocr.py"
NOTES_DIR="/Users/faisalshomemacmini/.openclaw/workspace/legal/cases/Warp Drive Case/notes/batch-summaries"
LOG_FILE="/Users/faisalshomemacmini/.openclaw/workspace/legal/cases/Warp Drive Case/logs/worker3.log"
BATCH_SIZE=100

# Pre-generate full sorted file list once
FILE_LIST="/tmp/wde-worker3-filelist.txt"
ls "$DISCOVERY_DIR" > "$FILE_LIST"
TOTAL=$(wc -l < "$FILE_LIST" | tr -d ' ')

echo "Worker 3 RESUME: batches 205-286 starting at $(date)" > "$LOG_FILE"
echo "Total discovery files: $TOTAL" >> "$LOG_FILE"

TOTAL_HITS=0
TOTAL_FORGE_HITS=0

for BATCH in $(seq 205 286); do
    START=$(( (BATCH - 1) * BATCH_SIZE + 1 ))
    END=$(( BATCH * BATCH_SIZE ))
    BATCH_DIR="/tmp/wde-w3-b${BATCH}"
    mkdir -p "$BATCH_DIR"

    # Extract files for this batch from pre-generated list
    sed -n "${START},${END}p" "$FILE_LIST" > "/tmp/w3-b${BATCH}.txt"

    # OCR each file
    PROCESSED=0
    while IFS= read -r FILE; do
        if [ -n "$FILE" ] && [ -f "$DISCOVERY_DIR/$FILE" ]; then
            BASENAME="${FILE%.pdf}"
            python3 "$OCR_SCRIPT" "$DISCOVERY_DIR/$FILE" --output "$BATCH_DIR/${BASENAME}.md" 2>/dev/null
            PROCESSED=$((PROCESSED + 1))
        fi
    done < "/tmp/w3-b${BATCH}.txt"

    # Search for hits - write matches to temp files
    HIT_COUNT=0
    FORGE_COUNT=0

    if compgen -G "$BATCH_DIR/*.md" > /dev/null 2>&1; then
        grep -r -l -i 'forgeadvisors\|jacqueline@forge\|warp drive engage.*dba\|travis.*okeefe\|michael.*brennan' "$BATCH_DIR/" 2>/dev/null > "/tmp/w3-hits-${BATCH}.txt" || true
        HIT_COUNT=$(wc -l < "/tmp/w3-hits-${BATCH}.txt" | tr -d ' ')

        grep -r -l -i 'forgeadvisors\|jacqueline@forge' "$BATCH_DIR/" 2>/dev/null > "/tmp/w3-forge-${BATCH}.txt" || true
        FORGE_COUNT=$(wc -l < "/tmp/w3-forge-${BATCH}.txt" | tr -d ' ')
    fi

    # Write batch summary
    SUMMARY_FILE="$NOTES_DIR/batch-${BATCH}-hits.txt"
    {
        echo "WORKER 3 - Batch ${BATCH}: ${PROCESSED} files processed (file range ${START}-${END})"
        echo "Scan date: $(date)"
        echo "---"
    } > "$SUMMARY_FILE"

    if [ "$HIT_COUNT" -gt 0 ]; then
        {
            echo "SMOKING GUN HITS: ${HIT_COUNT} files"
            cat "/tmp/w3-hits-${BATCH}.txt"
            echo ""
        } >> "$SUMMARY_FILE"
    else
        echo "No keyword hits in this batch." >> "$SUMMARY_FILE"
    fi

    if [ "$FORGE_COUNT" -gt 0 ]; then
        {
            echo "FORGE/JACQUELINE HITS: ${FORGE_COUNT} files"
            cat "/tmp/w3-forge-${BATCH}.txt"
            echo ""
            echo "--- FORGE HIT CONTEXT ---"
        } >> "$SUMMARY_FILE"

        while IFS= read -r HIT_FILE; do
            if [ -n "$HIT_FILE" ]; then
                echo "=== $(basename "$HIT_FILE") ===" >> "$SUMMARY_FILE"
                grep -i -B2 -A2 'forgeadvisors\|jacqueline@forge' "$HIT_FILE" >> "$SUMMARY_FILE" 2>/dev/null
                echo "" >> "$SUMMARY_FILE"
            fi
        done < "/tmp/w3-forge-${BATCH}.txt"
    fi

    TOTAL_HITS=$((TOTAL_HITS + HIT_COUNT))
    TOTAL_FORGE_HITS=$((TOTAL_FORGE_HITS + FORGE_COUNT))

    # Cleanup
    rm -rf "$BATCH_DIR"
    rm -f "/tmp/w3-b${BATCH}.txt" "/tmp/w3-hits-${BATCH}.txt" "/tmp/w3-forge-${BATCH}.txt"

    # Progress logging
    PCT=$(( (END * 100) / TOTAL ))
    echo "WORKER 3 - BATCH ${BATCH}: ${END}/${TOTAL} (${PCT}%) at $(date) | hits=${HIT_COUNT} forge=${FORGE_COUNT}" >> "$LOG_FILE"

    if [ $((BATCH % 10)) -eq 0 ]; then
        echo "[$(date)] WORKER 3 - Batch ${BATCH} (${PCT}%) | cumul hits=${TOTAL_HITS} forge=${TOTAL_FORGE_HITS}"
    fi
done

rm -f "$FILE_LIST"

{
    echo ""
    echo "======================================="
    echo "WORKER 3 COMPLETE at $(date)"
    echo "Batches: 205-286 (82 batches)"
    echo "Total keyword hits: ${TOTAL_HITS}"
    echo "Total forge/jacqueline hits: ${TOTAL_FORGE_HITS}"
    echo "======================================="
} >> "$LOG_FILE"

echo ""
echo "======================================="
echo "  WORKER 3 COMPLETE at $(date)"
echo "  Total keyword hits: ${TOTAL_HITS}"
echo "  Total forge/jacqueline hits: ${TOTAL_FORGE_HITS}"
echo "======================================="
