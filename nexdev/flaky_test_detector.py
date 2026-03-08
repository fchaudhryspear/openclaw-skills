#!/usr/bin/env python3
"""
NexDev v3.0 - Track D: Smart Orchestration
Flaky Test Detector

Identify unreliable tests (pass rate <95% over 30 runs)
Suggests quarantine, investigation, or fixes
"""

import json
from pathlib import Path
from typing import Optional, Dict, List, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum


class FlakinessLevel(Enum):
    STABLE = "stable"          # >95% pass rate
    LOW = "low"                # 90-95% pass rate
    MEDIUM = "medium"          # 80-90% pass rate  
    HIGH = "high"              # 70-80% pass rate
    CRITICAL = "critical"      # <70% pass rate


@dataclass
class TestResult:
    test_name: str
    file_path: str
    run_timestamp: str
    duration_ms: int
    status: str  # passed, failed, skipped
    error_message: str = None
    stack_trace: str = None
    retry_count: int = 0


@dataclass
class TestHistory:
    test_name: str
    file_path: str
    total_runs: int
    passed: int
    failed: int
    skipped: int
    pass_rate: float
    flakiness_level: str
    avg_duration_ms: float
    last_failure: str = None
    failure_pattern: str = None
    recommended_action: str = None


@dataclass
class QuarantineRecommendation:
    test_name: str
    file_path: str
    flakiness_level: str
    pass_rate: float
    reason: str
    suggested_action: str  # quarantine, investigate, fix, monitor
    priority: int  # 1-5, 1 being highest


class FlakyTestDetector:
    """Detect and manage flaky tests"""
    
    FLAKINESS_THRESHOLDS = {
        'stable': 0.95,
        'low': 0.90,
        'medium': 0.80,
        'high': 0.70,
        'critical': 0.0
    }
    
    MIN_RUNS_FOR_ANALYSIS = 10
    QUARANTINE_THRESHOLD = 0.85  # Auto-quarantine below this
    
    def __init__(self, config_path: str = None):
        self.config = self._load_config(config_path)
        self.history_dir = Path.home() / '.openclaw' / 'workspace' / 'nexdev' / 'test_history'
        self.quarantine_file = Path.home() / '.openclaw' / 'workspace' / 'nexdev' / 'quarantined_tests.json'
        self.report_dir = Path.home() / '.openclaw' / 'workspace' / 'nexdev' / 'flaky_reports'
        
        self.history_dir.mkdir(parents=True, exist_ok=True)
        self.report_dir.mkdir(parents=True, exist_ok=True)
        
    def _load_config(self, config_path: str) -> Dict:
        default_config = {
            'analysis': {
                'min_runs_for_flakiness': 10,
                'analysis_window_days': 30,
                'auto_quarantine': False,
                'quarantine_threshold': 0.85
            },
            'detection': {
                'consecutive_passes_to_unc quarantine': 5,
                'failure_patterns': [
                    'timeout',
                    'race condition',
                    'intermittent',
                    'async',
                    'timing'
                ]
            },
            'reporting': {
                'frequency': 'weekly',  # daily, weekly, monthly
                'notify_channels': ['slack'],
                'include_trends': True
            },
            'integrations': {
                'github_actions': False,
                'jenkins': False,
                'circleci': False,
                'test_results_api': None
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
        
    async def analyze_test_suite(self, repo_path: str = None) -> Dict:
        """
        Analyze all tests for flakiness
        
        Args:
            repo_path: Repository path
            
        Returns:
            Analysis results with flakiness reports
        """
        print("\n🔍 Analyzing test suite for flakiness...")
        
        # Load test history
        test_histories = await self._load_test_histories(repo_path)
        
        if not test_histories:
            return {
                'status': 'no_data',
                'message': 'No test history found. Run tests first to collect data.'
            }
            
        # Calculate flakiness metrics
        print("📊 Calculating flakiness metrics...")
        flaky_tests = []
        stable_tests = []
        
        for test_name, history in test_histories.items():
            flakiness = self._calculate_flakiness(history)
            
            if flakiness['level'] != FlakinessLevel.STABLE.value:
                flaky_tests.append({
                    'test': test_name,
                    **flakiness
                })
            else:
                stable_tests.append(test_name)
                
        # Generate recommendations
        print("🎯 Generating recommendations...")
        recommendations = self._generate_recommendations(flaky_tests)
        
        # Update quarantine list
        quarantine_updates = self._update_quarantine_list(flaky_tests)
        
        result = {
            'timestamp': datetime.now().isoformat(),
            'total_tests': len(test_histories),
            'stable_tests': len(stable_tests),
            'flaky_tests': len(flaky_tests),
            'flakiness_breakdown': self._count_by_flakiness_level(flaky_tests),
            'quarantine_updates': quarantine_updates,
            'recommendations': recommendations
        }
        
        # Save report
        self._save_report(result)
        
        return result
        
    async def _load_test_histories(self, repo_path: str = None) -> Dict[str, TestHistory]:
        """Load test execution history from files or CI APIs"""
        histories = {}
        
        # Try loading from local files first
        history_files = list(self.history_dir.glob('*.jsonl'))
        
        for history_file in history_files:
            try:
                with open(history_file) as f:
                    for line in f:
                        if not line.strip():
                            continue
                            
                        result = json.loads(line)
                        test_key = f"{result['file_path']}::{result['test_name']}"
                        
                        if test_key not in histories:
                            histories[test_key] = {
                                'test_name': result['test_name'],
                                'file_path': result['file_path'],
                                'runs': [],
                                'passed': 0,
                                'failed': 0,
                                'skipped': 0,
                                'total_duration_ms': 0
                            }
                            
                        histories[test_key]['runs'].append(result)
                        
                        if result['status'] == 'passed':
                            histories[test_key]['passed'] += 1
                        elif result['status'] == 'failed':
                            histories[test_key]['failed'] += 1
                            histories[test_key]['last_failure'] = result['run_timestamp']
                            if result.get('error_message'):
                                histories[test_key]['failure_pattern'] = self._classify_failure(
                                    result['error_message']
                                )
                        else:
                            histories[test_key]['skipped'] += 1
                            
                        histories[test_key]['total_duration_ms'] += result['duration_ms']
                        
            except Exception as e:
                print(f"Error loading {history_file}: {e}")
                
        # Convert to TestHistory objects
        result = {}
        for key, data in histories.items():
            total_runs = data['passed'] + data['failed'] + data['skipped']
            
            if total_runs >= self.MIN_RUNS_FOR_ANALYSIS:
                result[key] = TestHistory(
                    test_name=data['test_name'],
                    file_path=data['file_path'],
                    total_runs=total_runs,
                    passed=data['passed'],
                    failed=data['failed'],
                    skipped=data['skipped'],
                    pass_rate=data['passed'] / total_runs if total_runs > 0 else 0,
                    flakiness_level='',  # Will be calculated
                    avg_duration_ms=data['total_duration_ms'] / total_runs if total_runs > 0 else 0,
                    last_failure=data.get('last_failure'),
                    failure_pattern=data.get('failure_pattern')
                )
                
        return result
        
    def _calculate_flakiness(self, history: TestHistory) -> Dict:
        """Calculate flakiness metrics for a test"""
        level = self._determine_flakiness_level(history.pass_rate)
        
        # Determine recommended action
        if history.pass_rate < self.QUARANTINE_THRESHOLD:
            action = "quarantine"
        elif history.flakiness_level in ['medium', 'high']:
            action = "investigate"
        elif history.flakiness_level == 'low':
            action = "monitor"
        else:
            action = "none"
            
        return {
            'level': level,
            'pass_rate': round(history.pass_rate * 100, 1),
            'total_runs': history.total_runs,
            'failed_runs': history.failed,
            'recommended_action': action,
            'priority': self._calculate_priority(level, history.pass_rate)
        }
        
    def _determine_flakiness_level(self, pass_rate: float) -> str:
        """Determine flakiness level based on pass rate"""
        if pass_rate >= self.FLAKINESS_THRESHOLDS['stable']:
            return FlakinessLevel.STABLE.value
        elif pass_rate >= self.FLAKINESS_THRESHOLDS['low']:
            return FlakinessLevel.LOW.value
        elif pass_rate >= self.FLAKINESS_THRESHOLDS['medium']:
            return FlakinessLevel.MEDIUM.value
        elif pass_rate >= self.FLAKINESS_THRESHOLDS['high']:
            return FlakinessLevel.HIGH.value
        else:
            return FlakinessLevel.CRITICAL.value
            
    def _classify_failure(self, error_message: str) -> str:
        """Classify failure pattern from error message"""
        error_lower = error_message.lower()
        
        patterns = {
            'timeout': ['timeout', 'timed out', 'exceeded maximum'],
            'race_condition': ['race', 'concurrent', 'thread', 'mutex'],
            'async_issue': ['async', 'await', 'promise', 'callback'],
            'resource_contestation': ['locked', 'in use', 'busy', 'available'],
            'network_issue': ['connection', 'network', 'dns', 'host unreachable'],
            'flaky': ['intermittent', 'sometimes', 'occasionally', 'random']
        }
        
        for pattern_type, keywords in patterns.items():
            if any(keyword in error_lower for keyword in keywords):
                return pattern_type
                
        return 'unknown'
        
    def _calculate_priority(self, level: str, pass_rate: float) -> int:
        """Calculate priority score (1-5, 1 being highest)"""
        base_priority = {
            'critical': 1,
            'high': 2,
            'medium': 3,
            'low': 4,
            'stable': 5
        }.get(level, 3)
        
        # Adjust based on how close to threshold
        if pass_rate < 0.70:
            base_priority = max(1, base_priority - 1)
            
        return base_priority
        
    def _generate_recommendations(self, flaky_tests: List[Dict]) -> List[Dict]:
        """Generate actionable recommendations for flaky tests"""
        recommendations = []
        
        # Group by severity
        critical = [t for t in flaky_tests if t['level'] == 'critical']
        high = [t for t in flaky_tests if t['level'] == 'high']
        medium = [t for t in flaky_tests if t['level'] == 'medium']
        
        if critical:
            recommendations.append({
                'severity': 'critical',
                'action': 'immediate_quarantine',
                'affected_tests': len(critical),
                'description': f"{len(critical)} test(s) critically flaky (<70% pass rate)",
                'steps': [
                    'Quarantine these tests immediately',
                    'Investigate root cause',
                    'Fix or remove if broken'
                ]
            })
            
        if high:
            recommendations.append({
                'severity': 'high',
                'action': 'schedule_fix',
                'affected_tests': len(high),
                'description': f"{len(high)} test(s) highly flaky (70-80% pass rate)",
                'steps': [
                    'Add to next sprint backlog',
                    'Review failure patterns',
                    'Consider adding retries temporarily'
                ]
            })
            
        if medium:
            recommendations.append({
                'severity': 'medium',
                'action': 'monitor_and_improve',
                'affected_tests': len(medium),
                'description': f"{len(medium)} test(s) moderately flaky (80-90% pass rate)",
                'steps': [
                    'Monitor trend over next week',
                    'Address if pass rate declines',
                    'Improve test reliability when capacity allows'
                ]
            })
            
        # Add specific test recommendations
        for test in sorted(flaky_tests, key=lambda x: x['priority'])[:10]:
            rec = {
                'severity': test['level'],
                'action': test['recommended_action'],
                'test': test['test'],
                'pass_rate': test['pass_rate'],
                'description': f"Test {test['test']} has {test['pass_rate']}% pass rate",
                'steps': self._get_specific_fix_steps(test)
            }
            recommendations.append(rec)
            
        return recommendations
        
    def _get_specific_fix_steps(self, test: Dict) -> List[str]:
        """Get specific fix steps based on flakiness characteristics"""
        steps = []
        
        if test['level'] in ['critical', 'high']:
            steps.extend([
                "Run test 50+ times locally to reproduce",
                "Check for timing dependencies or race conditions",
                "Review recent changes to test or code under test"
            ])
            
        if 'timeout' in test.get('failure_pattern', '').lower():
            steps.extend([
                "Increase timeout values",
                "Optimize slow operations",
                "Check for deadlocks"
            ])
            
        if 'race' in test.get('failure_pattern', '').lower():
            steps.extend([
                "Add proper synchronization",
                "Use atomic operations",
                "Review thread safety"
            ])
            
        if not steps:
            steps = [
                "Review test implementation",
                "Check for external dependencies",
                "Ensure proper test isolation"
            ]
            
        return steps
        
    def _update_quarantine_list(self, flaky_tests: List[Dict]) -> List[Dict]:
        """Update quarantined tests list"""
        updates = []
        
        # Load existing quarantine list
        quarantine = self._load_quarantine_list()
        
        for test in flaky_tests:
            if test['recommended_action'] == 'quarantine':
                test_key = test['test']
                
                if test_key not in quarantine:
                    # Add to quarantine
                    quarantine[test_key] = {
                        'added_at': datetime.now().isoformat(),
                        'reason': f"Flakiness: {test['pass_rate']}% pass rate ({test['level']} level)",
                        'priority': test['priority'],
                        'auto_quarantined': self.config['analysis']['auto_quarantine']
                    }
                    updates.append({
                        'test': test_key,
                        'action': 'added',
                        'reason': quarantine[test_key]['reason']
                    })
                    
        # Save updated quarantine list
        self._save_quarantine_list(quarantine)
        
        return updates
        
    def _load_quarantine_list(self) -> Dict:
        """Load quarantined tests"""
        if not self.quarantine_file.exists():
            return {}
            
        try:
            with open(self.quarantine_file) as f:
                return json.load(f)
        except Exception:
            return {}
            
    def _save_quarantine_list(self, quarantine: Dict):
        """Save quarantined tests"""
        with open(self.quarantine_file, 'w') as f:
            json.dump(quarantine, f, indent=2, default=str)
            
    def _count_by_flakiness_level(self, flaky_tests: List[Dict]) -> Dict:
        """Count flaky tests by level"""
        counts = {'critical': 0, 'high': 0, 'medium': 0, 'low': 0}
        
        for test in flaky_tests:
            level = test['level']
            if level in counts:
                counts[level] += 1
                
        return counts
        
    def _save_report(self, result: Dict):
        """Save analysis report"""
        report_file = self.report_dir / f"flaky_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        with open(report_file, 'w') as f:
            json.dump(result, f, indent=2)
            
        print(f"\n✅ Report saved to: {report_file}")
        
    def get_quarantined_tests(self) -> List[Dict]:
        """Get list of quarantined tests"""
        quarantine = self._load_quarantine_list()
        
        return [
            {'test': test, **info}
            for test, info in quarantine.items()
        ]
        
    def unquarantine_test(self, test_name: str, reason: str = None) -> bool:
        """Remove test from quarantine"""
        quarantine = self._load_quarantine_list()
        
        if test_name not in quarantine:
            return False
            
        del quarantine[test_name]
        self._save_quarantine_list(quarantine)
        
        return True
        
    async def record_test_run(self, test_result: TestResult):
        """Record a single test run result"""
        history_file = self.history_dir / f"{test_result.file_path.replace('/', '_')}.jsonl"
        
        result_data = asdict(test_result)
        
        with open(history_file, 'a') as f:
            f.write(json.dumps(result_data) + '\n')
            
    def generate_summary_report(self) -> str:
        """Generate human-readable summary report"""
        quarantine = self._load_quarantine_list()
        
        lines = [
            "# 🧪 Flaky Test Report",
            "",
            f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"**Quarantined Tests:** {len(quarantine)}",
            "",
            "## Quarantined Tests",
            ""
        ]
        
        if quarantine:
            lines.append("| Test | Added | Reason | Priority |")
            lines.append("|------|-------|--------|----------|")
            
            for test, info in sorted(quarantine.items(), 
                                    key=lambda x: x[1].get('priority', 5)):
                lines.append(f"| `{test}` | {info.get('added_at', 'N/A')[:10]} | {info.get('reason', 'N/A')[:40]} | {info.get('priority', 'N/A')} |")
        else:
            lines.append("✓ No tests currently quarantined")
            
        lines.extend([
            "",
            "## Recommendations",
            "",
            "• Run `analyze` to detect new flaky tests",
            "• Review quarantined tests and fix issues",
            "• Use `unquarantine <test>` after fixing"
        ])
        
        return "\n".join(lines)


# CLI Entry Point
if __name__ == '__main__':
    import asyncio
    import sys
    
    print("NexDev Flaky Test Detector v3.0")
    print("=" * 50)
    
    detector = FlakyTestDetector()
    
    if len(sys.argv) < 2:
        print("\nUsage:")
        print("  python flaky_test_detector.py analyze [repo_path]")
        print("  python flaky_test_detector.py quarantine <test_name>")
        print("  python flaky_test_detector.py unquarantine <test_name>")
        print("  python flaky_test_detector.py list")
        print("  python flaky_test_detector.py report")
        sys.exit(1)
        
    command = sys.argv[1]
    
    if command == 'analyze':
        repo_path = sys.argv[2] if len(sys.argv) > 2 else None
        
        result = asyncio.run(detector.analyze_test_suite(repo_path))
        
        if result.get('status') == 'no_data':
            print(f"\n⚠️  {result['message']}")
            print("\nTo collect test data:")
            print("  • Run your test suite with test result logging enabled")
            print("  • Test results will be saved automatically")
        else:
            print(f"\n📊 Analysis Results:")
            print(f"   Total tests analyzed: {result['total_tests']}")
            print(f"   Stable: {result['stable_tests']} ✅")
            print(f"   Flaky: {result['flaky_tests']} ⚠️")
            
            breakdown = result.get('flakiness_breakdown', {})
            if breakdown:
                print(f"\n   Flakiness Breakdown:")
                for level, count in breakdown.items():
                    icon = '🔴' if level == 'critical' else '🟠' if level == 'high' else '🟡'
                    print(f"     {icon} {level}: {count}")
                    
            if result.get('recommendations'):
                print(f"\n💡 Top Recommendations:")
                for rec in result['recommendations'][:3]:
                    print(f"   [{rec['severity'].upper()}] {rec.get('description', rec.get('action'))}")
                    
    elif command == 'quarantine':
        if len(sys.argv) < 3:
            print("Usage: python flaky_test_detector.py quarantine <test_name>")
            sys.exit(1)
            
        test_name = sys.argv[2]
        print(f"\nQuarantine functionality would add {test_name} to quarantine list")
        
    elif command == 'unquarantine':
        if len(sys.argv) < 3:
            print("Usage: python flaky_test_detector.py unquarantine <test_name>")
            sys.exit(1)
            
        test_name = sys.argv[2]
        removed = detector.unquarinate_test(test_name)
        
        if removed:
            print(f"✅ Removed {test_name} from quarantine")
        else:
            print(f"❌ Test {test_name} not found in quarantine")
            
    elif command == 'list':
        quarantined = detector.get_quarantined_tests()
        
        if not quarantined:
            print("\n✓ No tests currently quarantined")
        else:
            print(f"\n{len(quarantined)} quarantined test(s):\n")
            for test in quarantined:
                print(f"  • {test['test']}")
                print(f"    Reason: {test.get('reason', 'N/A')[:60]}")
                
    elif command == 'report':
        report = detector.generate_summary_report()
        print(report)
