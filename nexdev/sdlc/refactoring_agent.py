#!/usr/bin/env python3
"""
NexDev Phase 3.5 — Automated Code Refactoring & Modernization
===============================================================
Analyzes codebase for tech debt, outdated patterns, and refactoring opportunities.
"""

import re
from typing import Dict, List
from dataclasses import dataclass


@dataclass
class RefactoringOpportunity:
    id: str
    category: str  # complexity, duplication, naming, modernization, dead_code
    severity: str  # high, medium, low
    title: str
    description: str
    location: str
    suggestion: str
    estimated_effort: str  # minutes


class RefactoringAgent:
    """Automated code analysis and refactoring suggestions."""
    
    PATTERNS = {
        "long_function": {
            "check": lambda code: [(m.start(), m.group(1)) for m in re.finditer(
                r'def\s+(\w+)\s*\([^)]*\):', code) 
                if len(code[m.start():code.find('\ndef ', m.start()+1) 
                if code.find('\ndef ', m.start()+1) > 0 else len(code)].split('\n')) > 50],
            "category": "complexity",
            "severity": "medium",
            "title": "Long function (>50 lines)",
            "suggestion": "Break into smaller, focused functions following Single Responsibility Principle",
            "effort": "30 min",
        },
        "god_class": {
            "pattern": r"class\s+\w+[^:]*:(?:.*\n){100,}",
            "category": "complexity",
            "severity": "high",
            "title": "God class (>100 lines)",
            "suggestion": "Split into multiple focused classes using composition",
            "effort": "2 hours",
        },
        "magic_numbers": {
            "pattern": r"(?<![\w.])(?:(?<!=\s)|(?<=\(\s))(?:0\.\d+|\d{2,})(?![\w.])",
            "category": "naming",
            "severity": "low",
            "title": "Magic number",
            "suggestion": "Extract to named constant for readability",
            "effort": "5 min",
        },
        "bare_except": {
            "pattern": r"except\s*:",
            "category": "modernization",
            "severity": "medium",
            "title": "Bare except clause",
            "suggestion": "Catch specific exceptions (Exception at minimum, prefer more specific)",
            "effort": "5 min",
        },
        "print_debug": {
            "pattern": r"(?:print|console\.log)\s*\(.*(?:debug|test|TODO|FIXME|hack)",
            "category": "dead_code",
            "severity": "low",
            "title": "Debug print statement",
            "suggestion": "Remove debug prints, use proper logging framework",
            "effort": "2 min",
        },
        "deprecated_format": {
            "pattern": r"['\"].*%[sd].*['\"].*%\s*\(",
            "category": "modernization",
            "severity": "low",
            "title": "Old-style string formatting",
            "suggestion": "Use f-strings (Python 3.6+) for readability",
            "effort": "2 min",
        },
        "mutable_default": {
            "pattern": r"def\s+\w+\([^)]*(?:\[\]|\{\}|set\(\))[^)]*\):",
            "category": "modernization",
            "severity": "high",
            "title": "Mutable default argument",
            "suggestion": "Use None as default and create mutable inside function",
            "effort": "5 min",
        },
        "wildcard_import": {
            "pattern": r"from\s+\w+\s+import\s+\*",
            "category": "naming",
            "severity": "medium",
            "title": "Wildcard import",
            "suggestion": "Import specific names to avoid namespace pollution",
            "effort": "10 min",
        },
        "nested_conditionals": {
            "pattern": r"if\s+.*:\s*\n\s+if\s+.*:\s*\n\s+if",
            "category": "complexity",
            "severity": "medium",
            "title": "Deeply nested conditionals",
            "suggestion": "Use early returns, guard clauses, or extract into functions",
            "effort": "15 min",
        },
        "todo_fixme": {
            "pattern": r"#\s*(?:TODO|FIXME|HACK|XXX|TEMP)",
            "category": "dead_code",
            "severity": "low",
            "title": "TODO/FIXME comment",
            "suggestion": "Resolve or create a tracked issue",
            "effort": "varies",
        },
        "global_variable": {
            "pattern": r"^(?!(?:import|from|class|def|#|@|if __name))[\w]+\s*=\s*(?!.*lambda)",
            "category": "modernization",
            "severity": "medium",
            "title": "Global mutable state",
            "suggestion": "Encapsulate in a class or use dependency injection",
            "effort": "20 min",
        },
    }
    
    def analyze(self, code: str, filename: str = "unknown") -> List[RefactoringOpportunity]:
        """Analyze code for refactoring opportunities."""
        opportunities = []
        counter = 0
        lines = code.split("\n")
        
        for name, config in self.PATTERNS.items():
            if "pattern" in config:
                matches = list(re.finditer(config["pattern"], code, re.MULTILINE))
                for match in matches[:3]:  # Max 3 per pattern
                    counter += 1
                    line_num = code[:match.start()].count("\n") + 1
                    opportunities.append(RefactoringOpportunity(
                        id=f"REF-{counter:03d}",
                        category=config["category"],
                        severity=config["severity"],
                        title=config["title"],
                        description=f"Found at line {line_num}: {match.group(0)[:60]}",
                        location=f"{filename}:{line_num}",
                        suggestion=config["suggestion"],
                        estimated_effort=config["effort"],
                    ))
        
        # Check overall metrics
        total_lines = len(lines)
        if total_lines > 500:
            counter += 1
            opportunities.append(RefactoringOpportunity(
                id=f"REF-{counter:03d}", category="complexity", severity="medium",
                title=f"Large file ({total_lines} lines)",
                description=f"File has {total_lines} lines — consider splitting",
                location=filename, suggestion="Split into multiple modules by responsibility",
                estimated_effort="1 hour",
            ))
        
        # Check comment ratio
        comment_lines = sum(1 for l in lines if l.strip().startswith("#"))
        if total_lines > 50 and comment_lines / total_lines < 0.05:
            counter += 1
            opportunities.append(RefactoringOpportunity(
                id=f"REF-{counter:03d}", category="naming", severity="low",
                title="Low comment density",
                description=f"Only {comment_lines}/{total_lines} lines are comments ({comment_lines/total_lines*100:.0f}%)",
                location=filename, suggestion="Add docstrings and comments for complex logic",
                estimated_effort="20 min",
            ))
        
        return opportunities
    
    def calculate_tech_debt_score(self, opportunities: List[RefactoringOpportunity]) -> Dict:
        """Calculate a tech debt score from opportunities."""
        severity_weights = {"high": 3, "medium": 2, "low": 1}
        total_weight = sum(severity_weights.get(o.severity, 1) for o in opportunities)
        
        # Estimate total effort
        effort_map = {"2 min": 2, "5 min": 5, "10 min": 10, "15 min": 15,
                     "20 min": 20, "30 min": 30, "1 hour": 60, "2 hours": 120, "varies": 15}
        total_effort = sum(effort_map.get(o.estimated_effort, 15) for o in opportunities)
        
        # Score: 100 = no debt, 0 = lots of debt
        score = max(0, 100 - total_weight * 5)
        
        return {
            "score": score,
            "grade": "A" if score >= 80 else "B" if score >= 60 else "C" if score >= 40 else "D" if score >= 20 else "F",
            "total_issues": len(opportunities),
            "estimated_effort_minutes": total_effort,
            "by_category": {
                cat: sum(1 for o in opportunities if o.category == cat)
                for cat in set(o.category for o in opportunities)
            },
        }
    
    def format_report(self, opportunities: List[RefactoringOpportunity]) -> str:
        """Format refactoring report for chat."""
        if not opportunities:
            return "✅ **Code Quality:** No refactoring needed — clean code!"
        
        debt = self.calculate_tech_debt_score(opportunities)
        emoji = {"high": "🔴", "medium": "🟡", "low": "🔵"}
        
        lines = [
            f"🔧 **Refactoring Report** — Grade: **{debt['grade']}** ({debt['score']}/100)",
            f"Issues: {debt['total_issues']} | Est. effort: {debt['estimated_effort_minutes']} min",
            "",
        ]
        
        for o in sorted(opportunities, key=lambda x: ["high","medium","low"].index(x.severity)):
            lines.append(f"{emoji[o.severity]} **{o.id}** [{o.category}] {o.title}")
            lines.append(f"  📍 `{o.location}` | Effort: {o.estimated_effort}")
            lines.append(f"  💡 {o.suggestion}")
            lines.append("")
        
        return "\n".join(lines)


if __name__ == "__main__":
    agent = RefactoringAgent()
    
    test_code = '''
from utils import *

DEBUG = True
MAX_ITEMS = 100

def process_data(items=[]):
    result = ""
    for item in items:
        if item.type == "A":
            if item.status == "active":
                if item.value > 42:
                    result += "Item %s is valid" % item.name
    # TODO: fix this hacky implementation
    except:
        print("debug: something failed")
    return result
'''
    
    opps = agent.analyze(test_code, "processor.py")
    print(agent.format_report(opps))
    
    debt = agent.calculate_tech_debt_score(opps)
    print(f"\nTech Debt Score: {debt['score']}/100 (Grade: {debt['grade']})")
    print(f"\n✅ Refactoring Agent tested — found {len(opps)} opportunities")
