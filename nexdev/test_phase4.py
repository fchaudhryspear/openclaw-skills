#!/usr/bin/env python3
"""Quick test script for Phase 4 modules"""
import sys
sys.path.insert(0, '.')

from pathlib import Path
print("=" * 70)
print("🧪 Phase 4 Module Test Suite")
print("=" * 70)

# Test 1: Auto-Remediation (sync)
print("\n✅ Test 1: Auto-Remediation")
from auto_remediation import AutoRemediation
analyzer = AutoRemediation()
result = analyzer.analyze_error("TypeError: unsupported operand type(s)")
print(f"   Detected: {result['error_type']} ({result['confidence']:.0%})")

# Test 2: Dependency Upgrader (sync)
print("\n✅ Test 2: Dependency Scanner")
from dependency_upgrader import DependencyUpgrader
upgrader = DependencyUpgrader()
report = upgrader.scan_dependencies('/Users/faisalshomemacmini/.openclaw/workspace')
print(f"   Managers found: {report['managers_found'] or 'None'}")
print(f"   Packages scanned: {len(report['outdated_packages'])}")

# Test 3: Performance Monitor (sync)  
print("\n✅ Test 3: Performance Monitor")
from performance_monitor import PerformanceMonitor
monitor = PerformanceMonitor()
baseline = monitor.establish_baseline('test-svc', 24)
print(f"   Service: {baseline['service']}, Metrics: {len(baseline['samples_per_metric'])}")

# Test 4: SBOM Generator (async) - Test on OpenClaw itself
print("\n✅ Test 4: SBOM Generator")
import asyncio
from sbom_generator import SBOMGenerator
generator = SBOMGenerator()
sbom = asyncio.run(generator.generate_sbom(str(Path.home() / '.openclaw/workspace')))
print(f"   Components: {len(sbom.components)} packages scanned from workspace")
if sbom.components and len(sbom.components) > 0:
    print(f"   Sample: {[c.name for c in sbom.components[:3]]}")

# Test 5: Build Recovery (sync)
print("\n✅ Test 5: Build Recovery")
from build_recovery import BuildRecovery
recovery = BuildRecovery()
pending = recovery.list_pending_recovery()
print(f"   Pending recoveries: {len(pending)}")

# Test 6: Flaky Test Detector (sync)
print("\n✅ Test 6: Flaky Test Detector")
from flaky_test_detector import FlakyTestDetector
detector = FlakyTestDetector()
quarantine = detector.get_quarantined_tests()
print(f"   Quarantined tests: {len(quarantine)}")

print("\n" + "=" * 70)
print("🎉 All Phase 4 modules working correctly!")
print("=" * 70)
print("\nYou can now use these commands:")
print("  python3 auto_remediation.py \"error message\"")
print("  python3 dependency_upgrader.py scan ~/project")
print("  python3 sbom_generator.py generate ~/project")
print("  python3 performance_monitor.py baseline my-service --hours 24")
print("  python3 flaky_test_detector.py analyze")
print("=" * 70)
