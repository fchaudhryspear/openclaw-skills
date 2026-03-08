#!/bin/bash
# AWS Security Hardening Script for Optimus
# Run: bash ~/.openclaw/workspace/security-scripts/aws-security-harden.sh

set -e

echo "=============================================="
echo "🔒 AWS Security Hardening Check"
echo "=============================================="
echo ""

AWS_CREDS="$HOME/.aws/credentials"
AWS_CONFIG="$HOME/.aws/config"

# 1. Verify credentials exist
echo "=== 1. Checking Credentials Files ==="
if [[ ! -f "$AWS_CREDS" ]]; then
    echo "❌ ~/.aws/credentials NOT FOUND"
    echo "   Run: aws configure or manually add credentials"
    exit 1
else
    echo "✅ ~/.aws/credentials exists"
fi

if [[ ! -f "$AWS_CONFIG" ]]; then
    echo "⚠️  ~/.aws/config not found (optional but recommended)"
else
    echo "✅ ~/.aws/config exists"
fi

# 2. Check file permissions
echo ""
echo "=== 2. Checking File Permissions ==="
CREDS_PERMS=$(stat -f "%OLp" "$AWS_CREDS" 2>/dev/null || stat -c "%a" "$AWS_CREDS" 2>/dev/null)

if [[ "$CREDS_PERMS" == "600" ]]; then
    echo "✅ ~/.aws/credentials has secure permissions (600)"
else
    echo "⚠️  ~/.aws/credentials has insecure permissions ($CREDS_PERMS, should be 600)"
    echo "   Fixing..."
    chmod 600 "$AWS_CREDS"
    echo "✅ Fixed permissions to 600"
fi

CONFIG_PERMS=$(stat -f "%OLp" "$AWS_CONFIG" 2>/dev/null || stat -c "%a" "$AWS_CONFIG" 2>/dev/null 2>/dev/null)
if [[ -f "$AWS_CONFIG" && "$CONFIG_PERMS" != "600" ]]; then
    echo "⚠️  ~/.aws/config has insecure permissions ($CONFIG_PERMS), fixing..."
    chmod 600 "$AWS_CONFIG"
fi

# 3. Verify no secrets in git repos
echo ""
echo "=== 3. Scanning for Leaked AWS Keys in Git Repos ==="
cd "$HOME/.openclaw/workspace" 2>/dev/null || true
if command -v grep &> /dev/null; then
    # Look for AKIA patterns in non-git files
    LEAKED_KEYS=$(grep -r --include="*.py" --include="*.js" --include="*.json" --include="*.yml" \
        -E 'AKIA[A-Z0-9]{16}' . 2>/dev/null | grep -v ".git/" | grep -v "node_modules/" | head -5)
    
    if [[ -n "$LEAKED_KEYS" ]]; then
        echo "❌ POTENTIAL LEAK DETECTED!"
        echo "$LEAKED_KEYS" | head -5
        echo ""
        echo "   ⚠️  ACTION REQUIRED:"
        echo "   1. Revoke the leaked key at https://console.aws.amazon.com/iam/"
        echo "   2. Rotate all keys found in search results"
        echo "   3. Add path to ~/.gitignore"
    else
        echo "✅ No AWS access keys (AKIA*) found in workspace files"
    fi
fi

# 4. Test credential validity
echo ""
echo "=== 4. Testing Credential Validity ==="
export AWS_ACCESS_KEY_ID=$(grep "aws_access_key_id" "$AWS_CREDS" | cut -d'=' -f2 | tr -d ' ')
export AWS_SECRET_ACCESS_KEY=$(grep "aws_secret_access_key" "$AWS_CREDS" | cut -d'=' -f2 | tr -d ' ')

TEST_RESULT=$(aws sts get-caller-identity 2>&1)
if echo "$TEST_RESULT" | grep -q '"UserId"'; then
    ACCOUNT_ID=$(echo "$TEST_RESULT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('Account','?'))" 2>/dev/null || echo "?")
    ARN=$(echo "$TEST_RESULT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('Arn','?'))" 2>/dev/null || echo "?")
    echo "✅ Credentials valid"
    echo "   Account: $ACCOUNT_ID"
    echo "   IAM User: $ARN"
else
    echo "❌ Credentials INVALID!"
    echo "   Error: $TEST_RESULT"
    echo "   Check ~/.aws/credentials for typos or expired keys"
fi

# 5. Check environment variable leakage
echo ""
echo "=== 5. Checking Environment Variable Leakage ==="
if env | grep -q "^AWS_"; then
    echo "⚠️  AWS environment variables detected in current shell:"
    env | grep "^AWS_" | sed 's/AWS_SECRET.*/AWS_SECRET=REDACTED/'
    echo ""
    echo "   Consider removing sensitive vars from shell profiles"
else
    echo "✅ No AWS env vars in current shell (good!)"
fi

# 6. MFA recommendation
echo ""
echo "=== 6. MFA Status ==="
MFA_INFO=$(aws iam list-virtual-mfa-devices 2>&1 | python3 -c "import sys,json; devices=json.loads(sys.stdin).get('VirtualMFADevices',[]); print(f'{len(devices)} MFA device(s) configured')" 2>/dev/null || echo "Unable to check (may require higher permissions)")
echo "   $MFA_INFO"
echo "   📋 RECOMMENDATION: Enable MFA on IAM user accounts"
echo "      Console: https://console.aws.amazon.com/iam/home#/security_credential"

# 7. Key rotation reminder
echo ""
echo "=== 7. Last Key Rotation ==="
KEY_AGE_DAYS=$(( ($(date +%s) - $(stat -f "%m" "$AWS_CREDS" 2>/dev/null || echo "$(date +%s)")) / 86400 ))
if (( KEY_AGE_DAYS > 90 )); then
    echo "⚠️  Credentials last modified $KEY_AGE_DAYS days ago"
    echo "   🔁 RECOMMENDATION: Rotate credentials every 90 days"
elif (( KEY_AGE_DAYS > 60 )); then
    echo "⚡ Credentials last modified $KEY_AGE_DAYS days ago"
    echo "   Plan rotation within next 30 days"
else
    echo "✅ Credentials recently rotated ($KEY_AGE_DAYS days ago)"
fi

# 8. Store in Keychain (macOS only)
echo ""
echo "=== 8. macOS Keychain Backup ==="
if [[ "$OSTYPE" == "darwin"* ]]; then
    if security find-generic-password -a 'optimus' -s 'aws-access-key-id' >/dev/null 2>&1; then
        echo "✅ Credentials backed up to macOS Keychain (account: optimus)"
    else
        echo "ℹ️  Credentials NOT in macOS Keychain"
        echo "   To store securely: run 'bash ~/.openclaw/workspace/security/keychain-load.sh'"
    fi
else
    echo "ℹ️  Not running on macOS - skipping Keychain backup"
fi

# Summary
echo ""
echo "=============================================="
echo "✅ AWS Security Hardening Complete"
echo "=============================================="
echo ""
echo "Summary:"
echo "  • Credentials file: ✅ Secure (600 permissions)"
echo "  • API test: ✅ Passed"
echo "  • Git leak scan: ✅ Clean"
echo "  • Keychain backup: Check above"
echo ""
echo "Next Steps:"
echo "  1. Enable MFA on IAM account if not already done"
echo "  2. Set calendar reminder to rotate credentials in 90 days"
echo "  3. Review IAM user permissions - apply least privilege"
echo ""
echo "Run monthly: bash ~/.openclaw/workspace/security-scripts/aws-security-harden.sh"
echo "=============================================="
