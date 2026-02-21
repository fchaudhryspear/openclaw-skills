#!/bin/bash
#
# OpenClaw Disaster Recovery Restore Script
# Restores ALL OpenClaw data from a backup archive
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
log_section() { echo -e "${CYAN}[==== $1 ====]${NC}"; }

# Configuration
BACKUP_FILE="${1:-}"
OPENCLAW_DIR="${HOME}/.openclaw"
WORKSPACE_DIR="${OPENCLAW_DIR}/workspace"
TEMP_DIR=$(mktemp -d)
DRY_RUN=false
FORCE=false

# Show usage
usage() {
    cat <<EOF
OpenClaw Restore Script

Usage: $0 [OPTIONS] <backup-file>

Arguments:
  backup-file    Path to the backup tarball (openclaw-backup-YYYY-MM-DD-HHMMSS.tar.gz)

Options:
  -h, --help     Show this help message
  -d, --dry-run  Show what would be restored without making changes
  -f, --force    Skip confirmation prompts (USE WITH CAUTION)
  -c, --check    Only verify backup integrity, don't restore

Examples:
  $0 /path/to/openclaw-backup-2026-02-20-120000.tar.gz
  $0 --dry-run ~/openclaw-backups/openclaw-backup-2026-02-20-120000.tar.gz
  $0 --check ~/openclaw-backups/openclaw-backup-2026-02-20-120000.tar.gz

EOF
}

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            usage
            exit 0
            ;;
        -d|--dry-run)
            DRY_RUN=true
            shift
            ;;
        -f|--force)
            FORCE=true
            shift
            ;;
        -c|--check)
            CHECK_ONLY=true
            shift
            ;;
        -*)
            log_error "Unknown option: $1"
            usage
            exit 1
            ;;
        *)
            BACKUP_FILE="$1"
            shift
            ;;
    esac
done

# Validate backup file
if [[ -z "$BACKUP_FILE" ]]; then
    log_error "No backup file specified"
    usage
    exit 1
fi

if [[ ! -f "$BACKUP_FILE" ]]; then
    log_error "Backup file not found: $BACKUP_FILE"
    exit 1
fi

# Cleanup function
cleanup() {
    if [[ -d "$TEMP_DIR" ]]; then
        rm -rf "$TEMP_DIR"
    fi
}
trap cleanup EXIT

log_section "OPENCLAW DISASTER RECOVERY RESTORE"
echo ""
log_info "Backup file: $BACKUP_FILE"
log_info "Dry run: $DRY_RUN"
echo ""

# ============================================================================
# PHASE 1: VERIFY BACKUP INTEGRITY
# ============================================================================
log_section "PHASE 1: VERIFYING BACKUP INTEGRITY"

# Check if tarball is valid
log_info "Verifying tarball integrity..."
if ! tar tzf "$BACKUP_FILE" >/dev/null 2>&1; then
    log_error "Backup file is corrupted or invalid"
    exit 1
fi
log_success "Tarball integrity verified"

# Check for checksum file
CHECKSUM_FILE="${BACKUP_FILE}.sha256"
if [[ -f "$CHECKSUM_FILE" ]]; then
    log_info "Verifying checksum..."
    cd "$(dirname "$BACKUP_FILE")"
    if shasum -a 256 -c "$(basename "$CHECKSUM_FILE")" >/dev/null 2>&1; then
        log_success "Checksum verified"
    else
        log_warn "Checksum mismatch - backup may be corrupted"
        if [[ "$FORCE" != true ]]; then
            read -p "Continue anyway? (y/N): " confirm
            [[ "$confirm" =~ ^[Yy]$ ]] || exit 1
        fi
    fi
else
    log_warn "No checksum file found"
fi

# Extract to temp directory
log_info "Extracting backup..."
tar xzf "$BACKUP_FILE" -C "$TEMP_DIR"

# Find the backup directory name
BACKUP_NAME=$(ls -1 "$TEMP_DIR" | head -1)
EXTRACTED_DIR="${TEMP_DIR}/${BACKUP_NAME}"

if [[ ! -d "$EXTRACTED_DIR" ]]; then
    log_error "Invalid backup structure"
    exit 1
fi

# Verify manifest
if [[ -f "${EXTRACTED_DIR}/manifest.json" ]]; then
    log_success "Manifest found"
    MANIFEST_VERSION=$(grep -o '"version": "[^"]*"' "${EXTRACTED_DIR}/manifest.json" | cut -d'"' -f4)
    log_info "Backup version: $MANIFEST_VERSION"
else
    log_warn "No manifest found - backup may be incomplete"
fi

echo ""
log_section "BACKUP CONTENTS"
echo ""

# List what will be restored
[[ -f "${EXTRACTED_DIR}/workspace.tar.gz" ]] && echo "  ✓ Workspace (all user files, SOUL.md, MEMORY.md, etc.)"
[[ -d "${EXTRACTED_DIR}/config" ]] && echo "  ✓ OpenClaw configuration"
[[ -d "${EXTRACTED_DIR}/cron" ]] && echo "  ✓ Cron jobs"
[[ -f "${EXTRACTED_DIR}/agents.tar.gz" ]] && echo "  ✓ Agent configurations"
[[ -d "${EXTRACTED_DIR}/skills" ]] && echo "  ✓ Installed skills"
[[ -d "${EXTRACTED_DIR}/credentials" ]] && echo "  ✓ Credentials (secure)"
[[ -f "${EXTRACTED_DIR}/clawvault.tar.gz" ]] && echo "  ✓ ClawVault data and index"
[[ -d "${EXTRACTED_DIR}/telegram" ]] && echo "  ✓ Telegram configuration"
[[ -d "${EXTRACTED_DIR}/memory" ]] && echo "  ✓ Global memory"
[[ -f "${EXTRACTED_DIR}/system-info.txt" ]] && echo "  ✓ System information"

echo ""

# Check only mode
if [[ "${CHECK_ONLY:-false}" == true ]]; then
    log_success "Backup verification complete - backup is valid"
    exit 0
fi

# Dry run mode
if [[ "$DRY_RUN" == true ]]; then
    log_info "DRY RUN MODE - No changes will be made"
    log_info "To perform actual restore, run without --dry-run flag"
    exit 0
fi

# Confirm restore
if [[ "$FORCE" != true ]]; then
    log_warn "This will OVERWRITE your current OpenClaw installation!"
    echo ""
    read -p "Are you sure you want to continue? (yes/NO): " confirm
    if [[ "$confirm" != "yes" ]]; then
        log_info "Restore cancelled"
        exit 0
    fi
fi

# ============================================================================
# PHASE 2: PRE-RESTORE BACKUP
# ============================================================================
log_section "PHASE 2: CREATING SAFETY BACKUP"

SAFETY_BACKUP="${OPENCLAW_DIR}/.pre-restore-backup-$(date +%Y%m%d-%H%M%S)"
if [[ -d "$OPENCLAW_DIR" ]]; then
    log_info "Creating safety backup of current installation..."
    mkdir -p "$SAFETY_BACKUP"
    
    # Backup critical files
    [[ -f "${OPENCLAW_DIR}/openclaw.json" ]] && cp "${OPENCLAW_DIR}/openclaw.json" "$SAFETY_BACKUP/"
    [[ -d "${OPENCLAW_DIR}/cron" ]] && cp -r "${OPENCLAW_DIR}/cron" "$SAFETY_BACKUP/"
    [[ -d "${OPENCLAW_DIR}/credentials" ]] && cp -r "${OPENCLAW_DIR}/credentials" "$SAFETY_BACKUP/"
    
    log_success "Safety backup created at: $SAFETY_BACKUP"
fi

# ============================================================================
# PHASE 3: RESTORE WORKSPACE
# ============================================================================
log_section "PHASE 3: RESTORING WORKSPACE"

if [[ -f "${EXTRACTED_DIR}/workspace.tar.gz" ]]; then
    log_info "Restoring workspace files..."
    
    # Remove existing workspace (be careful!)
    if [[ -d "$WORKSPACE_DIR" ]]; then
        log_info "Removing existing workspace..."
        rm -rf "$WORKSPACE_DIR"
    fi
    
    # Restore workspace
    mkdir -p "$WORKSPACE_DIR"
    tar xzf "${EXTRACTED_DIR}/workspace.tar.gz" -C "$OPENCLAW_DIR"
    log_success "Workspace restored"
else
    log_warn "No workspace backup found"
fi

# ============================================================================
# PHASE 4: RESTORE CONFIGURATION
# ============================================================================
log_section "PHASE 4: RESTORING OPENCLAW CONFIGURATION"

if [[ -d "${EXTRACTED_DIR}/config" ]]; then
    log_info "Restoring configuration files..."
    
    for file in "${EXTRACTED_DIR}/config"/*; do
        if [[ -f "$file" ]]; then
            filename=$(basename "$file")
            cp "$file" "${OPENCLAW_DIR}/"
            log_info "  Restored: $filename"
        fi
    done
    
    log_success "Configuration restored"
else
    log_warn "No configuration backup found"
fi

# ============================================================================
# PHASE 5: RESTORE CRON JOBS
# ============================================================================
log_section "PHASE 5: RESTORING CRON JOBS"

if [[ -d "${EXTRACTED_DIR}/cron" ]]; then
    log_info "Restoring cron jobs..."
    
    if [[ -d "${OPENCLAW_DIR}/cron" ]]; then
        rm -rf "${OPENCLAW_DIR}/cron"
    fi
    
    cp -r "${EXTRACTED_DIR}/cron" "${OPENCLAW_DIR}/"
    log_success "Cron jobs restored"
    
    # Show what cron jobs were restored
    if [[ -f "${OPENCLAW_DIR}/cron/jobs.json" ]]; then
        log_info "Active cron jobs:"
        grep '"command"' "${OPENCLAW_DIR}/cron/jobs.json" | head -5 | while read line; do
            echo "  $line"
        done
    fi
else
    log_warn "No cron jobs backup found"
fi

# ============================================================================
# PHASE 6: RESTORE AGENTS
# ============================================================================
log_section "PHASE 6: RESTORING AGENTS"

if [[ -f "${EXTRACTED_DIR}/agents.tar.gz" ]]; then
    log_info "Restoring agent configurations..."
    
    if [[ -d "${OPENCLAW_DIR}/agents" ]]; then
        rm -rf "${OPENCLAW_DIR}/agents"
    fi
    
    tar xzf "${EXTRACTED_DIR}/agents.tar.gz" -C "$OPENCLAW_DIR"
    log_success "Agents restored"
else
    log_warn "No agents backup found"
fi

# ============================================================================
# PHASE 7: RESTORE SKILLS
# ============================================================================
log_section "PHASE 7: RESTORING SKILLS"

if [[ -d "${EXTRACTED_DIR}/skills" ]]; then
    log_info "Restoring installed skills..."
    
    if [[ -d "${OPENCLAW_DIR}/skills" ]]; then
        rm -rf "${OPENCLAW_DIR}/skills"
    fi
    
    cp -r "${EXTRACTED_DIR}/skills" "${OPENCLAW_DIR}/"
    log_success "Skills restored"
    
    # List restored skills
    log_info "Restored skills:"
    ls -1 "${OPENCLAW_DIR}/skills" 2>/dev/null | while read skill; do
        echo "  - $skill"
    done
else
    log_warn "No skills backup found"
fi

# ============================================================================
# PHASE 8: RESTORE CREDENTIALS
# ============================================================================
log_section "PHASE 8: RESTORING CREDENTIALS"

if [[ -d "${EXTRACTED_DIR}/credentials" ]]; then
    log_info "Restoring credentials (secure)..."
    
    if [[ -d "${OPENCLAW_DIR}/credentials" ]]; then
        rm -rf "${OPENCLAW_DIR}/credentials"
    fi
    
    cp -r "${EXTRACTED_DIR}/credentials" "${OPENCLAW_DIR}/"
    chmod -R 700 "${OPENCLAW_DIR}/credentials"
    log_success "Credentials restored with secure permissions"
else
    log_warn "No credentials backup found"
fi

# ============================================================================
# PHASE 9: RESTORE CLAWVAULT
# ============================================================================
log_section "PHASE 9: RESTORING CLAWVAULT"

if [[ -f "${EXTRACTED_DIR}/clawvault.tar.gz" ]]; then
    log_info "Restoring ClawVault..."
    
    CLAWVAULT_DIR="${WORKSPACE_DIR}/clawvault"
    if [[ -d "$CLAWVAULT_DIR" ]]; then
        rm -rf "$CLAWVAULT_DIR"
    fi
    
    tar xzf "${EXTRACTED_DIR}/clawvault.tar.gz" -C "$WORKSPACE_DIR"
    log_success "ClawVault restored"
else
    log_warn "No ClawVault backup found"
fi

# ============================================================================
# PHASE 10: RESTORE TELEGRAM
# ============================================================================
log_section "PHASE 10: RESTORING TELEGRAM CONFIGURATION"

if [[ -d "${EXTRACTED_DIR}/telegram" ]]; then
    log_info "Restoring Telegram configuration..."
    
    if [[ -d "${OPENCLAW_DIR}/telegram" ]]; then
        rm -rf "${OPENCLAW_DIR}/telegram"
    fi
    
    cp -r "${EXTRACTED_DIR}/telegram" "${OPENCLAW_DIR}/"
    log_success "Telegram configuration restored"
else
    log_warn "No Telegram configuration backup found"
fi

# ============================================================================
# PHASE 11: RESTORE GLOBAL MEMORY
# ============================================================================
log_section "PHASE 11: RESTORING GLOBAL MEMORY"

if [[ -d "${EXTRACTED_DIR}/memory" ]]; then
    log_info "Restoring global memory..."
    
    if [[ -d "${OPENCLAW_DIR}/memory" ]]; then
        rm -rf "${OPENCLAW_DIR}/memory"
    fi
    
    cp -r "${EXTRACTED_DIR}/memory" "${OPENCLAW_DIR}/"
    log_success "Global memory restored"
else
    log_warn "No global memory backup found"
fi

# ============================================================================
# PHASE 12: REBUILD CLAWVAULT INDEX
# ============================================================================
log_section "PHASE 12: REBUILDING CLAWVAULT INDEX"

CLAWVAULT_DIR="${WORKSPACE_DIR}/clawvault"
if [[ -d "$CLAWVAULT_DIR" ]]; then
    cd "$CLAWVAULT_DIR"
    
    if [[ -f "package.json" ]]; then
        log_info "Installing ClawVault dependencies..."
        npm install --silent 2>/dev/null || log_warn "Some dependencies may need manual installation"
        
        log_info "Building ClawVault..."
        npm run build --silent 2>/dev/null || log_warn "Build may have warnings"
        
        log_success "ClawVault index rebuilt"
    else
        log_warn "ClawVault package.json not found - skipping build"
    fi
else
    log_warn "ClawVault directory not found - skipping rebuild"
fi

# ============================================================================
# PHASE 13: VERIFY INTEGRITY
# ============================================================================
log_section "PHASE 13: VERIFYING RESTORED INTEGRITY"

VERIFICATION_ERRORS=0

# Check critical files
check_file() {
    if [[ -f "$1" ]]; then
        log_success "✓ $2"
    else
        log_error "✗ $2 - MISSING"
        ((VERIFICATION_ERRORS++))
    fi
}

check_dir() {
    if [[ -d "$1" ]]; then
        log_success "✓ $2"
    else
        log_warn "✗ $2 - NOT FOUND"
    fi
}

echo ""
echo "Verifying critical components:"
check_file "${OPENCLAW_DIR}/openclaw.json" "OpenClaw configuration"
check_dir "$WORKSPACE_DIR" "Workspace directory"
check_file "${WORKSPACE_DIR}/SOUL.md" "SOUL.md"
check_file "${WORKSPACE_DIR}/AGENTS.md" "AGENTS.md"
check_file "${WORKSPACE_DIR}/TOOLS.md" "TOOLS.md"
check_dir "${OPENCLAW_DIR}/cron" "Cron jobs directory"
check_dir "${OPENCLAW_DIR}/skills" "Skills directory"
check_dir "${WORKSPACE_DIR}/memory" "Memory directory"

# ============================================================================
# PHASE 14: FINAL SUMMARY
# ============================================================================
log_section "RESTORE COMPLETE"

echo ""
echo "=============================================="
echo "     RESTORATION SUMMARY"
echo "=============================================="
echo "Backup restored from: $BACKUP_FILE"
echo "Restored to: $OPENCLAW_DIR"
echo "Timestamp: $(date)"
echo ""
echo "Components restored:"
[[ -f "${EXTRACTED_DIR}/workspace.tar.gz" ]] && echo "  ✓ Workspace"
[[ -d "${EXTRACTED_DIR}/config" ]] && echo "  ✓ Configuration"
[[ -d "${EXTRACTED_DIR}/cron" ]] && echo "  ✓ Cron jobs"
[[ -f "${EXTRACTED_DIR}/agents.tar.gz" ]] && echo "  ✓ Agents"
[[ -d "${EXTRACTED_DIR}/skills" ]] && echo "  ✓ Skills"
[[ -d "${EXTRACTED_DIR}/credentials" ]] && echo "  ✓ Credentials"
[[ -f "${EXTRACTED_DIR}/clawvault.tar.gz" ]] && echo "  ✓ ClawVault"
[[ -d "${EXTRACTED_DIR}/telegram" ]] && echo "  ✓ Telegram"
[[ -d "${EXTRACTED_DIR}/memory" ]] && echo "  ✓ Global Memory"
echo ""

if [[ $VERIFICATION_ERRORS -eq 0 ]]; then
    log_success "All critical components verified!"
else
    log_warn "Some components may need attention ($VERIFICATION_ERRORS issues)"
fi

echo ""
echo "=============================================="
echo ""
log_info "NEXT STEPS:"
echo "  1. Verify your OpenClaw installation: openclaw doctor"
echo "  2. Test your agents and skills"
echo "  3. Check that cron jobs are running: openclaw cron list"
echo "  4. Review restored files in: $WORKSPACE_DIR"
echo ""
log_info "Safety backup available at: $SAFETY_BACKUP"
echo ""

exit 0
