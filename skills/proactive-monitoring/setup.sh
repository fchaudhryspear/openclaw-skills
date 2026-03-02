#!/bin/bash
# Setup script for Proactive Monitoring Skill
# Run this once to configure everything

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKSPACE="$HOME/.openclaw/workspace"

echo "🔧 Setting up Proactive Monitoring Skill..."

# Create data directories
echo "Creating data directories..."
mkdir -p "$WORKSPACE/data/monitoring"
mkdir -p "$WORKSPACE/logs"

# Check Python dependencies
echo "Checking Python dependencies..."
python3 -c "import psutil, yaml, requests" 2>/dev/null || {
    echo "Installing Python packages..."
    pip3 install psutil pyyaml requests --quiet
}

# Make scripts executable
echo "Setting executable permissions..."
chmod +x "$SCRIPT_DIR/monitor.py"
chmod +x "$SCRIPT_DIR/health-check.sh"

# Test Telegram configuration
if [[ -z "$TELEGRAM_CHAT_ID" ]] || [[ -z "$TELEGRAM_BOT_TOKEN" ]]; then
    echo ""
    echo "⚠️  Telegram credentials not set."
    echo ""
    echo "To enable Telegram alerts, run:"
    echo '  export TELEGRAM_CHAT_ID="your_chat_id"'
    echo '  export TELEGRAM_BOT_TOKEN="your_bot_token"'
    echo ""
    echo "Or add to ~/.zshrc for persistence:"
    echo '  echo "export TELEGRAM_CHAT_ID=your_chat_id" >> ~/.zshrc'
    echo '  echo "export TELEGRAM_BOT_TOKEN=your_bot_token" >> ~/.zshrc'
else
    echo "✅ Telegram credentials detected"
    
    # Test connection
    echo "Testing Telegram connection..."
    response=$(curl -s "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/getMe")
    if echo "$response" | grep -q '"result"'; then
        bot_name=$(echo "$response" | python3 -c "import sys,json; print(json.load(sys.stdin)['result']['username'])")
        echo "✅ Connected to Telegram bot: @$bot_name"
        
        # Send test message
        curl -s -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
            -H "Content-Type: application/json" \
            -d "{
                \"chat_id\": \"$TELEGRAM_CHAT_ID\",
                \"text\": \"🎉 Proactive Monitoring Skill is now active!\\n\\nAlert thresholds:\\n💰 Cost: >$10/day\\n🖥️ CPU: >90%\\n💾 Memory: >95%\\n💿 Disk: <10% free\\n🛡️ Security: SSH brute force detection\\n\\nUse: \`python3 monitor.py --help\` for options\"
            }" > /dev/null
        
        echo "✅ Test alert sent to Telegram"
    else
        echo "❌ Failed to connect to Telegram. Check your credentials."
    fi
fi

# Initialize cost tracking file
if [[ ! -f "$WORKSPACE/data/monitoring/daily_costs.json" ]]; then
    echo "Initializing cost tracking..."
    echo '{}' > "$WORKSPACE/data/monitoring/daily_costs.json"
fi

# Create log file
touch "$WORKSPACE/logs/monitoring.log"

echo ""
echo "🎉 Setup complete!"
echo ""
echo "Next steps:"
echo "  1. Quick test:      python3 monitor.py --once"
echo "  2. Continuous mode: python3 monitor.py --continuous"
echo "  3. Shell check:     ./health-check.sh full"
echo "  4. Dashboard:       open dashboard.html"
echo ""
echo "For help: python3 monitor.py --help"
echo ""
