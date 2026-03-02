"""
Compliance Audit Logger - Track all secret lifecycle events for compliance
Generates audit reports for security audits and compliance reviews.
"""

import os
import json
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Callable
from dataclasses import dataclass
import hashlib


@dataclass
class AuditEvent:
    """Represents a single audit log entry."""
    timestamp: str
    event_type: str
    secret_id: str
    user_id: str  # System or user who performed action
    action: str
    details: Dict
    ip_address: Optional[str] = None
    session_id: Optional[str] = None
    
    def to_dict(self) -> Dict:
        return {
            'timestamp': self.timestamp,
            'event_type': self.event_type,
            'secret_id': self.secret_id,
            'user_id': self.user_id,
            'action': self.action,
            'details': self.details,
            'ip_address': self.ip_address,
            'session_id': self.session_id
        }
    
    def to_log_line(self) -> str:
        """Convert to JSON log line format."""
        return json.dumps(self.to_dict())


class ComplianceAuditLogger:
    """Comprehensive audit logging for secrets lifecycle."""
    
    COMPLIANCE_EVENTS = [
        'SECRET_CREATED',
        'SECRET_ACCESSED',
        'SECRET_UPDATED',
        'SECRET_ROTATED',
        'SECRET_DELETED',
        'SECRET_EXPIRED',
        'EXPORT_ATTEMPTED',
        'AUTH_FAILED',
        'SETTINGS_CHANGED'
    ]
    
    def __init__(self, audit_file: str):
        self.audit_file = audit_file
        self._ensure_audit_file()
        
    def _ensure_audit_file(self):
        """Create audit file with secure permissions."""
        if not os.path.exists(self.audit_file):
            open(self.audit_file, 'a').close()
            os.chmod(self.audit_file, 0o600)
    
    def log_event(
        self,
        event_type: str,
        secret_id: str,
        action: str,
        details: Dict,
        user_id: str = 'system',
        ip_address: Optional[str] = None,
        session_id: Optional[str] = None
    ) -> AuditEvent:
        """Log a compliance event."""
        if event_type not in self.COMPLIANCE_EVENTS:
            event_type = 'OTHER'
            
        event = AuditEvent(
            timestamp=datetime.now().isoformat(),
            event_type=event_type,
            secret_id=secret_id,
            user_id=user_id,
            action=action,
            details=details,
            ip_address=ip_address,
            session_id=session_id
        )
        
        # Append to audit log (append-only)
        with open(self.audit_file, 'a') as f:
            f.write(event.to_log_line() + '\n')
        
        return event
    
    def get_events(
        self,
        since: Optional[datetime] = None,
        until: Optional[datetime] = None,
        event_types: Optional[List[str]] = None,
        secret_ids: Optional[List[str]] = None,
        user_ids: Optional[List[str]] = None,
        actions: Optional[List[str]] = None
    ) -> List[AuditEvent]:
        """Query audit log with filters."""
        events = []
        
        with open(self.audit_file, 'r') as f:
            for line in f:
                if not line.strip():
                    continue
                    
                try:
                    data = json.loads(line)
                    event = AuditEvent(**data)
                    
                    # Apply filters
                    if since and datetime.fromisoformat(event.timestamp) < since:
                        continue
                    if until and datetime.fromisoformat(event.timestamp) > until:
                        continue
                    if event_types and event.event_type not in event_types:
                        continue
                    if secret_ids and event.secret_id not in secret_ids:
                        continue
                    if user_ids and event.user_id not in user_ids:
                        continue
                    if actions and event.action not in actions:
                        continue
                        
                    events.append(event)
                except json.JSONDecodeError:
                    continue
        
        return sorted(events, key=lambda x: x.timestamp, reverse=True)
    
    def generate_compliance_report(
        self,
        start_date: datetime,
        end_date: datetime,
        include_summary: bool = True,
        include_details: bool = True
    ) -> Dict:
        """Generate a compliance audit report for a date range."""
        events = self.get_events(since=start_date, until=end_date)
        
        report = {
            'report_id': hashlib.sha256(
                f"{start_date.isoformat()}-{end_date.isoformat()}".encode()
            ).hexdigest()[:16],
            'generated_at': datetime.now().isoformat(),
            'period': {
                'start': start_date.isoformat(),
                'end': end_date.isoformat()
            },
            'total_events': len(events)
        }
        
        if include_summary:
            # Event type summary
            event_counts = {}
            for event in events:
                event_counts[event.event_type] = event_counts.get(event.event_type, 0) + 1
                
            report['summary'] = {
                'events_by_type': event_counts,
                'unique_secrets_accessed': len(set(e.secret_id for e in events)),
                'unique_users': len(set(e.user_id for e in events)),
                'rotation_count': event_counts.get('SECRET_ROTATED', 0),
                'access_count': event_counts.get('SECRET_ACCESSED', 0)
            }
        
        if include_details:
            # Group by secret for detailed view
            by_secret = {}
            for event in events:
                if event.secret_id not in by_secret:
                    by_secret[event.secret_id] = []
                by_secret[event.secret_id].append(event.to_dict())
            
            report['by_secret'] = by_secret
            
            # Timeline of events
            report['timeline'] = [e.to_dict() for e in events]
        
        return report
    
    def generate_rotation_history(self, days: int = 90) -> Dict:
        """Generate secret rotation history report."""
        since = datetime.now() - timedelta(days=days)
        events = self.get_events(
            since=since,
            event_types=['SECRET_ROTATED', 'SECRET_CREATED', 'SECRET_DELETED']
        )
        
        rotations = []
        for event in events:
            if event.event_type == 'SECRET_ROTATED':
                rotations.append({
                    'timestamp': event.timestamp,
                    'secret_id': event.secret_id,
                    'user': event.user_id,
                    'reason': event.details.get('reason', 'scheduled'),
                    'old_metadata': event.details.get('old_metadata', {})
                })
        
        return {
            'period_days': days,
            'total_rotations': len(rotations),
            'rotations': sorted(rotations, key=lambda x: x['timestamp'], reverse=True)
        }
    
    def detect_anomalies(self, lookback_days: int = 30) -> Dict:
        """Detect potential security anomalies in audit logs."""
        since = datetime.now() - timedelta(days=lookback_days)
        events = self.get_events(since=since)
        
        anomalies = []
        
        # Check for multiple failed auth attempts
        auth_fails = [e for e in events if e.event_type == 'AUTH_FAILED']
        if len(auth_fails) > 5:
            anomalies.append({
                'type': 'HIGH_AUTH_FAILURES',
                'count': len(auth_fails),
                'severity': 'medium',
                'description': f'{len(auth_fails)} authentication failures in {lookback_days} days'
            })
        
        # Check for off-hours access patterns
        off_hours = []
        for event in events:
            if event.action == 'SECRET_ACCESSED':
                hour = datetime.fromisoformat(event.timestamp).hour
                if hour < 6 or hour > 22:
                    off_hours.append(event)
        
        if len(off_hours) > 10:
            anomalies.append({
                'type': 'OFF_HOURS_ACCESS',
                'count': len(off_hours),
                'severity': 'low',
                'description': f'{len(off_hours)} accesses outside business hours (6am-10pm)'
            })
        
        # Check for secrets accessed without rotation
        accessed_secrets = set(e.secret_id for e in events if e.action == 'SECRET_ACCESSED')
        rotated_secrets = set(e.secret_id for e in events if e.event_type == 'SECRET_ROTATED')
        stale = accessed_secrets - rotated_secrets
        
        if len(stale) > 5:
            anomalies.append({
                'type': 'STALE_SECRETS',
                'count': len(stale),
                'severity': 'medium',
                'description': f'{len(stale)} secrets accessed but not rotated in {lookback_days} days'
            })
        
        return {
            'anomaly_count': len(anomalies),
            'anomalies': anomalies,
            'check_period_days': lookback_days,
            'checked_at': datetime.now().isoformat()
        }
    
    def export_for_audit(self, output_path: str, days: int = 365):
        """Export complete audit log for external audit review."""
        since = datetime.now() - timedelta(days=days)
        events = self.get_events(since=since)
        
        export_data = {
            'export_version': '1.0',
            'exported_at': datetime.now().isoformat(),
            'period_days': days,
            'total_records': len(events),
            'checksum': hashlib.sha256(
                ''.join(e.to_log_line() for e in events).encode()
            ).hexdigest(),
            'events': [e.to_dict() for e in events]
        }
        
        with open(output_path, 'w') as f:
            json.dump(export_data, f, indent=2)
        
        os.chmod(output_path, 0o600)
        return output_path
