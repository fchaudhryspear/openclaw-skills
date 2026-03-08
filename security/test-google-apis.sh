#!/bin/bash
GOOGLE=$(security find-generic-password -a optimus -s google-api-key -w 2>/dev/null)
echo "🧪 Google API Test — key: ${GOOGLE:0:15}... (${#GOOGLE} chars)"
echo ""

PASS=0; FAIL=0
models=(
  "gemini-2.5-flash"
  "gemini-2.5-pro"
  "gemini-2.0-flash"
  "gemini-2.0-flash-lite"
)

for model in "${models[@]}"; do
  R=$(curl -s --max-time 20 \
    "https://generativelanguage.googleapis.com/v1beta/models/${model}:generateContent?key=$GOOGLE" \
    -H "Content-Type: application/json" \
    -d '{"contents":[{"parts":[{"text":"Reply with only: OK"}]}]}')

  REPLY=$(echo "$R" | python3 -c "
import json,sys
d=json.load(sys.stdin)
t=d.get('candidates',[{}])[0].get('content',{}).get('parts',[{}])[0].get('text','')
err=d.get('error',{}).get('message','')
if t: print(t.strip()[:40])
elif err: print('ERR:'+err[:70])
else: print('EMPTY')
" 2>/dev/null)

  if [[ "$REPLY" == ERR:* ]]; then
    echo "❌ $model — $REPLY"
    FAIL=$((FAIL+1))
  else
    echo "✅ $model → \"$REPLY\""
    PASS=$((PASS+1))
  fi
done

echo ""
echo "Results: $PASS/$(($PASS+$FAIL)) passed"
