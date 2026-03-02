#!/bin/bash
echo "🔐 COMPREHENSIVE CLAWDBOT SECURITY AUDIT"
echo "Against 10 Known Attack Vectors"
echo "========================================"
echo ""

ISSUES=0
WARNINGS=0

Hack #1: SSH Brute Force

echo "1️⃣ SSH Security Check"
echo " Checking SSH configuration..."
if grep -q "^PasswordAuthentication yes" /etc/ssh/sshd_config 2>/dev/null; then
echo " ❌ CRITICAL: Password authentication enabled!"
echo " Fix: Disable password auth, use SSH keys only"
ISSUES=$((ISSUES + 1))
elif grep -q "^PasswordAuthentication no" /etc/ssh/sshd_config 2>/dev/null; then
echo " ✅ Password authentication disabled"
else
echo " ⚠️ WARNING: PasswordAuthentication not explicitly set"
WARNINGS=$((WARNINGS + 1))
fi

if grep -q "^PermitRootLogin yes" /etc/ssh/sshd_config 2>/dev/null; then
echo " ❌ CRITICAL: Root login enabled!"
echo " Fix: Set PermitRootLogin no"
ISSUES=$((ISSUES + 1))
elif grep -q "^PermitRootLogin no" /etc/ssh/sshd_config 2>/dev/null; then
echo " ✅ Root login disabled"
fi

if [ -f /usr/sbin/fail2ban-server ]; then # Note: fail2ban-server is Linux-specific, may not exist on macOS
echo " ✅ fail2ban installed"
else
echo " ⚠️ WARNING: fail2ban not installed"
echo " Install: sudo apt install fail2ban (or brew install fail2ban on macOS)" # Adjusted install command
WARNINGS=$((WARNINGS + 1))
fi
echo ""

Hack #2: Exposed Gateway

echo "2️⃣ Gateway Security Check"
echo " Checking gateway binding..."
GATEWAY_BIND=$(grep -A5 '"gateway"' ~/.openclaw/openclaw.json | grep '"bind"' | cut -d'"' -f4)
if [ "$GATEWAY_BIND" == "loopback" ]  [ "$GATEWAY_BIND" == "localhost" ]  [ "$GATEWAY_BIND" == "127.0.0.1" ]; then
echo " ✅ Gateway bound to localhost only"
else
echo " ❌ CRITICAL: Gateway may be exposed!"
echo " Current binding: $GATEWAY_BIND"
ISSUES=$((ISSUES + 1))
fi

GATEWAY_AUTH=$(grep -A5 '"gateway"' ~/.openclaw/openclaw.json | grep -A2 '"auth"' | grep '"mode"' | cut -d'"' -f4)
if [ "$GATEWAY_AUTH" == "token" ]; then
echo " ✅ Gateway authentication enabled (token mode)"
else
echo " ❌ CRITICAL: Gateway authentication weak or disabled!"
ISSUES=$((ISSUES + 1))
fi
echo ""

Hack #3: Telegram/Discord Allowlist

echo "3️⃣ Messaging Platform Allowlist Check"
echo " Checking Telegram configuration..."
TELEGRAM_DM=$(grep -A10 '"telegram"' ~/.openclaw/openclaw.json | grep '"dmPolicy"' | cut -d'"' -f4)
if [ "$TELEGRAM_DM" == "pairing" ] || [ "$TELEGRAM_DM" == "allowlist" ]; then
echo " ✅ Telegram DM policy secure: $TELEGRAM_DM"
else
echo " ❌ CRITICAL: Telegram DM policy open to anyone!"
echo " Current: $TELEGRAM_DM"
ISSUES=$((ISSUES + 1))
fi

TELEGRAM_GROUP=$(grep -A10 '"telegram"' ~/.openclaw/openclaw.json | grep '"groupPolicy"' | cut -d'"' -f4)
if [ "$TELEGRAM_GROUP" == "allowlist" ]; then
echo " ✅ Telegram group policy secure: allowlist"
else
echo " ⚠️ WARNING: Telegram group policy: $TELEGRAM_GROUP"
WARNINGS=$((WARNINGS + 1))
fi

if [ -f ~/.openclaw/credentials/telegram-allowFrom.json ]; then
ALLOW_COUNT=$(jq 'length' ~/.openclaw/credentials/telegram-allowFrom.json 2>/dev/null || echo "0")
if [ "$ALLOW_COUNT" -gt 0 ]; then
echo " ✅ Telegram allowlist configured ($ALLOW_COUNT user(s))"
else
echo " ⚠️ WARNING: Telegram allowlist empty"
WARNINGS=$((WARNINGS + 1))
fi
fi
echo ""

Hack #4: Browser Session Hijacking

echo "4️⃣ Browser Security Check"
BROWSER_ENABLED=$(grep -r "browser.*enabled.*true" ~/.openclaw/openclaw.json 2>/dev/null)
if [ -z "$BROWSER_ENABLED" ]; then
echo " ✅ Browser control not enabled"
else
echo " ⚠️ WARNING: Browser control enabled"
echo " Ensure using separate profile, not your logged-in Chrome!"
WARNINGS=$((WARNINGS + 1))
fi
echo ""
```
