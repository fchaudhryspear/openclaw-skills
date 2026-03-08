#!/bin/bash
# ================================================================
# test-all-apis.sh — Full API connectivity test for all providers
# Run: bash ~/.openclaw/workspace/security/test-all-apis.sh
# ================================================================

echo "🧪 API Connectivity Test — $(date)"
echo ""

PASS=0; FAIL=0

test_api() {
  local name="$1"; local result="$2"
  # Extract reply text
  REPLY=$(echo "$result" | python3 -c "
import json,sys
try:
    d=json.load(sys.stdin)
    for path in [['content',0,'text'],['choices',0,'message','content'],['candidates',0,'content','parts',0,'text']]:
        try:
            v=d
            for k in path: v=v[k]
            print(v.strip()[:50])
            sys.exit(0)
        except: pass
    err=d.get('error',{})
    if err: print('ERR:'+err.get('message','?')[:60]); sys.exit(1)
    sys.exit(1)
except: sys.exit(1)
" 2>/dev/null)

  if [[ -n "$REPLY" && "$REPLY" != ERR:* ]]; then
    echo "✅ $name → \"$REPLY\""
    PASS=$((PASS+1))
  else
    echo "❌ $name — ${REPLY:-no response}"
    FAIL=$((FAIL+1))
  fi
}

# Load from Keychain
ANTHROPIC=$(security find-generic-password -a optimus -s anthropic-api-key -w 2>/dev/null)
OPENAI=$(security find-generic-password -a optimus -s openai-api-key -w 2>/dev/null)
GOOGLE=$(security find-generic-password -a optimus -s google-api-key -w 2>/dev/null)
XAI=$(security find-generic-password -a optimus -s xai-api-key -w 2>/dev/null)
MOONSHOT=$(security find-generic-password -a optimus -s moonshot-api-key -w 2>/dev/null)
QWEN=$(security find-generic-password -a optimus -s qwen-sg-api-key -w 2>/dev/null)
BRAVE=$(security find-generic-password -a optimus -s brave-api-key -w 2>/dev/null)
AWS_KEY=$(security find-generic-password -a optimus -s aws-access-key-id -w 2>/dev/null)

echo "Keys loaded from Keychain:"
echo "  Anthropic : ${#ANTHROPIC} chars"
echo "  OpenAI    : ${#OPENAI} chars"
echo "  Google    : ${#GOOGLE} chars"
echo "  XAI       : ${#XAI} chars"
echo "  Moonshot  : ${#MOONSHOT} chars"
echo "  Qwen SG   : ${#QWEN} chars"
echo "  Brave     : ${#BRAVE} chars"
echo "  AWS Key   : ${#AWS_KEY} chars"
echo ""

# ── Anthropic ──
echo "Testing Anthropic..."
R=$(curl -s --max-time 15 https://api.anthropic.com/v1/messages \
  -H "x-api-key: $ANTHROPIC" \
  -H "anthropic-version: 2023-06-01" \
  -H "content-type: application/json" \
  -d '{"model":"claude-haiku-4-5-20251001","max_tokens":10,"messages":[{"role":"user","content":"Reply: OK"}]}')
test_api "Anthropic — claude-haiku-4-5" "$R"

# ── OpenAI ──
echo "Testing OpenAI..."
R=$(curl -s --max-time 15 https://api.openai.com/v1/chat/completions \
  -H "Authorization: Bearer $OPENAI" \
  -H "Content-Type: application/json" \
  -d '{"model":"gpt-4o-mini","max_tokens":10,"messages":[{"role":"user","content":"Reply: OK"}]}')
test_api "OpenAI — gpt-4o-mini" "$R"

# ── Google Gemini ──
echo "Testing Google Gemini..."
R=$(curl -s --max-time 15 "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key=$GOOGLE" \
  -H "Content-Type: application/json" \
  -d '{"contents":[{"parts":[{"text":"Reply: OK"}]}]}')
test_api "Google — gemini-2.0-flash" "$R"

# ── XAI Grok ──
echo "Testing XAI Grok..."
R=$(curl -s --max-time 15 https://api.x.ai/v1/chat/completions \
  -H "Authorization: Bearer $XAI" \
  -H "Content-Type: application/json" \
  -d '{"model":"grok-3-mini","max_tokens":10,"messages":[{"role":"user","content":"Reply: OK"}]}')
test_api "XAI — grok-3-mini" "$R"

# ── Moonshot / Kimi ──
echo "Testing Moonshot/Kimi..."
R=$(curl -s --max-time 20 https://api.moonshot.cn/v1/chat/completions \
  -H "Authorization: Bearer $MOONSHOT" \
  -H "Content-Type: application/json" \
  -d '{"model":"moonshot-v1-8k","max_tokens":10,"messages":[{"role":"user","content":"Reply: OK"}]}')
test_api "Moonshot — moonshot-v1-8k" "$R"

# ── Qwen Singapore (Plus) ──
echo "Testing Qwen Singapore..."
R=$(curl -s --max-time 15 https://dashscope-intl.aliyuncs.com/compatible-mode/v1/chat/completions \
  -H "Authorization: Bearer $QWEN" \
  -H "Content-Type: application/json" \
  -d '{"model":"qwen-plus","max_tokens":10,"messages":[{"role":"user","content":"Reply: OK"}]}')
test_api "Qwen — qwen-plus (SG)" "$R"

# ── Qwen Flash ──
echo "Testing Qwen Flash..."
R=$(curl -s --max-time 15 https://dashscope-intl.aliyuncs.com/compatible-mode/v1/chat/completions \
  -H "Authorization: Bearer $QWEN" \
  -H "Content-Type: application/json" \
  -d '{"model":"qwen-turbo","max_tokens":10,"messages":[{"role":"user","content":"Reply: OK"}]}')
test_api "Qwen — qwen-turbo (SG)" "$R"

# ── Brave Search ──
echo "Testing Brave Search..."
R=$(curl -s --max-time 10 "https://api.search.brave.com/res/v1/web/search?q=hello+world&count=1" \
  -H "Accept: application/json" \
  -H "X-Subscription-Token: $BRAVE")
COUNT=$(echo "$R" | python3 -c "import json,sys; d=json.load(sys.stdin); print(len(d.get('web',{}).get('results',[])))" 2>/dev/null)
if [[ "$COUNT" -gt 0 ]]; then
  echo "✅ Brave Search — $COUNT result(s)"
  PASS=$((PASS+1))
else
  echo "❌ Brave Search — 0 results or error"
  FAIL=$((FAIL+1))
fi

# ── AWS ──
echo "Testing AWS..."
if [[ -n "$AWS_KEY" ]]; then
  AWS_SECRET=$(security find-generic-password -a optimus -s aws-secret-access-key -w 2>/dev/null)
  R=$(AWS_ACCESS_KEY_ID=$AWS_KEY AWS_SECRET_ACCESS_KEY=$AWS_SECRET \
    aws sts get-caller-identity --output json 2>/dev/null)
  ACCT=$(echo "$R" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('Account','?'))" 2>/dev/null)
  if [[ -n "$ACCT" ]]; then
    echo "✅ AWS — Account: $ACCT"
    PASS=$((PASS+1))
  else
    echo "❌ AWS — not configured (run keychain-rotate.sh with new IAM keys)"
    FAIL=$((FAIL+1))
  fi
else
  echo "⚠️  AWS — no keys in Keychain yet (generate from IAM console)"
  FAIL=$((FAIL+1))
fi

# ── Summary ──
echo ""
echo "══════════════════════════════════"
echo "  Results: $PASS passed / $((PASS+FAIL)) total"
[[ $FAIL -eq 0 ]] && echo "  🎉 All APIs working!" || echo "  ⚠️  $FAIL API(s) need attention"
echo "══════════════════════════════════"
