"""
Observation Observer - Watches agent interactions and extracts memories
"""

import re
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, TextIO, Union
from dataclasses import dataclass

from .memory import Observation, ObservationType, MemoryVault


@dataclass
class SessionContext:
    """Context about the current session being observed"""
    session_id: str
    start_time: str
    agent_name: str = ""
    user_name: str = ""
    context_window_size: int = 0


class ObservationObserver:
    """
    Watches AI agent conversations and automatically extracts observations
    
    Features:
    - Pattern-based extraction of decisions, preferences, lessons
    - Confidence/importance scoring
    - Wiki-link detection [[topic]]
    - Integration with memory vault for storage
    - Rule-based compression (LLM-based optional)
    
    Based on ClawVault observational memory principles
    """
    
    # Regex patterns for extraction
    PATTERNS = {
        'decision': [
            r'(?:we|I|the team) (?:decided|chose|selected|picked) (.+?)(?:\.|$)',
            r'(.+?) (?:is|was) the better (?:choice|option|solution)',
            r'(?:let\'s|we will|I will) use (.+?)(?:\.|$)',
        ],
        'preference': [
            r'(.+?) (?:prefers|likes|wants|better than) (.+?)(?:\.|$)',
            r'I (?:prefer|like|want) (.+?)(?:\.|$)',
            r'(?:always|never) (?:use|avoid) (.+?)(?:\.|$)',
        ],
        'lesson': [
            r'(?:learned|discovered|found out) that (.+?)(?:\.|$)',
            r'(?:warning|note|important): (.+?)(?:\.|$)',
            r'(?:don\'t|do not|avoid) (.+?)(?:because?|since|.+$)',
        ],
        'milestone': [
            r'(?:deployed|shipped|released|completed) (.+?)(?:\.|$)',
            r'(.+?) (?:feature|task|project) (?:is done|complete|finished)',
        ],
        'commitment': [
            r'(?:I will|we will|must|need to) (.+?)(?:by|before)?(?:\s+(\S+))?(?:\.|$)',
            r'(?:promise|commit|guarantee) to (.+?)(?:\.|$)',
        ],
    }
    
    # Wiki-link pattern
    WIKI_LINK_PATTERN = r'\[\[(.*?)\]\]'
    
    # Priority indicators
    PRIORITY_KEYWORDS = {
        'high': ['critical', 'important', 'must', 'essential', 'urgent'],
        'medium': ['should', 'recommended', 'consider'],
        'low': ['could', 'optional', 'nice-to-have']
    }
    
    def __init__(self, vault: Optional[MemoryVault] = None):
        """
        Initialize the observer
        
        Args:
            vault: Memory vault to store extracted observations
        """
        self.vault = vault
        self.current_context: Optional[SessionContext] = None
        self.extracted_observations: List[Observation] = []
    
    def set_session_context(self, context: SessionContext) -> None:
        """Set the current session context"""
        self.current_context = context
    
    def observe_text(self, text: str) -> List[Observation]:
        """
        Observe a block of text and extract observations
        
        Args:
            text: Text content to analyze (conversation, transcript, etc.)
            
        Returns:
            List of extracted observations
        """
        observations = []
        
        # Extract wiki-links first
        tags = self._extract_wiki_links(text)
        
        # Search for decision patterns
        observations.extend(self._extract_by_type(
            text, ObservationType.DECISION, self.PATTERNS['decision'], tags
        ))
        
        # Search for preference patterns
        observations.extend(self._extract_by_type(
            text, ObservationType.PREFERENCE, self.PATTERNS['preference'], tags
        ))
        
        # Search for lesson patterns
        observations.extend(self._extract_by_type(
            text, ObservationType.LESSON, self.PATTERNS['lesson'], tags
        ))
        
        # Search for milestone patterns
        observations.extend(self._extract_by_type(
            text, ObservationType.MILESTONE, self.PATTERNS['milestone'], tags
        ))
        
        # Search for commitment patterns
        observations.extend(self._extract_by_type(
            text, ObservationType.COMMITMENT, self.PATTERNS['commitment'], tags
        ))
        
        # Store in vault if available
        if self.vault:
            for obs in observations:
                self.vault.add_observation(obs)
        
        self.extracted_observations.extend(observations)
        return observations
    
    def observe_file(self, file_path: Union[str, Path]) -> List[Observation]:
        """
        Observe a file and extract observations
        
        Args:
            file_path: Path to file to analyze
            
        Returns:
            List of extracted observations
        """
        path = Path(file_path)
        
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        with open(path, 'r', encoding='utf-8') as f:
            text = f.read()
        
        return self.observe_text(text)
    
    def observe_stream(self, stream: TextIO) -> List[Observation]:
        """
        Observe a stream of text (line by line)
        
        Args:
            stream: File-like object to read from
            
        Returns:
            List of extracted observations
        """
        full_text = stream.read()
        return self.observe_text(full_text)
    
    def _extract_wiki_links(self, text: str) -> List[str]:
        """Extract wiki-links like [[Topic]] from text"""
        return re.findall(self.WIKI_LINK_PATTERN, text)
    
    def _extract_by_type(
        self, 
        text: str, 
        obs_type: ObservationType, 
        patterns: List[str], 
        tags: List[str]
    ) -> List[Observation]:
        """Extract observations of a specific type using regex patterns"""
        observations = []
        
        for pattern in patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE | re.MULTILINE)
            
            for match in matches:
                content = match.group(0).strip()
                
                # Calculate scores
                confidence = self._calculate_confidence(content, pattern)
                importance = self._calculate_importance(text, content)
                
                # Create observation
                obs = Observation(
                    obs_id=str(uuid.uuid4()),
                    type=obs_type,
                    content=content,
                    confidence=confidence,
                    importance=importance,
                    timestamp=datetime.utcnow().isoformat(),
                    source=self.current_context.session_id if self.current_context else "",
                    tags=tags.copy()
                )
                
                observations.append(obs)
        
        return observations
    
    def _calculate_confidence(self, content: str, pattern: str) -> float:
        """
        Calculate confidence score based on pattern match quality
        
        Higher confidence for:
        - Clear, complete sentences
        - Strong indicative language
        """
        base_confidence = 0.75
        
        # Boost for clear language
        strong_words = ['decided', 'chose', 'will', 'must', 'always', 'never']
        if any(word in content.lower() for word in strong_words):
            base_confidence += 0.1
        
        # Boost for lengthier statements (more context)
        word_count = len(content.split())
        if word_count > 5:
            base_confidence += 0.05
        
        # Cap at 0.95
        return min(base_confidence, 0.95)
    
    def _calculate_importance(self, context: str, content: str) -> float:
        """
        Calculate importance score based on keywords and context
        
        Higher importance for:
        - Critical/urgent keywords
        - Decisions over preferences
        - Lessons learned
        """
        base_importance = 0.5
        context_lower = context.lower()
        content_lower = content.lower()
        
        # Check for priority keywords
        for level, keywords in self.PRIORITY_KEYWORDS.items():
            if any(kw in context_lower or kw in content_lower for kw in keywords):
                if level == 'high':
                    base_importance += 0.3
                elif level == 'medium':
                    base_importance += 0.15
                break
        
        # Boost certain types
        if 'important' in context_lower or 'critical' in context_lower:
            base_importance += 0.2
        
        # Cap at 1.0
        return min(base_importance, 1.0)
    
    def get_summary(self) -> str:
        """Get a summary of all extracted observations"""
        if not self.extracted_observations:
            return "No observations extracted yet."
        
        lines = [f"# Observation Summary ({len(self.extracted_observations)} total)", ""]
        
        # Group by type
        by_type: Dict[str, List[Observation]] = {}
        for obs in self.extracted_observations:
            if obs.type.value not in by_type:
                by_type[obs.type.value] = []
            by_type[obs.type.value].append(obs)
        
        for obs_type, observations in sorted(by_type.items()):
            lines.append(f"## {obs_type.capitalize()}s ({len(observations)})")
            for obs in sorted(observations, key=lambda x: x.importance, reverse=True):
                lines.append(f"  {obs.format_short()}")
            lines.append("")
        
        return "\n".join(lines)
    
    def compress_to_observations(self, raw_text: str) -> str:
        """
        Compress raw conversation text into formatted observations
        
        Format follows ClawVault style:
        [type|c=X.XX|i=X.XX] content [[tag1]] [[tag2]]
        
        Args:
            raw_text: Raw conversation/transcript text
            
        Returns:
            Compressed observation string
        """
        observations = self.observe_text(raw_text)
        
        lines = []
        for obs in observations:
            tags_str = ' '.join([f'[[{tag}]]' for tag in obs.tags])
            line = (
                f"[{obs.type.value}|c={obs.confidence:.2f}|i={obs.importance:.2f}] "
                f"{obs.content} {tags_str}".strip()
            )
            lines.append(line)
        
        return '\n'.join(lines)
