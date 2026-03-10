#!/usr/bin/env python3
"""
MO Cost Monitor — Tracks daily costs and sends Telegram alerts.

Designed to run as a cron job:
    0 9 * * * cd ~/.openclaw/workspace/mo/v2 && python3 cost_monitor.py daily
    0 9 * * 1 cd ~/.openclaw/workspace/mo/v2 && python3 cost_monitor.py weekly
"""

import json
import os
import sys
import argparse
import subprocess
from pathlib import Path
from datetime import datetime, date, timedelta

sys.path.insert(0, str(Path(__file__).parent))

from cost_dashboard import CostTracker
from result_cache import ResultCache

BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "-5263006024")

DAILY_BUDGET = 20.0   # $20/day alert threshold
WEEKLY_BUDGET = 100.0  # $100/week alert threshold


def send_telegram(message: str):
    """Send a message via Telegram."""
    if not BOT_TOKEN:
        print(f"[No bot token] {message}")
        return
    
    import urllib.request
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = json.dumps({"chat_id": CHAT_ID, "text": message}).encode()
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    try:
        urllib.request.urlopen(req, timeout=10)
    except Exception as e:
        print(f"Telegram send failed: {e}")


def daily_report():
    """Generate and send daily cost report."""
    tracker = CostTracker()
    cache = ResultCache()
    
    report = tracker.daily_report()
    formatted = tracker.format_report(report)
    
    cache_stats = cache.stats()
    
    total_cost = report.get("total_cost", 0)
    
    lines = [
        f"📊 MO Daily Cost Report — {date.today().isoformat()}",
        formatted,
        f"\n💾 Cache: {cache_stats['total_entries']} entries, "
        f"{cache_stats['total_hits']} hits, "
        f"~${cache_stats['estimated_cost_saved']:.4f} saved",
    ]
    
    if total_cost > DAILY_BUDGET:
        lines.insert(0, f"⚠️ BUDGET ALERT: ${total_cost:.2f} exceeds ${DAILY_BUDGET:.2f}/day limit!")
    
    message = "\n".join(lines)
    print(message)
    
    if total_cost > DAILY_BUDGET * 0.8:  # Alert at 80% of budget
        send_telegram(message)
    
    return message


def weekly_report():
    """Generate and send weekly cost summary."""
    tracker = CostTracker()
    cache = ResultCache()
    
    # Aggregate 7 days
    total = 0
    daily_costs = []
    for i in range(7):
        d = date.today() - timedelta(days=i)
        report = tracker.daily_report()  # Note: CostTracker may need date param
        cost = report.get("total_cost", 0)
        total += cost
        daily_costs.append((d.isoformat(), cost))
    
    cache_stats = cache.stats()
    
    lines = [
        f"📊 MO Weekly Cost Summary — Week ending {date.today().isoformat()}",
        f"Total: ${total:.4f}",
        f"Daily average: ${total/7:.4f}",
        "",
    ]
    
    for d, c in daily_costs:
        bar = "█" * int(c * 100) if c > 0 else "░"
        lines.append(f"  {d}: ${c:.4f} {bar}")
    
    lines.extend([
        f"\n💾 Cache savings: ~${cache_stats['estimated_cost_saved']:.4f}",
    ])
    
    if total > WEEKLY_BUDGET:
        lines.insert(0, f"⚠️ WEEKLY BUDGET ALERT: ${total:.2f} exceeds ${WEEKLY_BUDGET:.2f}/week!")
    
    message = "\n".join(lines)
    print(message)
    send_telegram(message)
    
    return message


def threshold_check():
    """Quick check if any thresholds need adjusting."""
    from dynamic_thresholds import ThresholdManager
    tm = ThresholdManager()
    
    # Check if any task types have unusual routing patterns
    from user_feedback import FeedbackCollector
    fc = FeedbackCollector()
    
    topics = ["code_gen", "architecture", "debug", "simple_qa", "security_audit"]
    adjustments = []
    
    for topic in topics:
        recs = fc.get_model_recommendations(topic)
        if recs and recs[0].get("avg_rating", 0) < 3.0:
            adjustments.append(f"  ⚠️ {topic}: top model rated {recs[0]['avg_rating']:.1f}/5 — consider escalating")
    
    if adjustments:
        message = "🔧 MO Threshold Check\n" + "\n".join(adjustments)
        print(message)
        send_telegram(message)
    else:
        print("✅ All thresholds look good")


def main():
    parser = argparse.ArgumentParser(description="MO Cost Monitor")
    sub = parser.add_subparsers(dest="command")
    sub.add_parser("daily", help="Daily cost report")
    sub.add_parser("weekly", help="Weekly cost summary")
    sub.add_parser("check", help="Threshold check")
    
    args = parser.parse_args()
    
    if args.command == "daily":
        daily_report()
    elif args.command == "weekly":
        weekly_report()
    elif args.command == "check":
        threshold_check()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
