#!/bin/bash
# OpenClaw Healthcheck Remediation Script - Home/Workstation Balanced
# Generated: 2026-02-17
# Run at your own risk—review each section. Most steps are manual or require admin privileges.
# Rollbacks are noted. Backup first!

echo "Starting remediation..."

# 1. Confirm/Enable Disk Encryption (FileVault) - Manual
echo "Open System Settings > Privacy & Security > FileVault and enable if off."
echo "Rollback: Disable in the same menu (requires admin password)."

# 2. Enable Backups (Time Machine)
tmutil destinationinfo  # Check current destinations
# If none, add one: tmutil setdestination /Volumes/YourBackupDrive  # Replace with your drive
tmutil startbackup
echo "Rollback: tmutil stopbackup or tmutil removedestination"

# 3. Enable OS Automatic Updates - Manual
echo "Open System Settings > General > Software Update > Automatic Updates and enable all options."
echo "Rollback: Disable in the same menu."

# 4. Install Missing Diagnostic Tools (via Homebrew)
# Install Homebrew if missing
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
brew install lsof coreutils
echo "Rollback: brew uninstall lsof coreutils; /bin/bash -c \"$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/uninstall.sh)\""

# 5. Update OpenClaw
openclaw update  # Or: pnpm update openclaw
echo "Rollback: pnpm install openclaw@2026.2.15"

# 6. Resolve OpenClaw State Dir Migration - Manual merge if needed
# Example: mv ~/.openclaw/old ~/.openclaw/backup && openclaw restart
echo "Manually check and merge ~/.openclaw if conflicts exist."
echo "Rollback: Restore from backup."

# 7. Address Trusted Proxies Warning
# Use OpenClaw config tool or edit config file manually
# Example: Set in config: gateway.trustedProxies = [\"192.168.1.0/24\"]
# Then: openclaw restart
echo "Edit config to add trusted proxies, then restart OpenClaw."
echo "Rollback: Remove setting and restart."

# 8. Test and Migrate Failing Services - Examples
# Model test: Use session_status or sub-agent spawn
# For migrations: Review old scripts in clawd old/ and test
echo "For migrations, e.g., node /path/to/old-office365-script.js"
echo "No automated rollback—test in isolation."

# 9. Re-Run Audits
openclaw security audit --deep
lsof -nP -iTCP -sTCP:LISTEN  # Now should work
/usr/libexec/ApplicationFirewall/socketfilterfw --getglobalstate
pfctl -s info  # If pfctl available via coreutils

echo "Remediation complete. Review outputs and verify access."