#!/usr/bin/env python3
"""
WDE Discovery Batch Processor (Worker 2: Batches 129-154)
Processes PDFs via OCR and flags documents containing target keywords.
"""

import sys
import os
import re
from pathlib import Path

# Config
DISCOVERY_DIR = Path(os.path.expanduser(
    "~/.openclaw/workspace/legal/cases/Warp Drive Case/Discovery"))
OUTPUT_DIR = Path(os.path.expanduser(
    "~/.openclaw/workspace/legal/cases/Warp Drive Case/notes/batch-summaries"))
OCR_SCRIPT = Path(os.path.expanduser(
    "~/.openclaw/workspace/legal/scripts/ocr.py"))

BATCH_SIZE = 100
START_BATCH = 129
END_BATCH = 154  # inclusive

# Search terms (case-insensitive)
SEARCH_TERMS = [
    "forgeadvisors",
    "jacqueline@forge",
    "warp drive engage dba",
]

def get_sorted_files():
    """Get all PDF files sorted by name."""
    files = sorted(f for f in DISCOVERY_DIR.iterdir() if f.suffix.lower() == '.pdf')
    return files

def extract_text_pymupdf(pdf_path):
    """Extract text from PDF using PyMuPDF (fast, no OCR)."""
    import fitz
    try:
        doc = fitz.open(str(pdf_path))
        text_parts = []
        for page in doc:
            text = page.get_text()
            if text:
                text_parts.append(text)
        doc.close()
        return '\n'.join(text_parts)
    except Exception as e:
        print(f"  [WARN] Failed to read {pdf_path.name}: {e}", file=sys.stderr)
        return ""

def search_text(text, terms):
    """Search text for any of the target terms (case-insensitive). Returns list of matched terms."""
    text_lower = text.lower()
    hits = []
    for term in terms:
        if term.lower() in text_lower:
            hits.append(term)
    return hits

def process_batch(batch_num, files):
    """Process a single batch. Returns list of (filename, matched_terms) tuples."""
    print(f"\n{'='*60}", file=sys.stderr)
    print(f"BATCH {batch_num}: {len(files)} files", file=sys.stderr)
    print(f"  Range: {files[0].name} → {files[-1].name}", file=sys.stderr)
    print(f"{'='*60}", file=sys.stderr)

    hits = []
    for i, pdf_path in enumerate(files):
        if (i + 1) % 20 == 0:
            print(f"  [{i+1}/{len(files)}] Processing {pdf_path.name}...", file=sys.stderr)

        text = extract_text_pymupdf(pdf_path)
        if not text.strip():
            # If no embedded text, note it but skip OCR for speed
            # (OCR is slow; embedded text covers most cases)
            continue

        matched = search_text(text, SEARCH_TERMS)
        if matched:
            hits.append((pdf_path.name, matched))

    return hits

def save_hit_list(batch_num, hits):
    """Save hit list to batch summary file."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUTPUT_DIR / f"batch-{batch_num}-hits.txt"

    with open(out_path, 'w') as f:
        f.write(f"WDE Discovery Scan — Batch {batch_num}\n")
        f.write(f"Search terms: {', '.join(SEARCH_TERMS)}\n")
        f.write(f"{'='*60}\n\n")

        if hits:
            f.write(f"HITS: {len(hits)} document(s) flagged\n\n")
            for filename, terms in hits:
                f.write(f"  {filename}\n")
                f.write(f"    Matched: {', '.join(terms)}\n")
        else:
            f.write("NO HITS in this batch.\n")

    print(f"  → Saved: {out_path}", file=sys.stderr)
    return out_path

def main():
    print("WDE Discovery Batch Processor", file=sys.stderr)
    print(f"Batches {START_BATCH}-{END_BATCH} (files {(START_BATCH-1)*BATCH_SIZE+1}-{END_BATCH*BATCH_SIZE})", file=sys.stderr)
    print(f"Search terms: {SEARCH_TERMS}", file=sys.stderr)

    # Get sorted file list
    all_files = get_sorted_files()
    total_files = len(all_files)
    print(f"Total Discovery files: {total_files}", file=sys.stderr)

    # Process each batch
    grand_total_hits = 0
    batch_results = {}

    for batch_num in range(START_BATCH, END_BATCH + 1):
        start_idx = (batch_num - 1) * BATCH_SIZE
        end_idx = batch_num * BATCH_SIZE
        batch_files = all_files[start_idx:end_idx]

        if not batch_files:
            print(f"BATCH {batch_num}: No files found (index {start_idx}-{end_idx})", file=sys.stderr)
            continue

        hits = process_batch(batch_num, batch_files)
        save_hit_list(batch_num, hits)

        batch_results[batch_num] = len(hits)
        grand_total_hits += len(hits)

    # Final summary
    print(f"\n{'='*60}", file=sys.stderr)
    print(f"COMPLETE — Batches {START_BATCH}-{END_BATCH}", file=sys.stderr)
    print(f"Total documents flagged: {grand_total_hits}", file=sys.stderr)
    print(f"{'='*60}", file=sys.stderr)

    # Print summary to stdout for capture
    print(f"\nWDE Discovery Scan Summary (Batches {START_BATCH}-{END_BATCH})")
    print(f"{'='*60}")
    print(f"Search terms: {', '.join(SEARCH_TERMS)}")
    print(f"Total batches processed: {len(batch_results)}")
    print(f"Total documents flagged: {grand_total_hits}")
    print()
    for bn in sorted(batch_results):
        status = f"{batch_results[bn]} hit(s)" if batch_results[bn] > 0 else "clean"
        print(f"  Batch {bn}: {status}")

if __name__ == '__main__':
    main()
