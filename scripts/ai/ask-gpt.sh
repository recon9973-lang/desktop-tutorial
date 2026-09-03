#!/usr/bin/env bash
# ask-gpt — OpenAI Chat Completions 래퍼 (JSON out 지원)
#
# 사용:
#   ask-gpt "질문 텍스트"
#   ask-gpt --model=gpt-5 --system=@path/to/system.md "질문"
#   ask-gpt --json "JSON으로만 답해"   # response_format=json_object
#   echo "질문" | ask-gpt --stdin
#
# 필수 env: OPENAI_API_KEY
# 의존:   curl, jq
set -euo pipefail

if [ -z "${OPENAI_API_KEY:-}" ]; then
  echo "ERROR: OPENAI_API_KEY 미설정. Claude Code Web의 Environment Variables에 등록하세요." >&2
  exit 2
fi
command -v jq >/dev/null 2>&1 || { echo "ERROR: jq 필요" >&2; exit 3; }

MODEL="${OPENAI_MODEL:-gpt-5}"
SYSTEM=""
JSON_MODE=0
FROM_STDIN=0
PROMPT=""

for a in "$@"; do
  case "$a" in
    --model=*)  MODEL="${a#*=}" ;;
    --system=@*) SYSTEM=$(cat "${a#*=@}") ;;
    --system=*)  SYSTEM="${a#*=}" ;;
    --json)      JSON_MODE=1 ;;
    --stdin)     FROM_STDIN=1 ;;
    --help|-h)
      sed -n '2,10p' "$0" | sed 's/^# //'; exit 0 ;;
    *)           PROMPT+="$a"$'\n' ;;
  esac
done

if [ "$FROM_STDIN" -eq 1 ]; then
  PROMPT=$(cat)
fi

if [ -z "$PROMPT" ]; then
  echo "ERROR: 질문이 비어 있음." >&2
  exit 4
fi

# 페이로드 구성 (system이 비어있으면 생략)
if [ -n "$SYSTEM" ]; then
  MSGS=$(jq -n --arg s "$SYSTEM" --arg p "$PROMPT" \
    '[{role:"system",content:$s},{role:"user",content:$p}]')
else
  MSGS=$(jq -n --arg p "$PROMPT" '[{role:"user",content:$p}]')
fi

if [ "$JSON_MODE" -eq 1 ]; then
  PAYLOAD=$(jq -n --arg m "$MODEL" --argjson msgs "$MSGS" \
    '{model:$m, messages:$msgs, response_format:{type:"json_object"}}')
else
  PAYLOAD=$(jq -n --arg m "$MODEL" --argjson msgs "$MSGS" \
    '{model:$m, messages:$msgs}')
fi

RESP=$(curl -sS --fail-with-body https://api.openai.com/v1/chat/completions \
  -H "Authorization: Bearer $OPENAI_API_KEY" \
  -H "Content-Type: application/json" \
  -d "$PAYLOAD" 2>&1) || {
    echo "ERROR: OpenAI API 호출 실패" >&2
    echo "$RESP" >&2
    exit 5
  }

echo "$RESP" | jq -r '.choices[0].message.content'
