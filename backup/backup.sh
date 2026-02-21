#!/bin/bash
#
# OpenClaw Disaster Recovery Backup Script
# Backs up ALL OpenClaw data for complete restoration after reinstall
#

set -euo pipefail

# Configuration
BACKUP_DIR="${HOME}/openclaw-backups"
WORKSPACE_DIR="${HOME}/.openclaw/workspace"
OPENCLAW_DIR="${HOME}/.openclaw"
TIMESTAMP=$(date +"%Y-%m-%d-%H%M%S")
BACKUP_NAME="openclaw-backup-${TIMESTAMP}"
BACKUP_FILE="${BACKUP_DIR}/${BACKUP_NAME}.tar.gz"
TEMP_DIR=$(mktemp -d)

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Cleanup function
cleanup() {
    if [[ -d "$TEMP_DIR" ]]; then
        rm -rf "$TEMP_DIR"
    fi
}
trap cleanup EXIT

# Ensure backup directory exists
mkdir -p "$BACKUP_DIR"

log_info "Starting OpenClaw backup at $(date)"
log_info "Backup file: ${BACKUP_FILE}"

# Create backup structure in temp directory
mkdir -p "${TEMP_DIR}/${BACKUP_NAME}"/{workspace,config,cron,agents,skills,credentials,clawvault,telegram,memory}

# ============================================================================
# 1. BACKUP WORKSPACE (All user files, SOUL.md, MEMORY.md, etc.)
# ============================================================================
log_info "Backing up workspace..."
if [[ -d "$WORKSPACE_DIR" ]]; then
    # Use tar to preserve permissions and exclude node_modules
    tar czf "${TEMP_DIR}/${BACKUP_NAME}/workspace.tar.gz" \
        --exclude='node_modules' \
        --exclude='.venv' \
        --exclude='__pycache__' \
        --exclude='*.pyc' \
        --exclude='.pytest_cache' \
        --exclude='.git/objects' \
        -C "$OPENCLAW_DIR" "workspace" 2>/dev/null || true
    WORKSPACE_SIZE=$(du -sh "${TEMP_DIR}/${BACKUP_NAME}/workspace.tar.gz" 2>/dev/null | cut -f1)
    log_success "Workspace backed up (${WORKSPACE_SIZE})"
else
    log_warn "Workspace directory not found"
fi

# ============================================================================
# 2. BACKUP OPENCLAW CONFIGURATION
# ============================================================================
log_info "Backing up OpenClaw configuration..."

# Main config file
if [[ -f "${OPENCLAW_DIR}/openclaw.json" ]]; then
    cp "${OPENCLAW_DIR}/openclaw.json" "${TEMP_DIR}/${BACKUP_NAME}/config/"
    log_success "openclaw.json backed up"
fi

# Backup config files
for f in "${OPENCLAW_DIR}"/*.json "${OPENCLAW_DIR}"/*.bak*; do
    if [[ -f "$f" ]]; then
        cp "$f" "${TEMP_DIR}/${BACKUP_NAME}/config/" 2>/dev/null || true
    fi
done

# Update check
if [[ -f "${OPENCLAW_DIR}/update-check.json" ]]; then
    cp "${OPENCLAW_DIR}/update-check.json" "${TEMP_DIR}/${BACKUP_NAME}/config/"
fi

# ============================================================================
# 3. BACKUP CRON JOBS
# ============================================================================
log_info "Backing up cron jobs..."
if [[ -d "${OPENCLAW_DIR}/cron" ]]; then
    cp -r "${OPENCLAW_DIR}/cron" "${TEMP_DIR}/${BACKUP_NAME}/"
    log_success "Cron jobs backed up"
fi

# Also save current crontab for reference
if command -v crontab &>/dev/null; then
    crontab -l > "${TEMP_DIR}/${BACKUP_NAME}/config/system-crontab.txt" 2>/dev/null || true
fi

# ============================================================================
# 4. BACKUP AGENTS CONFIGURATION
# ============================================================================
log_info "Backing up agents configuration..."
if [[ -d "${OPENCLAW_DIR}/agents" ]]; then
    # Backup agent configs but exclude session logs (too large)
    tar czf "${TEMP_DIR}/${BACKUP_NAME}/agents.tar.gz" \
        --exclude='sessions/*/logs' \
        --exclude='sessions/*/temp' \
        -C "$OPENCLAW_DIR" "agents" 2>/dev/null || true
    AGENTS_SIZE=$(du -sh "${TEMP_DIR}/${BACKUP_NAME}/agents.tar.gz" 2>/dev/null | cut -f1)
    log_success "Agents backed up (${AGENTS_SIZE})"
fi

# ============================================================================
# 5. BACKUP SKILLS
# ============================================================================
log_info "Backing up skills..."
if [[ -d "${OPENCLAW_DIR}/skills" ]]; then
    cp -r "${OPENCLAW_DIR}/skills" "${TEMP_DIR}/${BACKUP_NAME}/"
    log_success "Skills backed up"
fi

# ============================================================================
# 6. BACKUP CREDENTIALS (Sensitive - ensure proper permissions)
# ============================================================================
log_info "Backing up credentials..."
if [[ -d "${OPENCLAW_DIR}/credentials" ]]; then
    cp -r "${OPENCLAW_DIR}/credentials" "${TEMP_DIR}/${BACKUP_NAME}/"
    chmod -R 700 "${TEMP_DIR}/${BACKUP_NAME}/credentials"
    log_success "Credentials backed up (permissions secured)"
fi

# ============================================================================
# 7. BACKUP CLAWVAULT (Data and Index)
# ============================================================================
log_info "Backing up ClawVault..."
CLAWVAULT_WORKSPACE="${WORKSPACE_DIR}/clawvault"
if [[ -d "$CLAWVAULT_WORKSPACE" ]]; then
    # Exclude node_modules from ClawVault
    tar czf "${TEMP_DIR}/${BACKUP_NAME}/clawvault.tar.gz" \
        --exclude='node_modules' \
        --exclude='dist' \
        -C "$WORKSPACE_DIR" "clawvault" 2>/dev/null || true
    CLAWVAULT_SIZE=$(du -sh "${TEMP_DIR}/${BACKUP_NAME}/clawvault.tar.gz" 2>/dev/null | cut -f1)
    log_success "ClawVault backed up (${CLAWVAULT_SIZE})"
fi

# ============================================================================
# 8. BACKUP TELEGRAM CONFIGURATION
# ============================================================================
log_info "Backing up Telegram configuration..."
if [[ -d "${OPENCLAW_DIR}/telegram" ]]; then
    cp -r "${OPENCLAW_DIR}/telegram" "${TEMP_DIR}/${BACKUP_NAME}/"
    log_success "Telegram config backed up"
fi

# ============================================================================
# 9. BACKUP MEMORY DIRECTORY (if not in workspace)
# ============================================================================
log_info "Backing up global memory..."
if [[ -d "${OPENCLAW_DIR}/memory" ]]; then
    cp -r "${OPENCLAW_DIR}/memory" "${TEMP_DIR}/${BACKUP_NAME}/"
    log_success "Global memory backed up"
fi

# ============================================================================
# 10. COLLECT SYSTEM INFO
# ============================================================================
log_info "Collecting system information..."
cat > "${TEMP_DIR}/${BACKUP_NAME}/system-info.txt" <<EOF
OpenClaw Backup Information
===========================
Backup Date: $(date)
Hostname: $(hostname)
User: $(whoami)
OpenClaw Version: $(cat "${OPENCLAW_DIR}/update-check.json" 2>/dev/null | grep -o '"version":"[^"]*"' | cut -d'"' -f4 || echo "unknown")

Directory Sizes:
$(du -sh "$WORKSPACE_DIR" 2>/dev/null || echo "Workspace: not found")
$(du -sh "${OPENCLAW_DIR}/openclaw.json" 2>/dev/null || echo "Config: not found")
$(du -sh "${OPENCLAW_DIR}/cron" 2>/dev/null || echo "Cron: not found")
$(du -sh "${OPENCLAW_DIR}/skills" 2>/dev/null || echo "Skills: not found")

Installed Skills:
$(ls -1 "${OPENCLAW_DIR}/skills" 2>/dev/null || echo "No skills found")

Active Cron Jobs:
$(cat "${OPENCLAW_DIR}/cron/jobs.json" 2>/dev/null | grep '"command"' | head -20 || echo "No cron jobs found")
EOF

# ============================================================================
# 11. CREATE MANIFEST
# ============================================================================
log_info "Creating manifest..."

cat > "${TEMP_DIR}/${BACKUP_NAME}/manifest.json" <<EOF
{
  "version": "1.0",
  "backup_name": "${BACKUP_NAME}",
  "timestamp": "${TIMESTAMP}",
  "created_at": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
  "hostname": "$(hostname)",
  "username": "$(whoami)",
  "backup_type": "full",
  "components": {
    "workspace": {
      "backed_up": $([ -f "${TEMP_DIR}/${BACKUP_NAME}/workspace.tar.gz" ] && echo "true" || echo "false"),
      "path": "workspace.tar.gz"
    },
    "config": {
      "backed_up": $([ -d "${TEMP_DIR}/${BACKUP_NAME}/config" ] && echo "true" || echo "false"),
      "files": [$(ls -1 "${TEMP_DIR}/${BACKUP_NAME}/config" 2>/dev/null | sed 's/^/"/' | sed 's/$/"/' | tr '\n' ',' | sed 's/,$//')]
    },
    "cron": {
      "backed_up": $([ -d "${TEMP_DIR}/${BACKUP_NAME}/cron" ] && echo "true" || echo "false")
    },
    "agents": {
      "backed_up": $([ -f "${TEMP_DIR}/${BACKUP_NAME}/agents.tar.gz" ] && echo "true" || echo "false"),
      "path": "agents.tar.gz"
    },
    "skills": {
      "backed_up": $([ -d "${TEMP_DIR}/${BACKUP_NAME}/skills" ] && echo "true" || echo "false")
    },
    "credentials": {
      "backed_up": $([ -d "${TEMP_DIR}/${BACKUP_NAME}/credentials" ] && echo "true" || echo "false")
    },
    "clawvault": {
      "backed_up": $([ -f "${TEMP_DIR}/${BACKUP_NAME}/clawvault.tar.gz" ] && echo "true" || echo "false"),
      "path": "clawvault.tar.gz"
    },
    "telegram": {
      "backed_up": $([ -d "${TEMP_DIR}/${BACKUP_NAME}/telegram" ] && echo "true" || echo "false")
    },
    "global_memory": {
      "backed_up": $([ -d "${TEMP_DIR}/${BACKUP_NAME}/memory" ] && echo "true" || echo "false")
    }
  },
  "checksums": {},
  "restore_script_version": "1.0"
}
EOF

log_success "Manifest created"

# ============================================================================
# 12. CREATE FINAL TARBALL
# ============================================================================
log_info "Creating final backup archive..."
cd "$TEMP_DIR"
tar czf "$BACKUP_FILE" "$BACKUP_NAME"

if [[ -f "$BACKUP_FILE" ]]; then
    # Secure the backup file
    chmod 600 "$BACKUP_FILE"
    BACKUP_SIZE=$(du -sh "$BACKUP_FILE" | cut -f1)
    log_success "Backup created successfully: ${BACKUP_FILE}"
    log_info "Backup size: ${BACKUP_SIZE}"
else
    log_error "Failed to create backup file"
    exit 1
fi

# Generate checksum
log_info "Generating checksum..."
CHECKSUM=$(shasum -a 256 "$BACKUP_FILE" | cut -d' ' -f1)
echo "$CHECKSUM  $(basename "$BACKUP_FILE")" > "${BACKUP_FILE}.sha256"
log_success "Checksum: ${CHECKSUM:0:16}..."

# ============================================================================
# 13. ROTATION POLICY
# ============================================================================
log_info "Applying backup rotation policy..."

# Keep 7 daily backups
cd "$BACKUP_DIR"
DAILY_COUNT=$(ls -1 openclaw-backup-*.tar.gz 2>/dev/null | wc -l)
if [[ $DAILY_COUNT -gt 7 ]]; then
    # Move older daily backups to weekly
    ls -1t openclaw-backup-*.tar.gz | tail -n +8 | while read old_backup; do
        # Check if it's from Sunday (weekly backup)
        backup_date=$(echo "$old_backup" | grep -o '[0-9]\{4\}-[0-9]\{2\}-[0-9]\{2\}')
        if [[ $(date -j -f "%Y-%m-%d" "$backup_date" +%u 2>/dev/null) == "7" ]]; then
            # Keep Sunday backups (weekly)
            continue
        fi
        # Delete old daily backups beyond 7 days
        rm -f "$old_backup" "${old_backup}.sha256"
        log_info "Removed old daily backup: $old_backup"
    done
fi

# Keep 4 weekly backups (Sundays)
WEEKLY_COUNT=$(ls -1 openclaw-backup-*.tar.gz 2>/dev/null | while read f; do
    backup_date=$(echo "$f" | grep -o '[0-9]\{4\}-[0-9]\{2\}-[0-9]\{2\}')
    if [[ $(date -j -f "%Y-%m-%d" "$backup_date" +%u 2>/dev/null) == "7" ]]; then
        echo "$f"
    fi
done | wc -l)

if [[ $WEEKLY_COUNT -gt 4 ]]; then
    ls -1t openclaw-backup-*.tar.gz | while read f; do
        backup_date=$(echo "$f" | grep -o '[0-9]\{4\}-[0-9]\{2\}-[0-9]\{2\}')
        day_of_week=$(date -j -f "%Y-%m-%d" "$backup_date" +%u 2>/dev/null)
        if [[ "$day_of_week" == "7" ]]; then
            # Check if it's from the 1st of month (monthly)
            day_of_month=$(date -j -f "%Y-%m-%d" "$backup_date" +%d)
            if [[ "$day_of_month" != "01" ]]; then
                rm -f "$f" "${f}.sha256"
                log_info "Removed old weekly backup: $f"
            fi
        fi
    done
fi

# Count remaining backups
REMAINING=$(ls -1 openclaw-backup-*.tar.gz 2>/dev/null | wc -l)
log_success "Rotation complete. ${REMAINING} backups retained."

# ============================================================================
# 14. FINAL SUMMARY
# ============================================================================
echo ""
echo "=============================================="
echo "     BACKUP COMPLETED SUCCESSFULLY"
echo "=============================================="
echo "Backup file: ${BACKUP_FILE}"
echo "Backup size: ${BACKUP_SIZE}"
echo "Checksum: ${CHECKSUM}"
echo "Timestamp: ${TIMESTAMP}"
echo "Backups retained: ${REMAINING}"
echo "=============================================="
echo ""
log_info "To restore, run: ./restore.sh ${BACKUP_FILE}"

exit 0
