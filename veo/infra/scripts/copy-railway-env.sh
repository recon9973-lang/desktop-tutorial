#!/usr/bin/env bash
# 배포용 환경변수 묶음을 클립보드에 넣는다. Railway 의 Raw Editor 에 붙여넣으면 된다.
#
# 값을 화면에 출력하지 않는다. 넣은 항목의 *이름만* 보여 준다. 배포 설정을 옮기는 일은
# 비밀값을 한 번씩 더 눈에 띄게 만들기 쉬운데, 터미널에 찍힌 값은 스크롤 기록에도,
# 화면 공유에도 남는다.
#
# 사용법:  bash infra/scripts/copy-railway-env.sh [콘솔주소]
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
ENV_FILE="$ROOT/.env"
CONSOLE_URL="${1:-}"

if [ ! -f "$ENV_FILE" ]; then
  echo "$ENV_FILE 이 없습니다." >&2
  exit 1
fi

value_of() { grep "^$1=" "$ENV_FILE" | head -1 | cut -d= -f2- || true; }

# 서버가 뜨려면 반드시 있어야 하는 값들. production 에서는 암호화 키가 없으면
# 애플리케이션이 시작조차 하지 않는다 — 조용히 망가진 금고보다 안 켜지는 쪽이 낫다.
REQUIRED=(VEO_DATABASE_URL VEO_JWT_SECRET VEO_CREDENTIAL_ENCRYPTION_KEY)
# 없어도 뜨지만, 없으면 해당 지표가 '측정 불가'가 된다.
OPTIONAL=(
  VEO_NAVER_SEARCHAD_API_KEY VEO_NAVER_SEARCHAD_SECRET_KEY VEO_NAVER_SEARCHAD_CUSTOMER_ID
  VEO_NAVER_DATALAB_CLIENT_ID VEO_NAVER_DATALAB_CLIENT_SECRET
)

missing=()
for key in "${REQUIRED[@]}"; do
  [ -z "$(value_of "$key")" ] && missing+=("$key")
done
if [ ${#missing[@]} -gt 0 ]; then
  echo "다음 값이 .env 에 없습니다: ${missing[*]}" >&2
  exit 1
fi

BLOCK="VEO_ENVIRONMENT=production
VEO_LOG_FORMAT=json"

for key in "${REQUIRED[@]}" "${OPTIONAL[@]}"; do
  v="$(value_of "$key")"
  [ -n "$v" ] && BLOCK="$BLOCK
$key=$v"
done

if [ -n "$CONSOLE_URL" ]; then
  # 초대 링크가 가리키는 주소. 틀리면 링크는 발급되는데 아무 데도 가지 않는다.
  BLOCK="$BLOCK
VEO_CONSOLE_BASE_URL=$CONSOLE_URL
VEO_CORS_ALLOWED_ORIGINS=$CONSOLE_URL"
fi

printf '%s' "$BLOCK" | pbcopy

echo "클립보드에 복사했습니다. Railway 의 Variables → Raw Editor 에 붙여넣으십시오."
echo
echo "포함된 항목 (값은 표시하지 않음):"
printf '%s\n' "$BLOCK" | while IFS= read -r line; do
  echo "  ${line%%=*}"
done
echo
if [ -z "$CONSOLE_URL" ]; then
  echo "VEO_CONSOLE_BASE_URL 은 포함되지 않았습니다."
  echo "  콘솔 주소가 정해지면 인자로 넘겨 다시 실행하십시오:"
  echo "  bash infra/scripts/copy-railway-env.sh https://veo.seokorea.org"
  echo "  이 값이 없으면 직원 초대 링크가 잘못된 주소를 가리킵니다."
fi
