#!/bin/bash
# Worker 1 - Batches 52-75 (files 5101-7500 from sorted Discovery listing)
# Processes PDFs via OCR, searches for smoking gun keywords

CASE_DIR="/Users/faisalshomemacmini/.openclaw/workspace/legal/cases/Warp Drive Case"
DISC_DIR="$CASE_DIR/Discovery"
OCR_SCRIPT="/Users/faisalshomemacmini/.openclaw/workspace/legal/scripts/ocr.py"
SUMMARY_DIR="$CASE_DIR/notes/batch-summaries"
TMP_BASE="/tmp/wde-worker-1"
LOG="$CASE_DIR/logs/worker1-resume.log"

KEYWORDS="forgeadvisors|jacqueline@forge|warp.drive.engage.*dba"
BATCH_SIZE=100
START_BATCH=52
END_BATCH=75

mkdir -p "$SUMMARY_DIR"

# Get sorted file list
FILELIST=$(mktemp)
ls "$DISC_DIR" | sort > "$FILELIST"
TOTAL_FILES=$(wc -l < "$FILELIST")

echo "[$(date)] Worker 1 resuming: batches $START_BATCH-$END_BATCH" | tee -a "$LOG"

for BATCH in $(seq $START_BATCH $END_BATCH); do
    BATCH_START=$(( (BATCH - 1) * BATCH_SIZE + 1 ))
    BATCH_END=$(( BATCH * BATCH_SIZE ))

    SUMMARY_FILE="$SUMMARY_DIR/batch-${BATCH}-hits.txt"

    # Skip if already processed
    if [ -f "$SUMMARY_FILE" ]; then
        echo "[$(date)] Batch $BATCH: already exists, skipping" | tee -a "$LOG"
        continue
    fi

    BATCH_DIR="$TMP_BASE-batch-$BATCH"
    mkdir -p "$BATCH_DIR"

    # Get files for this batch
    BATCH_FILES=$(sed -n "${BATCH_START},${BATCH_END}p" "$FILELIST")
    FILE_COUNT=$(echo "$BATCH_FILES" | wc -l | tr -d ' ')

    echo "[$(date)] Batch $BATCH: processing $FILE_COUNT files (indices $BATCH_START-$BATCH_END)" | tee -a "$LOG"

    HITS=()
    PROCESSED=0
    ERRORS=0

    while IFS= read -r fname; do
        [ -z "$fname" ] && continue
        PDF_PATH="$DISC_DIR/$fname"
        BASENAME=$(echo "$fname" | sed 's/\.pdf$//' | sed 's/CONFIDENTIAL - *//' | tr ' ' '_')
        MD_PATH="$BATCH_DIR/${BASENAME}.md"

        # OCR the PDF
        if python3 "$OCR_SCRIPT" "$PDF_PATH" --output "$MD_PATH" 2>/dev/null; then
            PROCESSED=$((PROCESSED + 1))

            # Search for keywords (case-insensitive)
            if grep -qiE "$KEYWORDS" "$MD_PATH" 2>/dev/null; then
                HITS+=("$MD_PATH")
            fi
        else
            ERRORS=$((ERRORS + 1))
        fi

    done <<< "$BATCH_FILES"

    # Write batch summary
    HIT_COUNT=${#HITS[@]}
    {
        echo "WORKER 1 - SMOKING GUN Batch $BATCH: $FILE_COUNT files"
        if [ $HIT_COUNT -gt 0 ]; then
            for h in "${HITS[@]}"; do
                echo "$h"
            done
        else
            echo "(no keyword hits)"
        fi
    } > "$SUMMARY_FILE"

    echo "[$(date)] Batch $BATCH: done — $PROCESSED processed, $ERRORS errors, $HIT_COUNT hits" | tee -a "$LOG"

done

rm -f "$FILELIST"
echo "[$(date)] Worker 1 batches $START_BATCH-$END_BATCH COMPLETE" | tee -a "$LOG"
