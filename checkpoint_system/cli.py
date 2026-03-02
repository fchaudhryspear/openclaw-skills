#!/usr/bin/env python3
"""
Checkpoint CLI - Command-line interface for checkpoint operations

Usage:
    python cli.py checkpoint [options]      # Create checkpoint
    python cli.py wake [options]            # Wake from checkpoint
    python cli.py list                      # List checkpoints
    python cli.py restore <checkpoint-id>   # Restore specific checkpoint
    python cli.py cleanup [options]         # Clean old checkpoints
    python cli.py info <checkpoint-id>      # Show checkpoint details
"""

import argparse
import sys
import os
import json
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from checkpoint_manager import CheckpointManager
from wake_handler import WakeHandler
from security_utils import SecurityUtils


def load_security_config():
    """Load security configuration from environment or config file."""
    # Try to load from environment first
    master_key_env = os.environ.get("CHECKPOINT_MASTER_KEY")
    
    if master_key_env:
        # Load from base64 encoded env variable
        import base64
        try:
            return base64.b64decode(master_key_env)
        except Exception as e:
            print(f"Warning: Could not decode CHECKPOINT_MASTER_KEY: {e}")
    
    # Fallback to generating a new key (for testing only)
    print("⚠️  No master key found. Generating temporary key (not recommended for production)")
    return os.urandom(32)


def init_checkpoint_manager():
    """Initialize the checkpoint manager with proper configuration."""
    agent_id = os.environ.get("AGENT_ID", "default_agent")
    workspace_root = os.environ.get("WORKSPACE_ROOT", 
                                    "/Users/faisalshomemacmini/.openclaw/workspace")
    checkpoint_base_dir = os.environ.get("CHECKPOINT_DIR", 
                                         str(Path(workspace_root) / ".checkpoints"))
    
    master_key = load_security_config()
    security = SecurityUtils(master_key)
    manager = CheckpointManager(agent_id, checkpoint_base_dir, security)
    wake_handler = WakeHandler(manager, workspace_root)
    
    return manager, wake_handler


def cmd_checkpoint(args):
    """Handle checkpoint creation command."""
    manager, _ = init_checkpoint_manager()
    
    print("\n📝 Creating checkpoint...")
    
    # In a real scenario, this would capture the current agent state
    # For CLI usage, we can accept context from stdin or file
    
    if args.context_file:
        # Load context from file
        with open(args.context_file, 'r') as f:
            context = json.load(f)
        print(f"✅ Loaded context from: {args.context_file}")
    elif not sys.stdin.isatty():
        # Read context from stdin
        try:
            context = json.loads(sys.stdin.read())
            print("✅ Loaded context from stdin")
        except json.JSONDecodeError as e:
            print(f"❌ Invalid JSON in stdin: {e}")
            return 1
    else:
        # Interactive mode - create empty checkpoint
        print("ℹ️  No context provided. Creating empty checkpoint.")
        print("💡 Tip: Pipe JSON context via stdin or use --context-file")
        context = {"manual_checkpoint": True, "timestamp": str(datetime.now())}
    
    # Save checkpoint
    checkpoint_path = manager.save_checkpoint(context)
    
    print(f"\n{'='*60}")
    print("✅ CHECKPOINT CREATED SUCCESSFULLY")
    print(f"{'='*60}")
    print(f"Location: {checkpoint_path}")
    print(f"Agent ID: {manager.agent_id}")
    
    # Cleanup old checkpoints if requested
    if args.cleanup_old:
        manager.cleanup_old_checkpoint(args.keep_count)
        print(f"Cleaned up old checkpoints (kept {args.keep_count})")
    
    return 0


def cmd_wake(args):
    """Handle wake command."""
    _, wake_handler = init_checkpoint_manager()
    
    print("\n🔄 Attempting to wake agent...")
    
    target_cp = args.checkpoint if args.checkpoint else None
    
    # Perform wake
    context, cp_path = wake_handler.wake_agent(
        target_checkpoint=target_cp,
        restore_workspace=not args.no_workspace,
        dry_run=args.dry_run
    )
    
    if not context:
        print("❌ Failed to wake agent. No valid checkpoint found.")
        return 1
    
    if args.dry_run:
        print("\n⚠️  DRY RUN - Context loaded but not restored")
    
    if args.output:
        # Output restored context to file
        with open(args.output, 'w') as f:
            json.dump(context, f, indent=2)
        print(f"\n✅ Restored context saved to: {args.output}")
    
    return 0


def cmd_list(args):
    """List available checkpoints."""
    manager, wake_handler = init_checkpoint_manager()
    
    checkpoints = wake_handler.get_available_checkpoints()
    
    if not checkpoints:
        print("ℹ️  No checkpoints found.")
        return 0
    
    print(f"\n📋 Available Checkpoints for Agent: {manager.agent_id}")
    print("-" * 70)
    print(f"{'Timestamp':<25} {'Size':<10} {'Status':<12}")
    print("-" * 70)
    
    for cp in checkpoints:
        status = "✅ Valid" if cp.get('valid', False) else "❌ Corrupted"
        size_str = f"{cp['size_kb']:.1f} KB"
        print(f"{cp['timestamp']:<25} {size_str:<10} {status:<12}")
    
    print("-" * 70)
    print(f"Total: {len(checkpoints)} checkpoints")
    
    return 0


def cmd_restore(args):
    """Restore a specific checkpoint."""
    _, wake_handler = init_checkpoint_manager()
    
    print(f"\n🔄 Restoring checkpoint: {args.checkpoint_id}")
    
    # First get list to find the full path
    checkpoints = wake_handler.get_available_checkpoints()
    target_cp = None
    
    for cp in checkpoints:
        if args.checkpoint_id in cp['path']:
            target_cp = cp['path']
            break
    
    if not target_cp:
        print(f"❌ Checkpoint '{args.checkpoint_id}' not found.")
        return 1
    
    context, cp_path = wake_handler.wake_agent(
        target_checkpoint=target_cp,
        restore_workspace=True,
        dry_run=False
    )
    
    if context:
        print(f"\n✅ Successfully restored from: {cp_path}")
        return 0
    else:
        print("\n❌ Failed to restore checkpoint.")
        return 1


def cmd_cleanup(args):
    """Clean up old checkpoints."""
    manager, _ = init_checkpoint_manager()
    
    print(f"\n🧹 Cleaning up old checkpoints (keeping {args.keep})...")
    manager.cleanup_old_checkpoints(keep_count=args.keep)
    
    print("✅ Cleanup complete.")
    return 0


def cmd_info(args):
    """Show detailed information about a checkpoint."""
    _, wake_handler = init_checkpoint_manager()
    
    checkpoints = wake_handler.get_available_checkpoints()
    
    for cp in checkpoints:
        if args.checkpoint_id in cp['path']:
            print(f"\n📊 Checkpoint Information")
            print("=" * 60)
            print(f"Path:          {cp['path']}")
            print(f"Timestamp:     {cp['timestamp']}")
            print(f"Size:          {cp['size_kb']:.2f} KB")
            print(f"Valid:         {'Yes' if cp.get('valid') else 'No'}")
            
            if 'metadata' in cp:
                print(f"\nMetadata:")
                for key, value in cp['metadata'].items():
                    print(f"  {key}: {value}")
            
            if 'summary' in cp:
                print(f"\nContent Summary:")
                for key, value in cp['summary'].items():
                    print(f"  {key}: {value}")
            
            print("=" * 60)
            return 0
    
    print(f"❌ Checkpoint '{args.checkpoint_id}' not found.")
    return 1


def main():
    parser = argparse.ArgumentParser(
        description="OpenClaw Auto-Checkpoint & Wake System CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s checkpoint --context-file context.json     # Create checkpoint from file
  %(prog)s checkpoint < context.json                  # Create checkpoint from stdin
  %(prog)s checkpoint --cleanup-old --keep 3          # Create and clean old ones
  
  %(prog)s wake                                       # Wake from latest checkpoint
  %(prog)s wake --dry-run                             # Preview restoration
  %(prog)s wake --output restored.json                # Save restored context
  
  %(prog)s list                                       # List all checkpoints
  %(prog)s info abc123                                # Show checkpoint details
  %(prog)s restore abc123                             # Restore specific checkpoint
  
  %(prog)s cleanup --keep 5                           # Remove old checkpoints
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Checkpoint command
    checkpoint_parser = subparsers.add_parser('checkpoint', help='Create a checkpoint')
    checkpoint_parser.add_argument('--context-file', '-f', help='JSON file containing agent context')
    checkpoint_parser.add_argument('--cleanup-old', action='store_true', 
                                   help='Cleanup old checkpoints after saving')
    checkpoint_parser.add_argument('--keep-count', '-k', type=int, default=5,
                                   help='Number of checkpoints to keep (default: 5)')
    
    # Wake command
    wake_parser = subparsers.add_parser('wake', help='Wake agent from checkpoint')
    wake_parser.add_argument('--checkpoint', '-c', help='Specific checkpoint to restore')
    wake_parser.add_argument('--no-workspace', action='store_true',
                            help='Skip workspace restoration')
    wake_parser.add_argument('--dry-run', '-n', action='store_true',
                            help='Preview restoration without applying')
    wake_parser.add_argument('--output', '-o', help='Output file for restored context')
    
    # List command
    subparsers.add_parser('list', help='List available checkpoints')
    
    # Restore command
    restore_parser = subparsers.add_parser('restore', help='Restore specific checkpoint')
    restore_parser.add_argument('checkpoint_id', help='Checkpoint identifier (partial match)')
    
    # Cleanup command
    cleanup_parser = subparsers.add_parser('cleanup', help='Clean up old checkpoints')
    cleanup_parser.add_argument('--keep', '-k', type=int, default=5,
                               help='Number of checkpoints to keep (default: 5)')
    
    # Info command
    info_parser = subparsers.add_parser('info', help='Show checkpoint details')
    info_parser.add_argument('checkpoint_id', help='Checkpoint identifier (partial match)')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    # Dispatch to appropriate command handler
    commands = {
        'checkpoint': cmd_checkpoint,
        'wake': cmd_wake,
        'list': cmd_list,
        'restore': cmd_restore,
        'cleanup': cmd_cleanup,
        'info': cmd_info
    }
    
    return commands[args.command](args)


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
