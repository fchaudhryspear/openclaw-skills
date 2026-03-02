"""
Alert Manager
Handles alert routing, deduplication, and delivery to multiple channels
"""

import asyncio
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
import logging
import json

# Alert channels
try:
    from slack_sdk import AsyncWebhookClient
    SLACK_AVAILABLE = True
except ImportError:
    SLACK_AVAILABLE = False
    
try:
    import aiohttp
    AIOHTTP_AVAILABLE = True
except ImportError:
    AIOHTTP_AVAILABLE = False
    
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

logger = logging.getLogger(__name__)


@dataclass
class Alert:
    """Single alert instance"""
    alert_id: str
    title: str
    message: str
    severity: str  # critical, warning, info
    source: str
    resource: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)
    channel: Optional[str] = None
    acknowledged: bool = False
    resolved: bool = False
    
    def to_dict(self) -> Dict:
        return {
            'alert_id': self.alert_id,
            'title': self.title,
            'message': self.message,
            'severity': self.severity,
            'source': self.source,
            'resource': self.resource,
            'timestamp': self.timestamp.isoformat(),
            'metadata': self.metadata,
            'channel': self.channel,
            'acknowledged': self.acknowledged,
            'resolved': self.resolved
        }
    
    @property
    def dedup_key(self) -> str:
        """Generate deduplication key"""
        content = f"{self.source}:{self.resource}:{self.title}"
        return hashlib.md5(content.encode()).hexdigest()[:12]


class AlertManager:
    """
    Manages alerts with:
    - Multi-channel delivery (Slack, Telegram, Email)
    - Deduplication
    - Routing rules
    - Rate limiting
    """
    
    def __init__(self, config: Dict):
        self.config = config
        self.alert_history: Dict[str, Alert] = {}
        self.active_alerts: Dict[str, Alert] = {}
        self.dedup_cache: Dict[str, datetime] = {}
        
        # Channel configs
        self.slack_config = config.get('slack', {})
        self.telegram_config = config.get('telegram', {})
        self.email_config = config.get('email', {})
        
        # Rate limiting
        self.rate_limits = {
            'critical': config.get('rate_limit_critical', 60),  # min between alerts
            'warning': config.get('rate_limit_warning', 300),
            'info': config.get('rate_limit_info', 600)
        }
        self.last_alert_time: Dict[str, datetime] = {}
        
        # Routing rules
        self.routing_rules = config.get('routing_rules', {
            'critical': ['slack', 'telegram', 'email'],
            'warning': ['slack', 'telegram'],
            'info': ['slack']
        })
        
        # Deduplication window (seconds)
        self.dedup_window = config.get('dedup_window_seconds', 300)
        
    async def send_alert(self, alert: Alert) -> Dict[str, bool]:
        """Send alert to appropriate channels based on severity"""
        results = {}
        
        # Check rate limiting
        if not self._check_rate_limit(alert):
            logger.info(f"Rate limited alert: {alert.alert_id}")
            return {'rate_limited': True}
            
        # Get channels for this severity
        channels = self.routing_rules.get(
            alert.severity, 
            self.routing_rules.get('info', ['slack'])
        )
        
        # Override with alert-specific channel if set
        if alert.channel:
            channels = [alert.channel]
        
        # Send to each channel
        for channel in channels:
            try:
                if channel == 'slack':
                    success = await self._send_slack(alert)
                elif channel == 'telegram':
                    success = await self._send_telegram(alert)
                elif channel == 'email':
                    success = await self._send_email(alert)
                else:
                    logger.warning(f"Unknown channel: {channel}")
                    continue
                    
                results[channel] = success
                
                if success:
                    self._update_dedup_cache(alert)
                    
            except Exception as e:
                logger.error(f"Failed to send alert to {channel}: {e}")
                results[channel] = False
        
        # Store alert
        self.alert_history[alert.alert_id] = alert
        if not alert.resolved:
            self.active_alerts[alert.alert_id] = alert
            
        return results
        
    def _check_rate_limit(self, alert: Alert) -> bool:
        """Check if alert should be rate limited"""
        limit_key = f"{alert.source}:{alert.resource}"
        min_interval = self.rate_limits.get(alert.severity, 300)
        
        last_time = self.last_alert_time.get(limit_key)
        if last_time:
            elapsed = (datetime.utcnow() - last_time).total_seconds()
            if elapsed < min_interval:
                return False
                
        self.last_alert_time[limit_key] = datetime.utcnow()
        return True
        
    def _update_dedup_cache(self, alert: Alert):
        """Update deduplication cache"""
        self.dedup_cache[alert.dedup_key] = datetime.utcnow()
        
    def _is_duplicate(self, alert: Alert) -> bool:
        """Check if this is a duplicate alert within dedup window"""
        last_seen = self.dedup_cache.get(alert.dedup_key)
        if not last_seen:
            return False
            
        elapsed = (datetime.utcnow() - last_seen).total_seconds()
        return elapsed < self.dedup_window
        
    async def _send_slack(self, alert: Alert) -> bool:
        """Send alert to Slack webhook"""
        webhook_url = self.slack_config.get('webhook_url')
        if not webhook_url:
            logger.warning("Slack webhook URL not configured")
            return False
            
        # Format Slack message
        colors = {
            'critical': '#FF0000',
            'warning': '#FFA500',
            'info': '#36A64F'
        }
        
        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"🚨 {alert.title}" if alert.severity == 'critical' else f"⚠️ {alert.title}"
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": alert.message
                }
            },
            {
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": f"*Source:* `{alert.source}`\n*Resource:* `{alert.resource}`\n*Severity:* *{alert.severity.upper()}*"
                    }
                ]
            }
        ]
        
        # Add action buttons
        if not alert.acknowledged:
            blocks.append({
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "✅ Acknowledge"
                        },
                        "value": f"ack:{alert.alert_id}",
                        "url": f"{self.slack_config.get('acknowledge_url', '')}/ack/{alert.alert_id}"
                    },
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "🔧 View Details"
                        },
                        "value": f"details:{alert.alert_id}",
                        "url": f"{self.slack_config.get('dashboard_url', '')}/alerts/{alert.alert_id}"
                    }
                ]
            })
            
        payload = {
            "attachments": [{
                "color": colors.get(alert.severity, '#36A64F'),
                "blocks": blocks
            }]
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(webhook_url, json=payload) as response:
                    if response.status == 200:
                        logger.info(f"Slack alert sent: {alert.alert_id}")
                        return True
                    else:
                        logger.error(f"Slack webhook returned {response.status}")
                        return False
                        
        except Exception as e:
            logger.error(f"Failed to send Slack alert: {e}")
            return False
            
    async def _send_telegram(self, alert: Alert) -> bool:
        """Send alert to Telegram"""
        bot_token = self.telegram_config.get('bot_token')
        chat_id = self.telegram_config.get('chat_id')
        
        if not bot_token or not chat_id:
            logger.warning("Telegram not configured")
            return False
            
        # Format message
        emoji = {'critical': '🚨', 'warning': '⚠️', 'info': 'ℹ️'}
        text = f"""
{emoji.get(alert.severity, 'ℹ️')} *{alert.title}*

{alert.message}

━━━━━━━━━━━━━━━━
*Source:* `{alert.source}`
*Resource:* `{alert.resource}`
*Severity:* *{alert.severity.upper()}*
*Time:* {alert.timestamp.strftime('%Y-%m-%d %H:%M:%S')}
"""
        
        # Add inline keyboard if not acknowledged
        markup = None
        if not alert.acknowledged:
            markup = {
                "inline_keyboard": [
                    [
                        {"text": "✅ Acknowledge", "callback_data": f"ack_{alert.alert_id}"},
                        {"text": "🔧 Dashboard", "url": f"{self.telegram_config.get('dashboard_url', '')}/alerts/{alert.alert_id}"}
                    ]
                ]
            }
            
        try:
            url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url,
                    json={
                        'chat_id': chat_id,
                        'text': text,
                        'parse_mode': 'Markdown',
                        'reply_markup': markup
                    }
                ) as response:
                    if response.status == 200:
                        logger.info(f"Telegram alert sent: {alert.alert_id}")
                        return True
                    else:
                        error = await response.text()
                        logger.error(f"Telegram API error: {error}")
                        return False
                        
        except Exception as e:
            logger.error(f"Failed to send Telegram alert: {e}")
            return False
            
    async def _send_email(self, alert: Alert) -> bool:
        """Send alert via email"""
        smtp_server = self.email_config.get('smtp_server')
        smtp_port = self.email_config.get('smtp_port', 587)
        username = self.email_config.get('username')
        password = self.email_config.get('password')
        recipients = self.email_config.get('recipients', [])
        
        if not all([smtp_server, username, password, recipients]):
            logger.warning("Email not fully configured")
            return False
            
        subject = f"[{alert.severity.upper()}] {alert.title}"
        
        body = f"""
Cross-Service Monitor Alert

Title: {alert.title}
Severity: {alert.severity.upper()}

Message:
{alert.message}

---
Source: {alert.source}
Resource: {alert.resource}
Time: {alert.timestamp.strftime('%Y-%m-%d %H:%M:%S')}
Alert ID: {alert.alert_id}

Dashboard: {self.email_config.get('dashboard_url', 'N/A')}
"""
        
        try:
            msg = MIMEMultipart()
            msg['From'] = username
            msg['To'] = ', '.join(recipients)
            msg['Subject'] = subject
            msg.attach(MIMEText(body, 'plain'))
            
            server = smtplib.SMTP(smtp_server, smtp_port)
            server.starttls()
            server.login(username, password)
            server.send_message(msg)
            server.quit()
            
            logger.info(f"Email alert sent: {alert.alert_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email alert: {e}")
            return False
            
    async def send_bulk_alert(self, issues: List[Dict]) -> Dict:
        """Send consolidated alert for multiple related issues"""
        if not issues:
            return {}
            
        # Determine overall severity
        severities = [i.get('severity', 'info') for i in issues]
        if 'critical' in severities:
            severity = 'critical'
        elif 'warning' in severities:
            severity = 'warning'
        else:
            severity = 'info'
            
        # Create combined message
        affected_services = list(set(
            service for issue in issues 
            for service in issue.get('affected_services', [])
        ))
        
        message = "\n\n".join([
            f"**{issue['title']}**\n{issue.get('root_cause_hypothesis', 'No root cause identified')}"
            for issue in issues[:5]  # Limit to top 5
        ])
        
        alert = Alert(
            alert_id=f"BULK-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
            title=f"Multiple Issues Detected ({len(issues)} total)",
            message=message,
            severity=severity,
            source='correlation-engine',
            resource='|'.join(affected_services),
            metadata={
                'issue_count': len(issues),
                'affected_services': affected_services,
                'issues': [i['issue_id'] for i in issues]
            }
        )
        
        return await self.send_alert(alert)
        
    def acknowledge_alert(self, alert_id: str) -> bool:
        """Acknowledge an alert"""
        if alert_id in self.active_alerts:
            self.active_alerts[alert_id].acknowledged = True
            logger.info(f"Alert acknowledged: {alert_id}")
            return True
        return False
        
    def resolve_alert(self, alert_id: str) -> bool:
        """Resolve/close an alert"""
        if alert_id in self.active_alerts:
            self.active_alerts[alert_id].resolved = True
            del self.active_alerts[alert_id]
            logger.info(f"Alert resolved: {alert_id}")
            return True
        return False
        
    def get_active_alerts(self, severity: Optional[str] = None) -> List[Dict]:
        """Get list of active alerts"""
        alerts = []
        for alert in self.active_alerts.values():
            if severity and alert.severity != severity:
                continue
            alerts.append(alert.to_dict())
            
        # Sort by severity (critical first) then timestamp
        severity_order = {'critical': 0, 'warning': 1, 'info': 2}
        alerts.sort(key=lambda x: (severity_order.get(x['severity'], 3), x['timestamp']))
        
        return alerts
        
    def get_alert_summary(self) -> Dict:
        """Get summary of alert status"""
        now = datetime.utcnow()
        last_24h = now - timedelta(hours=24)
        
        recent_alerts = [
            a for a in self.alert_history.values()
            if datetime.fromisoformat(a.timestamp) > last_24h
        ]
        
        return {
            'active_count': len(self.active_alerts),
            'critical_active': len([a for a in self.active_alerts.values() if a.severity == 'critical']),
            'warning_active': len([a for a in self.active_alerts.values() if a.severity == 'warning']),
            'acknowledged_count': len([a for a in self.active_alerts.values() if a.acknowledged]),
            'total_24h': len(recent_alerts),
            'critical_24h': len([a for a in recent_alerts if a.severity == 'critical']),
            'resolved_24h': len([a for a in recent_alerts if a.resolved])
        }


class HealthChecker:
    """Periodic health check orchestrator"""
    
    def __init__(self, monitors: Dict, alert_manager: AlertManager, config: Dict):
        self.monitors = monitors
        self.alert_manager = alert_manager
        self.config = config
        self.check_interval = config.get('health_check_interval', 60)
        self.running = False
        
    async def start(self):
        """Start periodic health checks"""
        self.running = True
        logger.info("Starting health checker")
        
        while self.running:
            try:
                await self._run_health_check()
            except Exception as e:
                logger.error(f"Health check error: {e}")
                
            await asyncio.sleep(self.check_interval)
            
    async def stop(self):
        """Stop health checks"""
        self.running = False
        
    async def _run_health_check(self):
        """Run comprehensive health check across all services"""
        issues = []
        
        # AWS health
        if 'aws' in self.monitors:
            aws_health = await self.monitors['aws'].get_all_lambda_health()
            for func_name, metrics in aws_health.items():
                if metrics.error_rate > 0.05:
                    alert = Alert(
                        alert_id=f"AWS-LAMBDA-{func_name}-{datetime.utcnow().strftime('%H%M')}",
                        title=f"Lambda Error Rate High: {func_name}",
                        message=f"Error rate: {metrics.error_rate:.1%} (invocations: {metrics.invocations}, errors: {metrics.errors})",
                        severity='warning' if metrics.error_rate < 0.1 else 'critical',
                        source='aws',
                        resource=func_name,
                        metadata={'metrics': vars(metrics)}
                    )
                    await self.alert_manager.send_alert(alert)
                    issues.append({'type': 'lambda_errors', 'resource': func_name})
                    
        # Snowflake health  
        if 'snowflake' in self.monitors:
            query_health = await self.monitors['snowflake'].check_query_health()
            if query_health.failure_rate > 0.1:
                alert = Alert(
                    alert_id=f"SF-QUERY-{datetime.utcnow().strftime('%H%M')}",
                    title="Snowflake Query Failure Rate High",
                    message=f"Failure rate: {query_health.failure_rate:.1%} (queries: {query_health.total_queries}, failures: {query_health.failed_queries})",
                    severity='warning',
                    source='snowflake',
                    resource='query-execution',
                    metadata={'metrics': vars(query_health)}
                )
                await self.alert_manager.send_alert(alert)
                issues.append({'type': 'snowflake_failures'})
                
        # CRM health
        if 'crm' in self.monitors:
            crm_health = await self.monitors['crm'].get_all_health()
            for service, health in crm_health.items():
                if health.status == 'down':
                    alert = Alert(
                        alert_id=f"CRM-{service}-DOWN",
                        title=f"{service.upper()} API Down",
                        message=f"{service.capitalize()} API is not responding",
                        severity='critical',
                        source='crm',
                        resource=service,
                        metadata={'health': vars(health)}
                    )
                    await self.alert_manager.send_alert(alert)
                    issues.append({'type': 'crm_down', 'resource': service})
