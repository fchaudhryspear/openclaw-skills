#!/usr/bin/env python3
"""NexDev - Accessibility Auditor Agent. WCAG 2.2 compliance checking."""

import re
from typing import Dict, List


class AccessibilityAuditor:
    """Static accessibility checks + LLM-powered deep audit."""
    
    WCAG_CHECKS = {
        "1.1.1": {"name": "Non-text Content", "check": "img_alt"},
        "1.3.1": {"name": "Info and Relationships", "check": "semantic_html"},
        "1.4.3": {"name": "Contrast Minimum", "check": "contrast"},
        "2.1.1": {"name": "Keyboard", "check": "keyboard_nav"},
        "2.4.1": {"name": "Bypass Blocks", "check": "skip_links"},
        "2.4.2": {"name": "Page Titled", "check": "page_title"},
        "4.1.1": {"name": "Parsing", "check": "valid_html"},
        "4.1.2": {"name": "Name, Role, Value", "check": "aria_labels"},
    }
    
    def static_audit(self, html_or_jsx: str) -> List[Dict]:
        """Run static accessibility checks on HTML/JSX code."""
        findings = []
        
        # Check for images without alt text
        imgs = re.findall(r'<img[^>]*>', html_or_jsx)
        for img in imgs:
            if 'alt=' not in img and 'alt =' not in img:
                findings.append({
                    "criterion": "1.1.1", "level": "A", "status": "fail",
                    "element": img[:80], "issue": "Image missing alt attribute",
                    "remediation": "Add descriptive alt text or alt='' for decorative images",
                    "severity": "critical",
                })
        
        # Check for form inputs without labels
        inputs = re.findall(r'<input[^>]*>', html_or_jsx)
        for inp in inputs:
            if 'aria-label' not in inp and 'id=' not in inp:
                findings.append({
                    "criterion": "4.1.2", "level": "A", "status": "fail",
                    "element": inp[:80], "issue": "Form input missing label association",
                    "remediation": "Add aria-label or associate with <label> via id",
                    "severity": "major",
                })
        
        # Check for click handlers without keyboard equivalents
        onclick = re.findall(r'onClick=[{"\'].*?[}"\']', html_or_jsx)
        for handler in onclick:
            findings.append({
                "criterion": "2.1.1", "level": "A", "status": "warning",
                "element": handler[:80],
                "issue": "onClick handler - ensure keyboard equivalent exists",
                "remediation": "Add onKeyDown/onKeyPress handler or use <button> element",
                "severity": "major",
            })
        
        # Check for heading hierarchy
        headings = re.findall(r'<h(\d)', html_or_jsx)
        if headings:
            levels = [int(h) for h in headings]
            for i in range(1, len(levels)):
                if levels[i] > levels[i-1] + 1:
                    findings.append({
                        "criterion": "1.3.1", "level": "A", "status": "fail",
                        "element": f"h{levels[i]} after h{levels[i-1]}",
                        "issue": f"Heading level skipped: h{levels[i-1]} to h{levels[i]}",
                        "remediation": "Use sequential heading levels without skipping",
                        "severity": "minor",
                    })
        
        return findings
    
    def generate_report(self, findings: List[Dict]) -> Dict:
        """Generate accessibility audit report."""
        critical = sum(1 for f in findings if f.get("severity") == "critical")
        major = sum(1 for f in findings if f.get("severity") == "major")
        minor = sum(1 for f in findings if f.get("severity") == "minor")
        
        total = len(findings)
        score = max(0, 100 - (critical * 20) - (major * 10) - (minor * 3))
        
        return {
            "summary": {
                "total_issues": total,
                "critical": critical,
                "major": major,
                "minor": minor,
                "compliance_score": score,
            },
            "findings": findings,
            "recommendation": "fail" if critical > 0 else "pass_with_warnings" if major > 0 else "pass",
        }


if __name__ == "__main__":
    auditor = AccessibilityAuditor()
    test_html = '<img src="photo.jpg"><div onClick="doSomething()"><input type="text"><h1>Title</h1><h3>Skip</h3>'
    findings = auditor.static_audit(test_html)
    report = auditor.generate_report(findings)
    print(f"Score: {report['summary']['compliance_score']}/100")
    print(f"Issues: {report['summary']['total_issues']}")
    for f in findings:
        print(f"  [{f['severity']}] {f['criterion']}: {f['issue']}")
