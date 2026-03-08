#!/usr/bin/env python3
"""
NexDev Multi-Tenant Support (Phase 4 Feature)

Isolated instances per organization/project with data separation,
custom branding, and role-based access control.
Part of NexDev v3.0 World-Class Build Team Upgrade
"""

import json
import hashlib
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict
from datetime import datetime
import sqlite3
import secrets


TENANT_DB_PATH = Path.home() / ".openclaw/workspace/nexdev/tenant_management.db"
API_KEYS_DIR = Path.home() / ".openclaw/workspace/nexdev/api_keys"


@dataclass
class Tenant:
    """Represents an organization/project tenant."""
    id: str
    name: str
    display_name: str
    domain: Optional[str]  # For email-based auth
    logo_url: Optional[str]
    primary_color: str  # Hex color for branding
    features_enabled: List[str]  # ["advanced_analytics", "skill_marketplace"]
    plan_type: str  # "free", "pro", "enterprise"
    max_users: int
    max_projects: int
    created_at: str
    status: str  # "active", "suspended", "deleted"
    settings: Dict[str, Any]


@dataclass
class User:
    """Represents a user in a tenant."""
    id: str
    tenant_id: str
    email: str
    name: str
    role: str  # "admin", "developer", "viewer"
    api_key_hash: Optional[str]
    created_at: str
    last_login: Optional[str]
    status: str  # "active", "inactive"


def init_multi_tenant_db():
    """Initialize multi-tenant database schema."""
    conn = sqlite3.connect(TENANT_DB_PATH)
    cursor = conn.cursor()
    
    # Tenants table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tenants (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            display_name TEXT,
            domain TEXT,
            logo_url TEXT,
            primary_color TEXT DEFAULT '#007bff',
            features_enabled TEXT,
            plan_type TEXT DEFAULT 'free',
            max_users INTEGER DEFAULT 5,
            max_projects INTEGER DEFAULT 10,
            created_at TEXT,
            status TEXT DEFAULT 'active'
        )
    ''')
    
    # Users table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            tenant_id TEXT NOT NULL,
            email TEXT NOT NULL,
            name TEXT,
            role TEXT DEFAULT 'developer',
            api_key_hash TEXT,
            created_at TEXT,
            last_login TEXT,
            status TEXT DEFAULT 'active',
            FOREIGN KEY (tenant_id) REFERENCES tenants(id),
            UNIQUE(tenant_id, email)
        )
    ''')
    
    # API keys index
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_user_tenant ON users(tenant_id)
    ''')
    
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_email ON users(email)')
    
    # Usage tracking
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS usage_tracking (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tenant_id TEXT,
            user_id TEXT,
            endpoint TEXT,
            tokens_used INTEGER,
            cost_usd REAL,
            timestamp TEXT
        )
    ''')
    
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_usage_tenant ON usage_tracking(tenant_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_usage_time ON usage_tracking(timestamp DESC)')
    
    # Audit logs
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS audit_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tenant_id TEXT,
            user_id TEXT,
            action TEXT,
            resource_type TEXT,
            resource_id TEXT,
            details TEXT,
            ip_address TEXT,
            timestamp TEXT
        )
    ''')
    
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_audit_tenant ON audit_logs(tenant_id)')
    
    conn.commit()
    conn.close()
    
    # Ensure API keys directory exists
    API_KEYS_DIR.mkdir(parents=True, exist_ok=True)


def create_tenant(tenant_data: Dict[str, Any]) -> Tenant:
    """Create a new tenant."""
    tenant_id = f"tenant_{secrets.token_hex(8)}"
    
    now = datetime.now().isoformat()
    
    tenant = Tenant(
        id=tenant_id,
        name=tenant_data.get('name', ''),
        display_name=tenant_data.get('display_name', ''),
        domain=tenant_data.get('domain'),
        logo_url=tenant_data.get('logo_url'),
        primary_color=tenant_data.get('primary_color', '#007bff'),
        features_enabled=tenant_data.get('features_enabled', []),
        plan_type=tenant_data.get('plan_type', 'free'),
        max_users=tenant_data.get('max_users', 5),
        max_projects=tenant_data.get('max_projects', 10),
        created_at=now,
        status='active',
        settings=tenant_data.get('settings', {})
    )
    
    conn = sqlite3.connect(TENANT_DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO tenants 
        (id, name, display_name, domain, logo_url, primary_color, features_enabled,
         plan_type, max_users, max_projects, created_at, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        tenant.id, tenant.name, tenant.display_name, tenant.domain,
        tenant.logo_url, tenant.primary_color, json.dumps(tenant.features_enabled),
        tenant.plan_type, tenant.max_users, tenant.max_projects,
        tenant.created_at, tenant.status
    ))
    
    conn.commit()
    conn.close()
    
    return tenant


def get_tenant(tenant_id: str) -> Optional[Dict[str, Any]]:
    """Retrieve tenant by ID."""
    conn = sqlite3.connect(TENANT_DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM tenants WHERE id=?', (tenant_id,))
    row = cursor.fetchone()
    conn.close()
    
    if not row:
        return None
    
    columns = [desc[0] for desc in cursor.description]
    tenant_dict = dict(zip(columns, row))
    
    # Parse JSON fields
    try:
        tenant_dict['features_enabled'] = json.loads(tenant_dict['features_enabled'])
    except (json.JSONDecodeError, TypeError):
        tenant_dict['features_enabled'] = []
    
    return tenant_dict


def authenticate_api_key(api_key: str) -> Optional[Dict[str, Any]]:
    """Authenticate using API key and return user info."""
    hash_input = hashlib.sha256(api_key.encode()).hexdigest()
    
    conn = sqlite3.connect(TENANT_DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT u.*, t.id as tenant_id, t.name as tenant_name
        FROM users u
        JOIN tenants t ON u.tenant_id = t.id
        WHERE u.api_key_hash = ? AND u.status = 'active'
        AND t.status = 'active'
    ''', (hash_input,))
    
    row = cursor.fetchone()
    conn.close()
    
    if not row:
        return None
    
    columns = [desc[0] for desc in cursor.description]
    result = dict(zip(columns, row))
    
    return {
        'user': {k: v for k, v in result.items() if not k.startswith('tenant_')},
        'tenant': {
            'id': result['tenant_id'],
            'name': result['tenant_name']
        }
    }


def generate_api_key(user_id: str) -> str:
    """Generate API key for a user."""
    api_key = f"ndx_{secrets.token_urlsafe(32)}"
    api_key_hash = hashlib.sha256(api_key.encode()).hexdigest()
    
    conn = sqlite3.connect(TENANT_DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        UPDATE users SET api_key_hash = ? WHERE id = ?
    ''', (api_key_hash, user_id))
    
    conn.commit()
    conn.close()
    
    # Store full key in file system (encrypted would be better in production)
    key_file = API_KEYS_DIR / f"{user_id}.key"
    key_file.write_text(api_key)
    
    return api_key


def log_usage(tenant_id: str, user_id: str, endpoint: str, 
              tokens_used: int, cost_usd: float):
    """Track API usage for billing/quotas."""
    conn = sqlite3.connect(TENANT_DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO usage_tracking 
        (tenant_id, user_id, endpoint, tokens_used, cost_usd, timestamp)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (tenant_id, user_id, endpoint, tokens_used, cost_usd, 
          datetime.now().isoformat()))
    
    conn.commit()
    conn.close()


def log_audit_action(tenant_id: str, user_id: str, action: str,
                    resource_type: str, resource_id: str, 
                    details: Optional[str] = None, ip_address: str = ""):
    """Log audit event for compliance."""
    conn = sqlite3.connect(TENANT_DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO audit_logs 
        (tenant_id, user_id, action, resource_type, resource_id, details, ip_address, timestamp)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (tenant_id, user_id, action, resource_type, resource_id,
          json.dumps(details) if details else None, ip_address, 
          datetime.now().isoformat()))
    
    conn.commit()
    conn.close()


def get_tenant_usage(tenant_id: str, days: int = 30) -> Dict[str, Any]:
    """Get usage statistics for a tenant."""
    conn = sqlite3.connect(TENANT_DB_PATH)
    cursor = conn.cursor()
    
    from datetime import timedelta
    cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()
    
    cursor.execute('''
        SELECT SUM(tokens_used), SUM(cost_usd), COUNT(*)
        FROM usage_tracking
        WHERE tenant_id = ? AND timestamp >= ?
    ''', (tenant_id, cutoff_date))
    
    row = cursor.fetchone()
    conn.close()
    
    return {
        'tenant_id': tenant_id,
        'period_days': days,
        'total_tokens': row[0] or 0,
        'total_cost_usd': row[1] or 0,
        'total_requests': row[2] or 0
    }


def check_quota(tenant_id: str, feature: str) -> Dict[str, bool]:
    """Check if tenant is within quota limits."""
    tenant = get_tenant(tenant_id)
    if not tenant:
        return {'allowed': False, 'reason': 'Tenant not found'}
    
    # Check user limit
    conn = sqlite3.connect(TENANT_DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('SELECT COUNT(*) FROM users WHERE tenant_id = ?', (tenant_id,))
    user_count = cursor.fetchone()[0]
    
    conn.close()
    
    checks = {
        'max_users': user_count < tenant['max_users'],
        'max_projects': True,  # Would need project tracking
        'plan_allowed': feature != 'premium' or tenant['plan_type'] in ['pro', 'enterprise']
    }
    
    return {
        'allowed': all(checks.values()),
        'limits': {
            'users': {'current': user_count, 'max': tenant['max_users']},
            'projects': {'limit': tenant['max_projects']}
        },
        'failed_checks': [k for k, v in checks.items() if not v]
    }


if __name__ == "__main__":
    # Demo mode
    print("=" * 60)
    print("🏢 NEXDEV MULTI-TENANT - DEMO")
    print("=" * 60)
    
    init_multi_tenant_db()
    
    # Create sample tenant
    print("\nCreating sample tenant...")
    tenant = create_tenant({
        'name': 'Acme Corporation',
        'display_name': 'Acme Corp',
        'primary_color': '#FF5733',
        'plan_type': 'pro',
        'max_users': 20,
        'max_projects': 50
    })
    
    print(f"✅ Created tenant: {tenant.id}")
    print(f"   Name: {tenant.name}")
    print(f"   Plan: {tenant.plan_type}")
    print(f"   Max users: {tenant.max_users}")
    
    # Generate API key
    print("\nGenerating API key...")
    api_key = generate_api_key("user_demo")
    print(f"🔑 API Key: {api_key[:20]}...")
    
    # Test authentication
    print("\nTesting authentication...")
    auth_result = authenticate_api_key(api_key)
    if auth_result:
        print(f"✅ Authenticated: {auth_result['user']['email']}")
        print(f"   Tenant: {auth_result['tenant']['name']}")
    else:
        print("❌ Authentication failed")
    
    # Log some usage
    print("\nLogging usage...")
    log_usage(tenant.id, "user_demo", "/nexdev/run", 1000, 0.05)
    log_usage(tenant.id, "user_demo", "/nexdev/tests", 500, 0.02)
    
    # Get usage report
    usage = get_tenant_usage(tenant.id)
    print(f"📊 Usage Report:")
    print(f"   Total Tokens: {usage['total_tokens']}")
    print(f"   Total Cost: ${usage['total_cost_usd']:.4f}")
    print(f"   Requests: {usage['total_requests']}")
    
    # Check quota
    print("\nChecking quotas...")
    quota = check_quota(tenant.id, 'advanced_analytics')
    print(f"   Allowed: {quota['allowed']}")
    print(f"   User limit: {quota['limits']['users']['current']}/{quota['limits']['users']['max']}")
    
    print("\n" + "=" * 60)
    print("Demo complete!")
