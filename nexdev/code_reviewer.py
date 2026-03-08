#!/usr/bin/env python3
"""
NexDev Code Review Bot (Tier 1 Feature)

Pre-submit code quality checks: linting, security scan, style verification,
best practices analysis. Provides actionable feedback before PR merge.
Part of NexDev v3.0 World-Class Build Team Upgrade
"""

import re
import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from datetime import datetime

# ──────────────────────────────────────────────────────────────────────────────
# Quality Check Categories
# ──────────────────────────────────────────────────────────────────────────────

@dataclass
class ReviewIssue:
    """Represents a single review finding."""
    category: str  # "security", "style", "performance", "best_practice"
    severity: str  # "critical", "warning", "info"
    line: int
    message: str
    suggestion: str
    rule_id: str


# Security patterns to detect
SECURITY_PATTERNS = {
    "hardcoded_secret": {
        "pattern": r'(password|secret|api_key|token|passwd)\s*=\s*["\'][^"\']+["\']',
        "severity": "critical",
        "message": "Hardcoded secret detected",
        "rule_id": "SEC001"
    },
    "sql_injection_risk": {
        "pattern": r'execute\s*\(\s*f["\'].*\{',
        "severity": "critical",
        "message": "Potential SQL injection vulnerability - use parameterized queries",
        "rule_id": "SEC002"
    },
    "insecure_random": {
        "pattern": r'random\.random\(|Math\.random\(\)',
        "severity": "warning",
        "message": "Use cryptographically secure random for security-sensitive operations",
        "rule_id": "SEC003"
    },
    "eval_usage": {
        "pattern": r'\beval\s*\(|exec\s*\(',
        "severity": "warning",
        "message": "Avoid eval/exec - potential code injection risk",
        "rule_id": "SEC004"
    }
}

# Style patterns (Python-focused example)
STYLE_PATTERNS = {
    "long_line": {
        "max_length": 120,
        "severity": "info",
        "message": "Line exceeds recommended length (120 chars)",
        "rule_id": "STY001"
    },
    "missing_docstring": {
        "pattern": r'def\s+\w+.*:\s*$|class\s+\w+.*:\s*$',
        "severity": "warning",
        "message": "Missing docstring for function/class",
        "rule_id": "STY002"
    },
    "unused_import": {
        "pattern": r'^import\s+(\w+)\s*$|^from\s+\w+\s+import\s+(\w+)',
        "severity": "warning",
        "message": "Check if import is used in file",
        "rule_id": "STY003"
    },
    "magic_number": {
        "pattern": r'(?<![\'"])(?<!\w)(\d+(?:\.\d+)?)\b(?!([\'"]|\w))',
        "min_value": 2,
        "severity": "info",
        "message": "Consider extracting magic number to named constant",
        "rule_id": "STY004"
    }
}

# Performance anti-patterns
PERFORMANCE_PATTERNS = {
    "list_concatenation": {
        "pattern": r'\+\s*[\[\]]',
        "severity": "warning",
        "message": "Use list.extend() or list comprehension instead of repeated concatenation",
        "rule_id": "PERF001"
    },
    "string_concat_loop": {
        "pattern": r'\+=\s*[\'"][^\']*["\']',
        "severity": "warning",
        "message": "Use ''.join() for string building in loops",
        "rule_id": "PERF002"
    },
    "unnecessary_list_conversion": {
        "pattern": r'list\(map\(|list\(filter\(',
        "severity": "info",
        "message": "Consider using generator expression for better memory efficiency",
        "rule_id": "PERF003"
    }
}


# ──────────────────────────────────────────────────────────────────────────────
# Main Review Functions
# ──────────────────────────────────────────────────────────────────────────────

def analyze_security(code: str, lines: List[str]) -> List[ReviewIssue]:
    """Run security pattern analysis on code."""
    issues = []
    
    for pattern_name, config in SECURITY_PATTERNS.items():
        pattern = config.get('pattern', '')
        
        try:
            for match in re.finditer(pattern, code, re.MULTILINE | re.IGNORECASE):
                # Find line number
                line_num = code[:match.start()].count('\n') + 1
                
                issues.append(ReviewIssue(
                    category="security",
                    severity=config['severity'],
                    line=line_num,
                    message=config['message'],
                    suggestion=f"Rule: {config['rule_id']}",
                    rule_id=config['rule_id']
                ))
        except re.error:
            pass
    
    return issues


def analyze_style(code: str, lines: List[str], language: str = "python") -> List[ReviewIssue]:
    """Run style analysis on code."""
    issues = []
    
    if language == "python":
        # Check line lengths
        for i, line in enumerate(lines, 1):
            if len(line.rstrip()) > STYLE_PATTERNS['long_line']['max_length']:
                issues.append(ReviewIssue(
                    category="style",
                    severity=STYLE_PATTERNS['long_line']['severity'],
                    line=i,
                    message=f"Line has {len(line.rstrip())} characters (max 120)",
                    suggestion=STYLE_PATTERNS['long_line']['message'],
                    rule_id=STYLE_PATTERNS['long_line']['rule_id']
                ))
        
        # Check for missing docstrings
        for i, line in enumerate(lines[:-1], 1):
            if re.match(r'def\s+\w+\s*\([^)]*\)\s*(->\s*\w+)?:\s*$', line.strip()):
                # Check if next line has docstring
                next_line = lines[i].strip() if i < len(lines) else ""
                if not (next_line.startswith('"""') or next_line.startswith("'''") or next_line.startswith('#')):
                    issues.append(ReviewIssue(
                        category="style",
                        severity="warning",
                        line=i,
                        message="Function definition missing docstring",
                        suggestion="Add docstring describing parameters, return value, and purpose",
                        rule_id=STYLE_PATTERNS['missing_docstring']['rule_id']
                    ))
    
    return issues


def analyze_best_practices(code: str, language: str = "python") -> List[ReviewIssue]:
    """Run best practices analysis."""
    issues = []
    
    if language == "python":
        # Check for bare except clauses
        if re.search(r'except\s*:.', code, re.MULTILINE):
            issues.append(ReviewIssue(
                category="best_practice",
                severity="warning",
                line=0,
                message="Bare except clause found",
                suggestion="Specify exception type: except ExceptionType:",
                rule_id="BP001"
            ))
        
        # Check for print statements (debugging artifacts)
        if re.search(r'print\s*\(', code):
            issues.append(ReviewIssue(
                category="best_practice",
                severity="info",
                line=0,
                message="Print statement detected",
                suggestion="Consider using logging module instead",
                rule_id="BP002"
            ))
        
        # Check for TODO/FIXME comments
        todo_pattern = r'#\s*(TODO|FIXME|XXX|HACK):?\s*(.*)'
        todos = re.findall(todo_pattern, code, re.IGNORECASE)
        for _, todo_text in todos:
            issues.append(ReviewIssue(
                category="best_practice",
                severity="info",
                line=0,
                message=f"Todo comment: {todo_text}",
                suggestion="Create issue tracker ticket for follow-up",
                rule_id="BP003"
            ))
    
    return issues


def run_code_review(code: str, filepath: Optional[str] = None,
                   language: Optional[str] = None) -> Dict[str, Any]:
    """
    Run comprehensive code review on provided code.
    
    Args:
        code: Source code to review
        filepath: Optional file path for context
        language: Programming language (auto-detected if not provided)
        
    Returns:
        Dictionary with review findings and recommendations
    """
    lines = code.split('\n')
    
    # Detect language if not specified
    if language:
        lang = language
    elif filepath:
        ext = Path(filepath).suffix.lower()
        lang_map = {'.py': 'python', '.js': 'javascript', '.ts': 'typescript'}
        lang = lang_map.get(ext, 'python')
    else:
        lang = 'python'
    
    # Run all analyses
    security_issues = analyze_security(code, lines)
    style_issues = analyze_style(code, lines, lang)
    best_practice_issues = analyze_best_practices(code, lang)
    
    # Combine all issues
    all_issues = security_issues + style_issues + best_practice_issues
    
    # Sort by severity
    severity_order = {"critical": 0, "warning": 1, "info": 2}
    all_issues.sort(key=lambda x: (severity_order.get(x.severity, 3), x.line))
    
    # Calculate summary statistics
    critical_count = sum(1 for i in all_issues if i.severity == "critical")
    warning_count = sum(1 for i in all_issues if i.severity == "warning")
    info_count = sum(1 for i in all_issues if i.severity == "info")
    
    # Generate summary text
    summary_parts = []
    if critical_count > 0:
        summary_parts.append(f"❌ {critical_count} critical issue(s)")
    if warning_count > 0:
        summary_parts.append(f"⚠️  {warning_count} warning(s)")
    if info_count > 0:
        summary_parts.append(f"ℹ️  {info_count} info message(s)")
    
    summary = " | ".join(summary_parts) if summary_parts else "✅ No issues found"
    
    # Convert issues to serializable format
    issues_json = [
        {
            "category": issue.category,
            "severity": issue.severity,
            "line": issue.line,
            "message": issue.message,
            "suggestion": issue.suggestion,
            "rule_id": issue.rule_id
        }
        for issue in all_issues
    ]
    
    return {
        "success": True,
        "filepath": filepath or "<inline>",
        "language": lang,
        "lines_analyzed": len(lines),
        "summary": summary,
        "issue_counts": {
            "critical": critical_count,
            "warning": warning_count,
            "info": info_count,
            "total": len(all_issues)
        },
        "issues": issues_json,
        "can_merge": critical_count == 0,
        "timestamp": datetime.now().isoformat()
    }


def review_file(filepath: str) -> Dict[str, Any]:
    """
    Review an entire file.
    
    Args:
        filepath: Path to file to review
        
    Returns:
        Review results
    """
    file_path = Path(filepath)
    
    if not file_path.exists():
        return {
            "success": False,
            "error": f"File not found: {filepath}"
        }
    
    code = file_path.read_text()
    
    return run_code_review(code, filepath=str(file_path))


def review_directory(directory: str, extensions: List[str] = None) -> Dict[str, Any]:
    """
    Recursively review all source files in directory.
    
    Args:
        directory: Root directory
        extensions: File extensions to include (default: .py, .js, .ts)
        
    Returns:
        Summary of all reviews
    """
    dir_path = Path(directory)
    
    if not dir_path.is_dir():
        return {
            "success": False,
            "error": f"Not a directory: {directory}"
        }
    
    if extensions is None:
        extensions = ['.py', '.js', '.ts', '.java', '.go', '.rb']
    
    results = []
    total_issues = 0
    total_critical = 0
    total_warnings = 0
    
    # Pattern to skip common directories
    skip_dirs = {'node_modules', '__pycache__', '.git', 'venv', '.venv', 'build', 'dist'}
    
    for file_path in dir_path.rglob('*'):
        if file_path.is_file() and file_path.suffix in extensions:
            # Skip common build/cache directories
            if any(part in skip_dirs for part in file_path.parts):
                continue
            
            result = review_file(str(file_path))
            
            if result.get('success'):
                results.append({
                    "file": str(file_path.relative_to(dir_path)),
                    "summary": result.get('summary'),
                    "can_merge": result.get('can_merge'),
                    "issue_count": result.get('issue_counts', {}).get('total', 0)
                })
                
                total_issues += result.get('issue_counts', {}).get('total', 0)
                total_critical += result.get('issue_counts', {}).get('critical', 0)
                total_warnings += result.get('issue_counts', {}).get('warning', 0)
    
    return {
        "success": True,
        "directory": str(dir_path),
        "files_reviewed": len(results),
        "summary": {
            "total_files": len(results),
            "total_issues": total_issues,
            "critical": total_critical,
            "warnings": total_warnings
        },
        "results": results
    }


if __name__ == "__main__":
    # Demo mode
    print("=" * 60)
    print("🔍 NEXDEV CODE REVIEW BOT - DEMO")
    print("=" * 60)
    
    # Sample code with intentional issues
    sample_code = '''
import random
import os

PASSWORD = "secret123"

def calculate_total(items):
    total = 0
    for item in items:
        total += item.price * item.quantity
    
    return total

def process_data(data):
    try:
        result = eval(data)  # Dangerous!
    except:
        pass
    
    print("Processing complete")
    
    sql = f"SELECT * FROM users WHERE id = {user_id}"
    # TODO: Fix this query
    
    return result
'''
    
    print("\nSample Code:")
    print("-" * 60)
    for i, line in enumerate(sample_code.split('\n'), 1):
        print(f"{i:3}: {line}")
    
    print("\nRunning code review...")
    
    result = run_code_review(sample_code, language="python")
    
    print("\nReview Results:")
    print("-" * 60)
    print(f"Summary: {result['summary']}")
    print(f"Lines analyzed: {result['lines_analyzed']}")
    print(f"Can merge: {'Yes' if result['can_merge'] else 'NO - CRITICAL ISSUES FOUND'}")
    
    print("\nIssues Found:")
    for issue in result['issues'][:10]:  # Show first 10
        severity_icon = {
            "critical": "🔴",
            "warning": "🟡",
            "info": "🔵"
        }.get(issue['severity'], "⚪")
        
        print(f"\n{severity_icon} Line {issue['line'] or '-'} [{issue['severity'].upper()}]")
        print(f"   Category: {issue['category']}")
        print(f"   Issue: {issue['message']}")
        print(f"   Rule: {issue['rule_id']}")
        print(f"   Suggestion: {issue['suggestion']}")
    
    if result['issues']:
        print(f"\n{'=' * 60}")
        print(f"Total: {result['issue_counts']['total']} issues")
        print(f"Critical: {result['issue_counts']['critical']} | Warnings: {result['issue_counts']['warning']} | Info: {result['issue_counts']['info']}")
    
    print("\n" + "=" * 60)
    print("Demo complete!")
