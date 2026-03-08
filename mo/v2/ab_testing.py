#!/usr/bin/env python3
"""
MO Phase 2.4 — A/B Testing Framework
======================================
Occasionally routes the same query type to two different models,
compares outcomes, and logs the winner. Validates self-correction.
"""

import json
import random
import sqlite3
import hashlib
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta


DB_PATH = Path.home() / ".openclaw" / "workspace" / "mo" / "v2" / "ab_tests.db"


class ABTestFramework:
    """A/B testing for model routing decisions."""
    
    def __init__(self, db_path: str = None, sample_rate: float = 0.05):
        self.db_path = db_path or str(DB_PATH)
        self.sample_rate = sample_rate  # 5% of queries enter A/B tests
        self._init_db()
    
    def _init_db(self):
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS experiments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                description TEXT,
                model_a TEXT NOT NULL,
                model_b TEXT NOT NULL,
                topic TEXT,
                task_type TEXT,
                sample_rate REAL DEFAULT 0.05,
                status TEXT DEFAULT 'active',
                created_at TEXT,
                ended_at TEXT,
                winner TEXT,
                total_trials INTEGER DEFAULT 0,
                a_wins INTEGER DEFAULT 0,
                b_wins INTEGER DEFAULT 0,
                ties INTEGER DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS trial_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                experiment_id INTEGER NOT NULL,
                timestamp TEXT NOT NULL,
                query_hash TEXT,
                model_a_confidence REAL,
                model_b_confidence REAL,
                model_a_cost REAL,
                model_b_cost REAL,
                model_a_latency REAL,
                model_b_latency REAL,
                winner TEXT,
                reason TEXT,
                FOREIGN KEY (experiment_id) REFERENCES experiments(id)
            );
        """)
        conn.commit()
        conn.close()
    
    def create_experiment(self, name: str, model_a: str, model_b: str,
                          topic: str = None, task_type: str = None,
                          description: str = None, sample_rate: float = None) -> int:
        """Create a new A/B experiment."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.execute("""
            INSERT INTO experiments (name, description, model_a, model_b, topic, task_type,
                                    sample_rate, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (name, description or f"Compare {model_a} vs {model_b}",
              model_a, model_b, topic, task_type,
              sample_rate or self.sample_rate, datetime.now().isoformat()))
        exp_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return exp_id
    
    def should_ab_test(self, topic: str = None, task_type: str = None) -> Optional[Dict]:
        """
        Check if this query should be A/B tested.
        Returns experiment info if yes, None if no.
        """
        if random.random() > self.sample_rate:
            return None
        
        conn = sqlite3.connect(self.db_path)
        
        # Find active experiment matching this query
        if topic:
            exp = conn.execute("""
                SELECT id, name, model_a, model_b, sample_rate
                FROM experiments WHERE status='active' AND (topic=? OR topic IS NULL)
                ORDER BY RANDOM() LIMIT 1
            """, (topic,)).fetchone()
        else:
            exp = conn.execute("""
                SELECT id, name, model_a, model_b, sample_rate
                FROM experiments WHERE status='active'
                ORDER BY RANDOM() LIMIT 1
            """).fetchone()
        
        conn.close()
        
        if exp:
            return {
                "experiment_id": exp[0],
                "name": exp[1],
                "model_a": exp[2],
                "model_b": exp[3],
            }
        return None
    
    def record_trial(self, experiment_id: int, query_hash: str,
                     a_confidence: float, b_confidence: float,
                     a_cost: float = 0, b_cost: float = 0,
                     a_latency: float = 0, b_latency: float = 0) -> Dict:
        """
        Record results of an A/B trial.
        Determines winner based on confidence (primary) and cost (tiebreaker).
        """
        # Determine winner
        conf_diff = abs(a_confidence - b_confidence)
        
        if conf_diff < 0.05:  # Within 5% = tie on quality, break by cost
            if a_cost < b_cost * 0.8:  # A is 20%+ cheaper
                winner = "a"
                reason = "similar_quality_cheaper"
            elif b_cost < a_cost * 0.8:
                winner = "b"
                reason = "similar_quality_cheaper"
            else:
                winner = "tie"
                reason = "similar_quality_similar_cost"
        elif a_confidence > b_confidence:
            winner = "a"
            reason = "higher_confidence"
        else:
            winner = "b"
            reason = "higher_confidence"
        
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            INSERT INTO trial_results
            (experiment_id, timestamp, query_hash, model_a_confidence, model_b_confidence,
             model_a_cost, model_b_cost, model_a_latency, model_b_latency, winner, reason)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (experiment_id, datetime.now().isoformat(), query_hash,
              a_confidence, b_confidence, a_cost, b_cost, a_latency, b_latency,
              winner, reason))
        
        # Update experiment counters
        if winner == "a":
            conn.execute("UPDATE experiments SET total_trials=total_trials+1, a_wins=a_wins+1 WHERE id=?", (experiment_id,))
        elif winner == "b":
            conn.execute("UPDATE experiments SET total_trials=total_trials+1, b_wins=b_wins+1 WHERE id=?", (experiment_id,))
        else:
            conn.execute("UPDATE experiments SET total_trials=total_trials+1, ties=ties+1 WHERE id=?", (experiment_id,))
        
        conn.commit()
        conn.close()
        
        return {"winner": winner, "reason": reason}
    
    def get_experiment_results(self, experiment_id: int = None, name: str = None) -> Optional[Dict]:
        """Get results for an experiment."""
        conn = sqlite3.connect(self.db_path)
        
        if experiment_id:
            exp = conn.execute("SELECT * FROM experiments WHERE id=?", (experiment_id,)).fetchone()
        elif name:
            exp = conn.execute("SELECT * FROM experiments WHERE name=?", (name,)).fetchone()
        else:
            conn.close()
            return None
        
        if not exp:
            conn.close()
            return None
        
        total = exp[12] or 1
        result = {
            "id": exp[0], "name": exp[1], "description": exp[2],
            "model_a": exp[3], "model_b": exp[4],
            "topic": exp[5], "status": exp[7],
            "total_trials": exp[12],
            "model_a_wins": exp[13], "model_a_win_rate": round(exp[13] / total, 3),
            "model_b_wins": exp[14], "model_b_win_rate": round(exp[14] / total, 3),
            "ties": exp[15], "tie_rate": round(exp[15] / total, 3),
            "winner": exp[16],
            "statistical_significance": total >= 30,
        }
        
        # Determine winner if enough trials
        if total >= 30:
            if result["model_a_win_rate"] > 0.6:
                result["conclusion"] = f"{exp[3]} is clearly better"
            elif result["model_b_win_rate"] > 0.6:
                result["conclusion"] = f"{exp[4]} is clearly better"
            else:
                result["conclusion"] = "No clear winner — models are comparable"
        else:
            result["conclusion"] = f"Need {30 - total} more trials for significance"
        
        conn.close()
        return result
    
    def end_experiment(self, experiment_id: int):
        """End an experiment and declare a winner."""
        result = self.get_experiment_results(experiment_id)
        if not result:
            return
        
        winner = None
        if result["model_a_win_rate"] > result["model_b_win_rate"]:
            winner = result["model_a"]
        elif result["model_b_win_rate"] > result["model_a_win_rate"]:
            winner = result["model_b"]
        
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            UPDATE experiments SET status='ended', ended_at=?, winner=? WHERE id=?
        """, (datetime.now().isoformat(), winner, experiment_id))
        conn.commit()
        conn.close()
    
    def list_experiments(self, status: str = None) -> List[Dict]:
        """List all experiments."""
        conn = sqlite3.connect(self.db_path)
        if status:
            rows = conn.execute("SELECT * FROM experiments WHERE status=?", (status,)).fetchall()
        else:
            rows = conn.execute("SELECT * FROM experiments").fetchall()
        conn.close()
        
        return [
            {
                "id": r[0], "name": r[1], "model_a": r[3], "model_b": r[4],
                "topic": r[5], "status": r[7], "trials": r[12],
                "a_wins": r[13], "b_wins": r[14], "winner": r[16],
            }
            for r in rows
        ]
    
    def format_results(self, experiment_id: int) -> str:
        """Format experiment results for chat."""
        r = self.get_experiment_results(experiment_id)
        if not r:
            return "Experiment not found"
        
        bar_a = "█" * int(r["model_a_win_rate"] * 20)
        bar_b = "█" * int(r["model_b_win_rate"] * 20)
        
        return (
            f"🧪 **A/B Test: {r['name']}**\n"
            f"Status: {r['status']} | Trials: {r['total_trials']}\n\n"
            f"**{r['model_a']}** {bar_a} {r['model_a_win_rate']*100:.0f}% ({r['model_a_wins']} wins)\n"
            f"**{r['model_b']}** {bar_b} {r['model_b_win_rate']*100:.0f}% ({r['model_b_wins']} wins)\n"
            f"Ties: {r['ties']} ({r['tie_rate']*100:.0f}%)\n\n"
            f"**Conclusion:** {r['conclusion']}"
        )


if __name__ == "__main__":
    ab = ABTestFramework(sample_rate=1.0)  # 100% for testing
    
    # Create experiment
    exp_id = ab.create_experiment(
        "sonnet_vs_qwen35_architecture",
        model_a="Sonnet", model_b="Qwen35",
        topic="architecture"
    )
    
    # Simulate trials
    for i in range(35):
        a_conf = random.uniform(0.82, 0.96)
        b_conf = random.uniform(0.78, 0.92)
        ab.record_trial(exp_id, f"query-{i}",
                       a_confidence=a_conf, b_confidence=b_conf,
                       a_cost=0.05, b_cost=0.01)
    
    print(ab.format_results(exp_id))
    print("\n✅ A/B Testing Framework tested")
