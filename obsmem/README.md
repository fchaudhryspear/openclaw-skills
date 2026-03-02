# ObsMem - Observational Memory for AI Agents

**An AI agent never forgets.** ✨

ObsMem is a security-focused observational memory system for AI agents. It watches conversations, extracts what matters, and builds persistent knowledge automatically. Based on best practices from [ClawVault](https://clawvault.dev/).

## 🎯 Features

- **Observational Memory**: Automatically extracts decisions, preferences, lessons from agent interactions
- **AES-256-GCM Encryption**: Industry-standard authenticated encryption for all stored data
- **scrypt KDF**: Secure password-derived key generation (N=2^14, r=8, p=1)
- **Secure File Permissions**: All files created with 0600 permissions
- **Memory Safety**: Sensitive data wiped from memory after use
- **Plaintext Avoidance**: Nothing sensitive written to disk in cleartext
- **Typed Observations**: Structured memory with confidence/importance scoring
- **Wiki-Link Support**: `[[topic]]` tags for knowledge graph building
- **Checkpoint & Recovery**: Point-in-time snapshots for disaster recovery

## 📦 Installation

```bash
# Install dependencies
pip install cryptography

# Add obsmem to your Python path or install as package
cd ~/.openclaw/workspace/obsmem
pip install -e .
```

## 🚀 Quick Start

### Basic Usage

```python
from obsmem.core.memory import MemoryVault, Observation, ObservationType
from obsmem.core.observer import ObservationObserver

# Initialize vault with encryption
vault = MemoryVault(
    vault_path="/path/to/vault",
    master_password="your-secure-password"
)

# Create an observer to extract memories
observer = ObservationObserver(vault=vault)

# Observe text (conversation, transcript, etc.)
text = """
We decided to use PostgreSQL over MongoDB for the new project.
It's important because we need ACID compliance.
Faisal prefers REST APIs over GraphQL for simplicity.
"""

observations = observer.observe_text(text)
print(f"Extracted {len(observations)} observations")

# Save to encrypted storage
vault.save()

# Load later
vault.load()

# Query memories
high_priority = vault.get_high_importance(threshold=0.7)
for obs in high_priority:
    print(obs.format_short())
```

### Manual Memory Storage

```python
from obsmem.core.memory import MemoryVault, Observation, ObservationType
import uuid

vault = MemoryVault("./my-vault", "secure-password")

# Create observation manually
obs = Observation(
    obs_id=str(uuid.uuid4()),
    type=ObservationType.DECISION,
    content="Chose TypeScript over JavaScript for type safety",
    confidence=0.95,
    importance=0.85,
    tags=["programming", "typescript", "decision"]
)

vault.add_observation(obs)
vault.save()
```

## 🔒 Security Features

### Encryption Architecture

```
┌─────────────────────────────────────────────┐
│           Master Password                    │
│              (user input)                    │
└─────────────────┬───────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────┐
│         scrypt KDF                           │
│   N=16384, r=8, p=1 (CPU/Memory hard)       │
└─────────────────┬───────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────┐
│      AES-256-GCM Key (32 bytes)             │
└─────────────────┬───────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────┐
│   Encrypted Blob Format:                     │
│   ┌──────────┬──────────┬─────────────────┐ │
│   │  Salt    │ Nonce    │ Ciphertext      │ │
│   │  (32B)   │ (12B)    │ (variable + 16) │ │
│   └──────────┴──────────┴─────────────────┘ │
└─────────────────────────────────────────────┘
```

### Security Guarantees

1. **No Plaintext on Disk**: All data encrypted before writing
2. **Unique Nonces**: Cryptographically random nonces per encryption
3. **Authenticated Encryption**: GCM mode provides integrity verification
4. **Secure Deletion**: Keys overwritten when no longer needed
5. **Atomic Writes**: Prevents corruption on crash/power loss
6. **Restrictive Permissions**: 0600 (owner read/write only)

## 📊 Observation Types

| Type | Description | Example |
|------|-------------|---------|
| `DECISION` | Significant choices made | "Chose PostgreSQL over MongoDB" |
| `PREFERENCE` | User/team preferences | "Prefers REST over GraphQL" |
| `LESSON` | Things learned | "Don't deploy on Fridays" |
| `MILESTONE` | Completed tasks/features | "Dashboard deployed" |
| `COMMITMENT` | Promises/todo items | "Will fix auth bug by Monday" |
| `CONTEXT` | Important context | "Project deadline: March 15" |
| `FACT` | Factual information | "API rate limit: 1000/hour" |
| `PERSONALITY` | Agent personality traits | "Uses casual tone" |

## 🔍 Search & Retrieval

### Filter by Type

```python
decisions = vault.filter_by_type(ObservationType.DECISION)
lessons = vault.filter_by_type(ObservationType.LESSON)
```

### Filter by Tags

```python
related = vault.filter_by_tags(["database", "postgresql"])
```

### Search by Content

```python
results = vault.search_by_content("database choice", min_confidence=0.7)
```

### Get High Importance

```python
critical = vault.get_high_importance(threshold=0.8)
```

## 💾 Checkpointing

```python
# Create checkpoint before risky operations
checkpoint_id = vault.checkpoint()
print(f"Created checkpoint: {checkpoint_id}")

# Restore if needed
success = vault.restore_checkpoint("20260301_153000")
if success:
    print("Restored successfully")
```

## 🛠️ Configuration

Settings are in `obsmem/config/settings.py`:

```python
from obsmem.config.settings import Config

# Default vault location
vault_path = Config.DEFAULT_VAULT_PATH

# Custom path
Config.ensure_vault_dir("/custom/vault/path")

# Encryption settings (should not need changing)
config = {
    'algorithm': Config.ENCRYPTION_ALGORITHM,  # AES-256-GCM
    'kdf_n': Config.KDF_N_PARAMETER,  # 16384
    'kdf_r': Config.KDF_R_PARAMETER,  # 8
    'kdf_p': Config.KDF_P_PARAMETER,  # 1
}
```

## 📁 Project Structure

```
obsmem/
├── __init__.py              # Package exports
├── core/
│   ├── __init__.py
│   ├── encryption.py        # AES-256-GCM secure storage
│   ├── memory.py            # Memory vault & observation types
│   └── observer.py          # Text observation extraction
├── config/
│   ├── __init__.py
│   └── settings.py          # Global configuration
└── utils/
    ├── __init__.py
    └── helpers.py           # Utility functions
```

## 🧪 Testing

```bash
# Run tests (create test_obsmem.py first)
python -m pytest tests/ -v

# Test encryption round-trip
python -c "
from obsmem.core.encryption import SecureStorage
storage = SecureStorage('/tmp/test.enc', 'password123')
storage.set('secret', 'very confidential')
storage.save()
storage.load()
print(storage.get('secret'))  # should print: very confidential
"
```

## 🔮 Future Enhancements

- [ ] Semantic search with vector embeddings
- [ ] Knowledge graph traversal
- [ ] LLM-based compression (optional)
- [ ] Multi-vault federation
- [ ] Incremental backup to cloud (encrypted)
- [ ] CLI interface for manual inspection

## 🤝 Integration with OpenClaw

Add to your agent's session lifecycle:

```python
# On session start
vault = MemoryVault("./vault", get_master_password())
vault.load()
observer = ObservationObserver(vault)

# During conversation
observations = observer.observe_text(conversation)

# Before session end (auto-checkpoint)
checkpoint_id = vault.checkpoint()
vault.save()

# On restart - detect context death and recover
if context_was_lost():
    latest_checkpoint = find_latest_checkpoint()
    vault.restore_checkpoint(latest_checkpoint)
```

## ⚠️ Important Notes

1. **Password Management**: Lose the password = lose the memory. There's no recovery!
2. **Backup Regularly**: Encrypt your vault directory backups
3. **Test Restores**: Periodically verify you can restore from checkpoints
4. **Memory Limitations**: Python's garbage collection means secure deletion is best-effort
5. **Not FIPS Compliant**: Uses cryptography library which may not meet all compliance requirements

## 📄 License

MIT License - See LICENSE file

## 🙏 Credits

Inspired by [ClawVault](https://clawvault.dev/) - An AI Agent Memory System

Security patterns based on industry best practices for:
- AES-256-GCM authenticated encryption
- scrypt key derivation
- Secure file handling

---

*"The best agents don't just respond. They remember."*
