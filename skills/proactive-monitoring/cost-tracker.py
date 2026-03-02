#!/usr/bin/env python3
"""
Cost Tracker Utility
Track and log AI/API usage costs manually or from billing APIs.
Integrates with the proactive monitoring system.
"""

import os
import sys
import json
from datetime import datetime, timedelta
from pathlib import Path
import argparse

DATA_DIR = Path.home() / ".openclaw/workspace/data/monitoring"
COSTS_FILE = DATA_DIR / "daily_costs.json"
USAGE_LOG = DATA_DIR / "api_usage.log"

def ensure_dirs():
    """Ensure data directories exist."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)

def get_today_str():
    """Get today's date as ISO string."""
    return datetime.now().date().isoformat()

def load_costs():
    """Load cost data from file."""
    ensure_dirs()
    if COSTS_FILE.exists():
        with open(COSTS_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_costs(costs):
    """Save cost data to file."""
    ensure_dirs()
    with open(COSTS_FILE, 'w') as f:
        json.dump(costs, f, indent=2)

def log_usage(service: str, model: str, cost: float, tokens: int = 0):
    """Log API usage to the usage log file."""
    ensure_dirs()
    
    timestamp = datetime.now().isoformat()
    log_line = f"{timestamp}|{service}|{model}|{tokens}|${cost:.4f}\n"
    
    with open(USAGE_LOG, 'a') as f:
        f.write(log_line)
    
    print(f"✅ Logged: {service}/{model} - ${cost:.4f} ({tokens} tokens)")
    
    # Also update daily totals
    costs = load_costs()
    today = get_today_str()
    
    if today not in costs:
        costs[today] = {'total': 0.0, 'services': {}}
    
    costs[today]['total'] += cost
    
    if service not in costs[today]['services']:
        costs[today]['services'][service] = 0.0
    
    costs[today]['services'][service] += cost
    
    save_costs(costs)

def get_daily_cost(date_str: str = None):
    """Get total cost for a specific date (defaults to today)."""
    costs = load_costs()
    target_date = date_str or get_today_str()
    return costs.get(target_date, {}).get('total', 0.0)

def get_service_breakdown(date_str: str = None):
    """Get cost breakdown by service."""
    costs = load_costs()
    target_date = date_str or get_today_str()
    return costs.get(target_date, {}).get('services', {})

def get_weekly_summary():
    """Get summary for the last 7 days."""
    costs = load_costs()
    today = datetime.now().date()
    week_data = []
    
    for i in range(7):
        date = today - timedelta(days=i)
        date_str = date.isoformat()
        if date_str in costs:
            week_data.append({
                'date': date_str,
                'total': costs[date_str]['total'],
                'services': costs[date_str].get('services', {})
            })
    
    return week_data

def print_summary(days: int = 7):
    """Print cost summary."""
    costs = load_costs()
    today = datetime.now().date()
    
    print(f"\n{'='*60}")
    print(f"AI/API Cost Summary")
    print(f"{'='*60}\n")
    
    total_7d = 0.0
    daily_costs = []
    
    # Last N days
    for i in range(days):
        date = today - timedelta(days=i)
        date_str = date.isoformat()
        
        if date_str in costs:
            day_total = costs[date_str]['total']
            total_7d += day_total
            daily_costs.append(day_total)
            
            marker = ""
            if day_total > 10:
                marker = " 🚨 OVER BUDGET"
            elif day_total > 8:
                marker = " ⚠️ Close"
            
            print(f"{date_str}: ${day_total:.2f}{marker}")
        else:
            daily_costs.append(0.0)
            print(f"{date_str}: $0.00 (no data)")
    
    print(f"\n{'-'*60}")
    
    if daily_costs:
        avg_daily = sum(daily_costs) / len(daily_costs)
        max_daily = max(daily_costs)
        min_daily = min(daily_costs)
        
        print(f"Total ({days} days):     ${total_7d:.2f}")
        print(f"Average daily:           ${avg_daily:.2f}")
        print(f"Highest day:             ${max_daily:.2f}")
        print(f"Lowest day:              ${min_daily:.2f}")
    
    # Project monthly cost
    if daily_costs and sum(daily_costs) > 0:
        projected_monthly = avg_daily * 30
        print(f"\nProjected monthly:       ${projected_monthly:.2f}")
        
        if projected_monthly > 300:
            print("⚠️  Warning: High monthly projection!")
    
    print(f"{'='*60}\n")

def clear_today():
    """Reset today's costs (for testing or correction)."""
    costs = load_costs()
    today = get_today_str()
    
    if today in costs:
        deleted = costs[today]
        del costs[today]
        save_costs(costs)
        print(f"Cleared {today}: ${deleted['total']:.2f}")
    else:
        print("No data to clear for today")

def compare_dates(date1: str, date2: str):
    """Compare costs between two dates."""
    c1 = get_daily_cost(date1)
    c2 = get_daily_cost(date2)
    
    diff = c2 - c1
    pct_change = (diff / c1 * 100) if c1 > 0 else 0
    
    print(f"\nComparison: {date1} vs {date2}")
    print(f"  {date1}: ${c1:.2f}")
    print(f"  {date2}: ${c2:.2f}")
    print(f"  Change:  ${diff:+.2f} ({pct_change:+.1f}%)")

def main():
    parser = argparse.ArgumentParser(description='Track AI/API costs')
    parser.add_argument('--log', '-l', nargs=3, metavar=('SERVICE', 'MODEL', 'COST'),
                        help='Log usage: cost-tracker --log openrouter qwen-72b 0.05')
    parser.add_argument('--today', '-t', action='store_true', help='Show today\'s cost')
    parser.add_argument('--summary', '-s', type=int, nargs='?', default=0, const=7,
                        metavar='DAYS', help='Show cost summary (default: 7 days)')
    parser.add_argument('--breakdown', '-b', action='store_true', help='Show service breakdown')
    parser.add_argument('--clear', '-c', action='store_true', help='Clear today\'s costs')
    parser.add_argument('--compare', nargs=2, metavar=('DATE1', 'DATE2'),
                        help='Compare two dates: 2024-01-01 2024-01-02')
    
    args = parser.parse_args()
    
    if args.log:
        service, model, cost = args.log
        try:
            cost = float(cost)
            log_usage(service, model, cost)
        except ValueError:
            print("Error: Cost must be a number")
            sys.exit(1)
    
    elif args.today:
        cost = get_daily_cost()
        print(f"Today's cost: ${cost:.2f}")
        threshold = 10.00
        if cost > threshold:
            print(f"⚠️  OVER BUDGET by ${cost - threshold:.2f}")
    
    elif args.summary > 0:
        print_summary(args.summary)
    
    elif args.breakdown:
        breakdown = get_service_breakdown()
        if breakdown:
            print(f"\nService breakdown for {get_today_str()}:\n")
            for service, cost in sorted(breakdown.items(), key=lambda x: -x[1]):
                print(f"  {service}: ${cost:.2f}")
            print(f"\n  Total: ${sum(breakdown.values()):.2f}")
        else:
            print("No cost data for today")
    
    elif args.clear:
        confirm = input("Clear today's costs? [y/N] ")
        if confirm.lower() == 'y':
            clear_today()
        else:
            print("Cancelled")
    
    elif args.compare:
        compare_dates(*args.compare)
    
    else:
        parser.print_help()

if __name__ == '__main__':
    main()
