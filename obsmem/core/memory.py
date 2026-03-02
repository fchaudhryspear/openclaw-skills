"""
Memory Vault - Main storage interface for observational memory
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, asdict
from enum import Enum

from .encryption import SecureStorage, SecurityError


class ObservationType(Enum):
    """Types of observations that can be stored"""
    DECISION = "decision"
    PREFERENCE = "preference"
    LESSON = "lesson"
    MILESTONE = "milestone"
    COMMITMENT = "commitment"
    CONTEXT = "context"
    FACT = "fact"
    PERSONALITY = "personality"


@dataclass
class Observation:
    """
    A single observation extracted from agent interactions
    
    Attributes:
        obs_id: Unique identifier for this observation
        type: Type of observation (decision, preference, etc.)
        content: The actual observation content
        confidence: Confidence score (0.0-1.0) from extraction
        importance: Importance score (0.0-1.0) for prioritization
        timestamp: When the observation was created
        source: Source session/context where it was found
        tags: Related wiki-links or topics [[tag1]] [[tag2]]
        metadata: Additional structured metadata
    """
    obs_id: str
    type: ObservationType
    content: str
    confidence: float = 0.9
    importance: float = 0.5
    timestamp: str = ""
    source: str = ""
    tags: List[str] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.utcnow().isoformat()
        if self.tags is None:
            self.tags = []
        if self.metadata is None:
            self.metadata = {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'obs_id': self.obs_id,
            'type': self.type.value,
            'content': self.content,
            'confidence': self.confidence,
            'importance': self.importance,
            'timestamp': self.timestamp,
            'source': self.source,
            'tags': self.tags,
            'metadata': self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Observation':
        """Create from dictionary"""
        return cls(
            obs_id=data['obs_id'],
            type=ObservationType(data['type']),
            content=data['content'],
            confidence=data.get('confidence', 0.9),
            importance=data.get('importance', 0.5),
            timestamp=data.get('timestamp', ''),
            source=data.get('source', ''),
            tags=data.get('tags', []),
            metadata=data.get('metadata', {})
        )
    
    def format_short(self) -> str:
        """Short formatted representation"""
        priority_icon = self._get_priority_icon()
        return f"{priority_icon} [{self.type.value}|c={self.confidence:.2f}|i={self.importance:.2f}] {self.content}"
    
    def _get_priority_icon(self) -> str:
        """Get emoji based on importance"""
        if self.importance >= 0.8:
            return "🔴"  # High priority
        elif self.importance >= 0.5:
            return "🟡"  # Medium priority
        else:
            return "🟢"  # Low priority


class MemoryVault:
    """
    Encrypted memory vault for AI agent observations
    
    Features:
    - AES-256-GCM encrypted storage
    - Typed observations with confidence/importance scoring
    - Tag-based organization with wiki-links
    - Semantic search support (pluggable backend)
    - Automatic checkpointing
    - Memory-safe operations
    """
    
    def __init__(self, vault_path: str | Path, master_password: str):
        """
        Initialize memory vault
        
        Args:
            vault_path: Directory path for vault files
            master_password: Master password for encryption
        """
        self.vault_path = Path(vault_path)
        self.storage = SecureStorage(
            filepath=self.vault_path / "memory.enc",
            master_password=master_password
        )
        self._observations: Dict[str, Observation] = {}
        self._loaded = False
    
    def load(self) -> None:
        """Load vault from encrypted storage"""
        raw_storage_data = self.storage.load()
        
        # Extract the vault data from storage format
        raw_data = raw_storage_data.get('_vault_data', {})
        
        # Reconstruct observations
        self._observations = {}
        for obs_id, obs_data in raw_data.get('observations', {}).items():
            try:
                self._observations[obs_id] = Observation.from_dict(obs_data)
            except Exception as e:
                print(f"Warning: Failed to load observation {obs_id}: {e}")
        
        self._loaded = True
    
    def save(self) -> None:
        """Save vault to encrypted storage"""
        # Convert observations to serializable format
        data = {
            'observations': {
                obs_id: obs.to_dict() 
                for obs_id, obs in self._observations.items()
            },
            'meta': {
                'last_modified': datetime.utcnow().isoformat(),
                'observation_count': len(self._observations)
            }
        }
        
        # Store in secure storage
        self.storage.set('_vault_data', data)
        self.storage.save()
    
    def add_observation(self, obs: Observation) -> None:
        """Add or update an observation"""
        if not self._loaded:
            self.load()
        
        self._observations[obs.obs_id] = obs
    
    def get_observation(self, obs_id: str) -> Optional[Observation]:
        """Get observation by ID"""
        if not self._loaded:
            self.load()
        return self._observations.get(obs_id)
    
    def delete_observation(self, obs_id: str) -> bool:
        """Delete an observation"""
        if not self._loaded:
            self.load()
        
        if obs_id in self._observations:
            del self._observations[obs_id]
            return True
        return False
    
    def get_all_observations(self) -> List[Observation]:
        """Get all observations sorted by importance"""
        if not self._loaded:
            self.load()
        
        return sorted(
            self._observations.values(),
            key=lambda x: x.importance,
            reverse=True
        )
    
    def filter_by_type(self, obs_type: ObservationType) -> List[Observation]:
        """Filter observations by type"""
        if not self._loaded:
            self.load()
        
        return [
            obs for obs in self._observations.values()
            if obs.type == obs_type
        ]
    
    def filter_by_tags(self, tags: List[str]) -> List[Observation]:
        """Find observations containing any of the specified tags"""
        if not self._loaded:
            self.load()
        
        results = []
        for obs in self._observations.values():
            if any(tag in obs.tags for tag in tags):
                results.append(obs)
        
        return results
    
    def search_by_content(self, query: str, min_confidence: float = 0.0) -> List[Observation]:
        """Simple keyword search (replace with semantic search for production)"""
        if not self._loaded:
            self.load()
        
        query_lower = query.lower()
        results = []
        
        for obs in self._observations.values():
            if obs.confidence >= min_confidence and query_lower in obs.content.lower():
                results.append(obs)
        
        return results
    
    def get_high_importance(self, threshold: float = 0.7) -> List[Observation]:
        """Get high-importance observations above threshold"""
        if not self._loaded:
            self.load()
        
        return [
            obs for obs in self._observations.values()
            if obs.importance >= threshold
        ]
    
    def checkpoint(self) -> str:
        """
        Create a checkpoint and return its ID
        Checkpoints are point-in-time snapshots for recovery
        """
        if not self._loaded:
            self.load()
        
        checkpoint_id = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        checkpoint_path = self.vault_path / f"checkpoint_{checkpoint_id}.enc"
        
        # Save current state to checkpoint file
        checkpoint_storage = SecureStorage(
            filepath=checkpoint_path,
            master_password=self.storage.master_password
        )
        
        raw_data = self.storage._data.copy() if hasattr(self.storage, '_data') else {}
        checkpoint_storage.set('_checkpoint_data', raw_data)
        checkpoint_storage.save()
        
        return checkpoint_id
    
    def restore_checkpoint(self, checkpoint_id: str) -> bool:
        """Restore from a checkpoint"""
        checkpoint_path = self.vault_path / f"checkpoint_{checkpoint_id}.enc"
        
        if not checkpoint_path.exists():
            return False
        
        try:
            checkpoint_storage = SecureStorage(
                filepath=checkpoint_path,
                master_password=self.storage.master_password
            )
            
            data = checkpoint_storage.get('_checkpoint_data', {})
            
            # Reload observations
            self._observations = {}
            for obs_id, obs_data in data.get('observations', {}).items():
                self._observations[obs_id] = Observation.from_dict(obs_data)
            
            self._loaded = True
            return True
            
        except Exception as e:
            print(f"Failed to restore checkpoint: {e}")
            return False
    
    def export_text(self, include_metadata: bool = False) -> str:
        """Export observations as human-readable text"""
        lines = ["# Observational Memory Export", ""]
        
        for obs in self.get_all_observations():
            lines.append(obs.format_short())
            if include_metadata and obs.metadata:
                lines.append(f"  Tags: {', '.join(obs.tags)}")
                lines.append(f"  Source: {obs.source}")
                lines.append("")
        
        return "\n".join(lines)
    
    def __len__(self) -> int:
        """Number of observations in vault"""
        if not self._loaded:
            self.load()
        return len(self._observations)
    
    def __del__(self):
        """Secure cleanup"""
        if hasattr(self, 'storage'):
            del self.storage
