"""
CRM Monitor
Monitors HubSpot, Salesforce API health and sync jobs
"""

import asyncio
import httpx
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from dataclasses import dataclass, field
import logging
import json

logger = logging.getLogger(__name__)


@dataclass
class CRMAPIHealth:
    """API health metrics for a CRM"""
    service_name: str  # hubspot, salesforce
    status: str = 'unknown'  # healthy, degraded, down
    last_successful_request: Optional[datetime] = None
    failed_requests_1h: int = 0
    total_requests_1h: int = 0
    avg_latency_ms: float = 0.0
    rate_limit_remaining: Optional[int] = None
    rate_limit_reset: Optional[datetime] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    @property
    def success_rate(self) -> float:
        return (self.total_requests_1h - self.failed_requests_1h) / max(self.total_requests_1h, 1)


@dataclass 
class WebhookDelivery:
    """Webhook delivery status"""
    webhook_id: str
    event_type: str
    delivered_at: Optional[datetime] = None
    success: bool = False
    http_status: Optional[int] = None
    response_time_ms: Optional[float] = None
    error_message: Optional[str] = None


@dataclass
class SyncJobMetrics:
    """Sync job performance metrics"""
    job_name: str
    last_run: Optional[datetime] = None
    last_status: str = 'unknown'  # success, failed, running
    duration_seconds: Optional[float] = None
    records_synced: int = 0
    records_failed: int = 0
    next_scheduled: Optional[datetime] = None
    lag_minutes: Optional[float] = None


class HubSpotMonitor:
    """Monitor HubSpot integration health"""
    
    def __init__(self, api_key: str, private_app_token: Optional[str] = None):
        self.base_url = "https://api.hubapi.com"
        self.headers = {
            'Authorization': f'Bearer {private_app_token or api_key}',
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
        self.api_key = api_key
        
    async def check_api_health(self) -> CRMAPIHealth:
        """Check HubSpot API health"""
        health = CRMAPIHealth(service_name='hubspot')
        
        try:
            start_time = datetime.utcnow()
            
            async with httpx.AsyncClient(timeout=10.0) as client:
                # Test basic API access
                response = await client.get(
                    f"{self.base_url}/crm/v3/objects/contacts",
                    headers=self.headers,
                    params={'limit': 1}
                )
                
                elapsed_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
                
                if response.status_code == 200:
                    health.status = 'healthy'
                    health.last_successful_request = datetime.utcnow()
                elif response.status_code == 429:
                    health.status = 'degraded'
                    health.rate_limit_remaining = 0
                    # Parse reset time from headers
                    if 'hb-ratelimit-reset' in response.headers:
                        reset_seconds = int(response.headers['hb-ratelimit-reset'])
                        health.rate_limit_reset = datetime.utcnow() + timedelta(seconds=reset_seconds)
                else:
                    health.status = 'down'
                    
                health.avg_latency_ms = elapsed_ms
                
        except httpx.TimeoutException:
            health.status = 'down'
            logger.error("HubSpot API timeout")
        except httpx.HTTPError as e:
            health.status = 'down'
            logger.error(f"HubSpot API error: {e}")
        except Exception as e:
            health.status = 'unknown'
            logger.error(f"HubSpot health check error: {e}")
            
        return health
    
    async def get_webhook_deliveries(self, hours: int = 24, 
                                    limit: int = 100) -> List[WebhookDelivery]:
        """Get recent webhook delivery status"""
        deliveries = []
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                # Note: This requires Webhooks API access
                # Alternative: Check your own webhook receiver logs
                response = await client.get(
                    f"{self.base_url}/webhooks/v1/deliveries",
                    headers=self.headers,
                    params={'limit': limit}
                )
                
                if response.status_code == 200:
                    data = response.json()
                    for item in data.get('results', []):
                        deliveries.append(WebhookDelivery(
                            webhook_id=item.get('id', ''),
                            event_type=item.get('subscriptionType', ''),
                            delivered_at=datetime.fromisoformat(item['createdAt'].replace('Z', '+00:00')) 
                                          if item.get('createdAt') else None,
                            success=item.get('responseStatus', 0) == 200,
                            http_status=item.get('responseStatus'),
                            response_time_ms=item.get('responseTime', {}).get('value'),
                            error_message=item.get('errorDescription')
                        ))
                        
        except Exception as e:
            logger.error(f"Error fetching webhook deliveries: {e}")
            
        return deliveries[:limit]
    
    async def check_data_freshness(self, object_type: str = 'contacts',
                                  time_property: str = 'lastmodifieddate') -> Dict:
        """Check how fresh data is in HubSpot"""
        result = {
            'object_type': object_type,
            'status': 'unknown',
            'last_update': None,
            'age_minutes': None,
            'total_count': 0
        }
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                # Get most recently modified object
                response = await client.get(
                    f"{self.base_url}/crm/v3/objects/{object_type}",
                    headers=self.headers,
                    params={
                        'limit': 1,
                        'sort': f'-{time_property}',
                        'properties': [time_property]
                    }
                )
                
                if response.status_code == 200:
                    data = response.json()
                    
                    # Get total count
                    count_response = await client.get(
                        f"{self.base_url}/crm/v3/objects/{object_type}/paged",
                        headers=self.headers
                    )
                    result['total_count'] = count_response.json().get('total', 0) if count_response.status_code == 200 else 0
                    
                    if data.get('results'):
                        latest = data['results'][0]
                        mod_time = latest.get('properties', {}).get(time_property)
                        
                        if mod_time:
                            last_mod = datetime.fromtimestamp(int(mod_time) / 1000)
                            result['last_update'] = last_mod.isoformat()
                            
                            age = datetime.utcnow() - last_mod.replace(tzinfo=last_mod.tzinfo) if last_mod.tzinfo else datetime.utcnow() - last_mod
                            result['age_minutes'] = age.total_seconds() / 60
                            
                            if result['age_minutes'] < 30:
                                result['status'] = 'healthy'
                            elif result['age_minutes'] < 120:
                                result['status'] = 'warning'
                            else:
                                result['status'] = 'critical'
                                
        except Exception as e:
            logger.error(f"Error checking HubSpot data freshness: {e}")
            result['error'] = str(e)
            
        return result
    
    async def get_sync_job_status(self, job_name: str) -> SyncJobMetrics:
        """
        Get status of a specific sync job.
        This would typically query your own job tracking system or HubSpot imports API.
        """
        # Placeholder - integrate with your actual job scheduler
        # Could check Airflow, cron logs, database job table, etc.
        
        metrics = SyncJobMetrics(job_name=job_name)
        
        # Example: Check last successful import via HubSpot API
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    f"{self.base_url}/imports/v1/imports",
                    headers=self.headers
                )
                
                if response.status_code == 200:
                    imports = response.json().get('results', [])
                    if imports:
                        latest = imports[0]
                        metrics.last_run = datetime.fromisoformat(
                            latest.get('createdAt', '').replace('Z', '+00:00')
                        )
                        metrics.last_status = 'success' if latest.get('state') == 'FINISHED' else 'failed'
                        
        except Exception as e:
            logger.error(f"Error getting sync job status: {e}")
            
        return metrics


class SalesforceMonitor:
    """Monitor Salesforce integration health"""
    
    def __init__(self, instance_url: str, session_token: str, 
                 client_id: Optional[str] = None,
                 client_secret: Optional[str] = None):
        self.instance_url = instance_url.rstrip('/')
        self.session_token = session_token
        self.client_id = client_id
        self.client_secret = client_secret
        self.headers = {
            'Authorization': f'Bearer {session_token}',
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
        
    async def check_api_health(self) -> CRMAPIHealth:
        """Check Salesforce API health"""
        health = CRMAPIHealth(service_name='salesforce')
        
        try:
            start_time = datetime.utcnow()
            
            async with httpx.AsyncClient(timeout=10.0) as client:
                # Test with simple SOQL query
                response = await client.get(
                    f"{self.instance_url}/services/data/v58.0/query",
                    headers=self.headers,
                    params={'q': 'SELECT Id FROM Account LIMIT 1'}
                )
                
                elapsed_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
                
                if response.status_code == 200:
                    health.status = 'healthy'
                    health.last_successful_request = datetime.utcnow()
                elif response.status_code == 401:
                    health.status = 'down'
                    logger.error("Salesforce authentication failed")
                elif response.status_code >= 500:
                    health.status = 'down'
                else:
                    health.status = 'degraded'
                    
                health.avg_latency_ms = elapsed_ms
                
        except httpx.TimeoutException:
            health.status = 'down'
            logger.error("Salesforce API timeout")
        except httpx.HTTPError as e:
            health.status = 'down'
            logger.error(f"Salesforce API error: {e}")
        except Exception as e:
            health.status = 'unknown'
            logger.error(f"Salesforce health check error: {e}")
            
        return health
    
    async def check_data_freshness(self, object_type: str = 'Account',
                                  date_field: str = 'LastModifiedDate') -> Dict:
        """Check how fresh data is in Salesforce object"""
        result = {
            'object_type': object_type,
            'status': 'unknown',
            'last_update': None,
            'age_minutes': None,
            'total_count': 0
        }
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                # Get record with most recent modification
                soql = f"SELECT {date_field}, Id FROM {object_type} ORDER BY {date_field} DESC LIMIT 1"
                
                response = await client.get(
                    f"{self.instance_url}/services/data/v58.0/query",
                    headers=self.headers,
                    params={'q': soql}
                )
                
                if response.status_code == 200:
                    data = response.json()
                    
                    if data.get('records'):
                        latest = data['records'][0]
                        mod_time_str = latest.get(date_field, '')
                        
                        if mod_time_str:
                            last_mod = datetime.fromisoformat(mod_time_str.replace('Z', '+00:00'))
                            result['last_update'] = last_mod.isoformat()
                            
                            age = datetime.utcnow().replace(tzinfo=last_mod.tzinfo) - last_mod
                            result['age_minutes'] = age.total_seconds() / 60
                            
                            if result['age_minutes'] < 30:
                                result['status'] = 'healthy'
                            elif result['age_minutes'] < 120:
                                result['status'] = 'warning'
                            else:
                                result['status'] = 'critical'
                                
        except Exception as e:
            logger.error(f"Error checking Salesforce data freshness: {e}")
            result['error'] = str(e)
            
        return result
    
    async def get_recent_errors(self, hours: int = 24, limit: int = 50) -> List[Dict]:
        """Get recent API errors from Salesforce debug logs"""
        errors = []
        
        # This would typically require EventLogFileQuery or ApexDebugLogs
        # Placeholder implementation
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                # Query SetupEventLog if available
                soql = f"""
                    SELECT EVENTDATE, TYPE, REPORTURL 
                    FROM SetupEventLog 
                    WHERE EVENTTYPE IN ('API_FAILED_LOGIN', 'API_ERROR')
                    AND EVENTDATE >= LAST_{hours}HOURS
                    ORDER BY EVENTDATE DESC
                    LIMIT {limit}
                """
                
                response = await client.get(
                    f"{self.instance_url}/services/data/v58.0/query",
                    headers=self.headers,
                    params={'q': soql}
                )
                
                if response.status_code == 200:
                    data = response.json()
                    for record in data.get('records', []):
                        errors.append({
                            'timestamp': record.get('EVENTDATE'),
                            'type': record.get('TYPE'),
                            'url': record.get('REPORTURL')
                        })
                        
        except Exception as e:
            logger.debug(f"Error fetching Salesforce errors (may not have permissions): {e}")
            
        return errors


class CompositeCRMMonitor:
    """Monitor multiple CRMs together"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.monitors = {}
        
        # Initialize configured monitors
        if config.get('hubspot', {}).get('enabled'):
            hs_config = config['hubspot']
            self.monitors['hubspot'] = HubSpotMonitor(
                api_key=hs_config.get('api_key', ''),
                private_app_token=hs_config.get('private_app_token')
            )
            
        if config.get('salesforce', {}).get('enabled'):
            sf_config = config['salesforce']
            self.monitors['salesforce'] = SalesforceMonitor(
                instance_url=sf_config.get('instance_url', ''),
                session_token=sf_config.get('session_token', '')
            )
    
    async def get_all_health(self) -> Dict[str, CRMAPIHealth]:
        """Get health status of all enabled CRMs"""
        results = {}
        
        for name, monitor in self.monitors.items():
            try:
                health = await monitor.check_api_health()
                results[name] = health
            except Exception as e:
                logger.error(f"Error checking {name} health: {e}")
                results[name] = CRMAPIHealth(service_name=name, status='unknown')
                
        return results
    
    async def get_all_data_freshness(self) -> Dict:
        """Check data freshness across all CRMs"""
        results = {
            'status': 'healthy',
            'systems': {},
            'issues': [],
            'checked_at': datetime.utcnow().isoformat()
        }
        
        if 'hubspot' in self.monitors:
            hs_freshness = await self.monitors['hubspot'].check_data_freshness()
            results['systems']['hubspot'] = hs_freshness
            
            if hs_freshness.get('status') == 'critical':
                results['status'] = 'critical'
                results['issues'].append({
                    'type': 'crm_data_stale',
                    'resource': 'hubspot',
                    'severity': 'critical',
                    'message': f"HubSpot data is {hs_freshness.get('age_minutes', 0):.0f} min old"
                })
            elif hs_freshness.get('status') == 'warning':
                if results['status'] != 'critical':
                    results['status'] = 'warning'
                results['issues'].append({
                    'type': 'crm_data_lagging',
                    'resource': 'hubspot',
                    'severity': 'warning',
                    'message': f"HubSpot data is {hs_freshness.get('age_minutes', 0):.0f} min old"
                })
                
        if 'salesforce' in self.monitors:
            sf_freshness = await self.monitors['salesforce'].check_data_freshness()
            results['systems']['salesforce'] = sf_freshness
            
            if sf_freshness.get('status') == 'critical':
                results['status'] = 'critical'
                results['issues'].append({
                    'type': 'crm_data_stale',
                    'resource': 'salesforce',
                    'severity': 'critical',
                    'message': f"Salesforce data is {sf_freshness.get('age_minutes', 0):.0f} min old"
                })
            elif sf_freshness.get('status') == 'warning':
                if results['status'] != 'critical':
                    results['status'] = 'warning'
                results['issues'].append({
                    'type': 'crm_data_lagging',
                    'resource': 'salesforce',
                    'severity': 'warning',
                    'message': f"Salesforce data is {sf_freshness.get('age_minutes', 0):.0f} min old"
                })
                
        return results
