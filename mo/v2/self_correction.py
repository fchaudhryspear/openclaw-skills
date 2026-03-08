#!/usr/bin/env python3
"""
MO Phase 2.2 — Self-Correction for Routing Logic
==================================================
Monitors MO's own routing decisions, identifies suboptimal patterns,
and proposes/applies adjustments to improve over time.
"""

import json
import sqlite3
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from collections import defaultdict


DB_PATH = Path.home() / ".openclaw" / "workspace" / "mo" / "v2" / "self_correction.db"


class SelfCorrectionEngine:
    """Analyzes MO routing history and identifies improvement opportunities."""
    
    def __init__(self, db_path: str = None):
        self.db_path = db_path or str(DB_PATH)
        self._init_db()
    
    def _init_db(self):
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS routing_decisions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                query_hash TEXT,
                topic TEXT,
                task_type TEXT,
                complexity INTEGER,
                model_selected TEXT NOT NULL,
                tier_selected INTEGER,
                confidence REAL,
                was_escalated INTEGER DEFAULT 0,
                escalation_count INTEGER DEFAULT 0,
                final_model TEXT,
                estimated_cost REAL,
                actual_cost REAL,
                success INTEGER DEFAULT 1,
                latency_ms REAL
            );
            CREATE TABLE IF NOT EXISTS correction_proposals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                pattern_type TEXT NOT NULL,
                description TEXT NOT NULL,
                current_behavior TEXT,
                proposed_change TEXT,
                impact_estimate TEXT,
                status TEXT DEFAULT 'proposed',
                applied_at TEXT,
                result TEXT
            );
            CREATE TABLE IF NOT EXISTS routing_rules_overrides (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                topic TEXT,
                task_type TEXT,
                preferred_model TEXT,
                avoid_model TEXT,
                min_tier INTEGER,
                max_tier INTEGER,
                reason TEXT,
                created_at TEXT,
                expires_at TEXT,
                active INTEGER DEFAULT 1
            );
            CREATE INDEX IF NOT EXISTS idx_decisions_topic ON routing_decisions(topic);
            CREATE INDEX IF NOT EXISTS idx_decisions_model ON routing_decisions(model_selected);
        """)
        conn.commit()
        conn.close()
    
    def record_decision(self, topic: str, task_type: str, complexity: int,
                        model: str, tier: int, confidence: float = None,
                        was_escalated: bool = False, escalation_count: int = 0,
                        final_model: str = None, estimated_cost: float = None,
                        actual_cost: float = None, success: bool = True,
                        latency_ms: float = None, query_hash: str = None):
        """Record a routing decision for analysis."""
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            INSERT INTO routing_decisions 
            (timestamp, query_hash, topic, task_type, complexity, model_selected, tier_selected,
             confidence, was_escalated, escalation_count, final_model, estimated_cost,
             actual_cost, success, latency_ms)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            datetime.now().isoformat(), query_hash, topic, task_type, complexity,
            model, tier, confidence, int(was_escalated), escalation_count,
            final_model or model, estimated_cost, actual_cost, int(success), latency_ms
        ))
        conn.commit()
        conn.close()
    
    def analyze(self, days: int = 7) -> Dict:
        """
        Analyze routing history and identify patterns needing correction.
        Returns analysis with proposed corrections.
        """
        conn = sqlite3.connect(self.db_path)
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()
        
        analysis = {
            "period_days": days,
            "timestamp": datetime.now().isoformat(),
            "patterns": [],
            "proposals": [],
        }
        
        # Pattern 1: Excessive escalations — model consistently failing for a topic
        escalation_pattern = conn.execute("""
            SELECT topic, model_selected, COUNT(*) as total,
                   SUM(was_escalated) as escalated,
                   CAST(SUM(was_escalated) AS FLOAT) / COUNT(*) as escalation_rate
            FROM routing_decisions
            WHERE timestamp >= ?
            GROUP BY topic, model_selected
            HAVING COUNT(*) >= 5 AND escalation_rate > 0.3
            ORDER BY escalation_rate DESC
        """, (cutoff,)).fetchall()
        
        for row in escalation_pattern:
            analysis["patterns"].append({
                "type": "excessive_escalation",
                "topic": row[0],
                "model": row[1],
                "total_queries": row[2],
                "escalations": row[3],
                "rate": round(row[4], 3),
            })
            analysis["proposals"].append({
                "type": "avoid_model",
                "description": f"Model '{row[1]}' has {row[4]*100:.0f}% escalation rate for '{row[0]}'. "
                              f"Consider routing directly to higher tier.",
                "action": {"topic": row[0], "avoid_model": row[1]},
            })
        
        # Pattern 2: Unnecessary expensive models — high-tier used for simple tasks
        overspec_pattern = conn.execute("""
            SELECT topic, model_selected, tier_selected, AVG(confidence), COUNT(*)
            FROM routing_decisions
            WHERE timestamp >= ? AND tier_selected >= 4 AND confidence >= 0.9 AND success = 1
            GROUP BY topic, model_selected
            HAVING COUNT(*) >= 3
        """, (cutoff,)).fetchall()
        
        for row in overspec_pattern:
            analysis["patterns"].append({
                "type": "overspecced_model",
                "topic": row[0],
                "model": row[1],
                "tier": row[2],
                "avg_confidence": round(row[3], 3),
                "count": row[4],
            })
            analysis["proposals"].append({
                "type": "downgrade_tier",
                "description": f"Tier {row[2]} model '{row[1]}' consistently scores {row[3]:.0%} confidence "
                              f"for '{row[0]}'. A cheaper model may suffice.",
                "action": {"topic": row[0], "max_tier": row[2] - 1},
            })
        
        # Pattern 3: Low confidence clusters — topic that consistently struggles
        low_conf_pattern = conn.execute("""
            SELECT topic, AVG(confidence), MIN(confidence), COUNT(*),
                   SUM(CASE WHEN success=0 THEN 1 ELSE 0 END) as failures
            FROM routing_decisions
            WHERE timestamp >= ? AND confidence IS NOT NULL
            GROUP BY topic
            HAVING AVG(confidence) < 0.75 AND COUNT(*) >= 5
        """, (cutoff,)).fetchall()
        
        for row in low_conf_pattern:
            analysis["patterns"].append({
                "type": "low_confidence_topic",
                "topic": row[0],
                "avg_confidence": round(row[1], 3),
                "min_confidence": round(row[2], 3),
                "count": row[3],
                "failures": row[4],
            })
            analysis["proposals"].append({
                "type": "upgrade_tier",
                "description": f"Topic '{row[0]}' has avg confidence {row[1]:.0%} across {row[3]} queries. "
                              f"Consider using higher-tier models.",
                "action": {"topic": row[0], "min_tier": 4},
            })
        
        # Pattern 4: Cost waste — same result achievable cheaper
        cost_pattern = conn.execute("""
            SELECT topic, model_selected, tier_selected, 
                   AVG(actual_cost) as avg_cost, COUNT(*) as total,
                   AVG(confidence) as avg_conf
            FROM routing_decisions
            WHERE timestamp >= ? AND actual_cost > 0 AND success = 1
            GROUP BY topic, model_selected
            HAVING COUNT(*) >= 3
            ORDER BY topic, avg_cost DESC
        """, (cutoff,)).fetchall()
        
        # Group by topic to find cheaper alternatives
        topic_costs = defaultdict(list)
        for row in cost_pattern:
            topic_costs[row[0]].append({
                "model": row[1], "tier": row[2],
                "avg_cost": row[3], "count": row[4], "avg_conf": row[5]
            })
        
        for topic, models in topic_costs.items():
            if len(models) >= 2:
                expensive = models[0]
                cheapest = min(models, key=lambda m: m["avg_cost"])
                if expensive["avg_cost"] > cheapest["avg_cost"] * 2 and cheapest["avg_conf"] >= 0.8:
                    analysis["patterns"].append({
                        "type": "cost_waste",
                        "topic": topic,
                        "expensive_model": expensive["model"],
                        "cheap_model": cheapest["model"],
                        "cost_ratio": round(expensive["avg_cost"] / max(cheapest["avg_cost"], 0.0001), 1),
                    })
                    analysis["proposals"].append({
                        "type": "prefer_cheaper",
                        "description": f"For '{topic}', '{cheapest['model']}' is {expensive['avg_cost']/max(cheapest['avg_cost'],0.0001):.1f}x cheaper "
                                      f"than '{expensive['model']}' with similar confidence ({cheapest['avg_conf']:.0%}).",
                        "action": {"topic": topic, "preferred_model": cheapest["model"]},
                    })
        
        conn.close()
        
        # Store proposals
        self._store_proposals(analysis["proposals"])
        
        return analysis
    
    def apply_proposal(self, proposal_id: int) -> bool:
        """Apply a correction proposal as a routing rule override."""
        conn = sqlite3.connect(self.db_path)
        
        proposal = conn.execute(
            "SELECT * FROM correction_proposals WHERE id=?", (proposal_id,)
        ).fetchone()
        
        if not proposal:
            conn.close()
            return False
        
        try:
            action = json.loads(proposal[4])  # proposed_change column
        except (json.JSONDecodeError, TypeError):
            conn.close()
            return False
        
        # Create routing rule override
        conn.execute("""
            INSERT INTO routing_rules_overrides 
            (topic, task_type, preferred_model, avoid_model, min_tier, max_tier, reason, created_at, expires_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            action.get("topic"), action.get("task_type"),
            action.get("preferred_model"), action.get("avoid_model"),
            action.get("min_tier"), action.get("max_tier"),
            f"Auto-correction proposal #{proposal_id}",
            datetime.now().isoformat(),
            (datetime.now() + timedelta(days=14)).isoformat(),  # 2-week trial
        ))
        
        conn.execute("""
            UPDATE correction_proposals SET status='applied', applied_at=? WHERE id=?
        """, (datetime.now().isoformat(), proposal_id))
        
        conn.commit()
        conn.close()
        return True
    
    def get_active_overrides(self, topic: str = None) -> List[Dict]:
        """Get active routing rule overrides."""
        conn = sqlite3.connect(self.db_path)
        now = datetime.now().isoformat()
        
        if topic:
            rows = conn.execute("""
                SELECT * FROM routing_rules_overrides
                WHERE active=1 AND (expires_at IS NULL OR expires_at > ?) AND topic=?
            """, (now, topic)).fetchall()
        else:
            rows = conn.execute("""
                SELECT * FROM routing_rules_overrides
                WHERE active=1 AND (expires_at IS NULL OR expires_at > ?)
            """, (now,)).fetchall()
        
        conn.close()
        
        return [
            {
                "id": r[0], "topic": r[1], "task_type": r[2],
                "preferred_model": r[3], "avoid_model": r[4],
                "min_tier": r[5], "max_tier": r[6], "reason": r[7],
            }
            for r in rows
        ]
    
    def _store_proposals(self, proposals: List[Dict]):
        """Store correction proposals in DB."""
        conn = sqlite3.connect(self.db_path)
        for p in proposals:
            conn.execute("""
                INSERT INTO correction_proposals (created_at, pattern_type, description, proposed_change)
                VALUES (?, ?, ?, ?)
            """, (datetime.now().isoformat(), p["type"], p["description"], json.dumps(p.get("action", {}))))
        conn.commit()
        conn.close()
    
    def format_analysis(self, analysis: Dict) -> str:
        """Format analysis for chat display."""
        lines = ["🔄 **MO Self-Correction Analysis**", ""]
        
        if not analysis["patterns"]:
            lines.append("No patterns requiring correction detected. ✅")
            return "\n".join(lines)
        
        lines.append(f"Found **{len(analysis['patterns'])}** patterns in last {analysis['period_days']} days:")
        
        for p in analysis["patterns"]:
            ptype = p["type"]
            if ptype == "excessive_escalation":
                lines.append(f"• ⚠️ **{p['model']}** escalates {p['rate']*100:.0f}% for '{p['topic']}' ({p['total_queries']} queries)")
            elif ptype == "overspecced_model":
                lines.append(f"• 💰 **{p['model']}** (Tier {p['tier']}) overkill for '{p['topic']}' (avg conf {p['avg_confidence']:.0%})")
            elif ptype == "low_confidence_topic":
                lines.append(f"• 📉 Topic '{p['topic']}' struggling: avg conf {p['avg_confidence']:.0%}, {p['failures']} failures")
            elif ptype == "cost_waste":
                lines.append(f"• 🔥 '{p['expensive_model']}' is {p['cost_ratio']}x more expensive than '{p['cheap_model']}' for '{p['topic']}'")
        
        if analysis["proposals"]:
            lines.append(f"\n**Proposed corrections:** {len(analysis['proposals'])}")
            for i, p in enumerate(analysis["proposals"]):
                lines.append(f"  {i+1}. {p['description'][:100]}")
        
        return "\n".join(lines)


if __name__ == "__main__":
    engine = SelfCorrectionEngine()
    
    # Simulate routing history
    for _ in range(10):
        engine.record_decision("code_gen", "code_gen", 3, "QwenCoder", 2,
                              confidence=0.85, success=True, actual_cost=0.001)
    for _ in range(6):
        engine.record_decision("simple_qa", "simple_qa", 1, "Sonnet", 5,
                              confidence=0.95, success=True, actual_cost=0.05)
    for _ in range(5):
        engine.record_decision("debug", "debug", 2, "GeminiFlash", 2,
                              confidence=0.6, was_escalated=True, success=True, actual_cost=0.002)
    
    analysis = engine.analyze(days=30)
    print(engine.format_analysis(analysis))
    print("\n✅ Self-Correction Engine tested")
