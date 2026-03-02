#!/usr/bin/env python3
"""
Cross-Service Monitor - Main Orchestrator
Runs all monitors, correlation engine, and alerting in one process
"""

import asyncio
import signal
import sys
from datetime import datetime
import logging
import yaml
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


class CrossServiceMonitor:
    """Main orchestrator for cross-service monitoring"""
    
    def __init__(self, config_path: str = None):
        self.config_path = Path(config_path) if config_path else Path(__file__).parent / "config.yaml"
        self.config = {}
        self.monitors = {}
        self.running = False
        
        # Import components (lazy load)
        self.aws_monitor = None
        self.snowflake_monitor = None
        self.crm_monitor = None
        self.correlator = None
        self.pipeline_tracker = None
        self.alert_manager = None
        
    def load_config(self):
        """Load configuration"""
        if self.config_path.exists():
            with open(self.config_path) as f:
                self.config = yaml.safe_load(f)
            logger.info(f"Loaded config from {self.config_path}")
        else:
            logger.warning(f"Config file not found: {self.config_path}, using defaults")
            self.config = self._default_config()
            
    def _default_config(self) -> dict:
        """Default configuration"""
        return {
            'services': {
                'aws': {'enabled': True, 'region': 'us-east-1'},
                'snowflake': {'enabled': True, 'warehouse': 'COMPUTE_WH'},
                'crm': {'hubspot': {'enabled': False}, 'salesforce': {'enabled': False}}
            },
            'monitoring': {
                'check_interval': 60,
                'aws_check_interval': 60,
                'snowflake_check_interval': 300,
                'crm_check_interval': 300
            },
            'alerting': {
                'telegram_chat_id': '',
                'slack_webhook': ''
            }
        }
        
    async def initialize(self):
        """Initialize all components"""
        self.load_config()
        
        # Dynamically import to avoid errors if dependencies missing
        try:
            from monitors.aws_monitor import AWSMonitor
            if self.config.get('services', {}).get('aws', {}).get('enabled', True):
                self.aws_monitor = AWSMonitor(
                    region=self.config['services']['aws'].get('region', 'us-east-1')
                )
                self.monitors['aws'] = self.aws_monitor
                logger.info("✓ AWS Monitor initialized")
        except ImportError as e:
            logger.warning(f"AWS Monitor not available: {e}")
            
        try:
            from monitors.snowflake_monitor import SnowflakeMonitor
            sf_config = self.config.get('services', {}).get('snowflake', {})
            if sf_config.get('enabled', True):
                # Get credentials from environment or config
                import os
                self.snowflake_monitor = SnowflakeMonitor(
                    account=sf_config.get('account') or os.getenv('SNOWFLAKE_ACCOUNT'),
                    user=sf_config.get('user') or os.getenv('SNOWFLAKE_USER'),
                    private_key=os.getenv('SNOWFLAKE_PRIVATE_KEY'),
                    password=os.getenv('SNOWFLAKE_PASSWORD'),
                    warehouse=sf_config.get('warehouse', 'COMPUTE_WH'),
                    database=sf_config.get('database', 'APPLICATIONS'),
                    role=sf_config.get('role', 'ACCOUNTADMIN')
                )
                self.monitors['snowflake'] = self.snowflake_monitor
                logger.info("✓ Snowflake Monitor initialized")
        except ImportError as e:
            logger.warning(f"Snowflake Monitor not available: {e}")
        except Exception as e:
            logger.warning(f"Snowflake Monitor initialization failed: {e}")
            
        try:
            from monitors.crm_monitor import CompositeCRMMonitor
            crm_config = self.config.get('services', {}).get('crm', {})
            if any(crm_config.get(s, {}).get('enabled', False) for s in ['hubspot', 'salesforce']):
                self.crm_monitor = CompositeCRMMonitor(crm_config)
                self.monitors['crm'] = self.crm_monitor
                logger.info("✓ CRM Monitor initialized")
        except ImportError as e:
            logger.warning(f"CRM Monitor not available: {e}")
            
        # Initialize correlation engine
        try:
            from engine.correlator import CorrelationEngine, PipelineTracker
            self.correlator = CorrelationEngine({
                'max_event_buffer': 10000,
                'correlation_window': 300,
                'pipeline_definitions': self.config.get('pipeline_definitions', [])
            })
            self.pipeline_tracker = PipelineTracker(
                pipelines=self.config.get('pipeline_definitions', []),
                config={'max_runs_history': 100}
            )
            logger.info("✓ Correlation Engine initialized")
        except ImportError as e:
            logger.warning(f"Correlation Engine not available: {e}")
            
        # Initialize alert manager
        try:
            from engine.alert_manager import AlertManager
            
            telegram_token = (
                self.config.get('alerting', {}).get('telegram_bot_token') or
                __import__('os').getenv('TELEGRAM_BOT_TOKEN', '')
            )
            
            self.alert_manager = AlertManager({
                'telegram': {
                    'bot_token': telegram_token,
                    'chat_id': self.config.get('alerting', {}).get('telegram_chat_id', ''),
                    'dashboard_url': self.config.get('dashboard', {}).get('url', '')
                },
                'dedup_window_seconds': 300
            })
            logger.info("✓ Alert Manager initialized")
        except ImportError as e:
            logger.warning(f"Alert Manager not available: {e}")
            
    async def run_health_checks(self):
        """Run periodic health checks across all services"""
        interval = self.config.get('monitoring', {}).get('check_interval', 60)
        
        while self.running:
            try:
                logger.info("Running health checks...")
                
                # Check AWS
                if self.aws_monitor:
                    await self._check_aws_health()
                    
                # Check Snowflake
                if self.snowflake_monitor:
                    await self._check_snowflake_health()
                    
                # Check CRM
                if self.crm_monitor:
                    await self._check_crm_health()
                    
                # Send bulk alert if there are issues
                if self.correlator:
                    issues = self.correlator.get_active_issues()
                    critical_issues = [i for i in issues if i['severity'] == 'critical']
                    if critical_issues and self.alert_manager:
                        await self.alert_manager.send_bulk_alert(critical_issues[:5])
                
            except Exception as e:
                logger.error(f"Health check error: {e}")
                
            await asyncio.sleep(interval)
            
    async def _check_aws_health(self):
        """Check AWS Lambda health"""
        try:
            lambda_health = await self.aws_monitor.get_all_lambda_health()
            
            for func_name, metrics in lambda_health.items():
                if metrics.error_rate > 0.05:
                    # Create correlation event
                    from engine.correlator import CorrelationEvent
                    
                    event = CorrelationEvent(
                        timestamp=datetime.utcnow(),
                        source='aws',
                        resource=func_name,
                        event_type='error',
                        severity='warning' if metrics.error_rate < 0.1 else 'critical',
                        details={
                            'invocations': metrics.invocations,
                            'errors': metrics.errors,
                            'error_rate': metrics.error_rate
                        }
                    )
                    self.correlator.add_event(event)
                    
                    # Send alert
                    if self.alert_manager:
                        from engine.alert_manager import Alert
                        alert = Alert(
                            alert_id=f"AWS-{func_name}-{int(datetime.utcnow().timestamp())}",
                            title=f"Lambda Error Rate: {func_name}",
                            message=f"Error rate {metrics.error_rate:.1%} ({metrics.errors}/{metrics.invocations})",
                            severity='warning' if metrics.error_rate < 0.1 else 'critical',
                            source='aws',
                            resource=func_name
                        )
                        await self.alert_manager.send_alert(alert)
                        
        except Exception as e:
            logger.error(f"AWS health check failed: {e}")
            
    async def _check_snowflake_health(self):
        """Check Snowflake query health"""
        try:
            query_health = await self.snowflake_monitor.check_query_health()
            
            if query_health.failure_rate > 0.1:
                from engine.correlator import CorrelationEvent
                
                event = CorrelationEvent(
                    timestamp=datetime.utcnow(),
                    source='snowflake',
                    resource='query-execution',
                    event_type='failure',
                    severity='warning',
                    details={
                        'total_queries': query_health.total_queries,
                        'failures': query_health.failed_queries,
                        'failure_rate': query_health.failure_rate
                    }
                )
                self.correlator.add_event(event)
                
                if self.alert_manager:
                    from engine.alert_manager import Alert
                    alert = Alert(
                        alert_id=f"SF-QRY-{int(datetime.utcnow().timestamp())}",
                        title="Snowflake Query Failure Rate High",
                        message=f"Failure rate: {query_health.failure_rate:.1%} ({query_health.failed_queries}/{query_health.total_queries})",
                        severity='warning',
                        source='snowflake',
                        resource='query-execution'
                    )
                    await self.alert_manager.send_alert(alert)
                    
        except Exception as e:
            logger.error(f"Snowflake health check failed: {e}")
            
    async def _check_crm_health(self):
        """Check CRM API health"""
        try:
            crm_health = await self.crm_monitor.get_all_health()
            
            for service, health in crm_health.items():
                if health.status == 'down':
                    from engine.correlator import CorrelationEvent
                    
                    event = CorrelationEvent(
                        timestamp=datetime.utcnow(),
                        source='crm',
                        resource=service,
                        event_type='failure',
                        severity='critical',
                        details={'status': health.status, 'latency_ms': health.avg_latency_ms}
                    )
                    self.correlator.add_event(event)
                    
                    if self.alert_manager:
                        from engine.alert_manager import Alert
                        alert = Alert(
                            alert_id=f"CRM-{service}-DOWN",
                            title=f"{service.upper()} API Down",
                            message=f"{service.capitalize()} API is not responding",
                            severity='critical',
                            source='crm',
                            resource=service
                        )
                        await self.alert_manager.send_alert(alert)
                        
        except Exception as e:
            logger.error(f"CRM health check failed: {e}")
            
    async def start_dashboard(self, port: int = 8080):
        """Start the web dashboard"""
        try:
            import uvicorn
            from dashboard.app import app
            
            logger.info(f"Starting dashboard on port {port}")
            
            # Run uvicorn in separate task
            config = uvicorn.Config(app, host="0.0.0.0", port=port, log_level="info")
            server = uvicorn.Server(config)
            await server.serve()
            
        except ImportError:
            logger.warning("Dashboard not available (uvicorn/fastapi not installed)")
            
    async def run(self, dashboard_port: int = 8080, no_dashboard: bool = False):
        """Run the monitor with optional dashboard"""
        self.running = True
        
        # Setup signal handlers
        loop = asyncio.get_event_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, lambda: asyncio.create_task(self.stop()))
            
        logger.info("=" * 60)
        logger.info("Cross-Service Correlation Monitor Starting")
        logger.info("=" * 60)
        
        # Initialize components
        await self.initialize()
        
        # Start tasks
        tasks = [asyncio.create_task(self.run_health_checks())]
        
        if not no_dashboard:
            tasks.append(asyncio.create_task(self.start_dashboard(dashboard_port)))
            
        # Wait for tasks
        try:
            await asyncio.gather(*tasks)
        except asyncio.CancelledError:
            pass
        finally:
            await self.stop()
            
    async def stop(self):
        """Stop the monitor"""
        logger.info("Shutting down Cross-Service Monitor...")
        self.running = False


def main():
    """Entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Cross-Service Correlation Monitor")
    parser.add_argument('--config', '-c', help='Path to config file')
    parser.add_argument('--port', '-p', type=int, default=8080, help='Dashboard port')
    parser.add_argument('--no-dashboard', action='store_true', help='Disable web dashboard')
    
    args = parser.parse_args()
    
    monitor = CrossServiceMonitor(config_path=args.config)
    
    try:
        asyncio.run(monitor.run(dashboard_port=args.port, no_dashboard=args.no_dashboard))
    except KeyboardInterrupt:
        logger.info("Interrupted by user")


if __name__ == "__main__":
    main()
