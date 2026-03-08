#!/usr/bin/env python3
"""
NexDev Skill Marketplace (Phase 4 Feature)

Extend NexDev with custom domain-specific skills/patterns.
Download, install, and manage skills from marketplace or private repos.
Part of NexDev v3.0 World-Class Build Team Upgrade
"""

import json
import shutil
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from datetime import datetime
import hashlib
import requests
import zipfile


SKILLS_DIR = Path.home() / ".openclaw/workspace/nexdev/skills"
MARKETPLACE_INDEX_URL = "https://api.nexdev.dev/v1/skills/index.json"


@dataclass
class Skill:
    """Represents an installable skill."""
    id: str
    name: str
    version: str
    description: str
    author: str
    category: str  # "web", "mobile", "enterprise", "fintech", "healthcare"
    tags: List[str]
    min_nexdev_version: str
    documentation_url: Optional[str]
    license: str
    download_count: int
    rating: float
    last_updated: str


def init_skills_directory():
    """Initialize skills directory structure."""
    SKILLS_DIR.mkdir(parents=True, exist_ok=True)
    
    # Create installed.json if it doesn't exist
    index_file = SKILLS_DIR / "installed.json"
    if not index_file.exists():
        with open(index_file, 'w') as f:
            json.dump({"skills": [], "version": "1.0"}, f, indent=2)


def get_installed_skills() -> List[Dict[str, Any]]:
    """Get list of installed skills."""
    init_skills_directory()
    index_file = SKILLS_DIR / "installed.json"
    
    try:
        with open(index_file, 'r') as f:
            data = json.load(f)
        return data.get("skills", [])
    except (json.JSONDecodeError, FileNotFoundError):
        return []


def search_marketplace(category: Optional[str] = None, 
                      query: Optional[str] = None) -> List[Skill]:
    """
    Search available skills in marketplace.
    
    Note: This is a mock implementation. Real version would call marketplace API.
    """
    # Sample skills catalog
    sample_skills = [
        Skill(
            id="skill_finetech_payments",
            name="FinTech Payments",
            version="1.2.0",
            description="Domain patterns for payment processing, PCI compliance, and transaction handling",
            author="NexDev Inc.",
            category="fintech",
            tags=["payments", "pci-dss", "transactions", "financial"],
            min_nexdev_version="3.0.0",
            documentation_url="https://docs.nexdev.dev/skills/finetech-payments",
            license="MIT",
            download_count=1523,
            rating=4.7,
            last_updated=datetime.now().isoformat()
        ),
        Skill(
            id="skill_healthcare_hipaa",
            name="Healthcare HIPAA Compliance",
            version="2.0.1",
            description="HIPAA-compliant patterns for healthcare applications",
            author="MedTech Solutions",
            category="healthcare",
            tags=["hipaa", "phr", "patient-data", "compliance"],
            min_nexdev_version="3.0.0",
            documentation_url="https://docs.nexdev.dev/skills/healthcare",
            license="Apache-2.0",
            download_count=892,
            rating=4.9,
            last_updated=datetime.now().isoformat()
        ),
        Skill(
            id="skill_web_react_best_practices",
            name="React Best Practices",
            version="3.1.0",
            description="React hooks, performance optimization, and modern patterns",
            author="Frontend Masters",
            category="web",
            tags=["react", "hooks", "performance", "frontend"],
            min_nexdev_version="3.0.0",
            documentation_url="https://docs.nexdev.dev/skills/react",
            license="MIT",
            download_count=5234,
            rating=4.6,
            last_updated=datetime.now().isoformat()
        )
    ]
    
    results = []
    for skill in sample_skills:
        # Filter by category
        if category and skill.category != category:
            continue
        
        # Filter by query
        if query:
            query_lower = query.lower()
            matches = (
                query_lower in skill.name.lower() or
                query_lower in skill.description.lower() or
                any(query_lower in tag for tag in skill.tags)
            )
            if not matches:
                continue
        
        results.append(skill)
    
    return results


def install_skill(skill_id: str, source: str = "marketplace") -> bool:
    """
    Install a skill.
    
    Args:
        skill_id: Skill identifier
        source: Source ("marketplace" or local path)
        
    Returns:
        True if successful
    """
    init_skills_directory()
    
    # Find skill info
    all_skills = search_marketplace()
    skill_info = next((s for s in all_skills if s.id == skill_id), None)
    
    if not skill_info:
        print(f"❌ Skill not found: {skill_id}")
        return False
    
    skill_dir = SKILLS_DIR / skill_id
    skill_dir.mkdir(parents=True, exist_ok=True)
    
    # Create skill metadata file
    metadata = {
        "id": skill_info.id,
        "name": skill_info.name,
        "version": skill_info.version,
        "author": skill_info.author,
        "install_date": datetime.now().isoformat(),
        "source": source
    }
    
    metadata_file = skill_dir / "skill.json"
    with open(metadata_file, 'w') as f:
        json.dump(metadata, f, indent=2)
    
    # Add to installed list
    installed = get_installed_skills()
    installed.append({
        "id": skill_info.id,
        "name": skill_info.name,
        "version": skill_info.version,
        "category": skill_info.category,
        "installed_at": datetime.now().isoformat()
    })
    
    with open(SKILLS_DIR / "installed.json", 'w') as f:
        json.dump({"skills": installed}, f, indent=2)
    
    # Update download count (would be in real marketplace API)
    print(f"✅ Installed: {skill_info.name} v{skill_info.version}")
    print(f"   Category: {skill_info.category}")
    print(f"   Documentation: {skill_info.documentation_url}")
    
    return True


def uninstall_skill(skill_id: str) -> bool:
    """Uninstall a skill."""
    skill_dir = SKILLS_DIR / skill_id
    
    if not skill_dir.exists():
        print(f"❌ Skill not installed: {skill_id}")
        return False
    
    # Remove directory
    shutil.rmtree(skill_dir)
    
    # Update installed list
    installed = get_installed_skills()
    installed = [s for s in installed if s['id'] != skill_id]
    
    with open(SKILLS_DIR / "installed.json", 'w') as f:
        json.dump({"skills": installed}, f, indent=2)
    
    print(f"✅ Uninstalled: {skill_id}")
    return True


def load_skill_patterns(skill_id: str) -> List[Dict[str, Any]]:
    """Load patterns/rules from an installed skill."""
    skill_dir = SKILLS_DIR / skill_id
    
    if not skill_dir.exists():
        return []
    
    # Look for patterns.json in skill directory
    patterns_file = skill_dir / "patterns.json"
    
    if patterns_file.exists():
        with open(patterns_file, 'r') as f:
            return json.load(f).get("patterns", [])
    
    return []


def validate_skill(skill_path: Path) -> Dict[str, Any]:
    """
    Validate a skill package before installation.
    
    Args:
        skill_path: Path to skill archive or directory
        
    Returns:
        Validation result with errors/warnings
    """
    result = {
        'valid': True,
        'errors': [],
        'warnings': [],
        'metadata': {}
    }
    
    # Check required files
    required_files = ["skill.json"]
    
    if skill_path.is_dir():
        for req_file in required_files:
            if not (skill_path / req_file).exists():
                result['errors'].append(f"Missing required file: {req_file}")
                result['valid'] = False
    elif skill_path.suffix == '.zip':
        # Would extract and check contents
        pass
    else:
        result['errors'].append("Invalid skill format. Expected directory or .zip")
        result['valid'] = False
    
    # Check skill.json format
    if result['valid']:
        try:
            skill_json = skill_path / "skill.json"
            with open(skill_json, 'r') as f:
                metadata = json.load(f)
            
            required_keys = ["id", "name", "version"]
            for key in required_keys:
                if key not in metadata:
                    result['errors'].append(f"Missing required key: {key}")
                    result['valid'] = False
            
            result['metadata'] = metadata
            
        except json.JSONDecodeError as e:
            result['errors'].append(f"Invalid JSON in skill.json: {e}")
            result['valid'] = False
    
    return result


if __name__ == "__main__":
    # Demo mode
    print("=" * 60)
    print("📦 NEXDEV SKILL MARKETPLACE - DEMO")
    print("=" * 60)
    
    init_skills_directory()
    
    # List installed skills
    print("\n📚 Currently Installed Skills:")
    installed = get_installed_skills()
    
    if installed:
        for skill in installed:
            print(f"  • {skill['name']} v{skill['version']} ({skill['category']})")
    else:
        print("  No skills installed yet")
    
    # Search marketplace
    print("\n🔍 Searching Marketplace...")
    
    # Search for fintech skills
    finetech_skills = search_marketplace(category="fintech")
    print(f"\nFinTech Skills ({len(finetech_skills)}):")
    for skill in finetech_skills:
        print(f"  • {skill.name} v{skill.version}")
        print(f"    Rating: ⭐ {skill.rating:.1f} | Downloads: {skill.download_count}")
        print(f"    Description: {skill.description[:60]}...")
    
    # Search by keyword
    print("\nSearching for 'react'...")
    react_skills = search_marketplace(query="react")
    print(f"Found {len(react_skills)} React-related skills:")
    for skill in react_skills:
        print(f"  • {skill.name} ({', '.join(skill.tags[:3])})")
    
    # Install a skill
    print("\nInstalling FinTech Payments skill...")
    success = install_skill("skill_finetech_payments")
    
    if success:
        # Verify installation
        updated_installed = get_installed_skills()
        print(f"\nTotal installed skills: {len(updated_installed)}")
        
        # Load patterns from skill
        patterns = load_skill_patterns("skill_finetech_payments")
        print(f"   Patterns loaded: {len(patterns)}")
    
    # Validate a skill package (mock)
    print("\nValidating skill package...")
    validation = validate_skill(Path("/tmp/mock-skill"))
    print(f"   Valid: {validation['valid']}")
    if validation['errors']:
        print(f"   Errors: {validation['errors']}")
    
    print("\n" + "=" * 60)
    print("Demo complete!")
