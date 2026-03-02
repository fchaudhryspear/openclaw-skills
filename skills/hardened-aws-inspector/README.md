# Hardened AWS Inspector Skill

**Read-only AWS auditing tools for security compliance.**

---

## ⚡ Overview

Four read-only scripts that safely inspect your AWS infrastructure without making any changes:

1. `list_ec2_instances.py` - List all EC2 instances + health status
2. `list_s3_buckets.py` - List all S3 buckets + public access settings  
3. `list_iam_users.py` - Audit IAM users, groups, permissions
4. `list_amplify_apps.py` - List Amplify apps + deployment status

**Security Features:**
- 🔒 No write permissions (strictly read-only)
- 🔐 Credentials from environment variables only
- 📝 All output logged to workspace logs directory
- 🚫 Credentials NEVER stored in code or config files
- ✅ IAM policy requires least privilege

---

## 🚀 Quick Start

### Option 1: Using Environment Variables (RECOMMENDED)

```bash
export AWS_ACCESS_KEY_ID=YOUR_AWS_ACCESS_KEY_ID
export AWS_SECRET_ACCESS_KEY=YOUR_AWS_SECRET_ACCESS_KEY

# Test connection
aws sts get-caller-identity

# Run inspector scripts
python3 skills/hardened-aws-inspector/scripts/list_ec2_instances.py
python3 skills/hardened-aws-inspector/scripts/list_s3_buckets.py
python3 skills/hardened-aws-inspector/scripts/list_iam_users.py
python3 skills/hardened-aws-inspector/scripts/list_amplify_apps.py
```

### Option 2: Using ~/.aws/credentials

```bash
cat > ~/.aws/credentials << 'EOF'
[default]
aws_access_key_id = YOUR_AWS_ACCESS_KEY_ID
aws_secret_access_key = YOUR_AWS_SECRET_ACCESS_KEY
EOF

chmod 600 ~/.aws/credentials
```

Then run scripts directly.

---

## 📁 File Structure

```
skills/hardened-aws-inspector/
├── README.md                           # This file
├── iam-policy.json                     # Required IAM permissions policy
└── scripts/
    ├── list_ec2_instances.py          # EC2 inventory script
    ├── list_s3_buckets.py             # S3 bucket audit script
    ├── list_iam_users.py              # IAM user/permissions audit
    └── list_amplify_apps.py           # Amplify app inventory
```

---

## 🔧 Script Details

### list_ec2_instances.py

Lists all EC2 instances with their state, instance type, launch time, and tags.

```bash
python3 scripts/list_ec2_instances.py
```

Sample output:
```json
{
  "instances": [
    {
      "InstanceId": "i-abc123def456",
      "State": "running",
      "InstanceType": "t3.micro",
      "LaunchTime": "2026-01-15T10:30:00Z",
      "Tags": {...}
    }
  ],
  "total_count": 1,
  "status": "success"
}
```

### list_s3_buckets.py

Lists all S3 buckets with public access status, encryption, and versioning.

```bash
python3 scripts/list_s3_buckets.py
```

Highlights:
- Public access blocking status
- Server-side encryption enabled?
- Versioning enabled?
- Last modified date

### list_iam_users.py

Audits IAM users, their groups, attached policies, and MFA status.

```bash
python3 scripts/list_iam_users.py
```

Security findings:
- Users with MFA disabled
- Users with no MFA
- Users with overly permissive policies
- Unused access keys (>90 days old)

### list_amplify_apps.py

Lists AWS Amplify applications with build/deployment status.

```bash
python3 scripts/list_amplify_apps.py
```

Shows:
- App name and ID
- Current branch deployments
- Build status
- Custom domains connected

---

## 🔐 Security Configuration

### Required IAM Policy

Create a read-only IAM policy for the service user (`data-lake-deploy`):

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "EC2ReadOnly",
      "Effect": "Allow",
      "Action": [
        "ec2:DescribeInstances",
        "ec2:DescribeTags",
        "ec2:DescribeAvailabilityZones",
        "ec2:DescribeRegions"
      ],
      "Resource": "*"
    },
    {
      "Sid": "S3ReadOnly",
      "Effect": "Allow",
      "Action": [
        "s3:ListAllMyBuckets",
        "s3:GetBucketPolicy",
        "s3:GetBucketAcl",
        "s3:ListBucket",
        "s3:GetObject",
        "s3:GetEncryptionConfiguration",
        "s3:GetBucketVersioning"
      ],
      "Resource": "*"
    },
    {
      "Sid": "IAMReadOnly",
      "Effect": "Allow",
      "Action": [
        "iam:ListUsers",
        "iam:GetUser",
        "iam:ListGroupsForUser",
        "iam:ListUserPolicies",
        "iam:GetPolicy",
        "iam:ListAttachedUserPolicies",
        "iam:ListMFADevices",
        "iam:GetAccountAuthorizationDetails"
      ],
      "Resource": "*"
    },
    {
      "Sid": "AmplifyReadOnly",
      "Effect": "Allow",
      "Action": [
        "amplify:GetApp",
        "amplify:ListApps",
        "amplify:ListJobs",
        "amplify:GetJob",
        "amplify:GetBranch"
      ],
      "Resource": "*"
    },
    {
      "Sid": "STSAssumeRole",
      "Effect": "Allow",
      "Action": "sts:GetCallerIdentity",
      "Resource": "*"
    }
  ]
}
```

To apply this policy:

1. Go to: https://console.aws.amazon.com/iam/home#/policies/new
2. Click **"JSON"** tab
3. Paste the policy above
4. Name: `hardened-aws-inspector-read-only`
5. Create policy

Then attach to `data-lake-deploy` user:

1. Go to: https://console.aws.amazon.com/iam/home#/users
2. Click **"data-lake-deploy"** user
3. Go to **"Permissions"** tab → **"Add permissions"**
4. Select policy: `hardened-aws-inspector-read-only`
5. Add permissions

---

## 🔄 Automated Usage

### Schedule Daily Scans

Add to crontab for daily automated scans:

```bash
# Run every day at 7 AM CST
0 7 * * * cd /Users/faisalshomemacmini/.openclaw/workspace && python3 skills/hardened-aws-inspector/scripts/list_ec2_instances.py >> workspace/logs/aws-ec2-scan.log 2>&1
```

### Combine Into Single Report

```bash
#!/bin/bash
# ~/scripts/daily-aws-audit.sh

cd /Users/faisalshomemacmini/.openclaw/workspace

echo "=== AWS Daily Security Audit ===" > workspace/logs/daily-audit-$(date +%Y%m%d).txt
echo "" >> workspace/logs/daily-audit-$(date +%Y%m%d).txt

python3 skills/hardened-aws-inspector/scripts/list_ec2_instances.py >> workspace/logs/daily-audit-$(date +%Y%m%d).txt
python3 skills/hardened-aws-inspector/scripts/list_s3_buckets.py >> workspace/logs/daily-audit-$(date +%Y%m%d).txt
python3 skills/hardened-aws-inspector/scripts/list_iam_users.py >> workspace/logs/daily-audit-$(date +%Y%m%d).txt
python3 skills/hardened-aws-inspector/scripts/list_amplify_apps.py >> workspace/logs/daily-audit-$(date +%Y%m%d).txt
```

---

## ❗ Troubleshooting

### Issue: "Unable to locate credentials"

**Solution:** Set environment variables or create `~/.aws/credentials`:

```bash
export AWS_ACCESS_KEY_ID=your_access_key_here
export AWS_SECRET_ACCESS_KEY=your_secret_key_here
```

Or create credentials file:
```bash
nano ~/.aws/credentials
```

Add:
```ini
[default]
aws_access_key_id = YOUR_KEY_ID
aws_secret_access_key = YOUR_SECRET_KEY
```

Set permissions:
```bash
chmod 600 ~/.aws/credentials
```

### Issue: "Access Denied" / "UnauthorizedOperation"

**Solution:** Your IAM user doesn't have sufficient permissions. Attach the `hardened-aws-inspector-read-only` policy as documented above.

### Issue: Region Not Found

**Solution:** Add region configuration:
```bash
export AWS_DEFAULT_REGION=us-east-1
```

Or edit `~/.aws/config`:
```ini
[default]
region = us-east-1
output = json
```

---

## 📊 Output Formats

All scripts output JSON by default. For human-readable format, use Python's `json.tool`:

```bash
python3 scripts/list_ec2_instances.py | python3 -m json.tool
```

---

## 🎯 Use Cases

### Security Compliance Auditing
```bash
python3 scripts/list_iam_users.py | grep -i "MFA disabled"
python3 scripts/list_s3_buckets.py | grep -i "public"
```

### Infrastructure Inventory
```bash
python3 scripts/list_ec2_instances.py
python3 scripts/list_amplify_apps.py
```

### Cost Optimization Analysis
```bash
python3 scripts/list_ec2_instances.py | jq '.instances[] | select(.State == "stopped")'
```

---

## 🔒 Best Practices

✅ **DO:**
- Store credentials in Keychain or environment variables
- Rotate access keys every 90 days
- Review scan results regularly
- Enable CloudTrail logging for API activity

❌ **DON'T:**
- Commit credentials to git
- Share credentials via email/chat
- Store secrets in plaintext files
- Use root account access keys

---

## 📋 Maintenance

### Update IAM Permissions

If you encounter permission errors:

1. Check CloudTrail for denied actions
2. Add required permissions to the IAM policy
3. Reattach policy to user
4. Test again

### Log Rotation

Logs are saved to `workspace/logs/`. Set up log rotation:

```bash
# Add to /etc/logrotate.d/aws-inspector
/Users/faisalshomemacmini/.openclaw/workspace/logs/aws-*.log {
    daily
    rotate 30
    compress
    delaycompress
    notifempty
    create 0644 faisalshomemacmini staff
}
```

---

**Last Updated:** 2026-03-01  
**Owner:** Optimus AI Agent  
**Status:** Production Ready ✅
