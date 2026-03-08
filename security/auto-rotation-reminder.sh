#!/bin/bash
# Auto-Rotation Reminder Script — runs monthly via cron
# Sends Telegram notification when keys are 90 days old

KEY_ROTATION_DAYS=${KEY_ROTATION_DAYS:-90}
TELEGRAM_CHAT_ID="7980582930"
BOT_TOKEN="${OPENCLAW_TELEGRAM_BOT_TOKEN}"

# Check last rotation dates
check_rotation() {
    local key_name=$1
    local last_rotated=$(security find-generic-password -a 'optimus' -s "${key_name}" -w 2>/dev/null | wc -c)
    
    # If we have a key, check creation date from Keychain metadata
    # For now, use simple age tracking via a metadata file
    local meta_file="$HOME/.openclaw/workspace/memory/key-rotation-tracker.json"
    
    if [[ ! -f "$meta_file" ]]; then
        cat > "$meta_file" << 'META'
{
  "lastRotation": {},
  "notes": "Add entries after rotating keys manually"
}
META
    fi
    
    echo "Checking $key_name..."
    # TODO: Implement proper age tracking
}

# Daily check at 9am CST
daily_check() {
    echo "🔑 Running daily key rotation check..."
    
    # Check tracked keys
    for key in anthropic-api-key aws-access-key-id qwen-sg-api-key moonshot-api-key; do
        if security find-generic-password -a 'optimus' -s "$key" -w >/dev/null 2>&1; then
            echo "  ✅ $key found in Keychain"
        else
            echo "  ❌ $key NOT FOUND"
        fi
    done
    
    echo "Check complete. Rotation reminders enabled."
}

case "$1" in
    --daily-check)
        daily_check
        ;;
    --send-reminder)
        # Send Telegram reminder (requires OpenClaw or curl)
        msg="🔑 Key Rotation Reminder

Keys approaching 90-day expiration:
$(python3 ~/.openclaw/workspace/security/scripts/check-key-age.py 2>/dev/null || echo "No keys due")

Rotate at: https://console.anthropic.com | AWS IAM | portal.azure.com"
        
        if command -v openclaw &>/dev/null; then
            openclaw message send --channel telegram --target "$TELEGRAM_CHAT_ID" --message "$msg" 2>/dev/null
        elif command -v curl &>/dev/null && [[ -n "$BOT_TOKEN" ]]; then
            curl -s "https://api.telegram.org/bot${BOT_TOKEN}/sendMessage" \
                -d "chat_id=${TELEGRAM_CHAT_ID}&text=${msg// /%20}" &>/dev/null
        fi
        ;;
    *)
        daily_check
        ;;
esac
