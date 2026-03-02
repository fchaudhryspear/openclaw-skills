  • Once nano opens, paste the entire content below into it. (Copy the text from # Hack #5: Password Manager Exposure all the way to the end of the echo "" line at the bottom).

Hack #5: Password Manager Exposure

echo "5️⃣ Password Manager Security Check"
if command -v op &> /dev/null; then
echo " ⚠️ WARNING: 1Password CLI installed"
if op account list &> /dev/null; then
echo " ❌ CRITICAL: 1Password CLI is authenticated!"
echo " Run: op signout"
ISSUES=$((ISSUES + 1))
else
echo " ✅ 1Password CLI not authenticated"
fi
else
echo " ✅ 1Password CLI not installed"
fi

if [ -f ~/.password-store/.gpg-id ]; then
echo " ⚠️ WARNING: pass (password store) detected"
WARNINGS=$((WARNINGS + 1))
fi
echo ""

Hack #6: Slack Security Check

echo "6️⃣ Slack Security Check"
SLACK_ENABLED=$(grep -A5 '"slack"' ~/.openclaw/openclaw.json 2>/dev/null | grep '"enabled".*true')
if [ -z "$SLACK_ENABLED" ]; then
echo " ✅ Slack not enabled"
else
echo " ⚠️ WARNING: Slack enabled"
echo " Ensure tokens are not exposed in logs/config"
WARNINGS=$((WARNINGS + 1))
fi
echo ""

Hack #7: Docker/Privileged Mode (macOS specific check)

echo "7️⃣ Container Security Check"

For macOS, Docker Desktop is common. We check if Docker is running.

if pgrep -x "Docker Desktop" &> /dev/null; then
echo " ⚠️ WARNING: Docker Desktop is running"

More advanced checks for container escape/privilege are complex on macOS without specific tools.

This part of the script is primarily designed for Linux servers.

echo " ℹ️ Advanced container security checks for macOS are more complex."
echo "    Manual review of Docker configurations and images is recommended."
WARNINGS=$((WARNINGS + 1))
else
echo " ✅ Docker not running (or not Docker Desktop on macOS)"
fi
echo ""

Hack #8: File Permissions

echo "8️⃣ File Permission Check"
echo " Checking sensitive files..."
BAD_PERMS=0
for file in ~/.openclaw/openclaw.json ~/.openclaw/credentials/.json ~/.aws/credentials ~/.ssh/id_ 2>/dev/null; do
if [ -f "$file" ]; then
PERMS=$(stat -f %A "$file" 2>/dev/null) # stat -f %A for macOS permissions
if [ "$PERMS" != "600" ] && [ "$PERMS" != "400" ]; then
echo " ❌ Bad permissions on $file: $PERMS (should be 600 or 400)"
BAD_PERMS=$((BAD_PERMS + 1))
fi
fi
done
if [ "$BAD_PERMS" -eq 0 ]; then
echo " ✅ All sensitive files have correct permissions"
else
echo " ❌ CRITICAL: $BAD_PERMS file(s) with incorrect permissions"
ISSUES=$((ISSUES + BAD_PERMS))
fi
echo ""

Hack #9: Environment Variables

echo "9️⃣ Environment Variable Security Check"
if [ -f ~/clawd/.env ]; then
ENV_PERMS=$(stat -f %A ~/clawd/.env) # stat -f %A for macOS permissions
if [ "$ENV_PERMS" != "600" ]; then
echo " ❌ CRITICAL: .env file has permissions: $ENV_PERMS"
ISSUES=$((ISSUES + 1))
else
echo " ✅ .env file permissions correct"
fi
else
echo " ✅ No .env file found"
fi
echo ""

Additional checks

echo "🔟 Additional Security Checks"

Check for exposed ports

echo " Checking for exposed services..."
EXPOSED=$(lsof -nP -iTCP -sTCP:LISTEN 2>/dev/null | grep -v "127.0.0.1|::1" | wc -l)
if [ "$EXPOSED" -gt 2 ]; then
echo " ⚠️ WARNING: $EXPOSED services listening on public interfaces"
lsof -nP -iTCP -sTCP:LISTEN 2>/dev/null | grep -v "127.0.0.1|::1" | grep "LISTEN"
WARNINGS=$((WARNINGS + 1))
else
echo " ✅ Minimal services exposed"
fi

Check firewall (macOS specific)

FIREWALL_STATE=$(/usr/libexec/ApplicationFirewall/socketfilterfw --getglobalstate 2>/dev/null | grep "Firewall is enabled")
if [ -z "$FIREWALL_STATE" ]; then
echo " ❌ CRITICAL: Firewall not active!"
ISSUES=$((ISSUES + 1))
else
echo " ✅ Firewall active"
fi


