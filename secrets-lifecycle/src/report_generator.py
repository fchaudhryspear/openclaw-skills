"""
Report Generator - Generate rotation calendars, expiration trackers, and compliance logs
Delivers formatted reports for human review and automated processing.
"""

import os
import json
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from pathlib import Path


class ReportGenerator:
    """Generate formatted reports for secrets lifecycle management."""
    
    def __init__(self, reports_dir: str):
        self.reports_dir = reports_dir
        os.makedirs(reports_dir, mode=0o700, exist_ok=True)
        
    def _safe_filename(self, name: str) -> str:
        """Create safe filename from name."""
        return ''.join(c if c.isalnum() or c in '-_' else '_' for c in name)
    
    def generate_expiration_tracker_report(
        self,
        status: Dict,
        alerts: List[Dict],
        output_format: str = 'text'
    ) -> str:
        """Generate expiration tracking report/dashboard."""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        if output_format == 'json':
            return json.dumps({
                'generated_at': timestamp,
                'status': status,
                'alerts': alerts
            }, indent=2)
        
        # Text/ASCII format
        lines = []
        lines.append("=" * 60)
        lines.append("SECRETS EXPIRATION TRACKER")
        lines.append(f"Generated: {timestamp}")
        lines.append("=" * 60)
        lines.append("")
        
        summary = status.get('summary', {})
        
        # Summary statistics
        lines.append("SUMMARY")
        lines.append("-" * 40)
        lines.append(f"Total Active Secrets:     {summary.get('total_active_secrets', 0)}")
        lines.append(f"🚨 Expired:               {summary.get('expired_count', 0)}")
        lines.append(f"🔴 Expiring Today:        {summary.get('expiring_today_count', 0)}")
        lines.append(f"🟠 Expiring (7 days):     {summary.get('expiring_7_days_count', 0)}")
        lines.append(f"🟡 Expiring (30 days):    {summary.get('expiring_30_days_count', 0)}")
        lines.append(f"⚪ No Expiration Set:     {summary.get('no_expiration_count', 0)}")
        lines.append("")
        
        # Expired secrets
        if status.get('expired'):
            lines.append("🚨 EXPIRED SECRETS (Immediate Action Required)")
            lines.append("-" * 40)
            for secret in sorted(status['expired'], key=lambda x: x['days_remaining']):
                lines.append(f"  • {secret['name']} ({secret['service']})")
                lines.append(f"    ID: {secret['id']} | Expires: {secret['expiration_date']}")
                lines.append(f"    Days Overdue: {abs(secret['days_remaining'])}")
                lines.append("")
        
        # Expiring today
        if status.get('expiring_today'):
            lines.append("🔴 EXPIRING TODAY")
            lines.append("-" * 40)
            for secret in status['expiring_today']:
                lines.append(f"  ⚠️ {secret['name']} ({secret['service']})")
                lines.append(f"    ID: {secret['id']}")
                lines.append("")
        
        # Expiring within 7 days
        if status.get('expiring_7_days'):
            lines.append("🟠 EXPIRING WITHIN 7 DAYS")
            lines.append("-" * 40)
            for secret in sorted(status['expiring_7_days'], key=lambda x: x['days_remaining']):
                bar = self._urgency_bar(secret['days_remaining'], 7)
                lines.append(f"  [{bar}] {secret['name']} ({secret['service']})")
                lines.append(f"    ID: {secret['id']} | {secret['days_remaining']} days remaining")
                lines.append("")
        
        # Expiring within 30 days
        if status.get('expiring_30_days'):
            lines.append("🟡 EXPIRING WITHIN 30 DAYS")
            lines.append("-" * 40)
            for secret in sorted(status['expiring_30_days'], key=lambda x: x['days_remaining']):
                bar = self._urgency_bar(secret['days_remaining'], 30)
                lines.append(f"  [{bar}] {secret['name']} ({secret['service']})")
                lines.append(f"    ID: {secret['id']} | {secret['days_remaining']} days remaining")
                lines.append("")
        
        # No expiration set
        if status.get('no_expiration_set'):
            lines.append("⚪ NO EXPIRATION DATE SET")
            lines.append("-" * 40)
            lines.append("  Consider adding expiration dates for:")
            for secret in status['no_expiration_set']:
                lines.append(f"    • {secret['name']} ({secret['service']})")
            lines.append("")
        
        # Recent alerts
        if alerts:
            lines.append("RECENT ALERTS")
            lines.append("-" * 40)
            for alert in alerts[:10]:  # Show last 10
                severity_icon = {
                    'urgent': '🚨',
                    'critical': '🔴',
                    'warning': '🟠',
                    'info': '🟡'
                }.get(alert.get('severity', 'info'), 'ℹ️')
                lines.append(f"  {severity_icon} {alert.get('message', 'Alert')}")
            lines.append("")
        
        lines.append("=" * 60)
        lines.append("End of Report")
        lines.append("=" * 60)
        
        return '\n'.join(lines)
    
    def _urgency_bar(self, days: int, max_days: int) -> str:
        """Create urgency progress bar."""
        filled = int((max_days - days) / max_days * 20)
        empty = 20 - filled
        bars = '█' * filled + '░' * empty
        return bars
    
    def generate_rotation_calendar(
        self,
        secrets_list: List[Dict],
        view: str = 'monthly',
        months_ahead: int = 3
    ) -> str:
        """Generate a rotation schedule calendar view."""
        now = datetime.now()
        
        if view == 'calendar':
            return self._generate_calendar_view(secrets_list, now, months_ahead)
        else:
            return self._generate_table_view(secrets_list, now)
    
    def _generate_calendar_view(
        self,
        secrets_list: List[Dict],
        start_date: datetime,
        months_ahead: int
    ) -> str:
        """Generate ASCII calendar view of rotations."""
        lines = []
        lines.append("=" * 70)
        lines.append("SECRET ROTATION CALENDAR")
        lines.append(f"View: Next {months_ahead} months | Generated: {start_date.strftime('%Y-%m-%d')}")
        lines.append("=" * 70)
        lines.append("")
        
        # Build rotation schedule
        rotations_by_date = {}
        for secret in secrets_list:
            next_rot = secret.get('next_rotation')
            if not next_rot:
                continue
                
            rot_date = datetime.fromisoformat(next_rot)
            key = rot_date.strftime('%Y-%m-%d')
            
            if key not in rotations_by_date:
                rotations_by_date[key] = []
            rotations_by_date[key].append({
                'name': secret['name'],
                'service': secret['service'],
                'id': secret['id']
            })
        
        # Sort by date
        sorted_dates = sorted(rotations_by_date.keys())
        
        # Group by month and display
        current_month = start_date.strftime('%Y-%m')
        month_data = {}
        
        for date_key in sorted_dates:
            month = date_key[:7]  # YYYY-MM
            if month not in month_data:
                month_data[month] = []
            month_data[month].append((date_key, rotations_by_date[date_key]))
        
        # Display each month
        for month_idx in range(months_ahead):
            target_month = (start_date + timedelta(days=30*month_idx)).strftime('%Y-%m')
            
            if target_month not in month_data:
                continue
            
            # Month header
            month_name = datetime.strptime(target_month + "-01", '%Y-%m-%d').strftime('%B %Y')
            lines.append("")
            lines.append(f"▶ {month_name}")
            lines.append("-" * 50)
            
            for date_key, items in month_data[target_month]:
                day_num = date_key[8:]
                day_name = datetime.strptime(date_key, '%Y-%m-%d').strftime('%A')
                
                # Color indicator based on urgency
                days_until = (datetime.strptime(date_key, '%Y-%m-%d') - start_date).days
                if days_until <= 7:
                    indicator = "🔴"
                elif days_until <= 30:
                    indicator = "🟠"
                else:
                    indicator = "🟢"
                
                lines.append(f"  {indicator} {day_num} ({day_name[:3]})")
                for item in items:
                    lines.append(f"      • {item['name']} ({item['service']})")
                    lines.append(f"        ID: {item['id'][:8]}...")
                lines.append("")
        
        lines.append("=" * 70)
        lines.append("Legend: 🔴 < 7 days | 🟠 < 30 days | 🟢 > 30 days")
        lines.append("=" * 70)
        
        return '\n'.join(lines)
    
    def _generate_table_view(self, secrets_list: List[Dict], now: datetime) -> str:
        """Generate table view of rotation schedule."""
        lines = []
        lines.append("=" * 90)
        lines.append("ROTATION SCHEDULE TABLE")
        lines.append(f"Generated: {now.strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("=" * 90)
        lines.append("")
        
        # Table headers
        lines.append(f"{'Service':<20} {'Name':<25} {'Next Rotation':<15} {'Days Until':<12} {'Status'}")
        lines.append("-" * 90)
        
        # Get secrets with rotation dates
        rotatable = [s for s in secrets_list if s.get('next_rotation')]
        
        # Sort by next rotation date
        rotatable.sort(key=lambda x: x.get('next_rotation', '9999'))
        
        for secret in rotatable[:50]:  # Limit to 50
            next_rot = datetime.fromisoformat(secret['next_rotation'])
            days_until = (next_rot - now).days
            
            # Status indicator
            if days_until < 0:
                status = "OVERDUE"
                indicator = "🚨"
            elif days_until <= 7:
                status = "CRITICAL"
                indicator = "🔴"
            elif days_until <= 30:
                status = "WARNING"
                indicator = "🟠"
            else:
                status = "OK"
                indicator = "✅"
            
            service = secret.get('service', 'N/A')[:19]
            name = secret.get('name', 'N/A')[:24]
            rot_date = secret.get('next_rotation', 'N/A')[:10]
            
            lines.append(f"{indicator} {service:<20} {name:<25} {rot_date:<15} {days_until:<12} {status}")
        
        lines.append("")
        lines.append(f"Total Rotatable Secrets: {len(rotatable)}")
        lines.append("=" * 90)
        
        return '\n'.join(lines)
    
    def generate_compliance_audit_log(
        self,
        events: List[Dict],
        summary: Dict,
        anomalies: Dict,
        period_days: int = 90
    ) -> str:
        """Generate formatted compliance audit log report."""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        lines = []
        lines.append("=" * 70)
        lines.append("COMPLIANCE AUDIT LOG REPORT")
        lines.append(f"Period: Last {period_days} days")
        lines.append(f"Generated: {timestamp}")
        lines.append("=" * 70)
        lines.append("")
        
        # Executive summary
        lines.append("EXECUTIVE SUMMARY")
        lines.append("-" * 40)
        lines.append(f"Total Events Logged:    {summary.get('total_events', 0)}")
        lines.append(f"Secrets Accessed:       {summary.get('unique_secrets_accessed', 0)}")
        lines.append(f"Unique Users:           {summary.get('unique_users', 0)}")
        lines.append(f"Secret Rotations:       {summary.get('rotation_count', 0)}")
        lines.append(f"Access Events:          {summary.get('access_count', 0)}")
        lines.append("")
        
        # Anomalies section
        if anomalies.get('anomaly_count', 0) > 0:
            lines.append("⚠️ SECURITY ANOMALIES DETECTED")
            lines.append("-" * 40)
            for anomaly in anomalies.get('anomalies', []):
                lines.append(f"  [{anomaly.get('severity', 'unknown').upper()}] {anomaly.get('type')}")
                lines.append(f"    {anomaly.get('description')}")
                lines.append("")
        else:
            lines.append("✅ No security anomalies detected")
            lines.append("")
        
        # Event breakdown
        lines.append("EVENT BREAKDOWN BY TYPE")
        lines.append("-" * 40)
        event_counts = summary.get('events_by_type', {})
        for event_type, count in sorted(event_counts.items(), key=lambda x: -x[1]):
            icon = {
                'SECRET_CREATED': '➕',
                'SECRET_ACCESSED': '👁️',
                'SECRET_UPDATED': '✏️',
                'SECRET_ROTATED': '🔄',
                'SECRET_DELETED': '🗑️',
                'SECRET_EXPIRED': '⏰',
                'AUTH_FAILED': '🚫'
            }.get(event_type, '•')
            lines.append(f"  {icon} {event_type}: {count}")
        lines.append("")
        
        # Recent detailed events
        lines.append("RECENT EVENT TIMELINE")
        lines.append("-" * 40)
        timeline = events[:20]  # Last 20 events
        
        for event in timeline:
            ts = event.get('timestamp', '')[:19].replace('T', ' ')
            event_type = event.get('event_type', '')
            action = event.get('action', '')
            secret_id = event.get('secret_id', '')[:12]
            user = event.get('user_id', 'system')
            
            lines.append(f"  [{ts}] {event_type}")
            lines.append(f"         Action: {action} | Secret: {secret_id}... | User: {user}")
            lines.append("")
        
        lines.append("=" * 70)
        lines.append("End of Compliance Report")
        lines.append(f"Report ID: {summary.get('report_id', 'N/A')}")
        lines.append("=" * 70)
        
        return '\n'.join(lines)
    
    def save_report(
        self,
        content: str,
        report_name: str,
        report_type: str = 'general'
    ) -> str:
        """Save report to file with timestamp."""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        safe_name = self._safe_filename(report_name)
        
        # Determine extension based on type
        ext_map = {
            'general': 'txt',
            'calendar': 'txt',
            'audit': 'log',
            'json': 'json'
        }
        extension = ext_map.get(report_type, 'txt')
        
        filename = f"{safe_name}_{timestamp}.{extension}"
        filepath = os.path.join(self.reports_dir, filename)
        
        with open(filepath, 'w') as f:
            f.write(content)
        
        os.chmod(filepath, 0o600)
        
        return filepath
    
    def get_latest_reports(self, limit: int = 10) -> List[Dict]:
        """Get list of latest generated reports."""
        reports = []
        
        if not os.path.exists(self.reports_dir):
            return reports
        
        for filename in os.listdir(self.reports_dir):
            filepath = os.path.join(self.reports_dir, filename)
            if os.path.isfile(filepath):
                stat = os.stat(filepath)
                reports.append({
                    'filename': filename,
                    'path': filepath,
                    'size_bytes': stat.st_size,
                    'created_at': datetime.fromtimestamp(stat.st_ctime).isoformat()
                })
        
        return sorted(reports, key=lambda x: x['created_at'], reverse=True)[:limit]
