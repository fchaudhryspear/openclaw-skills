#!/usr/bin/env python3
"""
Optimus Secret Scanner — Pre-commit / Pre-push / Manual
Usage:
  python3 pre_commit_scanner.py           # scan all
  python3 pre_commit_scanner.py staged    # scan git staged files only
  python3 pre_commit_scanner.py all       # scan entire workspace
  python3 pre_commit_scanner.py <path>    # scan specific file or directory
"""
import re, sys, os, subprocess

# ── Secret patterns ──────────────────────────────────────────────────────────
PATTERNS = [
    (r'sk-ant-api03-[A-Za-z0-9_\-]{80,}',          'Anthropic API key'),
    (r'sk-proj-[A-Za-z0-9_\-]{80,}',               'OpenAI project key'),
    (r'xai-[A-Za-z0-9]{60,}',                       'XAI/Grok key'),
    (r'AIzaSy[A-Za-z0-9_\-]{33}',                   'Google API key'),
    (r'BSAU_[A-Za-z0-9_\-]{20,}',                   'Brave Search key'),
    (r'BSAfY[A-Za-z0-9_\-]{20,}',                   'Brave Search key'),
    (r'AKIA[A-Z0-9]{16}',                            'AWS Access Key ID'),
    (r'(?i)aws.{0,20}secret.{0,20}[A-Za-z0-9/+=]{40}', 'AWS Secret Key'),
    (r'ghp_[A-Za-z0-9]{36}',                        'GitHub Personal Token'),
    (r'gho_[A-Za-z0-9]{36}',                        'GitHub OAuth Token'),
    (r'xoxb-[A-Za-z0-9\-]{50,}',                    'Slack Bot Token'),
    (r'xoxp-[A-Za-z0-9\-]{50,}',                    'Slack User Token'),
    (r'sk-[A-Za-z0-9]{93}',                          'Moonshot/Kimi key'),
    # Generic sk- long enough to be real, not test/dummy values
    (r'sk-(?!abc|test|fake|example|dummy|hyTB|3PKh)[A-Za-z0-9_\-]{45,}', 'Generic API key'),
]

# ── Skip rules ────────────────────────────────────────────────────────────────
SKIP_DIRS  = {'.git', 'node_modules', 'dist', '__pycache__', '.venv', '.aws-sam', 'coverage'}
SKIP_EXTS  = {'.png', '.jpg', '.jpeg', '.gif', '.webp', '.ico',
              '.zip', '.tar', '.gz', '.bin', '.exe', '.pdf', '.lock'}
# Files that intentionally contain fake/dummy keys for testing
SKIP_PATHS = {
    'tests/', 'test/', '/examples/', 'SENSITIVE_DATA.md',
    'examples.ts', 'scanner.test', 'integration.test',
    'reference-based-demo', 'lifecycle.test'
}

def should_skip(path):
    return any(s in path for s in SKIP_PATHS)

def scan_file(path):
    if should_skip(path):
        return []
    findings = []
    try:
        with open(path, 'r', encoding='utf-8', errors='ignore') as f:
            for i, line in enumerate(f, 1):
                for pattern, label in PATTERNS:
                    if re.search(pattern, line):
                        findings.append((path, i, label, line.strip()[:80]))
    except Exception:
        pass
    return findings

def scan_staged():
    """Scan only git-staged files."""
    try:
        result = subprocess.run(
            ['git', 'diff', '--cached', '--name-only', '--diff-filter=ACM'],
            capture_output=True, text=True
        )
        files = [f.strip() for f in result.stdout.splitlines() if f.strip()]
    except Exception:
        return []

    root = subprocess.run(['git', 'rev-parse', '--show-toplevel'],
                          capture_output=True, text=True).stdout.strip()
    findings = []
    for f in files:
        ext = os.path.splitext(f)[1].lower()
        if ext in SKIP_EXTS:
            continue
        full = os.path.join(root, f)
        if os.path.isfile(full):
            findings.extend(scan_file(full))
    return findings

def scan_dir(root):
    """Scan entire directory tree."""
    findings = []
    for dirpath, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for f in files:
            ext = os.path.splitext(f)[1].lower()
            if ext in SKIP_EXTS:
                continue
            findings.extend(scan_file(os.path.join(dirpath, f)))
    return findings

def report(findings):
    if findings:
        print("🚨 SECRET LEAK DETECTED\n")
        for path, line, label, snippet in findings:
            print(f"  [{label}]")
            print(f"    File : {path}:{line}")
            print(f"    Line : {snippet[:60]}...")
            print()
        print(f"Total: {len(findings)} secret(s) found. Fix before proceeding.")
        return False
    else:
        print("✅ No secrets found.")
        return True

if __name__ == '__main__':
    mode = sys.argv[1] if len(sys.argv) > 1 else 'all'

    if mode == 'staged':
        findings = scan_staged()
    elif os.path.isfile(mode):
        findings = scan_file(mode)
    elif os.path.isdir(mode):
        findings = scan_dir(mode)
    else:
        # Default: scan workspace root
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        findings = scan_dir(root)

    sys.exit(0 if report(findings) else 1)
