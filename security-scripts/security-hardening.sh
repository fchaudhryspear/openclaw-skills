#!/bin/bash
echo "🔒 MAC MINI SECURITY HARDENING"
echo "=============================="
echo ""

if [ "$EUID" -ne 0 ]; then
echo "❌ Please run with sudo: sudo bash $0"
exit 1
fi

echo "1️⃣ Enabling Firewall..."
/usr/libexec/ApplicationFirewall/socketfilterfw --setglobalstate on
echo " ✅ Firewall enabled"
echo ""

echo "2️⃣ Enabling Stealth Mode (invisible to network scans)..."
/usr/libexec/ApplicationFirewall/socketfilterfw --setstealthmode on
echo " ✅ Stealth mode enabled"
echo ""

echo "3️⃣ Enabling Firewall Logging..."
/usr/libexec/ApplicationFirewall/socketfilterfw --setloggingmode on
/usr/libexec/ApplicationFirewall/socketfilterfw --setloggingopt detail
echo " ✅ Logging enabled"
echo ""

echo "4️⃣ Disabling Screen Sharing..."
launchctl disable system/com.apple.screensharing 2>/dev/null
launchctl bootout system/com.apple.screensharing 2>/dev/null
echo " ✅ Screen Sharing disabled"
echo ""

echo "5️⃣ Disabling Remote Apple Events..."
systemsetup -setremoteappleevents off 2>/dev/null
echo " ✅ Remote Apple Events disabled"
echo ""

WARNING: Disabling SSH will prevent remote login. Review carefully.

echo "6️⃣ Disabling Remote Login (SSH)..."
systemsetup -setremotelogin off 2>/dev/null
echo " ✅ SSH disabled"
echo ""

echo "7️⃣ Requiring password immediately after sleep..."
defaults write com.apple.screensaver askForPassword -int 1
defaults write com.apple.screensaver askForPasswordDelay -int 0
echo " ✅ Immediate password required"
echo ""

echo "8️⃣ Disabling Bluetooth Sharing..."
defaults -currentHost write com.apple.Bluetooth PrefKeyServicesEnabled -bool false
echo " ✅ Bluetooth sharing disabled"
echo ""

echo "9️⃣ Securing Safari (if installed)..."
defaults write com.apple.Safari AutoOpenSafeDownloads -bool false
defaults write com.apple.Safari SendDoNotTrackHTTPHeader -bool true
echo " ✅ Safari hardened"
echo ""

echo "🔟 Setting secure umask..."

Ensure /etc/profile exists or create it. This is a system-wide setting.

if [ -f /etc/profile ]; then
if ! grep -q "umask 027" /etc/profile; then
echo "umask 027" | sudo tee -a /etc/profile > /dev/null
echo " ✅ Secure umask set in /etc/profile"
else
echo " ✅ Secure umask already set in /etc/profile"
fi
else
echo "umask 027" | sudo tee /etc/profile > /dev/null
echo " ✅ Secure umask set by creating /etc/profile"
fi
echo ""

echo "========================================"
echo "🛡️ SECURITY HARDENING COMPLETE"
echo "========================================"
echo ""

echo "Additional manual steps recommended:"
echo "1. Enable Find My Mac in iCloud settings"
echo "2. Review Login Items in System Settings"
echo "3. Enable Lockdown Mode for maximum security"
echo "4. Set firmware password (optional, advanced)"
echo ""
/usr/libexec/ApplicationFirewall/socketfilterfw --getglobalstate
/usr/libexec/ApplicationFirewall/socketfilterfw --getstealthmode
