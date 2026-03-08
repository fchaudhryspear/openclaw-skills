#!/usr/bin/env python3
"""
NexDev v3.0 - Track B: Ecosystem
Slack/Teams Notification Engine

Team notifications on PRs, deployments, incidents
Notification tiers: critical (immediate), summary (hourly digest), silent (logs only)
"""

import json
import requests
from pathlib import Path
from typing import Optional, Dict, List
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum


class NotificationTier(Enum):
    CRITICAL = "critical"  # Immediate push + DM
    HIGH = "high"          # Channel mention
    NORMAL = "normal"      # Channel post
    SUMMARY = "summary"    # Hourly digest
    SILENT = "silent"      # Log only


@dataclass
class Notification:
    channel: str
    message: str
    tier: NotificationTier
    icon: str = "🔔"
    color: str = "#36a64f"  # Slack attachment color
    actions: List[Dict] = None
    username: str = "NexDev"
    thread_ts: str = None


class SlackNotifier:
    """Multi-platform notification engine for team collaboration"""
    
    PLATFORMS = {
        'slack': {
            'api_url': 'https://slack.com/api/chat.postMessage',
            'webhook_field': 'slack_webhook_url'
        },
        'discord': {
            'api_url': '{webhook}/messages',
            'webhook_field': 'discord_webhook_url'
        },
        'teams': {
            'api_url': '{webhook}',
            'webhook_field': 'teams_webhook_url'
        }
    }
    
    ICONS = {
        'pr_opened': '🔓',
        'pr_merged': '✅',
        'pr_closed': '❌',
        'build_success': '🎉',
        'build_failed': '🚨',
        'deployment_success': '🚀',
        'deployment_failed': '💥',
        'incident_created': '⚠️',
        'incident_resolved': '✔️',
        'code_review': '👀',
        'dependency_update': '📦',
        'test_failure': '🧪',
        'security_alert': '🔒',
        'default': '🔔'
    }
    
    COLORS = {
        'success': '#36a64f',   # Green
        'error': '#ff0000',     # Red
        'warning': '#ffa500',   # Orange
        'info': '#1d98ff',      # Blue
        'neutral': '#808080'    # Gray
    }
    
    def __init__(self, config_path: str = None):
        self.config = self._load_config(config_path)
        self.notification_queue = Path.home() / '.openclaw' / 'workspace' / 'nexdev' / 'notification_queue.json'
        self.delivery_log = Path.home() / '.openclaw' / 'workspace' / 'nexdev' / 'logs' / 'notifications.jsonl'
        self.queue_dir = Path.home() / '.openclaw' / 'workspace' / 'nexdev'
        self.queue_dir.mkdir(parents=True, exist_ok=True)
        
    def _load_config(self, config_path: str) -> Dict:
        default_config = {
            'platforms': {
                'slack': {
                    'enabled': True,
                    'token': '',
                    'channels': {
                        'general': '#general',
                        'deployments': '#deployments',
                        'incidents': '#incidents',
                        'reviews': '#code-reviews'
                    }
                },
                'discord': {
                    'enabled': False,
                    'webhook_url': ''
                },
                'teams': {
                    'enabled': False,
                    'webhook_url': ''
                }
            },
            'routing': {
                'pr_events': 'reviews',
                'build_events': 'general',
                'deployment_events': 'deployments',
                'incident_events': 'incidents',
                'default': 'general'
            },
            'digest': {
                'enabled': True,
                'schedule': ['09:00', '13:00', '17:00'],  # Daily summaries
                'timezone': 'America/Chicago',
                'include_summary': True
            },
            'mentions': {
                'on_critical': True,
                'on_deployment_failure': True,
                'on_security_alert': True,
                'users_to_mention': []  # [@user1, @user2]
            },
            'throttle': {
                'max_per_minute': 10,
                'cooldown_seconds': 5
            }
        }
        
        if config_path and Path(config_path).exists():
            try:
                with open(config_path) as f:
                    user_config = json.load(f)
                    default_config.update(user_config)
            except Exception:
                pass
                
        return default_config
        
    async def send_notification(self, event_type: str, payload: Dict, 
                                platform: str = 'slack') -> Dict:
        """
        Send notification based on event type
        
        Args:
            event_type: Type of event (pr_opened, build_failed, etc.)
            payload: Event-specific data
            platform: Target platform (slack, discord, teams)
            
        Returns:
            Delivery result
        """
        # Determine notification tier and channel
        tier = self._get_notification_tier(event_type, payload)
        channel = self._get_channel_for_event(event_type)
        icon = self.ICONS.get(event_type, self.ICONS['default'])
        
        # Format message
        message = self._format_message(event_type, payload, icon)
        
        # Create notification object
        notification = Notification(
            channel=channel,
            message=message,
            tier=tier,
            icon=icon,
            color=self._get_color_for_event(event_type, payload),
            username="NexDev"
        )
        
        # Handle based on tier
        if tier == NotificationTier.SUMMARY:
            # Queue for digest
            return await self._queue_for_digest(notification)
        elif tier == NotificationTier.SILENT:
            # Just log
            self._log_notification(notification, 'queued')
            return {'status': 'logged', 'tier': 'silent'}
        else:
            # Send immediately
            return await self._send_immediate(notification, platform)
            
    def _get_notification_tier(self, event_type: str, payload: Dict) -> NotificationTier:
        """Determine notification priority"""
        # Critical events
        if event_type in ['incident_created', 'build_failed', 'deployment_failed']:
            if event_type == 'incident_created':
                return NotificationTier.CRITICAL
            elif event_type == 'build_failed':
                return NotificationTier.HIGH
            elif event_type == 'deployment_failed':
                return NotificationTier.HIGH
                
        # Security alerts are always important
        if event_type == 'security_alert':
            return NotificationTier.HIGH
            
        # Normal events
        if event_type in ['pr_opened', 'pr_merged', 'code_review', 'dependency_update']:
            return NotificationTier.NORMAL
            
        # Default
        return NotificationTier.NORMAL
        
    def _get_channel_for_event(self, event_type: str) -> str:
        """Get target channel for event type"""
        routing = self.config['routing']
        
        if event_type.startswith('pr_'):
            return routing.get('pr_events', routing['default'])
        elif event_type.startswith('build_'):
            return routing.get('build_events', routing['default'])
        elif event_type.startswith('deployment_'):
            return routing.get('deployment_events', routing['default'])
        elif event_type.startswith('incident_'):
            return routing.get('incident_events', routing['default'])
        else:
            return routing['default']
            
    def _format_message(self, event_type: str, payload: Dict, icon: str) -> str:
        """Format human-readable message"""
        templates = {
            'pr_opened': "{icon} **PR Opened**: {title}\n<{url}|#{number}> by @{author}",
            'pr_merged': "{icon} **PR Merged**: {title}\n<{url}|#{number}> by @{author}",
            'pr_closed': "{icon} **PR Closed**: {title}\n<{url}|#{number}>",
            'build_success': "{icon} **Build Passed**: {project} - #{build_number}",
            'build_failed': "{icon} **Build Failed**: {project} - #{build_number}\n{error}",
            'deployment_success': "{icon} **Deployed**: {project} to {environment}\nVersion: {version}",
            'deployment_failed': "{icon} **Deployment Failed**: {project} to {environment}\n{error}",
            'incident_created': "{icon} **Incident**: {title}\nSeverity: {severity}\n{description}",
            'incident_resolved': "{icon} **Incident Resolved**: {title}",
            'code_review': "{icon} **Review Requested**: {title}\n<{url}|#{number}> from @{author}",
            'dependency_update': "{icon} **Dependency Updated**: {package} {old_version} → {new_version}",
            'test_failure': "{icon} **Test Failed**: {test_name} in {file}",
            'security_alert': "{icon} **Security Alert**: {alert_type}\n{description}"
        }
        
        template = templates.get(event_type, "{icon} **{event_type}**:\n{payload}")
        
        # Simple string formatting
        message = template.format(icon=icon, event_type=event_type, payload=str(payload))
        
        # Replace payload placeholders
        for key, value in payload.items():
            placeholder = "{" + key + "}"
            message = message.replace(placeholder, str(value)[:100])
            
        return message
        
    def _get_color_for_event(self, event_type: str, payload: Dict) -> str:
        """Get attachment color based on event"""
        if event_type.endswith('_success') or event_type in ['pr_merged', 'incident_resolved']:
            return self.COLORS['success']
        elif event_type.endswith('_failed') or event_type in ['incident_created']:
            return self.COLORS['error']
        elif event_type in ['security_alert', 'build_failed', 'deployment_failed']:
            return self.COLORS['error']
        elif event_type in ['code_review', 'pr_opened']:
            return self.COLORS['info']
        else:
            return self.COLORS['neutral']
            
    async def _send_immediate(self, notification: Notification, platform: str) -> Dict:
        """Send notification immediately"""
        if platform == 'slack':
            return await self._send_slack(notification)
        elif platform == 'discord':
            return await self._send_discord(notification)
        elif platform == 'teams':
            return await self._send_teams(notification)
        else:
            return {'status': 'error', 'message': f'Unsupported platform: {platform}'}
            
    async def _send_slack(self, notification: Notification) -> Dict:
        """Send to Slack"""
        slack_config = self.config['platforms']['slack']
        
        if not slack_config['token']:
            return {'status': 'error', 'message': 'Slack token not configured'}
            
        channel = self._resolve_channel(notification.channel)
        
        # Build message with mentions for critical events
        text = notification.message
        if notification.tier in [NotificationTier.CRITICAL, NotificationTier.HIGH]:
            mentions = self.config['mentions'].get('users_to_mention', [])
            if self.config['mentions'].get('on_critical', False):
                text = " ".join([f"<@{user}>" for user in mentions]) + "\n" + text
                
        payload = {
            'channel': channel,
            'text': text,
            'username': notification.username,
            'icon_emoji': notification.icon,
            'attachments': [{
                'color': notification.color,
                'text': text,
                'footer': 'NexDev • Automated Notification',
                'ts': int(datetime.now().timestamp())
            }]
        }
        
        # Add action buttons if present
        if notification.actions:
            payload['attachments'][0]['actions'] = notification.actions
            
        headers = {
            'Authorization': f"Bearer {slack_config['token']}",
            'Content-Type': 'application/json'
        }
        
        response = requests.post(
            self.PLATFORMS['slack']['api_url'],
            headers=headers,
            json=payload,
            timeout=30
        )
        
        if response.status_code == 200:
            self._log_notification(notification, 'sent', platform)
            return {'status': 'sent', 'platform': platform, 'response': response.json()}
        else:
            self._log_notification(notification, 'failed', platform, response.text)
            return {'status': 'failed', 'platform': platform, 'error': response.text}
            
    async def _send_discord(self, notification: Notification) -> Dict:
        """Send to Discord webhook"""
        discord_config = self.config['platforms']['discord']
        
        if not discord_config.get('webhook_url'):
            return {'status': 'error', 'message': 'Discord webhook not configured'}
            
        payload = {
            'username': notification.username,
            'avatar_url': 'https://i.imgur.com/your-avatar.png',
            'embeds': [{
                'title': notification.icon,
                'description': notification.message,
                'color': int(notification.color.lstrip('#'), 16),
                'footer': {
                    'text': 'NexDev • Automated Notification'
                }
            }]
        }
        
        response = requests.post(discord_config['webhook_url'], json=payload, timeout=30)
        
        if response.status_code in [200, 204]:
            self._log_notification(notification, 'sent', 'discord')
            return {'status': 'sent', 'platform': 'discord'}
        else:
            return {'status': 'failed', 'platform': 'discord', 'error': response.text}
            
    async def _send_teams(self, notification: Notification) -> Dict:
        """Send to Microsoft Teams webhook"""
        teams_config = self.config['platforms']['teams']
        
        if not teams_config.get('webhook_url'):
            return {'status': 'error', 'message': 'Teams webhook not configured'}
            
        payload = {
            'text': notification.message,
            'attachments': [{
                'contentType': 'application/vnd.microsoft.card.adaptive',
                'content': {
                    '$schema': 'http://adaptivecards.io/schemas/adaptive-card.json',
                    'type': 'AdaptiveCard',
                    'version': '1.2',
                    'body': [{
                        'type': 'TextBlock',
                        'text': notification.message,
                        'wrap': True
                    }]
                }
            }]
        }
        
        response = requests.post(teams_config['webhook_url'], json=payload, timeout=30)
        
        if response.status_code in [200, 202]:
            self._log_notification(notification, 'sent', 'teams')
            return {'status': 'sent', 'platform': 'teams'}
        else:
            return {'status': 'failed', 'platform': 'teams', 'error': response.text}
            
    def _resolve_channel(self, channel_name: str) -> str:
        """Resolve channel name to ID"""
        # Would call Slack API to resolve channel name to ID
        # For now, return as-is
        if channel_name.startswith('#'):
            return channel_name
        return f"#{channel_name}"
            
    async def _queue_for_digest(self, notification: Notification) -> Dict:
        """Queue notification for digest"""
        queue = self._load_queue()
        
        queue.append({
            'timestamp': datetime.now().isoformat(),
            'notification': asdict(notification)
        })
        
        self._save_queue(queue)
        self._log_notification(notification, 'queued_for_digest')
        
        return {'status': 'queued_for_digest'}
        
    async def send_digest(self, platform: str = 'slack') -> Dict:
        """Send queued digest notifications"""
        queue = self._load_queue()
        
        if not queue:
            return {'status': 'empty', 'count': 0}
            
        # Group by type
        grouped = {}
        for item in queue:
            msg = item['notification']['message']
            # Simplified grouping logic
            key = 'notifications'
            if key not in grouped:
                grouped[key] = []
            grouped[key].append(msg)
            
        # Build digest message
        lines = ["*📊 NexDev Digest*"]
        lines.append(f"_{len(queue)} notification(s)_\n")
        
        for msg in queue[:10]:  # Limit to 10 items
            lines.append(msg['notification']['message'])
            
        if len(queue) > 10:
            lines.append(f"\n_and {len(queue) - 10} more..._")
            
        digest_notification = Notification(
            channel=self.config['routing']['default'],
            message="\n".join(lines),
            tier=NotificationTier.NORMAL,
            icon="📊"
        )
        
        result = await self._send_immediate(digest_notification, platform)
        
        # Clear queue after sending
        self._save_queue([])
        
        return {
            'status': 'sent',
            'count': len(queue),
            'result': result
        }
        
    def _load_queue(self) -> List[Dict]:
        """Load notification queue"""
        if not self.notification_queue.exists():
            return []
            
        try:
            with open(self.notification_queue) as f:
                return json.load(f)
        except Exception:
            return []
            
    def _save_queue(self, queue: List[Dict]):
        """Save notification queue"""
        with open(self.notification_queue, 'w') as f:
            json.dump(queue, f, indent=2)
            
    def _log_notification(self, notification: Notification, status: str, 
                          platform: str = None, error: str = None):
        """Log notification delivery attempt"""
        entry = {
            'timestamp': datetime.now().isoformat(),
            'channel': notification.channel,
            'tier': notification.tier.value,
            'status': status,
            'platform': platform,
            'icon': notification.icon
        }
        
        if error:
            entry['error'] = error
            
        log_file = Path(self.delivery_log)
        log_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(log_file, 'a') as f:
            f.write(json.dumps(entry) + '\n')


# Helper function for quick notifications
def notify(event_type: str, **kwargs) -> Dict:
    """Quick notification helper"""
    notifier = SlackNotifier()
    
    import asyncio
    return asyncio.run(notifier.send_notification(event_type, kwargs))


# CLI Entry Point
if __name__ == '__main__':
    import asyncio
    import sys
    
    print("NexDev Slack Notifier v3.0")
    print("=" * 50)
    
    notifier = SlackNotifier()
    
    if len(sys.argv) < 2:
        print("\nUsage:")
        print("  python slack_notifier.py test <event_type>")
        print("  python slack_notifier.py send <platform> <channel> \"message\"")
        print("  python slack_notifier.py digest")
        sys.exit(1)
        
    command = sys.argv[1]
    
    if command == 'test':
        event_type = sys.argv[2] if len(sys.argv) > 2 else 'build_failed'
        
        test_payloads = {
            'build_failed': {
                'project': 'my-app',
                'build_number': '1234',
                'error': 'Compilation failed at line 42',
                'branch': 'main'
            },
            'pr_opened': {
                'title': 'Add new feature',
                'number': '42',
                'author': 'developer',
                'url': 'https://github.com/org/repo/pull/42'
            },
            'deployment_success': {
                'project': 'my-app',
                'environment': 'production',
                'version': 'v1.2.3'
            }
        }
        
        payload = test_payloads.get(event_type, {'message': 'Test notification'})
        
        result = asyncio.run(notifier.send_notification(event_type, payload))
        print(json.dumps(result, indent=2))
        
    elif command == 'send':
        if len(sys.argv) < 4:
            print("Usage: python slack_notifier.py send <platform> <channel> \"message\"")
            sys.exit(1)
            
        platform = sys.argv[2]
        channel = sys.argv[3]
        message = sys.argv[4] if len(sys.argv) > 4 else ""
        
        notification = Notification(
            channel=channel,
            message=message,
            tier=NotificationTier.NORMAL
        )
        
        result = asyncio.run(notifier._send_immediate(notification, platform))
        print(json.dumps(result, indent=2))
        
    elif command == 'digest':
        result = asyncio.run(notifier.send_digest())
        print(json.dumps(result, indent=2))
