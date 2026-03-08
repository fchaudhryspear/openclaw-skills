#!/usr/bin/env python3
"""
NexDev Phase 2B.3 — Performance Engineer Agent
================================================
Analyzes code for performance bottlenecks, suggests optimizations,
and provides benchmarking recommendations.
"""

import re
from typing import Dict, List
from dataclasses import dataclass, asdict


@dataclass
class PerformanceFinding:
    id: str
    severity: str  # critical, high, medium, low
    category: str  # algorithm, database, memory, network, io
    title: str
    description: str
    location: str
    recommendation: str
    estimated_impact: str = ""


class PerformanceEngineer:
    """Performance analysis agent for NexDev pipeline."""
    
    # Performance anti-patterns
    ANTIPATTERNS = {
        "n_plus_one": {
            "patterns": [
                r"for.*in.*:\s*\n\s*.*\.query\(",
                r"for.*in.*:\s*\n\s*.*\.execute\(",
                r"for.*in.*:\s*\n\s*.*\.find\(",
                r"for.*in.*:\s*\n\s*.*\.get\(",
                r"for.*in.*:\s*\n\s*.*fetch",
            ],
            "category": "database",
            "severity": "critical",
            "title": "N+1 Query Pattern",
            "description": "Database query inside a loop — causes N+1 queries instead of 1",
            "recommendation": "Use batch fetching, JOINs, or eager loading to fetch all data in one query",
            "impact": "Can be 10-100x slower with large datasets",
        },
        "no_pagination": {
            "patterns": [
                r"\.all\(\)",
                r"SELECT\s+\*\s+FROM\s+\w+\s*(?!.*LIMIT)",
                r"find\(\{\}\)",
                r"\.fetchall\(\)",
            ],
            "category": "database",
            "severity": "high",
            "title": "Unbounded Query",
            "description": "Fetching all records without pagination — memory bomb with large datasets",
            "recommendation": "Add LIMIT/OFFSET pagination or cursor-based pagination",
            "impact": "Memory exhaustion and slow responses with large tables",
        },
        "no_index_hint": {
            "patterns": [
                r"WHERE.*LIKE\s+['\"]%",
                r"WHERE.*!=",
                r"WHERE.*NOT\s+IN",
                r"ORDER\s+BY.*(?!.*INDEX)",
            ],
            "category": "database",
            "severity": "medium",
            "title": "Potentially Unindexed Query",
            "description": "Query pattern that may not use indexes efficiently",
            "recommendation": "Ensure appropriate indexes exist, avoid leading wildcards in LIKE",
            "impact": "Full table scans on large datasets",
        },
        "sync_io_in_async": {
            "patterns": [
                r"async.*def.*:\s*\n(?:.*\n)*?\s+(?:open|read|write)\(",
                r"async.*def.*:\s*\n(?:.*\n)*?\s+requests\.",
                r"async.*def.*:\s*\n(?:.*\n)*?\s+time\.sleep\(",
            ],
            "category": "io",
            "severity": "high",
            "title": "Synchronous I/O in Async Context",
            "description": "Blocking I/O operation inside async function — blocks event loop",
            "recommendation": "Use aiohttp instead of requests, aiofiles for file I/O, asyncio.sleep",
            "impact": "Blocks all concurrent requests",
        },
        "nested_loops": {
            "patterns": [
                r"for\s+\w+\s+in\s+\w+:\s*\n\s+for\s+\w+\s+in\s+\w+:\s*\n\s+for",
            ],
            "category": "algorithm",
            "severity": "high",
            "title": "Triple Nested Loop (O(n³))",
            "description": "Three nested loops — cubic time complexity",
            "recommendation": "Use hash maps, sorting, or different algorithms to reduce complexity",
            "impact": "Unusable with datasets > 1000 items",
        },
        "double_loop": {
            "patterns": [
                r"for\s+\w+\s+in\s+\w+:\s*\n\s+for\s+\w+\s+in\s+\w+:",
            ],
            "category": "algorithm",
            "severity": "medium",
            "title": "Nested Loop (O(n²))",
            "description": "Two nested loops — quadratic time complexity",
            "recommendation": "Consider hash maps or sorted data for O(n log n) or O(n) alternatives",
            "impact": "Slow with datasets > 10K items",
        },
        "string_concat_loop": {
            "patterns": [
                r"for.*:\s*\n\s+\w+\s*\+=\s*['\"]",
                r"for.*:\s*\n\s+\w+\s*=\s*\w+\s*\+\s*['\"]",
            ],
            "category": "memory",
            "severity": "medium",
            "title": "String Concatenation in Loop",
            "description": "Building strings with += in a loop — creates new string objects each iteration",
            "recommendation": "Use list.append() + ''.join() or io.StringIO",
            "impact": "O(n²) memory allocation for large strings",
        },
        "no_caching": {
            "patterns": [
                r"def\s+get_\w+\(.*\):\s*\n\s+.*\.query\(",
                r"def\s+fetch_\w+\(.*\):\s*\n\s+.*requests\.get\(",
            ],
            "category": "network",
            "severity": "low",
            "title": "No Caching on Repeated Fetches",
            "description": "Function fetches data without caching — redundant calls",
            "recommendation": "Add caching (Redis, lru_cache, or in-memory TTL cache)",
            "impact": "Unnecessary latency and API/DB load",
        },
        "large_payload": {
            "patterns": [
                r"json\.dumps\(.*\)",
                r"jsonify\(.*all\(\)\)",
                r"return\s+.*\.to_dict\(\)",
            ],
            "category": "network",
            "severity": "low",
            "title": "Potentially Large Response Payload",
            "description": "Response may include unnecessary data",
            "recommendation": "Use field selection, DTOs, or GraphQL to return only needed fields",
            "impact": "Increased bandwidth and client parsing time",
        },
    }
    
    def analyze_code(self, code: str, filename: str = "unknown") -> List[PerformanceFinding]:
        """Analyze code for performance issues."""
        findings = []
        counter = 0
        
        for pattern_name, config in self.ANTIPATTERNS.items():
            for pattern in config["patterns"]:
                matches = list(re.finditer(pattern, code, re.MULTILINE))
                if matches:
                    counter += 1
                    # Find approximate line number
                    first_match = matches[0]
                    line_num = code[:first_match.start()].count("\n") + 1
                    
                    findings.append(PerformanceFinding(
                        id=f"PERF-{counter:03d}",
                        severity=config["severity"],
                        category=config["category"],
                        title=config["title"],
                        description=config["description"],
                        location=f"{filename}:{line_num}",
                        recommendation=config["recommendation"],
                        estimated_impact=config.get("impact", ""),
                    ))
                    break  # One finding per pattern group
        
        return findings
    
    def analyze_architecture(self, design_data: Dict) -> List[PerformanceFinding]:
        """Analyze architecture for performance concerns."""
        findings = []
        counter = 0
        
        components = design_data.get("components", [])
        tech_stack = design_data.get("tech_stack", {})
        
        # Check for caching layer
        has_cache = any("redis" in c.get("technology", "").lower() or 
                       "cache" in c.get("name", "").lower()
                       for c in components)
        
        if not has_cache and len(components) > 3:
            counter += 1
            findings.append(PerformanceFinding(
                id=f"ARCH-PERF-{counter:03d}", severity="high",
                category="network", title="No Caching Layer",
                description="Architecture lacks a caching layer (Redis/Memcached)",
                location="architecture.components",
                recommendation="Add Redis or similar caching for frequently accessed data",
                estimated_impact="2-10x improvement on read-heavy workloads",
            ))
        
        # Check for CDN
        has_frontend = any("frontend" in c.get("type", "").lower() for c in components)
        has_cdn = any("cdn" in c.get("name", "").lower() for c in components)
        
        if has_frontend and not has_cdn:
            counter += 1
            findings.append(PerformanceFinding(
                id=f"ARCH-PERF-{counter:03d}", severity="medium",
                category="network", title="No CDN for Static Assets",
                description="Frontend exists without a CDN for static asset delivery",
                location="architecture.components",
                recommendation="Add CloudFront/CloudFlare CDN for static assets",
                estimated_impact="50-80% reduction in page load time",
            ))
        
        # Check for connection pooling
        has_db = any("database" in c.get("type", "").lower() for c in components)
        if has_db:
            counter += 1
            findings.append(PerformanceFinding(
                id=f"ARCH-PERF-{counter:03d}", severity="medium",
                category="database", title="Ensure Database Connection Pooling",
                description="Database connections should use connection pooling",
                location="architecture.database",
                recommendation="Configure connection pool (PgBouncer, SQLAlchemy pool, etc.)",
                estimated_impact="Prevents connection exhaustion under load",
            ))
        
        return findings
    
    def suggest_optimizations(self, code: str) -> List[Dict]:
        """Suggest specific code optimizations."""
        suggestions = []
        
        # Check for list comprehension opportunities
        if re.search(r"for\s+\w+\s+in\s+\w+:\s*\n\s+\w+\.append\(", code):
            suggestions.append({
                "type": "refactor",
                "title": "Use list comprehension",
                "description": "Replace loop+append pattern with list comprehension for 2-3x speed",
            })
        
        # Check for set usage
        if re.search(r"if\s+\w+\s+in\s+\[", code):
            suggestions.append({
                "type": "data_structure",
                "title": "Use set for membership testing",
                "description": "Replace list membership test with set for O(1) lookup",
            })
        
        # Check for generator opportunities
        if re.search(r"return\s+\[.*for.*in.*\]", code):
            suggestions.append({
                "type": "memory",
                "title": "Consider generator for large results",
                "description": "If result is consumed once, use generator to save memory",
            })
        
        return suggestions
    
    def format_report(self, findings: List[PerformanceFinding],
                      suggestions: List[Dict] = None) -> str:
        """Format performance report for chat."""
        severity_emoji = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🔵"}
        
        lines = ["⚡ **Performance Analysis Report**", ""]
        
        if not findings:
            lines.append("✅ No significant performance issues detected")
            return "\n".join(lines)
        
        by_cat = {}
        for f in findings:
            by_cat[f.category] = by_cat.get(f.category, 0) + 1
        
        lines.append(f"Found **{len(findings)}** issues: " + 
                     ", ".join(f"{v} {k}" for k, v in by_cat.items()))
        lines.append("")
        
        for f in sorted(findings, key=lambda x: ["critical","high","medium","low"].index(x.severity)):
            lines.append(f"{severity_emoji[f.severity]} **{f.id}** [{f.category}] {f.title}")
            lines.append(f"  📍 `{f.location}`")
            lines.append(f"  💡 {f.recommendation}")
            if f.estimated_impact:
                lines.append(f"  📈 Impact: {f.estimated_impact}")
            lines.append("")
        
        if suggestions:
            lines.append("**Quick Wins:**")
            for s in suggestions:
                lines.append(f"• {s['title']}: {s['description']}")
        
        return "\n".join(lines)


if __name__ == "__main__":
    perf = PerformanceEngineer()
    
    test_code = '''
async def get_users_with_orders(db):
    users = db.query(User).all()
    result = []
    for user in users:
        orders = db.query(Order).filter(user_id=user.id).all()
        name = ""
        for order in orders:
            name += order.product_name + ", "
        result.append({"user": user, "orders": orders})
    return result

def search_users(name):
    if name in ["admin", "root", "test"]:
        return None
    return db.execute(f"SELECT * FROM users WHERE name LIKE '%{name}%'")
'''
    
    findings = perf.analyze_code(test_code, "users.py")
    suggestions = perf.suggest_optimizations(test_code)
    print(perf.format_report(findings, suggestions))
    print(f"\n✅ Performance Engineer tested — found {len(findings)} issues")
