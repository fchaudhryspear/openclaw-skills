#!/usr/bin/env python3
"""Worker 7 - WDE Discovery Batch Processing (Batches 533-614)
Fast text extraction via PyMuPDF, flags forge/jacqueline hits.
Saves per-batch summaries to notes/batch-summaries/
"""

import os
import re
import time
import subprocess
from pathlib import Path
from datetime import datetime

CASE_DIR = Path("/Users/faisalshomemacmini/.openclaw/workspace/legal/cases/Warp Drive Case")
DISCOVERY_DIR = CASE_DIR / "Discovery"
SUMMARIES_DIR = CASE_DIR / "notes" / "batch-summaries"
BATCH_SIZE = 100
START_BATCH = 533
END_BATCH = 614

# Search patterns (case-insensitive)
SEARCH_PATTERN = re.compile(
    r"forgeadvisors|jacqueline@forge|forge\s*advisors|jacqueline.*forge|forge.*jacqueline",
    re.IGNORECASE
)

SUMMARIES_DIR.mkdir(parents=True, exist_ok=True)

# Get sorted file list
print("Scanning Discovery directory...")
all_files = sorted(f for f in DISCOVERY_DIR.iterdir() if f.suffix.lower() == ".pdf")
total_files = len(all_files)
print(f"Total Discovery files: {total_files}")
print(f"Worker 7: Batches {START_BATCH}-{END_BATCH}")
print("=" * 50)

all_hits_file = SUMMARIES_DIR / "worker7-all-hits.txt"
all_hits = []

total_processed = 0
total_hits = 0
total_errors = 0

def extract_text_pdftotext(pdf_path):
    """Fast extraction via pdftotext CLI."""
    try:
        result = subprocess.run(
            ["pdftotext", str(pdf_path), "-"],
            capture_output=True, text=True, timeout=30
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout
    except Exception:
        pass
    return None

def extract_text_pymupdf(pdf_path):
    """Fallback extraction via PyMuPDF."""
    try:
        import fitz
        doc = fitz.open(str(pdf_path))
        text = ""
        for page in doc:
            text += page.get_text()
        doc.close()
        return text if text.strip() else None
    except Exception:
        return None

for batch_num in range(START_BATCH, END_BATCH + 1):
    start_idx = (batch_num - 1) * BATCH_SIZE
    end_idx = batch_num * BATCH_SIZE

    if start_idx >= total_files:
        print(f"Batch {batch_num}: beyond file count, stopping.")
        break

    end_idx = min(end_idx, total_files)
    batch_files = all_files[start_idx:end_idx]
    batch_count = len(batch_files)
    batch_hits = 0
    batch_errors = 0
    batch_hit_names = []
    batch_start = time.time()

    for pdf_path in batch_files:
        basename = pdf_path.stem

        # Try pdftotext first (fastest)
        text = extract_text_pdftotext(pdf_path)
        if text is None:
            text = extract_text_pymupdf(pdf_path)
        if text is None:
            batch_errors += 1
            continue

        # Search for hits
        if SEARCH_PATTERN.search(text):
            batch_hits += 1
            batch_hit_names.append(basename)
            # Get matching lines for the log
            matches = []
            for line in text.split("\n"):
                if SEARCH_PATTERN.search(line):
                    matches.append(line.strip()[:200])
                    if len(matches) >= 3:
                        break
            hit_line = f"Batch {batch_num} | {basename} | {matches[0] if matches else 'pattern match'}"
            all_hits.append(hit_line)

    batch_duration = time.time() - batch_start
    total_processed += batch_count
    total_hits += batch_hits
    total_errors += batch_errors

    # Write batch summary
    summary_file = SUMMARIES_DIR / f"batch-{batch_num}-summary.md"
    hit_list = "\n".join(f"  - {n}" for n in batch_hit_names) if batch_hit_names else "No hits in this batch."
    summary_file.write_text(
        f"# Batch {batch_num} Summary (Worker 7)\n"
        f"**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        f"**Files:** {start_idx+1} - {end_idx} ({batch_count} files)\n"
        f"**Duration:** {batch_duration:.1f}s\n"
        f"**Errors:** {batch_errors}\n\n"
        f"## Forge/Jacqueline Hits: {batch_hits}\n"
        f"{hit_list}\n"
    )

    # Write hits file (matching existing format)
    if batch_hits > 0:
        hits_file = SUMMARIES_DIR / f"batch-{batch_num}-hits.txt"
        hits_file.write_text(f"WORKER 7 - SMOKING GUN Batch {batch_num}: {batch_hits} files\n")

    # Progress
    pct = (total_processed * 100) // ((END_BATCH - START_BATCH + 1) * BATCH_SIZE)
    pct = min(pct, 100)
    print(f"Batch {batch_num}: {batch_count} files, {batch_hits} hits, {batch_duration:.1f}s [{pct}%]")

# Write all hits file
all_hits_file.write_text("\n".join(all_hits) + "\n" if all_hits else "No hits found.\n")

print()
print("=" * 50)
print("WORKER 7 COMPLETE")
print(f"Batches: {START_BATCH} - {END_BATCH}")
print(f"Files processed: {total_processed}")
print(f"Total hits: {total_hits}")
print(f"Total errors: {total_errors}")
print(f"All hits saved to: {all_hits_file}")
print("=" * 50)
