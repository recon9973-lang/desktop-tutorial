#!/usr/bin/env bash
# 한국 관측점의 열쇠를 만든다. **값은 화면에 출력하지 않는다.**
#
# 이 열쇠 하나로 두 곳을 잠근다:
#   Vercel  (veo-platform-web)  VEO_EGRESS_TOKEN
#   Railway (API)               VEO_EGRESS_KR_TOKEN
# 두 값이 같아야 한다. 다르면 API 가 401 을 받고, 경유는 조용히 실패한 뒤 원래 응답을
# 그대로 쓴다 — 진단은 죽지 않지만 막힌 사이트는 계속 못 잰다.
#
# 값은 클립보드로만 넘긴다. 터미널에 찍힌 비밀값은 스크롤 기록에도, 화면 공유에도,
# 나중에 누가 위로 올려 볼 때도 남는다.
#
# 사용법:  bash infra/scripts/make-egress-token.sh
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
ENV_FILE="$ROOT/.env"

if ! command -v pbcopy >/dev/null 2>&1; then
  echo "이 스크립트는 macOS 의 pbcopy 를 씁니다." >&2
  exit 1
fi

# 이미 있으면 다시 만들지 않는다. 새로 만들면 두 곳을 **동시에** 바꿔야 하는데,
# 그 사이에 배포가 돌면 경유가 401 로 죽는다.
EXISTING="$(grep '^VEO_EGRESS_KR_TOKEN=' "$ENV_FILE" 2>/dev/null | head -1 | cut -d= -f2- || true)"

if [ -n "$EXISTING" ]; then
  printf '%s' "$EXISTING" | pbcopy
  echo "이미 만들어 둔 열쇠를 클립보드에 넣었습니다 (값은 표시하지 않습니다)."
else
  # `tr </dev/urandom | head -c` 는 head 가 먼저 끝나면서 tr 을 SIGPIPE 로 죽인다.
  # `set -o pipefail` 아래에서는 그것이 종료코드 141 이 되어 스크립트가 조용히 멈춘다
  # (실제로 한 번 겪었다). 파이프 없이 한 번에 만든다.
  TOKEN="$(python3 -c 'import secrets; print(secrets.token_urlsafe(36))')"
  umask 077
  touch "$ENV_FILE"
  # 로컬에서도 같은 값을 쓰도록 .env 에 남긴다. 0600 이고 gitignore 되어 있다.
  printf '\n# 한국 관측점(경유) — Vercel 의 VEO_EGRESS_TOKEN 과 같은 값이어야 한다.\n' >> "$ENV_FILE"
  printf 'VEO_EGRESS_KR_URL=https://veo.seokorea.org/api/egress\n' >> "$ENV_FILE"
  printf 'VEO_EGRESS_KR_TOKEN=%s\n' "$TOKEN" >> "$ENV_FILE"
  chmod 600 "$ENV_FILE"
  printf '%s' "$TOKEN" | pbcopy
  echo "새 열쇠를 만들어 $ENV_FILE 에 저장하고 클립보드에 넣었습니다 (값은 표시하지 않습니다)."
fi

cat <<'GUIDE'

붙여넣을 곳은 두 군데입니다. 클립보드에 이미 들어 있으니 각각 붙여넣기만 하십시오.

  1) Vercel — 프로젝트 veo-platform-web
     Settings → Environment Variables → Add
       이름 : VEO_EGRESS_TOKEN
       값   : (붙여넣기)
       환경 : Production 체크
     저장한 뒤 Deployments 에서 맨 위 배포를 Redeploy 하십시오.
     환경변수는 **다시 배포해야** 적용됩니다.

  2) Railway — API 서비스
     Variables → New Variable 두 개
       VEO_EGRESS_KR_URL   = https://veo.seokorea.org/api/egress
       VEO_EGRESS_KR_TOKEN = (붙여넣기)
     저장하면 Railway 가 알아서 다시 띄웁니다.

둘 중 하나라도 빠지면 경유는 꺼진 것으로 동작합니다 — 지금과 똑같이 돌고, 막힌
사이트는 계속 "수집 실패" 로 보고됩니다. 진단이 깨지지는 않습니다.
GUIDE
