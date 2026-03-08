#!/bin/bash
# =============================================================
# Optimus Keychain Loader
# Reads keys from macOS Keychain → writes auth-profiles.json
# Called at OpenClaw startup or manually any time.
# =============================================================

ACCOUNT="optimus"
AUTH_FILE="$HOME/.openclaw/agents/main/agent/auth-profiles.json"

get_key() {
  security find-generic-password -a "$ACCOUNT" -s "$1" -w 2>/dev/null
}

echo "🔑 Loading keys from Keychain..."

ANTHROPIC=$(get_key "anthropic-api-key")
OPENAI=$(get_key "openai-api-key")
GOOGLE=$(get_key "google-api-key")
XAI=$(get_key "xai-api-key")
MOONSHOT=$(get_key "moonshot-api-key")
BRAVE=$(get_key "brave-api-key")
QWEN_SG=$(get_key "qwen-sg-api-key")
AWS_KEY_ID=$(get_key "aws-access-key-id")
AWS_SECRET=$(get_key "aws-secret-access-key")

# Validate — abort if any critical key is missing
if [[ -z "$ANTHROPIC" || -z "$OPENAI" || -z "$GOOGLE" ]]; then
  echo "❌ One or more critical keys not found in Keychain. Run keychain-setup.sh first."
  exit 1
fi

# Read existing file to preserve OAuth tokens (qwen-portal)
QWEN_PORTAL_ACCESS=$(python3 -c "
import json
try:
  d = json.load(open('$AUTH_FILE'))
  print(d['profiles'].get('qwen-portal:default', {}).get('access', ''))
except: print('')
" 2>/dev/null)

QWEN_PORTAL_REFRESH=$(python3 -c "
import json
try:
  d = json.load(open('$AUTH_FILE'))
  print(d['profiles'].get('qwen-portal:default', {}).get('refresh', ''))
except: print('')
" 2>/dev/null)

QWEN_PORTAL_EXPIRES=$(python3 -c "
import json
try:
  d = json.load(open('$AUTH_FILE'))
  print(d['profiles'].get('qwen-portal:default', {}).get('expires', ''))
except: print('')
" 2>/dev/null)

# Write fresh auth-profiles.json
python3 - <<PYEOF
import json

profiles = {
    "anthropic:default": {
        "type": "api_key",
        "provider": "anthropic",
        "key": "$ANTHROPIC"
    },
    "google:default": {
        "type": "api_key",
        "provider": "google",
        "key": "$GOOGLE"
    },
    "openai:default": {
        "type": "api_key",
        "provider": "openai",
        "key": "$OPENAI"
    },
    "moonshot:default": {
        "type": "api_key",
        "provider": "moonshot",
        "key": "$MOONSHOT"
    },
    "xai:default": {
        "type": "api_key",
        "provider": "xai",
        "key": "$XAI"
    },
    "alibaba-sg:default": {
        "type": "api_key",
        "provider": "alibaba-sg",
        "key": "$QWEN_SG"
    },
    "alibaba-us:default": {
        "type": "api_key",
        "provider": "alibaba-us",
        "key": "$QWEN_SG"
    }
}

# Preserve qwen-portal OAuth if it exists
if "$QWEN_PORTAL_ACCESS":
    profiles["qwen-portal:default"] = {
        "type": "oauth",
        "provider": "qwen-portal",
        "access": "$QWEN_PORTAL_ACCESS",
        "refresh": "$QWEN_PORTAL_REFRESH",
        "expires": int("$QWEN_PORTAL_EXPIRES") if "$QWEN_PORTAL_EXPIRES" else 0
    }

output = {
    "version": 1,
    "profiles": profiles,
    "lastGood": {k.split(":")[0]: k for k in profiles.keys()},
    "usageStats": {}
}

with open("$AUTH_FILE", "w") as f:
    json.dump(output, f, indent=2)

print("✅ auth-profiles.json updated from Keychain")
PYEOF

# Also update clawdbot.json brave key
python3 - <<PYEOF2
import re
try:
    path = "$HOME/.openclaw/clawdbot.json 13-48-50-514.json"
    with open(path, "r") as f:
        content = f.read()
    # Replace any existing brave key pattern
    content = re.sub(r'BSA[A-Za-z0-9_-]{20,}', '$BRAVE', content)
    with open(path, "w") as f:
        f.write(content)
    print("✅ Brave key updated in clawdbot.json")
except Exception as e:
    print(f"⚠️  clawdbot.json update skipped: {e}")
PYEOF2

# ── Write ~/.aws/credentials from Keychain ──────────────────────
if [[ -n "$AWS_KEY_ID" && -n "$AWS_SECRET" ]]; then
  mkdir -p ~/.aws
  cat > ~/.aws/credentials << AWSEOF
[default]
aws_access_key_id = $AWS_KEY_ID
aws_secret_access_key = $AWS_SECRET
region = us-east-1
AWSEOF
  chmod 600 ~/.aws/credentials
  echo "✅ ~/.aws/credentials written from Keychain"
else
  echo "⚠️  AWS keys not in Keychain — ~/.aws/credentials not updated"
fi

echo ""
echo "🔐 Keys loaded from Keychain — auth-profiles.json is now secret-free on disk"

# ── Patch openclaw.json provider keys from Keychain ──────────────
OPENCLAW_JSON="$HOME/.openclaw/openclaw.json"
if [[ -f "$OPENCLAW_JSON" ]]; then
  python3 - << PYEOF
import json

with open("$OPENCLAW_JSON", "r") as f:
    d = json.load(f)

p = d.get("models", {}).get("providers", {})
updates = {
    "anthropic":  ("$ANTHROPIC",  "apiKey"),
    "google":     ("$GOOGLE",     "apiKey"),
    "xai":        ("$XAI",        "apiKey"),
    "moonshot":   ("$MOONSHOT",   "apiKey"),
    "openai":     ("$OPENAI",     "apiKey"),
    "alibaba-sg": ("$QWEN_SG",    "apiKey"),
}

for provider, (key, field) in updates.items():
    if provider in p and key:
        p[provider][field] = key

if "tools" in d and "web" in d["tools"] and "search" in d["tools"]["web"]:
    d["tools"]["web"]["search"]["apiKey"] = "$BRAVE"

with open("$OPENCLAW_JSON", "w") as f:
    json.dump(d, f, indent=2)

print("✅ openclaw.json provider keys updated from Keychain")
PYEOF
fi

# Microsoft Graph OAuth secrets (Office365 Evening Run)
OAUTH2_SECRET_FLOBASE=$(get_key "msgraph-flobase-secret")
OAUTH2_SECRET_UTILITYVALET=$(get_key "msgraph-utilityvalet-secret")
OAUTH2_SECRET_STARSHIP=$(get_key "msgraph-starship-secret")
OAUTH2_SECRET_DALLASPARTNERS=$(get_key "msgraph-dallaspartners-secret")
OAUTH2_SECRET_SPEARHEAD=$(get_key "msgraph-spearhead-secret")

if [[ -n "$OAUTH2_SECRET_FLOBASE" || -n "$OAUTH2_SECRET_UTILITYVALET" ]]; then
    export OAUTH2_SECRET_FLOBASE
    export OAUTH2_SECRET_UTILITYVALET
    export OAUTH2_SECRET_STARSHIP
    export OAUTH2_SECRET_DALLASPARTNERS
    export OAUTH2_SECRET_SPEARHEAD
    echo "✅ Office365 OAuth secrets loaded from Keychain"
fi
if [[ -n "$AWS_KEY_ID" && -n "$AWS_SECRET" ]]; then
    export AWS_ACCESS_KEY_ID="$AWS_KEY_ID"
    export AWS_SECRET_ACCESS_KEY="$AWS_SECRET"
    # Write to .aws/credentials if it doesn't exist or is empty
    mkdir -p ~/.aws
    if ! grep -q "^aws_access_key_id" ~/.aws/credentials 2>/dev/null; then
        cat > ~/.aws/credentials << CREDS
[default]
aws_access_key_id = $AWS_KEY_ID
aws_secret_access_key = $AWS_SECRET
CREDS
        chmod 600 ~/.aws/credentials
        echo "✅ AWS credentials loaded from Keychain"
    fi
fi

# AWS credentials
AWS_KEY_ID=$(get_key "aws-access-key-id")
AWS_SECRET=$(get_key "aws-secret-access-key")
if [[ -n "$AWS_KEY_ID" && -n "$AWS_SECRET" ]]; then
    export AWS_ACCESS_KEY_ID="$AWS_KEY_ID"
    export AWS_SECRET_ACCESS_KEY="$AWS_SECRET"
    # Write to .aws/credentials if it doesn't exist or is empty
    mkdir -p ~/.aws
    if ! grep -q "^aws_access_key_id" ~/.aws/credentials 2>/dev/null; then
        cat > ~/.aws/credentials << CREDS
[default]
aws_access_key_id = $AWS_KEY_ID
aws_secret_access_key = $AWS_SECRET
CREDS
        chmod 600 ~/.aws/credentials
    fi
fi
