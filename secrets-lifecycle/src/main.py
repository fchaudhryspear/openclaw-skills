#!/usr/bin/env python3
"""
Secrets Lifecycle Manager - Main CLI Interface
Track API key expirations, credential rotation schedules, audit logging.
Generates alerts before keys expire (30/7/1 day warnings).
"""

import os
import sys
import argparse
import json
from datetime import datetime, timedelta
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from secret_manager import SecretManager
from expiration_tracker import ExpirationTracker, AlertSeverity
from compliance_audit import ComplianceAuditLogger
from report_generator import ReportGenerator


# Default paths
DEFAULT_DATA_DIR = os.path.join(
    os.path.expanduser('~'), '.secrets-lifecycle', 'data'
)
DEFAULT_REPORTS_DIR = os.path.join(
    os.path.expanduser('~'), '.secrets-lifecycle', 'reports'
)


def get_master_password() -> str:
    """Get master password from environment or prompt."""
    pw = os.environ.get('SECRETS_MASTER_PASSWORD')
    if pw:
        return pw
    
    import getpass
    return getpass.getpass("Enter master password for secrets vault: ")


def init_vault(args):
    """Initialize a new secrets vault."""
    data_dir = args.data_dir or DEFAULT_DATA_DIR
    os.makedirs(data_dir, mode=0o700, exist_ok=True)
    
    # Get or generate master password
    if hasattr(args, 'password') and args.password:
        password = args.password
    else:
        password = get_master_password()
    
    # Create manager (this initializes the vault)
    sm = SecretManager(data_dir, password)
    
    print(f"✅ Vault initialized at: {data_dir}")
    print(f"   Secrets file: {sm.secrets_file}")
    print(f"   Audit file: {sm.audit_file}")
    print("\n⚠️  IMPORTANT: Remember your master password. It cannot be recovered!")
    
    return sm


def add_secret(args, sm: SecretManager):
    """Add a new secret to the vault."""
    # Parse expiration date if provided
    expiration = None
    if args.expiration:
        try:
            expiration = datetime.fromisoformat(args.expiration)
        except ValueError:
            # Try common formats
            for fmt in ['%Y-%m-%d', '%Y/%m/%d', '%m/%d/%Y']:
                try:
                    expiration = datetime.strptime(args.expiration, fmt)
                    break
                except ValueError:
                    continue
    
    secret_id = sm.add_secret(
        name=args.name,
        value=args.value,
        service=args.service,
        expiration_date=expiration,
        rotation_days=args.rotation_days,
        notes=args.notes or '',
        tags=args.tags.split(',') if args.tags else []
    )
    
    print(f"✅ Secret added successfully!")
    print(f"   ID: {secret_id}")
    print(f"   Name: {args.name}")
    print(f"   Service: {args.service}")
    if expiration:
        print(f"   Expires: {expiration.strftime('%Y-%m-%d')}")
    if args.rotation_days:
        print(f"   Rotation schedule: Every {args.rotation_days} days")


def list_secrets(args, sm: SecretManager):
    """List all secrets (metadata only, no values)."""
    secrets = sm.list_secrets(include_deleted=args.include_deleted)
    
    if not secrets:
        print("No secrets found.")
        return
    
    print(f"\n{'ID':<18} {'Name':<25} {'Service':<20} {'Expires':<15} {'Status'}")
    print("-" * 90)
    
    for s in secrets:
        exp_date = s.get('expiration_date', 'N/A')[:10] if s.get('expiration_date') else 'N/A'
        status = s.get('status', 'active')
        
        # Add indicator based on expiration
        indicator = ""
        if s.get('expiration_date'):
            exp = datetime.fromisoformat(s['expiration_date'])
            days = (exp - datetime.now()).days
            if days < 0:
                indicator = "🚨 "
            elif days <= 7:
                indicator = "🔴 "
            elif days <= 30:
                indicator = "🟠 "
        
        print(f"{indicator}{s['id']:<18} {s['name']:<25} {s['service']:<20} {exp_date:<15} {status}")
    
    print(f"\nTotal: {len(secrets)} secrets")


def get_secret(args, sm: SecretManager):
    """Retrieve a secret by ID."""
    secret = sm.get_secret(args.secret_id)
    
    if not secret:
        print(f"❌ Secret not found: {args.secret_id}")
        return
    
    print(f"\nSecret Details:")
    print(f"  ID: {secret['id']}")
    print(f"  Name: {secret['name']}")
    print(f"  Service: {secret['service']}")
    print(f"  Value: {secret['value'][:8]}..." if len(secret['value']) > 8 else f"  Value: {secret['value']}")
    
    if secret.get('expiration_date'):
        exp = datetime.fromisoformat(secret['expiration_date'])
        days = (exp - datetime.now()).days
        print(f"  Expires: {secret['expiration_date'][:10]} ({days} days)")
    
    if secret.get('rotation_days'):
        print(f"  Rotation: Every {secret['rotation_days']} days")
    
    if secret.get('notes'):
        print(f"  Notes: {secret['notes']}")
    
    if secret.get('tags'):
        print(f"  Tags: {', '.join(secret['tags'])}")


def rotate_secret(args, sm: SecretManager):
    """Rotate a secret with a new value."""
    if not args.new_value:
        # Generate random value
        import secrets as sec
        new_value = sec.token_urlsafe(32)
        print(f"Generated new value (URL-safe base64, 32 bytes)")
    else:
        new_value = args.new_value
    
    if sm.rotate_secret(args.secret_id, new_value):
        print(f"✅ Secret rotated successfully!")
        print(f"   New value: {new_value[:8]}... (full value shown above)")
    else:
        print(f"❌ Failed to rotate secret: {args.secret_id}")


def check_expirations(args, sm: SecretManager, tracker: ExpirationTracker):
    """Check for expiring secrets and generate alerts."""
    alerts = tracker.check_expirations(force_check=args.force)
    status = tracker.get_current_status()
    
    # Generate report
    rg = ReportGenerator(args.reports_dir or DEFAULT_REPORTS_DIR)
    report = rg.generate_expiration_tracker_report(status, [a.to_dict() for a in alerts])
    
    print(report)
    
    # Save report
    filepath = rg.save_report(report, 'expiration_tracker', 'general')
    print(f"\n📄 Report saved to: {filepath}")
    
    # Return count of critical alerts
    critical_count = sum(1 for a in alerts if a.severity in [AlertSeverity.CRITICAL, AlertSeverity.URGENT])
    return critical_count


def generate_calendar(args, sm: SecretManager):
    """Generate rotation calendar."""
    secrets = sm.list_secrets(include_deleted=False)
    rg = ReportGenerator(args.reports_dir or DEFAULT_REPORTS_DIR)
    
    calendar = rg.generate_rotation_calendar(secrets, view=args.view, months_ahead=args.months)
    
    # Print to console
    print(calendar)
    
    # Save report
    filepath = rg.save_report(calendar, 'rotation_calendar', 'calendar')
    print(f"\n📄 Calendar saved to: {filepath}")


def generate_audit_report(args, audit_logger: ComplianceAuditLogger):
    """Generate compliance audit report."""
    since = datetime.now() - timedelta(days=args.days)
    
    events = audit_logger.get_events(since=since)
    report_data = audit_logger.generate_compliance_report(
        start_date=since,
        end_date=datetime.now(),
        include_summary=True,
        include_details=True
    )
    
    anomalies = audit_logger.detect_anomalies(lookback_days=args.days)
    
    rg = ReportGenerator(args.reports_dir or DEFAULT_REPORTS_DIR)
    report = rg.generate_compliance_audit_log(
        events=[e.to_dict() for e in events][:100],
        summary=report_data.get('summary', {}),
        anomalies=anomalies,
        period_days=args.days
    )
    
    print(report)
    
    filepath = rg.save_report(report, 'compliance_audit', 'audit')
    print(f"\n📄 Audit report saved to: {filepath}")


def show_status(args, sm: SecretManager, tracker: ExpirationTracker):
    """Show current vault status."""
    status = tracker.get_current_status()
    
    rg = ReportGenerator(args.reports_dir or DEFAULT_REPORTS_DIR)
    report = rg.generate_expiration_tracker_report(status, [])
    
    print(report)


def export_audit(args, audit_logger: ComplianceAuditLogger):
    """Export audit log for external review."""
    output_path = args.output or f"/tmp/audit_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    
    audit_logger.export_for_audit(output_path, days=args.days)
    print(f"✅ Audit log exported to: {output_path}")


def main():
    parser = argparse.ArgumentParser(
        description='Secrets Lifecycle Manager - Track API key expirations and rotations',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s init                              Initialize new vault
  %(prog)s add --name api_key --value xxx --service stripe --expiration 2026-06-01
  %(prog)s list                              List all secrets
  %(prog)s check                             Check expirations and generate alerts
  %(prog)s calendar                          Show rotation calendar
  %(prog)s audit --days 90                   Generate compliance report
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # Init command
    init_parser = subparsers.add_parser('init', help='Initialize new vault')
    init_parser.add_argument('--data-dir', help='Data directory path')
    init_parser.add_argument('--password', help='Master password (use env var for security)')
    
    # Add command
    add_parser = subparsers.add_parser('add', help='Add a new secret')
    add_parser.add_argument('--name', required=True, help='Secret name')
    add_parser.add_argument('--value', required=True, help='Secret value')
    add_parser.add_argument('--service', required=True, help='Service/provider name')
    add_parser.add_argument('--expiration', help='Expiration date (ISO format)')
    add_parser.add_argument('--rotation-days', type=int, help='Rotation interval in days')
    add_parser.add_argument('--notes', help='Optional notes')
    add_parser.add_argument('--tags', help='Comma-separated tags')
    
    # List command
    list_parser = subparsers.add_parser('list', help='List all secrets')
    list_parser.add_argument('--include-deleted', action='store_true', help='Include deleted secrets')
    
    # Get command
    get_parser = subparsers.add_parser('get', help='Get a secret by ID')
    get_parser.add_argument('secret_id', help='Secret ID')
    
    # Rotate command
    rotate_parser = subparsers.add_parser('rotate', help='Rotate a secret')
    rotate_parser.add_argument('secret_id', help='Secret ID')
    rotate_parser.add_argument('--new-value', help='New secret value (generate if not provided)')
    
    # Check command
    check_parser = subparsers.add_parser('check', help='Check expirations and generate alerts')
    check_parser.add_argument('--force', action='store_true', help='Force check regardless of last alert time')
    
    # Status command
    status_parser = subparsers.add_parser('status', help='Show current vault status')
    
    # Calendar command
    cal_parser = subparsers.add_parser('calendar', help='Show rotation calendar')
    cal_parser.add_argument('--view', choices=['table', 'calendar'], default='table', help='View type')
    cal_parser.add_argument('--months', type=int, default=3, help='Months to display ahead')
    
    # Audit command
    audit_parser = subparsers.add_parser('audit', help='Generate compliance audit report')
    audit_parser.add_argument('--days', type=int, default=90, help='Days to look back')
    
    # Export command
    export_parser = subparsers.add_parser('export', help='Export audit log')
    export_parser.add_argument('--days', type=int, default=365, help='Days to export')
    export_parser.add_argument('--output', help='Output file path')
    
    # Common arguments
    for p in [check_parser, status_parser, cal_parser, audit_parser, export_parser]:
        p.add_argument('--data-dir', help='Data directory path')
        p.add_argument('--reports-dir', help='Reports directory path')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    # Data directories
    data_dir = getattr(args, 'data_dir', None) or DEFAULT_DATA_DIR
    reports_dir = getattr(args, 'reports_dir', None) or DEFAULT_REPORTS_DIR
    
    # Handle init separately (doesn't need existing vault)
    if args.command == 'init':
        init_vault(args)
        return
    
    # Load or initialize components
    try:
        password = get_master_password()
        sm = SecretManager(data_dir, password)
    except Exception as e:
        print(f"❌ Error loading vault: {e}")
        print("   Run 'secrets-lifecycle init' to create a new vault")
        sys.exit(1)
    
    tracker = ExpirationTracker(sm, os.path.join(data_dir, 'alerts.json'))
    audit_logger = ComplianceAuditLogger(os.path.join(data_dir, 'audit.log'))
    
    # Execute command
    if args.command == 'add':
        add_secret(args, sm)
    elif args.command == 'list':
        list_secrets(args, sm)
    elif args.command == 'get':
        get_secret(args, sm)
    elif args.command == 'rotate':
        rotate_secret(args, sm)
    elif args.command == 'check':
        exit_code = check_expirations(args, sm, tracker)
        sys.exit(exit_code if exit_code > 0 else 0)
    elif args.command == 'status':
        show_status(args, sm, tracker)
    elif args.command == 'calendar':
        generate_calendar(args, sm)
    elif args.command == 'audit':
        generate_audit_report(args, audit_logger)
    elif args.command == 'export':
        export_audit(args, audit_logger)


if __name__ == '__main__':
    main()
