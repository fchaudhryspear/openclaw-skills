#!/usr/bin/env python3
"""
NexDev v3.0 - Track A: Self-Healing
Dependency Upgrader

Automated dependency monitoring and safe auto-upgrades with security checks
Major versions require approval; minor/patch auto-applied
"""

import json
import subprocess
import re
from pathlib import Path
from typing import Optional, Dict, List, Tuple
from datetime import datetime, timedelta


class DependencyUpgrader:
    """Safe automated dependency upgrade system"""
    
    SUPPORTED_MANAGERS = {
        'pip': ['requirements.txt', 'Pipfile', 'pyproject.toml'],
        'npm': ['package.json', 'package-lock.json'],
        'yarn': ['yarn.lock', 'package.json'],
        'cargo': ['Cargo.toml', 'Cargo.lock'],
        'composer': ['composer.json', 'composer.lock'],
        'gem': ['Gemfile', 'Gemfile.lock']
    }
    
    SECURITY_SOURCES = [
        'https://github.com/advisories?query=type%3Areviewed+ecosystem%3Apip',
        'https://www.cvedetails.com/',
        'npm audit'
    ]
    
    def __init__(self, config_path: str = None):
        self.config = self._load_config(config_path)
        self.upgrade_log = Path.home() / '.openclaw' / 'workspace' / 'nexdev' / 'logs' / 'dependency_upgrades.jsonl'
        self.pending_approvals = Path.home() / '.openclaw' / 'workspace' / 'nexdev' / 'pending_approval.json'
        self.upgrade_log.parent.mkdir(parents=True, exist_ok=True)
        
    def _load_config(self, config_path: str) -> Dict:
        default_config = {
            'auto_upgrade_minor_patch': True,
            'require_approval_for_major': True,
            'require_approval_for_security_fixes': False,
            'blocked_packages': [],
            'allowed_packages': [],  # Empty means all allowed
            'schedule': {
                'enabled': True,
                'day_of_week': 'sunday',
                'time': '02:00'
            },
            'create_pr_for_major': True,
            'run_tests_after_upgrade': True,
            'notify_on_upgrade': True,
            'max_packages_per_run': 50
        }
        
        if config_path and Path(config_path).exists():
            try:
                with open(config_path) as f:
                    user_config = json.load(f)
                    default_config.update(user_config)
            except Exception:
                pass
                
        return default_config
        
    def scan_dependencies(self, repo_path: str = None) -> Dict:
        """
        Scan project dependencies and check for available updates
        
        Args:
            repo_path: Repository path (defaults to current directory)
            
        Returns:
            Report with outdated packages and upgrade recommendations
        """
        base_path = Path(repo_path) if repo_path else Path.cwd()
        
        report = {
            'scan_time': datetime.now().isoformat(),
            'repo_path': str(base_path),
            'managers_found': [],
            'outdated_packages': [],
            'security_vulnerabilities': [],
            'upgrade_recommendations': {
                'auto_safe': [],
                'needs_approval': [],
                'blocked': []
            }
        }
        
        # Detect package managers
        for manager, files in self.SUPPORTED_MANAGERS.items():
            for filename in files:
                if (base_path / filename).exists():
                    report['managers_found'].append(manager)
                    
                    # Scan for this manager
                    scan_result = self._scan_manager(manager, base_path)
                    report['outdated_packages'].extend(scan_result.get('packages', []))
                    report['security_vulnerabilities'].extend(
                        scan_result.get('vulnerabilities', [])
                    )
                    
        # Categorize upgrades
        for pkg in report['outdated_packages']:
            upgrade_type = self._classify_upgrade(pkg)
            
            if pkg['name'] in self.config['blocked_packages']:
                report['upgrade_recommendations']['blocked'].append(pkg)
            elif upgrade_type == 'major' or pkg.get('has_vulnerability'):
                report['upgrade_recommendations']['needs_approval'].append(pkg)
            elif self.config['auto_upgrade_minor_patch']:
                report['upgrade_recommendations']['auto_safe'].append(pkg)
                
        self._log_scan({
            'action': 'dependency_scan',
            'report': report
        })
        
        return report
        
    def _scan_manager(self, manager: str, repo_path: Path) -> Dict:
        """Scan a specific package manager for outdated dependencies"""
        result = {'packages': [], 'vulnerabilities': []}
        
        try:
            if manager == 'pip':
                result = self._scan_pip(repo_path)
            elif manager == 'npm':
                result = self._scan_npm(repo_path)
            elif manager == 'cargo':
                result = self._scan_cargo(repo_path)
            # Add more managers as needed
                
        except Exception as e:
            print(f"Error scanning {manager}: {e}")
            
        return result
        
    def _scan_pip(self, repo_path: Path) -> Dict:
        """Scan Python dependencies via pip"""
        result = {'packages': [], 'vulnerabilities': []}
        
        try:
            # Run pip list --outdated
            proc = subprocess.run(
                ['pip', 'list', '--outdated', '--format=json'],
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if proc.returncode == 0:
                outdated = json.loads(proc.stdout)
                
                for pkg in outdated:
                    name = pkg['name']
                    current = pkg['version']
                    latest = pkg['latest_version']
                    
                    version_info = self._parse_version_diff(current, latest)
                    
                    result['packages'].append({
                        'manager': 'pip',
                        'name': name,
                        'current_version': current,
                        'latest_version': latest,
                        'version_type': version_info['type'],  # major/minor/patch
                        'changelog_url': self._get_pypi_changelog(name),
                        'has_vulnerability': False  # Would check via pip-audit
                    })
                    
        except Exception as e:
            print(f"Error scanning pip: {e}")
            
        return result
        
    def _scan_npm(self, repo_path: Path) -> Dict:
        """Scan Node.js dependencies via npm"""
        result = {'packages': [], 'vulnerabilities': []}
        
        try:
            # Run npm outdated
            proc = subprocess.run(
                ['npm', 'outdated', '--json'],
                cwd=repo_path,
                capture_output=True,
                text=True,
                timeout=120
            )
            
            if proc.returncode == 0 and proc.stdout.strip():
                outdated = json.loads(proc.stdout)
                
                for name, info in outdated.items():
                    current = info.get('wanted', info.get('current'))
                    latest = info.get('latest')
                    
                    if current and latest:
                        version_info = self._parse_version_diff(current, latest)
                        
                        result['packages'].append({
                            'manager': 'npm',
                            'name': name,
                            'current_version': current,
                            'latest_version': latest,
                            'version_type': version_info['type'],
                            'changelog_url': f'https://github.com/{info.get("repository", "")}/releases' if info.get('repository') else None,
                            'has_vulnerability': False
                        })
                        
            # Check for vulnerabilities
            proc_audit = subprocess.run(
                ['npm', 'audit', '--json'],
                cwd=repo_path,
                capture_output=True,
                text=True,
                timeout=120
            )
            
            if proc_audit.returncode == 0:
                audit = json.loads(proc_audit.stdout)
                
                for id_, vuln in audit.get('actions', []).items():
                    result['vulnerabilities'].append({
                        'id': id_,
                        'package': vuln.get('module_name'),
                        'severity': vuln.get('severity', 'unknown'),
                        'vulnerable_versions': vuln.get('vulnerable_versions'),
                        'fixed_in': vuln.get('resolution', {}).get('target'),
                        'url': vuln.get('url')
                    })
                    
        except Exception as e:
            print(f"Error scanning npm: {e}")
            
        return result
        
    def _scan_cargo(self, repo_path: Path) -> Dict:
        """Scan Rust dependencies via cargo"""
        result = {'packages': [], 'vulnerabilities': []}
        
        try:
            proc = subprocess.run(
                ['cargo', 'update', '--dry-run', '--message-format=json'],
                cwd=repo_path,
                capture_output=True,
                text=True,
                timeout=120
            )
            
            # Simplified - would parse cargo-outdated output properly
            # This is a placeholder
            
        except Exception as e:
            print(f"Error scanning cargo: {e}")
            
        return result
        
    def _parse_version_diff(self, current: str, latest: str) -> Dict:
        """Parse semantic version difference"""
        def extract_numbers(version):
            # Extract numeric parts from version string
            match = re.match(r'v?(\d+)\.?(\d*)\.?(\d*)', version)
            if match:
                major = int(match.group(1))
                minor = int(match.group(2)) if match.group(2) else 0
                patch = int(match.group(3)) if match.group(3) else 0
                return (major, minor, patch)
            return (0, 0, 0)
            
        curr = extract_numbers(current)
        lat = extract_numbers(latest)
        
        if lat[0] > curr[0]:
            version_type = 'major'
        elif lat[1] > curr[1]:
            version_type = 'minor'
        else:
            version_type = 'patch'
            
        return {
            'type': version_type,
            'from': current,
            'to': latest,
            'is_upgrade': lat > curr
        }
        
    def _get_pypi_changelog(self, package_name: str) -> Optional[str]:
        """Get PyPI changelog URL"""
        return f"https://pypi.org/project/{package_name}/#history"
        
    def _classify_upgrade(self, pkg: Dict) -> str:
        """Classify upgrade type"""
        return pkg.get('version_type', 'unknown')
        
    async def apply_upgrades(self, packages: List[Dict], dry_run: bool = True) -> Dict:
        """
        Apply dependency upgrades
        
        Args:
            packages: List of package dicts to upgrade
            dry_run: If True, only simulate upgrades
            
        Returns:
            Upgrade results with status for each package
        """
        results = {
            'timestamp': datetime.now().isoformat(),
            'dry_run': dry_run,
            'total_packages': len(packages),
            'successful': [],
            'failed': [],
            'skipped': []
        }
        
        for pkg in packages:
            manager = pkg.get('manager')
            name = pkg.get('name')
            version = pkg.get('latest_version')
            
            result = await self._upgrade_package(manager, name, version, dry_run)
            
            if result.get('success'):
                results['successful'].append(pkg)
            elif result.get('skipped'):
                results['skipped'].append(pkg)
            else:
                results['failed'].append({
                    'package': pkg,
                    'error': result.get('error')
                })
                
        # Run tests if configured
        if not dry_run and self.config['run_tests_after_upgrade'] and results['successful']:
            test_result = await self._run_post_upgrade_tests()
            results['tests'] = test_result
            
        self._log_upgrade({
            'action': 'apply_upgrades',
            'results': results,
            'dry_run': dry_run
        })
        
        return results
        
    async def _upgrade_package(self, manager: str, name: str, version: str, 
                               dry_run: bool) -> Dict:
        """Upgrade a single package"""
        result = {'success': False, 'name': name, 'manager': manager}
        
        try:
            if manager == 'pip':
                cmd = ['pip', 'install', f'{name}>={version}']
                if dry_run:
                    cmd.append('--dry-run')
                    
                proc = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=120
                )
                
                result['success'] = proc.returncode == 0
                result['output'] = proc.stdout[:500]
                
            elif manager == 'npm':
                cmd = ['npm', 'install', f'{name}@{version}']
                
                proc = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=180
                )
                
                result['success'] = proc.returncode == 0
                result['output'] = proc.stdout[:500]
                
            else:
                result['error'] = f'Unsupported package manager: {manager}'
                
        except Exception as e:
            result['error'] = str(e)
            
        return result
        
    async def _run_post_upgrade_tests(self) -> Dict:
        """Run tests after upgrades"""
        # In real implementation, would detect test framework and run appropriate command
        return {
            'ran': True,
            'status': 'skipped',  # Placeholder
            'message': 'Test runner not configured'
        }
        
    def request_major_approval(self, packages: List[Dict]) -> Dict:
        """
        Request approval for major version upgrades
        
        Args:
            packages: List of packages requiring approval
            
        Returns:
            Approval request record
        """
        approval_id = f"maj-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        approval_request = {
            'id': approval_id,
            'created_at': datetime.now().isoformat(),
            'status': 'pending',
            'packages': packages,
            'summary': self._generate_approval_summary(packages)
        }
        
        # Save pending approvals
        pending = self._load_pending_approvals()
        pending[approval_id] = approval_request
        self._save_pending_approvals(pending)
        
        # Create PR if configured
        if self.config['create_pr_for_major']:
            self._create_upgrade_pr(approval_request)
            
        return approval_request
        
    def _generate_approval_summary(self, packages: List[Dict]) -> str:
        """Generate human-readable summary for approval"""
        lines = ["🚨 Major Version Upgrades Requiring Approval\n"]
        
        for pkg in packages:
            lines.append(f"\n• **{pkg['name']}**")
            lines.append(f"  Current: {pkg['current_version']} → Latest: {pkg['latest_version']}")
            lines.append(f"  Manager: {pkg['manager']}")
            if pkg.get('changelog_url'):
                lines.append(f"  Changelog: {pkg['changelog_url']}")
                
        lines.append(f"\nTotal: {len(packages)} package(s)")
        
        return "\n".join(lines)
        
    def _create_upgrade_pr(self, approval_request: Dict):
        """Create GitHub PR for major upgrades"""
        # In real implementation, would use GitHub API
        title = f"feat: Major dependency updates ({len(approval_request['packages'])} packages)"
        
        body = f"""
## Major Dependency Upgrades

This PR was automatically generated by NexDev dependency upgrader.

{approval_request['summary']}

### Actions Required
- [ ] Review changelogs for breaking changes
- [ ] Test thoroughly in staging
- [ ] Update documentation if APIs changed
- [ ] Run full test suite

Approved by: @mention-reviewer
"""
        
        print(f"Would create PR: {title}")
        print(f"Body:\n{body}")
        
    def approve_upgrade(self, approval_id: str) -> Dict:
        """Approve a pending upgrade request"""
        pending = self._load_pending_approvals()
        
        if approval_id not in pending:
            return {'status': 'error', 'message': 'Approval request not found'}
            
        request = pending[approval_id]
        
        if request['status'] != 'pending':
            return {'status': 'error', 'message': 'Request already processed'}
            
        # Mark as approved
        request['status'] = 'approved'
        request['approved_at'] = datetime.now().isoformat()
        
        # Apply upgrades
        upgrade_result = self.apply_upgrades(request['packages'], dry_run=False)
        
        # Remove from pending
        del pending[approval_id]
        self._save_pending_approvals(pending)
        
        return {
            'status': 'success',
            'approval_id': approval_id,
            'upgrade_result': upgrade_result
        }
        
    def reject_upgrade(self, approval_id: str, reason: str = None) -> Dict:
        """Reject a pending upgrade request"""
        pending = self._load_pending_approvals()
        
        if approval_id not in pending:
            return {'status': 'error', 'message': 'Approval request not found'}
            
        request = pending[approval_id]
        request['status'] = 'rejected'
        request['rejected_at'] = datetime.now().isoformat()
        request['rejection_reason'] = reason
        
        del pending[approval_id]
        self._save_pending_approvals(pending)
        
        return {
            'status': 'success',
            'approval_id': approval_id,
            'reason': reason
        }
        
    def _load_pending_approvals(self) -> Dict:
        """Load pending approval requests"""
        if not self.pending_approvals.exists():
            return {}
            
        try:
            with open(self.pending_approvals) as f:
                return json.load(f)
        except Exception:
            return {}
            
    def _save_pending_approvals(self, pending: Dict):
        """Save pending approval requests"""
        with open(self.pending_approvals, 'w') as f:
            json.dump(pending, f, indent=2, default=str)
            
    def _log_scan(self, entry: Dict):
        """Log scan to JSONL file"""
        entry['timestamp'] = datetime.now().isoformat()
        
        with open(self.upgrade_log, 'a') as f:
            f.write(json.dumps(entry) + '\n')
            
    def _log_upgrade(self, entry: Dict):
        """Log upgrade attempt to JSONL file"""
        entry['timestamp'] = datetime.now().isoformat()
        
        with open(self.upgrade_log, 'a') as f:
            f.write(json.dumps(entry) + '\n')


# CLI Entry Point
if __name__ == '__main__':
    import asyncio
    import sys
    
    print("NexDev Dependency Upgrader v3.0")
    print("=" * 50)
    
    upgrader = DependencyUpgrader()
    
    if len(sys.argv) < 2:
        print("\nUsage:")
        print("  python dependency_upgrader.py scan [repo_path]")
        print("  python dependency_upgrader.py upgrade [--dry-run]")
        print("  python dependency_upgrader.py list-pending")
        print("  python dependency_upgrader.py approve <approval_id>")
        sys.exit(1)
        
    command = sys.argv[1]
    
    if command == 'scan':
        repo_path = sys.argv[2] if len(sys.argv) > 2 else None
        report = upgrader.scan_dependencies(repo_path)
        print(json.dumps(report, indent=2))
        
    elif command == 'upgrade':
        dry_run = '--dry-run' in sys.argv
        report = upgrader.scan_dependencies()
        
        packages = report['upgrade_recommendations']['auto_safe']
        
        if packages:
            print(f"\nUpgrading {len(packages)} auto-safe package(s)...")
            result = asyncio.run(upgrader.apply_upgrades(packages, dry_run=dry_run))
            print(json.dumps(result, indent=2))
        else:
            print("\nNo auto-safe upgrades available")
            
        # Check for major upgrades needing approval
        majors = report['upgrade_recommendations']['needs_approval']
        if majors:
            print(f"\n⚠️  {len(majors)} major upgrade(s) require approval:")
            for pkg in majors[:5]:
                print(f"  - {pkg['name']}: {pkg['current_version']} → {pkg['latest_version']}")
                
    elif command == 'list-pending':
        pending = upgrader._load_pending_approvals()
        
        if not pending:
            print("\nNo pending approvals")
        else:
            print(f"\n{len(pending)} pending approval(s):\n")
            for pid, req in pending.items():
                print(f"🔸 {pid} - {len(req['packages'])} package(s) - {req['status']}")
                
    elif command == 'approve':
        if len(sys.argv) < 3:
            print("Usage: python dependency_upgrader.py approve <approval_id>")
            sys.exit(1)
            
        result = upgrader.approve_upgrade(sys.argv[2])
        print(json.dumps(result, indent=2))
