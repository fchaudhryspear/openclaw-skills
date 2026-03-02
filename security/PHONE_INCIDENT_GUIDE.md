# 📱 EMERGENCY SECURITY ACTIONS - PHONE-FRIENDLY GUIDE

You're NOT at your computer but need to act NOW on AWS credential exposure.

---

## ⚡ ACTION #1: REVOKE AWS ACCESS KEY (CRITICAL - 5 MINUTES)

### Option A: AWS Mobile App (EASIEST)

**If you have the AWS Mobile App installed:**

1. **Open the AWS App**
   - iOS: App Store → "Amazon Web Services"
   - Android: Google Play → "Amazon Web Services"

2. **Sign in with ROOT account**
   - Email: Your root account email (likely personal Gmail based on context)
   - Password: Your root password
   - Tap "Sign In"

3. **Navigate to Credentials**
   - Tap ☰ menu → "Security & Identity" → "Access Keys"
   - OR tap profile icon → "My Security Credentials"

4. **Delete the compromised key**
   - Find key starting with: `AKIA_REVOKED_KEY`
   - Tap on it
   - Tap **"Delete Access Key"**
   - Confirm deletion

### Option B: Mobile Browser

**No app? Use any browser on your phone:**

1. **Open this URL:** https://console.aws.amazon.com/iam/home#/security_credentials
  
2. **Sign in as ROOT:**
   - You'll be redirected to: https://aws.amazon.com/console/
   - Sign in with your EMAIL ACCOUNT (root account, not IAM user)

3. **Find Access Keys:**
   - Once logged in, look for "Security Credentials" in top navigation
   - OR scroll down the IAM dashboard for "Access keys" section

4. **Delete the key:**
   - Look for: `AKIA_REVOKED_KEY`
   - Click "Delete" next to that key
   - Confirm

---

## ⚡ ACTION #2: CHANGE ROOT PASSWORD (5 MINUTES)

### Via Mobile Browser (Same session as above):

1. **After signing into AWS Console:**
   
2. **Click your account name** in the top-right corner
   
3. **Select "My Security Credentials"**

4. **Scroll to "Password"** section

5. **Click "Change password"**

6. **Enter new password:**
   - Minimum 8 characters (use 16+ for security)
   - Mix of upper/lower case, numbers, symbols
   - Example: `SecureP@ssw0rd!2026AwsRoot`
   
7. **Click "Change password" to confirm**

---

## ⚡ ACTION #3: ENABLE MFA (10 MINUTES) - PRIORITY HIGH

This protects your account even if credentials are compromised again.

### Step 1: Install Authenticator App (if not already installed)

**iOS:**
- Open App Store
- Search "Authy" or "Google Authenticator"
- Install (both free)

**Android:**
- Open Google Play
- Search "Authy" or "Google Authenticator"  
- Install (both free)

**Recommendation:** Authy allows cloud backup if you lose your phone

### Step 2: Enable MFA in AWS

1. **In AWS Console** (same session as before)

2. **Go to:** IAM → Dashboard → "Users" → Find and click on "root"

3. **Or navigate directly:** https://console.aws.amazon.com/iam/home#/mfa

4. **Click "Assign MFA"** under MFA status

5. **Select MFA type:** Choose "Virtual MFA device"

6. **Follow the setup:**
   - Click "Show QR code"
   - Scan QR code with your authenticator app
   - Enter first 6-digit code displayed
   - Enter second 6-digit code (wait ~30 seconds for new code)
   - Click "Assign MFA"

✅ **Done! MFA is now enabled on your root account.**

---

## ⚡ ACTION #4: GITHUB DELETION - WAIT UNTIL AT COMPUTER

❌ **Cannot be done from phone efficiently**

GitHub repository deletion requires either:
- Desktop browser access to repository settings, OR
- Running commands on your Mac

**What to do instead:**
- Mark this step as "PENDING"
- Complete when you return to your computer (~10 minutes required)
- Run the one-command cleanup script (see below)

---

## 📋 QUICK REFERENCE CHEAT SHEET

Copy this to notes app:

```
🔴 AWS COMPROMISED CREDENTIALS - INCIDENT RESPONSE

[ ] 1. AWS Key Revoked?
    └─ Key: AKIA_REVOKED_KEY
    └─ Status: ___DONE___ / ___NOT DONE___
    
[ ] 2. Root Password Changed?
    └─ Status: ___DONE___ / ___NOT DONE___
    
[ ] 3. MFA Enabled?
    └─ App used: ___Authy___ / ___Google Auth___
    └─ Status: ___DONE___ / ___NOT DONE___
    
[ ] 4. GitHub Repo Deleted?
    └─ Will complete at computer
    └─ Script: ./security/one-command-cleanup.sh
    └─ Status: PENDING

Timestamp started: ___:___ CST
Timestamp completed: ___:___ CST
```

---

## 📞 IF YOU NEED HELP

**AWS Support (24/7):**
- Free support portal: https://console.aws.amazon.com/support
- Or call: 1-888-485-1963 (US toll-free)
- Reference: "Security Incident - Credential Exposure"

**For immediate assistance:**
- Explain: "I exposed AWS root access keys publicly on GitHub"
- They will prioritize your ticket as **severe/critical**

---

## ✅ WHEN YOU RETURN TO YOUR COMPUTER

Run THIS command immediately:

```bash
cd ~/openclaw/workspace && chmod +x security/one-command-cleanup.sh && ./security/one-command-cleanup.sh
```

This ONE COMMAND will:
1. Delete GitHub repository
2. Remove ALL secrets from git history  
3. Create new private repository
4. Prevent future leaks

Then run:
```bash
pip install boto3 && python security/aws-audit.py
```

To check for unauthorized activity.

---

## 🕐 ESTIMATED TIME REMAINING

| Task | Time Required | Priority |
|------|---------------|----------|
| Revoke AWS Key | 5 min | 🔴 Critical |
| Change Password | 5 min | 🔴 Critical |
| Enable MFA | 10 min | 🔴 Critical |
| GitHub Cleanup (at computer) | 15 min | 🟡 High |
| Full Audit | 20-30 min | 🟡 High |

**Total remaining after this: ~50-60 minutes**

---

**Keep this document open on your phone. Check off items as you complete them.**

Any questions? Reply here when you get back to your computer.
