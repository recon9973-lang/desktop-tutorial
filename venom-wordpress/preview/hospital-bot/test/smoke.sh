#!/usr/bin/env bash
# 베노미 배포 스모크 테스트 — 실측 엔드포인트 점검
#   BASE=https://<배포도메인> ./hospital-bot/test/smoke.sh "대구 수성구 OO치과"
# jq 있으면 예쁘게, 없으면 원본 출력.
set -u
BASE="${BASE:-http://localhost:3000}"
HOSP="${1:-대구 수성구 OO치과}"
pp(){ if command -v jq >/dev/null 2>&1; then jq "$@"; else cat; fi; }

echo "▶ BASE=$BASE  병원=$HOSP"
echo; echo "== 1) 상태·키 설정 =="
curl -s "$BASE/api/hospital-bot" | pp '.config // .'

echo; echo "== 2) 종합 진단(GEO light) =="
curl -s --get "$BASE/api/hospital-bot" --data-urlencode "hospital=$HOSP" \
  | pp '{grade:.summary.grade, urgent:.summary.urgent, seo:.seo.score100, blog:.local.blog.total, topKw:.ads.keywords[0], geo:.geo.status}'

echo; echo "== 3) GEO 실측(느림 20~30초) =="
curl -s --get "$BASE/api/hospital-bot" --data-urlencode "hospital=$HOSP" --data-urlencode "geo=1" \
  | pp '.geo | {status, grade, citationRate, shareOfVoice, sentiment, engines}'

echo; echo "웹 리포트: $BASE/hospital-bot/report.html?hospital=$(python3 -c "import urllib.parse,sys;print(urllib.parse.quote(sys.argv[1]))" "$HOSP" 2>/dev/null || echo "$HOSP")"
