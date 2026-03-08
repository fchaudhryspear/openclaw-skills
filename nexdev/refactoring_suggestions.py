#!/usr/bin/env python3
"""
NexDev Refactoring Suggestion Engine (Phase 2 Feature)

Analyzes code for technical debt, anti-patterns, and optimization opportunities.
Provides actionable refactoring suggestions with estimated impact.
Part of NexDev v3.0 World-Class Build Team Upgrade
"""

import re
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from enum import Enum


class ImpactLevel(Enum):
    """Impact level of suggested refactoring."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class RefactoringSuggestion:
    """Represents a single refactoring suggestion."""
    category: str  # "performance", "readability", "security", "maintainability"
    severity: str  # "info", "warning", "error"
    line_number: int
    title: str
    description: str
    current_code: str
    suggested_code: str
    impact: ImpactLevel
    effort: str  # "small", "medium", "large"
    benefit: str  # What you gain from doing it


# ──────────────────────────────────────────────────────────────────────────────
# Anti-Pattern Detection Rules
# ──────────────────────────────────────────────────────────────────────────────

ANTI_PATTERNS = {
    "long_function": {
        "pattern": r'def\s+(\w+)\s*\([^)]*\):.*?(?=\ndef\s|\Z)',
        "check": lambda code: len(code.split('\n')) > 50,
        "message": "Function is too long (>50 lines)",
        "suggestion": "Extract into smaller, focused functions",
        "impact": ImpactLevel.MEDIUM,
        "category": "maintainability"
    },
    
    "deep_nesting": {
        "pattern": r'(if|for|while|try).*:\s*\n(\s+)+.*:(?:\s*\n(\s+){4}.*:)?',
        "check": lambda code: re.findall(r'^(\s+)', code, re.MULTILINE),
        "message": "Deep nesting detected (>3 levels)",
        "suggestion": "Use early returns or extract methods",
        "impact": ImpactLevel.LOW,
        "category": "readability"
    },
    
    "magic_numbers": {
        "pattern": r'(?<![\'\"\w])(\d+(?:\.\d+)?)\b(?!([\'\"]|[\w]))',
        "check": lambda match: float(match.group(1)) not in [0, 1, 2, -1],
        "message": "Magic number should be named constant",
        "suggestion": "Extract to named constant with descriptive name",
        "impact": ImpactLevel.LOW,
        "category": "maintainability"
    },
    
    "duplicate_code": {
        "pattern": r'^(.{50,}).*?\1',  # Same 50+ chars appearing twice
        "check": lambda code: len(re.findall(pattern, code, re.DOTALL)) > 0,
        "message": "Duplicate code block detected",
        "suggestion": "Extract to shared function/module",
        "impact": ImpactLevel.HIGH,
        "category": "maintainability"
    },
    
    "god_class": {
        "pattern": r'class\s+(\w+).*?:.*?(?=\nclass\s|\Z)',
        "check": lambda class_body: class_body.count('self.') > 20,
        "message": "Class has too many responsibilities",
        "suggestion": "Apply Single Responsibility Principle",
        "impact": ImpactLevel.HIGH,
        "category": "maintainability"
    },
    
    "unused_import": {
        "pattern": r'^import\s+(\w+)|^from\s+\w+\s+import\s+(\w+)',
        "check": lambda match, code: match.group(1) or match.group(2) not in code,
        "message": "Import not used in file",
        "suggestion": "Remove unused import",
        "impact": ImpactLevel.LOW,
        "category": "cleanliness"
    },
    
    "print_statement": {
        "pattern": r'print\s*\(',
        "message": "Debug print statement found",
        "suggestion": "Replace with logging module",
        "impact": ImpactLevel.LOW,
        "category": "maintainability"
    },
    
    "bare_except": {
        "pattern": r'except\s*:.*',
        "message": "Bare except catches all exceptions",
        "suggestion": "Specify exception type: except ExceptionType:",
        "impact": ImpactLevel.HIGH,
        "category": "security"
    },
    
    "hardcoded_password": {
        "pattern": r'(password|passwd|pwd)\s*=\s*["\'][^"\']+["\']',
        "message": "Hardcoded password detected",
        "suggestion": "Use environment variable or secret manager",
        "impact": ImpactLevel.CRITICAL,
        "category": "security"
    },
    
    "sql_injection_risk": {
        "pattern": r'execute\s*\(\s*f["\'].*\{.*\}',
        "message": "Potential SQL injection vulnerability",
        "suggestion": "Use parameterized queries",
        "impact": ImpactLevel.CRITICAL,
        "category": "security"
    },
    
    "inefficient_string_concat": {
        "pattern": r'\+=\s*[\'"][^\']*["\']',
        "context": "loop",
        "message": "String concatenation in loop",
        "suggestion": "Use ''.join() for better performance",
        "impact": ImpactLevel.MEDIUM,
        "category": "performance"
    },
    
    "list_concatenation": {
        "pattern": r'\[\s*\.\.\.\s*\]\s*\+\s*\[',
        "message": "Repeated list concatenation",
        "suggestion": "Use list.extend() or list comprehension",
        "impact": ImpactLevel.MEDIUM,
        "category": "performance"
    },
    
    "missing_docstring": {
        "pattern": r'(def|class)\s+(\w+).*?:\s*\n\s*(?![\'\"])',
        "message": "Missing docstring",
        "suggestion": "Add Google/NumPy-style docstring",
        "impact": ImpactLevel.LOW,
        "category": "readability"
    }
}


# ──────────────────────────────────────────────────────────────────────────────
# Analysis Functions
# ──────────────────────────────────────────────────────────────────────────────

def detect_long_functions(code: str) -> List[RefactoringSuggestion]:
    """Detect functions that are too long."""
    suggestions = []
    
    func_pattern = r'def\s+(\w+)\s*\(([^)]*)\)\s*:'
    matches = re.finditer(func_pattern, code)
    
    for match in matches:
        func_name = match.group(1)
        func_start = match.start()
        
        # Find function body
        next_def = re.search(r'\ndef\s+', code[func_start + 1:])
        if next_def:
            func_end = func_start + 1 + next_def.start()
        else:
            func_end = len(code)
        
        func_body = code[func_start:func_end]
        lines = func_body.split('\n')
        
        if len(lines) > 50:
            suggestions.append(RefactoringSuggestion(
                category="maintainability",
                severity="warning",
                line_number=code[:func_start].count('\n') + 1,
                title=f"Long function: {func_name}",
                description=f"Function has {len(lines)} lines (threshold: 50)",
                current_code=func_body[:200] + "...",
                suggested_code="# Extract into smaller helper functions",
                impact=ImpactLevel.MEDIUM,
                effort="medium",
                benefit="Improved readability and testability"
            ))
    
    return suggestions


def detect_deep_nesting(code: str) -> List[RefactoringSuggestion]:
    """Detect deeply nested code blocks."""
    suggestions = []
    
    # Count indentation levels
    lines = code.split('\n')
    max_indent = 0
    max_indent_line = 0
    
    for i, line in enumerate(lines):
        stripped = line.lstrip()
        if stripped and not stripped.startswith('#'):
            indent = len(line) - len(stripped)
            indent_level = indent // 4  # Assume 4-space tabs
            if indent_level > max_indent:
                max_indent = indent_level
                max_indent_line = i + 1
    
    if max_indent > 4:  # More than 4 levels deep
        suggestions.append(RefactoringSuggestion(
            category="readability",
            severity="info",
            line_number=max_indent_line,
            title="Deep nesting detected",
            description=f"Nesting depth: {max_indent} levels (recommended: max 3-4)",
            current_code=lines[max_indent_line - 1].strip(),
            suggested_code="Use early returns or guard clauses",
            impact=ImpactLevel.LOW,
            effort="small",
            benefit="Improved code readability"
        ))
    
    return suggestions


def detect_magic_numbers(code: str) -> List[RefactoringSuggestion]:
    """Detect magic numbers that should be constants."""
    suggestions = []
    
    pattern = r'(?<![\'\"a-zA-Z_])(\d+(?:\.\d+)?)\b(?!([\'\"]|[a-zA-Z_]))'
    matches = re.finditer(pattern, code)
    
    common_constants = [0, 1, 2, -1, 100, 1000, 0.5, 0.1, 3600, 86400, 60]
    
    for match in matches:
        try:
            value = float(match.group(1))
            if value not in common_constants and abs(value) > 0:
                line_num = code[:match.start()].count('\n') + 1
                suggestions.append(RefactoringSuggestion(
                    category="maintainability",
                    severity="info",
                    line_number=line_num,
                    title=f"Magic number: {value}",
                    description="Literal number without semantic meaning",
                    current_code=match.group(0),
                    suggested_code=f"# Extract to CONSTANT_NAME = {value}",
                    impact=ImpactLevel.LOW,
                    effort="small",
                    benefit="Better maintainability and self-documentation"
                ))
        except ValueError:
            pass
    
    return suggestions


def detect_hardcoded_secrets(code: str) -> List[RefactoringSuggestion]:
    """Detect hardcoded passwords, API keys, secrets."""
    suggestions = []
    
    secret_patterns = [
        (r'(?:password|passwd|pwd|pass)\s*=\s*["\']([^"\']+)["\']', 'Password'),
        (r'(?:api[_-]?key|apikey)\s*=\s*["\']([^"\']+)["\']', 'API key'),
        (r'(?:secret[_-]?key|secretkey)\s*=\s*["\']([^"\']+)["\']', 'Secret key'),
        (r'(?:token|auth[_-]?token)\s*=\s*["\']([^"\']+)["\']', 'Token'),
        (r'(?:aws[_-]?access[_-]?key|AWS_ACCESS_KEY)\s*=\s*["\']([^"\']+)["\']', 'AWS Key')
    ]
    
    for pattern, secret_type in secret_patterns:
        matches = re.finditer(pattern, code, re.IGNORECASE)
        for match in matches:
            line_num = code[:match.start()].count('\n') + 1
            suggestions.append(RefactoringSuggestion(
                category="security",
                severity="error",
                line_number=line_num,
                title=f"Hardcoded {secret_type}",
                description=f"{secret_type} should never be hardcoded",
                current_code=match.group(0)[:80] + "...",
                suggested_code=f"# Use: os.environ.get('{secret_type.upper()}')",
                impact=ImpactLevel.CRITICAL,
                effort="small",
                benefit="Security compliance and safe credential rotation"
            ))
    
    return suggestions


def detect_performance_issues(code: str) -> List[RefactoringSuggestion]:
    """Detect common performance anti-patterns."""
    suggestions = []
    
    # Check for string concatenation in loops
    if re.search(r'for\s+.*:.*\+=.*["\']', code, re.DOTALL):
        line_num = code.find('+=').count('\n') + 1 if '+=' in code else 0
        suggestions.append(RefactoringSuggestion(
            category="performance",
            severity="warning",
            line_number=line_num,
            title="String concatenation in loop",
            description="Using += for string building in loop",
            current_code="# Look for: string += 'text' inside for loop",
            suggested_code="# Use: ''.join([...]) instead",
            impact=ImpactLevel.MEDIUM,
            effort="small",
            benefit="O(n²) → O(n) time complexity"
        ))
    
    # Check for inefficient list operations
    if re.search(r'for\s+.*in\s+range\(len\(.*\)\):', code):
        suggestions.append(RefactoringSuggestion(
            category="performance",
            severity="info",
            line_number=0,
            title="Inefficient iteration",
            description="Using range(len()) instead of enumerate()",
            current_code="for i in range(len(items)):",
            suggested_code="for i, item in enumerate(items):",
            impact=ImpactLevel.LOW,
            effort="small",
            benefit="Cleaner, more Pythonic code"
        ))
    
    # Check for repeated database/API calls in loops
    if re.search(r'for\s+.*:.*(?:\.query\(|requests\.)', code, re.DOTALL):
        suggestions.append(RefactoringSuggestion(
            category="performance",
            severity="warning",
            line_number=0,
            title="Database/API call in loop",
            description="Multiple sequential calls in loop",
            current_code="# Database/API call inside for loop",
            suggested_code="# Batch the calls or use bulk operations",
            impact=ImpactLevel.HIGH,
            effort="medium",
            benefit="Reduce N+1 query problem"
        ))
    
    return suggestions


def analyze_file_for_refactoring(filepath: str) -> Dict[str, Any]:
    """
    Comprehensive refactoring analysis for a file.
    
    Args:
        filepath: Path to source file
        
    Returns:
        Dictionary with analysis results
    """
    file_path = Path(filepath)
    
    if not file_path.exists():
        return {"success": False, "error": f"File not found: {filepath}"}
    
    code = file_path.read_text()
    language = "python" if file_path.suffix == ".py" else "unknown"
    
    if language != "python":
        return {"success": False, "message": "Only Python files supported currently"}
    
    # Run all detectors
    all_suggestions = []
    
    all_suggestions.extend(detect_long_functions(code))
    all_suggestions.extend(detect_deep_nesting(code))
    all_suggestions.extend(detect_magic_numbers(code))
    all_suggestions.extend(detect_hardcoded_secrets(code))
    all_suggestions.extend(detect_performance_issues(code))
    
    # Sort by severity
    severity_order = {"critical": 0, "error": 1, "warning": 2, "info": 3}
    all_suggestions.sort(key=lambda x: severity_order.get(x.severity, 4))
    
    # Calculate summary
    critical_count = sum(1 for s in all_suggestions if s.severity == "critical")
    error_count = sum(1 for s in all_suggestions if s.severity == "error")
    warning_count = sum(1 for s in all_suggestions if s.severity == "warning")
    info_count = sum(1 for s in all_suggestions if s.severity == "info")
    
    can_merge = critical_count == 0 and error_count == 0
    
    return {
        "success": True,
        "filepath": str(file_path),
        "language": language,
        "lines_analyzed": len(code.split('\n')),
        "summary": {
            "total_issues": len(all_suggestions),
            "critical": critical_count,
            "errors": error_count,
            "warnings": warning_count,
            "info": info_count
        },
        "can_merge": can_merge,
        "suggestions": [
            {
                "category": s.category,
                "severity": s.severity,
                "line": s.line_number,
                "title": s.title,
                "description": s.description,
                "current_code": s.current_code,
                "suggested_code": s.suggested_code,
                "impact": s.impact.value,
                "effort": s.effort,
                "benefit": s.benefit
            }
            for s in all_suggestions
        ],
        "tech_debt_score": _calculate_tech_debt_score(all_suggestions)
    }


def _calculate_tech_debt_score(suggestions: List[RefactoringSuggestion]) -> float:
    """Calculate tech debt score based on issues found (lower is better)."""
    weights = {
        "critical": 100,
        "error": 50,
        "warning": 20,
        "info": 5
    }
    
    total = sum(weights.get(s.severity, 0) for s in suggestions)
    
    # Normalize to 0-100 scale
    return min(total / 10, 100.0)


def generate_refactoring_plan(analysis_result: Dict[str, Any]) -> str:
    """Generate prioritized refactoring plan from analysis results."""
    
    lines = [
        "=" * 70,
        "REFACTORING PLAN",
        "=" * 70,
        "",
        f"File: {analysis_result.get('filepath', 'Unknown')}",
        f"Tech Debt Score: {analysis_result.get('tech_debt_score', 0):.1f}/100",
        "",
        "SUMMARY",
        "-" * 70
    ]
    
    summary = analysis_result.get("summary", {})
    lines.append(f"Total Issues:     {summary.get('total_issues', 0)}")
    lines.append(f"Critical:         {summary.get('critical', 0)} 🔴")
    lines.append(f"Errors:           {summary.get('errors', 0)} 🟠")
    lines.append(f"Warnings:         {summary.get('warnings', 0)} 🟡")
    lines.append(f"Info:             {summary.get('info', 0)} 🔵")
    lines.append(f"Can Merge:        {'Yes ✅' if analysis_result.get('can_merge') else 'NO ❌'}")
    
    suggestions = analysis_result.get("suggestions", [])
    
    # Security issues first
    security_issues = [s for s in suggestions if s['category'] == 'security']
    if security_issues:
        lines.extend([
            "",
            "🔒 SECURITY ISSUES (Fix Immediately)",
            "-" * 70
        ])
        for issue in security_issues:
            lines.extend([
                f"\nLine {issue['line']}: {issue['title']}",
                f"   Issue: {issue['description']}",
                f"   Fix: {issue['suggested_code']}",
                f"   Benefit: {issue['benefit']}"
            ])
    
    # Performance issues
    perf_issues = [s for s in suggestions if s['category'] == 'performance']
    if perf_issues:
        lines.extend([
            "",
            "⚡ PERFORMANCE ISSUES (High Priority)",
            "-" * 70
        ])
        for issue in perf_issues:
            lines.extend([
                f"\nLine {issue['line']}: {issue['title']}",
                f"   Issue: {issue['description']}",
                f"   Effort: {issue['effort']} | Impact: {issue['impact']}",
                f"   Benefit: {issue['benefit']}"
            ])
    
    # Maintainability issues
    maint_issues = [s for s in suggestions if s['category'] == 'maintainability']
    if maint_issues:
        lines.extend([
            "",
            "🧹 MAINTAINABILITY ISSUES",
            "-" * 70
        ])
        for issue in maint_issues[:10]:  # Show first 10
            lines.extend([
                f"\nLine {issue['line']}: {issue['title']}",
                f"   Issue: {issue['description']}",
                f"   Effort: {issue['effort']}"
            ])
    
    lines.extend([
        "",
        "=" * 70,
        "PRIORITY ORDER",
        "-" * 70,
        "1. Fix all security issues immediately",
        "2. Address performance bottlenecks",
        "3. Tackle maintainability issues incrementally",
        "4. Consider technical debt in sprint planning",
        "",
        "=" * 70
    ])
    
    return "\n".join(lines)


if __name__ == "__main__":
    # Demo mode
    print("=" * 60)
    print("♻️  REFACTORING ANALYSIS - DEMO")
    print("=" * 60)
    
    # Sample problematic code
    sample_code = '''
def process_data(data, api_key="sk-secret123", timeout=30):
    result = ""
    
    for item in data:
        result += str(item) + ", "
        
        if item > 100:
            if item > 500:
                if item > 1000:
                    print("Large item!")
                    response = requests.get(f"http://api.com?id={item}")
    
    try:
        execute(f"DELETE FROM logs WHERE id = {user_id}")
    except:
        pass
    
    return result

PASSWORD = "admin123"
MAX_SIZE = 1000
'''
    
    # Save to temp file
    from tempfile import NamedTemporaryFile
    with NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write(sample_code)
        temp_path = f.name
    
    print("\nSample Code:")
    print("-" * 60)
    print(sample_code)
    
    print("\nRunning analysis...")
    result = analyze_file_for_refactoring(temp_path)
    
    print("\nAnalysis Results:")
    print("-" * 60)
    print(f"Summary: {result['summary']}")
    print(f"Tech Debt Score: {result['tech_debt_score']:.1f}/100")
    print(f"Can Merge: {'Yes' if result['can_merge'] else 'NO'}")
    
    # Print report
    report = generate_refactoring_plan(result)
    print(report)
    
    print("\n" + "=" * 60)
    print("Demo complete!")
