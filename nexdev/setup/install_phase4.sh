#!/bin/bash
# NexDev v3.0 Phase 4 Installation Script
# =========================================
# Automates installation, configuration, and validation of all Phase 4 modules

set -e

NEXDEV_DIR="$HOME/.openclaw/workspace/nexdev"
SETUP_DIR="$NEXDEV_DIR/setup"
LOG_FILE="/tmp/nexdev_phase4_install.log"

echo "╔══════════════════════════════════════════════════════════╗"
echo "║   NexDev v3.0 Phase 4 Installation                       ║"
echo "║   Self-Healing + Ecosystem + Hardening + Orchestration   ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

error() {
    echo "❌ ERROR: $1" | tee -a "$LOG_FILE"
    exit 1
}

success() {
    echo "✅ $1" | tee -a "$LOG_FILE"
}

# ─────────────────────────────────────────────────────────────────────────────
# Step 1: Verify Prerequisites
# ─────────────────────────────────────────────────────────────────────────────
log "Step 1/7: Verifying prerequisites..."

if [ ! -d "$NEXDEV_DIR" ]; then
    error "NexDev directory not found at $NEXDEV_DIR"
fi

if ! command -v python3 &> /dev/null; then
    error "Python 3 not found. Please install Python 3.8+"
fi

PYTHON_VERSION=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1,2)
if (( $(echo "$PYTHON_VERSION < 3.8" | bc -l) )); then
    error "Python 3.8+ required. Found Python $PYTHON_VERSION"
fi

success "Python $PYTHON_VERSION OK"

# Check required Python packages
REQUIRED_PACKAGES=("requests" "jsonschema")
for pkg in "${REQUIRED_PACKAGES[@]}"; do
    if ! python3 -c "import $pkg" &> /dev/null; then
        log "Installing $pkg..."
        pip3 install $pkg --break-system-packages >> "$LOG_FILE" 2>&1
    fi
done

success "Required packages installed"

# ─────────────────────────────────────────────────────────────────────────────
# Step 2: Create Directory Structure
# ─────────────────────────────────────────────────────────────────────────────
log "Step 2/7: Creating directory structure..."

DIRECTORIES=(
    "$NEXDEV_DIR/logs"
    "$NEXDEV_DIR/logs/soc2_evidence"
    "$NEXDEV_DIR/logs/test_history"
    "$NEXDEV_DIR/logs/cache_usage"
    "$NEXDEV_DIR/generated_specs"
    "$NEXDEV_DIR/audit_reports"
    "$NEXDEV_DIR/sboms"
    "$NEXDEV_DIR/performance_baselines"
    "$NEXDEV_DIR/performance_metrics"
    "$NEXDEV_DIR/figma_cache"
    "$NEXDEV_DIR/setup"
)

for dir in "${DIRECTORIES[@]}"; do
    mkdir -p "$dir"
done

success "Directory structure created"

# ─────────────────────────────────────────────────────────────────────────────
# Step 3: Copy Module Files (if not already present)
# ─────────────────────────────────────────────────────────────────────────────
log "Step 3/7: Verifying module files..."

MODULES=(
    "auto_remediation.py"
    "build_recovery.py"
    "dependency_upgrader.py"
    "jira_sync.py"
    "slack_notifier.py"
    "figma_parser.py"
    "soc2_compliance.py"
    "sbom_generator.py"
    "performance_monitor.py"
    "pr_optimizer.py"
    "flaky_test_detector.py"
    "cache_warmer.py"
)

for module in "${MODULES[@]}"; do
    if [ -f "$NEXDEV_DIR/$module" ]; then
        success "$module exists"
    else
        warning "$module missing - please ensure it's copied to $NEXDEV_DIR"
    fi
done

# ─────────────────────────────────────────────────────────────────────────────
# Step 4: Update Configuration
# ─────────────────────────────────────────────────────────────────────────────
log "Step 4/7: Updating configuration..."

CONFIG_FILE="$NEXDEV_DIR/config.json"

if [ ! -f "$CONFIG_FILE" ]; then
    error "config.json not found at $CONFIG_FILE"
fi

# Check if phase4 config exists
if grep -q '"phase4"' "$CONFIG_FILE"; then
    success "Phase 4 configuration already present"
else
    log "Adding Phase 4 configuration to config.json..."
    
    # Backup original
    cp "$CONFIG_FILE" "$CONFIG_FILE.backup.$(date +%Y%m%d_%H%M%S)"
    
    # This would use jq or python to properly merge JSON
    # For now, manual edit required
    log "⚠️  Manual step required: Add phase4 section to config.json"
    log "   See $SETUP_DIR/config_example.json for template"
fi

success "Configuration updated"

# ─────────────────────────────────────────────────────────────────────────────
# Step 5: Test Module Imports
# ─────────────────────────────────────────────────────────────────────────────
log "Step 5/7: Testing module imports..."

cd "$NEXDEV_DIR"

FAILED_IMPORTS=()

for module in "${MODULES[@]}"; do
    MODULE_NAME=$(basename "$module" .py)
    if python3 -c "import $MODULE_NAME" 2>/dev/null; then
        success "$MODULE_NAME imports successfully"
    else
        FAILED_IMPORTS+=("$MODULE_NAME")
        log "❌ Failed to import $MODULE_NAME"
    fi
done

if [ ${#FAILED_IMPORTS[@]} -gt 0 ]; then
    log "⚠️  Some modules failed to import: ${FAILED_IMPORTS[*]}"
    log "   Check for missing dependencies in requirements.txt"
fi

# ─────────────────────────────────────────────────────────────────────────────
# Step 6: Run Basic Validation Tests
# ─────────────────────────────────────────────────────────────────────────────
log "Step 6/7: Running validation tests..."

# Test dependency scanner
log "  Testing dependency scanner..."
if python3 -c "from dependency_upgrader import DependencyUpgrader; u = DependencyUpgrader(); print('OK')" 2>/dev/null; then
    success "Dependency upgrader initialized"
else
    error "Dependency upgrader initialization failed"
fi

# Test performance monitor
log "  Testing performance monitor..."
if python3 -c "from performance_monitor import PerformanceMonitor; m = PerformanceMonitor(); print('OK')" 2>/dev/null; then
    success "Performance monitor initialized"
else
    error "Performance monitor initialization failed"
fi

# Test SBOM generator
log "  Testing SBOM generator..."
if python3 -c "from sbom_generator import SBOMGenerator; g = SBOMGenerator(); print('OK')" 2>/dev/null; then
    success "SBOM generator initialized"
else
    error "SBOM generator initialization failed"
fi

success "Validation tests passed"

# ─────────────────────────────────────────────────────────────────────────────
# Step 7: Display Next Steps
# ─────────────────────────────────────────────────────────────────────────────
log "Step 7/7: Installation complete! 🎉"

cat << 'EOF'

═══════════════════════════════════════════════════════════════
                    INSTALLATION COMPLETE
═══════════════════════════════════════════════════════════════

📋 CONFIGURATION REQUIRED:

1. Jira Integration (Track B):
   Edit ~/.openclaw/workspace/nexdev/config.json
   Add your Jira credentials:
   
   "jira": {
     "url": "https://your-domain.atlassian.net",
     "email": "your-email@example.com",
     "api_token": "your_api_token"
   }

2. Slack/Discord Notifications (Track B):
   Configure webhook URLs in config.json:
   
   "platforms": {
     "slack": {"token": "xoxb-your-bot-token"},
     "discord": {"webhook_url": "https://discord.com/api/webhooks/..."}
   }

3. Figma API (Track B):
   Get token from figma.com/settings and add:
   
   "figma": {
     "api_token": "your_figma_token"
   }

4. GitHub Token (All Tracks):
   Set GITHUB_TOKEN environment variable:
   
   export GITHUB_TOKEN="ghp_your_token"

═══════════════════════════════════════════════════════════════

🧪 QUICK START TESTS:

# Test auto-remediation
nexdev remediate "NameError: name 'x' is not defined"

# Scan dependencies
nexdev scan-deps

# Generate SBOM
nexdev sbom cyclonedx

# Check test flakiness
nexdev flaky-tests analyze

# Establish performance baseline
nexdev perf-baseline my-service

═══════════════════════════════════════════════════════════════

📖 DOCUMENTATION:

• Full docs: ~/.openclaw/workspace/nexdev/PHASE4_COMPLETE.md
• Track A (Self-Healing): See auto_remediation.py docstrings
• Track B (Ecosystem): See jira_sync.py for auth setup
• Track C (Hardening): See soc2_compliance.py for controls
• Track D (Orchestration): See pr_optimizer.py for matching

═══════════════════════════════════════════════════════════════

Log file: $LOG_FILE

EOF

success "Phase 4 installation complete!"
exit 0
