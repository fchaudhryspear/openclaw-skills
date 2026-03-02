#!/bin/bash
# Test runner for Checkpoint System
# Usage: ./run_tests.sh [all|security|manager|integration|demo]

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKSPACE_DIR="$(dirname "$SCRIPT_DIR")"

echo "======================================"
echo "  OpenClaw Checkpoint System Tests"
echo "======================================"
echo ""
echo "Workspace: $WORKSPACE_DIR"
echo ""

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

run_test_file() {
    local test_file=$1
    local test_name=$2
    
    echo -e "${YELLOW}Running $test_name...${NC}"
    echo "--------------------------------------"
    
    if python3 "$test_file"; then
        echo -e "${GREEN}✓ $test_name PASSED${NC}"
    else
        echo -e "${RED}✗ $test_name FAILED${NC}"
        return 1
    fi
    echo ""
}

demo_basic_usage() {
    echo -e "${YELLOW}Demonstrating basic checkpoint usage...${NC}"
    echo "--------------------------------------"
    
    cat > /tmp/demo_checkpoint.py << 'EOF'
import os
import sys
import tempfile
import shutil
from pathlib import Path

# Add workspace to path
sys.path.insert(0, "/Users/faisalshomemacmini/.openclaw/workspace")

from security_utils import SecurityUtils
from checkpoint_system.checkpoint_manager import CheckpointManager
from checkpoint_system.wake_handler import WakeHandler

# Setup
print("🔧 Setting up checkpoint system...")
test_dir = tempfile.mkdtemp()
master_key = os.urandom(32)
security = SecurityUtils(master_key)

checkpoint_dir = os.path.join(test_dir, ".checkpoints")
manager = CheckpointManager("demo_agent", checkpoint_dir, security)

workspace = Path(test_dir) / "workspace"
workspace.mkdir()
(workspace / "test.txt").write_text("Hello from checkpoint demo!")

wake_handler = WakeHandler(manager, str(workspace))

print("✅ System initialized\n")

# Demo 1: Create checkpoint
print("=" * 60)
print("📝 Creating initial checkpoint...")
print("=" * 60)
context = {
    "task_plan": ["Step 1: Initialize", "Step 2: Process", "Step 3: Complete"],
    "current_step": 0,
    "memory": ["Demo agent ready"]
}
cp_path = manager.save_checkpoint(context, workspace_root=str(workspace))
print(f"Checkpoint saved to: {cp_path}\n")

# Demo 2: Modify and create second checkpoint
print("=" * 60)
print("📝 Updating context and creating second checkpoint...")
print("=" * 60)
context["current_step"] = 1
context["memory"].append("Processed first step")
(workspace / "output.txt").write_text("Results from step 1")

cp_path2 = manager.save_checkpoint(context, workspace_root=str(workspace))
print(f"Second checkpoint saved to: {cp_path2}\n")

# Demo 3: List checkpoints
print("=" * 60)
print("📋 Listing available checkpoints...")
print("=" * 60)
checkpoints = manager.list_checkpoints()
for i, cp in enumerate(checkpoints, 1):
    status = "✅ Valid" if cp["valid"] else "❌ Invalid"
    print(f"{i}. {cp['timestamp']} ({cp['size_kb']:.1f} KB) - {status}")
print()

# Demo 4: Simulate crash - delete files
print("=" * 60)
print("💥 Simulating crash - deleting workspace files...")
print("=" * 60)
(workspace / "test.txt").unlink()
(workspace / "output.txt").unlink()
print("Files deleted!\n")

# Demo 5: Recover from checkpoint
print("=" * 60)
print("🔄 Recovering from latest checkpoint...")
print("=" * 60)
loaded_context, loaded_path = wake_handler.wake_agent(dry_run=False)

if loaded_context:
    print(f"✅ Successfully recovered!")
    print(f"   Current step: {loaded_context['current_step']}")
    print(f"   Memory items: {len(loaded_context['memory'])}")
    print(f"   From: {loaded_path}")
else:
    print("❌ Recovery failed!")

print()

# Verify files restored
print("=" * 60)
print("📁 Verifying workspace restoration...")
print("=" * 60)
if (workspace / "test.txt").exists():
    print(f"✅ test.txt restored: '{(workspace / 'test.txt').read_text()}'")
else:
    print("❌ test.txt not restored")

if (workspace / "output.txt").exists():
    print(f"✅ output.txt restored: '{(workspace / 'output.txt').read_text()}'")
else:
    print("❌ output.txt not restored")

print()

# Cleanup
print("🧹 Cleaning up...")
shutil.rmtree(test_dir)
print("✅ Done!")

print("\n" + "=" * 60)
print("🎉 Demo completed successfully!")
print("=" * 60)
EOF

    python3 /tmp/demo_checkpoint.py
    rm /tmp/demo_checkpoint.py
    echo ""
}

case "${1:-all}" in
    security)
        run_test_file "$SCRIPT_DIR/test_security.py" "Security Tests"
        ;;
    
    manager)
        run_test_file "$SCRIPT_DIR/test_checkpoint_manager.py" "Checkpoint Manager Tests"
        ;;
    
    integration)
        run_test_file "$SCRIPT_DIR/test_integration.py" "Integration Tests"
        ;;
    
    demo)
        demo_basic_usage
        ;;
    
    all)
        echo -e "${YELLOW}Running all tests...${NC}"
        echo ""
        
        run_test_file "$SCRIPT_DIR/test_security.py" "Security Tests"
        run_test_file "$SCRIPT_DIR/test_checkpoint_manager.py" "Checkpoint Manager Tests"
        run_test_file "$SCRIPT_DIR/test_integration.py" "Integration Tests"
        
        echo ""
        echo "======================================"
        echo -e "${GREEN}All tests completed!${NC}"
        echo "======================================"
        
        echo ""
        read -p "Run demo? (y/n) " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            demo_basic_usage
        fi
        ;;
    
    *)
        echo "Usage: $0 [all|security|manager|integration|demo]"
        echo ""
        echo "Options:"
        echo "  all          Run all tests (default)"
        echo "  security     Run security/encryption tests only"
        echo "  manager      Run checkpoint manager tests only"
        echo "  integration  Run integration tests only"
        echo "  demo         Run basic usage demonstration"
        exit 1
        ;;
esac
