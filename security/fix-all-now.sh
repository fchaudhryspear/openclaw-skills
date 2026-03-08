#!/bin/bash
# ================================================================
# fix-all-now.sh — Full security remediation
# Fixes:
#   1. auth-profiles.json — reload correct keys from Keychain
#   2. clawdbot.json — remove plaintext OpenAI/XAI/Gemini keys  
#   3. Script permissions — lock down to owner-only
#   4. AWS credentials file — ensure no plaintext keys
# Run: bash ~/.openclaw/workspace/security/fix-all-now.sh
# ================================================================
set -e

ACCOUNT="optimus"
AUTH_FILE="$HOME/.openclaw/agents/main/agent/auth-profiles.json"
CLAWDBOT="$HOME/.openclaw/clawdbot.json 13-48-50-514.json"

echo "🔍 Security Remediation — $(date)"
echo ""

# ── Step 1: Verify all keys are in Keychain ──────────────────────
echo "Step 1: Verifying Keychain entries..."
MISSING=0
for svc in anthropic-api-key openai-api-key google-api-key xai-api-key moonshot-api-key brave-api-key qwen-sg-api-key aws-access-key-id aws-secret-access-key; do
  val=$(security find-generic-password -a "$ACCOUNT" -s "$svc" -w 2>/dev/null)
  if [[ -z "$val" ]]; then
    echo "  ❌ MISSING: $svc"
    MISSING=$((MISSING+1))
  else
    echo "  ✅ $svc: ${val:0:12}..."
  fi
done

if [[ $MISSING -gt 0 ]]; then
  echo ""
  echo "⚠️  $MISSING key(s) missing from Keychain. Running keychain-setup.sh first..."
  bash "$(dirname "$0")/keychain-setup.sh"
fi

echo ""

# ── Step 2: Reload auth-profiles.json from Keychain ──────────────
echo "Step 2: Reloading auth-profiles.json from Keychain..."
bash "$(dirname "$0")/keychain-load.sh"

# Verify — check for old leaked keys
OLD_KEYS=("AIzaSyCj-CqJ" "xai-ZrOCURTz" "sk-3PKhTvKCr" "xai-Xd8YrHa")
LEAKED=0
for old in "${OLD_KEYS[@]}"; do
  if grep -q "$old" "$AUTH_FILE" 2>/dev/null; then
    echo "  ❌ OLD LEAKED KEY still present: $old"
    LEAKED=$((LEAKED+1))
  fi
done
if [[ $LEAKED -eq 0 ]]; then
  echo "  ✅ No old leaked keys in auth-profiles.json"
fi

echo ""

# ── Step 3: Fix clawdbot.json — remove plaintext keys ────────────
echo "Step 3: Scrubbing clawdbot.json..."
if [[ -f "$CLAWDBOT" ]]; then
  python3 - << PYEOF
import json, re

with open("$CLAWDBOT", "r") as f:
    content = f.read()

original_len = len(content)

# Replace any LLM API keys with redacted placeholders
replacements = [
    (r'sk-proj-[A-Za-z0-9_\-]{80,}',     '[OPENAI_KEY_IN_KEYCHAIN]'),
    (r'sk-ant-api03-[A-Za-z0-9_\-]{80,}', '[ANTHROPIC_KEY_IN_KEYCHAIN]'),
    (r'xai-[A-Za-z0-9]{60,}',             '[XAI_KEY_IN_KEYCHAIN]'),
    (r'AIzaSy[A-Za-z0-9_\-]{33}',         '[GOOGLE_KEY_IN_KEYCHAIN]'),
    (r'sk-(?!abc|test|fake|example)[A-Za-z0-9_\-]{45,}', '[SK_KEY_IN_KEYCHAIN]'),
]

for pattern, replacement in replacements:
    content, count = re.subn(pattern, replacement, content)
    if count:
        print(f"  ✅ Replaced {count}x: {replacement}")

with open("$CLAWDBOT", "w") as f:
    f.write(content)

print(f"  ✅ clawdbot.json scrubbed ({original_len} → {len(content)} chars)")
PYEOF
else
  echo "  ⚠️  clawdbot.json not found at expected path"
fi

echo ""

# ── Step 4: Lock down file permissions ───────────────────────────
echo "Step 4: Hardening file permissions..."
chmod 600 "$AUTH_FILE" 2>/dev/null && echo "  ✅ auth-profiles.json → 600 (owner read/write only)"
chmod 600 "$CLAWDBOT" 2>/dev/null && echo "  ✅ clawdbot.json → 600"
chmod 700 "$(dirname "$0")/keychain-setup.sh" 2>/dev/null && echo "  ✅ keychain-setup.sh → 700 (owner only)"
chmod 700 "$(dirname "$0")/keychain-load.sh" 2>/dev/null && echo "  ✅ keychain-load.sh → 700"
chmod 700 "$(dirname "$0")/keychain-rotate.sh" 2>/dev/null && echo "  ✅ keychain-rotate.sh → 700"

echo ""

# ── Step 5: Check AWS credentials file ───────────────────────────
echo "Step 5: Checking AWS credentials..."
AWS_CREDS="$HOME/.aws/credentials"
if [[ -f "$AWS_CREDS" ]]; then
  perms=$(stat -f "%OLp" "$AWS_CREDS")
  if [[ "$perms" != "600" ]]; then
    chmod 600 "$AWS_CREDS"
    echo "  ✅ ~/.aws/credentials permissions fixed → 600"
  else
    echo "  ✅ ~/.aws/credentials permissions OK (600)"
  fi
  # Check for obviously leaked key patterns
  if grep -qE "AKIA[A-Z0-9]{16}" "$AWS_CREDS" 2>/dev/null; then
    echo "  ⚠️  AWS credentials file has keys — verify they are current and not leaked"
    grep "aws_access_key_id" "$AWS_CREDS" | sed 's/=.*$/= [REDACTED]/'
  else
    echo "  ✅ No AWS key IDs visible in credentials file"
  fi
else
  echo "  ℹ️  No ~/.aws/credentials file found"
fi

echo ""

# ── Step 6: Final scan ───────────────────────────────────────────
echo "Step 6: Final full workspace scan..."
python3 "$(dirname "$0")/pre_commit_scanner.py" all

echo ""
echo "═══════════════════════════════════════════"
echo "✅ Security remediation complete"
echo "═══════════════════════════════════════════"
