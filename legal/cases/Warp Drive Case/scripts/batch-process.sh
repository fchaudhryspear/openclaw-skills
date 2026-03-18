#!/bin/bash
# Automated WDE Discovery Batch Processing
# Runs continuously, processing 100 files at a time

DISCOVERY_DIR="/Users/faisalshomemacmini/.openclaw/workspace/legal/cases/Warp Drive Case/Discovery"
OCR_SCRIPT="/Users/faisalshomemacmini/.openclaw/workspace/legal/scripts/ocr.py"
NOTES_DIR="/Users/faisalshomemacmini/.openclaw/workspace/legal/cases/Warp Drive Case/notes/batch-reviews"
BATCH_SIZE=100

# Create output directories
mkdir -p "$NOTES_DIR"
mkdir -p "/tmp/wde-ocr-batches"

# Get total file count
TOTAL_FILES=$(ls "$DISCOVERY_DIR" | wc -l)
echo "Total files to process: $TOTAL_FILES"

# Process starting from batch 3 (after 200 already done)
START_BATCH=3
for ((BATCH=$START_BATCH; BATCH<=1000; BATCH++)); do
    START=$(( ($BATCH-1) * BATCH_SIZE + 1 ))
    END=$(( $BATCH * BATCH_SIZE ))
    
    echo "=== BATCH $BATCH (Files $START-$END) ==="
    BATCH_DIR="/tmp/wde-ocr-batches/batch_$BATCH"
    mkdir -p "$BATCH_DIR"
    
    # Get file list for this batch
    ls "$DISCOVERY_DIR" | sed -n "${START},${END}p" > "/tmp/batch_${BATCH}_files.txt"
    
    # Process each file
    while read -r FILE; do
        if [ -f "$DISCOVERY_DIR/$FILE" ]; then
            BASENAME=$(basename "$FILE" .pdf)
            python3 "$OCR_SCRIPT" "$DISCOVERY_DIR/$FILE" --output "$BATCH_DIR/${BASENAME}.md" 2>/dev/null
        fi
    done < "/tmp/batch_${BATCH}_files.txt"
    
    # Count processed files
    PROCESSED=$(ls "$BATCH_DIR" | wc -l)
    echo "Batch $BATCH complete: $PROCESSED files OCR'd"
    echo "$BATCH,$PROCESSED,$(date +%Y-%m-%d-%H:%M:%S)" >> "$NOTES_DIR/progress.log"
    
    # Generate summary for batch (key documents only)
    echo "Generating summary for Batch $BATCH..."
    
    # Look for smoking gun keywords
    grep -l -i "forge\|spearhead\|warp drive\|caesars\|adobe\|jacqueline" "$BATCH_DIR"/*.md 2>/dev/null | head -20 > "/tmp/batch_${BATCH}_hits.txt"
    
    if [ -s "/tmp/batch_${BATCH}_hits.txt" ]; then
        echo "SMOKING GUN CANDIDATES in Batch $BATCH:" > "$NOTES_DIR/Batch-$BATCH-Summary.md"
        cat "/tmp/batch_${BATCH}_hits.txt" >> "$NOTES_DIR/Batch-$BATCH-Summary.md"
    fi
    
    # Cleanup OCR files to save space (keep summaries)
    rm -rf "$BATCH_DIR"
    
    echo "Batch $BATCH complete. Progress: $END/$TOTAL_FILES"
    echo "---"
done

echo "All batches complete!"
