#!/usr/bin/env bash
#
# 다른 프로젝트(예: VENOM Marketing ERP)의 환경변수를 VEO 이름으로 옮긴다.
#
# 이 스크립트는 값을 화면에 절대 출력하지 않는다. 어떤 키가 설정됐는지 이름만 알린다.
# 터미널 기록, 셸 히스토리, 로그 어디에도 비밀값이 남지 않게 하기 위해서다.
#
# 사용법:
#   infra/scripts/import-provider-credentials.sh <원본_env_파일> [<원본_env_파일2> ...]
#
# 예:
#   infra/scripts/import-provider-credentials.sh ../your-supplement/.env ../flowlens/.env.local
#
# Vercel 에 있는 값은 먼저 내려받는다:
#   npx vercel env pull .env.erp --environment=production
#   infra/scripts/import-provider-credentials.sh .env.erp && rm -f .env.erp
#
set -euo pipefail

VEO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
TARGET="${VEO_ROOT}/.env"

if [[ $# -eq 0 ]]; then
  echo "사용법: $0 <원본_env_파일> [...]" >&2
  exit 2
fi

# 원본 이름 -> VEO 이름.
#
# 이름을 다시 짓는 이유: VEO 는 같은 '네이버'라도 검색광고(절대 검색량)와
# 데이터랩(상대 지수)을 서로 다른 데이터로 취급한다. 이름이 같으면 코드에서도
# 섞이기 시작한다.
MAPPINGS=(
  # 네이버 검색광고 — 절대 월간 검색량·클릭·CTR·경쟁도
  "NAVER_AD_API_KEY=VEO_NAVER_SEARCHAD_API_KEY"
  "NAVER_AD_SECRET=VEO_NAVER_SEARCHAD_SECRET_KEY"
  "NAVER_AD_CUSTOMER_ID=VEO_NAVER_SEARCHAD_CUSTOMER_ID"
  "NAVER_SEARCHAD_API_KEY=VEO_NAVER_SEARCHAD_API_KEY"
  "NAVER_SEARCHAD_SECRET_KEY=VEO_NAVER_SEARCHAD_SECRET_KEY"
  "NAVER_SEARCHAD_CUSTOMER_ID=VEO_NAVER_SEARCHAD_CUSTOMER_ID"

  # 네이버 개발자센터 — 데이터랩 상대 지수. 검색량이 아니다.
  "NAVER_CLIENT_ID=VEO_NAVER_DATALAB_CLIENT_ID"
  "NAVER_CLIENT_SECRET=VEO_NAVER_DATALAB_CLIENT_SECRET"

  # AI 답변 관측 및 의미 판단.
  # 엔진마다 답이 다르므로 각각 별도 측정이며, 하나의 노출률로 합치지 않는다.
  "OPENAI_API_KEY=VEO_OPENAI_API_KEY"
  "GOOGLE_AI_API_KEY=VEO_GOOGLE_GEMINI_API_KEY"
  "GEMINI_API_KEY=VEO_GOOGLE_GEMINI_API_KEY"
  "GOOGLE_GEMINI_API_KEY=VEO_GOOGLE_GEMINI_API_KEY"
  "PERPLEXITY_API_KEY=VEO_PERPLEXITY_API_KEY"
  "ANTHROPIC_API_KEY=VEO_ANTHROPIC_API_KEY"

  # 구글
  "GOOGLE_PAGESPEED_API_KEY=VEO_GOOGLE_PAGESPEED_API_KEY"
  "PAGESPEED_API_KEY=VEO_GOOGLE_PAGESPEED_API_KEY"
)

read_value() {
  # 원본 파일에서 KEY 의 값을 읽는다. 따옴표와 'export ' 접두사를 벗긴다.
  local file="$1" key="$2" line value
  line="$(grep -E "^[[:space:]]*(export[[:space:]]+)?${key}=" "$file" 2>/dev/null | tail -n 1 || true)"
  [[ -z "$line" ]] && return 1
  value="${line#*=}"
  value="${value%$'\r'}"
  # 앞뒤 따옴표 제거
  if [[ "$value" == \"*\" || "$value" == \'*\' ]]; then
    value="${value:1:${#value}-2}"
  fi
  [[ -z "$value" ]] && return 1
  printf '%s' "$value"
}

upsert() {
  # TARGET 에서 KEY 줄을 교체하거나 없으면 추가한다.
  local key="$1" value="$2" tmp
  tmp="$(mktemp)"
  chmod 600 "$tmp"
  if [[ -f "$TARGET" ]]; then
    grep -vE "^[[:space:]]*${key}=" "$TARGET" > "$tmp" || true
  fi
  printf '%s=%s\n' "$key" "$value" >> "$tmp"
  mv "$tmp" "$TARGET"
  chmod 600 "$TARGET"
}

touch "$TARGET"
chmod 600 "$TARGET"

imported=()
skipped=()

for source_file in "$@"; do
  if [[ ! -f "$source_file" ]]; then
    echo "  건너뜀: $source_file (파일 없음)" >&2
    continue
  fi
  for mapping in "${MAPPINGS[@]}"; do
    src_key="${mapping%%=*}"
    veo_key="${mapping##*=}"
    if value="$(read_value "$source_file" "$src_key")"; then
      upsert "$veo_key" "$value"
      imported+=("$veo_key")
      unset value
    fi
  done
done

# 중복 제거해서 이름만 보고한다. 값은 출력하지 않는다.
echo "VEO/.env 에 설정된 키:"
if [[ ${#imported[@]} -eq 0 ]]; then
  echo "  (없음 — 원본 파일에 해당 변수가 없습니다)"
else
  printf '  %s\n' "${imported[@]}" | sort -u
fi

# 아직 비어 있는 것도 이름만 알린다.
echo
echo "아직 없는 키 (해당 제공자는 DISABLED_NO_CREDENTIAL 로 동작):"
for veo_key in VEO_NAVER_SEARCHAD_API_KEY VEO_NAVER_SEARCHAD_SECRET_KEY \
               VEO_NAVER_SEARCHAD_CUSTOMER_ID VEO_NAVER_DATALAB_CLIENT_ID \
               VEO_NAVER_DATALAB_CLIENT_SECRET VEO_OPENAI_API_KEY \
               VEO_GOOGLE_GEMINI_API_KEY VEO_PERPLEXITY_API_KEY \
               VEO_ANTHROPIC_API_KEY VEO_GOOGLE_PAGESPEED_API_KEY; do
  if ! grep -qE "^${veo_key}=." "$TARGET" 2>/dev/null; then
    echo "  $veo_key"
  fi
done

echo
echo "확인:  make providers"
echo "주의:  .env 는 .gitignore 에 있습니다. 커밋되지 않는지 반드시 확인하세요."
