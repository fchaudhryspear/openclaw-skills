#!/usr/bin/env python3
"""NexDev - Compliance & Trust Agents.
Legal Compliance Checker, Identity & Trust Architect."""

import re
import json
from typing import Dict, List


class LegalComplianceChecker:
    """Scans code for regulatory compliance issues."""
    
    PII_PATTERNS = {
        "email": r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}',
        "ssn": r'\b\d{3}-\d{2}-\d{4}\b',
        "phone": r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b',
        "credit_card": r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b',
        "ip_address": r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b',
    }
    
    COMPLIANCE_CHECKS = {
        "gdpr": {
            "data_retention": "Check for data retention/deletion mechanisms",
            "consent": "Check for user consent collection",
            "data_portability": "Check for data export capability",
            "right_to_forget": "Check for data deletion endpoints",
        },
        "hipaa": {
            "encryption": "Check for data encryption at rest and in transit",
            "access_control": "Check for role-based access control",
            "audit_logging": "Check for audit trail logging",
        },
        "soc2": {
            "access_control": "Check for authentication and authorization",
            "monitoring": "Check for system monitoring and alerting",
            "encryption": "Check for encryption in transit (TLS/SSL)",
        },
    }
    
    def scan_for_pii(self, code: str) -> List[Dict]:
        """Scan code for hardcoded PII patterns."""
        findings = []
        for pii_type, pattern in self.PII_PATTERNS.items():
            matches = re.findall(pattern, code)
            if matches:
                # Filter out common false positives
                real_matches = [m for m in matches if not m.startswith("example") 
                              and "test" not in m.lower() and "0.0.0.0" not in m]
                if real_matches:
                    findings.append({
                        "type": pii_type,
                        "count": len(real_matches),
                        "samples": real_matches[:3],
                        "severity": "critical" if pii_type in ("ssn", "credit_card") else "high",
                        "remediation": f"Remove hardcoded {pii_type} data. Use environment variables or secrets manager.",
                    })
        return findings
    
    def check_encryption(self, code: str) -> List[Dict]:
        """Check for encryption-related issues."""
        findings = []
        
        # Check for HTTP instead of HTTPS
        http_urls = re.findall(r'http://[^\s"\']+', code)
        if http_urls:
            findings.append({
                "framework": "soc2", "requirement": "encryption_in_transit",
                "status": "non_compliant", "severity": "high",
                "issue": f"Found {len(http_urls)} HTTP (non-encrypted) URLs",
                "remediation": "Use HTTPS for all external connections",
            })
        
        # Check for weak crypto
        weak_crypto = re.findall(r'(md5|sha1|DES|RC4)', code, re.IGNORECASE)
        if weak_crypto:
            findings.append({
                "framework": "general", "requirement": "strong_encryption",
                "status": "non_compliant", "severity": "critical",
                "issue": f"Weak cryptographic algorithm detected: {', '.join(set(weak_crypto))}",
                "remediation": "Use SHA-256+ for hashing, AES-256 for encryption",
            })
        
        return findings
    
    def audit(self, code: str, frameworks: List[str] = None) -> Dict:
        """Full compliance audit."""
        frameworks = frameworks or ["gdpr", "soc2"]
        pii = self.scan_for_pii(code)
        crypto = self.check_encryption(code)
        
        all_findings = pii + crypto
        critical = sum(1 for f in all_findings if f.get("severity") == "critical")
        high = sum(1 for f in all_findings if f.get("severity") == "high")
        
        score = max(0, 100 - (critical * 25) - (high * 15))
        
        return {
            "frameworks_checked": frameworks,
            "pii_findings": pii,
            "encryption_findings": crypto,
            "compliance_score": score,
            "risk_level": "critical" if critical > 0 else "high" if high > 0 else "low",
            "total_findings": len(all_findings),
        }


class IdentityTrustArchitect:
    """Designs agent identity and trust systems."""
    
    TRUST_LEVELS = {
        "untrusted": 0,
        "basic": 1,
        "verified": 2,
        "trusted": 3,
        "privileged": 4,
    }
    
    def design_identity_model(self, agents: List[Dict]) -> Dict:
        """Design an identity model for a set of agents."""
        identity_model = {
            "agents": [],
            "auth_mechanism": "JWT with RSA-256 signing",
            "token_format": "JWT",
            "rotation_policy": "24h token expiry, 7d refresh token",
        }
        
        for agent in agents:
            identity_model["agents"].append({
                "id": agent.get("id", agent.get("name", "unknown")),
                "role": agent.get("role", "worker"),
                "permissions": agent.get("permissions", ["read"]),
                "trust_level": agent.get("trust_level", "basic"),
                "trust_score": self.TRUST_LEVELS.get(agent.get("trust_level", "basic"), 1),
            })
        
        return identity_model


if __name__ == "__main__":
    checker = LegalComplianceChecker()
    test_code = '''
    email = "user@company.com"
    url = "http://api.example.com/data"
    password = hashlib.md5(raw_password).hexdigest()
    '''
    result = checker.audit(test_code)
    print(f"Score: {result['compliance_score']}/100, Risk: {result['risk_level']}")
    print(f"Findings: {result['total_findings']}")
