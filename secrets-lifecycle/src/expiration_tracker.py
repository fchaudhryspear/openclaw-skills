"""
Expiration Tracker - Monitor API key expirations and generate alerts
Generates warnings at 30, 7, and 1 day before expiration.
"""

import os
import json
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from dataclasses import dataclass, asdict
from enum import Enum


class AlertSeverity(Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    URGENT = "urgent"


@dataclass
class ExpirationAlert:
    """Represents an expiration alert."""
    secret_id: str
    secret_name: str
    service: str
    expiration_date: datetime
    days_remaining: int
    severity: AlertSeverity
    message: str
    created_at: datetime
    
    def to_dict(self) -> Dict:
        return {
            'secret_id': self.secret_id,
            'secret_name': self.secret_name,
            'service': self.service,
            'expiration_date': self.expiration_date.isoformat(),
            'days_remaining': self.days_remaining,
            'severity': self.severity.value,
            'message': self.message,
            'created_at': self.created_at.isoformat()
        }


class ExpirationTracker:
    """Tracks secret expirations and generates alerts."""
    
    def __init__(self, secrets_manager, alerts_file: str):
        self.sm = secrets_manager
        self.alerts_file = alerts_file
        self._ensure_alerts_file()
        
    def _ensure_alerts_file(self):
        """Create alerts file if it doesn't exist."""
        if not os.path.exists(self.alerts_file):
            # Initialize with secure permissions
            open(self.alerts_file, 'a').close()
            os.chmod(self.alerts_file, 0o600)
    
    def _load_alerts(self) -> List[Dict]:
        """Load existing alerts from file."""
        if os.path.exists(self.alerts_file):
            with open(self.alerts_file, 'r') as f:
                return [json.loads(line) for line in f if line.strip()]
        return []
    
    def _save_alert(self, alert: ExpirationAlert):
        """Save a new alert to file."""
        with open(self.alerts_file, 'a') as f:
            f.write(json.dumps(alert.to_dict()) + '\n')
    
    def calculate_severity(self, days_remaining: int) -> AlertSeverity:
        """Determine alert severity based on days remaining."""
        if days_remaining <= 0:
            return AlertSeverity.URGENT
        elif days_remaining <= 1:
            return AlertSeverity.CRITICAL
        elif days_remaining <= 7:
            return AlertSeverity.WARNING
        else:
            return AlertSeverity.INFO
    
    def generate_alert_message(self, days_remaining: int, secret_name: str, service: str) -> str:
        """Generate human-readable alert message."""
        if days_remaining <= 0:
            return f"🚨 EXPIRED: {secret_name} ({service}) expired {abs(days_remaining)} day(s) ago!"
        elif days_remaining == 1:
            return f"🔴 URGENT: {secret_name} ({service}) expires TOMORROW!"
        elif days_remaining <= 7:
            return f"🟠 WARNING: {secret_name} ({service}) expires in {days_remaining} days"
        else:
            return f"🟡 REMINDER: {secret_name} ({service}) expires in {days_remaining} days"
    
    def check_expirations(self, force_check: bool = False) -> List[ExpirationAlert]:
        """
        Check all secrets for upcoming expirations.
        Generates alerts at 30, 7, and 1 day thresholds.
        
        Args:
            force_check: If True, check all secrets regardless of last alert
            
        Returns:
            List of newly generated alerts
        """
        now = datetime.now()
        new_alerts = []
        existing_alerts = self._load_alerts()
        
        # Track which alerts we've already sent (last 24h per threshold)
        recent_alerts = {}
        for alert in existing_alerts:
            key = (alert['secret_id'], alert['severity'])
            alert_time = datetime.fromisoformat(alert['created_at'])
            if (now - alert_time).total_seconds() < 86400:  # Within 24 hours
                recent_alerts[key] = alert_time
        
        # Get all active secrets
        secrets_list = self.sm.list_secrets(include_deleted=False)
        
        for secret in secrets_list:
            if not secret.get('expiration_date'):
                continue
                
            exp_date = datetime.fromisoformat(secret['expiration_date'])
            days_remaining = (exp_date - now).days
            
            # Determine which threshold this falls into
            threshold = None
            if days_remaining <= 0:
                threshold = AlertSeverity.URGENT
            elif days_remaining == 1:
                threshold = AlertSeverity.CRITICAL
            elif days_remaining <= 7:
                threshold = AlertSeverity.WARNING
            elif days_remaining <= 30:
                threshold = AlertSeverity.INFO
            
            if threshold is None:
                continue  # More than 30 days out, no alert needed
            
            # Check if we've already alerted today for this threshold
            alert_key = (secret['id'], threshold)
            if alert_key in recent_alerts and not force_check:
                continue  # Already alerted within 24h
            
            # Generate alert
            alert = ExpirationAlert(
                secret_id=secret['id'],
                secret_name=secret['name'],
                service=secret['service'],
                expiration_date=exp_date,
                days_remaining=days_remaining,
                severity=threshold,
                message=self.generate_alert_message(days_remaining, secret['name'], secret['service']),
                created_at=now
            )
            
            self._save_alert(alert)
            new_alerts.append(alert)
        
        return new_alerts
    
    def get_all_alerts(self, 
                       since: Optional[datetime] = None,
                       severity: Optional[AlertSeverity] = None,
                       include_resolved: bool = False) -> List[Dict]:
        """Get all alerts with optional filtering."""
        alerts = self._load_alerts()
        
        if since:
            alerts = [a for a in alerts if datetime.fromisoformat(a['created_at']) >= since]
        
        if severity:
            alerts = [a for a in alerts if a['severity'] == severity.value]
        
        # Sort by created date descending
        alerts.sort(key=lambda x: x['created_at'], reverse=True)
        
        return alerts
    
    def get_current_status(self) -> Dict:
        """Get current expiration status summary."""
        expiring_soon = self.sm.get_expiring_secrets(days=30)
        now = datetime.now()
        
        status = {
            'total_active_secrets': len([s for s in self.sm.list_secrets() if s.get('status') != 'deleted']),
            'expired': [],
            'expiring_today': [],
            'expiring_7_days': [],
            'expiring_30_days': [],
            'no_expiration_set': [],
            'summary': {}
        }
        
        for secret in self.sm.list_secrets():
            if secret.get('status') == 'deleted':
                continue
                
            if not secret.get('expiration_date'):
                status['no_expiration_set'].append({
                    'id': secret['id'],
                    'name': secret['name'],
                    'service': secret['service']
                })
                continue
                
            exp_date = datetime.fromisoformat(secret['expiration_date'])
            days_remaining = (exp_date - now).days
            
            entry = {
                'id': secret['id'],
                'name': secret['name'],
                'service': secret['service'],
                'expiration_date': secret['expiration_date'],
                'days_remaining': days_remaining
            }
            
            if days_remaining < 0:
                status['expired'].append(entry)
            elif days_remaining == 0:
                status['expiring_today'].append(entry)
            elif days_remaining <= 7:
                status['expiring_7_days'].append(entry)
            elif days_remaining <= 30:
                status['expiring_30_days'].append(entry)
        
        status['summary'] = {
            'expired_count': len(status['expired']),
            'expiring_today_count': len(status['expiring_today']),
            'expiring_7_days_count': len(status['expiring_7_days']),
            'expiring_30_days_count': len(status['expiring_30_days']),
            'no_expiration_count': len(status['no_expiration_set'])
        }
        
        return status
    
    def run_daily_check(self) -> Dict:
        """Run daily expiration check and return summary."""
        new_alerts = self.check_expirations()
        status = self.get_current_status()
        
        return {
            'check_time': datetime.now().isoformat(),
            'new_alerts_generated': len(new_alerts),
            'alerts': [a.to_dict() for a in new_alerts],
            'status_summary': status['summary']
        }
