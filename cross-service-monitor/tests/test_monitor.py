#!/usr/bin/env python3
"""
Test script for Cross-Service Monitor
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

async def test_aws_monitor():
    """Test AWS monitor"""
    print("Testing AWS Monitor...")
    from monitors.aws_monitor import AWSMonitor
    
    monitor = AWSMonitor(region='us-east-1')
    
    # Test listing functions
    functions = await monitor.list_lambda_functions()
    print(f"  Found {len(functions)} Lambda functions")
    
    # Test health check
    if functions:
        health = await monitor.check_lambda_function(functions[0])
        print(f"  {functions[0]}: invocations={health.invocations}, errors={health.errors}")
    
    # Test alarms
    alarms = await monitor.check_cloudwatch_alarms()
    print(f"  Alarms: {alarms.get('total', 0)} total, {alarms.get('in_alarm', 0)} in alarm")
    
    return True


async def test_snowflake_monitor():
    """Test Snowflake monitor"""
    print("\nTesting Snowflake Monitor...")
    import os
    from monitors.snowflake_monitor import SnowflakeMonitor
    
    account = os.getenv('SNOWFLAKE_ACCOUNT')
    user = os.getenv('SNOWFLAKE_USER')
    
    if not account or not user:
        print("  Skipping - SNOWFLAKE_ACCOUNT or SNOWFLAKE_USER not set")
        return False
    
    try:
        monitor = SnowflakeMonitor(
            account=account,
            user=user,
            private_key=os.getenv('SNOWFLAKE_PRIVATE_KEY'),
            password=os.getenv('SNOWFLAKE_PASSWORD')
        )
        
        # Test query health
        query_health = await monitor.check_query_health()
        print(f"  Queries (24h): {query_health.total_queries}")
        print(f"  Success rate: {query_health.success_rate:.1%}")
        print(f"  Failures: {query_health.failed_queries}")
        
        # Test warehouse status
        warehouses = await monitor.check_warehouse_status()
        print(f"  Warehouses: {len(warehouses)}")
        for name, wh in warehouses.items():
            print(f"    {name}: {wh.state}")
        
        return True
        
    except Exception as e:
        print(f"  Error: {e}")
        return False


async def test_correlator():
    """Test correlation engine"""
    print("\nTesting Correlation Engine...")
    from engine.correlator import CorrelationEngine, CorrelationEvent
    from datetime import datetime
    
    correlator = CorrelationEngine({
        'max_event_buffer': 1000,
        'correlation_window': 300,
        'pipeline_definitions': []
    })
    
    # Simulate events
    events = [
        CorrelationEvent(
            timestamp=datetime.utcnow(),
            source='aws',
            resource='data-loader',
            event_type='failure',
            severity='critical',
            details={'error': 'Lambda timeout'}
        ),
        CorrelationEvent(
            timestamp=datetime.utcnow(),
            source='snowflake',
            resource='load-data',
            event_type='failure',
            severity='warning',
            details={'error': 'Upstream data missing'}
        ),
        CorrelationEvent(
            timestamp=datetime.utcnow(),
            source='crm',
            resource='hubspot',
            event_type='latency_spike',
            severity='warning',
            details={'latency_ms': 5000}
        ),
    ]
    
    for event in events:
        correlator.add_event(event)
    
    issues = correlator.get_active_issues()
    print(f"  Generated {len(issues)} correlated issues")
    for issue in issues:
        print(f"    - {issue['title']} ({issue['severity']})")
    
    return True


async def test_alert_manager():
    """Test alert manager"""
    print("\nTesting Alert Manager...")
    from engine.alert_manager import AlertManager, Alert
    
    config = {
        'telegram': {
            'bot_token': '',  # Set for real testing
            'chat_id': ''
        },
        'dedup_window_seconds': 60
    }
    
    manager = AlertManager(config)
    
    # Send test alert
    alert = Alert(
        alert_id='TEST-001',
        title='Test Alert',
        message='This is a test alert',
        severity='info',
        source='test',
        resource='test-resource'
    )
    
    results = await manager.send_alert(alert)
    print(f"  Alert sent to channels: {results}")
    
    # Check summary
    summary = manager.get_alert_summary()
    print(f"  Active alerts: {summary['active_count']}")
    
    return True


async def main():
    """Run all tests"""
    print("=" * 60)
    print("Cross-Service Monitor Tests")
    print("=" * 60)
    
    results = {}
    
    results['aws'] = await test_aws_monitor()
    results['snowflake'] = await test_snowflake_monitor()
    results['correlator'] = await test_correlator()
    results['alerts'] = await test_alert_manager()
    
    print("\n" + "=" * 60)
    print("Test Results:")
    for name, passed in results.items():
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"  {name}: {status}")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
