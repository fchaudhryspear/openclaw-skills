#!/usr/bin/env python3
"""
NexDev v3.0 - Track C: Production Hardening
SBOM (Software Bill of Materials) Generator

Generate SBOM in CycloneDX and SPDX formats for supply chain security
Supports: pip, npm, cargo, maven, gradle dependencies
"""

import json
import subprocess
from pathlib import Path
from typing import Optional, Dict, List, Tuple
from datetime import datetime
from dataclasses import dataclass, asdict, field
from enum import Enum


class SBOMFormat(Enum):
    CYCLONEDX = "cyclonedx"
    SPDX = "spdx"


@dataclass
class Component:
    type: str  # library, application, framework
    name: str
    version: str
    supplier: str = None
    purl: str = None  # Package URL
    cpe: str = None   # Common Platform Enumeration
    licenses: List[Dict] = field(default_factory=list)
    hashes: Dict[str, str] = field(default_factory=dict)
    external_references: List[Dict] = field(default_factory=list)


@dataclass
class Vulnerability:
    id: str
    source: str
    severity: str  # CRITICAL, HIGH, MEDIUM, LOW, INFO
    description: str
    recommendations: str
    affected_versions: List[str]
    fixed_version: str = None


@dataclass 
class SBOM:
    spec_version: str
    version: int
    metadata: Dict
    components: List[Component]
    vulnerabilities: List[Vulnerability] = None
    dependencies: List[Dict] = None
    serial_number: str = None
    generated_at: str = None


class SBOMGenerator:
    """Generate Software Bill of Materials in standard formats"""
    
    SUPPORTED_MANAGERS = {
        'pip': ['requirements.txt', 'Pipfile.lock', 'poetry.lock'],
        'npm': ['package-lock.json', 'yarn.lock', 'package.json'],  # Added package.json fallback
        'cargo': ['Cargo.lock'],
        'maven': ['pom.xml', 'target/*.jar'],
        'gradle': ['build.gradle', 'build.gradle.kts'],
        'composer': ['composer.lock']
    }
    
    def __init__(self, config_path: str = None):
        self.config = self._load_config(config_path)
        self.sbom_output_dir = Path.home() / '.openclaw' / 'workspace' / 'nexdev' / 'sboms'
        self.sbom_output_dir.mkdir(parents=True, exist_ok=True)
        
    def _load_config(self, config_path: str) -> Dict:
        default_config = {
            'output': {
                'formats': ['cyclonedx', 'spdx'],
                'include_dev_dependencies': False,
                'include_transitive': True
            },
            'scanning': {
                'check_vulnerabilities': True,
                'check_licenses': True,
                'license_allowlist': ['MIT', 'Apache-2.0', 'BSD-3-Clause', 'ISC'],
                'license_denylist': ['GPL-3.0', 'AGPL-3.0']
            },
            'vulnerability_sources': {
                'osv': True,  # Open Source Vulnerabilities
                'nvd': False,  # NVD (requires API key)
                'github_advisories': True
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
        
    async def generate_sbom(self, repo_path: str = None, 
                           output_format: SBOMFormat = None) -> SBOM:
        """
        Generate SBOM for a project
        
        Args:
            repo_path: Repository path (defaults to current directory)
            output_format: Output format (defaults to config setting)
            
        Returns:
            Complete SBOM object
        """
        base_path = Path(repo_path) if repo_path else Path.cwd()
        
        # Detect package managers
        managers_found = self._detect_package_managers(base_path)
        
        if not managers_found:
            raise ValueError("No supported package managers found")
            
        # Collect all components
        components = []
        dependencies = []
        
        for manager in managers_found:
            manager_components, manager_deps = await self._scan_manager(manager, base_path)
            components.extend(manager_components)
            dependencies.extend(manager_deps)
            
        # Check for vulnerabilities
        vulnerabilities = []
        if self.config['scanning']['check_vulnerabilities']:
            print("\n🔍 Scanning for vulnerabilities...")
            vulnerabilities = await self._check_vulnerabilities(components)
            
        # Check license compliance
        license_issues = []
        if self.config['scanning']['check_licenses']:
            license_issues = self._check_license_compliance(components)
            
        # Build metadata
        metadata = {
            'timestamp': datetime.now().isoformat(),
            'tools': [{
                'vendor': 'NexDev',
                'name': 'sbom-generator',
                'version': '3.0.0'
            }],
            'component': {
                'type': 'application',
                'name': base_path.name,
                'version': self._detect_project_version(base_path)
            },
            'manufacture': self.config.get('organization', {}).get('name'),
            'supplier': self.config.get('organization', {}).get('name')
        }
        
        serial_number = f"urn:uuid:{self._generate_uuid()}"
        
        return SBOM(
            spec_version="1.5" if output_format == SBOMFormat.CYCLONEDX else "2.3",
            version=1,
            metadata=metadata,
            components=components,
            vulnerabilities=vulnerabilities,
            dependencies=dependencies,
            serial_number=serial_number,
            generated_at=datetime.now().isoformat()
        )
        
    def _detect_package_managers(self, base_path: Path) -> List[str]:
        """Detect which package managers are used in the project"""
        managers = []
        
        for manager, filenames in self.SUPPORTED_MANAGERS.items():
            for filename in filenames:
                if '*' in filename:
                    # Glob pattern
                    matches = list(base_path.glob(filename))
                    if matches:
                        managers.append(manager)
                        break
                else:
                    if (base_path / filename).exists():
                        managers.append(manager)
                        break
                        
        return managers
        
    async def _scan_manager(self, manager: str, base_path: Path) -> Tuple[List[Component], List[Dict]]:
        """Scan a specific package manager for dependencies"""
        components = []
        dependencies = []
        
        if manager == 'pip':
            components, dependencies = await self._scan_pip(base_path)
        elif manager == 'npm':
            components, dependencies = await self._scan_npm(base_path)
        elif manager == 'cargo':
            components, dependencies = await self._scan_cargo(base_path)
        # Add more managers
            
        return components, dependencies
        
    async def _scan_pip(self, base_path: Path) -> Tuple[List[Component], List[Dict]]:
        """Scan Python dependencies via pip"""
        components = []
        dependencies = []
        
        try:
            # Get installed packages with pip list
            proc = subprocess.run(
                ['pip', 'list', '--format=json'],
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if proc.returncode == 0:
                packages = json.loads(proc.stdout)
                
                for pkg in packages:
                    component = Component(
                        type='library',
                        name=pkg['name'],
                        version=pkg['version'],
                        purl=f"pkg:pypi/{pkg['name'].lower()}@{pkg['version']}",
                        licenses=self._get_pypi_licenses(pkg['name'], pkg['version'])
                    )
                    components.append(component)
                    
        except Exception as e:
            print(f"Error scanning pip: {e}")
            
        return components, dependencies
        
    async def _scan_npm(self, base_path: Path) -> Tuple[List[Component], List[Dict]]:
        """Scan Node.js dependencies via npm"""
        components = []
        dependencies = []
        
        try:
            # Try package-lock.json first, then yarn.lock, then package.json
            lock_file = base_path / 'package-lock.json'
            
            if lock_file.exists():
                with open(lock_file) as f:
                    lock_data = json.load(f)
                    
                packages = lock_data.get('packages', {}) or lock_data.get('dependencies', {})
                
                for name, info in packages.items():
                    if name == '' or not info.get('version'):
                        continue
                        
                    clean_name = name.replace('node_modules/', '').split('/')[-1]
                    
                    component = Component(
                        type='library',
                        name=clean_name,
                        version=info.get('version'),
                        purl=f"pkg:npm/{clean_name}@{info.get('version')}",
                        licenses=info.get('license') if isinstance(info.get('license'), list) else [{'type': info.get('license')}]
                    )
                    components.append(component)
                    
            # Fallback: parse package.json for basic deps (when no lock file)
            elif (base_path / 'package.json').exists():
                with open(base_path / 'package.json') as f:
                    pkg_json = json.load(f)
                    
                # Get dependencies and devDependencies
                all_deps = {
                    **pkg_json.get('dependencies', {}),
                    **pkg_json.get('devDependencies', {})
                }
                
                for name, version in all_deps.items():
                    # Version might be "^1.2.3" - extract actual version number
                    clean_version = version.lstrip('^~>=')
                    
                    component = Component(
                        type='library',
                        name=name,
                        version=clean_version,
                        purl=f"pkg:npm/{name}@{clean_version}"
                    )
                    components.append(component)
                        
        except Exception as e:
            print(f"Error scanning npm: {e}")
            
        return components, dependencies
        
    async def _scan_cargo(self, base_path: Path) -> Tuple[List[Component], List[Dict]]:
        """Scan Rust dependencies via Cargo.lock"""
        components = []
        dependencies = []
        
        try:
            lock_file = base_path / 'Cargo.lock'
            
            if lock_file.exists():
                # Parse TOML (simplified - would use toml library)
                content = lock_file.read_text()
                
                # Simple regex parsing for demo
                import re
                package_pattern = r'\[\[package\]\]\nname = "([^"]+)"\nversion = "([^"]+)"'
                
                for match in re.finditer(package_pattern, content):
                    name, version = match.groups()
                    
                    component = Component(
                        type='library',
                        name=name,
                        version=version,
                        purl=f"pkg:cargo/{name}@{version}"
                    )
                    components.append(component)
                    
        except Exception as e:
            print(f"Error scanning cargo: {e}")
            
        return components, dependencies
        
    def _get_pypi_licenses(self, package_name: str, version: str) -> List[Dict]:
        """Get license info from PyPI"""
        try:
            response = requests.get(
                f"https://pypi.org/pypi/{package_name}/{version}/json",
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                license_str = data['info'].get('license', '')
                
                if license_str:
                    return [{'type': license_str}]
                    
        except Exception:
            pass
            
        return []
        
    async def _check_vulnerabilities(self, components: List[Component]) -> List[Vulnerability]:
        """Check components against vulnerability databases"""
        vulnerabilities = []
        
        # Use OSV (Open Source Vulnerabilities) API
        for component in components:
            vulns = await self._check_osv(component)
            vulnerabilities.extend(vulns)
            
        # Can add more sources: Snyk, GitHub Advisories, NVD
        
        return vulnerabilities
        
    async def _check_osv(self, component: Component) -> List[Vulnerability]:
        """Check component against OSV database"""
        vulns = []
        
        try:
            # OSV query format
            payload = {
                'package': {
                    'name': component.name,
                    'ecosystem': 'PyPI' if component.purl and 'pypi' in component.purl else 'npm'
                },
                'version': component.version
            }
            
            response = requests.post(
                'https://api.osv.dev/v1/query',
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                
                for vuln_data in data.get('vulns', []):
                    severity = 'UNKNOWN'
                    for impact in vuln_data.get('severity', []):
                        if impact['type'] == 'CVSS_V3':
                            score = float(impact['score'].split('/')[0])
                            if score >= 9.0:
                                severity = 'CRITICAL'
                            elif score >= 7.0:
                                severity = 'HIGH'
                            elif score >= 4.0:
                                severity = 'MEDIUM'
                            else:
                                severity = 'LOW'
                                
                    vuln = Vulnerability(
                        id=vuln_data['id'],
                        source='OSV',
                        severity=severity,
                        description=vuln_data.get('details', ''),
                        recommendations=vuln_data.get('references', [{}])[0].get('url', ''),
                        affected_versions=[vuln_data.get('summary', '')],
                        fixed_version=None
                    )
                    vulns.append(vuln)
                    
        except Exception as e:
            print(f"Error checking OSV for {component.name}: {e}")
            
        return vulns
        
    def _check_license_compliance(self, components: List[Component]) -> List[Dict]:
        """Check components against allowed/denied license lists"""
        issues = []
        
        allowlist = self.config['scanning']['license_allowlist']
        denylist = self.config['scanning']['license_denylist']
        
        for component in components:
            for license_info in component.licenses:
                license_type = license_info.get('type', '')
                
                if license_type in denylist:
                    issues.append({
                        'component': component.name,
                        'version': component.version,
                        'license': license_type,
                        'status': 'denied',
                        'message': f"License {license_type} is on denylist"
                    })
                elif license_type and license_type not in allowlist:
                    issues.append({
                        'component': component.name,
                        'version': component.version,
                        'license': license_type,
                        'status': 'unknown',
                        'message': f"License {license_type} not in allowlist"
                    })
                    
        return issues
        
    def _detect_project_version(self, base_path: Path) -> str:
        """Detect project version from common files"""
        # Check pyproject.toml, package.json, Cargo.toml, etc.
        
        package_json = base_path / 'package.json'
        if package_json.exists():
            try:
                with open(package_json) as f:
                    data = json.load(f)
                    return data.get('version', '0.0.0')
            except Exception:
                pass
                
        pyproject = base_path / 'pyproject.toml'
        if pyproject.exists():
            content = pyproject.read_text()
            import re
            match = re.search(r'version\s*=\s*"([^"]+)"', content)
            if match:
                return match.group(1)
                
        return '0.0.0'
        
    def _generate_uuid(self) -> str:
        """Generate UUID for serial number"""
        import uuid
        return str(uuid.uuid4())
        
    def export_sbom(self, sbom: SBOM, output_format: SBOMFormat, 
                    output_path: str = None) -> str:
        """Export SBOM to file in specified format"""
        if output_format == SBOMFormat.CYCLONEDX:
            return self._export_cyclonedx(sbom, output_path)
        elif output_format == SBOMFormat.SPDX:
            return self._export_spdx(sbom, output_path)
            
    def _export_cyclonedx(self, sbom: SBOM, output_path: str = None) -> str:
        """Export to CycloneDX JSON format"""
        cyclonedx_doc = {
            'bomFormat': 'CycloneDX',
            'specVersion': sbom.spec_version,
            'serialNumber': sbom.serial_number,
            'version': sbom.version,
            'metadata': sbom.metadata,
            'components': [],
            'vulnerabilities': []
        }
        
        # Convert components
        for comp in sbom.components:
            comp_dict = {
                'type': comp.type,
                'name': comp.name,
                'version': comp.version,
                'purl': comp.purl
            }
            
            if comp.supplier:
                comp_dict['supplier'] = {'name': comp.supplier}
                
            if comp.licenses:
                comp_dict['licenses'] = [
                    {'license': lic} for lic in comp.licenses
                ]
                
            if comp.hashes:
                comp_dict['hashes'] = [
                    {'alg': alg, 'content': val} for alg, val in comp.hashes.items()
                ]
                
            cyclonedx_doc['components'].append(comp_dict)
            
        # Convert vulnerabilities
        if sbom.vulnerabilities:
            for vuln in sbom.vulnerabilities:
                cyclonedx_doc['vulnerabilities'].append({
                    'id': vuln.id,
                    'source': {'name': vuln.source},
                    'ratings': [{'severity': vuln.severity.lower()}],
                    'description': vuln.description,
                    'recommendations': vuln.recommendations
                })
                
        # Write to file
        output_path = output_path or str(
            self.sbom_output_dir / f"sbom_{datetime.now().strftime('%Y%m%d_%H%M%S')}.cyclonedx.json"
        )
        
        with open(output_path, 'w') as f:
            json.dump(cyclonedx_doc, f, indent=2)
            
        print(f"\n✅ CycloneDX SBOM saved to: {output_path}")
        return output_path
        
    def _export_spdx(self, sbom: SBOM, output_path: str = None) -> str:
        """Export to SPDX JSON format"""
        spdx_doc = {
            'spdxVersion': f"SPDX-{sbom.spec_version}",
            'dataLicense': 'CC0-1.0',
            'SPDXID': 'SPDXRef-DOCUMENT',
            'name': sbom.metadata['component']['name'],
            'documentNamespace': sbom.serial_number,
            'creationInfo': {
                'created': sbom.generated_at,
                'creators': ['Tool: NexDev-SBOM-Generator-3.0.0']
            },
            'packages': [],
            'relationships': []
        }
        
        # Convert components to packages
        for i, comp in enumerate(sbom.components):
            pkg = {
                'SPDXID': f"SPDXRef-Package-{i}",
                'name': comp.name,
                'versionInfo': comp.version,
                'downloadLocation': 'NOASSERTION',
                'filesAnalyzed': False
            }
            
            if comp.purl:
                pkg['externalRefs'] = [{
                    'referenceCategory': 'PACKAGE-MANAGER',
                    'referenceType': 'purl',
                    'referenceLocator': comp.purl
                }]
                
            if comp.licenses:
                license_ids = [lic.get('type', 'NOASSERTION') for lic in comp.licenses]
                pkg['licenseConcluded'] = license_ids[0] if len(license_ids) == 1 else 'AND'.join(license_ids)
                
            spdx_doc['packages'].append(pkg)
            
        # Write to file
        output_path = output_path or str(
            self.sbom_output_dir / f"sbom_{datetime.now().strftime('%Y%m%d_%H%M%S')}.spdx.json"
        )
        
        with open(output_path, 'w') as f:
            json.dump(spdx_doc, f, indent=2)
            
        print(f"\n✅ SPDX SBOM saved to: {output_path}")
        return output_path


# CLI Entry Point
if __name__ == '__main__':
    import asyncio
    import sys
    
    print("NexDev SBOM Generator v3.0")
    print("=" * 50)
    
    generator = SBOMGenerator()
    
    if len(sys.argv) < 2:
        print("\nUsage:")
        print("  python sbom_generator.py generate [repo_path]")
        print("  python sbom_generator.py export [cyclonedx|spdx] [repo_path]")
        sys.exit(1)
        
    command = sys.argv[1]
    
    if command == 'generate':
        repo_path = sys.argv[2] if len(sys.argv) > 2 else None
        
        print(f"\n📦 Generating SBOM for: {repo_path or 'current directory'}")
        sbom = asyncio.run(generator.generate_sbom(repo_path))
        
        print(f"\n✅ Generated SBOM with {len(sbom.components)} components")
        if sbom.vulnerabilities:
            print(f"⚠️  Found {len(sbom.vulnerabilities)} vulnerabilities:")
            for vuln in sbom.vulnerabilities[:5]:
                print(f"   - {vuln.id}: {vuln.severity}")
                
        # Export both formats
        generator.export_sbom(sbom, SBOMFormat.CYCLONEDX)
        generator.export_sbom(sbom, SBOMFormat.SPDX)
        
    elif command == 'export':
        fmt = sys.argv[2] if len(sys.argv) > 2 else 'cyclonedx'
        repo_path = sys.argv[3] if len(sys.argv) > 3 else None
        
        sbom = asyncio.run(generator.generate_sbom(repo_path))
        
        format_map = {
            'cyclonedx': SBOMFormat.CYCLONEDX,
            'spdx': SBOMFormat.SPDX
        }
        
        generator.export_sbom(sbom, format_map.get(fmt, SBOMFormat.CYCLONEDX))
