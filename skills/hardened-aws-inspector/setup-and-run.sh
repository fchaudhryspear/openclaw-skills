#!/bin/bash
# Hardened AWS Inspector - Quick Setup Script
# Automatically configures credentials and runs all audit scripts

set -e

echo "🔐 HARDENED AWS INSPECTOR SETUP"
echo "================================"
echo ""

WORKSPACE="/Users/faisalshomemacmini/.openclaw/workspace"
cd "$WORKSPACE"

# Step 1: Configure credentials from Keychain or prompt
echo "Step 1: Setting up AWS credentials..."

if security find-generic-password -s "AWS_ACCESS_KEY_ID" -a "data-lake-deploy" -w 2>/dev/null; then
    echo "✅ Credentials found in macOS Keychain"
    
    export AWS_ACCESS_KEY_ID=$(security find-generic-password -s "AWS_ACCESS_KEY_ID" -a "data-lake-deploy" -w 2>/dev/null)
    export AWS_SECRET_ACCESS_KEY=$(security find-generic-password -s "AWS_SECRET_ACCESS_KEY" -a "data-lake-deploy" -w 2>/dev/null)
else
    # Fallback to ~/.aws/credentials file
    if [ -f "$HOME/.aws/credentials" ]; then
        echo "✅ Credentials found in ~/.aws/credentials"
        export AWS_ACCESS_KEY_ID=$(grep 'aws_access_key_id' ~/.aws/credentials | cut -d'=' -f2 | tr -d ' ')
        export AWS_SECRET_ACCESS_KEY=$(grep 'aws_secret_access_key' ~/.aws/credentials | cut -d'=' -f2 | tr -d ' ')
    else
        echo "❌ No credentials found!"
        echo ""
        echo "Please configure one of the following:"
        echo "  Option 1: Add to macOS Keychain"
        echo "  Option 2: Create ~/.aws/credentials file"
        exit 1
    fi
fi

echo ""
echo "Step 2: Testing AWS connection..."

if aws sts get-caller-identity > /dev/null 2>&1; then
    echo "✅ AWS credentials working!"
    USER_ARN=$(aws sts get-caller-identity --query 'Arn' --output text)
    echo "   User ARN: $USER_ARN"
else
    echo "❌ AWS credentials failed!"
    echo "   Check ~/.aws/credentials or Keychain settings"
    exit 1
fi

echo ""
echo "Step 3: Running security audits..."
echo ""

# Ensure logs directory exists
mkdir -p "$WORKSPACE/logs"

# Run each audit script
for SCRIPT in scripts/list_ec2_instances.py \
              scripts/list_s3_buckets.py \
              scripts/list_iam_users.py \
              scripts/list_amplify_apps.py; do
    
    if [ -f "$SCRIPT" ]; then
        echo "📊 Running $(basename $SCRIPT)..."
        python3 "$SCRIPT" >> "$WORKSPACE/logs/aws-audit-$(date +%Y%m%d).log" 2>&1
        echo "   ✅ Completed → See logs/${PWD##*/}/logs/aws-audit-*.log"
    else
        echo "⚠️  Script not found: $SCRIPT"
    fi
done

echo ""
echo "================================"
echo "✅ ALL AUDITS COMPLETE!"
echo ""
echo "Results saved to: workspace/logs/"
echo "- EC2 instances → logs/aws-audit-YYYYMMDD.log"
echo "- S3 buckets → logs/aws-audit-YYYYMMDD.log"
echo "- IAM users → logs/aws-audit-YYYYMMDD.log"
echo "- Amplify apps → logs/aws-audit-YYYYMMDD.log"
echo ""
echo "To view results:"
tail -100 "$WORKSPACE/logs/aws-audit-$(date +%Y%m%d).log"
echo ""
echo "================================"
