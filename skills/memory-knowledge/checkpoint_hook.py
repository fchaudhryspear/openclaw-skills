#!/usr/bin/env python3
"""
Checkpoint Integration Hook - Automatically captures lessons from checkpoint attempts.

This module hooks into the checkpoint system to automatically capture:
- Failed attempts after max retries
- Successful resolutions of complex problems
- Errors and their solutions

Usage:
    import checkpoint_hook
    checkpoint_hook.init()  # Called during OpenClaw startup
    
    # Manual trigger
    checkpoint_hook.capture_lesson_from_session(session_id, outcome)
"""

import os
import sys
import json
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any
import logging

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from knowledge_manager import manager

logger = logging.getLogger(__name__)

# Configuration
AUTO_CAPTURE_ENABLED = os.environ.get('KNOWLEDGE_AUTO_CAPTURE', 'true').lower() == 'true'
CAPTURE_FAILURES_ONLY = os.environ.get('KNOWLEDGE_CAPTURE_FAILURES_ONLY', 'false').lower() == 'true'
MAX_RETRIES_THRESHOLD = int(os.environ.get('KNOWLEDGE_MAX_RETRIES_THRESHOLD', '3'))

# Workspace paths
WORKSPACE_ROOT = Path(os.environ.get('OPENCLAW_WORKSPACE', '/Users/faisalshomemacmini/.openclaw/workspace'))
SESSION_LOG_DIR = WORKSPACE_ROOT / 'memory'


def init():
    """Initialize the checkpoint hook."""
    if AUTO_CAPTURE_ENABLED:
        logger.info("Knowledge retention auto-capture initialized")
    return AUTO_CAPTURE_ENABLED


def extract_session_context(session_id: str) -> Optional[Dict[str, Any]]:
    """
    Extract context from session logs for a given session ID.
    
    This looks for session-related files in memory/ directory.
    """
    # Look for session-specific files
    possible_files = [
        SESSION_LOG_DIR / f"{session_id}.md",
        SESSION_LOG_DIR / f"session-{session_id}.json",
    ]
    
    for filepath in possible_files:
        if filepath.exists():
            try:
                if filepath.suffix == '.json':
                    return json.loads(filepath.read_text())
                else:
                    return {'raw_content': filepath.read_text()}
            except Exception as e:
                logger.error(f"Failed to parse session file {filepath}: {e}")
    
    # If no specific file found, return minimal context
    return {
        'session_id': session_id,
        'timestamp': datetime.now().isoformat(),
        'detected_source': 'fallback'
    }


def determine_outcome_and_topic(session_context: Dict, 
                                attempt_count: int,
                                error_messages: list = None) -> tuple:
    """
    Determine the outcome (success/failure/partial) and extract topic from session context.
    
    Returns:
        Tuple of (outcome, topic)
    """
    error_messages = error_messages or []
    
    # Check for failure indicators
    has_errors = len(error_messages) > 0 or attempt_count >= MAX_RETRIES_THRESHOLD
    
    if has_errors and not CAPTURE_FAILURES_ONLY:
        outcome = 'failure' if attempt_count >= MAX_RETRIES_THRESHOLD else 'partial'
    elif has_errors and CAPTURE_FAILURES_ONLY:
        outcome = 'failure'
    else:
        outcome = 'success'
    
    # Extract topic from context
    raw_content = session_context.get('raw_content', '')
    
    # Try to find topic markers
    topic = None
    for marker in ['# ', '## ', 'Topic:', 'Task:', 'Goal:']:
        if marker in raw_content:
            lines = raw_content.split('\n')
            for line in lines:
                if marker in line:
                    topic = line.replace(marker, '').strip()[:100]
                    break
        if topic:
            break
    
    # Fallback to generic topic
    if not topic:
        topic = f"Session {session_context.get('session_id', 'unknown')} ({outcome})"
    
    return outcome, topic


def build_lesson_content(outcome: str, session_context: Dict, 
                        error_messages: list = None,
                        resolution: Optional[str] = None) -> str:
    """Build formatted lesson content from session data."""
    error_messages = error_messages or []
    
    lines = []
    
    if outcome == 'failure':
        lines.append("## ⚠️ What Went Wrong")
        if error_messages:
            for i, err in enumerate(error_messages, 1):
                lines.append(f"{i}. {err}")
        else:
            lines.append("Multiple retry attempts exceeded without success.")
        
        lines.append("\n## 💡 Key Insights")
        lines.append("- Identify root cause before retrying")
        lines.append("- Consider alternative approaches when stuck")
        lines.append("- Document workarounds for future reference")
        
        if resolution:
            lines.append(f"\n## 🔧 Resolution Attempted\n{resolution}")
            
    elif outcome == 'partial':
        lines.append("## 🎯 Partial Success")
        lines.append("The task was partially completed but encountered obstacles.")
        
        if error_messages:
            lines.append("\n## ⚠️ Remaining Issues")
            for err in error_messages:
                lines.append(f"- {err}")
                
    else:  # success
        lines.append("## ✅ Successful Resolution")
        lines.append("The task was completed successfully.")
        
        if resolution:
            lines.append(f"\n## 🔧 Solution Applied\n{resolution}")
        
        lines.append("\n## 💡 Lessons Learned")
        lines.append("- Document what worked for future reference")
        lines.append("- Consider if this approach can be generalized")
        lines.append("- Note any assumptions or edge cases")
    
    return '\n'.join(lines)


def capture_lesson_from_session(session_id: str, 
                               outcome: str = 'auto',
                               error_messages: list = None,
                               resolution: Optional[str] = None,
                               project: Optional[str] = None,
                               tags: Optional[list] = None) -> Optional[str]:
    """
    Capture a lesson from a session's state.
    
    Args:
        session_id: The session identifier
        outcome: 'success', 'failure', 'partial', or 'auto' to detect
        error_messages: List of error messages encountered
        resolution: Description of how it was resolved
        project: Associated project name
        tags: Additional tags
        
    Returns:
        Path to saved lesson file, or None if skipped
    """
    if not AUTO_CAPTURE_ENABLED:
        logger.debug("Auto-capture disabled, skipping")
        return None
    
    # Extract session context
    session_context = extract_session_context(session_id)
    
    # Determine outcome if auto
    if outcome == 'auto':
        error_messages = error_messages or []
        attempt_count = len(error_messages) + 1  # Rough estimate
        outcome, _ = determine_outcome_and_topic(session_context, attempt_count, error_messages)
    
    # Skip successful outcomes if configured to only capture failures
    if outcome == 'success' and CAPTURE_FAILURES_ONLY:
        logger.debug("Skipping successful lesson per configuration")
        return None
    
    # Determine topic
    _, topic = determine_outcome_and_topic(session_context, 1, error_messages)
    
    # Build content
    content = build_lesson_content(outcome, session_context, error_messages, resolution)
    
    # Save lesson
    try:
        lesson_path = manager.save_lesson(
            topic=topic,
            content=content,
            outcome=outcome,
            project=project,
            tags=tags or ['checkpoint', 'auto-captured'],
            context=f"Auto-captured from session {session_id}",
            session_id=session_id,
            actor='checkpoint-hook'
        )
        logger.info(f"Auto-captured lesson: {lesson_path}")
        return str(lesson_path)
    except Exception as e:
        logger.error(f"Failed to capture lesson from session {session_id}: {e}")
        return None


def on_checkpoint_failure(checkpoint_name: str, 
                         attempt: int,
                         error: str,
                         project: Optional[str] = None):
    """Hook called when a checkpoint fails."""
    if attempt >= MAX_RETRIES_THRESHOLD:
        return capture_lesson_from_session(
            session_id=f"checkpoint-{checkpoint_name}",
            outcome='failure',
            error_messages=[error],
            project=project,
            tags=['checkpoint', 'max-retries-exceeded']
        )
    return None


def on_checkpoint_success(checkpoint_name: str,
                         resolution: str,
                         project: Optional[str] = None):
    """Hook called when a checkpoint succeeds after difficulty."""
    if CAPTURE_FAILURES_ONLY:
        return None
    
    return capture_lesson_from_session(
        session_id=f"checkpoint-{checkpoint_name}",
        outcome='success',
        resolution=resolution,
        project=project,
        tags=['checkpoint', 'resolved']
    )


def log_attempt(session_id: str, attempt_type: str, details: dict = None):
    """Log an attempt for later analysis."""
    log_file = SESSION_LOG_DIR / 'checkpoint-attempts.jsonl'
    
    entry = {
        'timestamp': datetime.now().isoformat(),
        'session_id': session_id,
        'attempt_type': attempt_type,  # 'retry', 'success', 'failure'
        'details': details or {}
    }
    
    with open(log_file, 'a') as f:
        f.write(json.dumps(entry) + '\n')


# Convenience function for manual triggering
def save_lesson(topic: str, content: str, outcome: str = 'success',
               project: Optional[str] = None, tags: Optional[list] = None,
               context: Optional[str] = None):
    """Manual lesson saving function."""
    return capture_lesson_from_session(
        session_id=f"manual-{datetime.now().strftime('%Y%m%d%H%M%S')}",
        outcome=outcome,
        project=project,
        tags=tags or ['manual']
    )


if __name__ == '__main__':
    # Test initialization
    print(f"Initializing knowledge retention hook...")
    enabled = init()
    print(f"Auto-capture enabled: {enabled}")
    
    # Show stats
    stats = manager.get_stats()
    print(f"Current lessons in database: {stats['total_lessons']}")
