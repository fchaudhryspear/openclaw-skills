#!/bin/bash
# Worker 6: Process WDE Discovery batches 451-532
# OCR PDFs, flag forgeadvisors/jacqueline@forge hits, save to batch-summaries

DISCOVERY_DIR="/Users/faisalshomemacmini/.openclaw/workspace/legal/cases/Warp Drive Case/Discovery"
OCR_SCRIPT="/Users/faisalshomemacmini/.openclaw/workspace/legal/scripts/ocr.py"
SUMMARIES_DIR="/Users/faisalshomemacmini/.openclaw/workspace/legal/cases/Warp Drive Case/notes/batch-summaries"
TMPDIR="/tmp/wde-worker-6"
SORTED_LIST="/tmp/wde-worker6-sorted.txt"

mkdir -p "$SUMMARIES_DIR" "$TMPDIR"

# Build sorted PDF list
ls "$DISCOVERY_DIR"/*.pdf 2>/dev/null | sort > "$SORTED_LIST"
TOTAL_PDFS=$(wc -l < "$SORTED_LIST")
echo "Total PDFs in Discovery: $TOTAL_PDFS"

START_BATCH=451
END_BATCH=532
HITS_TOTAL=0
PROCESSED=0
SKIPPED=0
ERRORS=0

echo ""
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║  WORKER 6 — Batches $START_BATCH-$END_BATCH                              ║"
echo "║  $(date)                                  ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""

for BATCH in $(seq $START_BATCH $END_BATCH); do
    # Skip already-processed batches
    if [ -f "$SUMMARIES_DIR/batch-${BATCH}-hits.txt" ]; then
        echo "  ⊘ Batch $BATCH: already exists, skipping"
        SKIPPED=$((SKIPPED + 1))
        continue
    fi

    # Get the PDF for this batch index
    PDF_PATH=$(sed -n "${BATCH}p" "$SORTED_LIST")
    if [ -z "$PDF_PATH" ] || [ ! -f "$PDF_PATH" ]; then
        echo "  ✗ Batch $BATCH: no file at index $BATCH"
        ERRORS=$((ERRORS + 1))
        continue
    fi

    BASENAME=$(basename "$PDF_PATH" .pdf)
    OCR_OUT="$TMPDIR/${BASENAME}.md"

    # OCR the PDF
    python3 "$OCR_SCRIPT" "$PDF_PATH" --output "$OCR_OUT" 2>/dev/null

    if [ ! -f "$OCR_OUT" ]; then
        echo "  ✗ Batch $BATCH ($BASENAME): OCR failed"
        echo "WORKER 6 - Batch $BATCH ($BASENAME): OCR FAILED" > "$SUMMARIES_DIR/batch-${BATCH}-hits.txt"
        ERRORS=$((ERRORS + 1))
        continue
    fi

    # Scan for key terms
    HITS=$(grep -c -i "forgeadvisors\|jacqueline@forge" "$OCR_OUT" 2>/dev/null || echo "0")
    HIT_FILES=""

    if [ "$HITS" -gt 0 ]; then
        HIT_FILES=$(grep -n -i "forgeadvisors\|jacqueline@forge" "$OCR_OUT" 2>/dev/null)
        HITS_TOTAL=$((HITS_TOTAL + 1))
        echo "  ★ Batch $BATCH ($BASENAME): $HITS hit(s) — FLAGGED"
    else
        echo "  ✓ Batch $BATCH ($BASENAME): clean"
    fi

    # Write batch summary
    {
        echo "WORKER 6 - Batch $BATCH: $HITS hit(s)"
        echo "File: $BASENAME.pdf"
        echo "Date: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
        if [ "$HITS" -gt 0 ]; then
            echo ""
            echo "=== HITS ==="
            echo "$HIT_FILES"
            echo ""
            echo "FLAGGED: forgeadvisors/jacqueline@forge match"
        fi
    } > "$SUMMARIES_DIR/batch-${BATCH}-hits.txt"

    PROCESSED=$((PROCESSED + 1))

    # Clean up OCR temp file
    rm -f "$OCR_OUT"

    # Progress every 10 batches
    if [ $(( (BATCH - START_BATCH + 1) % 10 )) -eq 0 ]; then
        echo "  --- Progress: $((BATCH - START_BATCH + 1)) / $((END_BATCH - START_BATCH + 1)) ---"
    fi
done

# Final summary
echo ""
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║  WORKER 6 COMPLETE                                         ║"
echo "║  Processed: $PROCESSED | Skipped: $SKIPPED | Errors: $ERRORS          ║"
echo "║  Flagged hits: $HITS_TOTAL                                      ║"
echo "╚══════════════════════════════════════════════════════════════╝"

# Write master summary
{
    echo "# Worker 6 — Batches $START_BATCH-$END_BATCH Summary"
    echo "**Completed:** $(date)"
    echo "**Processed:** $PROCESSED"
    echo "**Skipped (existing):** $SKIPPED"
    echo "**Errors:** $ERRORS"
    echo "**Flagged (forgeadvisors/jacqueline@forge):** $HITS_TOTAL"
    echo ""
    echo "## Flagged Files:"
    for BATCH in $(seq $START_BATCH $END_BATCH); do
        if [ -f "$SUMMARIES_DIR/batch-${BATCH}-hits.txt" ]; then
            if grep -q "FLAGGED" "$SUMMARIES_DIR/batch-${BATCH}-hits.txt" 2>/dev/null; then
                grep "^File:" "$SUMMARIES_DIR/batch-${BATCH}-hits.txt"
            fi
        fi
    done
} > "$SUMMARIES_DIR/worker6-master-summary.md"

# Cleanup
rm -rf "$TMPDIR"
echo "Master summary: $SUMMARIES_DIR/worker6-master-summary.md"
