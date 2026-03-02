#!/usr/bin/env python3
"""Pre-commit/pre-push secret scanner."""
import re, sys, os

PATTERNS = [
    (r'sk-ant-api03-[A-Za-z0-9_\-]{80,}', 'Anthropic API key'),
    (r'sk-proj-[A-Za-z0-9_\-]{80,}', 'OpenAI project key'),
    (r'xai-[A-Za-z0-9]{60,}', 'XAI/Grok key'),
    (r'AIzaSy[A-Za-z0-9_\-]{33}', 'Google API key'),
    (r'BSAU_[A-Za-z0-9_\-]{20,}', 'Brave Search key'),
    (r'BSAfY[A-Za-z0-9_\-]{20,}', 'Brave Search key'),
    # Generic sk- only if long enough to be real (>40 chars, not abc/test patterns)
    (r'sk-(?!abc|test|fake|example|dummy)[A-Za-z0-9_\-]{45,}', 'Generic API key'),
]

SKIP_DIRS = {'.git', 'node_modules', 'dist', '__pycache__', '.venv'}
SKIP_EXTS = {'.png', '.jpg', '.jpeg', '.gif', '.webp', '.ico', '.zip', '.tar', '.gz'}
# Test files use fake keys intentionally
SKIP_PATHS = {'tests/', 'test/', 'examples/', 'SENSITIVE_DATA.md', 'examples.ts'}

def scan_file(path):
    findings = []
    # Skip test/example files
    if any(s in path for s in SKIP_PATHS):
        return findings
    try:
        with open(path, 'r', encoding='utf-8', errors='ignore') as f:
            for i, line in enumerate(f, 1):
                for pattern, label in PATTERNS:
                    if re.search(pattern, line):
                        findings.append((path, i, label))
    except Exception:
        pass
    return findings

def scan_all():
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    findings = []
    for dirpath, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for f in files:
            if any(f.endswith(e) for e in SKIP_EXTS):
                continue
            findings.extend(scan_file(os.path.join(dirpath, f)))
    return findings

if __name__ == '__main__':
    findings = scan_all()
    if findings:
        print("🚨 SECRET LEAK DETECTED — aborting push!")
        for path, line, label in findings:
            print(f"  {label} at {path}:{line}")
        sys.exit(1)
    else:
        print("✅ No secrets found.")
        sys.exit(0)
