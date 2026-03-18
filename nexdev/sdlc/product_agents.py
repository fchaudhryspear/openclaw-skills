#!/usr/bin/env python3
"""NexDev - Product & Project Management Agents.
Sprint Prioritizer, Feedback Synthesizer, Senior PM, Analytics Reporter."""

import json
from typing import Dict, List
from datetime import datetime


class SprintPrioritizer:
    """Prioritizes backlog items using WSJF (Weighted Shortest Job First)."""
    
    def prioritize(self, items: List[Dict]) -> List[Dict]:
        """Score and sort items by priority."""
        for item in items:
            bv = item.get("business_value", 5)
            tc = item.get("time_criticality", 5)
            rr = item.get("risk_reduction", 3)
            effort = max(item.get("effort", 3), 1)
            item["wsjf_score"] = round((bv + tc + rr) / effort, 2)
            item["priority"] = (
                "P0" if item["wsjf_score"] >= 8 else
                "P1" if item["wsjf_score"] >= 5 else
                "P2" if item["wsjf_score"] >= 3 else "P3"
            )
        return sorted(items, key=lambda x: -x["wsjf_score"])


class FeedbackSynthesizer:
    """Extracts themes and priorities from user feedback."""
    
    def categorize(self, feedback_items: List[str]) -> Dict:
        """Basic keyword-based categorization."""
        categories = {
            "bug": [], "feature_request": [], "performance": [],
            "ux": [], "other": [],
        }
        keywords = {
            "bug": ["bug", "broken", "error", "crash", "fail", "wrong", "fix"],
            "feature_request": ["wish", "want", "would be nice", "add", "feature", "missing", "need"],
            "performance": ["slow", "fast", "speed", "latency", "timeout", "lag"],
            "ux": ["confusing", "hard to", "unclear", "intuitive", "design", "layout"],
        }
        for fb in feedback_items:
            fb_lower = fb.lower()
            matched = False
            for cat, kws in keywords.items():
                if any(kw in fb_lower for kw in kws):
                    categories[cat].append(fb)
                    matched = True
                    break
            if not matched:
                categories["other"].append(fb)
        return categories


class SeniorProjectManager:
    """Converts specs into task breakdowns with estimates."""
    
    def estimate_effort(self, task_description: str) -> int:
        """Rough effort estimation in story points."""
        desc = task_description.lower()
        if any(w in desc for w in ["simple", "minor", "tweak", "typo"]):
            return 1
        if any(w in desc for w in ["crud", "form", "page", "endpoint"]):
            return 3
        if any(w in desc for w in ["auth", "integration", "migration", "refactor"]):
            return 5
        if any(w in desc for w in ["architecture", "redesign", "infrastructure"]):
            return 8
        return 3  # Default


class AnalyticsReporter:
    """Generates dashboard and report specifications."""
    
    def generate_dashboard_spec(self, metrics: List[str], data_source: str) -> Dict:
        """Generate a dashboard specification from metrics list."""
        widgets = []
        for metric in metrics:
            widget_type = "metric" if "count" in metric.lower() or "total" in metric.lower() else "chart"
            widgets.append({
                "type": widget_type,
                "title": metric,
                "data_source": data_source,
                "refresh_interval_seconds": 300,
            })
        return {
            "name": f"Dashboard - {datetime.now().strftime('%Y-%m-%d')}",
            "widgets": widgets,
            "layout": "grid",
            "auto_refresh": True,
        }


if __name__ == "__main__":
    sp = SprintPrioritizer()
    items = [
        {"title": "Fix login bug", "business_value": 9, "time_criticality": 8, "risk_reduction": 5, "effort": 2},
        {"title": "Add dark mode", "business_value": 4, "time_criticality": 2, "risk_reduction": 1, "effort": 5},
        {"title": "Upgrade auth", "business_value": 7, "time_criticality": 6, "risk_reduction": 8, "effort": 3},
    ]
    result = sp.prioritize(items)
    for item in result:
        print(f"  {item['priority']} [{item['wsjf_score']}] {item['title']}")
