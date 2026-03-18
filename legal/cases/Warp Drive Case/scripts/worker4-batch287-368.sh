#!/bin/sh
# Worker 4: WDE Discovery Batch Processing (Batches 287-368)
# Processes PDFs via OCR, flags forgeadvisors/jacqueline@forge hits
# Saves results to notes/batch-summaries/

BASE_DIR="/Users/faisalshomemacmini/.openclaw/workspace/legal/cases/Warp Drive Case"
DISCOVERY_DIR="$BASE_DIR/Discovery"
OCR_SCRIPT="/Users/faisalshomemacmini/.openclaw/workspace/legal/scripts/ocr.py"
NOTES_DIR="$BASE_DIR/notes/batch-summaries"
FILE_LIST="/tmp/wde-all-files-sorted.txt"
BATCH_SIZE=100
WORKER=4
START_BATCH=287
END_BATCH=368
LOG_FILE="$BASE_DIR/logs/worker4-progress.log"

mkdir -p "$NOTES_DIR" "$BASE_DIR/logs"

# Build sorted file list if not present
if [ ! -f "$FILE_LIST" ] || [ "$(wc -l < "$FILE_LIST" | tr -d ' ')" = "0" ]; then
    echo "[Worker $WORKER] Building file index..."
    find "$DISCOVERY_DIR" -maxdepth 1 -name '*.pdf' -type f | sort > "$FILE_LIST"
fi

TOTAL=$(wc -l < "$FILE_LIST" | tr -d ' ')
echo "[Worker $WORKER] Total Discovery PDFs: $TOTAL"
echo "[Worker $WORKER] Processing batches $START_BATCH - $END_BATCH"
echo "=================================="

HITS_TOTAL=0
BATCHES_DONE=0
BATCHES_SKIPPED=0

BATCH=$START_BATCH
while [ "$BATCH" -le "$END_BATCH" ]; do
    HITS_FILE="$NOTES_DIR/batch-$BATCH-hits.txt"

    # Skip if already processed
    if [ -f "$HITS_FILE" ]; then
        echo "[Worker $WORKER] Batch $BATCH: SKIP (already exists)"
        BATCHES_SKIPPED=$((BATCHES_SKIPPED + 1))
        BATCH=$((BATCH + 1))
        continue
    fi

    START_IDX=$(( (BATCH - 1) * BATCH_SIZE + 1 ))
    END_IDX=$(( BATCH * BATCH_SIZE ))
    BATCH_DIR="/tmp/wde-worker-${WORKER}-batch-${BATCH}"
    mkdir -p "$BATCH_DIR"

    printf "[Worker %s] Batch %s (files %s-%s): " "$WORKER" "$BATCH" "$START_IDX" "$END_IDX"

    BATCH_START=$(date +%s)
    FILE_COUNT=0

    # Extract file list for this batch
    sed -n "${START_IDX},${END_IDX}p" "$FILE_LIST" > "/tmp/worker4-batch-${BATCH}-list.txt"

    # OCR each file
    while IFS= read -r FILE; do
        if [ -f "$FILE" ]; then
            BASENAME=$(basename "$FILE" .pdf)
            python3 "$OCR_SCRIPT" "$FILE" --output "$BATCH_DIR/${BASENAME}.md" 2>/dev/null || true
            FILE_COUNT=$((FILE_COUNT + 1))
            if [ $((FILE_COUNT % 10)) -eq 0 ]; then
                printf "."
            fi
        fi
    done < "/tmp/worker4-batch-${BATCH}-list.txt"

    BATCH_END=$(date +%s)
    DURATION=$((BATCH_END - BATCH_START))

    # Check for smoking gun hits
    BATCH_HITS=0
    HIT_FILES=""
    if ls "$BATCH_DIR"/*.md 1>/dev/null 2>&1; then
        HIT_FILES=$(grep -rl -i -E "forgeadvisors|jacqueline@forge|forge technology advisors|warp drive engage.*dba|jacqueline.*catala.*forge|forge.*advisory" "$BATCH_DIR"/ 2>/dev/null || true)
        if [ -n "$HIT_FILES" ]; then
            BATCH_HITS=$(echo "$HIT_FILES" | wc -l | tr -d ' ')
        fi
    fi

    # Write batch summary
    echo "WORKER $WORKER - SMOKING GUN Batch $BATCH: $BATCH_HITS files" > "$HITS_FILE"
    if [ -n "$HIT_FILES" ]; then
        echo "$HIT_FILES" >> "$HITS_FILE"
        echo "" >> "$HITS_FILE"
        echo "--- HIT DETAILS ---" >> "$HITS_FILE"
        echo "$HIT_FILES" | while IFS= read -r HIT; do
            echo "" >> "$HITS_FILE"
            echo "=== $(basename "$HIT") ===" >> "$HITS_FILE"
            grep -i -E "forgeadvisors|jacqueline@forge|forge technology advisors|warp drive engage.*dba|jacqueline.*catala.*forge|forge.*advisory" "$HIT" 2>/dev/null | head -5 >> "$HITS_FILE"
        done
    fi

    HITS_TOTAL=$((HITS_TOTAL + BATCH_HITS))
    BATCHES_DONE=$((BATCHES_DONE + 1))

    # Cleanup OCR temp files
    rm -rf "$BATCH_DIR"
    rm -f "/tmp/worker4-batch-${BATCH}-list.txt"

    if [ "$BATCH_HITS" -gt 0 ]; then
        echo " ${FILE_COUNT} files, ${DURATION}s | *** $BATCH_HITS HITS ***"
    else
        echo " ${FILE_COUNT} files, ${DURATION}s | clean"
    fi

    # Log progress
    echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) | Batch $BATCH | ${FILE_COUNT} files | ${DURATION}s | ${BATCH_HITS} hits" >> "$LOG_FILE"

    # Milestone report every 10 batches
    PROGRESS=$(( (BATCH - START_BATCH + 1) % 10 ))
    if [ "$PROGRESS" -eq 0 ]; then
        echo ""
        echo "==========================================="
        echo "  WORKER $WORKER MILESTONE: Batch $BATCH"
        echo "  Batches done: $BATCHES_DONE | Skipped: $BATCHES_SKIPPED"
        echo "  Total hits so far: $HITS_TOTAL"
        echo "==========================================="
        echo ""
    fi

    BATCH=$((BATCH + 1))
done

echo ""
echo "========================================================"
echo "  WORKER $WORKER COMPLETE"
echo "  Batches processed: $BATCHES_DONE (skipped: $BATCHES_SKIPPED)"
echo "  Total forge/jacqueline hits: $HITS_TOTAL"
echo "========================================================"
