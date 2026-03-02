"""
Tests for ObsMem - Observational Memory System
"""

import pytest
import tempfile
import shutil
from pathlib import Path
import time

from obsmem.core.encryption import SecureStorage, SecurityError
from obsmem.core.memory import MemoryVault, Observation, ObservationType
from obsmem.core.observer import ObservationObserver


class TestSecureStorage:
    """Test encryption layer"""
    
    def setup_method(self):
        """Create temp directory for tests"""
        self.test_dir = tempfile.mkdtemp()
        
    def teardown_method(self):
        """Cleanup temp files"""
        shutil.rmtree(self.test_dir, ignore_errors=True)
    
    def test_basic_encrypt_decrypt(self):
        """Test basic encryption/decryption cycle"""
        filepath = Path(self.test_dir) / "test.enc"
        storage = SecureStorage(filepath, "test_password_123")
        
        # Set and save data
        storage.set("key1", "value1")
        storage.set("number", 42)
        storage.set("nested", {"a": 1, "b": 2})
        storage.save()
        
        # Load and verify
        storage2 = SecureStorage(filepath, "test_password_123")
        storage2.load()
        
        assert storage2.get("key1") == "value1"
        assert storage2.get("number") == 42
        assert storage2.get("nested") == {"a": 1, "b": 2}
    
    def test_wrong_password(self):
        """Test that wrong password fails decryption"""
        filepath = Path(self.test_dir) / "test.enc"
        storage = SecureStorage(filepath, "correct_password")
        storage.set("secret", "hidden")
        storage.save()
        
        # Try with wrong password
        storage2 = SecureStorage(filepath, "wrong_password")
        
        # Should fail during load
        with pytest.raises(Exception):
            storage2.load()
    
    def test_file_permissions(self):
        """Test that files are created with secure permissions"""
        filepath = Path(self.test_dir) / "test.enc"
        storage = SecureStorage(filepath, "password")
        storage.set("data", "value")
        storage.save()
        
        # Check permissions (should be 0600)
        mode = filepath.stat().st_mode & 0o777
        assert mode == 0o600
    
    def test_new_file_creation(self):
        """Test creating new encrypted file"""
        filepath = Path(self.test_dir) / "new.enc"
        
        assert not filepath.exists()
        
        storage = SecureStorage(filepath, "password")
        storage.set("test", "data")
        storage.save()
        
        assert filepath.exists()
    
    def test_empty_storage(self):
        """Test storage with no data"""
        filepath = Path(self.test_dir) / "empty.enc"
        storage = SecureStorage(filepath, "password")
        storage.save()
        
        storage2 = SecureStorage(filepath, "password")
        storage2.load()
        
        assert storage2.get("nonexistent") is None


class TestObservation:
    """Test observation data structure"""
    
    def setup_method(self):
        pass
    
    def teardown_method(self):
        pass
    
    def test_observation_creation(self):
        """Test creating an observation"""
        obs = Observation(
            obs_id="test-123",
            type=ObservationType.DECISION,
            content="Chose PostgreSQL over MongoDB",
            confidence=0.95,
            importance=0.85,
            tags=["database", "decision"]
        )
        
        assert obs.obs_id == "test-123"
        assert obs.type == ObservationType.DECISION
        assert obs.confidence == 0.95
        assert len(obs.tags) == 2
    
    def test_observation_serialization(self):
        """Test converting observation to/from dict"""
        obs = Observation(
            obs_id="test-456",
            type=ObservationType.LESSON,
            content="Always validate user input",
            confidence=0.9,
            importance=0.95
        )
        
        # Serialize
        data = obs.to_dict()
        
        # Deserialize
        obs2 = Observation.from_dict(data)
        
        assert obs2.obs_id == obs.obs_id
        assert obs2.type == obs.type
        assert obs2.content == obs.content
    
    def test_priority_icons(self):
        """Test priority icon assignment"""
        high = Observation(
            obs_id="1",
            type=ObservationType.DECISION,
            content="High priority item",
            importance=0.9
        )
        medium = Observation(
            obs_id="2",
            type=ObservationType.DECISION,
            content="Medium priority item",
            importance=0.6
        )
        low = Observation(
            obs_id="3",
            type=ObservationType.DECISION,
            content="Low priority item",
            importance=0.3
        )
        
        assert high._get_priority_icon() == "🔴"
        assert medium._get_priority_icon() == "🟡"
        assert low._get_priority_icon() == "🟢"


class TestMemoryVault:
    """Test memory vault operations"""
    
    def setup_method(self):
        """Create temp vault"""
        # Call parent if exists
        try:
            super().setup_method()
        except (AttributeError, TypeError):
            pass
            
        self.test_dir = tempfile.mkdtemp()
        self.vault_path = Path(self.test_dir) / "vault"
        self.vault = MemoryVault(self.vault_path, "vault_password_456")
    
    def teardown_method(self):
        """Cleanup"""
        # Call parent if exists
        try:
            super().teardown_method()
        except (AttributeError, TypeError):
            pass
            
        shutil.rmtree(self.test_dir, ignore_errors=True)
    
    def test_add_and_retrieve(self):
        """Test adding and retrieving observations"""
        obs = Observation(
            obs_id="obs-1",
            type=ObservationType.DECISION,
            content="Test decision",
            importance=0.8
        )
        
        self.vault.add_observation(obs)
        self.vault.save()
        
        # Reload and retrieve
        self.vault.load()
        retrieved = self.vault.get_observation("obs-1")
        
        assert retrieved is not None
        assert retrieved.content == "Test decision"
    
    def test_filter_by_type(self):
        """Test filtering observations by type"""
        self.vault.add_observation(Observation(
            obs_id="1", type=ObservationType.DECISION, content="Decision 1"
        ))
        self.vault.add_observation(Observation(
            obs_id="2", type=ObservationType.PREFERENCE, content="Preference 1"
        ))
        self.vault.add_observation(Observation(
            obs_id="3", type=ObservationType.DECISION, content="Decision 2"
        ))
        
        decisions = self.vault.filter_by_type(ObservationType.DECISION)
        
        assert len(decisions) == 2
    
    def test_filter_by_tags(self):
        """Test filtering by tags"""
        self.vault.add_observation(Observation(
            obs_id="1", type=ObservationType.DECISION,
            content="Database choice", tags=["database", "backend"]
        ))
        self.vault.add_observation(Observation(
            obs_id="2", type=ObservationType.DECISION,
            content="Frontend framework", tags=["frontend", "react"]
        ))
        
        db_related = self.vault.filter_by_tags(["database"])
        
        assert len(db_related) == 1
    
    def test_high_importance_filter(self):
        """Test getting high importance observations"""
        self.vault.add_observation(Observation(
            obs_id="1", type=ObservationType.DECISION,
            content="Critical decision", importance=0.9
        ))
        self.vault.add_observation(Observation(
            obs_id="2", type=ObservationType.DECISION,
            content="Minor note", importance=0.3
        ))
        
        high = self.vault.get_high_importance(threshold=0.7)
        
        assert len(high) == 1
        assert high[0].importance == 0.9
    
    def test_checkpoint_restore(self):
        """Test checkpoint creation and restoration"""
        # Add some observations
        self.vault.add_observation(Observation(
            obs_id="1", type=ObservationType.DECISION, content="Initial state"
        ))
        self.vault.save()
        
        # Create checkpoint
        checkpoint_id = self.vault.checkpoint()
        assert checkpoint_id is not None
        
        # Add more observations
        self.vault.add_observation(Observation(
            obs_id="2", type=ObservationType.DECISION, content="After checkpoint"
        ))
        
        # Restore
        success = self.vault.restore_checkpoint(checkpoint_id)
        assert success
        
        # Should only have the first observation
        obs_ids = [o.obs_id for o in self.vault.get_all_observations()]
        assert "1" in obs_ids
        assert "2" not in obs_ids


class TestObservationObserver:
    """Test observation extraction"""
    
    def setup_method(self):
        """Setup observer with temp vault"""
        try:
            super().setup_method()
        except (AttributeError, TypeError):
            pass
            
        self.test_dir = tempfile.mkdtemp()
        vault_path = Path(self.test_dir) / "vault"
        self.vault = MemoryVault(vault_path, "observer_test_pwd")
        self.observer = ObservationObserver(vault=self.vault)
    
    def teardown_method(self):
        """Cleanup"""
        try:
            super().teardown_method()
        except (AttributeError, TypeError):
            pass
        
        shutil.rmtree(self.test_dir, ignore_errors=True)
    
    def test_extract_decision(self):
        """Test decision extraction"""
        text = "We decided to use TypeScript for better type safety."
        
        observations = self.observer.observe_text(text)
        
        assert len(observations) > 0
        assert any(o.type == ObservationType.DECISION for o in observations)
    
    def test_extract_preference(self):
        """Test preference extraction"""
        text = "Faisal prefers REST APIs over GraphQL for simplicity."
        
        observations = self.observer.observe_text(text)
        
        assert len(observations) > 0
        assert any(o.type == ObservationType.PREFERENCE for o in observations)
    
    def test_wiki_link_extraction(self):
        """Test wiki-link tag extraction"""
        text = """
        We chose [[PostgreSQL]] as our database.
        Important for the [[backend]] architecture.
        """
        
        observations = self.observer.observe_text(text)
        
        # Check that tags were extracted
        all_tags = []
        for obs in observations:
            all_tags.extend(obs.tags)
        
        assert "PostgreSQL" in all_tags or "backend" in all_tags
    
    def test_confidence_scoring(self):
        """Test that confidence scores are reasonable"""
        text = "We definitely decided this is the right approach."
        
        observations = self.observer.observe_text(text)
        
        for obs in observations:
            assert 0.0 <= obs.confidence <= 1.0
    
    def test_importance_scoring(self):
        """Test that importance scores reflect content"""
        text = """
        Critical: We must implement proper authentication.
        This is important for security.
        """
        
        observations = self.observer.observe_text(text)
        
        # Should find at least one high importance observation
        high_imp = [o for o in observations if o.importance >= 0.7]
        assert len(high_imp) > 0
    
    def test_compress_format(self):
        """Test compression to ClawVault format"""
        text = "We decided on PostgreSQL for the database."
        
        compressed = self.observer.compress_to_observations(text)
        
        # Should contain formatted observation
        assert "[decision" in compressed.lower() or "[preference" in compressed.lower()


def run_tests():
    """Run all tests manually"""
    import sys
    
    test_classes = [
        TestSecureStorage,
        TestObservation,
        TestMemoryVault,
        TestObservationObserver
    ]
    
    passed = 0
    failed = 0
    
    for test_class in test_classes:
        print(f"\n{'='*60}")
        print(f"Running {test_class.__name__}")
        print('='*60)
        
        instance = test_class()
        
        for method_name in dir(instance):
            if method_name.startswith('test_'):
                try:
                    instance.setup_method()
                    getattr(instance, method_name)()
                    print(f"  ✅ {method_name}")
                    passed += 1
                except Exception as e:
                    print(f"  ❌ {method_name}: {e}")
                    failed += 1
                finally:
                    instance.teardown_method()
    
    print(f"\n{'='*60}")
    print(f"Results: {passed} passed, {failed} failed")
    print('='*60)
    
    return failed == 0


if __name__ == "__main__":
    success = run_tests()
    exit(0 if success else 1)
