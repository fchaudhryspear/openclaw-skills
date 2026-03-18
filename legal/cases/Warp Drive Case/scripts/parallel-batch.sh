#!/bin/bash
# Parallel WDE Discovery Processing
# Splits 61,270 files across multiple concurrent workers

DISCOVERY_DIR="/Users/faisalshomemacmini/.openclaw/workspace/legal/cases/Warp Drive Case/Discovery"
OCR_SCRIPT="/Users/faisalshomemacmini/.openclaw/workspace/legal/scripts/ocr.py"
NOTES_DIR="/Users/faisalshomemacmini/.openclaw/workspace/legal/cases/Warp Drive Case/notes/batch-summaries"
PROGRESS_FILE="/Users/faisalshomemacmini/.openclaw/workspace/legal/cases/Warp Drive Case/logs/parallel-progress.txt"

mkdir -p "$NOTES_DIR"
mkdir -p "/Users/faisalshomemacmini/.openclaw/workspace/legal/cases/Warp Drive Case/logs"

# Get total files
TOTAL=$(ls "$DISCOVERY_DIR" | wc -l)
echo "Starting parallel processing of $TOTAL files at $(date)"

# Number of parallel workers
WORKERS=8
BATCH_SIZE=100

# Function to process a range of batches
process_range() {
    local START_BATCH=$1
    local END_BATCH=$2
    local WORKER_ID=$3
    
    for ((BATCH=START_BATCH; BATCH<=END_BATCH; BATCH++)); do
        local START=$(( ($BATCH-1) * BATCH_SIZE + 1 ))
        local END=$(( $BATCH * BATCH_SIZE ))
        local BATCH_DIR="/tmp/wde-worker-$WORKER_ID-batch-$BATCH"
        mkdir -p "$BATCH_DIR"
        
        # Get file list for this batch
        ls "$DISCOVERY_DIR" | sed -n "${START},${END}p" > "/tmp/worker-$WORKER_ID-batch-$BATCH-list.txt"
        
        # Process each file
        while read -r FILE; do
            if [ -f "$DISCOVERY_DIR/$FILE" ]; then
                local BASENAME=$(basename "$FILE" .pdf)
                python3 "$OCR_SCRIPT" "$DISCOVERY_DIR/$FILE" --output "$BATCH_DIR/${BASENAME}.md" 2>/dev/null
            fi
        done < "/tmp/worker-$WORKER_ID-batch-$BATCH-list.txt"
        
        # Check for smoking gun hits
        local HITS=$(grep -l -i "forgeadvisors\|jacqueline@forge\|warp drive engage.*dba\|travis.*okeefe\|michael.*brennan" "$BATCH_DIR"/*.md 2>/dev/null | wc -l | tr -d ' ')
        
        if [ "$HITS" -gt 0 ]; then
            echo "WORKER $WORKER_ID - SMOKING GUN Batch $BATCH: $HITS files" >> "$NOTES_DIR/batch-$BATCH-hits.txt"
            grep -l -i "forgeadvisors\|jacqueline@forge" "$BATCH_DIR"/*.md 2>/dev/null >> "$NOTES_DIR/batch-$BATCH-hits.txt"
        fi
        
        # Log progress
        echo "WORKER $WORKER_ID - BATCH $BATCH: $END/$TOTAL processed at $(date)" >> "$PROGRESS_FILE"
        
        # Cleanup
        rm -rf "$BATCH_DIR"
        
        # Progress report every 10 batches per worker
        if [ $((BATCH % 10)) -eq 0 ]; then
            local PCT=$(( (END * 100) / TOTAL ))
            echo "[$(date)] WORKER $WORKER_ID - Batch $BATCH complete ($PCT%)"
        fi
    done
}

# Calculate batches per worker
TOTAL_BATCHES=$(( (TOTAL + BATCH_SIZE - 1) / BATCH_SIZE ))
BATCHES_PER_WORKER=$(( (TOTAL_BATCHES + WORKERS - 1) / WORKERS ))

echo "Total batches: $TOTAL_BATCHES"
echo "Batches per worker: $BATCHES_PER_WORKER"
echo "Workers: $WORKERS"
echo "---"

# Launch parallel workers
for ((W=1; W<=WORKERS; W++)); do
    START=$(( ($W-1) * BATCHES_PER_WORKER + 1 ))
    END=$(( $W * BATCHES_PER_WORKER ))
    if [ $END -gt $TOTAL_BATCHES ]; then
        END=$TOTAL_BATCHES
    fi
    
    echo "Launching Worker $W: batches $START-$END"
    process_range $START $END $W &
    PIDS[$W]=$!
done

# Wait for all workers
echo "Waiting for all workers to complete..."
for ((W=1; W<=WORKERS; W++)); do
    wait ${PIDS[$W]}
    echo "Worker $W complete"
done

echo ""
echo "═══════════════════════════════════════════════════════════════"
echo "  ALL WORKERS COMPLETE"
echo "  Finished at $(date)"
echo "═══════════════════════════════════════════════════════════════"
