#!/usr/bin/env python3
"""
NexDev Dependency Scanner (Tier 1 Feature)

Scans project dependencies for vulnerabilities, outdated packages,
and license compliance issues before installation.
Part of NexDev v3.0 World-Class Build Team Upgrade
"""

import json
import re
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime

# ──────────────────────────────────────────────────────────────────────────────
# Vulnerability Database (Mock - Real would use PyUp, Snyk, npm audit APIs)
# ──────────────────────────────────────────────────────────────────────────────

KNOWN_VULNERABILITIES = {
    "python": {
        "requests": [
            {"cve": "CVE-2023-32681", "severity": "medium", "fixed_in": "2.31.0", "description": "Unintended leak of Proxy-Authorization header"}
        ],
        "pillow": [
            {"cve": "CVE-2023-44271", "severity": "high", "fixed_in": "10.0.1", "description": "DoS via crafted JPEG file"}
        ],
        "urllib3": [
            {"cve": "CVE-2023-43804", "severity": "medium", "fixed_in": "2.0.6", "description": "Cookie leakage across domains"}
        ],
        "django": [
            {"cve": "CVE-2023-46695", "severity": "high", "fixed_in": "4.2.8", "description": "Potential ReDoS vulnerability"}
        ]
    },
    "javascript": {
        "express": [
            {"cve": "CVE-2022-24999", "severity": "high", "fixed_in": "4.18.2", "description": "Prototype pollution in qs"}
        ],
        "lodash": [
            {"cve": "CVE-2021-23337", "severity": "high", "fixed_in": "4.17.21", "description": "Command injection vulnerability"}
        ],
        "axios": [
            {"cve": "CVE-2023-45857", "severity": "medium", "fixed_in": "1.6.0", "description": "CSRF token leakage"}
        ]
    }
}

LICENSE_RISKS = {
    "high_risk": ["GPL-3.0", "AGPL-3.0", "SSPL"],
    "medium_risk": ["LGPL-3.0", "MPL-2.0", "EPL-2.0"],
    "low_risk": ["MIT", "Apache-2.0", "BSD-2-Clause", "BSD-3-Clause", "ISC"]
}


# ──────────────────────────────────────────────────────────────────────────────
# Package File Parsers
# ──────────────────────────────────────────────────────────────────────────────

def parse_requirements_txt(content: str) -> List[Dict[str, Any]]:
    """Parse requirements.txt file."""
    packages = []
    
    for line in content.split('\n'):
        line = line.strip()
        
        # Skip comments and empty lines
        if not line or line.startswith('#') or line.startswith('-'):
            continue
        
        # Parse package name and version
        match = re.match(r'^([a-zA-Z0-9_-]+)(?:==|>=|<=|~=|!=)?(.*)$', line)
        if match:
            packages.append({
                "name": match.group(1),
                "version_constraint": match.group(2).strip(),
                "current_version": match.group(2).strip() if '==' in line else None
            })
    
    return packages


def parse_package_json(content: str) -> List[Dict[str, Any]]:
    """Parse package.json file."""
    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        return []
    
    packages = []
    
    for dep_type in ['dependencies', 'devDependencies']:
        deps = data.get(dep_type, {})
        for name, version in deps.items():
            packages.append({
                "name": name,
                "version_constraint": version,
                "current_version": version.lstrip('^~'),
                "type": dep_type.replace('D', '').lower()
            })
    
    return packages


def parse_gemfile(content: str) -> List[Dict[str, Any]]:
    """Parse Gemfile (Ruby)."""
    packages = []
    
    pattern = r"gem\s+['\"]([^'\"]+)['\"](?:,\s*['\"]([^'\"]+)['\"])?"
    
    for match in re.finditer(pattern, content):
        packages.append({
            "name": match.group(1),
            "version_constraint": match.group(2) if match.group(2) else None,
            "current_version": match.group(2) if match.group(2) else None
        })
    
    return packages


# ──────────────────────────────────────────────────────────────────────────────
# Analysis Functions
# ──────────────────────────────────────────────────────────────────────────────

def check_vulnerabilities(packages: List[Dict[str, Any]], language: str) -> List[Dict[str, Any]]:
    """Check packages against known vulnerability database."""
    vulns = []
    
    lang_vulns = KNOWN_VULNERABILITIES.get(language, {})
    
    for pkg in packages:
        pkg_name = pkg['name'].lower()
        
        if pkg_name in lang_vulns:
            for vuln in lang_vulns[pkg_name]:
                current_ver = pkg.get('current_version')
                
                # Simple version comparison (imperfect but functional)
                is_affected = True
                if current_ver and 'fixed_in' in vuln:
                    try:
                        curr_parts = [int(x) for x in current_ver.replace('v','').split('.')[:3]]
                        fixed_parts = [int(x) for x in vuln['fixed_in'].replace('v','').split('.')[:3]]
                        
                        is_affected = curr_parts < fixed_parts
                    except (ValueError, AttributeError):
                        pass
                
                if is_affected:
                    vulns.append({
                        "package": pkg_name,
                        "cve": vuln.get('cve', 'Unknown'),
                        "severity": vuln.get('severity', 'unknown'),
                        "description": vuln.get('description', ''),
                        "fixed_in": vuln.get('fixed_in', 'Unknown'),
                        "recommendation": f"Upgrade to {vuln.get('fixed_in')} or later"
                    })
    
    return vulns


def check_license_compliance(packages: List[Dict[str, Any]], allow_commercial: bool = True) -> List[Dict[str, Any]]:
    """Check package licenses for compliance."""
    # This would require calling an API like license-checker, scancode, etc.
    # For now, returns mock structure
    
    return [{
        "package": "example-pkg",
        "license": "MIT",
        "risk_level": "low",
        "is_commercial_safe": True,
        "note": "Permissive license - safe for commercial use"
    }]


def get_latest_version(package_name: str, language: str) -> Optional[str]:
    """Fetch latest version from package registry."""
    # Mock implementation - would call PyPI/npm registry APIs
    
    mock_versions = {
        "requests": "2.31.0",
        "flask": "3.0.0",
        "express": "4.18.2",
        "react": "18.2.0"
    }
    
    return mock_versions.get(package_name)


def suggest_updates(packages: List[Dict[str, Any]], language: str) -> List[Dict[str, Any]]:
    """Suggest package updates."""
    updates = []
    
    for pkg in packages:
        latest = get_latest_version(pkg['name'], language)
        current = pkg.get('current_version')
        
        if latest and current and latest != current:
            try:
                curr_parts = [int(x) for x in current.replace('v','').replace('^','').replace('~','').split('.')[:3]]
                latest_parts = [int(x) for x in latest.split('.')[:3]]
                
                is_outdated = curr_parts < latest_parts
                
                if is_outdated:
                    major_bump = latest_parts[0] > curr_parts[0] if len(curr_parts) > 0 else False
                    
                    updates.append({
                        "package": pkg['name'],
                        "current_version": current,
                        "latest_version": latest,
                        "is_major_upgrade": major_bump,
                        "breaking_changes_warning": major_bump,
                        "command": f"{language}-install update {pkg['name']}@{latest}"
                    })
            except (ValueError, IndexError):
                pass
    
    return updates


# ──────────────────────────────────────────────────────────────────────────────
# Main Integration Functions
# ──────────────────────────────────────────────────────────────────────────────

def scan_project(project_dir: str) -> Dict[str, Any]:
    """
    Scan a project for dependency issues.
    
    Args:
        project_dir: Root directory of the project
        
    Returns:
        Comprehensive scan results
    """
    project_path = Path(project_dir)
    
    results = {
        "success": False,
        "project_dir": str(project_path),
        "scan_time": datetime.now().isoformat(),
        "packages_found": [],
        "vulnerabilities": [],
        "updates_available": [],
        "license_issues": [],
        "summary": {}
    }
    
    # Detect package files
    package_files = []
    
    # Python
    req_txt = project_path / "requirements.txt"
    if req_txt.exists():
        package_files.append({"path": str(req_txt), "language": "python", "type": "requirements"})
    
    pyproject = project_path / "pyproject.toml"
    if pyproject.exists():
        package_files.append({"path": str(pyproject), "language": "python", "type": "pyproject"})
    
    # JavaScript
    package_json = project_path / "package.json"
    if package_json.exists():
        package_files.append({"path": str(package_json), "language": "javascript", "type": "npm"})
    
    # Ruby
    gemfile = project_path / "Gemfile"
    if gemfile.exists():
        package_files.append({"path": str(gemfile), "language": "ruby", "type": "bundle"})
    
    if not package_files:
        results["error"] = "No package management files found"
        return results
    
    # Process each package file
    all_packages = []
    languages_detected = set()
    
    for pf in package_files:
        content = Path(pf["path"]).read_text()
        language = pf["language"]
        languages_detected.add(language)
        
        if pf["type"] == "requirements":
            packages = parse_requirements_txt(content)
        elif pf["type"] == "npm":
            packages = parse_package_json(content)
        elif pf["type"] == "bundle":
            packages = parse_gemfile(content)
        else:
            packages = []
        
        all_packages.extend([{**p, "source_file": pf["path"]} for p in packages])
    
    results["packages_found"] = all_packages
    results["languages"] = list(languages_detected)
    
    # Analyze for issues
    for language in languages_detected:
        lang_packages = [p for p in all_packages if p.get("source_file", "").find(language) >= 0 or any(k in language for k in ['python', 'javascript'])]
        
        # Check vulnerabilities
        vulns = check_vulnerabilities(lang_packages, language)
        results["vulnerabilities"].extend(vulns)
        
        # Check for updates
        updates = suggest_updates(lang_packages, language)
        results["updates_available"].extend(updates)
        
        # Check licenses
        licenses = check_license_compliance(lang_packages)
        results["license_issues"].extend(licenses)
    
    # Generate summary
    critical_vulns = sum(1 for v in results["vulnerabilities"] if v["severity"] == "critical")
    high_vulns = sum(1 for v in results["vulnerabilities"] if v["severity"] == "high")
    medium_vulns = sum(1 for v in results["vulnerabilities"] if v["severity"] == "medium")
    
    results["summary"] = {
        "total_packages": len(all_packages),
        "total_vulnerabilities": len(results["vulnerabilities"]),
        "critical": critical_vulns,
        "high": high_vulns,
        "medium": medium_vulns,
        "updates_available": len(results["updates_available"]),
        "safe_to_install": critical_vulns == 0 and high_vulns == 0,
        "languages": list(languages_detected)
    }
    
    results["success"] = True
    
    return results


def generate_recommendation_report(scan_results: Dict[str, Any]) -> str:
    """Generate human-readable recommendation report."""
    
    lines = [
        "=" * 70,
        "DEPENDENCY SCAN REPORT",
        "=" * 70,
        "",
        f"Project: {scan_results.get('project_dir', 'Unknown')}",
        f"Scan Time: {scan_results.get('scan_time', 'Unknown')}",
        "",
        "SUMMARY",
        "-" * 70
    ]
    
    summary = scan_results.get("summary", {})
    lines.append(f"Total Packages:      {summary.get('total_packages', 0)}")
    lines.append(f"Vulnerabilities:     {summary.get('total_vulnerabilities', 0)}")
    lines.append(f"  • Critical:        {summary.get('critical', 0)} 🔴")
    lines.append(f"  • High:            {summary.get('high', 0)} 🟠")
    lines.append(f"  • Medium:          {summary.get('medium', 0)} 🟡")
    lines.append(f"Updates Available:   {summary.get('updates_available', 0)}")
    lines.append(f"Safe to Install:     {'Yes ✅' if summary.get('safe_to_install') else 'NO ❌'}")
    
    if scan_results.get("vulnerabilities"):
        lines.extend([
            "",
            "VULNERABILITIES DETECTED",
            "-" * 70
        ])
        
        for vuln in scan_results["vulnerabilities"]:
            icon = {"critical": "🔴", "high": "🟠", "medium": "🟡"}.get(vuln["severity"], "⚪")
            lines.extend([
                "",
                f"{icon} Package: {vuln['package']}",
                f"   CVE: {vuln['cve']}",
                f"   Severity: {vuln['severity'].upper()}",
                f"   Issue: {vuln['description']}",
                f"   Fix: {vuln['recommendation']}"
            ])
    
    if scan_results.get("updates_available"):
        lines.extend([
            "",
            "AVAILABLE UPDATES",
            "-" * 70
        ])
        
        for upd in scan_results["updates_available"][:10]:  # Top 10
            warning = " ⚠️ BREAKING CHANGES" if upd.get("breaking_changes_warning") else ""
            lines.append(f"  • {upd['package']}: {upd['current_version']} → {upd['latest_version']}{warning}")
    
    lines.extend([
        "",
        "=" * 70,
        "Recommendations:",
        "-" * 70
    ])
    
    if summary.get("critical", 0) > 0:
        lines.append("  ❗ URGENT: Fix critical vulnerabilities before deployment!")
    if summary.get("high", 0) > 0:
        lines.append("  ⚠️  HIGH: Address high-severity issues immediately")
    if summary.get("updates_available", 0) > 0:
        lines.append("  🔄 UPDATE: Run dependency updates to stay current")
    if summary.get("safe_to_install", False):
        lines.append("  ✅ All clear! Safe to install and deploy")
    
    lines.append("")
    lines.append("=" * 70)
    
    return "\n".join(lines)


if __name__ == "__main__":
    # Demo mode
    print("=" * 60)
    print("🔒 NEXDEV DEPENDENCY SCANNER - DEMO")
    print("=" * 60)
    
    # Create sample requirements.txt
    sample_req = """
# Core dependencies
requests==2.28.0
flask==2.0.0
pillow==9.0.0
numpy>=1.21.0

# Dev dependencies
pytest==7.0.0
black==22.0.0
"""
    
    print("\nSample requirements.txt:")
    print("-" * 60)
    print(sample_req)
    
    # Parse
    packages = parse_requirements_txt(sample_req)
    
    print(f"\nParsed {len(packages)} packages:")
    for pkg in packages:
        print(f"  • {pkg['name']} {pkg.get('current_version', 'unspecified')}")
    
    # Check vulnerabilities
    print("\nChecking vulnerabilities...")
    vulns = check_vulnerabilities(packages, "python")
    
    if vulns:
        print(f"\nFound {len(vulns)} vulnerabilities:")
        for v in vulns:
            icon = {"critical": "🔴", "high": "🟠", "medium": "🟡"}.get(v["severity"], "⚪")
            print(f"  {icon} {v['package']} ({v['severity']}) - {v['cve']}")
            print(f"     Fix: {v['recommendation']}")
    else:
        print("✅ No known vulnerabilities detected")
    
    # Check updates
    print("\nChecking for updates...")
    updates = suggest_updates(packages, "python")
    
    if updates:
        print(f"Available updates:")
        for u in updates[:3]:
            print(f"  • {u['package']}: {u['current_version']} → {u['latest_version']}")
    else:
        print("✅ All packages up to date")
    
    print("\n" + "=" * 60)
    print("Demo complete!")
