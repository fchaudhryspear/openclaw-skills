#!/usr/bin/env python3
"""
NexDev Phase 3.2 — Proactive Self-Healing
===========================================
Monitors deployed apps, diagnoses issues from logs/metrics,
generates fixes, and deploys them (with approval in supervised mode).
"""

import re
import json
from typing import Dict, List, Optional
from datetime import datetime
from dataclasses import dataclass, field, asdict


@dataclass
class HealthIncident:
    id: str
    severity: str  # critical, warning, info
    type: str  # error_spike, latency, memory, crash, dependency
    description: str
    detected_at: str
    source: str  # log, metric, healthcheck
    raw_data: str = ""
    diagnosis: str = ""
    proposed_fix: str = ""
    fix_code: str = ""
    status: str = "detected"  # detected, diagnosing, fix_proposed, fix_applied, resolved, ignored
    auto_fixable: bool = False


class SelfHealingEngine:
    """Monitors and auto-heals deployed applications."""
    
    # Known error patterns and their fixes
    ERROR_PATTERNS = {
        "connection_pool_exhausted": {
            "patterns": [r"connection pool.*exhaust", r"too many connections", r"FATAL.*connection limit"],
            "severity": "critical",
            "type": "dependency",
            "diagnosis": "Database connection pool exhausted — too many concurrent connections",
            "fix": "Increase pool size or add connection timeout",
            "auto_fixable": True,
            "fix_template": "DATABASE_POOL_SIZE={new_size}  # Was {old_size}",
        },
        "oom_kill": {
            "patterns": [r"OOMKill", r"out of memory", r"memory limit exceeded", r"MemoryError"],
            "severity": "critical",
            "type": "memory",
            "diagnosis": "Application running out of memory — likely memory leak or undersized container",
            "fix": "Increase memory limit, investigate memory leak",
            "auto_fixable": False,
        },
        "unhandled_exception": {
            "patterns": [r"unhandled.*exception", r"uncaught.*error", r"Traceback.*most recent"],
            "severity": "warning",
            "type": "error_spike",
            "diagnosis": "Unhandled exception in application code",
            "fix": "Add error handling around the failing code path",
            "auto_fixable": True,
        },
        "timeout": {
            "patterns": [r"timeout.*exceeded", r"request.*timed out", r"504.*gateway"],
            "severity": "warning",
            "type": "latency",
            "diagnosis": "Request timeouts — upstream service or database slow",
            "fix": "Increase timeout, add circuit breaker, check upstream health",
            "auto_fixable": True,
            "fix_template": "REQUEST_TIMEOUT={new_timeout}  # Was {old_timeout}",
        },
        "rate_limited": {
            "patterns": [r"429.*too many", r"rate.*limit", r"throttl"],
            "severity": "warning",
            "type": "dependency",
            "diagnosis": "External API rate limiting — too many requests",
            "fix": "Add request queuing, implement exponential backoff",
            "auto_fixable": True,
        },
        "ssl_cert_expiry": {
            "patterns": [r"certificate.*expir", r"ssl.*cert.*invalid", r"CERTIFICATE_VERIFY_FAILED"],
            "severity": "critical",
            "type": "dependency",
            "diagnosis": "SSL certificate expired or invalid",
            "fix": "Renew SSL certificate",
            "auto_fixable": False,
        },
        "disk_full": {
            "patterns": [r"no space left", r"disk.*full", r"ENOSPC"],
            "severity": "critical",
            "type": "crash",
            "diagnosis": "Disk space exhausted",
            "fix": "Clean up old logs/data, increase volume size",
            "auto_fixable": True,
            "fix_template": "find /var/log -name '*.log' -mtime +7 -delete",
        },
        "dependency_down": {
            "patterns": [r"ECONNREFUSED", r"connection refused", r"service unavailable", r"503"],
            "severity": "warning",
            "type": "dependency",
            "diagnosis": "Downstream dependency is unreachable",
            "fix": "Check dependency health, enable circuit breaker",
            "auto_fixable": True,
        },
    }
    
    def __init__(self):
        self.incidents: Dict[str, HealthIncident] = {}
        self.incident_counter = 0
    
    def analyze_logs(self, log_text: str, source: str = "app") -> List[HealthIncident]:
        """Analyze log output for known error patterns."""
        incidents = []
        
        for pattern_name, config in self.ERROR_PATTERNS.items():
            for pattern in config["patterns"]:
                if re.search(pattern, log_text, re.IGNORECASE):
                    self.incident_counter += 1
                    incident = HealthIncident(
                        id=f"INC-{self.incident_counter:04d}",
                        severity=config["severity"],
                        type=config["type"],
                        description=config["diagnosis"],
                        detected_at=datetime.now().isoformat(),
                        source=source,
                        raw_data=log_text[:500],
                        diagnosis=config["diagnosis"],
                        proposed_fix=config["fix"],
                        auto_fixable=config.get("auto_fixable", False),
                    )
                    
                    if config.get("fix_template"):
                        incident.fix_code = config["fix_template"]
                    
                    incidents.append(incident)
                    self.incidents[incident.id] = incident
                    break  # One incident per pattern group
        
        return incidents
    
    def analyze_metrics(self, metrics: Dict) -> List[HealthIncident]:
        """Analyze application metrics for anomalies."""
        incidents = []
        
        # Error rate check
        error_rate = metrics.get("error_rate", 0)
        if error_rate > 0.05:  # >5% error rate
            self.incident_counter += 1
            incidents.append(HealthIncident(
                id=f"INC-{self.incident_counter:04d}",
                severity="critical" if error_rate > 0.2 else "warning",
                type="error_spike",
                description=f"Error rate is {error_rate*100:.1f}% (threshold: 5%)",
                detected_at=datetime.now().isoformat(),
                source="metrics",
                diagnosis=f"Error rate spike: {error_rate*100:.1f}%",
                proposed_fix="Investigate error logs, check recent deployments",
            ))
        
        # Latency check
        p95_latency = metrics.get("p95_latency_ms", 0)
        if p95_latency > 2000:  # >2s p95
            self.incident_counter += 1
            incidents.append(HealthIncident(
                id=f"INC-{self.incident_counter:04d}",
                severity="warning",
                type="latency",
                description=f"P95 latency is {p95_latency}ms (threshold: 2000ms)",
                detected_at=datetime.now().isoformat(),
                source="metrics",
                diagnosis=f"High latency: {p95_latency}ms p95",
                proposed_fix="Check database queries, add caching, review recent changes",
            ))
        
        # Memory check
        memory_pct = metrics.get("memory_usage_pct", 0)
        if memory_pct > 85:
            self.incident_counter += 1
            incidents.append(HealthIncident(
                id=f"INC-{self.incident_counter:04d}",
                severity="warning" if memory_pct < 95 else "critical",
                type="memory",
                description=f"Memory usage at {memory_pct}%",
                detected_at=datetime.now().isoformat(),
                source="metrics",
                diagnosis=f"High memory usage: {memory_pct}%",
                proposed_fix="Investigate memory leaks, increase container memory, restart pod",
                auto_fixable=True,
                fix_code="kubectl rollout restart deployment/app",
            ))
        
        for inc in incidents:
            self.incidents[inc.id] = inc
        
        return incidents
    
    def get_remediation_plan(self, incident_id: str) -> Dict:
        """Get detailed remediation plan for an incident."""
        incident = self.incidents.get(incident_id)
        if not incident:
            return {"error": "Incident not found"}
        
        plan = {
            "incident": asdict(incident),
            "steps": [],
            "estimated_time": "5-15 minutes",
            "requires_approval": not incident.auto_fixable,
        }
        
        # Generate remediation steps based on type
        if incident.type == "error_spike":
            plan["steps"] = [
                "1. Check recent deployments for rollback candidates",
                "2. Review error logs for root cause",
                "3. If deployment-related: initiate rollback",
                "4. If code bug: generate hotfix",
                "5. Deploy fix or rollback",
                "6. Monitor error rate for 15 minutes",
            ]
        elif incident.type == "latency":
            plan["steps"] = [
                "1. Check database slow query log",
                "2. Review cache hit rates",
                "3. Check upstream dependency latency",
                "4. If DB: add missing indexes or optimize queries",
                "5. If cache: warm cache or increase TTL",
                "6. Monitor p95 latency for 15 minutes",
            ]
        elif incident.type == "memory":
            plan["steps"] = [
                "1. Check for memory leak indicators",
                "2. Review recent code changes",
                "3. If leak found: generate fix",
                "4. If not: increase memory limit",
                "5. Restart affected pods/containers",
                "6. Monitor memory for 30 minutes",
            ]
        elif incident.type == "dependency":
            plan["steps"] = [
                "1. Check dependency health endpoints",
                "2. If down: enable circuit breaker",
                "3. If rate-limited: reduce request rate",
                "4. Add retry with exponential backoff",
                "5. Alert dependency team if external",
            ]
        
        return plan
    
    def format_incident_report(self, incidents: List[HealthIncident] = None) -> str:
        """Format incident report for chat."""
        incidents = incidents or list(self.incidents.values())
        if not incidents:
            return "🟢 **Self-Healing Monitor:** All systems healthy"
        
        emoji = {"critical": "🔴", "warning": "🟡", "info": "🔵"}
        
        lines = ["🏥 **Self-Healing Incident Report**", ""]
        
        for inc in sorted(incidents, key=lambda x: ["critical","warning","info"].index(x.severity)):
            fix_badge = " [AUTO-FIXABLE]" if inc.auto_fixable else ""
            lines.append(f"{emoji.get(inc.severity, '⚪')} **{inc.id}** [{inc.severity}]{fix_badge}")
            lines.append(f"  Type: {inc.type} | Source: {inc.source}")
            lines.append(f"  {inc.description}")
            lines.append(f"  💡 Fix: {inc.proposed_fix}")
            if inc.fix_code:
                lines.append(f"  📝 `{inc.fix_code}`")
            lines.append("")
        
        auto_fixable = sum(1 for i in incidents if i.auto_fixable)
        lines.append(f"**Summary:** {len(incidents)} incidents, {auto_fixable} auto-fixable")
        
        return "\n".join(lines)


if __name__ == "__main__":
    healer = SelfHealingEngine()
    
    # Test log analysis
    logs = """
    2026-03-08 00:30:15 ERROR connection pool exhausted - max connections reached
    2026-03-08 00:30:16 FATAL request timed out after 30000ms
    2026-03-08 00:30:17 WARNING 429 Too Many Requests from external API
    """
    
    incidents = healer.analyze_logs(logs)
    
    # Test metric analysis
    metrics_incidents = healer.analyze_metrics({
        "error_rate": 0.08,
        "p95_latency_ms": 3500,
        "memory_usage_pct": 92,
    })
    
    all_incidents = incidents + metrics_incidents
    print(healer.format_incident_report(all_incidents))
    
    # Get remediation plan for first incident
    if all_incidents:
        plan = healer.get_remediation_plan(all_incidents[0].id)
        print(f"\nRemediation plan for {all_incidents[0].id}:")
        for step in plan["steps"]:
            print(f"  {step}")
    
    print(f"\n✅ Self-Healing Engine tested — {len(all_incidents)} incidents detected")
