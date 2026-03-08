# Optimus Security Policy
**Version:** 1.0 — 2026-03-02  
**Status:** Active  
**Owner:** Fas / Credologi

---

## 1. What This Covers

This policy governs how API keys, credentials, tokens, and other secrets are handled across all code, files, git commits, and uploads in the Optimus workspace.

**Root cause of the March 2, 2026 incident:** API keys were typed into a chat/Box document, that document was saved as a JSON file, committed to git, and pushed to two public GitHub repos. All keys were compromised.

---

## 2. The Golden Rules (Never Break These)

| # | Rule |
|---|------|
| 1 | **Never type a real API key into a chat, doc, or message** |
| 2 | **Never hardcode keys in any file** — use env vars or Keychain |
| 3 | **Never commit a file containing a real key** — scanner will block it |
| 4 | **Never bypass the pre-commit hook** (`git commit --no-verify` is forbidden) |
| 5 | **Never store keys in markdown, README, or documentation** |
| 6 | **Rotate immediately if a key is exposed** — even to yourself in chat |

---

## 3. Where Keys Live

| Provider | Keychain Service | Load Script |
|----------|-----------------|-------------|
| Anthropic | `anthropic-api-key` | auto via keychain-load.sh |
| OpenAI | `openai-api-key` | auto |
| Google Gemini | `google-api-key` | auto |
| XAI Grok | `xai-api-key` | auto |
| Moonshot/Kimi | `moonshot-api-key` | auto |
| Brave Search | `brave-api-key` | auto via clawdbot.json |
| Qwen (SG + US) | `qwen-sg-api-key` | auto |

**Auth file:** `~/.openclaw/agents/main/agent/auth-profiles.json`  
→ Always populated from Keychain at runtime. Never edit directly.

---

## 4. Before Uploading / Pushing to GitHub

### Step 1 — Run the scanner manually
```bash
python3 ~/.openclaw/workspace/security/pre_commit_scanner.py all
```
Must return `✅ No secrets found.` before proceeding.

### Step 2 — Check .gitignore covers sensitive paths
```bash
cat ~/.openclaw/workspace/.gitignore | grep -E "api-keys|box_downloads|\.env|backup"
```
Must show these entries:
- `workspace/api-keys.json`
- `box_downloads/`
- `*.backup`
- `.env` / `.env.*`

### Step 3 — Verify git status doesn't include secret files
```bash
cd ~/.openclaw/workspace && git status
```
If `box_downloads/`, `api-keys.json`, or `.env` appear — **stop and abort**.

### Step 4 — Push (scanner auto-runs via pre-push hook)
```bash
git push origin main
```
The pre-push hook runs the full workspace scan automatically. If it fails, the push is blocked.

---

## 5. Rotating a Key

**When to rotate:** Key exposed in any chat, doc, file, or log. When in doubt — rotate.

```bash
# Rotate a single key
bash ~/.openclaw/workspace/security/keychain-rotate.sh <service-name> <new-key>

# Available service names:
#   anthropic-api-key
#   openai-api-key
#   google-api-key
#   xai-api-key
#   moonshot-api-key
#   brave-api-key
#   qwen-sg-api-key
```

After rotation, verify OpenClaw is using the new key:
```bash
bash ~/.openclaw/workspace/security/keychain-load.sh
```

---

## 6. If a Leak Is Detected

Follow this checklist in order — speed matters:

```
[ ] 1. REVOKE the key immediately at the provider console
[ ] 2. Generate a new key at the provider console
[ ] 3. Rotate in Keychain: keychain-rotate.sh <service> <new-key>
[ ] 4. Find the source: grep -r "OLD_KEY_PREFIX" ~/.openclaw/workspace
[ ] 5. Check git history: git log -p --all | grep -E "sk-|xai-|AIza|AKIA"
[ ] 6. If in git history: git filter-repo --path <file> --invert-paths
[ ] 7. Force push both remotes: git push origin --force --all
[ ] 8. Force push:             git push newrepo --force --all
[ ] 9. Check GitHub Secret Scanning alerts (Settings > Security)
[ ] 10. Log the incident in ~/memory/decisions/ and ~/memory/rules/
```

**Provider consoles:**
- Anthropic: https://console.anthropic.com/settings/keys
- OpenAI: https://platform.openai.com/api-keys
- Google: https://aistudio.google.com/app/apikey
- XAI: https://console.x.ai
- Moonshot: https://platform.moonshot.ai
- Brave: https://api.search.brave.com/app/keys
- Qwen: https://modelstudio.console.alibabacloud.com

---

## 7. .gitignore Required Entries

These must always be present in `.gitignore`:

```gitignore
# Secrets — never commit
.env
.env.*
*.backup
workspace/api-keys.json
box_downloads/
auth-profiles.json
**/auth-profiles.json
clawdbot*.json
*.pem
*.key
*.p12
*.pfx
```

---

## 8. What's Allowed in Code Files

| ✅ Allowed | ❌ Never |
|-----------|---------|
| `process.env.OPENAI_API_KEY` | `sk-proj-abc123...` |
| `$ANTHROPIC_API_KEY` | `sk-ant-api03-...` |
| `security find-generic-password ...` | Hardcoded key value |
| `YOUR_API_KEY_HERE` placeholder | Real key in README/docs |
| Fake keys in test files (`sk-abcdefgh...`) | Real keys in test files |

---

## 9. Auto-Protections Active

| Protection | Status | Where |
|-----------|--------|-------|
| Pre-commit hook scans staged files | ✅ Active | `.git/hooks/pre-commit` |
| Pre-push hook scans full workspace | ✅ Active | `.git/hooks/pre-push` |
| Keys in macOS Keychain | ✅ Active | `security` tool |
| Keychain loader on terminal open | ✅ Active | `~/.zshrc` |
| `.gitignore` covers secret files | ✅ Active | `.gitignore` |
| GitHub Secret Scanning (push protection) | ✅ Active | GitHub repo settings |

---

## 10. Adding a New API Key (Future)

1. **Get key** from provider console
2. **Store in Keychain:**
   ```bash
   security add-generic-password -U -a "optimus" -s "<service-name>-api-key" -w "<key>"
   ```
3. **Add to keychain-load.sh** — add `get_key "<service-name>-api-key"` and inject into auth-profiles.json
4. **Add pattern to scanner** — add regex to `pre_commit_scanner.py` PATTERNS list
5. **Add to .gitignore** if any config file references it
6. **Test:** `bash keychain-load.sh` + `python3 pre_commit_scanner.py all`

---

*This policy is enforced automatically by git hooks. Manual bypasses (`--no-verify`) are prohibited except in documented emergencies.*
