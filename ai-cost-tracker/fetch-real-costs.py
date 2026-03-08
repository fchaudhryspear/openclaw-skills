#!/usr/bin/env python3
"""
Fetch REAL costs from provider APIs (not estimates)
Requires API keys with billing access
"""

import json
import os
from datetime import datetime, timedelta
import requests

OUTPUT_PATH = os.path.expanduser("~/.openclaw/workspace/ai-cost-tracker/logs/real-costs.json")

def get_anthropic_usage(api_key, days=7):
    """Fetch actual usage from Anthropic API (requires billing permissions)."""
    # Note: Anthropic's public API doesn't expose billing data yet
    # This requires manual CSV export from console for now
    
    return {
        "provider": "anthropic",
        "status": "manual_export_required",
        "note": "Use platform.claude.com → Settings → Billing → Export CSV",
        "workspaces_found": ["clawbot_mm_3_2026", "myclawdbot_mm"],
        "instructions": """
To track real costs automatically:
1. Go to https://console.anthropic.com/settings/billing
2. Click 'Export Usage' for the past month
3. Save as ~/.openclaw/workspace/ai-cost-tracker/logs/anthropic-usage.csv
4. Run: python3 fetch-real-costs.py --parse
"""
    }

def get_google_usage(api_key, days=7):
    """Fetch Google Cloud billing data."""
    url = f"https://billingbudgets.googleapis.com/v1/projects/{os.getenv('GOOGLE_CLOUD_PROJECT')}/billingAccounts/*/budgets"
    headers = {"Authorization": f"Bearer {api_key}"}
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            return {"provider": "google", "data": response.json()}
    except Exception as e:
        return {"provider": "google", "error": str(e)}
    
    return {"provider": "google", "status": "no_access"}

def get_openai_usage(api_key, days=7):
    """Fetch OpenAI usage data."""
    url = f"https://api.openai.com/v1/dashboard/billing/usage?start_date={(datetime.now()-timedelta(days=days)).strftime('%Y-%m-%d')}&end_date={datetime.now().strftime('%Y-%m-%d')}"
    headers = {"Authorization": f"Bearer {api_key}"}
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            data = response.json()
            total = data.get("total_usage", 0) / 100  # Convert from cents
            return {
                "provider": "openai",
                "total_cost": total,
                "period_days": days
            }
    except Exception as e:
        return {"provider": "openai", "error": str(e)}
    
    return {"provider": "openai", "status": "no_access"}

def parse_anthropic_csv(csv_path):
    """Parse exported Anthropic usage CSV."""
    import csv
    
    results = {}
    with open(os.path.expanduser(csv_path)) as f:
        reader = csv.DictReader(f)
        for row in reader:
            date = row.get("date", "")[:10]  # YYYY-MM-DD
            workspace = row.get("workspace_name", "unknown")
            cost = float(row.get("cost", 0))
            
            if date not in results:
                results[date] = {"total": 0, "by_workspace": {}}
            
            results[date]["total"] += cost
            if workspace not in results[date]["by_workspace"]:
                results[date]["by_workspace"][workspace] = 0
            results[date]["by_workspace"][workspace] += cost
    
    return results

def generate_summary(all_costs):
    """Generate combined cost summary."""
    total = sum(d.get("total_cost", 0) for d in all_costs.values())
    
    summary = {
        "generated_at": datetime.now().isoformat(),
        "total_cost_this_month": total,
        "by_provider": all_costs,
        "recommendations": []
    }
    
    # Add recommendations based on spending patterns
    if total > 50:
        summary["recommendations"].append("⚠️ High monthly spend — review model selection")
    if any("anthropic" in k.lower() and v.get("total_cost", 0) > 30 for k, v in all_costs.items()):
        summary["recommendations"].append("💡 Consider using cheaper models (Sonnet vs Opus)")
    
    return summary

def main():
    print("\n🔍 Fetching real costs from providers...\n")
    
    all_costs = {}
    
    # Get API keys from environment or Keychain
    anthropic_key = os.getenv("ANTHROPIC_API_KEY")
    google_key = os.getenv("GOOGLE_API_KEY")
    openai_key = os.getenv("OPENAI_API_KEY")
    
    # Fetch from each provider
    if anthropic_key:
        all_costs["anthropic"] = get_anthropic_usage(anthropic_key)
    else:
        all_costs["anthropic"] = get_anthropic_usage(None)
    
    if google_key:
        all_costs["google"] = get_google_usage(google_key)
    
    if openai_key:
        all_costs["openai"] = get_openai_usage(openai_key)
    
    # Check for CSV exports
    csv_path = os.path.expanduser("~/.openclaw/workspace/ai-cost-tracker/logs/anthropic-usage.csv")
    if os.path.exists(csv_path):
        all_costs["anthropic_csv"] = parse_anthropic_csv(csv_path)
    
    # Generate and save summary
    summary = generate_summary(all_costs)
    
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, 'w') as f:
        json.dump(summary, f, indent=2)
    
    print("📊 COST SUMMARY:")
    print(f"   Total tracked: ${summary['total_cost_this_month']:.2f}")
    print(f"   Providers checked: {len(all_costs)}")
    if summary.get('recommendations'):
        print("\n   Recommendations:")
        for rec in summary['recommendations']:
            print(f"   {rec}")
    
    print(f"\n📁 Full report: {OUTPUT_PATH}")
    print()

if __name__ == "__main__":
    import sys
    if "--parse-csv" in sys.argv:
        csv_path = input("Enter path to Anthropic usage CSV: ")
        results = parse_anthropic_csv(csv_path)
        print(json.dumps(results, indent=2))
    else:
        main()
