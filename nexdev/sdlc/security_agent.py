#!/usr/bin/env python3
"""
NexDev Phase 2B.2 — Security Architect Agent
==============================================
Specialized sub-agent for identifying security vulnerabilities,
OWASP Top 10 analysis, and threat modeling.
"""

import re
from typing import Dict, List
from datetime import datetime
from dataclasses import dataclass, field, asdict


@dataclass
class SecurityFinding:
    id: str
    severity: str  # critical, high, medium, low, info
    category: str  # OWASP category
    title: str
    description: str
    location: str  # file:line or component
    recommendation: str
    cwe_id: str = ""
    owasp_ref: str = ""


@dataclass
class ThreatModel:
    asset: str
    threat: str
    attack_vector: str
    likelihood: str  # low, medium, high
    impact: str
    mitigation: str
    status: str = "open"


class SecurityArchitect:
    """Security analysis agent for NexDev pipeline."""
    
    # OWASP Top 10 (2021) patterns
    OWASP_PATTERNS = {
        "A01:2021-Broken Access Control": {
            "patterns": [
                r"(?i)admin.*=.*true",
                r"(?i)role.*=.*['\"]admin['\"]",
                r"(?i)is_admin\s*=\s*request",
                r"(?i)@app\.route.*methods.*without.*auth",
                r"(?i)disable.*auth",
                r"(?i)skip.*authorization",
            ],
            "description": "Access control enforcement failures",
            "recommendation": "Implement proper RBAC, deny by default, validate permissions server-side",
        },
        "A02:2021-Cryptographic Failures": {
            "patterns": [
                r"(?i)md5\s*\(",
                r"(?i)sha1\s*\(",
                r"(?i)password\s*=\s*['\"][^'\"]{1,20}['\"]",
                r"(?i)secret.*=.*['\"]hardcoded",
                r"(?i)http://(?!localhost|127\.0\.0\.1)",
                r"(?i)verify\s*=\s*False",
                r"(?i)ssl\s*=\s*False",
            ],
            "description": "Weak cryptography or plaintext sensitive data",
            "recommendation": "Use strong encryption (AES-256, bcrypt), enforce HTTPS, never hardcode secrets",
        },
        "A03:2021-Injection": {
            "patterns": [
                r"(?i)execute\s*\(\s*['\"].*%s",
                r"(?i)execute\s*\(\s*f['\"]",
                r"(?i)query\s*=\s*['\"].*\+.*user",
                r"(?i)system\s*\(",
                r"(?i)subprocess\.call\s*\(\s*['\"].*\+",
                r"(?i)eval\s*\(",
                r"(?i)exec\s*\(",
                r"(?i)os\.system\s*\(",
                r"(?i)innerHTML\s*=",
                r"(?i)document\.write\s*\(",
            ],
            "description": "SQL, OS command, or code injection vulnerabilities",
            "recommendation": "Use parameterized queries, input validation, avoid eval/exec",
        },
        "A04:2021-Insecure Design": {
            "patterns": [
                r"(?i)# ?TODO.*security",
                r"(?i)# ?FIXME.*auth",
                r"(?i)# ?HACK",
                r"(?i)password.*=.*password",
                r"(?i)trust.*user.*input",
            ],
            "description": "Flaws in design patterns and architecture",
            "recommendation": "Use threat modeling, secure design patterns, defense in depth",
        },
        "A05:2021-Security Misconfiguration": {
            "patterns": [
                r"(?i)debug\s*=\s*True",
                r"(?i)DEBUG\s*=\s*True",
                r"(?i)allow_origins\s*=\s*\[?\s*['\"]?\*",
                r"(?i)CORS.*\*",
                r"(?i)expose.*stack.*trace",
                r"(?i)verbose.*error",
            ],
            "description": "Insecure default configurations",
            "recommendation": "Disable debug mode, restrict CORS, minimize error details in production",
        },
        "A07:2021-Auth Failures": {
            "patterns": [
                r"(?i)jwt.*algorithm\s*=\s*['\"]none['\"]",
                r"(?i)verify.*=.*False",
                r"(?i)password.*len.*<\s*[1-7]\b",
                r"(?i)max.*login.*attempt.*=.*[0-9]{3,}",
                r"(?i)session.*expire.*=.*0",
                r"(?i)token.*expire.*never",
            ],
            "description": "Authentication and session management flaws",
            "recommendation": "Strong passwords, MFA, secure session management, rate limiting",
        },
        "A09:2021-Logging Failures": {
            "patterns": [
                r"(?i)password.*log",
                r"(?i)log.*password",
                r"(?i)print\s*\(.*password",
                r"(?i)print\s*\(.*secret",
                r"(?i)print\s*\(.*token",
                r"(?i)console\.log.*password",
                r"(?i)console\.log.*secret",
            ],
            "description": "Insufficient logging or logging sensitive data",
            "recommendation": "Log security events, never log credentials, use structured logging",
        },
    }
    
    def scan_code(self, code: str, filename: str = "unknown") -> List[SecurityFinding]:
        """Scan code for security vulnerabilities."""
        findings = []
        lines = code.split("\n")
        finding_counter = 0
        
        for owasp_id, config in self.OWASP_PATTERNS.items():
            for pattern in config["patterns"]:
                for line_num, line in enumerate(lines, 1):
                    if re.search(pattern, line):
                        finding_counter += 1
                        
                        # Determine severity
                        severity = "high"
                        if "A03" in owasp_id:  # Injection = critical
                            severity = "critical"
                        elif "A05" in owasp_id or "A09" in owasp_id:
                            severity = "medium"
                        elif "A04" in owasp_id:
                            severity = "low"
                        
                        findings.append(SecurityFinding(
                            id=f"SEC-{finding_counter:03d}",
                            severity=severity,
                            category=owasp_id,
                            title=f"{owasp_id.split('-')[1]} vulnerability detected",
                            description=config["description"],
                            location=f"{filename}:{line_num}",
                            recommendation=config["recommendation"],
                            owasp_ref=owasp_id,
                        ))
        
        return findings
    
    def scan_architecture(self, design_data: Dict) -> List[SecurityFinding]:
        """Scan architecture design for security issues."""
        findings = []
        counter = 0
        
        # Check for missing security components
        components = [c.get("name", "").lower() for c in design_data.get("components", [])]
        
        if not any("auth" in c for c in components):
            counter += 1
            findings.append(SecurityFinding(
                id=f"ARCH-SEC-{counter:03d}", severity="critical",
                category="A01:2021-Broken Access Control",
                title="No authentication service defined",
                description="Architecture lacks a dedicated authentication component",
                location="architecture.components",
                recommendation="Add an Authentication Service with JWT/OAuth2 support",
            ))
        
        if not any("rate" in c or "gateway" in c for c in components):
            counter += 1
            findings.append(SecurityFinding(
                id=f"ARCH-SEC-{counter:03d}", severity="high",
                category="A05:2021-Security Misconfiguration",
                title="No API gateway or rate limiting",
                description="Architecture lacks rate limiting protection",
                location="architecture.components",
                recommendation="Add API Gateway with rate limiting and DDoS protection",
            ))
        
        # Check endpoints for auth
        for ep in design_data.get("api_endpoints", []):
            if isinstance(ep, dict) and not ep.get("auth_required", True):
                path = ep.get("path", "unknown")
                if "health" not in path and "public" not in path:
                    counter += 1
                    findings.append(SecurityFinding(
                        id=f"ARCH-SEC-{counter:03d}", severity="medium",
                        category="A01:2021-Broken Access Control",
                        title=f"Unauthenticated endpoint: {path}",
                        description="Endpoint does not require authentication",
                        location=f"api:{path}",
                        recommendation="Review if this endpoint should be public",
                    ))
        
        # Check security considerations
        security_notes = design_data.get("security_considerations", [])
        if len(security_notes) < 3:
            counter += 1
            findings.append(SecurityFinding(
                id=f"ARCH-SEC-{counter:03d}", severity="medium",
                category="A04:2021-Insecure Design",
                title="Insufficient security considerations",
                description=f"Only {len(security_notes)} security considerations documented",
                location="architecture.security_considerations",
                recommendation="Document at least 8 security considerations covering OWASP Top 10",
            ))
        
        return findings
    
    def generate_threat_model(self, design_data: Dict) -> List[ThreatModel]:
        """Generate a basic threat model from architecture."""
        threats = []
        
        # Standard threats per component type
        component_threats = {
            "api": [
                ThreatModel("API Endpoints", "SQL Injection", "Malformed input parameters",
                           "medium", "high", "Parameterized queries, input validation"),
                ThreatModel("API Endpoints", "DDoS Attack", "High-volume requests",
                           "medium", "high", "Rate limiting, WAF, auto-scaling"),
            ],
            "auth": [
                ThreatModel("Authentication", "Credential Stuffing", "Automated login attempts",
                           "high", "high", "Rate limiting, MFA, account lockout"),
                ThreatModel("Authentication", "Token Theft", "XSS or session hijacking",
                           "medium", "high", "Secure cookies, short token expiry, CSRF protection"),
            ],
            "database": [
                ThreatModel("Database", "Data Breach", "Unauthorized access to database",
                           "medium", "critical", "Encryption at rest, network isolation, least privilege"),
                ThreatModel("Database", "Data Loss", "Accidental deletion or corruption",
                           "low", "critical", "Automated backups, point-in-time recovery"),
            ],
            "frontend": [
                ThreatModel("Frontend", "XSS Attack", "Injected malicious scripts",
                           "high", "medium", "Content Security Policy, output encoding"),
                ThreatModel("Frontend", "CSRF Attack", "Forged cross-site requests",
                           "medium", "medium", "CSRF tokens, SameSite cookies"),
            ],
            "payment": [
                ThreatModel("Payments", "Payment Fraud", "Stolen card numbers",
                           "medium", "high", "Use Stripe/payment processor tokens, never store card data"),
            ],
        }
        
        for component in design_data.get("components", []):
            comp_name = component.get("name", "").lower()
            for key, threat_list in component_threats.items():
                if key in comp_name:
                    threats.extend(threat_list)
        
        return threats
    
    def format_security_report(self, findings: List[SecurityFinding],
                                threats: List[ThreatModel] = None) -> str:
        """Format security report for chat."""
        severity_emoji = {
            "critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🔵", "info": "⚪"
        }
        
        lines = ["🔒 **Security Analysis Report**", ""]
        
        # Summary
        by_severity = {}
        for f in findings:
            by_severity[f.severity] = by_severity.get(f.severity, 0) + 1
        
        summary_parts = []
        for sev in ["critical", "high", "medium", "low"]:
            if sev in by_severity:
                summary_parts.append(f"{severity_emoji[sev]} {by_severity[sev]} {sev}")
        
        lines.append(f"**Findings:** {' | '.join(summary_parts) if summary_parts else '✅ No issues'}")
        lines.append("")
        
        # Findings
        for f in sorted(findings, key=lambda x: ["critical","high","medium","low","info"].index(x.severity)):
            lines.append(f"{severity_emoji[f.severity]} **{f.id}** [{f.severity.upper()}] {f.title}")
            lines.append(f"  Location: `{f.location}`")
            lines.append(f"  Fix: {f.recommendation}")
            lines.append("")
        
        # Threat model
        if threats:
            lines.append("**Threat Model:**")
            for t in threats:
                lines.append(f"• **{t.asset}** — {t.threat} (Likelihood: {t.likelihood}, Impact: {t.impact})")
                lines.append(f"  Mitigation: {t.mitigation}")
        
        return "\n".join(lines)


if __name__ == "__main__":
    sec = SecurityArchitect()
    
    # Test code scanning
    test_code = '''
import os
from flask import Flask, request
app = Flask(__name__)
app.config["DEBUG"] = True

@app.route("/admin")
def admin():
    is_admin = request.args.get("admin")
    if is_admin == "true":
        return "Admin panel"

def get_user(user_id):
    query = "SELECT * FROM users WHERE id = " + user_id
    cursor.execute(query)
    return cursor.fetchone()

password = "admin123"
print(f"User password: {password}")
'''
    
    findings = sec.scan_code(test_code, "app.py")
    print(sec.format_security_report(findings))
    print(f"\n✅ Security Architect tested — found {len(findings)} issues")
