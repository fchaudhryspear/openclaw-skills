#!/usr/bin/env python3
"""
Knowledge Retention Manager - Core system for storing and retrieving lessons learned.

This module provides:
- Lesson capture and storage in memory/lessons/
- Searchable index management
- Access logging for audit trails
- Integration with ClawVault for encrypted storage
"""

import json
import os
import re
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Base paths (resolved from workspace root)
WORKSPACE_ROOT = Path(os.environ.get('OPENCLAW_WORKSPACE', '/Users/faisalshomemacmini/.openclaw/workspace'))
MEMORY_DIR = WORKSPACE_ROOT / 'memory'
LESSONS_DIR = MEMORY_DIR / 'lessons'
INDEX_FILE = MEMORY_DIR / 'knowledge-index.jsonl'
ACCESS_LOG_FILE = MEMORY_DIR / 'access-logs.jsonl'
VAULT_DIR = MEMORY_DIR / 'knowledge-vault'


class KnowledgeManager:
    """Manages knowledge storage, retrieval, and indexing."""
    
    def __init__(self):
        self._ensure_directories()
        
    def _ensure_directories(self):
        """Create necessary directories if they don't exist."""
        LESSONS_DIR.mkdir(parents=True, exist_ok=True)
        VAULT_DIR.mkdir(parents=True, exist_ok=True)
        
    def _log_access(self, operation: str, topic: str, outcome: str = 'success', 
                    details: Optional[Dict] = None, user: str = 'system'):
        """Log access to knowledge base for audit trail."""
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'operation': operation,  # read, write, delete, search
            'topic': topic,
            'outcome': outcome,
            'user': user,
            'details': details or {}
        }
        with open(ACCESS_LOG_FILE, 'a') as f:
            f.write(json.dumps(log_entry) + '\n')
            
    def _sanitize_filename(self, text: str) -> str:
        """Convert text to safe filename."""
        # Remove special characters, limit length
        sanitized = re.sub(r'[^\w\s-]', '', text.lower())
        sanitized = re.sub(r'\s+', '-', sanitized)
        sanitized = re.sub(r'-+', '-', sanitized)
        return sanitized[:100].strip('-')
    
    def _load_index(self) -> List[Dict]:
        """Load the knowledge index from file."""
        if not INDEX_FILE.exists():
            return []
        
        index = []
        with open(INDEX_FILE, 'r') as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        index.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
        return index
    
    def _save_index(self, index: List[Dict]):
        """Save the knowledge index to file."""
        with open(INDEX_FILE, 'w') as f:
            for entry in index:
                f.write(json.dumps(entry) + '\n')
    
    def save_lesson(self, topic: str, content: str, outcome: str = 'success',
                   project: Optional[str] = None, tags: Optional[List[str]] = None,
                   context: Optional[str] = None, session_id: Optional[str] = None,
                   sensitive: bool = False, actor: str = 'system') -> Path:
        """
        Save a lesson to the knowledge base.
        
        Args:
            topic: Main topic/title of the lesson
            content: Full lesson content (markdown format recommended)
            outcome: success, failure, or partial
            project: Related project name/path
            tags: List of tag strings for categorization
            context: Brief context description
            session_id: Session ID where this occurred
            sensitive: If True, store encrypted in vault
            actor: User/system who created this
            
        Returns:
            Path to the saved lesson file
        """
        # Sanitize and create filename
        timestamp = datetime.now()
        date_str = timestamp.strftime('%Y-%m-%d')
        time_str = timestamp.strftime('%H%M')
        sanitized_topic = self._sanitize_filename(topic)
        
        if sensitive:
            # Store in encrypted vault
            lesson_file = VAULT_DIR / f"{date_str}-{sanitized_topic}.md.enc"
        else:
            # Store in regular lessons directory
            lesson_file = LESSONS_DIR / f"{date_str}-{sanitized_topic}.md"
        
        # Format the lesson file content
        lesson_content = self._format_lesson(
            topic=topic,
            content=content,
            outcome=outcome,
            project=project,
            tags=tags or [],
            context=context,
            session_id=session_id,
            actor=actor,
            sensitive=sensitive
        )
        
        # Write the file
        with open(lesson_file, 'w') as f:
            f.write(lesson_content)
        
        # Update index
        index_entry = {
            'id': hashlib.md5(f"{topic}{timestamp}".encode()).hexdigest()[:12],
            'filename': lesson_file.name,
            'path': str(lesson_file),
            'topic': topic,
            'date': date_str,
            'time': time_str,
            'outcome': outcome,
            'project': project,
            'tags': tags or [],
            'sensitive': sensitive,
            'summary': self._extract_summary(content)[:200] if content else ''
        }
        
        index = self._load_index()
        index.append(index_entry)
        self._save_index(index)
        
        # Log the access
        self._log_access(
            operation='write',
            topic=topic,
            outcome='success',
            details={'file': str(lesson_file), 'sensitive': sensitive},
            user=actor
        )
        
        logger.info(f"Saved lesson: {lesson_file}")
        return lesson_file
    
    def _format_lesson(self, topic: str, content: str, outcome: str,
                      project: Optional[str], tags: List[str],
                      context: Optional[str], session_id: Optional[str],
                      actor: str, sensitive: bool) -> str:
        """Format lesson content into markdown file."""
        timestamp = datetime.now()
        
        lines = [
            f"# {topic}",
            "",
            f"- **Date:** {timestamp.strftime('%Y-%m-%d %H:%M %Z')}",
            f"- **Outcome:** {outcome}",
            f"- **Project:** {project or 'None'}",
            f"- **Tags:** [{', '.join(tags)}]",
            f"- **Context:** {context or 'No context provided'}",
            "",
            "## Lesson",
            content,
            "",
            "---",
            f"**Session ID:** {session_id or 'N/A'}",
            f"**Actor:** {actor}",
            f"**Sensitive:** {'Yes ⚠️' if sensitive else 'No'}",
        ]
        
        return '\n'.join(lines)
    
    def _extract_summary(self, content: str) -> str:
        """Extract a brief summary from content."""
        # Look for "Lesson Learned:" or first paragraph
        match = re.search(r'(?:Lesson|Key Insight)[:\s]+([^\n]+)', content)
        if match:
            return match.group(1).strip()
        
        # Fall back to first few sentences
        sentences = re.split(r'[.!?]+\s*', content)
        return '. '.join(sentences[:2]) if sentences else content[:200]
    
    def recall(self, query: str, max_results: int = 10) -> List[Dict]:
        """
        Search for relevant lessons by query.
        
        Args:
            query: Search query string
            max_results: Maximum number of results to return
            
        Returns:
            List of matching index entries with relevance scores
        """
        index = self._load_index()
        query_lower = query.lower()
        keywords = set(query_lower.split())
        
        scored_results = []
        for entry in index:
            score = 0
            
            # Topic match (highest weight)
            if query_lower in entry['topic'].lower():
                score += 100
            elif any(kw in entry['topic'].lower() for kw in keywords):
                score += 50
            
            # Tag matches
            for tag in entry.get('tags', []):
                if tag.lower() in keywords:
                    score += 30
            
            # Summary/content match
            summary_lower = entry.get('summary', '').lower()
            if any(kw in summary_lower for kw in keywords):
                score += 20
            
            # Outcome bonus for failure-related queries
            if 'fail' in query_lower and entry.get('outcome') == 'failure':
                score += 15
            
            if score > 0:
                scored_results.append({**entry, 'score': score})
        
        # Sort by score descending
        scored_results.sort(key=lambda x: x['score'], reverse=True)
        
        # Log the search
        self._log_access(
            operation='search',
            topic=query,
            outcome=f'retrieved_{len(scored_results[:max_results])}',
            details={'query': query, 'results_count': len(scored_results)},
            user='system'
        )
        
        return scored_results[:max_results]
    
    def list_lessons(self, outcome: Optional[str] = None, 
                    project: Optional[str] = None,
                    days: Optional[int] = None) -> List[Dict]:
        """
        List lessons with optional filters.
        
        Args:
            outcome: Filter by outcome (success/failure/partial)
            project: Filter by project
            days: Only show lessons from last N days
            
        Returns:
            List of lesson metadata entries
        """
        index = self._load_index()
        filtered = index
        
        if outcome:
            filtered = [e for e in filtered if e.get('outcome') == outcome]
        
        if project:
            filtered = [e for e in filtered if e.get('project') == project]
        
        if days:
            cutoff = datetime.now().timestamp() - (days * 86400)
            filtered = [e for e in filtered 
                       if datetime.fromisoformat(e['date']).timestamp() > cutoff]
        
        return sorted(filtered, key=lambda x: x['date'], reverse=True)
    
    def get_lesson_content(self, filename: str) -> Optional[str]:
        """Read full content of a lesson file."""
        lesson_file = LESSONS_DIR / filename
        if not lesson_file.exists():
            lesson_file = VAULT_DIR / filename
            if not lesson_file.exists():
                return None
        
        try:
            content = lesson_file.read_text()
            self._log_access(
                operation='read',
                topic=filename,
                outcome='success',
                details={'sensitive': str(filename.endswith('.enc'))}
            )
            return content
        except Exception as e:
            logger.error(f"Failed to read lesson {filename}: {e}")
            return None
    
    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about the knowledge base."""
        index = self._load_index()
        
        outcomes = {}
        projects = {}
        tags = {}
        
        for entry in index:
            outcome = entry.get('outcome', 'unknown')
            outcomes[outcome] = outcomes.get(outcome, 0) + 1
            
            project = entry.get('project')
            if project:
                projects[project] = projects.get(project, 0) + 1
            
            for tag in entry.get('tags', []):
                tags[tag] = tags.get(tag, 0) + 1
        
        return {
            'total_lessons': len(index),
            'outcomes': outcomes,
            'projects': dict(sorted(projects.items(), 
                                   key=lambda x: x[1], reverse=True)[:10]),
            'top_tags': dict(sorted(tags.items(), 
                                   key=lambda x: x[1], reverse=True)[:10]),
            'recent_activity': len([e for e in index 
                                   if datetime.fromisoformat(e['date']) 
                                   >= datetime.now().replace(hour=0)])
        }


# Convenience functions for CLI integration
manager = KnowledgeManager()

def remember(topic: str, content: str, outcome: str = 'success',
            project: Optional[str] = None, tags: Optional[List[str]] = None,
            context: Optional[str] = None) -> str:
    """Store a new lesson."""
    path = manager.save_lesson(
        topic=topic,
        content=content,
        outcome=outcome,
        project=project,
        tags=tags,
        context=context
    )
    return f"✅ Lesson saved: {path}"

def recall(query: str, max_results: int = 5) -> str:
    """Search for relevant lessons."""
    results = manager.recall(query, max_results)
    
    if not results:
        return f"No lessons found matching: {query}"
    
    output = [f"🔍 Found {len(results)} lesson(s) for '{query}':\n"]
    for i, result in enumerate(results, 1):
        output.append(f"\n{i}. **{result['topic']}**")
        output.append(f"   📅 {result['date']} | 🎯 {result['outcome']}")
        if result.get('project'):
            output.append(f"   📁 Project: {result['project']}")
        if result.get('tags'):
            output.append(f"   🏷️ Tags: {', '.join(result['tags'])}")
        output.append(f"   💬 {result.get('summary', 'No summary')[:150]}...")
    
    return '\n'.join(output)

if __name__ == '__main__':
    # Quick test
    print("Knowledge Manager initialized")
    print(f"Lessons dir: {LESSONS_DIR}")
    print(f"Stats: {manager.get_stats()}")
