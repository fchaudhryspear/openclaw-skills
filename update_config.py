
import json
import os
import shutil
import subprocess

# 1. Setup Paths
config_path = os.path.expanduser("~/.openclaw/openclaw.json")
backup_path = config_path + ".bak.v3"

# 2. Create Safety Backup
if os.path.exists(config_path):
    shutil.copy(config_path, backup_path)
    print(f"✅ Backup created at: {backup_path}")
else:
    print("❌ Config file not found. Run 'openclaw onboard' first.")
    exit(1)

# 3. Load Current Config
with open(config_path, 'r') as f:
    config = json.load(f)

# ==========================================
# 4. APPLY MODEL ORCHESTRATOR v3.0 LOGIC
# ==========================================
# --- A. Clean Up Old Providers ---
# Remove Qwen/Ollama/Legacy providers to prevent conflicts
if "models" in config and "providers" in config["models"]:
    for key in ["qwen-portal", "ollama", "openai"]:
        if key in config["models"]["providers"]:
            del config["models"]["providers"][key]

# --- B. Define New Provider Stack ---
new_providers = {
    # 1. ANTHROPIC (The "Operator" - UI/Complex Logic)
    "anthropic": {
        "api": "anthropic-messages",
        "baseUrl": "https://api.anthropic.com/v1",
        "apiKey": "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",
        "models": [
            {
                "id": "claude-3-5-sonnet-latest",
                "name": "Claude 3.5 Sonnet",
                "reasoning": True,
                "input": ["text", "image"], # MODIFIED: Removed "tool_code"
                "contextWindow": 200000,
                "maxTokens": 8192
            }
        ]
    },
    # 2. GOOGLE (The "Data Sifter" - Video/Long Context)
    # Note: Removed "api" key to fix the "Invalid Input" error you saw earlier.
    "google": {
        "baseUrl": "https://generativelanguage.googleapis.com/v1beta",
        "apiKey": "AIzaSyCj-CqJABlMaSWbJ5HHzyWEhMn0TyYDVtg",
        "models": [
            {
                "id": "gemini-2.5-flash",
                "name": "Gemini 2.5 Flash",
                "reasoning": True,
                "input": ["text", "image"], # MODIFIED: Removed "video", "audio"
                "contextWindow": 1000000,
                "maxTokens": 8192
            }
        ]
    },
    # 3. xAI (The "News Desk" - Real-time)
    "xai": {
        "api": "openai-completions",
        "baseUrl": "https://api.x.ai/v1",
        "apiKey": "xai-ZrOCURTzyXMdJN8s7HwGQqAdWH6CvEpnfEjIRRjwk1B9zsuKp1v5Uxm3KBX6yJe0JAkJVC6ZlnsCr1I3",
        "models": [
            {
                "id": "grok-beta", # "grok-3" is usually accessed via this ID in API currently
                "name": "Grok 3 (Beta)",
                "reasoning": False,
                "input": ["text"],
                "contextWindow": 131072,
                "maxTokens": 8192
            }
        ]
    }
}

# Add/Update new providers
if "models" not in config:
    config["models"] = {}
if "providers" not in config["models"]:
    config["models"]["providers"] = {}
config["models"]["providers"].update(new_providers)

# --- C. Update Agent Defaults & Aliases ---
if "agents" not in config:
    config["agents"] = {"defaults": {}}
if "defaults" not in config["agents"]:
    config["agents"]["defaults"] = {}

# Primary model
config["agents"]["defaults"]["model"] = {
    "primary": "xai/grok-beta",
    "fallbacks": ["google/gemini-2.5-flash", "anthropic/claude-3-5-sonnet-latest"]
}

# Aliases
config["agents"]["defaults"]["models"] = {
    "google/gemini-1.5-flash": {}, # Keep if needed, otherwise remove
    "google/gemini-live-2.5-flash": {}, # Keep if needed, otherwise remove
    "moonshot/kimi-k2.5": {"alias": "Kimi"},
    "xai/grok-beta": {"alias": "GrokMini"},
    "anthropic/claude-3-5-sonnet-latest": {"alias": "Sonnet"},
    "google/gemini-2.5-flash": {"alias": "GeminiFlash"}
}
# Remove old aliases if they exist for qwen
if "qwen-portal/coder-model" in config["agents"]["defaults"]["models"]:
    del config["agents"]["defaults"]["models"]["qwen-portal/coder-model"]
if "qwen-portal/vision-model" in config["agents"]["defaults"]["models"]:
    del config["agents"]["defaults"]["models"]["qwen-portal/vision-model"]


# --- D. Enable Gateway Restart ---
if "commands" not in config:
    config["commands"] = {}
config["commands"]["restart"] = True

print("✅ Configuration updated in memory.")

# 5. Write Updated Config
with open(config_path, 'w') as f:
    json.dump(config, f, indent=2)
print(f"✅ Updated configuration written to: {config_path}")

# 6. Restart Gateway
try:
    print("Attempting to restart OpenClaw Gateway...")
    subprocess.run(["openclaw", "gateway", "restart"], check=True)
    print("✅ OpenClaw Gateway restart initiated.")
except subprocess.CalledProcessError as e:
    print(f"❌ Failed to restart OpenClaw Gateway: {e}")
    print("Please restart OpenClaw manually if the changes don't take effect.")
except FileNotFoundError:
    print("❌ 'openclaw' command not found. Please ensure OpenClaw CLI is in your PATH.")
    print("Please restart OpenClaw manually if the changes don't take effect.")
