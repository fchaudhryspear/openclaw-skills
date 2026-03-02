# 🔴 SECURITY INCIDENT RESPONSE: AWS Credential Exposure

## Incident Overview

**Date:** 2026-03-01  
**Severity:** CRITICAL  
**Exposed:** AWS Root Account Access Key `AKIA_REVOKED_KEY`  
**Location:** GitHub repository (https://github.com/fchaudhryspear/openclaw-skills)

---

## Immediate Actions Required ⚡

### ✅ COMPLETED (Automated)

- [x] Updated `.gitignore` to prevent future secret commits
- [x] Created emergency cleanup script (`security/emergency-cleanup.sh`)
- [x] Created CloudTrail audit script (`security/aws-audit.py`)
- [x] Prepared GitHub token revocation commands

### 🔴 URGENT - DO THESE NOW

1. **REVOKE AWS ACCESS KEY (5 minutes)**
   ```
   URL: https://console.aws.amazon.com/iam/home?#/security_credentials
   Action: Delete access key AKIA_REVOKED_KEY
   ```

2. **CHANGE ROOT PASSWORD (5 minutes)**
   ```
   URL: https://console.aws.amazon.com
   Navigate: Security Credentials → Change Password
   ```

3. **ENABLE MFA ON ROOT ACCOUNT (10 minutes)**
   ```
   URL: https://console.aws.amazon.com/iam/home?#/mfa
   Recommended: Authy or Google Authenticator
   ```

4. **DELETE/PRIVATIZE GITHUB REPOSITORY (10 minutes)**
   ```
   URL: https://github.com/fchaudhryspear/openclaw-skills/settings
   Options:
     a) Quick fix: Settings → Danger Zone → Make Private
     b) Best practice: Delete repo, recreate private version
   ```

5. **RUN EMERGENCY CLEANUP SCRIPT (20 minutes)**
   ```bash
   cd ~/openclaw/workspace
   chmod +x security/emergency-cleanup.sh
   ./security/emergency-cleanup.sh
   ```
   
   This will:
   - Remove all secrets from git history using BFG
   - Force push cleaned history to GitHub
   - Verify removal was successful

---

## Investigation Checklist 🔍

### Phase 1: CloudTrail Audit (Run immediately after revoking credentials)

```bash
cd ~/openclaw/workspace
pip install boto3
python security/aws-audit.py
```

This checks for:
- [ ] Unauthorized IAM user creation
- [ ] New access keys generated
- [ ] EC2 instances launched (crypto mining?)
- [ ] S3 buckets created/modified
- [ ] Lambda functions deployed
- [ ] Billing anomalies

### Phase 2: Manual Review (30-60 minutes)

Navigate to AWS Console and check:

#### EC2 Instances
- [ ] All running instances reviewed
- [ ] No unknown AMIs
- [ ] No suspicious process names (bitcoin, mining, etc.)
- [ ] Instance metadata service v2 enforced

#### S3 Buckets
- [ ] Bucket list reviewed
- [ ] Public access settings verified
- [ ] Block public access enabled on all buckets
- [ ] No unauthorized uploads found

#### IAM Users & Roles
- [ ] User list reviewed
- [ ] No new users since exposure date
- [ ] Admin privileges limited
- [ ] Service accounts use roles, not long-term credentials

#### Lambda Functions
- [ ] Function list reviewed
- [ ] Code unchanged without authorization
- [ ] Environment variables checked for injected secrets
- [ ] Dead letter queues examined

#### SNS/SQS
- [ ] Topics and queues reviewed
- [ ] Subscriptions verified legitimate
- [ ] Message content inspected for data exfiltration

#### RDS Databases
- [ ] Instances reviewed
- [ ] Snapshots checked
- [ ] Access logs examined
- [ ] No unauthorized exports

---

## Remediation Steps

### If Compromise Confirmed

1. **AWS Support Ticket**
   ```
   Severity: Severe
   Category: Security > Account compromise
   Description: "Root account access key exposed publicly on GitHub"
   Include: Evidence of unauthorized activity if found
   ```

2. **Notify Affected Parties**
   - Internal team lead
   - CTO / Security team
   - Legal (if customer data potentially exposed)
   - Insurance (if breach coverage exists)

3. **Rotate ALL Credentials**
   - AWS IAM users (not just root)
   - Database passwords
   - API keys for all services
   - OAuth tokens
   - SSH keys

4. **Enable Enhanced Monitoring**
   ```bash
   # CloudWatch detailed monitoring on all EC2
   # Enable GuardDuty (threat detection)
   # Enable Inspector (vulnerability scanning)
   ```

### Prevention Measures (Implement after cleanup)

1. **GitHub Protection**
   ```bash
   # Enable in repo settings:
   ☑ Secret scanning
   ☑ Secret scanning push protection
   ☑ Dependabot alerts
   ☑ Code scanning alerts
   ```

2. **Pre-Commit Hooks**
   ```bash
   pip install detect-secrets pre-commit
   detect-secrets scan --baseline .secrets.baseline
   pre-commit install
   ```

3. **Environment Variable Management**
   - Use AWS Secrets Manager instead of environment variables
   - Implement HashiCorp Vault for central secret management
   - Never commit `.env` files even if empty

4. **IAM Best Practices**
   - Root account ONLY used for initial setup
   - IAM users with least privilege permissions
   - MFA required for all human users
   - Rotate access keys every 90 days max
   - Use temporary credentials via STS when possible

5. **Monitoring & Alerting**
   - CloudWatch alarms on unusual API calls
   - SNS notifications for guardrail violations
   - Cost anomaly detection at $50/day threshold
   - Daily CloudTrail log delivery to S3

---

## Communication Template

### Internal Notification

```
Subject: URGENT: AWS Security Incident - Credentials Exposed

Team,

At [TIME], we discovered that AWS root account access keys were 
publicly exposed on GitHub. 

Current Status:
- Credentials have been revoked (or are being revoked now)
- Repository is being secured/deleted
- Full audit is underway

Actions Taken:
1. ✅ Revoked compromised access key
2. ✅ Changed root password
3. ✅ Running CloudTrail audit
4. 🔄 Cleaning git history

Next Steps:
- Complete full infrastructure audit within 2 hours
- Review all IAM users and rotate their credentials
- Assess any potential data exposure

If you notice anything unusual on your projects, report immediately.

[Your Name]
Security Team
```

### External (if required by law)

*Consult legal counsel before sending external communications.*

---

## Timeline Log

| Date | Time CST | Action | Performed By |
|------|----------|--------|--------------|
| 2026-03-01 | 19:20 | Incident detected | Security monitoring |
| 2026-03-01 | 19:21 | Automated cleanup started | Optimus AI |
| 2026-03-01 | ____ :____ | AWS key revoked | ________________ |
| 2026-03-01 | ____ :____ | Root password changed | ________________ |
| 2026-03-01 | ____ :____ | MFA enabled | ________________ |
| 2026-03-01 | ____ :____ | GitHub repo secured | ________________ |
| 2026-03-01 | ____ :____ | Git history cleaned | ________________ |
| 2026-03-01 | ____ :____ | CloudTrail audit complete | ________________ |
| 2026-03-01 | ____ :____ | Incident resolved | ________________ |

---

## Lessons Learned

After resolution, conduct post-mortem:

☑ How did the secret get committed?  
☑ What could have prevented it?  
☑ Was detection timely enough?  
☑ Are there gaps in our processes?  
☑ What tools need improvement?  

**Update this document with findings.**

---

## Contact Information

- **AWS Support:** https://console.aws.amazon.com/support
- **GitHub Security:** security-advisories@github.com
- **Internal Security Lead:** [Contact Info]
- **CISO:** [Contact Info]

---

*This document should be stored securely and shared only with authorized personnel involved in incident response.*
