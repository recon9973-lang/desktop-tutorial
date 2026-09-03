#!/usr/bin/env bash
# SessionStart 훅용 — 컨테이너 리셋 대응: ask-gpt 설치 + 서브에이전트 글로벌 복사
set -euo pipefail

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$(pwd)}"
SRC="$PROJECT_DIR/scripts/ai/ask-gpt.sh"
DST_DIR="$HOME/bin"
DST="$DST_DIR/ask-gpt"

[ -f "$SRC" ] || { echo "install-ai-tools: $SRC 없음" >&2; exit 0; }

mkdir -p "$DST_DIR"
cp "$SRC" "$DST"
chmod +x "$DST"

# 이 세션 PATH에 노출
case ":$PATH:" in
  *":$DST_DIR:"*) ;;
  *)
    export PATH="$DST_DIR:$PATH"
    if [ -f "$HOME/.bashrc" ] && ! grep -q "$DST_DIR" "$HOME/.bashrc" 2>/dev/null; then
      echo "export PATH=\"$DST_DIR:\$PATH\"" >> "$HOME/.bashrc"
    fi
    ;;
esac

# 서브에이전트를 유저 글로벌로도 복사 (전 프로젝트 재사용)
if [ -d "$PROJECT_DIR/.claude/agents" ]; then
  mkdir -p "$HOME/.claude/agents"
  cp -f "$PROJECT_DIR/.claude/agents/"*.md "$HOME/.claude/agents/" 2>/dev/null || true
fi

# 상태 리포트 (한 줄)
if [ -n "${OPENAI_API_KEY:-}" ]; then
  echo "✓ ask-gpt 설치됨 · OPENAI_API_KEY 감지됨 (GPT 견제 활성)"
else
  echo "⚠ ask-gpt 설치됨 · OPENAI_API_KEY 미설정 (GPT 감시자 비활성)"
fi
