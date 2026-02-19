# Model Orchestrator v3.0 — Design Document

*Created: 2026-02-17 | Status: DESIGN*

---

## Philosophy

Don't use a $15/MTok model to do a $0.10/MTok model's job. Route every task to the **cheapest model that can do it well.** Escalate only when needed.

---

## The Roster

### Tier 0: Free / Unlimited (70% of work)

| Model | Cost (in/out per MTok) | Context | Role |
|-------|----------------------|---------|------|
| **google/gemini-1.5-flash** | FREE | 1M | **The Workhorse** — default for everything |

- Completely free tier on Google AI Studio
- 1M context window — massive docs, logs, codebases
- Fast inference, good enough for 70% of tasks
- Chat, lookups, file ops, simple Q&A, summaries
- **This is where most tokens should go — $0 cost**

### Tier 1: Premium Cheap / High-Volume (20% of work)

| Model | Cost (in/out per MTok) | Context | Role |
|-------|----------------------|---------|------|
| **google/gemini-2.5-flash** | $0.10 / $0.40 | 1M+ | **Value King** — when free tier isn't enough |

- 25x cheaper than Claude/GPT-4o
- Native video understanding (watch 2hr footage, find a 3-sec clip)
- 1M+ context window
- Smarter than 1.5-flash — use as the "data sifter" before sending to expensive models
- **Escalate here when 1.5-flash quality is insufficient**

### Tier 2: Specialist / Smart-Cheap (8% of work)

| Model | Cost (in/out per MTok) | Context | Role |
|-------|----------------------|---------|------|
| **xai/grok-3-mini** | ~$0.30 / ~$0.50 | 128K | **Smart Cheap** — reasoning at mini prices |
| **xai/grok-3** | ~$3.00 / ~$15.00 | 128K | **The "Now" Model** — real-time X/Twitter |
| **moonshot/kimi-k2.5** | $0.50 / $2.00 | 256K | **Swarm Architect** — parallel research |

**Grok 3 Mini:** Punches above weight on logic/reasoning. Perfect for chatbot-level tasks that need to be smarter than a script but don't justify flagship pricing. Replaces old Grok 4 Fast role.

**Grok 3 (Full):** The only model with real-time X firehose access. No knowledge cutoff — native instant access to global conversation. Use for: stock sentiment, breaking news, social monitoring. No overlap with any other model.

**Kimi K2.5:** Spawns multiple sub-agents for parallel research. Not a linear chatbot — it's an organization. Use for: competitor research, multi-source analysis, long document processing, writing style matching (cached). 256K context.

### Tier 3: Flagship / Precision (2% of work)

| Model | Cost (in/out per MTok) | Context | Role |
|-------|----------------------|---------|------|
| **anthropic/claude-sonnet-4** | $3.00 / $15.00 | 200K | **The Operator** — reasoning + computer use |
| **anthropic/claude-opus-4** | $15.00 / $75.00 | 200K | **The Architect** — hardest problems only |

**Claude Sonnet 4:** Best-in-class for code generation, tool orchestration, and computer use (UI navigation — click buttons, fill forms from screenshots). The "Chief of Staff" that handles complex multi-step work.

**Claude Opus 4:** Nuclear option. Only for the hardest reasoning, most critical decisions, or when Sonnet isn't cutting it. Current default — **needs to be moved to on-demand only.**

### Tier 4: Self-Hosted / Free (Future)

| Model | Cost | Role |
|-------|------|------|
| **alibaba/qwen-2.5-coder** | Free (self-hosted) | **Loop Coder** — rewrite functions 50x for $0 |
| **alibaba/qwen-2.5-math** | Free (self-hosted) | **Math Specialist** — calculus, financial modeling |

**Qwen Coder:** Open weights, run on local GPU or cheap provider (Groq/Together). When you need to iterate on code 50 times, don't pay Claude for each attempt.

**Qwen Math:** Trained specifically on math — not a humanities major that learned math as a second language. Financial modeling, logic puzzles, number-heavy work where generalists hallucinate.

*Self-hosted tier requires: local GPU or Groq/Together account. Deploy when ready.*

---

## Routing Decision Tree

```
Incoming Task
│
├─ Is it routine? (chat, lookup, file ops, simple Q&A)
│  └─ → Gemini 1.5 Flash (FREE)
│
├─ Routine but needs better quality / smarter reasoning?
│  └─ → Gemini 2.5 Flash ($0.10/MTok)
│
├─ Needs real-time news / social data?
│  └─ → Grok 3 Full (X firehose)
│
├─ Needs smart reasoning but not flagship?
│  └─ → Grok 3 Mini ($0.30/MTok)
│
├─ Needs parallel multi-source research?
│  └─ → Kimi K2.5 (agent swarm)
│
├─ Needs massive document/video processing?
│  └─ → Gemini 2.5 Flash (1M+ context, $0.10/MTok)
│
├─ Needs code generation / tool orchestration / UI control?
│  └─ → Claude Sonnet 4 ($3/MTok)
│
├─ Needs hardest reasoning / critical decisions?
│  └─ → Claude Opus 4 ($15/MTok) — spawn as sub-agent
│
├─ Needs iterative code rewrites (50+ attempts)?
│  └─ → Qwen Coder (free, self-hosted)
│
├─ Needs pure math / financial modeling?
│  └─ → Qwen Math (free, self-hosted)
│
└─ Unsure?
   └─ → Start with Gemini Flash, escalate if quality insufficient
```

---

## Cost Projections

### Current (All Claude Opus 4)
- ~$15-75/MTok
- Estimated: $10-30/day for conversation alone
- Monthly: $300-900

### Target (Orchestrated)

| Tier | Model | Workload % | Daily Cost |
|------|-------|-----------|------------|
| Free | Gemini 1.5 Flash | 70% | $0.00 |
| Cheap | Gemini 2.5 Flash | 20% | ~$0.20-0.80 |
| Specialist | Grok Mini + K2.5 | 5% | ~$0.20-0.50 |
| Real-time | Grok 3 Full | 1% | ~$0.10-0.30 |
| Flagship | Claude Sonnet 4 | 3% | ~$0.50-1.00 |
| Nuclear | Claude Opus 4 | 1% | ~$0.20-0.50 |
| **Total** | | **100%** | **~$1.20-3.10/day** |

**Monthly: ~$36-93** (vs $300-900 current = **88-96% savings**)

### Future (With Self-Hosted)

| Addition | Impact |
|----------|--------|
| Qwen Coder (self-hosted) | Code iteration → $0 |
| Qwen Math (self-hosted) | Math tasks → $0 |
| **Projected Monthly** | **~$30-90** |

---

## Implementation Plan

### Phase 1: Switch Default Model ⏳
1. Switch OpenClaw default from Claude Opus → Gemini 1.5 Flash (FREE)
2. Add Gemini 2.5 Flash as quality escalation
3. Keep Claude available via `/model` command or explicit request
4. Requires: Google/Gemini API key

### Phase 2: Auto-Escalation Behavior ⏳
1. Define complexity triggers in AGENTS.md
2. Auto-spawn Claude sub-agents for complex tasks
3. Criteria:
   - Multi-step reasoning → Claude Sonnet (sub-agent)
   - Code architecture/debugging → Claude Sonnet (sub-agent)
   - Critical business decisions → Claude Opus (sub-agent)
   - Everything else → Gemini Flash (main session)

### Phase 3: Specialist Integration ⏳
1. Add Grok 3 API key (xAI)
2. Add Kimi K2.5 API key (Moonshot)
3. Route real-time queries → Grok 3
4. Route parallel research → Kimi K2.5
5. Route smart-cheap reasoning → Grok 3 Mini

### Phase 4: Self-Hosted Tier (Future) ⏳
1. Set up Qwen Coder on Groq/Together or local GPU
2. Set up Qwen Math similarly
3. Route iterative coding and math tasks → free tier

### Phase 5: Email Automation Revival (Future) ⏳
1. Rebuild email-to-tasks with Grok Mini (extraction)
2. Rebuild auto-reply with K2.5 (style matching, cached)
3. Rebuild calendar sync
4. Daily summary via Gemini Flash

---

## Unique Model Capabilities (No Overlap)

| Model | Unique Superpower | No Other Model Can... |
|-------|-------------------|----------------------|
| **Grok 3** | Real-time X firehose | Access live Twitter/X data natively |
| **Kimi K2.5** | Native agent swarm | Spawn parallel sub-agents for research |
| **Claude Sonnet** | Computer Use (UI) | Reliably click buttons in screenshots |
| **Gemini Flash** | 1M+ native video | Watch 2hr video and find a 3-sec clip |
| **Qwen Math** | Pure math weights | Solve calculus without hallucinating |
| **Qwen Coder** | Free (open weights) | Iterate code 50x for $0 |

---

## API Keys Needed

| Provider | Model(s) | Status | Key Location |
|----------|----------|--------|-------------|
| Google | Gemini 2.5 Flash | ❌ Need key | OpenClaw auth profile |
| Anthropic | Claude Sonnet/Opus | ✅ Active | OpenClaw auth profile |
| xAI | Grok 3 / Grok 3 Mini | ❌ Need key | OpenClaw auth profile |
| Moonshot | Kimi K2.5 | ❌ Need key | OpenClaw auth profile |
| Groq/Together | Qwen Coder/Math | ❌ Future | Self-hosted config |

---

## Quick Reference

```
"Just chat with me"          → Gemini 1.5 Flash (FREE)
"Summarize this doc"         → Gemini 1.5 Flash (FREE)
"Need better quality"        → Gemini 2.5 Flash
"What's trending on X?"      → Grok 3
"Research this competitor"    → Kimi K2.5 (swarm)
"Debug this code"             → Claude Sonnet (sub-agent)
"Watch this video for X"     → Gemini Flash (1M context)
"Solve this equation"         → Qwen Math (future)
"Rewrite this function"      → Qwen Coder (future)
"Make a critical decision"   → Claude Opus (sub-agent)
"Read these 100 PDFs"        → Gemini 1.5 Flash (FREE, 1M context)
"Check stock sentiment now"  → Grok 3 (X firehose)
```

---

*This replaces the old 3-model system (Grok 4 Fast / K2.5 / Claude). Same philosophy, more models, smarter routing, lower costs.*
