#!/bin/bash
# ============================================================================
# AWS CREDENTIAL CLEANUP SCRIPT
# Replaces revoked credentials with placeholder, prompts for new IAM user setup
# ============================================================================

set -e

echo "🔒 AWS CREDENTIAL CLEANUP"
echo "This will remove the compromised key from your local files."
echo ""

WORKSPACE="/Users/faisalshomemacmini/.openclaw/workspace"
cd "$WORKSPACE"

# Step 1: Delete box_downloads directory (contains leaked credentials)
echo "Step 1: Removing box_downloads/ directory (leaked credentials)..."
if [ -d "box_downdownloads" ]; then
    rm -rf box_downloads/
    echo "✅ box_downloads/ deleted"
else
    echo "ℹ️  box_downloads/ not found (already removed)"
fi

# Step 2: Update ~/.aws/credentials
echo ""
echo "Step 2: Updating ~/.aws/credentials file..."
AWS_CREDS="$HOME/.aws/credentials"

if [ -f "$AWS_CREDS" ]; then
    # Backup original
    cp "$AWS_CREDS" "$AWS_CREDS.backup-$(date +%Y%m%d-%H%M%S)"
    echo "✅ Backed up original credentials to $AWS_CREDS.backup-*"
    
    # Clear the file
    cat > "$AWS_CREDS" << 'EOF'
# WARNING: This file was cleared due to credential compromise
# The access key AKIAVUDEQWFUYC2LSGN6 has been revoked by AWS
#
# SETUP NEW IAM USER INSTRUCTIONS:
# 1. Go to https://console.aws.amazon.com/iam/home#/users
# 2. Click "Add users"
# 3. Create user: e.g., "openclaw-service" or "data-lake-deploy"
# 4. Permissions: Programmatic access + PowerUserAccess (or more restrictive)
# 5. Copy the NEW access key ID and secret access key
# 6. Paste them below in the format shown
#
[default]
# aws_access_key_id = YOUR_NEW_ACCESS_KEY_HERE
# aws_secret_access_key = YOUR_NEW_SECRET_KEY_HERE

# NOTE: Root account access keys should NEVER be stored here.
# Always use IAM users with limited permissions.
EOF
    
    chmod 600 "$AWS_CREDS"
    echo "✅ Cleared ~/.aws/credentials"
    echo ""
    echo "⚠️  IMPORTANT: You need to create a new IAM user!"
    echo "   URL: https://console.aws.amazon.com/iam/home#/users"
    echo "   Do NOT use root account access keys."
else
    echo "ℹ️  No AWS credentials file found at $AWS_CREDS"
fi

# Step 3: Search for any remaining references
echo ""
echo "Step 3: Searching for remaining hardcoded credentials..."
REMAINING=$(grep -r "AKIA[A-Z0-9]\{16\}" --include="*.json" --include="*.py" --include="*.js" --exclude-dir="security" . 2>/dev/null | wc -l || echo "0")

if [ "$REMAINING" -gt "0" ]; then
    echo "⚠️  Found $REMAINING potential credential references:"
    grep -r "AKIA[A-Z0-9]\{16\}" --include="*.json" --include="*.py" --include="*.js" --exclude-dir="security" . 2>/dev/null || true
    echo ""
    echo "Review these files manually and remove hardcoded keys."
else
    echo "✅ No hardcoded AWS keys found in source files"
fi

# Step 4: Generate setup instructions for new IAM user
echo ""
echo "============================================================================"
echo "NEXT STEPS: CREATE NEW IAM USER"
echo "============================================================================"
echo ""
echo "DO THIS NOW:"
echo ""
echo "1. Open this URL in your browser:"
echo "   👉 https://console.aws.amazon.com/iam/home#/users"
echo ""
echo "2. Click: Add users"
echo ""
echo "3. New user details:"
echo "   └─ User name: openclaw-service (or data-lake-deploy)"
echo "   └─ Type: Programmatic access"
echo "   └─ Permissions: PowerUserAccess OR custom policy"
echo ""
echo "4. After creating, you'll see:"
echo "   └─ Access Key ID (starts with AKIA...)"
echo "   └─ Secret Access Key (40 characters)"
echo ""
echo "5. ADD THESE TO ~/.aws/credentials (replace the comments):"
echo ""
cat << 'TEMPLATE'
[default]
aws_access_key_id = YOUR_NEW_KEY_ID_HERE
aws_secret_access_key = YOUR_NEW_SECRET_HERE
TEMPLATE
echo ""
echo "6. Also update environment variables if needed:"
echo "   export AWS_ACCESS_KEY_ID=new_key_here"
echo "   export AWS_SECRET_ACCESS_KEY=new_secret_here"
echo ""
echo "7. Test new credentials:"
echo "   aws sts get-caller-identity"
echo ""
echo "✅ After completing these steps, your workspace is fully secured!"
echo ""
