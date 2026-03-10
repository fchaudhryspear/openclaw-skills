#!/usr/bin/env python3
"""
MO Memory Sync — Ensures context continuity across model switches.

Before expensive tasks: checks if context exists in memory.
After cheap tasks: writes results back to memory.
"""

import json
import os
from pathlib import Path
from datetime import datetime, date


MEMORY_DIR = Path.home() / ".openclaw" / "sandboxes" / "agent-main-f331f052" / "memory"
ACTIVE_PROJECTS = MEMORY_DIR / "active_projects.json"
MODEL_PERF = MEMORY_DIR / "model_performance.json"
MEMORY_MD = Path.home() / ".openclaw" / "sandboxes" / "agent-main-f331f052" / "MEMORY.md"


class MemorySync:
    """Manages memory persistence across model switches."""
    
    def __init__(self):
        self.memory_dir = MEMORY_DIR
        self.memory_dir.mkdir(parents=True, exist_ok=True)
    
    def get_project_context(self, project_id: str) -> dict:
        """Load project context from active_projects.json."""
        try:
            data = json.loads(ACTIVE_PROJECTS.read_text())
            return data.get("projects", {}).get(project_id, {})
        except (FileNotFoundError, json.JSONDecodeError):
            return {}
    
    def update_project(self, project_id: str, updates: dict):
        """Update project state in active_projects.json."""
        try:
            data = json.loads(ACTIVE_PROJECTS.read_text())
        except (FileNotFoundError, json.JSONDecodeError):
            data = {"projects": {}, "last_updated": ""}
        
        if project_id not in data["projects"]:
            data["projects"][project_id] = {"created": datetime.now().isoformat()}
        
        data["projects"][project_id].update(updates)
        data["projects"][project_id]["last_updated"] = datetime.now().isoformat()
        data["last_updated"] = datetime.now().isoformat()
        
        ACTIVE_PROJECTS.write_text(json.dumps(data, indent=2))
    
    def record_model_performance(self, model: str, topic: str, success: bool,
                                  cost: float = 0, latency_ms: float = 0):
        """Track model performance per topic."""
        try:
            data = json.loads(MODEL_PERF.read_text())
        except (FileNotFoundError, json.JSONDecodeError):
            data = {"models": {}, "last_updated": ""}
        
        if model not in data["models"]:
            data["models"][model] = {"success": 0, "failure": 0, "topics": {}}
        
        m = data["models"][model]
        if success:
            m["success"] += 1
        else:
            m["failure"] += 1
        
        if topic not in m["topics"]:
            m["topics"][topic] = {"success": 0, "failure": 0, "total_cost": 0, "avg_latency": 0, "count": 0}
        
        t = m["topics"][topic]
        if success:
            t["success"] += 1
        else:
            t["failure"] += 1
        t["total_cost"] += cost
        t["count"] += 1
        t["avg_latency"] = ((t["avg_latency"] * (t["count"] - 1)) + latency_ms) / t["count"]
        
        data["last_updated"] = datetime.now().isoformat()
        MODEL_PERF.write_text(json.dumps(data, indent=2))
    
    def get_best_model_for_topic(self, topic: str) -> str:
        """Find the best-performing model for a topic."""
        try:
            data = json.loads(MODEL_PERF.read_text())
        except (FileNotFoundError, json.JSONDecodeError):
            return None
        
        best_model = None
        best_rate = 0
        
        for model, perf in data.get("models", {}).items():
            topic_data = perf.get("topics", {}).get(topic, {})
            total = topic_data.get("success", 0) + topic_data.get("failure", 0)
            if total >= 3:  # Minimum sample size
                rate = topic_data["success"] / total
                if rate > best_rate:
                    best_rate = rate
                    best_model = model
        
        return best_model
    
    def write_daily_log(self, content: str):
        """Append to today's daily memory file."""
        today = date.today().isoformat()
        daily_file = self.memory_dir / f"{today}.md"
        
        if daily_file.exists():
            existing = daily_file.read_text()
        else:
            existing = f"# {today}\n\n"
        
        timestamp = datetime.now().strftime("%H:%M")
        existing += f"\n## {timestamp}\n{content}\n"
        daily_file.write_text(existing)
    
    def get_recent_context(self, days: int = 2) -> str:
        """Get recent memory context for model context loading."""
        context_parts = []
        today = date.today()
        
        for i in range(days):
            d = date.fromordinal(today.toordinal() - i)
            daily_file = self.memory_dir / f"{d.isoformat()}.md"
            if daily_file.exists():
                context_parts.append(daily_file.read_text()[:2000])  # Cap at 2000 chars
        
        return "\n---\n".join(context_parts)
    
    def cleanup_stale_projects(self, max_age_days: int = 7):
        """Mark projects as stale if not updated in N days."""
        try:
            data = json.loads(ACTIVE_PROJECTS.read_text())
        except (FileNotFoundError, json.JSONDecodeError):
            return
        
        now = datetime.now()
        for pid, project in data.get("projects", {}).items():
            last = project.get("last_updated", "")
            if last:
                try:
                    last_dt = datetime.fromisoformat(last)
                    if (now - last_dt).days > max_age_days:
                        project["status"] = "stale"
                except ValueError:
                    pass
        
        data["last_updated"] = now.isoformat()
        ACTIVE_PROJECTS.write_text(json.dumps(data, indent=2))


if __name__ == "__main__":
    sync = MemorySync()
    
    # Demo
    sync.record_model_performance("QwenFlash", "simple_qa", True, cost=0.0001, latency_ms=500)
    sync.record_model_performance("Sonnet", "architecture", True, cost=0.05, latency_ms=8000)
    
    best = sync.get_best_model_for_topic("simple_qa")
    print(f"Best model for simple_qa: {best}")
    
    print(f"Recent context length: {len(sync.get_recent_context())} chars")
    print("Memory sync ready.")
