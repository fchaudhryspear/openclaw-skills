#!/bin/bash
# Continuous WDE Batch Processing - Automated

cd "/Users/faisalshomemacmini/.openclaw/workspace/legal/cases/Warp Drive Case"

DISCOVERY_DIR="Discovery"
NOTES_DIR="notes/batch-summaries"
PROGRESS_FILE="logs/batch-progress.txt"
BATCH_SIZE=100
OCR_SCRIPT="/Users/faisalshomemacmini/.openclaw/workspace/legal/scripts/ocr.py"

# Get total files
TOTAL=$(ls "$DISCOVERY_DIR" | wc -l)
echo "Starting automated processing of $TOTAL files at $(date)"

# Start from batch 4 (1-3 already done)
for ((BATCH=4; BATCH<=1000; BATCH++)); do
    START=$(( ($BATCH-1) * BATCH_SIZE + 1 ))
    END=$(( $BATCH * BATCH_SIZE ))
    
    BATCH_DIR="/tmp/wde-batch-$BATCH"
    mkdir -p "$BATCH_DIR"
    
    echo "[$(date '+%H:%M:%S')] Batch $BATCH: files $START-$END"
    
    # Get file list
    ls "$DISCOVERY_DIR" | sed -n "${START},${END}p" > "/tmp/batch-$BATCH-list.txt"
    
    # OCR each file
    while read -r FILE; do
        if [ -f "$DISCOVERY_DIR/$FILE" ]; then
            BASENAME=$(basename "$FILE" .pdf)
            python3 "$OCR_SCRIPT" "$DISCOVERY_DIR/$FILE" --output "$BATCH_DIR/${BASENAME}.md" 2>/dev/null
        fi
    done < "/tmp/batch-$BATCH-list.txt"
    
    # Check for smoking gun hits
    HITS=$(grep -l -i "forgeadvisors\|jacqueline@forge\|warp drive engage.*dba\|forge technology advisors" "$BATCH_DIR"/*.md 2>/dev/null | wc -l | tr -d ' ')
    
    if [ "$HITS" -gt 0 ]; then
        echo "SMOKING GUN Batch $BATCH: $HITS files" >> "$NOTES_DIR/batch-$BATCH-hits.txt"
        grep -l -i "forgeadvisors\|jacqueline@forge" "$BATCH_DIR"/*.md 2>/dev/null >> "$NOTES_DIR/batch-$BATCH-hits.txt"
    fi
    
    # Log progress
    echo "BATCH $BATCH: $END/$TOTAL processed at $(date)" >> "$PROGRESS_FILE"
    
    # Cleanup
    rm -rf "$BATCH_DIR"
    
    # Progress report every 10 batches
    if [ $((BATCH % 10)) -eq 0 ]; then
        PCT=$(( (END * 100) / TOTAL ))
        echo "[$(date)] PROGRESS: Batch $BATCH complete ($PCT%)"
    fi
done

echo "Processing complete at $(date)"
