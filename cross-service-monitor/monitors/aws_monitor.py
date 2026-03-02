"""
AWS Service Monitor
Monitors Lambda, S3, SQS, CloudWatch Alarms
"""

import asyncio
import boto3
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from dataclasses import dataclass, field
import logging

logger = logging.getLogger(__name__)


@dataclass
class LambdaMetrics:
    """Lambda function metrics"""
    function_name: str
    invocations: int = 0
    errors: int = 0
    duration_avg_ms: float = 0.0
    duration_p99_ms: float = 0.0
    throttle_count: int = 0
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    @property
    def error_rate(self) -> float:
        return self.errors / max(self.invocations, 1)


@dataclass
class SQSMetrics:
    """SQS Queue metrics"""
    queue_name: str
    approx_number_of_messages_visible: int = 0
    approx_number_of_messages_not_visible: int = 0
    approx_age_of_oldest_message_seconds: int = 0
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class S3Metrics:
    """S3 Bucket metrics"""
    bucket_name: str
    total_objects: int = 0
    total_size_bytes: int = 0
    timestamp: datetime = field(default_factory=datetime.utcnow)


class AWSMonitor:
    """Monitor AWS services for pipeline health"""
    
    def __init__(self, region: str = "us-east-1"):
        self.cloudwatch = boto3.client('cloudwatch', region_name=region)
        self.lambda_client = boto3.client('lambda', region_name=region)
        self.sqs = boto3.client('sqs', region_name=region)
        self.s3 = boto3.client('s3')
        self.region = region
        
    async def check_lambda_function(self, function_name: str, 
                                    period: int = 300,
                                    periods: int = 24) -> LambdaMetrics:
        """Check Lambda function metrics from CloudWatch"""
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(minutes=period * periods / 60)
        
        metrics_to_fetch = [
            {'Id': 'invocations', 'MetricStat': {
                'Metric': {'Namespace': 'AWS/Lambda', 
                          'MetricName': 'Invocations',
                          'Dimensions': [{'Name': 'FunctionName', 'Value': function_name}]},
                'Period': period,
                'Stat': 'Sum'
            }},
            {'Id': 'errors', 'MetricStat': {
                'Metric': {'Namespace': 'AWS/Lambda',
                          'MetricName': 'Errors',
                          'Dimensions': [{'Name': 'FunctionName', 'Value': function_name}]},
                'Period': period,
                'Stat': 'Sum'
            }},
            {'Id': 'duration', 'MetricStat': {
                'Metric': {'Namespace': 'AWS/Lambda',
                          'MetricName': 'Duration',
                          'Dimensions': [{'Name': 'FunctionName', 'Value': function_name}]},
                'Period': period,
                'Stat': 'Average'
            }},
            {'Id': 'throttles', 'MetricStat': {
                'Metric': {'Namespace': 'AWS/Lambda',
                          'MetricName': 'Throttles',
                          'Dimensions': [{'Name': 'FunctionName', 'Value': function_name}]},
                'Period': period,
                'Stat': 'Sum'
            }}
        ]
        
        try:
            response = self.cloudwatch.get_metric_data(
                MetricDataQueries=metrics_to_fetch,
                StartTime=start_time,
                EndTime=end_time
            )
            
            metrics = LambdaMetrics(function_name=function_name)
            
            for metric_data in response.get('MetricDataResults', []):
                values = [v for v in metric_data['Values'] if v is not None]
                
                if metric_data['Id'] == 'invocations':
                    metrics.invocations = int(sum(values))
                elif metric_data['Id'] == 'errors':
                    metrics.errors = int(sum(values))
                elif metric_data['Id'] == 'duration':
                    metrics.duration_avg_ms = sum(values) / len(values) if values else 0
                elif metric_data['Id'] == 'throttles':
                    metrics.throttle_count = int(sum(values))
                    
            metrics.timestamp = end_time
            
        except Exception as e:
            logger.error(f"Error fetching Lambda metrics for {function_name}: {e}")
            metrics.timestamp = end_time
            
        return metrics
    
    async def list_lambda_functions(self) -> List[str]:
        """List all Lambda functions"""
        functions = []
        try:
            paginator = self.lambda_client.get_paginator('list_functions')
            for page in paginator.paginate():
                for func in page.get('Functions', []):
                    functions.append(func['FunctionName'])
        except Exception as e:
            logger.error(f"Error listing Lambda functions: {e}")
        return functions
    
    async def check_cloudwatch_alarms(self, alarm_names: Optional[List[str]] = None) -> Dict:
        """Check status of CloudWatch alarms"""
        try:
            if alarm_names:
                response = self.cloudwatch.describe_alarms(AlarmNames=alarm_names)
            else:
                response = self.cloudwatch.describe_alarms(StateValue='ALARM')
                
            alarms = response.get('MetricAlarms', [])
            
            alarm_status = {
                'total': len(alarms),
                'in_alarm': 0,
                'ok': 0,
                'insufficient_data': 0,
                'details': []
            }
            
            for alarm in alarms:
                state = alarm['State']['Value']
                
                if state == 'ALARM':
                    alarm_status['in_alarm'] += 1
                elif state == 'OK':
                    alarm_status['ok'] += 1
                else:
                    alarm_status['insufficient_data'] += 1
                    
                alarm_status['details'].append({
                    'name': alarm['AlarmName'],
                    'state': state,
                    'description': alarm.get('Description', ''),
                    'last_updated': alarm['StateUpdateTime'].isoformat()
                })
                
            return alarm_status
            
        except Exception as e:
            logger.error(f"Error checking alarms: {e}")
            return {'error': str(e)}
    
    async def check_sqs_queue(self, queue_url: str) -> SQSMetrics:
        """Check SQS queue metrics"""
        queue_name = queue_url.split('/')[-1]
        metrics = SQSMetrics(queue_name=queue_name)
        
        try:
            attrs = self.sqs.get_queue_attributes(
                QueueUrl=queue_url,
                AttributeNames=['ApproximateNumberOfMessages',
                               'ApproximateNumberOfMessagesNotVisible',
                               'ApproximateAgeOfOldestMessage']
            )
            
            attr_map = attrs.get('Attributes', {})
            metrics.approx_number_of_messages_visible = int(attr_map.get('ApproximateNumberOfMessages', 0))
            metrics.approx_number_of_messages_not_visible = int(attr_map.get('ApproximateNumberOfMessagesNotVisible', 0))
            
            oldest_age = attr_map.get('ApproximateAgeOfOldestMessage', '0')
            metrics.approx_age_of_oldest_message_seconds = int(oldest_age) if oldest_age != '0' else 0
            
        except Exception as e:
            logger.error(f"Error checking SQS queue {queue_name}: {e}")
            
        metrics.timestamp = datetime.utcnow()
        return metrics
    
    async def check_s3_bucket(self, bucket_name: str) -> S3Metrics:
        """Get basic S3 bucket statistics"""
        metrics = S3Metrics(bucket_name=bucket_name)
        
        try:
            # Get object count using list_objects_v2
            response = self.s3.list_objects_v2(Bucket=bucket_name, MaxKeys=1)
            metrics.total_objects = response.get('KeyCount', 0)
            
            # Note: For accurate size, you'd need CloudWatch or S3 Inventory
            # This is just a quick count
        except Exception as e:
            logger.error(f"Error checking S3 bucket {bucket_name}: {e}")
            
        metrics.timestamp = datetime.utcnow()
        return metrics
    
    async def get_lambda_logs_recent_errors(self, function_name: str, 
                                            limit: int = 10) -> List[Dict]:
        """Get recent error logs from Lambda"""
        # Log group name format: /aws/lambda/{function_name}
        log_group = f"/aws/lambda/{function_name}"
        
        try:
            logs_client = boto3.client('logs', region_name=self.region)
            
            # Search for ERROR messages
            start_time = int((datetime.utcnow() - timedelta(hours=24)).timestamp() * 1000)
            
            # Use FilterLogEvents
            response = logs_client.filter_log_events(
                logGroupName=log_group,
                filterPattern='ERROR',
                startTime=start_time,
                limit=limit,
                interleaved=True
            )
            
            errors = []
            for event in response.get('events', []):
                errors.append({
                    'timestamp': datetime.fromtimestamp(event['timestamp'] / 1000).isoformat(),
                    'message': event['message'][:500],  # Truncate long messages
                    'log_stream': event.get('logStreamName', '')
                })
                
            return errors
            
        except Exception as e:
            logger.error(f"Error fetching logs for {function_name}: {e}")
            return []
    
    async def get_all_lambda_health(self) -> Dict[str, LambdaMetrics]:
        """Get health status for all Lambda functions"""
        functions = await self.list_lambda_functions()
        health = {}
        
        # Limit concurrent calls
        semaphore = asyncio.Semaphore(10)
        
        async def fetch_with_semaphore(func):
            async with semaphore:
                return await self.check_lambda_function(func)
        
        tasks = [fetch_with_semaphore(f) for f in functions]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for func, result in zip(functions, results):
            if isinstance(result, LambdaMetrics):
                health[func] = result
            else:
                logger.error(f"Failed to get health for {func}: {result}")
                
        return health
    
    async def check_pipeline_dependencies(self, lambda_functions: List[str],
                                         sqs_queues: List[str]) -> Dict:
        """Check health of multiple Lambda functions and SQS queues as a pipeline"""
        results = {
            'status': 'healthy',
            'lambdas': {},
            'sqs_queues': {},
            'issues': [],
            'checked_at': datetime.utcnow().isoformat()
        }
        
        # Check all Lambdas
        lambda_health = await self.get_all_lambda_health()
        for func_name in lambda_functions:
            if func_name in lambda_health:
                metrics = lambda_health[func_name]
                results['lambdas'][func_name] = {
                    'invocations': metrics.invocations,
                    'errors': metrics.errors,
                    'error_rate': metrics.error_rate,
                    'status': 'error' if metrics.error_rate > 0.05 else 'healthy'
                }
                
                if metrics.error_rate > 0.05:
                    results['status'] = 'warning'
                    results['issues'].append({
                        'type': 'lambda_error_rate',
                        'resource': func_name,
                        'severity': 'warning',
                        'message': f"High error rate: {metrics.error_rate:.1%}"
                    })
                    
                if metrics.throttle_count > 0:
                    results['status'] = 'critical'
                    results['issues'].append({
                        'type': 'lambda_throttled',
                        'resource': func_name,
                        'severity': 'critical',
                        'message': f"Throttled {metrics.throttle_count} times"
                    })
        
        # Check all SQS queues
        for queue_url in sqs_queues:
            try:
                sqs_metrics = await self.check_sqs_queue(queue_url)
                results['sqs_queues'][queue_url] = {
                    'visible_messages': sqs_metrics.approx_number_of_messages_visible,
                    'hidden_messages': sqs_metrics.approx_number_of_messages_not_visible,
                    'oldest_message_age_sec': sqs_metrics.approx_age_of_oldest_message_seconds,
                    'status': 'healthy'
                }
                
                if sqs_metrics.approx_number_of_messages_visible > 1000:
                    results['status'] = 'warning'
                    results['issues'].append({
                        'type': 'sqs_backlog',
                        'resource': queue_url,
                        'severity': 'warning',
                        'message': f"Queue backlog: {sqs_metrics.approx_number_of_messages_visible} messages"
                    })
                    
            except Exception as e:
                results['sqs_queues'][queue_url] = {
                    'status': 'error',
                    'error': str(e)
                }
                results['status'] = 'warning'
                
        return results
