#!/usr/bin/env python3
"""
NexDev v3.0 - Track C: Production Hardening
Performance Regression Monitor

Auto-baseline after deployments, alert on >10% degradation
Tracks: response time, throughput, error rate, resource utilization
"""

import json
import subprocess
from pathlib import Path
from typing import Optional, Dict, List, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum


class Severity(Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class PerformanceMetric:
    timestamp: str
    deployment_id: str
    metric_name: str  # latency_p50, latency_p95, throughput, error_rate
    value: float
    unit: str
    baseline_value: float = None
    deviation_pct: float = None


@dataclass
class Baseline:
    metric_name: str
    baseline_value: float
    std_deviation: float
    measurement_period_start: str
    measurement_period_end: str
    sample_count: int
    confidence_level: float


@dataclass
class RegressionAlert:
    alert_id: str
    triggered_at: str
    severity: str
    metric_name: str
    current_value: float
    baseline_value: float
    deviation_pct: float
    deployment_id: str
    affected_services: List[str]
    recommendations: List[str]
    acknowledged: bool = False


class PerformanceMonitor:
    """Detect and alert on performance regressions"""
    
    METRICS_TO_TRACK = [
        'latency_p50',
        'latency_p95', 
        'latency_p99',
        'throughput_rps',
        'error_rate_percent',
        'cpu_utilization_percent',
        'memory_utilization_percent',
        'db_query_time_ms'
    ]
    
    DEFAULT_THRESHOLDS = {
        'latency_p50': {'warning': 10, 'critical': 25},
        'latency_p95': {'warning': 15, 'critical': 30},
        'latency_p99': {'warning': 20, 'critical': 40},
        'throughput_rps': {'warning': -10, 'critical': -20},  # Negative = decrease
        'error_rate_percent': {'warning': 50, 'critical': 100},  # Percentage increase
        'cpu_utilization_percent': {'warning': 20, 'critical': 40},
        'memory_utilization_percent': {'warning': 15, 'critical': 30}
    }
    
    def __init__(self, config_path: str = None):
        self.config = self._load_config(config_path)
        self.baseline_dir = Path.home() / '.openclaw' / 'workspace' / 'nexdev' / 'performance_baselines'
        self.metrics_dir = Path.home() / '.openclaw' / 'workspace' / 'nexdev' / 'performance_metrics'
        self.alerts_file = Path.home() / '.openclaw' / 'workspace' / 'nexdev' / 'performance_alerts.json'
        
        self.baseline_dir.mkdir(parents=True, exist_ok=True)
        self.metrics_dir.mkdir(parents=True, exist_ok=True)
        
    def _load_config(self, config_path: str) -> Dict:
        default_config = {
            'monitoring': {
                'interval_seconds': 60,
                'baseline_period_hours': 24,
                'comparison_window_hours': 1,
                'auto_baseline_after_deploy': True
            },
            'thresholds': self.DEFAULT_THRESHOLDS,
            'alerting': {
                'enabled': True,
                'channels': ['slack', 'email'],
                'cooldown_minutes': 30,
                'escalation_timeout_hours': 2
            },
            'integrations': {
                'cloudwatch': False,
                'datadog': False,
                'newrelic': False,
                'prometheus': False
            },
            'retention': {
                'metrics_days': 90,
                'baselines_count': 10
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
        
    async def collect_metrics(self, service_name: str, 
                             deployment_id: str = None) -> List[PerformanceMetric]:
        """
        Collect current performance metrics
        
        Args:
            service_name: Name of service to monitor
            deployment_id: Current deployment identifier
            
        Returns:
            List of collected metrics
        """
        deployment_id = deployment_id or self._get_current_deployment(service_name)
        metrics = []
        now = datetime.now().isoformat()
        
        # Collect from configured sources
        for integration, enabled in self.config['integrations'].items():
            if enabled:
                integration_metrics = await self._collect_from_integration(
                    integration, service_name, deployment_id
                )
                metrics.extend(integration_metrics)
                
        # If no integrations configured, generate sample data
        if not metrics:
            print("⚠️  No integrations configured - generating sample metrics")
            metrics = self._generate_sample_metrics(service_name, deployment_id, now)
            
        # Compare against baselines and flag regressions
        for metric in metrics:
            baseline = self._get_baseline(service_name, metric.metric_name)
            if baseline:
                metric.baseline_value = baseline.baseline_value
                metric.deviation_pct = self._calculate_deviation(
                    metric.value, baseline.baseline_value
                )
                
                # Check for regression
                await self._check_regression(service_name, metric, baseline)
                
        # Save metrics
        self._save_metrics(service_name, metrics)
        
        return metrics
        
    async def _collect_from_integration(self, integration: str, 
                                        service_name: str,
                                        deployment_id: str) -> List[PerformanceMetric]:
        """Collect metrics from external monitoring source"""
        metrics = []
        now = datetime.now().isoformat()
        
        try:
            if integration == 'cloudwatch':
                # Would use AWS CloudWatch API
                # Sample implementation
                metrics.append(PerformanceMetric(
                    timestamp=now,
                    deployment_id=deployment_id,
                    metric_name='latency_p50',
                    value=self._fetch_cloudwatch_metric(service_name, 'LatencyP50'),
                    unit='ms'
                ))
            elif integration == 'datadog':
                # Would use Datadog API
                pass
            elif integration == 'prometheus':
                # Would scrape Prometheus endpoint
                pass
                
        except Exception as e:
            print(f"Error collecting from {integration}: {e}")
            
        return metrics
        
    def _fetch_cloudwatch_metric(self, service_name: str, 
                                 metric_name: str) -> float:
        """Fetch metric from CloudWatch (placeholder)"""
        # Would call boto3 client.get_metric_statistics()
        # For demo, return random realistic value
        import random
        base_values = {
            'LatencyP50': 45,
            'LatencyP95': 120,
            'LatencyP99': 250,
            'RequestCount': 10000,
            'ErrorCode': 50
        }
        
        base = base_values.get(metric_name, 100)
        return base + random.uniform(-base * 0.1, base * 0.1)
        
    def _generate_sample_metrics(self, service_name: str, 
                                 deployment_id: str, now: str) -> List[PerformanceMetric]:
        """Generate sample metrics for demo/testing"""
        import random
        
        base_latency = 50 + random.uniform(-5, 5)
        
        return [
            PerformanceMetric(
                timestamp=now,
                deployment_id=deployment_id,
                metric_name='latency_p50',
                value=base_latency,
                unit='ms'
            ),
            PerformanceMetric(
                timestamp=now,
                deployment_id=deployment_id,
                metric_name='latency_p95',
                value=base_latency * 2.2 + random.uniform(-10, 10),
                unit='ms'
            ),
            PerformanceMetric(
                timestamp=now,
                deployment_id=deployment_id,
                metric_name='latency_p99',
                value=base_latency * 4.5 + random.uniform(-20, 20),
                unit='ms'
            ),
            PerformanceMetric(
                timestamp=now,
                deployment_id=deployment_id,
                metric_name='throughput_rps',
                value=1250 + random.uniform(-50, 50),
                unit='requests/sec'
            ),
            PerformanceMetric(
                timestamp=now,
                deployment_id=deployment_id,
                metric_name='error_rate_percent',
                value=0.12 + random.uniform(-0.05, 0.05),
                unit='percent'
            ),
            PerformanceMetric(
                timestamp=now,
                deployment_id=deployment_id,
                metric_name='cpu_utilization_percent',
                value=35 + random.uniform(-5, 5),
                unit='percent'
            ),
            PerformanceMetric(
                timestamp=now,
                deployment_id=deployment_id,
                metric_name='memory_utilization_percent',
                value=62 + random.uniform(-3, 3),
                unit='percent'
            )
        ]
        
    def _calculate_deviation(self, current: float, baseline: float) -> float:
        """Calculate percentage deviation from baseline"""
        if baseline == 0:
            return 0
        return ((current - baseline) / baseline) * 100
        
    async def _check_regression(self, service_name: str, 
                                metric: PerformanceMetric,
                                baseline: Baseline):
        """Check if metric shows regression and alert if needed"""
        if metric.deviation_pct is None:
            return
            
        thresholds = self.config['thresholds'].get(metric.metric_name, {})
        warning_threshold = thresholds.get('warning', 10)
        critical_threshold = thresholds.get('critical', 25)
        
        # Determine severity
        severity = None
        if abs(metric.deviation_pct) >= critical_threshold:
            severity = Severity.CRITICAL
        elif abs(metric.deviation_pct) >= warning_threshold:
            severity = Severity.WARNING
            
        if severity:
            # Create alert
            alert = await self._create_alert(
                service_name=service_name,
                metric=metric,
                baseline=baseline,
                severity=severity
            )
            
            # Send notification
            if self.config['alerting']['enabled']:
                await self._send_alert_notification(alert)
                
    async def _create_alert(self, service_name: str, metric: PerformanceMetric,
                           baseline: Baseline, severity: Severity) -> RegressionAlert:
        """Create performance regression alert"""
        alert_id = f"perf-{datetime.now().strftime('%Y%m%d%H%M%S')}-{hash(str(metric)) % 10000}"
        
        # Generate recommendations based on metric type
        recommendations = self._generate_recommendations(metric)
        
        alert = RegressionAlert(
            alert_id=alert_id,
            triggered_at=datetime.now().isoformat(),
            severity=severity.value,
            metric_name=metric.metric_name,
            current_value=metric.value,
            baseline_value=baseline.baseline_value,
            deviation_pct=metric.deviation_pct,
            deployment_id=metric.deployment_id,
            affected_services=[service_name],
            recommendations=recommendations
        )
        
        # Save alert
        alerts = self._load_alerts()
        alerts.append(asdict(alert))
        self._save_alerts(alerts)
        
        return alert
        
    def _generate_recommendations(self, metric: PerformanceMetric) -> List[str]:
        """Generate actionable recommendations based on metric type"""
        recommendations = []
        
        if 'latency' in metric.metric_name:
            recommendations.extend([
                "Review recent code changes for performance impact",
                "Check database query performance",
                "Verify infrastructure capacity is adequate",
                "Consider caching frequently-accessed data",
                "Profile application to identify bottlenecks"
            ])
        elif 'throughput' in metric.metric_name:
            recommendations.extend([
                "Check for increased traffic patterns",
                "Review horizontal scaling configuration",
                "Verify load balancer health",
                "Check downstream service dependencies"
            ])
        elif 'error_rate' in metric.metric_name:
            recommendations.extend([
                "Review application logs for exceptions",
                "Check dependent service health",
                "Verify recent deployments",
                "Review error budgets and SLOs"
            ])
        elif 'cpu' in metric.metric_name:
            recommendations.extend([
                "Profile CPU-intensive operations",
                "Check for infinite loops or inefficient algorithms",
                "Review thread pool configurations",
                "Consider increasing instance count"
            ])
        elif 'memory' in metric.metric_name:
            recommendations.extend([
                "Check for memory leaks",
                "Review cache sizes and eviction policies",
                "Verify garbage collection settings",
                "Consider increasing memory allocation"
            ])
            
        return recommendations[:5]  # Limit to top 5
        
    async def _send_alert_notification(self, alert: RegressionAlert):
        """Send alert notification via configured channels"""
        # Would integrate with SlackNotifier from Track B
        # For now, log the alert
        
        notification = {
            'timestamp': datetime.now().isoformat(),
            'alert_id': alert.alert_id,
            'severity': alert.severity,
            'message': f"⚠️ Performance Regression Detected: {alert.metric_name} "
                      f"(+{alert.deviation_pct:.1f}% from baseline)",
            'recommendations': alert.recommendations
        }
        
        print(f"\n🚨 {notification['message']}")
        for rec in alert.recommendations[:2]:
            print(f"   → {rec}")
            
    def establish_baseline(self, service_name: str, 
                          period_hours: int = 24) -> Dict:
        """
        Establish performance baseline from recent metrics
        
        Args:
            service_name: Service to baseline
            period_hours: How far back to look (default 24h)
            
        Returns:
            Baseline establishment results
        """
        cutoff_time = datetime.now() - timedelta(hours=period_hours)
        
        baselines = {}
        
        for metric_name in self.METRICS_TO_TRACK:
            # Load historical metrics
            metrics = self._load_historical_metrics(service_name, cutoff_time)
            
            if not metrics:
                continue
                
            # Filter for this metric
            metric_values = [
                m['value'] for m in metrics 
                if m.get('metric_name') == metric_name
            ]
            
            if len(metric_values) < 10:
                continue
                
            # Calculate statistics
            import statistics
            mean_value = statistics.mean(metric_values)
            std_dev = statistics.stdev(metric_values) if len(metric_values) > 1 else 0
            
            baseline = Baseline(
                metric_name=metric_name,
                baseline_value=mean_value,
                std_deviation=std_dev,
                measurement_period_start=cutoff_time.isoformat(),
                measurement_period_end=datetime.now().isoformat(),
                sample_count=len(metric_values),
                confidence_level=0.95
            )
            
            baselines[metric_name] = asdict(baseline)
            
        # Save baselines
        self._save_baseline(service_name, baselines)
        
        summary = {
            'service': service_name,
            'period_hours': period_hours,
            'samples_per_metric': {},
            'status': 'complete'
        }
        
        # Count samples properly for each metric
        for m in self.METRICS_TO_TRACK:
            baseline_data = baselines.get(m, {})
            if isinstance(baseline_data, dict):
                summary['samples_per_metric'][m] = baseline_data.get('sample_count', 0)
            else:
                summary['samples_per_metric'][m] = 0
        
        print(f"\n✅ Established baseline for {service_name}")
        print(f"   Period: {period_hours} hours")
        print(f"   Metrics baselined: {len(baselines)}")
        
        return summary
        
    def _get_baseline(self, service_name: str, metric_name: str) -> Optional[Baseline]:
        """Get stored baseline for a service/metric combination"""
        baseline_file = self.baseline_dir / f"{service_name}_baselines.json"
        
        if not baseline_file.exists():
            return None
            
        try:
            with open(baseline_file) as f:
                baselines = json.load(f)
                
            if metric_name not in baselines:
                return None
                
            data = baselines[metric_name]
            return Baseline(**data)
            
        except Exception:
            return None
            
    def _load_historical_metrics(self, service_name: str, 
                                 since: datetime) -> List[Dict]:
        """Load historical metrics from file storage"""
        metrics = []
        
        metrics_file = self.metrics_dir / f"{service_name}_metrics.jsonl"
        
        if not metrics_file.exists():
            return metrics
            
        try:
            with open(metrics_file) as f:
                for line in f:
                    try:
                        metric = json.loads(line)
                        metric_timestamp = datetime.fromisoformat(metric['timestamp'])
                        
                        if metric_timestamp >= since:
                            metrics.append(metric)
                    except json.JSONDecodeError:
                        continue
                            
        except Exception:
            pass
            
        return metrics
        
    def _save_metrics(self, service_name: str, 
                      metrics: List[PerformanceMetric]):
        """Save metrics to JSONL file"""
        metrics_file = self.metrics_dir / f"{service_name}_metrics.jsonl"
        
        with open(metrics_file, 'a') as f:
            for metric in metrics:
                f.write(json.dumps(asdict(metric)) + '\n')
                
        # Clean up old metrics beyond retention period
        self._cleanup_old_metrics(service_name)
        
    def _cleanup_old_metrics(self, service_name: str):
        """Remove metrics older than retention period"""
        metrics_file = self.metrics_dir / f"{service_name}_metrics.jsonl"
        
        if not metrics_file.exists():
            return
            
        retention_days = self.config['retention']['metrics_days']
        cutoff = datetime.now() - timedelta(days=retention_days)
        
        # Read all metrics
        metrics = []
        try:
            with open(metrics_file) as f:
                for line in f:
                    try:
                        metric = json.loads(line)
                        metric_timestamp = datetime.fromisoformat(metric['timestamp'])
                        
                        if metric_timestamp >= cutoff:
                            metrics.append(metric)
                    except json.JSONDecodeError:
                        continue
        except Exception:
            return
            
        # Rewrite file with filtered metrics
        with open(metrics_file, 'w') as f:
            for metric in metrics:
                f.write(json.dumps(metric) + '\n')
                
    def _save_baseline(self, service_name: str, baselines: Dict):
        """Save baseline to file"""
        baseline_file = self.baseline_dir / f"{service_name}_baselines.json"
        
        # Load existing baselines
        all_baselines = {}
        if baseline_file.exists():
            try:
                with open(baseline_file) as f:
                    all_baselines = json.load(f)
            except Exception:
                pass
                
        # Update with new baselines
        all_baselines.update({
            'updated_at': datetime.now().isoformat(),
            **baselines
        })
        
        with open(baseline_file, 'w') as f:
            json.dump(all_baselines, f, indent=2)
            
    def _load_alerts(self) -> List[Dict]:
        """Load alerts from file"""
        if not self.alerts_file.exists():
            return []
            
        try:
            with open(self.alerts_file) as f:
                return json.load(f)
        except Exception:
            return []
            
    def _save_alerts(self, alerts: List[Dict]):
        """Save alerts to file"""
        with open(self.alerts_file, 'w') as f:
            json.dump(alerts, f, indent=2, default=str)
            
    def _get_current_deployment(self, service_name: str) -> str:
        """Get current deployment ID (would pull from deployment system)"""
        # Placeholder - would integrate with GitHub Actions, ArgoCD, etc.
        return f"deploy-{datetime.now().strftime('%Y%m%d-%H%M')}"
        
    def get_dashboard_data(self, service_name: str) -> Dict:
        """Get data for performance dashboard"""
        baselines = self._load_baseline_file(service_name)
        recent_metrics = self._get_recent_metrics(service_name, hours=24)
        active_alerts = self._get_active_alerts(service_name)
        
        return {
            'service': service_name,
            'last_updated': datetime.now().isoformat(),
            'baselines': baselines,
            'recent_metrics': recent_metrics,
            'active_alerts': active_alerts
        }
        
    def _load_baseline_file(self, service_name: str) -> Dict:
        """Load baseline file"""
        baseline_file = self.baseline_dir / f"{service_name}_baselines.json"
        
        if not baseline_file.exists():
            return {}
            
        try:
            with open(baseline_file) as f:
                return json.load(f)
        except Exception:
            return {}
            
    def _get_recent_metrics(self, service_name: str, 
                           hours: int = 24) -> List[Dict]:
        """Get recent metrics"""
        metrics = self._load_historical_metrics(
            service_name,
            datetime.now() - timedelta(hours=hours)
        )
        
        # Group by metric name
        grouped = {}
        for metric in metrics:
            name = metric['metric_name']
            if name not in grouped:
                grouped[name] = []
            grouped[name].append(metric)
            
        return grouped
        
    def _get_active_alerts(self, service_name: str) -> List[Dict]:
        """Get unacknowledged alerts for service"""
        all_alerts = self._load_alerts()
        
        active = [
            a for a in all_alerts
            if service_name in a.get('affected_services', [])
            and not a.get('acknowledged', False)
        ]
        
        return sorted(active, key=lambda x: x['triggered_at'], reverse=True)[:10]


# CLI Entry Point
if __name__ == '__main__':
    import asyncio
    import sys
    
    print("NexDev Performance Monitor v3.0")
    print("=" * 50)
    
    monitor = PerformanceMonitor()
    
    if len(sys.argv) < 2:
        print("\nUsage:")
        print("  python performance_monitor.py collect <service_name>")
        print("  python performance_monitor.py baseline <service_name> [--hours 24]")
        print("  python performance_monitor.py dashboard <service_name>")
        print("  python performance_monitor.py alerts")
        sys.exit(1)
        
    command = sys.argv[1]
    
    if command == 'collect':
        if len(sys.argv) < 3:
            print("Usage: python performance_monitor.py collect <service_name>")
            sys.exit(1)
            
        service = sys.argv[2]
        
        print(f"\n📊 Collecting metrics for: {service}")
        metrics = asyncio.run(monitor.collect_metrics(service))
        
        print(f"\nCollected {len(metrics)} metrics:")
        for m in metrics:
            if m.deviation_pct:
                status = "🚨" if abs(m.deviation_pct) > 15 else "⚠️" if abs(m.deviation_pct) > 10 else "✅"
                print(f"  {status} {m.metric_name}: {m.value:.2f} {m.unit} "
                      f"(vs baseline {m.baseline_value:.2f}, {m.deviation_pct:+.1f}%)")
            else:
                print(f"  • {m.metric_name}: {m.value:.2f} {m.unit}")
                
    elif command == 'baseline':
        if len(sys.argv) < 3:
            print("Usage: python performance_monitor.py baseline <service_name> [--hours 24]")
            sys.exit(1)
            
        service = sys.argv[2]
        hours = 24
        
        for i, arg in enumerate(sys.argv):
            if arg == '--hours' and i + 1 < len(sys.argv):
                hours = int(sys.argv[i + 1])
                
        result = monitor.establish_baseline(service, hours)
        print(json.dumps(result, indent=2))
        
    elif command == 'dashboard':
        if len(sys.argv) < 3:
            print("Usage: python performance_monitor.py dashboard <service_name>")
            sys.exit(1)
            
        service = sys.argv[2]
        data = monitor.get_dashboard_data(service)
        
        print(f"\n📈 Performance Dashboard: {service}")
        print(f"Last updated: {data['last_updated']}")
        print(f"\nBaselines ({len(data['baselines'])} metrics):")
        for metric_name, baseline in data['baselines'].items():
            if isinstance(baseline, dict) and 'baseline_value' in baseline:
                print(f"  • {metric_name}: {baseline['baseline_value']:.2f} "
                      f"(±{baseline['std_deviation']:.2f})")
                      
        print(f"\nActive alerts: {len(data['active_alerts'])}")
        
    elif command == 'alerts':
        alerts = monitor._load_alerts()
        
        if not alerts:
            print("\nNo active alerts")
        else:
            print(f"\n{len(alerts)} total alert(s):\n")
            for alert in alerts[-10:]:
                severity_icon = '🔴' if alert['severity'] == 'critical' else '🟡'
                print(f"{severity_icon} {alert['alert_id']} - {alert['metric_name']} "
                      f"(+{alert['deviation_pct']:.1f}%)")
