#!/usr/bin/env python3
"""
MO Phase 2.1 — Temporal & Conversational Context Learning
===========================================================
Analyzes conversation threads and recent interactions to favor models
that performed well in the same context. Maintains session continuity.
"""

import json
import sqlite3
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from collections import defaultdict


DB_PATH = Path.home() / ".openclaw" / "workspace" / "mo" / "v2" / "temporal_context.db"


class TemporalContextEngine:
    """Tracks conversation context and learns model preferences over time."""
    
    def __init__(self, db_path: str = None):
        self.db_path = db_path or str(DB_PATH)
        self._init_db()
        self._session_cache: Dict[str, Dict] = {}
    
    def _init_db(self):
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS conversation_turns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                topic TEXT,
                task_type TEXT,
                model_used TEXT NOT NULL,
                confidence REAL,
                success INTEGER DEFAULT 1,
                tokens_used INTEGER DEFAULT 0,
                cost REAL DEFAULT 0.0
            );
            CREATE TABLE IF NOT EXISTS topic_streaks (
                topic TEXT NOT NULL,
                model TEXT NOT NULL,
                consecutive_successes INTEGER DEFAULT 0,
                total_uses INTEGER DEFAULT 0,
                avg_confidence REAL DEFAULT 0.0,
                last_used TEXT,
                PRIMARY KEY (topic, model)
            );
            CREATE TABLE IF NOT EXISTS session_context (
                session_id TEXT PRIMARY KEY,
                current_topic TEXT,
                current_model TEXT,
                turn_count INTEGER DEFAULT 0,
                topic_switches INTEGER DEFAULT 0,
                started_at TEXT,
                last_active TEXT,
                context_blob TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_turns_session ON conversation_turns(session_id);
            CREATE INDEX IF NOT EXISTS idx_turns_topic ON conversation_turns(topic);
        """)
        conn.commit()
        conn.close()
    
    def record_turn(self, session_id: str, topic: str, model: str,
                    task_type: str = None, confidence: float = None,
                    success: bool = True, tokens: int = 0, cost: float = 0.0):
        """Record a conversation turn for learning."""
        conn = sqlite3.connect(self.db_path)
        now = datetime.now().isoformat()
        
        # Record turn
        conn.execute("""
            INSERT INTO conversation_turns 
            (session_id, timestamp, topic, task_type, model_used, confidence, success, tokens_used, cost)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (session_id, now, topic, task_type, model, confidence, int(success), tokens, cost))
        
        # Update topic streak
        streak = conn.execute(
            "SELECT consecutive_successes, total_uses, avg_confidence FROM topic_streaks WHERE topic=? AND model=?",
            (topic, model)
        ).fetchone()
        
        if streak:
            consec = streak[0] + 1 if success else 0
            total = streak[1] + 1
            avg_conf = (streak[2] * streak[1] + (confidence or 0.8)) / total if confidence else streak[2]
            conn.execute("""
                UPDATE topic_streaks SET consecutive_successes=?, total_uses=?, avg_confidence=?, last_used=?
                WHERE topic=? AND model=?
            """, (consec, total, avg_conf, now, topic, model))
        else:
            conn.execute("""
                INSERT INTO topic_streaks (topic, model, consecutive_successes, total_uses, avg_confidence, last_used)
                VALUES (?, ?, ?, 1, ?, ?)
            """, (topic, model, 1 if success else 0, confidence or 0.8, now))
        
        # Update session context
        session = conn.execute(
            "SELECT current_topic, turn_count FROM session_context WHERE session_id=?",
            (session_id,)
        ).fetchone()
        
        if session:
            topic_switch = 1 if session[0] != topic else 0
            conn.execute("""
                UPDATE session_context SET current_topic=?, current_model=?, turn_count=turn_count+1,
                topic_switches=topic_switches+?, last_active=?
                WHERE session_id=?
            """, (topic, model, topic_switch, now, session_id))
        else:
            conn.execute("""
                INSERT INTO session_context (session_id, current_topic, current_model, turn_count, started_at, last_active)
                VALUES (?, ?, ?, 1, ?, ?)
            """, (session_id, topic, model, now, now))
        
        conn.commit()
        conn.close()
    
    def get_context_recommendation(self, session_id: str, topic: str) -> Optional[str]:
        """
        Get model recommendation based on conversational context.
        
        Priority:
        1. Same session, same topic → use same model (continuity)
        2. Topic streak → use model with best streak
        3. Recent history → use model that worked recently for this topic
        """
        conn = sqlite3.connect(self.db_path)
        
        # 1. Session continuity — same topic, same model
        session = conn.execute(
            "SELECT current_topic, current_model, turn_count FROM session_context WHERE session_id=?",
            (session_id,)
        ).fetchone()
        
        if session and session[0] == topic and session[2] > 0:
            conn.close()
            return session[1]  # Keep using same model for continuity
        
        # 2. Topic streak — best performing model for this topic
        streak = conn.execute("""
            SELECT model, consecutive_successes, avg_confidence, total_uses
            FROM topic_streaks WHERE topic=? AND total_uses >= 3
            ORDER BY avg_confidence DESC, consecutive_successes DESC
            LIMIT 1
        """, (topic,)).fetchone()
        
        if streak and streak[2] >= 0.8:
            conn.close()
            return streak[0]
        
        # 3. Recent history — what worked in last 24h for this topic
        cutoff = (datetime.now() - timedelta(hours=24)).isoformat()
        recent = conn.execute("""
            SELECT model_used, AVG(confidence), COUNT(*)
            FROM conversation_turns
            WHERE topic=? AND timestamp >= ? AND success=1
            GROUP BY model_used
            ORDER BY AVG(confidence) DESC
            LIMIT 1
        """, (topic, cutoff)).fetchone()
        
        conn.close()
        
        if recent:
            return recent[0]
        
        return None  # No context-based recommendation
    
    def get_session_summary(self, session_id: str) -> Dict:
        """Get summary of a session's context."""
        conn = sqlite3.connect(self.db_path)
        
        session = conn.execute(
            "SELECT * FROM session_context WHERE session_id=?", (session_id,)
        ).fetchone()
        
        if not session:
            conn.close()
            return {"session_id": session_id, "exists": False}
        
        turns = conn.execute("""
            SELECT topic, model_used, confidence, success
            FROM conversation_turns WHERE session_id=?
            ORDER BY timestamp DESC LIMIT 10
        """, (session_id,)).fetchall()
        
        conn.close()
        
        return {
            "session_id": session_id,
            "current_topic": session[1],
            "current_model": session[2],
            "turn_count": session[3],
            "topic_switches": session[4],
            "recent_turns": [
                {"topic": t[0], "model": t[1], "confidence": t[2], "success": bool(t[3])}
                for t in turns
            ]
        }
    
    def get_topic_insights(self) -> List[Dict]:
        """Get insights on all tracked topics."""
        conn = sqlite3.connect(self.db_path)
        rows = conn.execute("""
            SELECT topic, model, consecutive_successes, total_uses, avg_confidence
            FROM topic_streaks ORDER BY topic, avg_confidence DESC
        """).fetchall()
        conn.close()
        
        topics = defaultdict(list)
        for row in rows:
            topics[row[0]].append({
                "model": row[1], "streak": row[2],
                "uses": row[3], "avg_confidence": round(row[4], 3)
            })
        
        return dict(topics)


if __name__ == "__main__":
    engine = TemporalContextEngine()
    
    # Simulate a conversation
    sid = "test-session-001"
    engine.record_turn(sid, "architecture", "Sonnet", confidence=0.92, success=True)
    engine.record_turn(sid, "architecture", "Sonnet", confidence=0.88, success=True)
    engine.record_turn(sid, "architecture", "Sonnet", confidence=0.95, success=True)
    engine.record_turn(sid, "code_gen", "QwenCoder", confidence=0.85, success=True)
    
    rec = engine.get_context_recommendation(sid, "architecture")
    print(f"Recommendation for architecture: {rec}")
    
    rec2 = engine.get_context_recommendation(sid, "code_gen")
    print(f"Recommendation for code_gen: {rec2}")
    
    print(f"\nSession summary: {json.dumps(engine.get_session_summary(sid), indent=2)}")
    print(f"\n✅ Temporal Context Engine tested")
