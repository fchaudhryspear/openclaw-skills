#!/bin/bash
# Worker 5 Resume: Process batches 369-450
# Each batch = 100 files from sorted Discovery directory listing

DISCOVERY_DIR="/Users/faisalshomemacmini/.openclaw/workspace/legal/cases/Warp Drive Case/Discovery"
OCR_SCRIPT="/Users/faisalshomemacmini/.openclaw/workspace/legal/scripts/ocr.py"
NOTES_DIR="/Users/faisalshomemacmini/.openclaw/workspace/legal/cases/Warp Drive Case/notes/batch-summaries"
PROGRESS_FILE="/Users/faisalshomemacmini/.openclaw/workspace/legal/cases/Warp Drive Case/logs/parallel-progress.txt"
BATCH_SIZE=100
TOTAL=61340

mkdir -p "$NOTES_DIR"

# Get sorted file list once
FILE_LIST="/tmp/wde-worker5-filelist.txt"
ls "$DISCOVERY_DIR" | sort > "$FILE_LIST"

echo "Worker 5 Resume: Batches 369-450 starting at $(date)"
echo "=================================================="

for BATCH in $(seq 369 450); do
    START=$(( ($BATCH-1) * BATCH_SIZE + 1 ))
    END=$(( $BATCH * BATCH_SIZE ))
    BATCH_DIR="/tmp/wde-worker-5-batch-$BATCH"
    mkdir -p "$BATCH_DIR"

    # Get files for this batch
    sed -n "${START},${END}p" "$FILE_LIST" > "/tmp/worker-5-batch-$BATCH-list.txt"
    FILE_COUNT=$(wc -l < "/tmp/worker-5-batch-$BATCH-list.txt" | tr -d ' ')

    if [ "$FILE_COUNT" -eq 0 ]; then
        echo "BATCH $BATCH: No files — skipping"
        continue
    fi

    BATCH_START=$(date +%s)
    PROCESSED=0

    # Process each file
    while read -r FILE; do
        if [ -f "$DISCOVERY_DIR/$FILE" ]; then
            BASENAME=$(basename "$FILE" .pdf)
            python3 "$OCR_SCRIPT" "$DISCOVERY_DIR/$FILE" --output "$BATCH_DIR/${BASENAME}.md" 2>/dev/null
            PROCESSED=$((PROCESSED + 1))
        fi
    done < "/tmp/worker-5-batch-$BATCH-list.txt"

    BATCH_END=$(date +%s)
    DURATION=$((BATCH_END - BATCH_START))

    # Check for smoking gun hits
    HITS=0
    HIT_FILES=""
    if ls "$BATCH_DIR"/*.md 1>/dev/null 2>&1; then
        HIT_FILES=$(grep -l -i "forgeadvisors\|jacqueline@forge\|warp drive engage.*dba\|travis.*okeefe\|michael.*brennan" "$BATCH_DIR"/*.md 2>/dev/null)
        if [ -n "$HIT_FILES" ]; then
            HITS=$(echo "$HIT_FILES" | wc -l | tr -d ' ')
            echo "WORKER 5 - SMOKING GUN Batch $BATCH: $HITS files" > "$NOTES_DIR/batch-$BATCH-hits.txt"
            echo "$HIT_FILES" >> "$NOTES_DIR/batch-$BATCH-hits.txt"

            # Extract matching lines for context
            echo "" >> "$NOTES_DIR/batch-$BATCH-hits.txt"
            echo "=== HIT CONTEXT ===" >> "$NOTES_DIR/batch-$BATCH-hits.txt"
            grep -i -H "forgeadvisors\|jacqueline@forge\|warp drive engage.*dba\|travis.*okeefe\|michael.*brennan" $HIT_FILES >> "$NOTES_DIR/batch-$BATCH-hits.txt" 2>/dev/null
        fi
    fi

    # Log progress
    echo "WORKER 5 - BATCH $BATCH: $END/$TOTAL processed at $(date)" >> "$PROGRESS_FILE"

    # Console output
    if [ "$HITS" -gt 0 ]; then
        echo "BATCH $BATCH: $PROCESSED files, ${DURATION}s — *** $HITS HITS ***"
    else
        echo "BATCH $BATCH: $PROCESSED files, ${DURATION}s — no hits"
    fi

    # Cleanup OCR temp files
    rm -rf "$BATCH_DIR"
    rm -f "/tmp/worker-5-batch-$BATCH-list.txt"
done

rm -f "$FILE_LIST"

echo ""
echo "=================================================="
echo "Worker 5 batches 369-450 COMPLETE at $(date)"
echo "=================================================="

# Summary of all hits
echo ""
echo "=== ALL HITS FROM BATCHES 369-450 ==="
cat "$NOTES_DIR"/batch-{369..450}-hits.txt 2>/dev/null || echo "No hits found in this range."
