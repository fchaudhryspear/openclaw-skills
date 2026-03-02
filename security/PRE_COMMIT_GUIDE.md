# 🔒 Pre-Commit Security Protection System

**Automatic secret detection before every git commit to prevent accidental credential leaks.**

---

## 🎯 What This Protects Against

| Threat | Detection Method | Status |
|--------|-----------------|--------|
| AWS Access Keys | Pattern: `AKIA[0-9A-Z]{16}` | ✅ Scanned |
| GitHub Tokens | Patterns: `ghp_`, `gho_`, `ghu_` | ✅ Scanned |
| OpenAI/Anthropic Keys | Patterns: `sk-...` | ✅ Scanned |
| Database URLs | Connection strings with passwords | ✅ Scanned |
| Slack Tokens/Webhooks | Token patterns | ✅ Scanned |
| Private Keys | `-----BEGIN PRIVATE KEY-----` | ✅ Scanned |
| Generic Password/Tokens | Keyword + value patterns | ✅ Scanned |

---

## 🚀 Quick Setup (One-Time)

### Step 1: Install Git Pre-Commit Hook

```bash
cd ~/openclaw/workspace

# Copy hook to git hooks directory
cp security/git-precommit-hook .git/hooks/pre-commit

# Make executable
chmod +x .git/hooks/pre-commit
```

✅ **Done!** Now every `git commit` will automatically scan for secrets.

### Step 2: Verify Installation

```bash
# Check if hook is installed
ls -la .git/hooks/pre-commit

# Test scanner manually
python3 security/pre_commit_scanner.py staged
```

---

## 🔍 How It Works

### Before Commit:
```
User runs: git add <file> && git commit -m "..."
    ↓
Git executes: .git/hooks/pre-commit
    ↓
Scanner checks: All staged files against secret patterns
    ↓
If secrets detected → COMMIT BLOCKED ❌
If clean → COMMIT ALLOWED ✅
```

### If Blocked:
```
❌ FOUND 1 POTENTIAL SECRET(S)!

------------------------------------------------------------
❌ AWS Access Key ID
   File: config/secrets.json:15
   Match: AKIAI44QH8DHBEXAMPLE
   
------------------------------------------------------------
TO FIX:
1. Remove the secret from the file
2. Use environment variables instead
3. Add to .env.example with placeholder values
4. If intentional, add pattern to ALLOWED_PATTERNS

Then unstage changes: git reset HEAD <file>
```

---

## 💡 Best Practices (What TO DO)

### ✅ GOOD: Using Environment Variables

```python
# ❌ BAD - Hardcoded credentials in code
aws_key = "AKIAIOSFODNN7EXAMPLE"
password = "MySecurePassword123!"

# ✅ GOOD - Load from environment
import os
aws_key = os.getenv("AWS_ACCESS_KEY_ID")
password = os.getenv("DB_PASSWORD")
```

### ✅ GOOD: Create `.env.example` Template

```bash
# .env.example
AWS_ACCESS_KEY_ID=YOUR_KEY_HERE
AWS_SECRET_ACCESS_KEY=YOUR_SECRET_HERE
DATABASE_URL=postgres://user:password@host:port/dbname
API_TOKEN=your_token_here
```

This shows required env vars WITHOUT actual secrets!

### ✅ GOOD: Add to `.gitignore`

```gitignore
# Don't commit these!
.env
.env.local
.env.*.local
credentials.json
secrets.json
*.pem
*.key
```

---

## ⚙️ Configuration

### Customize Detected Patterns

Edit `/Users/faisalshomemacmini/.openclaw/workspace/security/pre_commit_scanner.py`:

```python
# Add new secret patterns:
SECRET_PATTERNS = {
    # ... existing patterns ...
    
    # Your custom service:
    'Custom API Key': r'custom_api_[a-zA-Z0-9]{32}',
}
```

### Add False Positive Exceptions

```python
ALLOWED_PATTERNS = [
    # ... existing exceptions ...
    
    # Allow your specific cases:
    r'special-pattern-to-exempt',
]
```

### Skip Directories

```python
SKIP_PATHS = [
    # ... existing skips ...
    
    # Add more:
    'vendor/',
    'third_party/',
]
```

---

## 🛠️ Troubleshooting

### Problem: "Commit still allowed even though I added a secret"

**Solution:** Run manual full scan:
```bash
python3 security/pre_commit_scanner.py all
```

### Problem: "False positive - legitimate code blocked"

**Solution 1:** Add to `ALLOWED_PATTERNS`  
**Solution 2:** Rename variable/file to avoid keywords  
**Solution 3:** Temporarily skip check (not recommended):
```bash
git commit --no-verify
```

### Problem: "Pre-commit hook doesn't run"

**Solution:** Reinstall hook:
```bash
chmod +x .git/hooks/pre-commit
```

Or re-copy:
```bash
cp security/git-precommit-hook .git/hooks/pre-commit
```

---

## 📊 Manual Scan Commands

### Scan Staged Files (Before Commit)
```bash
python3 security/pre_commit_scanner.py staged
```

### Scan Entire Workspace
```bash
python3 security/pre_commit_scanner.py all
```

### Scan Specific Files
```bash
# Edit scanner temporarily or pass filepath as argument
python3 -c "from security.pre_commit_scanner import scan_file; print(scan_file('config/app.py'))"
```

---

## 🔐 Secrets Should Go Here Instead

| Secret Type | Store In | Example |
|-------------|----------|---------|
| AWS Credentials | `~/.aws/credentials` | Managed by AWS CLI |
| API Keys | Environment variables | `export API_KEY="xxx"` |
| Database Passwords | `.env` file (ignored) | `DB_PASSWORD=secret` |
| OAuth Tokens | 1Password / LastPass | Encrypted password manager |
| SSH Keys | `~/.ssh/` (never git) | Private key stays local |
| Box Downloads | Deleted (`box_downloads/`) | Don't store locally! |

---

## 🚦 Workflow Integration

### Normal Development Flow

```bash
# 1. Make changes
$ vim my_code.py

# 2. Stage changes
$ git add my_code.py

# 3. Commit (scanner runs automatically!)
$ git commit -m "Add feature X"

# If OK:
✅ No secrets found. Proceeding with commit.

# If blocked:
🚨 FOUND 1 POTENTIAL SECRET(S)!
...follow fix instructions...
```

### Fixing an Accidental Commit

If you accidentally committed secrets BEFORE installing this hook:

1. **Revoke the exposed secret immediately!** (like we did with AWS key)
2. **Remove from history:**
   ```bash
   bfg --delete-files "*.json"
   git reflog expire --expire=now --all
   git gc --prune=now --aggressive
   git push origin main --force
   ```
3. **Install pre-commit hook to prevent recurrence**

---

## 🎓 Learning Resources

- **Why protect secrets:** https://cheatsheetseries.owasp.org/cheatsheets/Secrets_Management_Cheat_Sheet.html
- **GitHub secret scanning:** https://docs.github.com/en/code-security/secret-scanning/about-secret-scanning
- **Best practices:** https://12factor.net/config

---

## ✅ Verification Checklist

After setup, verify everything works:

```bash
[ ] 1. Hook installed
    └─ ls -la .git/hooks/pre-commit
    └─ Should show: -rwxr-xr-x

[ ] 2. Test benign commit
    └─ echo "test" >> test.txt
    └─ git add test.txt
    └─ git commit -m "Test"
    └─ Should succeed ✅

[ ] 3. Test blocking behavior
    └─ echo "password = \"super_secret\"" > bad_file.txt
    └─ git add bad_file.txt
    └─ git commit -m "Should fail"
    └─ Should be blocked ❌

[ ] 4. Clean up test files
    └─ git reset HEAD bad_file.txt
    └─ rm bad_file.txt test.txt
```

---

## 🆘 Support & Maintenance

### Update Scanner

If you find a new type of secret not being caught:
1. Add pattern to `SECRET_PATTERNS` dict in scanner
2. Test: `python3 security/pre_commit_scanner.py staged`
3. Commit the update to improve future protection

### Report Issues

If scanner has bugs or false positives:
- Document the file/pattern causing issues
- Test on isolated branch
- Report to security team or update configuration

---

## 🎉 Summary

**With this system in place:**

✅ Prevents accidental credential commits  
✅ Educates developers on secure practices  
✅ Reduces security incident risk  
✅ Enforces best practices automatically  
✅ Serves as security checklist reminder  

**Remember:** This is just ONE layer of defense. Still:
- Review pull requests carefully
- Rotate secrets periodically
- Monitor for leaked credentials on GitHub
- Never store production secrets in repos

---

**Questions? Review the code in `security/pre_commit_scanner.py`**

Last Updated: 2026-03-01  
Maintainer: Optimus AI Agent
