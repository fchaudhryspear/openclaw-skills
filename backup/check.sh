#!/bin/bash
#
# OpenClaw Backup Pre-flight Check Script
# Verifies backup integrity before restore
#

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Logging functions
log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }
log_section() { echo -e "${CYAN}[$1]${NC}"; }

# Configuration
BACKUP_FILE="${1:-}"
TEMP_DIR=$(mktemp -d)
EXIT_CODE=0

# Show usage
usage() {
    cat <<EOF
OpenClaw Backup Pre-flight Check

Usage: $0 <backup-file>

Arguments:
  backup-file    Path to the backup tarball to verify

This script checks:
  - Tarball integrity and validity
  - Manifest completeness
  - Component availability
  - Disk space requirements
  - What will be restored

Examples:
  $0 ~/openclaw-backups/openclaw-backup-2026-02-20-120000.tar.gz

EOF
}

# Validate arguments
if [[ -z "$BACKUP_FILE" ]]; then
    log_error "No backup file specified"
    usage
    exit 1
fi

if [[ ! -f "$BACKUP_FILE" ]]; then
    log_error "Backup file not found: $BACKUP_FILE"
    exit 1
fi

# Cleanup
cleanup() {
    [[ -d "$TEMP_DIR" ]] && rm -rf "$TEMP_DIR"
}
trap cleanup EXIT

log_section "OPENCLAW BACKUP PRE-FLIGHT CHECK"
echo ""
log_info "Backup file: $BACKUP_FILE"
log_info "Backup size: $(du -sh "$BACKUP_FILE" | cut -f1)"
echo ""

# ============================================================================
# CHECK 1: TARBALL VALIDITY
# ============================================================================
log_section "CHECK 1: TARBALL INTEGRITY"

log_info "Checking tarball structure..."
if ! tar tzf "$BACKUP_FILE" >/dev/null 2>&1; then
    log_error "✗ Tarball is corrupted or invalid"
    exit 1
fi
log_success "✓ Tarball structure is valid"

# List contents
log_info "Archive contents:"
tar tzf "$BACKUP_FILE" | head -20 | while read line; do
    echo "  $line"
done
TOTAL_FILES=$(tar tzf "$BACKUP_FILE" | wc -l)
echo "  ... and $((TOTAL_FILES - 20)) more files"
echo ""

# ============================================================================
# CHECK 2: EXTRACT AND VERIFY MANIFEST
# ============================================================================
log_section "CHECK 2: MANIFEST VERIFICATION"

log_info "Extracting backup..."
tar xzf "$BACKUP_FILE" -C "$TEMP_DIR" 2>/dev/null || true

BACKUP_DIR=$(ls -1 "$TEMP_DIR" 2>/dev/null | head -1)
MANIFEST_PATH="${TEMP_DIR}/${BACKUP_DIR}/manifest.json"

if [[ ! -f "$MANIFEST_PATH" ]]; then
    log_error "✗ Manifest not found in backup"
    EXIT_CODE=1
else
    log_success "✓ Manifest found"
    
    # Parse and display manifest info
    log_info "Backup metadata:"
    echo ""
    
    VERSION=$(grep -o '"version": "[^"]*"' "$MANIFEST_PATH" | cut -d'"' -f4 || echo "unknown")
    TIMESTAMP=$(grep -o '"timestamp": "[^"]*"' "$MANIFEST_PATH" | cut -d'"' -f4 || echo "unknown")
    HOSTNAME=$(grep -o '"hostname": "[^"]*"' "$MANIFEST_PATH" | cut -d'"' -f4 || echo "unknown")
    USERNAME=$(grep -o '"username": "[^"]*"' "$MANIFEST_PATH" | cut -d'"' -f4 || echo "unknown")
    
    echo "  Backup Version: $VERSION"
    echo "  Created: $TIMESTAMP"
    echo "  Source Host: $HOSTNAME"
    echo "  Source User: $USERNAME"
    echo ""
    
    # Check components
    log_info "Components in backup:"
    
    check_component() {
        local key="$1"
        local name="$2"
        if grep -q "\"$key\": {$" "$MANIFEST_PATH" 2>/dev/null; then
            local backed_up=$(grep -A1 "\"$key\": {$" "$MANIFEST_PATH" | grep '"backed_up":' | grep -o 'true\|false' || echo "false")
            if [[ "$backed_up" == "true" ]]; then
                log_success "  ✓ $name"
            else
                log_warn "  ⚠ $name (incomplete)"
            fi
        else
            log_warn "  ✗ $name (not found)"
        fi
    }
    
    check_component "workspace" "Workspace"
    check_component "config" "Configuration"
    check_component "cron" "Cron Jobs"
    check_component "agents" "Agents"
    check_component "skills" "Skills"
    check_component "credentials" "Credentials"
    check_component "clawvault" "ClawVault"
    check_component "telegram" "Telegram"
    check_component "global_memory" "Global Memory"
fi
echo ""

# ============================================================================
# CHECK 3: CHECKSUM VERIFICATION
# ============================================================================
log_section "CHECK 3: CHECKSUM VERIFICATION"

CHECKSUM_FILE="${BACKUP_FILE}.sha256"
if [[ -f "$CHECKSUM_FILE" ]]; then
    log_info "Verifying checksum..."
    cd "$(dirname "$BACKUP_FILE")"
    if shasum -a 256 -c "$(basename "$CHECKSUM_FILE")" >/dev/null 2>&1; then
        log_success "✓ Checksum verified - backup is intact"
        EXPECTED_CHECKSUM=$(cat "$CHECKSUM_FILE" | cut -d' ' -f1)
        echo "  Checksum: ${EXPECTED_CHECKSUM:0:32}..."
    else
        log_error "✗ Checksum mismatch - backup may be corrupted!"
        EXIT_CODE=1
    fi
else
    log_warn "⚠ No checksum file found (${CHECKSUM_FILE})"
    log_warn "  Cannot verify data integrity"
fi
echo ""

# ============================================================================
# CHECK 4: DISK SPACE
# ============================================================================
log_section "CHECK 4: DISK SPACE REQUIREMENTS"

BACKUP_SIZE=$(stat -f%z "$BACKUP_FILE" 2>/dev/null || stat -c%s "$BACKUP_FILE" 2>/dev/null)
# Estimate 3x backup size for extraction + workspace + safety margin
REQUIRED_SPACE=$((BACKUP_SIZE * 3))
REQUIRED_MB=$((REQUIRED_SPACE / 1024 / 1024))

# Get available space on home directory
AVAILABLE_KB=$(df -k "$HOME" | tail -1 | awk '{print $4}')
AVAILABLE_MB=$((AVAILABLE_KB / 1024))

log_info "Space analysis:"
echo "  Backup size: $((BACKUP_SIZE / 1024 / 1024)) MB"
echo "  Estimated required: ${REQUIRED_MB} MB (includes extraction + restore)"
echo "  Available: ${AVAILABLE_MB} MB"

if [[ $AVAILABLE_MB -gt $REQUIRED_MB ]]; then
    log_success "✓ Sufficient disk space available"
else
    log_error "✗ Insufficient disk space!"
    log_error "  Need: ${REQUIRED_MB} MB, Have: ${AVAILABLE_MB} MB"
    EXIT_CODE=1
fi
echo ""

# ============================================================================
# CHECK 5: WHAT WILL BE RESTORED
# ============================================================================
log_section "CHECK 5: RESTORATION IMPACT"

OPENCLAW_DIR="${HOME}/.openclaw"

echo "The following will be RESTORED:"
echo ""

# Extract and list what will be restored
tar xzf "$BACKUP_FILE" -C "$TEMP_DIR" 2>/dev/null || true

if [[ -d "$TEMP_DIR" ]]; then
    BACKUP_CONTENTS=$(ls -1 "$TEMP_DIR" | head -1)
    EXTRACTED_DIR="${TEMP_DIR}/${BACKUP_CONTENTS}"
    
    if [[ -f "${EXTRACTED_DIR}/workspace.tar.gz" ]]; then
        echo "  📁 Workspace directory (all user files, SOUL.md, MEMORY.md, memory/)"
        tar tzf "${EXTRACTED_DIR}/workspace.tar.gz" 2>/dev/null | wc -l | xargs echo "     Files:"
    fi
    
    if [[ -d "${EXTRACTED_DIR}/config" ]]; then
        echo "  ⚙️  OpenClaw configuration (openclaw.json, patches, settings)"
        ls -1 "${EXTRACTED_DIR}/config" | wc -l | xargs echo "     Files:"
    fi
    
    if [[ -d "${EXTRACTED_DIR}/cron" ]]; then
        echo "  ⏰ Cron jobs and scheduled tasks"
        if [[ -f "${EXTRACTED_DIR}/cron/jobs.json" ]]; then
            grep -c '"command"' "${EXTRACTED_DIR}/cron/jobs.json" 2>/dev/null | xargs echo "     Jobs:"
        fi
    fi
    
    if [[ -f "${EXTRACTED_DIR}/agents.tar.gz" ]]; then
        echo "  🤖 Agent configurations and sessions"
    fi
    
    if [[ -d "${EXTRACTED_DIR}/skills" ]]; then
        echo "  🔧 Installed skills"
        ls -1 "${EXTRACTED_DIR}/skills" 2>/dev/null | wc -l | xargs echo "     Skills:"
    fi
    
    if [[ -d "${EXTRACTED_DIR}/credentials" ]]; then
        echo "  🔐 Credentials (API keys, tokens)"
    fi
    
    if [[ -f "${EXTRACTED_DIR}/clawvault.tar.gz" ]]; then
        echo "  📦 ClawVault data and index"
    fi
    
    if [[ -d "${EXTRACTED_DIR}/telegram" ]]; then
        echo "  💬 Telegram configuration"
    fi
    
    if [[ -d "${EXTRACTED_DIR}/memory" ]]; then
        echo "  🧠 Global memory directory"
    fi
fi

echo ""
echo "⚠️  WARNING: This will OVERWRITE your current OpenClaw installation!"
echo ""

# Check current installation
if [[ -d "$OPENCLAW_DIR" ]]; then
    log_warn "Current OpenClaw installation detected at: $OPENCLAW_DIR"
    echo "  The following will be REPLACED:"
    [[ -d "${OPENCLAW_DIR}/workspace" ]] && echo "    - Current workspace"
    [[ -f "${OPENCLAW_DIR}/openclaw.json" ]] && echo "    - Current configuration"
    [[ -d "${OPENCLAW_DIR}/cron" ]] && echo "    - Current cron jobs"
    [[ -d "${OPENCLAW_DIR}/skills" ]] && echo "    - Current skills"
    [[ -d "${OPENCLAW_DIR}/credentials" ]] && echo "    - Current credentials"
else
    log_info "No existing OpenClaw installation detected - fresh restore"
fi

echo ""

# ============================================================================
# CHECK 6: SYSTEM COMPATIBILITY
# ============================================================================
log_section "CHECK 6: SYSTEM COMPATIBILITY"

if [[ -f "$MANIFEST_PATH" ]]; then
    SOURCE_HOST=$(grep -o '"hostname": "[^"]*"' "$MANIFEST_PATH" | cut -d'"' -f4 || echo "unknown")
    CURRENT_HOST=$(hostname)
    
    if [[ "$SOURCE_HOST" != "$CURRENT_HOST" ]]; then
        log_warn "⚠ Backup is from different host: $SOURCE_HOST"
        log_warn "  Current host: $CURRENT_HOST"
        log_warn "  Some paths may need manual adjustment"
    else
        log_success "✓ Same host - full compatibility expected"
    fi
fi

# Check for required tools
log_info "Checking required tools:"

for tool in tar gzip shasum cp rm mv; do
    if command -v "$tool" &>/dev/null; then
        echo "  ✓ $tool"
    else
        log_error "  ✗ $tool - REQUIRED"
        EXIT_CODE=1
    fi
done

echo ""

# ============================================================================
# FINAL SUMMARY
# ============================================================================
log_section "PRE-FLIGHT SUMMARY"

echo ""
if [[ $EXIT_CODE -eq 0 ]]; then
    log_success "✅ BACKUP VERIFIED - READY FOR RESTORE"
    echo ""
    echo "To restore this backup, run:"
    echo "  ./restore.sh \"$BACKUP_FILE\""
    echo ""
    echo "Or with force flag (no confirmation):"
    echo "  ./restore.sh --force \"$BACKUP_FILE\""
else
    log_error "❌ BACKUP CHECK FAILED"
    echo ""
    echo "Please review the errors above before proceeding."
    echo "If you want to restore anyway, use:"
    echo "  ./restore.sh --force \"$BACKUP_FILE\""
fi

echo ""
exit $EXIT_CODE
