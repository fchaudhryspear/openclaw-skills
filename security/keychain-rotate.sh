#!/bin/bash
# =============================================================
# Optimus Key Rotation Helper
# Updates a single key in Keychain + reloads auth-profiles.json
# Usage: bash keychain-rotate.sh <service> <new-key>
# Example: bash keychain-rotate.sh anthropic-api-key sk-ant-...
# =============================================================

SERVICE="$1"
NEW_KEY="$2"
ACCOUNT="optimus"

VALID_SERVICES=(
  "anthropic-api-key"
  "openai-api-key"
  "google-api-key"
  "xai-api-key"
  "moonshot-api-key"
  "brave-api-key"
  "qwen-sg-api-key"
  "aws-access-key-id"
  "aws-secret-access-key"
)

if [[ -z "$SERVICE" || -z "$NEW_KEY" ]]; then
  echo "Usage: bash keychain-rotate.sh <service> <new-key>"
  echo ""
  echo "Available services:"
  for s in "${VALID_SERVICES[@]}"; do echo "  $s"; done
  exit 1
fi

echo "🔄 Rotating $SERVICE in Keychain..."
security add-generic-password -U -a "$ACCOUNT" -s "$SERVICE" -w "$NEW_KEY" \
  && echo "✅ Keychain updated" \
  || { echo "❌ Failed to update Keychain"; exit 1; }

echo "🔄 Reloading auth-profiles.json..."
bash "$(dirname "$0")/keychain-load.sh"

echo ""
echo "✅ Rotation complete for: $SERVICE"
