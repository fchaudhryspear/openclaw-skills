#!/usr/bin/env python3
"""
Proactive Monitoring System
Real-time cost anomaly detection, system health checks, and security posture monitoring.
"""

import os
import sys
import json
import time
import psutil
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
import yaml
import requests
from typing import Dict, List, Optional

class ProactiveMonitor:
    """Main monitoring orchestrator."""
    
    def __init__(self, config_path: str = None):
        self.config_path = config_path or Path(__file__).parent / "config.yaml"
        self.config = self._load_config()
        self.data_dir = Path(self.config['dashboard']['data_dir'])
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.alert_state = {}  # Track previous state to avoid duplicate alerts
        self.chat_id = os.getenv('TELEGRAM_CHAT_ID', self.config['notification'].get('chat_id', ''))
        
    def _load_config(self) -> dict:
        """Load configuration from YAML file."""
        with open(self.config_path, 'r') as f:
            return yaml.safe_load(f)
    
    def _send_telegram_alert(self, title: str, message: str, alert_type: str = "info"):
        """Send alert to Telegram."""
        if not self.chat_id:
            print(f"[ALERT] {title}: {message}")
            return
            
        # Color coding based on severity
        emojis = {
            'critical': '🔴',
            'warning': '⚠️', 
            'info': 'ℹ️',
            'security': '🛡️',
            'cost': '💰'
        }
        
        emoji = emojis.get(alert_type, 'ℹ️')
        formatted_message = f"{emoji} *{title}*\n\n{message}\n\n*Time:* {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        
        try:
            url = f"https://api.telegram.org/bot{os.getenv('TELEGRAM_BOT_TOKEN')}/sendMessage"
            payload = {
                'chat_id': self.chat_id,
                'text': formatted_message,
                'parse_mode': 'Markdown'
            }
            response = requests.post(url, json=payload, timeout=10)
            response.raise_for_status()
            print(f"[NOTIFY] Alert sent to Telegram")
        except Exception as e:
            print(f"[ERROR] Failed to send Telegram alert: {e}")
    
    def check_cost_anomaly(self) -> Optional[dict]:
        """
        Check for AI/API cost anomalies.
        Monitors daily spend across all services.
        """
        config = self.config['alerts']['cost']
        threshold = config['threshold_daily']
        
        # Get today's date
        today = datetime.now().date()
        today_str = today.isoformat()
        
        # Load cost data from tracking file
        cost_file = self.data_dir / "daily_costs.json"
        
        if cost_file.exists():
            with open(cost_file, 'r') as f:
                costs = json.load(f)
        else:
            costs = {}
        
        # Get today's cost (you can integrate with actual billing APIs here)
        # This is a placeholder - integrate with your specific API providers
        today_cost = costs.get(today_str, {}).get('total', 0.0)
        
        # Example: Check OpenRouter costs (common setup)
        # In production, query actual billing APIs
        current_cost = self._estimate_current_costs()
        today_cost += current_cost
        
        # Update cost file
        if today_str not in costs:
            costs[today_str] = {'total': 0.0, 'services': {}}
        
        costs[today_str]['total'] = today_cost
        
        # Save updated costs
        with open(cost_file, 'w') as f:
            json.dump(costs, f, indent=2)
        
        # Check against threshold
        if today_cost > threshold:
            alert_key = f"cost_{today_str}"
            if self.alert_state.get(alert_key) != today_cost:
                self.alert_state[alert_key] = today_cost
                
                diff = today_cost - threshold
                message = (
                    f"Daily AI/API costs have exceeded the ${threshold} threshold.\n\n"
                    f"*Current spending:* ${today_cost:.2f}\n"
                    f"*Over budget by:* ${diff:.2f}\n\n"
                    f"Consider reducing usage or upgrading plan."
                )
                self._send_telegram_alert(
                    "Cost Alert 💰", 
                    message, 
                    alert_type='cost'
                )
                
                return {
                    'status': 'alert',
                    'current': today_cost,
                    'threshold': threshold,
                    'overspent': diff
                }
        
        return {'status': 'ok', 'current': today_cost, 'threshold': threshold}
    
    def _estimate_current_costs(self) -> float:
        """
        Estimate current costs from recent API usage.
        Replace with actual billing API integration.
        """
        # Placeholder: In production, this would query:
        # - OpenRouter API
        # - Azure OpenAI
        # - AWS Bedrock
        # - Other provider APIs
        
        # For now, read from local usage log if exists
        usage_log = self.data_dir / "api_usage.log"
        if not usage_log.exists():
            return 0.0
            
        total = 0.0
        today = datetime.now().date().isoformat()
        
        try:
            with open(usage_log, 'r') as f:
                for line in f:
                    if today in line:
                        parts = line.strip().split('|')
                        if len(parts) >= 2:
                            try:
                                cost = float(parts[1])
                                total += cost
                            except ValueError:
                                pass
        except Exception:
            pass
            
        return total
    
    def check_system_health(self) -> Dict[str, any]:
        """Check system health metrics (CPU, memory, disk)."""
        results = {}
        alerts = []
        
        # CPU Check
        cpu_percent = psutil.cpu_percent(interval=1)
        critical_threshold = self.config['alerts']['system']['cpu_critical']
        warning_threshold = self.config['alerts']['system']['cpu_warning']
        
        results['cpu'] = {
            'percent': cpu_percent,
            'status': 'ok'
        }
        
        if cpu_percent > critical_threshold:
            results['cpu']['status'] = 'critical'
            alert_key = 'cpu_critical'
            if self.alert_state.get(alert_key) != cpu_percent:
                self.alert_state[alert_key] = cpu_percent
                alerts.append({
                    'type': 'cpu_critical',
                    'value': cpu_percent,
                    'threshold': critical_threshold
                })
        elif cpu_percent > warning_threshold:
            results['cpu']['status'] = 'warning'
            
        # Memory Check
        memory = psutil.virtual_memory()
        memory_percent = memory.percent
        
        results['memory'] = {
            'used_gb': round(memory.used / 1024**3, 2),
            'total_gb': round(memory.total / 1024**3, 2),
            'percent': memory_percent,
            'status': 'ok'
        }
        
        if memory_percent > self.config['alerts']['system']['memory_critical']:
            results['memory']['status'] = 'critical'
            alert_key = 'memory_critical'
            if self.alert_state.get(alert_key) != memory_percent:
                self.alert_state[alert_key] = memory_percent
                alerts.append({
                    'type': 'memory_critical',
                    'value': memory_percent,
                    'threshold': self.config['alerts']['system']['memory_critical']
                })
        
        # Disk Check (main volume)
        disk = psutil.disk_usage('/')
        percent_free = 100 - disk.percent
        
        results['disk'] = {
            'used_gb': round(disk.used / 1024**3, 2),
            'free_gb': round(disk.free / 1024**3, 2),
            'total_gb': round(disk.total / 1024**3, 2),
            'percent_free': round(percent_free, 1),
            'status': 'ok'
        }
        
        critical_disk = self.config['alerts']['system']['disk_critical_percent_free']
        warning_disk = self.config['alerts']['system']['disk_warning_percent_free']
        
        if percent_free < critical_disk:
            results['disk']['status'] = 'critical'
            alert_key = 'disk_critical'
            if self.alert_state.get(alert_key) != percent_free:
                self.alert_state[alert_key] = percent_free
                alerts.append({
                    'type': 'disk_critical',
                    'value': percent_free,
                    'threshold': critical_disk
                })
        elif percent_free < warning_disk:
            results['disk']['status'] = 'warning'
        
        # Send alerts if any
        for alert in alerts:
            self._send_system_alert(alert)
        
        return results
    
    def _send_system_alert(self, alert: dict):
        """Send system health alert to Telegram."""
        if alert['type'] == 'cpu_critical':
            message = (
                f"CPU usage is critically high!\n\n"
                f"*Current:* {alert['value']:.1f}%\n"
                f"*Threshold:* {alert['threshold']}%\n\n"
                f"Check for runaway processes:"
                f"`top -stats pid,command,%mem,%cpu`"
            )
            self._send_telegram_alert("System Alert 🔴", message, alert_type='critical')
            
        elif alert['type'] == 'memory_critical':
            message = (
                f"Memory usage is critically high!\n\n"
                f"*Current:* {alert['value']:.1f}%\n"
                f"*Threshold:* {alert['threshold']}%\n\n"
                f"Consider freeing up memory or adding swap."
            )
            self._send_telegram_alert("System Alert 🔴", message, alert_type='critical')
            
        elif alert['type'] == 'disk_critical':
            message = (
                f"Disk space is critically low!\n\n"
                f"*Free:* {alert['value']:.1f}%\n"
                f"*Threshold:* {alert['threshold']}%\n\n"
                f"Clean up disk space immediately."
            )
            self._send_telegram_alert("System Alert 🔴", message, alert_type='critical')
    
    def check_security_posture(self) -> Dict[str, any]:
        """Check security posture (SSH attempts, unusual activity)."""
        results = {
            'ssh_attempts': 0,
            'unusual_activity': False,
            'firewall_status': 'unknown',
            'last_check': datetime.now().isoformat()
        }
        
        alerts = []
        
        # Check SSH failed attempts (Linux/macOS logs)
        try:
            if sys.platform == 'darwin':
                # macOS - check auth.log via console or syslog
                cmd = "log show --predicate 'eventMessage contains \"failed\" and eventMessage contains \"sshd\"' --last 1h --info 2>/dev/null | wc -l"
            else:
                # Linux
                cmd = "sudo grep -c 'Failed password' /var/log/auth.log 2>/dev/null || echo 0"
            
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10)
            failed_count = int(result.stdout.strip() or 0)
            results['ssh_attempts'] = failed_count
            
            threshold = self.config['alerts']['security']['failed_ssh_attempts']
            if failed_count >= threshold:
                alerts.append({
                    'type': 'security',
                    'message': f"Multiple failed SSH attempts detected: {failed_count} in the last hour"
                })
        except Exception as e:
            results['ssh_attempts'] = 'error_checking'
            print(f"[WARN] Could not check SSH attempts: {e}")
        
        # Check firewall status
        try:
            if sys.platform == 'darwin':
                cmd = "pfctl -sa 2>/dev/null | grep 'status' | head -1"
            else:
                cmd = "sudo ufw status 2>/dev/null | head -1"
            
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10)
            results['firewall_status'] = result.stdout.strip()[:50] or 'unknown'
        except Exception:
            results['firewall_status'] = 'check_failed'
        
        # Check for unusual outbound traffic (basic check)
        try:
            net_io = psutil.net_io_counters()
            # You could compare with baseline here
            results['bytes_sent'] = net_io.bytes_sent
            results['bytes_recv'] = net_io.bytes_recv
        except Exception:
            results['network_stats'] = 'unavailable'
        
        # Send security alerts
        for alert in alerts:
            self._send_telegram_alert(
                "Security Alert 🛡️",
                alert['message'],
                alert_type='security'
            )
        
        return results
    
    def save_metrics(self, metrics: dict):
        """Save metrics to data store for dashboard."""
        timestamp = datetime.now().isoformat()
        
        metrics_file = self.data_dir / f"metrics_{datetime.now().date().isoformat()}.json"
        
        if metrics_file.exists():
            with open(metrics_file, 'r') as f:
                historical = json.load(f)
        else:
            historical = []
        
        historical.append({
            'timestamp': timestamp,
            **metrics
        })
        
        # Keep only last N entries (retention policy)
        retention_days = self.config['dashboard']['retention_days']
        cutoff = datetime.now() - timedelta(days=retention_days)
        
        historical = [
            m for m in historical 
            if datetime.fromisoformat(m['timestamp']) > cutoff
        ]
        
        with open(metrics_file, 'w') as f:
            json.dump(historical, f, indent=2)
    
    def run_full_check(self) -> dict:
        """Run complete monitoring check."""
        print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Running full monitoring check...")
        
        results = {
            'timestamp': datetime.now().isoformat(),
            'cost': self.check_cost_anomaly(),
            'system': self.check_system_health(),
            'security': self.check_security_posture()
        }
        
        # Save metrics
        self.save_metrics(results)
        
        # Summary
        issues = []
        if results['cost'] and results['cost'].get('status') == 'alert':
            issues.append('cost')
        if results['system'].get('cpu', {}).get('status') in ['critical', 'warning']:
            issues.append('cpu')
        if results['system'].get('memory', {}).get('status') in ['critical', 'warning']:
            issues.append('memory')
        if results['system'].get('disk', {}).get('status') in ['critical', 'warning']:
            issues.append('disk')
        
        if issues:
            print(f"[SUMMARY] Issues found: {', '.join(issues)}")
        else:
            print("[SUMMARY] All systems normal")
        
        return results
    
    def start_continuous_monitoring(self, interval_seconds: int = 300):
        """Start continuous monitoring loop."""
        print(f"Starting proactive monitoring (interval: {interval_seconds}s)")
        print(f"Alerts will be sent to Telegram: {self.chat_id}")
        print("Press Ctrl+C to stop\n")
        
        while True:
            try:
                self.run_full_check()
                time.sleep(interval_seconds)
            except KeyboardInterrupt:
                print("\nMonitoring stopped.")
                break
            except Exception as e:
                print(f"[ERROR] Monitoring error: {e}")
                time.sleep(60)  # Wait before retry


def main():
    """Entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Proactive Monitoring System')
    parser.add_argument('--config', '-c', help='Path to config file')
    parser.add_argument('--once', action='store_true', help='Run single check and exit')
    parser.add_argument('--continuous', '-t', action='store_true', help='Run continuous monitoring')
    parser.add_argument('--interval', '-i', type=int, default=300, help='Check interval in seconds')
    
    args = parser.parse_args()
    
    monitor = ProactiveMonitor(config_path=args.config)
    
    if args.once:
        results = monitor.run_full_check()
        print(json.dumps(results, indent=2))
    elif args.continuous:
        monitor.start_continuous_monitoring(args.interval)
    else:
        # Default: one check
        results = monitor.run_full_check()
        print(json.dumps(results, indent=2))


if __name__ == '__main__':
    main()
