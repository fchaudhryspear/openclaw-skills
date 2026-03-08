#!/usr/bin/env python3
"""
MO Phase 1.5 — Cost Dashboard & Reporting
===========================================
Tracks per-query costs, generates daily/weekly reports,
and provides real-time cost visibility for MO routing decisions.

Usage:
    from mo.v2.cost_dashboard import CostTracker
    ct = CostTracker()
    ct.record_query(model="Sonnet", input_tokens=1500, output_tokens=3000, 
                    topic="architecture", task_type="design")
    report = ct.daily_report()
    print(report)
"""

import json
import sqlite3
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime, timedelta, date

from token_estimator import MODEL_COSTS


DB_PATH = Path.home() / ".openclaw" / "workspace" / "mo" / "v2" / "cost_tracking.db"


class CostTracker:
    """Tracks all MO query costs for reporting and optimization."""
    
    def __init__(self, db_path: str = None):
        self.db_path = db_path or str(DB_PATH)
        self._init_db()
    
    def _init_db(self):
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS query_costs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                date TEXT NOT NULL,
                model_alias TEXT NOT NULL,
                tier INTEGER,
                topic TEXT,
                task_type TEXT,
                input_tokens INTEGER,
                output_tokens INTEGER,
                total_tokens INTEGER,
                estimated_cost REAL,
                actual_cost REAL,
                was_escalated INTEGER DEFAULT 0,
                original_model TEXT,
                savings_vs_opus REAL,
                latency_ms REAL
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_costs_date ON query_costs(date)
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_costs_model ON query_costs(model_alias)
        """)
        conn.commit()
        conn.close()
    
    def _calculate_cost(self, model: str, input_tokens: int, output_tokens: int) -> float:
        mc = MODEL_COSTS.get(model, {"input": 1.0, "output": 2.0})
        input_cost = (input_tokens / 1_000_000) * mc["input"]
        output_cost = (output_tokens / 1_000_000) * mc["output"]
        return round(input_cost + output_cost, 6)
    
    def _get_tier(self, model: str) -> int:
        tier_map = {
            "QwenFlash": 1, "GeminiLite": 1,
            "GeminiFlash": 2, "Gemini20Flash": 2, "GrokMini": 2, "QwenCoder": 2,
            "Qwen35": 3, "QwenPlus": 3, "Kimi": 3,
            "Haiku": 4, "QwenMax": 4, "GeminiPro": 4,
            "Grok": 5, "GrokFast": 5, "Sonnet": 5, "opus": 5, "GPT4o": 5,
        }
        return tier_map.get(model, 0)
    
    def record_query(self, model: str, input_tokens: int, output_tokens: int,
                     topic: str = "general", task_type: str = "default",
                     was_escalated: bool = False, original_model: str = None,
                     actual_cost: float = None, latency_ms: float = None):
        """Record a completed query with its cost."""
        now = datetime.now()
        estimated = self._calculate_cost(model, input_tokens, output_tokens)
        
        # Calculate savings vs if we'd used Opus
        opus_cost = self._calculate_cost("opus", input_tokens, output_tokens)
        savings = round(opus_cost - estimated, 6)
        
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            INSERT INTO query_costs (timestamp, date, model_alias, tier, topic, task_type,
                                     input_tokens, output_tokens, total_tokens,
                                     estimated_cost, actual_cost, was_escalated,
                                     original_model, savings_vs_opus, latency_ms)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            now.isoformat(), now.strftime("%Y-%m-%d"), model, self._get_tier(model),
            topic, task_type, input_tokens, output_tokens, input_tokens + output_tokens,
            estimated, actual_cost or estimated, int(was_escalated),
            original_model, savings, latency_ms
        ))
        conn.commit()
        conn.close()
    
    def daily_report(self, target_date: str = None) -> Dict:
        """Generate daily cost report."""
        target = target_date or date.today().isoformat()
        conn = sqlite3.connect(self.db_path)
        
        # Total queries and cost
        row = conn.execute("""
            SELECT COUNT(*), SUM(estimated_cost), SUM(savings_vs_opus),
                   AVG(latency_ms), SUM(total_tokens)
            FROM query_costs WHERE date = ?
        """, (target,)).fetchone()
        
        total_queries = row[0] or 0
        total_cost = round(row[1] or 0, 4)
        total_savings = round(row[2] or 0, 4)
        avg_latency = round(row[3] or 0, 0)
        total_tokens = row[4] or 0
        
        # By model
        by_model = conn.execute("""
            SELECT model_alias, COUNT(*), SUM(estimated_cost), AVG(total_tokens),
                   SUM(savings_vs_opus)
            FROM query_costs WHERE date = ?
            GROUP BY model_alias ORDER BY SUM(estimated_cost) DESC
        """, (target,)).fetchall()
        
        # By tier
        by_tier = conn.execute("""
            SELECT tier, COUNT(*), SUM(estimated_cost), SUM(savings_vs_opus)
            FROM query_costs WHERE date = ?
            GROUP BY tier ORDER BY tier
        """, (target,)).fetchall()
        
        # By topic
        by_topic = conn.execute("""
            SELECT topic, COUNT(*), SUM(estimated_cost), 
                   GROUP_CONCAT(DISTINCT model_alias)
            FROM query_costs WHERE date = ?
            GROUP BY topic ORDER BY SUM(estimated_cost) DESC
            LIMIT 10
        """, (target,)).fetchall()
        
        # Escalation stats
        escalation_row = conn.execute("""
            SELECT COUNT(*), SUM(CASE WHEN was_escalated=1 THEN 1 ELSE 0 END)
            FROM query_costs WHERE date = ?
        """, (target,)).fetchone()
        
        conn.close()
        
        escalation_rate = 0
        if escalation_row[0] > 0:
            escalation_rate = round(escalation_row[1] / escalation_row[0] * 100, 1)
        
        return {
            "date": target,
            "summary": {
                "total_queries": total_queries,
                "total_cost": total_cost,
                "total_savings_vs_opus": total_savings,
                "savings_pct": round(total_savings / (total_cost + total_savings) * 100, 1) if (total_cost + total_savings) > 0 else 0,
                "avg_cost_per_query": round(total_cost / total_queries, 6) if total_queries > 0 else 0,
                "total_tokens": total_tokens,
                "avg_latency_ms": avg_latency,
                "escalation_rate": escalation_rate,
            },
            "by_model": [
                {
                    "model": row[0],
                    "queries": row[1],
                    "cost": round(row[2], 4),
                    "avg_tokens": int(row[3]),
                    "savings": round(row[4], 4),
                }
                for row in by_model
            ],
            "by_tier": [
                {
                    "tier": row[0],
                    "queries": row[1],
                    "cost": round(row[2], 4),
                    "savings": round(row[3], 4),
                }
                for row in by_tier
            ],
            "by_topic": [
                {
                    "topic": row[0],
                    "queries": row[1],
                    "cost": round(row[2], 4),
                    "models_used": row[3],
                }
                for row in by_topic
            ],
        }
    
    def weekly_report(self) -> Dict:
        """Generate weekly cost report."""
        conn = sqlite3.connect(self.db_path)
        week_ago = (date.today() - timedelta(days=7)).isoformat()
        
        rows = conn.execute("""
            SELECT date, COUNT(*), SUM(estimated_cost), SUM(savings_vs_opus)
            FROM query_costs WHERE date >= ?
            GROUP BY date ORDER BY date
        """, (week_ago,)).fetchall()
        
        total_cost = sum(r[2] or 0 for r in rows)
        total_savings = sum(r[3] or 0 for r in rows)
        total_queries = sum(r[1] or 0 for r in rows)
        
        conn.close()
        
        return {
            "period": f"{week_ago} to {date.today().isoformat()}",
            "total_queries": total_queries,
            "total_cost": round(total_cost, 4),
            "total_savings_vs_opus": round(total_savings, 4),
            "avg_daily_cost": round(total_cost / max(len(rows), 1), 4),
            "daily_breakdown": [
                {
                    "date": row[0],
                    "queries": row[1],
                    "cost": round(row[2], 4),
                    "savings": round(row[3], 4),
                }
                for row in rows
            ]
        }
    
    def format_report(self, report: Dict) -> str:
        """Format a report dict into readable text for Discord/chat."""
        s = report.get("summary", {})
        lines = [
            f"📊 **MO Cost Report — {report.get('date', 'Weekly')}**",
            f"",
            f"**Summary:**",
            f"• Queries: {s.get('total_queries', 0)}",
            f"• Total Cost: ${s.get('total_cost', 0):.4f}",
            f"• Saved vs Opus: ${s.get('total_savings_vs_opus', 0):.4f} ({s.get('savings_pct', 0)}%)",
            f"• Avg/Query: ${s.get('avg_cost_per_query', 0):.6f}",
            f"• Escalation Rate: {s.get('escalation_rate', 0)}%",
            f"",
            f"**By Model:**",
        ]
        
        for m in report.get("by_model", [])[:5]:
            lines.append(f"• {m['model']}: {m['queries']} queries, ${m['cost']:.4f}")
        
        if report.get("by_topic"):
            lines.append(f"\n**Top Topics:**")
            for t in report.get("by_topic", [])[:5]:
                lines.append(f"• {t['topic']}: {t['queries']} queries, ${t['cost']:.4f}")
        
        return "\n".join(lines)


if __name__ == "__main__":
    ct = CostTracker()
    
    # Simulate some queries
    ct.record_query("QwenFlash", 500, 200, topic="simple_qa", task_type="simple_qa")
    ct.record_query("Sonnet", 2000, 5000, topic="architecture", task_type="architecture")
    ct.record_query("QwenCoder", 1500, 3000, topic="code_gen", task_type="code_gen")
    ct.record_query("GeminiFlash", 800, 400, topic="summarize", task_type="summarize")
    ct.record_query("Qwen35", 3000, 6000, topic="code_gen", task_type="refactor",
                    was_escalated=True, original_model="QwenCoder")
    
    report = ct.daily_report()
    print(ct.format_report(report))
