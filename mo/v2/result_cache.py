#!/usr/bin/env python3
"""
MO v2.1 Result Cache — Avoid redundant LLM work across pipeline stages.

Stores stage results keyed by content hash. TTL-based expiry.
Uses SQLite for persistence across sessions.
"""

import hashlib
import json
import sqlite3
import time
from pathlib import Path
from typing import Optional, Dict


DB_PATH = Path.home() / ".openclaw" / "workspace" / "mo" / "v2" / "result_cache.db"


class ResultCache:
    """Persistent result cache with TTL expiry."""
    
    def __init__(self, db_path: str = None, default_ttl: int = 86400):
        self.db_path = db_path or str(DB_PATH)
        self.default_ttl = default_ttl  # 24 hours
        self._init_db()
    
    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS cache (
                key TEXT PRIMARY KEY,
                stage TEXT NOT NULL,
                project_id TEXT,
                result TEXT NOT NULL,
                model TEXT,
                tokens_used INTEGER DEFAULT 0,
                cost REAL DEFAULT 0.0,
                created_at REAL NOT NULL,
                ttl INTEGER NOT NULL,
                hits INTEGER DEFAULT 0
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_cache_stage ON cache(stage)
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_cache_project ON cache(project_id)
        """)
        conn.commit()
        conn.close()
    
    def _hash_key(self, stage: str, input_data: str, project_id: str = None) -> str:
        raw = f"{stage}:{project_id or ''}:{input_data}"
        return hashlib.sha256(raw.encode()).hexdigest()[:32]
    
    def get(self, stage: str, input_data: str, project_id: str = None) -> Optional[Dict]:
        """Retrieve cached result if available and not expired."""
        key = self._hash_key(stage, input_data, project_id)
        conn = sqlite3.connect(self.db_path)
        row = conn.execute(
            "SELECT result, model, tokens_used, cost, created_at, ttl, hits FROM cache WHERE key = ?",
            (key,)
        ).fetchone()
        
        if row is None:
            conn.close()
            return None
        
        result, model, tokens, cost, created, ttl, hits = row
        
        # Check TTL
        if time.time() - created > ttl:
            conn.execute("DELETE FROM cache WHERE key = ?", (key,))
            conn.commit()
            conn.close()
            return None
        
        # Update hit count
        conn.execute("UPDATE cache SET hits = hits + 1 WHERE key = ?", (key,))
        conn.commit()
        conn.close()
        
        return {
            "result": json.loads(result),
            "model": model,
            "tokens_used": tokens,
            "cost": cost,
            "age_seconds": int(time.time() - created),
            "hits": hits + 1,
            "cached": True,
        }
    
    def put(self, stage: str, input_data: str, result: any,
            project_id: str = None, model: str = None,
            tokens_used: int = 0, cost: float = 0.0,
            ttl: int = None):
        """Store a result in the cache."""
        key = self._hash_key(stage, input_data, project_id)
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            INSERT OR REPLACE INTO cache (key, stage, project_id, result, model, tokens_used, cost, created_at, ttl, hits)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0)
        """, (key, stage, project_id, json.dumps(result), model, tokens_used, cost, time.time(), ttl or self.default_ttl))
        conn.commit()
        conn.close()
    
    def invalidate(self, stage: str = None, project_id: str = None):
        """Invalidate cache entries by stage or project."""
        conn = sqlite3.connect(self.db_path)
        if stage and project_id:
            conn.execute("DELETE FROM cache WHERE stage = ? AND project_id = ?", (stage, project_id))
        elif stage:
            conn.execute("DELETE FROM cache WHERE stage = ?", (stage,))
        elif project_id:
            conn.execute("DELETE FROM cache WHERE project_id = ?", (project_id,))
        else:
            conn.execute("DELETE FROM cache")
        conn.commit()
        conn.close()
    
    def cleanup(self):
        """Remove expired entries."""
        conn = sqlite3.connect(self.db_path)
        conn.execute("DELETE FROM cache WHERE (? - created_at) > ttl", (time.time(),))
        conn.commit()
        conn.close()
    
    def stats(self) -> Dict:
        """Get cache statistics."""
        conn = sqlite3.connect(self.db_path)
        total = conn.execute("SELECT COUNT(*) FROM cache").fetchone()[0]
        total_hits = conn.execute("SELECT SUM(hits) FROM cache").fetchone()[0] or 0
        total_cost_saved = conn.execute(
            "SELECT SUM(cost * hits) FROM cache WHERE hits > 0"
        ).fetchone()[0] or 0.0
        
        by_stage = conn.execute(
            "SELECT stage, COUNT(*), SUM(hits), SUM(cost * hits) FROM cache GROUP BY stage"
        ).fetchall()
        
        conn.close()
        
        return {
            "total_entries": total,
            "total_hits": total_hits,
            "estimated_cost_saved": round(total_cost_saved, 6),
            "by_stage": [
                {"stage": s, "entries": c, "hits": h, "cost_saved": round(cs or 0, 6)}
                for s, c, h, cs in by_stage
            ],
        }


if __name__ == "__main__":
    cache = ResultCache()
    
    # Demo
    cache.put("pm_analysis", "Build a task manager app", {"specs": "..."}, 
              project_id="DEMO", model="Kimi", tokens_used=5000, cost=0.0025)
    
    hit = cache.get("pm_analysis", "Build a task manager app", project_id="DEMO")
    print(f"Cache hit: {hit is not None}")
    print(f"Stats: {json.dumps(cache.stats(), indent=2)}")
