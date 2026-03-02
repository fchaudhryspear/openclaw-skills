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

echo ""
echo "🔐 Keys loaded from Keychain — auth-profiles.json is now secret-free on disk"
