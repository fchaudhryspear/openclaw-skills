# NexDev v3.0 — Integration Test Suite
========================================

## Overview

This directory contains automated tests for all Phase 4 modules:
- Track A: Self-Healing (auto_remediation, build_recovery, dependency_upgrader)
- Track B: Ecosystem (jira_sync, slack_notifier, figma_parser)
- Track C: Hardening (soc2_compliance, sbom_generator, performance_monitor)
- Track D: Orchestration (pr_optimizer, flaky_test_detector, cache_warmer)

---

## Running Tests

```bash
# Run all tests
python3 -m pytest tests/ -v

# Run specific track
python3 -m pytest tests/test_track_a.py -v
python3 -m pytest tests/test_track_b.py -v
python3 -m pytest tests/test_track_c.py -v
python3 -m pytest tests/test_track_d.py -v

# Run with coverage
python3 -m pytest tests/ --cov=nexdev --cov-report=html

# Run single test file
python3 -m pytest tests/test_auto_remediation.py::test_name_error_detection -v
```

---

## Test Structure

```
tests/
├── conftest.py                  # Shared fixtures
├── test_track_a_self_healing/
│   ├── test_auto_remediation.py
│   ├── test_build_recovery.py
│   └── test_dependency_upgrader.py
├── test_track_b_ecosystem/
│   ├── test_jira_sync.py
│   ├── test_slack_notifier.py
│   └── test_figma_parser.py
├── test_track_c_hardening/
│   ├── test_soc2_compliance.py
│   ├── test_sbom_generator.py
│   └── test_performance_monitor.py
└── test_track_d_orchestration/
    ├── test_pr_optimizer.py
    ├── test_flaky_test_detector.py
    └── test_cache_warmer.py
```

---

## Test Coverage Goals

| Track | Module | Unit Tests | Integration Tests | Expected Coverage |
|-------|--------|------------|------------------|-------------------|
| **A** | auto_remediation | 15 | 3 | >80% |
| **A** | build_recovery | 12 | 2 | >75% |
| **A** | dependency_upgrader | 10 | 3 | >70% |
| **B** | jira_sync | 8 | 4 | >65% (mocked API) |
| **B** | slack_notifier | 10 | 5 | >75% |
| **B** | figma_parser | 12 | 2 | >70% |
| **C** | soc2_compliance | 15 | 3 | >75% |
| **C** | sbom_generator | 10 | 4 | >80% |
| **C** | performance_monitor | 12 | 3 | >75% |
| **D** | pr_optimizer | 10 | 4 | >70% |
| **D** | flaky_test_detector | 14 | 3 | >75% |
| **D** | cache_warmer | 8 | 3 | >70% |

**Total:** ~136 unit tests, 39 integration tests

---

## Quick Start Example

### test_auto_remediation.py

```python
"""Tests for auto_remediation module."""

import pytest
from nexdev.auto_remediation import AutoRemediation


class TestAutoRemediation:
    """Test error diagnosis and fix generation."""
    
    @pytest.fixture
    def analyzer(self):
        return AutoRemediation()
    
    def test_name_error_detection(self, analyzer):
        """Test detection of NameError."""
        error_log = "NameError: name 'undefined_var' is not defined"
        
        diagnostic = analyzer.analyze_error(error_log)
        
        assert diagnostic['error_type'] == 'name_error'
        assert diagnostic['confidence'] >= 0.8
        assert 'undefined_var' in diagnostic['description']
    
    def test_syntax_error_detection(self, analyzer):
        """Test detection of SyntaxError."""
        error_log = """
          File "app.py", line 42
            if x == 5
                    ^
          SyntaxError: invalid syntax
        """
        
        diagnostic = analyzer.analyze_error(error_log)
        
        assert diagnostic['error_type'] == 'syntax_error'
        assert diagnostic['severity'] == 'high'
    
    def test_import_error_fix_suggestion(self, analyzer):
        """Test that ImportError generates pip install command."""
        error_log = "ModuleNotFoundError: No module named 'requests'"
        
        patch = analyzer.generate_patch(
            {'error_type': 'import_error', 'description': error_log}
        )
        
        assert 'pip_install_command' in patch
        assert patch['pip_install_command'] == 'pip install requests'
    
    def test_unsafe_code_blocked(self, analyzer):
        """Test that dangerous code patterns are rejected."""
        patch = {
            'replacement': 'result = eval(user_input)'
        }
        
        validation = analyzer._validate_patch(patch)
        
        assert not validation['secure']
        assert any('eval(' in issue for issue in validation['issues'])
```

### test_sbom_generator.py

```python
"""Tests for SBOM generation."""

import json
import pytest
from pathlib import Path
from nexdev.sbom_generator import SBOMGenerator, SBOMFormat


class TestSBOMGenerator:
    """Test Software Bill of Materials generation."""
    
    @pytest.fixture
    def generator(self, tmp_path):
        gen = SBOMGenerator()
        # Create sample package files
        (tmp_path / "package.json").write_text('{"name": "test", "version": "1.0.0"}')
        return gen
    
    def test_detects_npm_project(self, generator, tmp_path):
        """Test npm project detection."""
        managers = generator._detect_package_managers(tmp_path)
        
        assert 'npm' in managers
    
    def test_generates_cyclonedx_format(self, generator):
        """Test CycloneDX JSON output format."""
        # Would create mock components
        pass
    
    def test_checks_vulnerabilities(self, generator):
        """Test vulnerability checking against OSV database."""
        # Mock OSV API response
        pass
    
    def test_license_compliance_check(self, generator):
        """Test license allowlist/denylist enforcement."""
        components = [
            Component(name="good-lib", version="1.0.0", 
                     licenses=[{'type': 'MIT'}]),
            Component(name="bad-lib", version="2.0.0",
                     licenses=[{'type': 'GPL-3.0'}])
        ]
        
        issues = generator._check_license_compliance(components)
        
        assert len([i for i in issues if i['status'] == 'denied']) >= 1
```

---

## Fixtures (conftest.py)

```python
"""Shared pytest fixtures for all tests."""

import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch


@pytest.fixture
def temp_workspace(tmp_path):
    """Create temporary workspace directory structure."""
    dirs = ['logs', 'sboms', 'audit_reports', 'performance_baselines']
    for d in dirs:
        (tmp_path / d).mkdir(parents=True)
    return tmp_path


@pytest.fixture
def mock_github_api():
    """Mock GitHub API responses."""
    with patch('requests.get') as mock_get:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'id': 123,
            'number': 42,
            'title': 'Test PR',
            'state': 'open',
            'labels': [{'name': 'bug'}]
        }
        mock_get.return_value = mock_response
        yield mock_get


@pytest.fixture
def mock_jira_api():
    """Mock Jira API responses."""
    with patch('requests.get') as mock_get, \
         patch('requests.post') as mock_post:
        # Setup mock responses
        yield mock_get, mock_post


@pytest.fixture
def sample_build_log():
    """Sample CI/CD build log for testing."""
    return """
    Running tests...
    =============================
    test_auth.py::test_login PASSED
    test_api.py::test_endpoint FAILED
    
    =================================== FAILURES ===================================
    ____________________________ test_api.test_endpoint ____________________________
    ConnectionError: Failed to connect to localhost:5432
    """


@pytest.fixture
def sample_pr_data():
    """Sample pull request data."""
    return {
        'number': 42,
        'title': 'Fix critical bug',
        'author': 'developer1',
        'files_changed': 5,
        'lines_added': 150,
        'lines_deleted': 45,
        'labels': ['bug', 'critical'],
        'created_at': '2026-03-01T10:00:00Z'
    }
```

---

## Mock Data Files

Use these for integration tests that need realistic input:

- `fixtures/sample_error_logs.txt` — Various error types
- `fixtures/sample_build_outputs/` — CI logs from different providers
- `fixtures/test_dependencies/` — Sample package-lock.json, requirements.txt
- `fixtures/mock_figma_response.json` — Figma API sample response
- `fixtures/sample_sonarqube_report.json` — Code quality report

---

## Continuous Integration

Add to `.github/workflows/test-phase4.yml`:

```yaml
name: Phase 4 Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: |
          pip install pytest pytest-cov requests
          
      - name: Run tests
        run: |
          pytest tests/ --cov=nexdev --cov-report=xml
      
      - name: Upload coverage
        uses: codecov/codecov-action@v3
```

---

## Known Limitations

1. **Jira/GitHub Integration Tests**: Require real credentials or extensive mocking
2. **Figma Parser**: Uses mock API responses; actual parsing needs valid token
3. **Performance Monitor**: Baseline establishment requires historical data
4. **Cache Warmer**: Predictive features need substantial PR history

All external service calls are mocked in unit tests by default.

---

## Adding New Tests

1. Create test file in appropriate track directory
2. Follow naming convention: `test_<module_name>.py`
3. Use pytest fixtures from `conftest.py`
4. Mock external API calls
5. Add descriptive docstrings
6. Target >70% line coverage

Example template:

```python
"""Tests for <module_name>."""

import pytest
from nexdev.<module_name> import <ClassName>


class Test<ClassName>:
    """Test class description."""
    
    @pytest.fixture
    def instance(self):
        return <ClassName>()
    
    def test_critical_functionality(self, instance):
        """Test that should always work."""
        result = instance.critical_method()
        assert result is not None
        assert result['status'] == 'success'
```
