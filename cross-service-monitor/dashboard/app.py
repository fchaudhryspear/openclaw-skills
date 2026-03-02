"""
Cross-Service Monitor Dashboard API
FastAPI backend providing unified health view and alerting
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import logging
import yaml
import os
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Import monitors and engine
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from monitors.aws_monitor import AWSMonitor
from monitors.snowflake_monitor import SnowflakeMonitor
from monitors.crm_monitor import CompositeCRMMonitor
from engine.correlator import CorrelationEngine, PipelineTracker, CorrelationEvent
from engine.alert_manager import AlertManager, Alert

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Cross-Service Correlation Monitor",
    description="Track data pipelines across AWS → Snowflake → CRMs",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Pydantic models
class HealthResponse(BaseModel):
    status: str
    timestamp: str
    services: Dict[str, str]


class PipelineStatus(BaseModel):
    name: str
    status: str
    lag_minutes: Optional[float]
    last_run: Optional[str]
    success_rate: float


class AlertResponse(BaseModel):
    alert_id: str
    title: str
    message: str
    severity: str
    source: str
    resource: str
    timestamp: str


# Global state
config: Dict = {}
monitors: Dict = {}
correlator: CorrelationEngine = None
pipeline_tracker: PipelineTracker = None
alert_manager: AlertManager = None
health_task = None


def load_config():
    """Load configuration from YAML file"""
    config_path = Path(__file__).parent.parent / "config.yaml"
    
    if config_path.exists():
        with open(config_path) as f:
            return yaml.safe_load(f)
    return {}


def initialize_components():
    """Initialize all monitor and engine components"""
    global config, monitors, correlator, pipeline_tracker, alert_manager
    
    config = load_config()
    
    # Initialize AWS Monitor
    aws_config = config.get('services', {}).get('aws', {})
    if aws_config.get('enabled', True):
        monitors['aws'] = AWSMonitor(region=aws_config.get('region', 'us-east-1'))
        logger.info("AWS Monitor initialized")
    
    # Initialize Snowflake Monitor
    sf_config = config.get('services', {}).get('snowflake', {})
    if sf_config.get('enabled', True):
        monitors['snowflake'] = SnowflakeMonitor(
            account=sf_config.get('account'),
            user=sf_config.get('user'),
            warehouse=sf_config.get('warehouse', 'COMPUTE_WH'),
            database=sf_config.get('database', 'APPLICATIONS'),
            role=sf_config.get('role', 'ACCOUNTADMIN')
        )
        logger.info("Snowflake Monitor initialized")
    
    # Initialize CRM Monitor
    crm_config = config.get('services', {}).get('crm', {})
    if any(crm_config.get(service, {}).get('enabled', False) 
           for service in ['hubspot', 'salesforce']):
        monitors['crm'] = CompositeCRMMonitor(crm_config)
        logger.info("CRM Monitor initialized")
    
    # Initialize Correlation Engine
    correlator = CorrelationEngine({
        'max_event_buffer': 10000,
        'correlation_window': 300,
        'pipeline_definitions': config.get('pipeline_definitions', [])
    })
    logger.info("Correlation Engine initialized")
    
    # Initialize Pipeline Tracker
    pipeline_tracker = PipelineTracker(
        pipelines=config.get('pipeline_definitions', []),
        config={'max_runs_history': 100}
    )
    logger.info("Pipeline Tracker initialized")
    
    # Initialize Alert Manager
    alert_manager = AlertManager({
        'slack': config.get('alerting', {}).get('slack', {}),
        'telegram': {
            'bot_token': os.getenv('TELEGRAM_BOT_TOKEN', ''),
            'chat_id': config.get('alerting', {}).get('telegram_chat_id', ''),
            'dashboard_url': config.get('dashboard', {}).get('url', '')
        },
        'email': {
            'smtp_server': config.get('alerting', {}).get('email', {}).get('smtp_server'),
            'smtp_port': config.get('alerting', {}).get('email', {}).get('smtp_port', 587),
            'username': os.getenv('EMAIL_USERNAME', ''),
            'password': os.getenv('EMAIL_PASSWORD', ''),
            'recipients': [os.getenv('ALERT_EMAIL', 'faisal@credologi.com')],
            'dashboard_url': config.get('dashboard', {}).get('url', '')
        },
        'routing_rules': config.get('alerting', {}).get('channels', {}),
        'dedup_window_seconds': 300
    })
    logger.info("Alert Manager initialized")


# Startup/Shutdown
@app.on_event("startup")
async def startup_event():
    """Initialize on startup"""
    initialize_components()
    logger.info("Cross-Service Monitor started")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("Cross-Service Monitor shutting down")


# Health Endpoints
@app.get("/api/v1/health", response_model=HealthResponse)
async def health_check():
    """System health check"""
    services = {}
    
    for name in monitors.keys():
        services[name] = "configured"
        
    return HealthResponse(
        status="healthy",
        timestamp=datetime.utcnow().isoformat(),
        services=services
    )


@app.get("/api/v1/health/detailed")
async def detailed_health():
    """Detailed health across all services"""
    results = {
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat(),
        'services': {},
        'pipelines': {},
        'alerts_summary': {}
    }
    
    # AWS Health
    if 'aws' in monitors:
        try:
            aws_health = await monitors['aws'].get_all_lambda_health()
            functions_status = {
                name: {'status': 'error' if m.error_rate > 0.05 else 'healthy'}
                for name, m in aws_health.items()
            }
            results['services']['aws'] = {
                'status': 'healthy' if all(f['status'] == 'healthy' for f in functions_status.values()) else 'degraded',
                'functions': functions_status,
                'total_functions': len(aws_health)
            }
        except Exception as e:
            results['services']['aws'] = {'status': 'error', 'error': str(e)}
            
    # Snowflake Health
    if 'snowflake' in monitors:
        try:
            query_health = await monitors['snowflake'].check_query_health()
            results['services']['snowflake'] = {
                'status': 'healthy' if query_health.success_rate > 0.9 else 'degraded',
                'query_success_rate': query_health.success_rate,
                'queries_24h': query_health.total_queries,
                'failures_24h': query_health.failed_queries,
                'avg_execution_time_ms': query_health.avg_execution_time_ms
            }
        except Exception as e:
            results['services']['snowflake'] = {'status': 'error', 'error': str(e)}
    
    # CRM Health
    if 'crm' in monitors:
        try:
            crm_health = await monitors['crm'].get_all_health()
            crm_status = {
                name: {'status': h.status, 'latency_ms': h.avg_latency_ms}
                for name, h in crm_health.items()
            }
            results['services']['crm'] = {
                'status': 'healthy' if all(h.status != 'down' for h in crm_health.values()) else 'degraded',
                'systems': crm_status
            }
        except Exception as e:
            results['services']['crm'] = {'status': 'error', 'error': str(e)}
    
    # Pipeline Status
    if pipeline_tracker:
        results['pipelines'] = pipeline_tracker.check_all_pipelines()
    
    # Alerts Summary
    if alert_manager:
        results['alerts_summary'] = alert_manager.get_alert_summary()
    
    # Overall status
    service_statuses = [s.get('status', 'unknown') for s in results['services'].values()]
    if 'error' in service_statuses:
        results['status'] = 'critical'
    elif 'degraded' in service_statuses:
        results['status'] = 'warning'
        
    return results


# Pipeline Endpoints
@app.get("/api/v1/pipelines")
async def list_pipelines():
    """List all configured pipelines"""
    return {
        'pipelines': config.get('pipeline_definitions', []),
        'count': len(config.get('pipeline_definitions', []))
    }


@app.get("/api/v1/pipelines/status")
async def get_pipeline_status():
    """Get status of all pipelines"""
    if not pipeline_tracker:
        raise HTTPException(status_code=503, detail="Pipeline tracker not initialized")
        
    return pipeline_tracker.check_all_pipelines()


@app.get("/api/v1/pipelines/{pipeline_name}/status")
async def get_single_pipeline_status(pipeline_name: str):
    """Get status of specific pipeline"""
    if not pipeline_tracker:
        raise HTTPException(status_code=503, detail="Pipeline tracker not initialized")
        
    status = pipeline_tracker.get_pipeline_status(pipeline_name)
    if status['status'] == 'unknown':
        raise HTTPException(status_code=404, detail=f"Pipeline {pipeline_name} not found")
        
    return status


# Metrics Endpoints
@app.get("/api/v1/metrics/aws")
async def get_aws_metrics():
    """Get AWS service metrics"""
    if 'aws' not in monitors:
        raise HTTPException(status_code=503, detail="AWS monitor not available")
        
    lambda_health = await monitors['aws'].get_all_lambda_health()
    
    return {
        'lambdas': {
            name: {
                'invocations': m.invocations,
                'errors': m.errors,
                'error_rate': m.error_rate,
                'duration_avg_ms': m.duration_avg_ms,
                'throttles': m.throttle_count
            }
            for name, m in lambda_health.items()
        },
        'timestamp': datetime.utcnow().isoformat()
    }


@app.get("/api/v1/metrics/snowflake")
async def get_snowflake_metrics():
    """Get Snowflake metrics"""
    if 'snowflake' not in monitors:
        raise HTTPException(status_code=503, detail="Snowflake monitor not available")
        
    query_health = await monitors['snowflake'].check_query_health()
    warehouse_status = await monitors['snowflake'].check_warehouse_status()
    storage = await monitors['snowflake'].check_storage_usage()
    
    return {
        'queries': {
            'total_24h': query_health.total_queries,
            'successful': query_health.successful_queries,
            'failed': query_health.failed_queries,
            'success_rate': query_health.success_rate,
            'avg_execution_time_ms': query_health.avg_execution_time_ms,
            'p99_execution_time_ms': query_health.p99_execution_time_ms,
            'credits_used': query_health.credits_used
        },
        'warehouses': {
            name: {
                'state': w.state,
                'queued_queries': w.queued_queries,
                'active_sessions': w.active_sessions,
                'cpu_percentage': w.cpu_percentage
            }
            for name, w in warehouse_status.items()
        },
        'storage': {
            'total_gb': storage.total_gb,
            'top_tables': dict(list(storage.bytes_per_table.items())[:10])
        },
        'timestamp': datetime.utcnow().isoformat()
    }


@app.get("/api/v1/metrics/crm")
async def get_crm_metrics():
    """Get CRM metrics"""
    if 'crm' not in monitors:
        raise HTTPException(status_code=503, detail="CRM monitor not available")
        
    health = await monitors['crm'].get_all_health()
    freshness = await monitors['crm'].get_all_data_freshness()
    
    return {
        'api_health': {
            name: {
                'status': h.status,
                'success_rate': h.success_rate,
                'avg_latency_ms': h.avg_latency_ms,
                'last_successful': h.last_successful_request.isoformat() if h.last_successful_request else None
            }
            for name, h in health.items()
        },
        'data_freshness': freshness,
        'timestamp': datetime.utcnow().isoformat()
    }


# Alert Endpoints
@app.get("/api/v1/alerts")
async def get_alerts(
    severity: Optional[str] = Query(None, regex="^(critical|warning|info)$"),
    active: bool = True
):
    """Get active alerts"""
    if not alert_manager:
        raise HTTPException(status_code=503, detail="Alert manager not available")
        
    alerts = alert_manager.get_active_alerts(severity=severity if active else None)
    
    return {
        'alerts': alerts,
        'count': len(alerts),
        'filter': {'severity': severity, 'active': active}
    }


@app.get("/api/v1/alerts/issues")
async def get_correlated_issues(
    severity: Optional[str] = Query(None),
    include_resolved: bool = False
):
    """Get correlated issues from correlation engine"""
    if not correlator:
        raise HTTPException(status_code=503, detail="Correlation engine not available")
        
    issues = correlator.get_active_issues(
        severity=severity,
        include_resolved=include_resolved
    )
    
    return {
        'issues': issues,
        'count': len(issues)
    }


@app.post("/api/v1/alerts/acknowledge/{alert_id}")
async def acknowledge_alert(alert_id: str):
    """Acknowledge an alert"""
    if not alert_manager:
        raise HTTPException(status_code=503, detail="Alert manager not available")
        
    if alert_manager.acknowledge_alert(alert_id):
        return {'message': 'Alert acknowledged', 'alert_id': alert_id}
    else:
        raise HTTPException(status_code=404, detail="Alert not found")


@app.post("/api/v1/alerts/resolve/{alert_id}")
async def resolve_alert(alert_id: str):
    """Resolve an alert"""
    if not alert_manager:
        raise HTTPException(status_code=503, detail="Alert manager not available")
        
    if alert_manager.resolve_alert(alert_id):
        return {'message': 'Alert resolved', 'alert_id': alert_id}
    else:
        raise HTTPException(status_code=404, detail="Alert not found")


@app.post("/api/v1/alerts/test")
async def send_test_alert():
    """Send test alert to all configured channels"""
    if not alert_manager:
        raise HTTPException(status_code=503, detail="Alert manager not available")
        
    alert = Alert(
        alert_id=f"TEST-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
        title="Test Alert - Cross-Service Monitor",
        message="This is a test alert to verify alerting configuration is working correctly.",
        severity='info',
        source='system',
        resource='test',
        metadata={'test': True}
    )
    
    results = await alert_manager.send_alert(alert)
    
    return {
        'message': 'Test alert sent',
        'alert_id': alert.alert_id,
        'channel_results': results
    }


# Correlation Events
@app.post("/api/v1/events")
async def ingest_event(event_data: Dict):
    """Ingest external event for correlation"""
    if not correlator:
        raise HTTPException(status_code=503, detail="Correlation engine not available")
        
    event = CorrelationEvent(
        timestamp=datetime.fromisoformat(event_data.get('timestamp', datetime.utcnow().isoformat())),
        source=event_data['source'],
        resource=event_data['resource'],
        event_type=event_data['event_type'],
        severity=event_data.get('severity', 'info'),
        details=event_data.get('details', {})
    )
    
    correlator.add_event(event)
    
    return {'message': 'Event ingested', 'timestamp': datetime.utcnow().isoformat()}


# Dashboard Data
@app.get("/api/v1/dashboard/summary")
async def get_dashboard_summary():
    """Get comprehensive dashboard summary"""
    summary = {
        'timestamp': datetime.utcnow().isoformat(),
        'overall_status': 'healthy',
        'services': {},
        'pipelines': {},
        'alerts': {},
        'recent_events': []
    }
    
    # Gather service health
    for service_name, monitor in monitors.items():
        try:
            if service_name == 'aws':
                health = await monitor.get_all_lambda_health()
                summary['services']['aws'] = {
                    'function_count': len(health),
                    'status': 'healthy' if all(m.error_rate < 0.05 for m in health.values()) else 'degraded'
                }
            elif service_name == 'snowflake':
                query_health = await monitor.check_query_health()
                summary['services']['snowflake'] = {
                    'queries_24h': query_health.total_queries,
                    'success_rate': query_health.success_rate,
                    'status': 'healthy' if query_health.success_rate > 0.9 else 'degraded'
                }
            elif service_name == 'crm':
                health = await monitor.get_all_health()
                summary['services']['crm'] = {
                    'systems': len(health),
                    'status': 'healthy' if all(h.status != 'down' for h in health.values()) else 'degraded'
                }
        except Exception as e:
            summary['services'][service_name] = {'status': 'error', 'error': str(e)}
    
    # Pipeline status
    if pipeline_tracker:
        pipeline_status = pipeline_tracker.check_all_pipelines()
        summary['pipelines'] = {
            'count': len(pipeline_status.get('pipelines', {})),
            'status': pipeline_status.get('status', 'unknown'),
            'issues': pipeline_status.get('issues', [])
        }
    
    # Active alerts
    if alert_manager:
        active_alerts = alert_manager.get_active_alerts()
        summary['alerts'] = {
            'active_count': len(active_alerts),
            'critical': len([a for a in active_alerts if a.severity == 'critical']),
            'warning': len([a for a in active_alerts if a.severity == 'warning'])
        }
    
    # Determine overall status
    statuses = [s.get('status', 'unknown') for s in summary['services'].values()]
    if 'error' in statuses or summary['alerts']['critical'] > 0:
        summary['overall_status'] = 'critical'
    elif 'degraded' in statuses or summary['alerts']['warning'] > 0:
        summary['overall_status'] = 'warning'
    
    return summary


if __name__ == "__main__":
    import uvicorn
    
    port = int(os.getenv('DASHBOARD_PORT', 8080))
    host = os.getenv('DASHBOARD_HOST', '0.0.0.0')
    
    logger.info(f"Starting dashboard on {host}:{port}")
    uvicorn.run(app, host=host, port=port, reload=False)
