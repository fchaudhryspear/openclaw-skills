#!/usr/bin/env python3
"""Calculate real costs from session token data"""

import json, subprocess

# Fetch sessions
result = subprocess.run(['openclaw', 'sessions', '--json'], capture_output=True, text=True)
raw = result.stdout

# Handle null values
for line in raw.split('\n'):
    if 'null' in line:
        raw = raw.replace('null', '"NULL"')

data = json.loads(raw)
sessions = data.get('sessions', [])

PRICING = {
    'anthropic/claude-sonnet-4-6': {'input': 3.00, 'output': 15.00},
    'anthropic/claude-opus-4-6': {'input': 5.00, 'output': 25.00},
    'moonshot/kimi-k2.5': {'input': 0.60, 'output': 2.50},
    'alibaba-sg/qwen3.5-122b-a10b': {'input': 0.40, 'output': 1.20},
    'google/gemini-2.5-flash': {'input': 0.10, 'output': 0.40},
    'xai/grok-3-mini': {'input': 0.30, 'output': 0.60},
}

by_model = {}
total_tokens = 0
total_cost = 0

for s in sessions:
    model = s.get('model') or 'unknown'
    tokens = s.get('totalTokens')
    if tokens is None or tokens == "NULL" or tokens == 0:
        continue
    
    total_tokens += tokens
    input_t = int(tokens * 0.7)
    output_t = int(tokens * 0.3)
    
    p = PRICING.get(model, {'input': 0.10, 'output': 0.40})
    cost = (input_t / 1e6 * p['input']) + (output_t / 1e6 * p['output'])
    
    if model not in by_model:
        by_model[model] = {'tokens': 0, 'cost': 0}
    by_model[model]['tokens'] += tokens
    by_model[model]['cost'] += cost
    total_cost += cost

sorted_models = sorted(by_model.items(), key=lambda x: x[1]['cost'], reverse=True)

print("=" * 75)
print("MATH FROM SESSION TOKENS (using real pricing)")
print("=" * 75)
print(f"\n{'Model':<35} {'Runs':>6} {'Tokens':>12} {'Cost':>12}")
print("-" * 75)
for model, d in sorted_models[:10]:
    short = model.split('/')[-1][:32]
    print(f"{short:<35} {d['tokens']//1000:>5}K tok   ${d['cost']:>8.2f}")

print("-" * 75)
print(f"{'TOTAL':<35} {(total_tokens//1000):>5}K tok   ${total_cost:>8.2f}")
print("=" * 75)
print(f"\nYour Claude dashboard showed: $34.15")
print(f"Our calculation from sessions: ${total_cost:.2f}")
print(f"Gap: ${abs(34.15 - total_cost):.2f}")
if total_cost < 30:
    print("\n⚠️  BIG GAP — Most traffic isn't going through OpenClaw sessions!")
    print("   Check clawbot_mm_3_2026 workspace directly on claude.com")
