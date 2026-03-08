#!/usr/bin/env python3
"""
MO Phase 1.3 — Explicit User Feedback Loops
=============================================
Captures user feedback (good/bad/rating) and feeds it into the
MO learning loop to improve model selection over time.

Trigger words: /goodresponse, /badresponse, /rate <1-5>
Emoji reactions also captured via platform hooks.

Usage:
    from mo.v2.user_feedback import FeedbackCollector
    fc = FeedbackCollector()
    fc.record_feedback(model="Sonnet", topic="architecture", rating=5, query_hash="abc123")
    recommendations = fc.get_model_recommendations("architecture")
"""

import json
import sqlite3
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime, timedelta


DB_PATH = Path.home() / ".openclaw" / "workspace" / "mo" / "v2" / "feedback.db"


class FeedbackCollector:
    """Collects and analyzes user feedback for MO learning."""
    
    def __init__(self, db_path: str = None):
        self.db_path = db_path or str(DB_PATH)
        self._init_db()
    
    def _init_db(self):
        """Initialize SQLite database."""
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                model_alias TEXT NOT NULL,
                model_full TEXT,
                topic TEXT,
                task_type TEXT,
                rating INTEGER CHECK(rating BETWEEN 1 AND 5),
                feedback_type TEXT DEFAULT 'explicit',
                query_hash TEXT,
                query_preview TEXT,
                confidence_score REAL,
                estimated_cost REAL,
                actual_cost REAL,
                notes TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS model_scores (
                model_alias TEXT NOT NULL,
                topic TEXT NOT NULL,
                weighted_score REAL DEFAULT 0.0,
                total_feedback INTEGER DEFAULT 0,
                last_updated TEXT,
                PRIMARY KEY (model_alias, topic)
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_feedback_model ON feedback(model_alias)
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_feedback_topic ON feedback(topic)
        """)
        conn.commit()
        conn.close()
    
    def record_feedback(self, model: str, rating: int, 
                        topic: str = "general",
                        task_type: str = None,
                        query_hash: str = None,
                        query_preview: str = None,
                        confidence_score: float = None,
                        estimated_cost: float = None,
                        actual_cost: float = None,
                        feedback_type: str = "explicit",
                        model_full: str = None,
                        notes: str = None):
        """
        Record a piece of user feedback.
        
        Args:
            model: Model alias (e.g., "Sonnet")
            rating: 1-5 (1=terrible, 5=excellent)
            topic: Topic/domain of the query
            feedback_type: "explicit" (user typed), "reaction" (emoji), "implicit" (no complaint = good)
        """
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            INSERT INTO feedback (timestamp, model_alias, model_full, topic, task_type,
                                  rating, feedback_type, query_hash, query_preview,
                                  confidence_score, estimated_cost, actual_cost, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            datetime.now().isoformat(), model, model_full, topic, task_type,
            rating, feedback_type, query_hash, query_preview,
            confidence_score, estimated_cost, actual_cost, notes
        ))
        
        # Update rolling model score
        self._update_model_score(conn, model, topic, rating)
        conn.commit()
        conn.close()
    
    def _update_model_score(self, conn, model: str, topic: str, new_rating: int):
        """Update weighted rolling score for model+topic pair."""
        row = conn.execute(
            "SELECT weighted_score, total_feedback FROM model_scores WHERE model_alias=? AND topic=?",
            (model, topic)
        ).fetchone()
        
        decay = 0.95  # Recent feedback weighted more heavily
        
        if row:
            old_score, count = row
            # Exponential moving average
            new_score = old_score * decay + (new_rating / 5.0) * (1 - decay)
            conn.execute("""
                UPDATE model_scores 
                SET weighted_score=?, total_feedback=?, last_updated=?
                WHERE model_alias=? AND topic=?
            """, (new_score, count + 1, datetime.now().isoformat(), model, topic))
        else:
            conn.execute("""
                INSERT INTO model_scores (model_alias, topic, weighted_score, total_feedback, last_updated)
                VALUES (?, ?, ?, 1, ?)
            """, (model, topic, new_rating / 5.0, datetime.now().isoformat()))
    
    def get_model_recommendations(self, topic: str, top_n: int = 3) -> List[Dict]:
        """
        Get recommended models for a topic based on feedback history.
        
        Returns sorted list of models with scores.
        """
        conn = sqlite3.connect(self.db_path)
        rows = conn.execute("""
            SELECT model_alias, weighted_score, total_feedback, last_updated
            FROM model_scores
            WHERE topic = ? AND total_feedback >= 3
            ORDER BY weighted_score DESC
            LIMIT ?
        """, (topic, top_n)).fetchall()
        conn.close()
        
        return [
            {
                "model": row[0],
                "score": round(row[1], 3),
                "feedback_count": row[2],
                "last_updated": row[3],
            }
            for row in rows
        ]
    
    def get_model_score(self, model: str, topic: str) -> Optional[float]:
        """Get current weighted score for a specific model+topic."""
        conn = sqlite3.connect(self.db_path)
        row = conn.execute(
            "SELECT weighted_score FROM model_scores WHERE model_alias=? AND topic=?",
            (model, topic)
        ).fetchone()
        conn.close()
        return row[0] if row else None
    
    def get_feedback_summary(self, days: int = 7) -> Dict:
        """Get summary of recent feedback."""
        conn = sqlite3.connect(self.db_path)
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()
        
        total = conn.execute(
            "SELECT COUNT(*) FROM feedback WHERE timestamp >= ?", (cutoff,)
        ).fetchone()[0]
        
        avg_rating = conn.execute(
            "SELECT AVG(rating) FROM feedback WHERE timestamp >= ?", (cutoff,)
        ).fetchone()[0]
        
        by_model = conn.execute("""
            SELECT model_alias, COUNT(*), AVG(rating), 
                   SUM(CASE WHEN rating >= 4 THEN 1 ELSE 0 END) as good,
                   SUM(CASE WHEN rating <= 2 THEN 1 ELSE 0 END) as bad
            FROM feedback WHERE timestamp >= ?
            GROUP BY model_alias
            ORDER BY AVG(rating) DESC
        """, (cutoff,)).fetchall()
        
        conn.close()
        
        return {
            "period_days": days,
            "total_feedback": total,
            "avg_rating": round(avg_rating, 2) if avg_rating else None,
            "by_model": [
                {
                    "model": row[0],
                    "count": row[1],
                    "avg_rating": round(row[2], 2),
                    "good_pct": round(row[3] / row[1] * 100, 1) if row[1] > 0 else 0,
                    "bad_pct": round(row[4] / row[1] * 100, 1) if row[1] > 0 else 0,
                }
                for row in by_model
            ]
        }
    
    def parse_feedback_command(self, message: str) -> Optional[Dict]:
        """
        Parse user feedback from chat messages.
        
        Recognized formats:
            /goodresponse           → rating 5
            /badresponse            → rating 1
            /rate 4                 → rating 4
            /rate 3 architecture    → rating 3, topic override
        """
        msg = message.strip().lower()
        
        if msg == "/goodresponse":
            return {"rating": 5, "feedback_type": "explicit"}
        elif msg == "/badresponse":
            return {"rating": 1, "feedback_type": "explicit"}
        elif msg.startswith("/rate"):
            parts = msg.split()
            if len(parts) >= 2:
                try:
                    rating = int(parts[1])
                    rating = max(1, min(5, rating))
                    topic = parts[2] if len(parts) >= 3 else None
                    return {"rating": rating, "topic": topic, "feedback_type": "explicit"}
                except ValueError:
                    pass
        
        return None


if __name__ == "__main__":
    fc = FeedbackCollector()
    
    # Simulate some feedback
    fc.record_feedback("Sonnet", 5, topic="architecture", query_preview="Design auth system")
    fc.record_feedback("QwenCoder", 4, topic="code_gen", query_preview="Write Python class")
    fc.record_feedback("QwenFlash", 3, topic="simple_qa", query_preview="What is Docker?")
    fc.record_feedback("Sonnet", 4, topic="architecture", query_preview="Microservice design")
    fc.record_feedback("Sonnet", 5, topic="architecture", query_preview="Database schema")
    
    print("Recommendations for 'architecture':")
    for rec in fc.get_model_recommendations("architecture"):
        print(f"  {rec['model']}: score={rec['score']}, n={rec['feedback_count']}")
    
    print(f"\nFeedback summary: {json.dumps(fc.get_feedback_summary(), indent=2)}")
