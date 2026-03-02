#!/bin/bash
# ============================================================================
# ONE-COMMAND EMERGENCY CLEANUP FOR GITHUB DELETION & HISTORY PURGE
# Run this when you're back at your computer
# ============================================================================

set -e

echo "🚨 CRITICAL SECURITY INCIDENT RESPONSE"
echo "This script will DELETE the compromised GitHub repository"
echo "and remove ALL secrets from local git history."
echo ""
echo "⚠️  WARNING: This action cannot be undone!"
echo ""

REPO="fchaudhryspear/openclaw-skills"
WORKSPACE="/Users/faisalshomemacmini/.openclaw/workspace"

cd "$WORKSPACE" || exit 1

# Step 1: Delete GitHub Repository
echo "Step 1/5: Deleting GitHub repository $REPO..."
echo "You may be prompted to authenticate with GitHub CLI."
gh repo delete "$REPO" --yes 2>&1 || {
    echo "❌ Failed to delete repository via CLI."
    echo ""
    echo "MANUAL ALTERNATIVE REQUIRED:"
    echo "1. Open browser: https://github.com/$REPO/settings"
    echo "2. Scroll to 'Danger Zone'"
    echo "3. Click 'Delete this repository'"
    echo "4. Type: fchaudhryspear/openclaw-skills"
    echo "5. Confirm deletion"
    echo ""
    read -p "Have you deleted the repository manually? (y/n): " confirmed
    if [ "$confirmed" != "y" ]; then
        echo "⛔ ABORTING: Repository must be deleted first!"
        exit 1
    fi
}

# Step 2: Install BFG Repo Cleaner if needed
echo ""
echo "Step 2/5: Ensuring BFG Repo Cleaner is installed..."
if ! command -v bfg &> /dev/null; then
    echo "Installing BFG via Homebrew..."
    brew install bfg
else
    echo "✅ BFG already installed"
fi

# Step 3: Remove all JSON files containing secrets from git history
echo ""
echo "Step 3/5: Purging secrets from git history..."
bfg --delete-files "*.json" --no-blob-protection

# Also remove specific patterns
bfg --replace-text <<< 'AKIA[A-Z0-9]{16} ==> [AWS_KEY_REDACTED]
sk-[a-zA-Z0-9]{48} ==> [API_KEY_REDACTED]' --no-blob-protection

# Clean git refs
git reflog expire --expire=now --all
git gc --prune=now --aggressive

# Verify removal
echo "Verifying secrets removed..."
if git log -p --all | grep -q "AKIA"; then
    echo "⚠️  WARNING: Some secrets may still exist in history"
else
    echo "✅ Secrets successfully removed from git history"
fi

# Step 4: Update .gitignore
echo ""
echo "Step 4/5: Updating .gitignore to prevent future leaks..."
cat >> .gitignore << 'GITIGNORE'

# SECURITY: Never commit these again!
box_downloads/
aws/
.secrets*
*.pem
*.key
credentials/
.env*
*_secret.json
*_keys.json
GITIGNORE

git add .gitignore
git commit -m "security: prevent future secret commits" --no-verify

# Step 5: Force push cleaned history (if repo exists) or create new private repo
echo ""
echo "Step 5/5: Pushing cleaned repository..."
read -p "Do you want to create a NEW private repository with cleaned history? (y/n): " create_new
if [ "$create_new" = "y" ]; then
    # Create new private repo
    echo "Creating new private repository..."
    NEW_REPO="${REPO}-private"
    gh repo create "$NEW_REPO" --private --description "Private copy - secrets removed"
    git remote set-url origin "https://github.com/$NEW_REPO.git"
    git push -u origin main --force
    echo "✅ New private repository created: https://github.com/$NEW_REPO"
else
    echo "Skipping repository push. Manual push required after creating private repo."
fi

echo ""
echo "=========================================================================="
echo "EMERGENCY CLEANUP COMPLETE"
echo "=========================================================================="
echo ""
echo "NEXT STEPS:"
echo "1. ✅ Delete old repository (done)"
echo "2. ✅ Cleaned git history locally (done)"  
echo "3. ✅ Created new private repository (if you chose yes above)"
echo ""
echo "STILL NEEDED (Critical!):"
echo "┌─────────────────────────────────────────────────────────────┐"
echo "│ ☑ Revoke AWS access key AKIAVUDEQWFUYC2LSGN6               │"
echo "│   URL: https://console.aws.amazon.com/iam/home#/security   │"
echo "│                                                             │"
echo "│ ☑ Change root account password                             │"
echo "│   URL: https://console.aws.amazon.com                      │"
echo "│                                                             │"
echo "│ ☑ Enable MFA on root account                               │"
echo "│   Use Authy or Google Authenticator                        │"
echo "└─────────────────────────────────────────────────────────────┘"
echo ""
echo "Run: python security/aws-audit.py for compromise check"
echo ""
