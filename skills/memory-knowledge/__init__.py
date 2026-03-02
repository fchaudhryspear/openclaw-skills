"""
Knowledge Retention System - Memory Skill Package

Provides /remember and /recall commands for storing and retrieving lessons learned.
"""

from .knowledge_manager import KnowledgeManager, remember, recall, manager
from .checkpoint_hook import (
    init as init_hook,
    capture_lesson_from_session,
    on_checkpoint_failure,
    on_checkpoint_success,
    save_lesson
)

__all__ = [
    'KnowledgeManager',
    'remember',
    'recall', 
    'manager',
    'init_hook',
    'capture_lesson_from_session',
    'on_checkpoint_failure',
    'on_checkpoint_success',
    'save_lesson'
]

# Auto-initialize on import
if __name__ != '__main__':
    try:
        init_hook()
    except Exception as e:
        pass  # Silent fail during import
