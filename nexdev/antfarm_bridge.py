#!/usr/bin/env python3
"""
NexDev ↔ Antfarm Workflow Bridge (Phase 2 Integration)

Triggers Antfarm workflows from NexDev task detection
and reports results back to MO learning database.
"""

import subprocess
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional

ANTFARM_CLI = Path.home() / '.openclaw/workspace/antfarm/dist/cli/cli.js'
NEXDEV_LOG_DIR = Path.home() / '.openclaw/workspace/nexdev/logs'

# Workflow mapping: what queries trigger what Antfarm workflows
WORKFLOW_MAPPING = {
    'bug-fix': {
        'keywords': [
            'fix bug', 'error', 'broken', 'test fail', 'debug', 
            'TypeError', 'SyntaxError', 'stack trace', 'exception'
        ],
        'workflow_id': 'bug-fix',
        'timeout_min': 30,
        'priority_tier': 'validation'  # NexDev tier to use for analysis
    },
    'feature-dev': {
        'keywords': [
            'implement feature', 'add endpoint', 'create component',
            'build new', 'develop', 'integrate service'
        ],
        'workflow_id': 'feature-dev',
        'timeout_min': 120,
        'priority_tier': 'execution'
    },
    'security-audit': {
        'keywords': [
            'security audit', 'vulnerability', 'OWASP', 'exploit',
            'penetration test', 'auth bypass', 'injection attack'
        ],
        'workflow_id': 'security-audit',
        'timeout_min': 60,
        'priority_tier': 'strategic'
    },
    'model-orchestrator': {
        'keywords': [
            'optimize model routing', 'tier strategy', 'cost optimization',
            'model performance', 'routing decision'
        ],
        'workflow_id': 'model-orchestrator',
        'timeout_min': 45,
        'priority_tier': 'execution'
    }
}


def detect_antfarm_task(query: str) -> Dict[str, Any]:
    """
    Detect if query should trigger an Antfarm workflow.
    
    Args:
        query: User's coding query
        
    Returns:
        Dictionary with workflow info or {'trigger_antfarm': False}
    """
    query_lower = query.lower()
    
    best_match = None
    highest_score = 0
    
    for task_type, config in WORKFLOW_MAPPING.items():
        score = sum(1 for kw in config['keywords'] if kw in query_lower)
        
        if score > highest_score:
            highest_score = score
            best_match = {
                'task_type': task_type,
                'workflow_id': config['workflow_id'],
                'timeout_min': config['timeout_min'],
                'priority_tier': config['priority_tier'],
                'match_count': score
            }
    
    # Threshold: at least 2 keyword matches to trigger
    if highest_score >= 2 and best_match:
        return {
            'trigger_antfarm': True,
            **best_match
        }
    
    return {'trigger_antfarm': False}


def run_antfarm_workflow(workflow_id: str, task_description: str, 
                        timeout_minutes: int = 30) -> Dict[str, Any]:
    """
    Execute Antfarm workflow and capture results.
    
    Args:
        workflow_id: Workflow name (e.g., 'bug-fix')
        task_description: Detailed task description
        timeout_minutes: Maximum runtime in minutes
        
    Returns:
        Dictionary with execution result
    """
    cmd = [
        'node', str(ANTFARM_CLI), 'workflow', 'run',
        workflow_id, task_description
    ]
    
    start_time = datetime.now()
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout_minutes * 60,
            cwd=str(Path.home() / '.openclaw/workspace/antfarm')
        )
        
        duration_sec = (datetime.now() - start_time).total_seconds()
        
        return {
            'success': result.returncode == 0,
            'workflow_id': workflow_id,
            'task_description': task_description[:200],
            'stdout': result.stdout,
            'stderr': result.stderr,
            'exit_code': result.returncode,
            'duration_sec': duration_sec,
            'timestamp': start_time.isoformat()
        }
        
    except subprocess.TimeoutExpired:
        return {
            'success': False,
            'workflow_id': workflow_id,
            'error': f'Timeout after {timeout_minutes} minutes',
            'duration_sec': timeout_minutes * 60,
            'timestamp': start_time.isoformat()
        }
        
    except Exception as e:
        return {
            'success': False,
            'workflow_id': workflow_id,
            'error': str(e),
            'timestamp': start_time.isoformat()
        }


def report_workflow_result(task_type: str, result: Dict[str, Any]):
    """
    Report Antfarm workflow result back to MO performance database.
    
    Args:
        task_type: Workflow type (e.g., 'bug-fix')
        result: Workflow execution result dictionary
    """
    try:
        # Add MO modules to path
        import sys
        sys.path.insert(0, str(Path.home() / '.openclaw/workspace/memory'))
        
        from memory.performance_logger import log_query_result
        
        topic = f"antfarm-{task_type}"
        success = result.get('success', False)
        
        # Log to MO performance database
        log_query_result(
            topic=topic,
            model_used="antfarm-workflow",
            success=success,
            tokens_input=0,  # Workflows don't use tokens directly
            tokens_output=0,
            cost_usd=0.10,  # Estimate (no direct billing)
            confidence_score=1.0 if success else 0.0,
            query_text=result.get('task_description', '')[:500],
            response_summary=(result.get('stdout', '') + result.get('stderr', ''))[:500]
        )
        
        # Also log to NexDev-specific log
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'type': 'antfarm-workflow',
            'task_type': task_type,
            'success': success,
            'duration_sec': result.get('duration_sec', 0),
            'cost_estimate_usd': 0.10
        }
        
        log_path = NEXDEV_LOG_DIR / 'antfarm_workflows.jsonl'
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(log_path, 'a') as f:
            f.write(json.dumps(log_entry) + '\n')
            
    except ImportError as e:
        print(f"⚠️  Cannot report to MO DB: {e}")
    except Exception as e:
        print(f"⚠️  Error reporting workflow result: {e}")


def get_workflow_status(query_prefix: str = "") -> Dict[str, Any]:
    """
    Check status of recent Antfarm workflow runs.
    
    Args:
        query_prefix: Filter by task prefix (optional)
        
    Returns:
        Dictionary with workflow status summary
    """
    import sqlite3
    
    # This would integrate with Antfarm's SQLite state DB
    # For now, return mock structure
    return {
        'active_runs': 0,
        'completed_last_24h': 0,
        'success_rate_7d': 0.0,
        'avg_duration_min': 0.0
    }


if __name__ == "__main__":
    # Test mode
    print("=" * 60)
    print("🔗 ANT-FARM BRIDGE TEST")
    print("=" * 60)
    
    # Test detection
    test_queries = [
        "Fix this TypeError: Cannot read property 'map'",
        "Implement Stripe webhook handler",
        "Security audit on authentication flow",
        "What time is it?"
    ]
    
    print("\nWorkflow Detection:\n")
    for query in test_queries:
        result = detect_antfarm_task(query)
        if result['trigger_antfarm']:
            print(f"✅ {query[:50]}...")
            print(f"   → {result['workflow_id']} ({result['task_type']})")
            print(f"   Match count: {result['match_count']}")
        else:
            print(f"❌ {query[:50]}...")
            print(f"   → No workflow triggered")
        print()
    
    print("=" * 60)
    print("Test complete!")
