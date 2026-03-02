#!/bin/bash
# ============================================================================
# CRITICAL: Remove AWS credentials from git history
# Run this IMMEDIATELY after making .gitignore changes
# ============================================================================

set -e

echo "🚨 EMERGENCY CREDENTIAL PURGE SCRIPT"
echo "This will remove sensitive files from ALL git history."
echo ""

REPO_PATH="/Users/faisalshomemacmini/.openclaw/workspace"
cd $REPO_PATH

echo "Step 1: Installing BFG Repo Cleaner..."
if ! command -v bfg &> /dev/null; then
    echo "Installing BFG via Homebrew..."
    brew install bfg
fi

echo ""
echo "Step 2: Removing box_downloads/ (contains Box API keys)..."
bfg --delete-files "file_*.json" --no-blob-protection

echo ""
echo "Step 3: Removing any remaining secrets..."
# Remove common secret patterns
bfg --replace-text <<< 'AKIA[A-Z0-9]{16} ==> [REDACTED_AWS_KEY]
sk-[a-zA-Z0-9]{48} ==> [REDACTED_API_KEY]' --no-blob-protection

echo ""
echo "Step 4: Cleaning Git repository..."
git reflog expire --expire=now --all
git gc --prune=now --aggressive

echo ""
echo "Step 5: Verifying removal..."
echo "Searching for AKIA pattern in history..."
if git log -p --all | grep -q "AKIA"; then
    echo "⚠️  WARNING: AWS keys still found in history!"
    echo "Re-running aggressive cleanup..."
    bfg --delete-files "*.json" --no-blob-protection
    git reflog expire --expire=now --all
    git gc --prune=now --aggressive
else
    echo "✅ AWS keys successfully removed from history"
fi

echo ""
echo "Step 6: Force pushing cleaned history..."
echo "⚠️  THIS WILL OVERWRITE REMOTE REPOSITORY!"
read -p "Continue? (type YES to confirm): " confirm
if [ "$confirm" = "YES" ]; then
    git push origin main --force
    echo ""
    echo "✅ Repository cleaned and pushed!"
    echo ""
    echo "IMPORTANT NEXT STEPS:"
    echo "1. Delete all forks of this repository"
    echo "2. Notify anyone who may have cloned it"
    echo "3. Monitor AWS CloudTrail for suspicious activity"
else
    echo "❌ Aborted. Manual force-push required."
fi

echo ""
echo "============================================================================"
echo "CLEANUP COMPLETE"
echo "============================================================================"
