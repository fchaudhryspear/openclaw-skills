"""
Correlation Engine
Detects cross-service issues, correlates failures, identifies patterns
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from collections import defaultdict
import logging
import json

logger = logging.getLogger(__name__)


@dataclass
class CorrelationEvent:
    """Single event for correlation analysis"""
    timestamp: datetime
    source: str  # aws, snowflake, crm
    resource: str  # specific function/table/object
    event_type: str  # error, latency_spike, failure, recovery
    severity: str  # info, warning, critical
    details: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        return {
            'timestamp': self.timestamp.isoformat(),
            'source': self.source,
            'resource': self.resource,
            'event_type': self.event_type,
            'severity': self.severity,
            'details': self.details
        }


@dataclass
class CorrelatedIssue:
    """Group of related events forming an issue"""
    issue_id: str
    title: str
    severity: str
    status: str = 'active'  # active, acknowledged, resolved
    created_at: datetime
    updated_at: datetime
    events: List[CorrelationEvent] = field(default_factory=list)
    affected_services: List[str] = field(default_factory=list)
    root_cause_hypothesis: Optional[str] = None
    impact_score: float = 0.0
    
    def to_dict(self) -> Dict:
        return {
            'issue_id': self.issue_id,
            'title': self.title,
            'severity': self.severity,
            'status': self.status,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'events': [e.to_dict() for e in self.events],
            'affected_services': self.affected_services,
            'root_cause_hypothesis': self.root_cause_hypothesis,
            'impact_score': self.impact_score
        }


@dataclass
class PipelineRun:
    """Single pipeline execution"""
    run_id: str
    pipeline_name: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    status: str = 'running'  # running, success, failed, partial
    steps: List[Dict] = field(default_factory=list)
    duration_seconds: Optional[float] = None
    error_message: Optional[str] = None


class CorrelationEngine:
    """
    Main correlation engine that:
    1. Collects events from all monitors
    2. Detects cross-service patterns
    3. Identifies root causes
    4. Tracks pipeline health
    """
    
    def __init__(self, config: Dict):
        self.config = config
        self.event_buffer: List[CorrelationEvent] = []
        self.active_issues: Dict[str, CorrelatedIssue] = {}
        self.pipeline_runs: Dict[str, PipelineRun] = {}
        self.max_buffer_size = config.get('max_event_buffer', 10000)
        self.correlation_window_seconds = config.get('correlation_window', 300)
        
        # Pipeline definitions
        self.pipelines = config.get('pipeline_definitions', [])
        
        # Issue counter
        self._issue_counter = 0
        
    def add_event(self, event: CorrelationEvent):
        """Add a new event to the buffer"""
        self.event_buffer.append(event)
        
        # Prune old events
        if len(self.event_buffer) > self.max_buffer_size:
            cutoff = datetime.utcnow() - timedelta(seconds=self.correlation_window_seconds * 10)
            self.event_buffer = [
                e for e in self.event_buffer 
                if e.timestamp > cutoff
            ]
            
        # Run correlation checks
        self._run_correlation_checks(event)
        
    def _run_correlation_checks(self, new_event: CorrelationEvent):
        """Check for correlations with existing events"""
        
        # Get events within correlation window
        window_start = new_event.timestamp - timedelta(seconds=self.correlation_window_seconds)
        recent_events = [
            e for e in self.event_buffer
            if e.timestamp >= window_start and e != new_event
        ]
        
        # Check different correlation patterns
        self._check_cascading_failures(new_event, recent_events)
        self._check_service_outage(new_event, recent_events)
        self._check_pipeline_blockage(new_event, recent_events)
        self._check_latency_propagation(new_event, recent_events)
        
    def _check_cascading_failures(self, new_event: CorrelationEvent, 
                                  recent_events: List[CorrelationEvent]):
        """Detect when one service failure causes failures downstream"""
        if new_event.event_type not in ['error', 'failure']:
            return
            
        # Look for subsequent errors in dependent services
        cascaded = []
        for event in recent_events:
            if event.timestamp > new_event.timestamp and event.event_type in ['error', 'failure']:
                # Check if this is a known dependency chain
                if self._is_dependency_chain(new_event.source, event.source):
                    cascaded.append(event)
                    
        if len(cascaded) >= 2:  # Original + 2 downstream failures
            self._create_issue(
                title=f"Cascading failure detected: {new_event.source} → multiple downstream services",
                severity='critical',
                events=[new_event] + cascaded,
                affected_services=list(set([new_event.source] + [e.source for e in cascaded])),
                root_cause="Upstream service failure causing cascade"
            )
            
    def _check_service_outage(self, new_event: CorrelationEvent,
                             recent_events: List[CorrelationEvent]):
        """Detect widespread service outages"""
        if new_event.source not in ['aws', 'snowflake', 'crm']:
            return
            
        # Count errors from same source in time window
        source_errors = [
            e for e in recent_events
            if e.source == new_event.source 
            and e.event_type in ['error', 'failure']
        ]
        
        if len(source_errors) >= 5:  # Multiple errors suggests outage
            self._create_issue(
                title=f"Service outage detected: {new_event.source}",
                severity='critical',
                events=[new_event] + source_errors[:10],
                affected_services=[new_event.source],
                root_cause="Multiple simultaneous failures suggest service outage"
            )
            
    def _check_pipeline_blockage(self, new_event: CorrelationEvent,
                                 recent_events: List[CorrelationEvent]):
        """Detect when a pipeline step blocks subsequent steps"""
        # Check if this event matches a pipeline step failure
        matching_pipeline = None
        failed_step = None
        
        for pipeline in self.pipelines:
            for step_idx, step in enumerate(pipeline.get('steps', [])):
                if (step.get('service') == new_event.source and 
                    step.get('resource') == new_event.resource):
                    matching_pipeline = pipeline
                    failed_step = step_idx
                    break
                    
        if not matching_pipeline or failed_step is None:
            return
            
        # Check if downstream pipeline steps are also failing/stuck
        downstream_issues = []
        for step_idx in range(failed_step + 1, len(matching_pipeline.get('steps', []))):
            step = matching_pipeline['steps'][step_idx]
            # Check for events indicating this step hasn't started/completed
            # This would be implemented based on your actual monitoring
            
        if downstream_issues:
            self._create_issue(
                title=f"Pipeline blocked: {matching_pipeline['name']}",
                severity='warning',
                events=[new_event] + downstream_issues,
                affected_services=[
                    s.get('service') for s in matching_pipeline.get('steps', [])
                ],
                root_cause=f"Step {failed_step + 1} failure blocking pipeline"
            )
            
    def _check_latency_propagation(self, new_event: CorrelationEvent,
                                   recent_events: List[CorrelationEvent]):
        """Detect when latency increases propagate through the system"""
        if new_event.event_type != 'latency_spike':
            return
            
        # Look for correlated latency increases
        latency_chain = [new_event]
        
        for event in recent_events:
            if event.event_type == 'latency_spike':
                if self._is_downstream(new_event.source, event.source):
                    latency_chain.append(event)
                    
        if len(latency_chain) >= 3:
            self._create_issue(
                title=f"Latency propagation detected",
                severity='warning',
                events=latency_chain,
                affected_services=list(set(e.source for e in latency_chain)),
                root_cause="Latency spike propagating through service dependencies"
            )
            
    def _is_dependency_chain(self, upstream: str, downstream: str) -> bool:
        """Check if downstream depends on upstream"""
        # Known dependency chains
        dependencies = {
            ('aws', 'snowflake'): True,  # AWS loads into Snowflake
            ('snowflake', 'crm'): True,   # Snowflake syncs to CRM
            ('aws', 'crm'): False,        # No direct dependency
        }
        return dependencies.get((upstream, downstream), False)
        
    def _is_downstream(self, source: str, target: str) -> bool:
        """Check if target is downstream of source"""
        flow_order = ['aws', 'snowflake', 'crm']
        try:
            return flow_order.index(target) > flow_order.index(source)
        except ValueError:
            return False
            
    def _create_issue(self, title: str, severity: str, events: List[CorrelationEvent],
                     affected_services: List[str], root_cause: str):
        """Create a new correlated issue"""
        self._issue_counter += 1
        issue_id = f"ISSUE-{self._issue_counter:04d}"
        now = datetime.utcnow()
        
        # Calculate impact score based on severity and number of affected services
        severity_scores = {'info': 1, 'warning': 3, 'critical': 10}
        impact_score = severity_scores.get(severity, 1) * len(set(affected_services))
        
        issue = CorrelatedIssue(
            issue_id=issue_id,
            title=title,
            severity=severity,
            created_at=now,
            updated_at=now,
            events=events,
            affected_services=affected_services,
            root_cause_hypothesis=root_cause,
            impact_score=impact_score
        )
        
        # Store or update issue
        existing_key = self._find_similar_issue(issue)
        if existing_key:
            # Update existing issue with new events
            self.active_issues[existing_key].events.extend(events)
            self.active_issues[existing_key].updated_at = now
            logger.info(f"Updated existing issue {existing_key}")
        else:
            self.active_issues[issue_id] = issue
            logger.info(f"Created new issue {issue_id}: {title}")
            
    def _find_similar_issue(self, new_issue: CorrelatedIssue) -> Optional[str]:
        """Find if there's a similar active issue to merge with"""
        threshold = timedelta(minutes=10)
        
        for issue_id, issue in self.active_issues.items():
            if issue.status != 'active':
                continue
                
            # Check if issues overlap in time and affect same services
            time_diff = abs((issue.created_at - new_issue.created_at).total_seconds())
            if time_diff < threshold.total_seconds():
                # Check for service overlap
                overlapping = set(issue.affected_services) & set(new_issue.affected_services)
                if overlapping and issue.severity == new_issue.severity:
                    return issue_id
                    
        return None
        
    def get_active_issues(self, severity: Optional[str] = None,
                         include_resolved: bool = False) -> List[Dict]:
        """Get list of active issues"""
        issues = []
        for issue in self.active_issues.values():
            if not include_resolved and issue.status != 'active':
                continue
            if severity and issue.severity != severity:
                continue
            issues.append(issue.to_dict())
            
        # Sort by impact score
        issues.sort(key=lambda x: x['impact_score'], reverse=True)
        return issues
        
    def acknowledge_issue(self, issue_id: str) -> bool:
        """Mark an issue as acknowledged"""
        if issue_id in self.active_issues:
            self.active_issues[issue_id].status = 'acknowledged'
            return True
        return False
        
    def resolve_issue(self, issue_id: str) -> bool:
        """Mark an issue as resolved"""
        if issue_id in self.active_issues:
            self.active_issues[issue_id].status = 'resolved'
            self.active_issues[issue_id].updated_at = datetime.utcnow()
            
            # Create resolution event
            event = CorrelationEvent(
                timestamp=datetime.utcnow(),
                source='system',
                resource=issue_id,
                event_type='recovery',
                severity='info',
                details={'resolved_issue': issue_id}
            )
            self.add_event(event)
            
            return True
        return False


class PipelineTracker:
    """Track pipeline executions and detect lags"""
    
    def __init__(self, pipelines: List[Dict], config: Dict):
        self.pipelines = pipelines
        self.config = config
        self.runs: Dict[str, List[PipelineRun]] = defaultdict(list)
        self.max_runs_per_pipeline = config.get('max_runs_history', 100)
        
    def start_run(self, pipeline_name: str, run_id: Optional[str] = None) -> PipelineRun:
        """Start tracking a new pipeline run"""
        import uuid
        
        run = PipelineRun(
            run_id=run_id or str(uuid.uuid4()),
            pipeline_name=pipeline_name,
            started_at=datetime.utcnow(),
            status='running'
        )
        
        self.runs[pipeline_name].append(run)
        
        # Trim history
        if len(self.runs[pipeline_name]) > self.max_runs_per_pipeline:
            self.runs[pipeline_name] = self.runs[pipeline_name][-self.max_runs_per_pipeline:]
            
        return run
        
    def complete_run(self, pipeline_name: str, run_id: str, 
                    status: str, error_message: Optional[str] = None):
        """Mark a pipeline run as complete"""
        runs = self.runs.get(pipeline_name, [])
        
        for run in reversed(runs):
            if run.run_id == run_id and run.status == 'running':
                run.completed_at = datetime.utcnow()
                run.status = status
                run.error_message = error_message
                run.duration_seconds = (run.completed_at - run.started_at).total_seconds()
                break
                
    def get_pipeline_status(self, pipeline_name: str) -> Dict:
        """Get current status of a pipeline"""
        runs = self.runs.get(pipeline_name, [])
        
        if not runs:
            return {
                'pipeline_name': pipeline_name,
                'status': 'unknown',
                'last_run': None
            }
            
        latest_run = runs[-1]
        
        # Calculate lag
        pipeline_def = next((p for p in self.pipelines if p['name'] == pipeline_name), None)
        schedule = pipeline_def.get('schedule', '') if pipeline_def else ''
        
        lag_minutes = None
        expected_next = self._calculate_expected_next_run(schedule)
        if expected_next and latest_run.completed_at:
            lag_minutes = (datetime.utcnow() - latest_run.completed_at).total_seconds() / 60
            
        return {
            'pipeline_name': pipeline_name,
            'status': latest_run.status,
            'current_run_id': latest_run.run_id,
            'started_at': latest_run.started_at.isoformat(),
            'completed_at': latest_run.completed_at.isoformat() if latest_run.completed_at else None,
            'duration_seconds': latest_run.duration_seconds,
            'error_message': latest_run.error_message,
            'lag_minutes': lag_minutes,
            'recent_runs': len([r for r in runs if r.status == 'success']) / max(len(runs), 1)
        }
        
    def _calculate_expected_next_run(self, cron_schedule: str) -> Optional[datetime]:
        """Calculate next expected run time from cron schedule"""
        # Simplified implementation - use a proper cron library in production
        # For now, return None
        return None
        
    def check_all_pipelines(self) -> Dict:
        """Check status of all pipelines"""
        results = {
            'status': 'healthy',
            'pipelines': {},
            'issues': [],
            'checked_at': datetime.utcnow().isoformat()
        }
        
        for pipeline in self.pipelines:
            name = pipeline['name']
            status = self.get_pipeline_status(name)
            results['pipelines'][name] = status
            
            # Check for issues
            if status['status'] == 'failed':
                results['status'] = 'critical'
                results['issues'].append({
                    'type': 'pipeline_failed',
                    'resource': name,
                    'severity': 'critical',
                    'message': f"Pipeline {name} failed: {status.get('error_message', 'Unknown error')}"
                })
            elif status.get('lag_minutes') is not None:
                timeout = pipeline.get('timeout_minutes', 30)
                if status['lag_minutes'] > timeout * 2:
                    results['status'] = 'critical'
                    results['issues'].append({
                        'type': 'pipeline_lag',
                        'resource': name,
                        'severity': 'critical',
                        'message': f"Pipeline {name} lagging by {status['lag_minutes']:.0f} min"
                    })
                elif status['lag_minutes'] > timeout:
                    if results['status'] != 'critical':
                        results['status'] = 'warning'
                    results['issues'].append({
                        'type': 'pipeline_lag',
                        'resource': name,
                        'severity': 'warning',
                        'message': f"Pipeline {name} lagging by {status['lag_minutes']:.0f} min"
                    })
                    
        return results
