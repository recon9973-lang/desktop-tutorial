#!/usr/bin/env bash
# GROUND(@ground_geo) 인스타그램 사진 3장 발행 (영상 취소, 사진만).
# 이미지는 공개 CDN(jsDelivr)에 호스팅돼 있어 그대로 image_url로 사용.
#
# 실행 (토큰 있는 어디서든):
#   IG_ID=17841472664941872 TOKEN=<INSTAGRAM_ACCESS_TOKEN> bash publish-ig.sh
#
# 필요: bash, curl, python3
set -euo pipefail

: "${IG_ID:?INSTAGRAM_BUSINESS_ID(=17841472664941872) 를 IG_ID 로 지정하세요}"
: "${TOKEN:?INSTAGRAM_ACCESS_TOKEN 을 TOKEN 으로 지정하세요}"
GV="${GRAPH_VERSION:-v21.0}"
BASE="https://graph.facebook.com/${GV}"

# 공개 이미지 URL(커밋 SHA 고정) — 안정적으로 접근 가능.
IMG_BASE="https://cdn.jsdelivr.net/gh/recon9973-lang/desktop-tutorial@2b9583686e9bac72339740fb6e15ad93114fcfe4/persona-nami/ig"

IMAGES=(
  "${IMG_BASE}/post1.png"
  "${IMG_BASE}/post2.png"
  "${IMG_BASE}/post3.png"
)

CAP1="요즘 저희 엄마도 궁금한 거 있으면 초록창 대신 챗지피티한테 물어보시더라고요 😅

검색이 '링크 고르기'에서 '답 하나 받기'로 바뀌는 중이에요. 그래서 이제 마케팅은 '검색 1등'이 아니라 → AI가 콕 집어 골라주는 그 답이 되는 것이 핵심이에요.

이걸 GEO(생성형 엔진 최적화)라고 불러요. 어렵지 않아요, 여기서 하나씩 같이 풀어봐요!

여러분은 요즘 검색, 어디서 하세요? 👇

#GEO #AI검색 #마케팅 #GROUND #검색마케팅 #디지털마케팅"

CAP2="궁금해서 진짜 해봤어요. ChatGPT한테 \"○○ 잘하는 곳 추천해줘\" 했더니… 우리는 언급도 안 되더라고요 🥲

AI는 '검색 순위'가 아니라 '믿을 만한 정보'를 골라서 인용하거든요. 그래서 요즘 AEO(답변 엔진 최적화)가 중요해졌어요.

오늘은 핵심 3가지만!
1️⃣ 질문–답 형식으로 쓰기
2️⃣ 출처·근거 확실하게
3️⃣ FAQ 구조화(스키마)

내일 하나씩 자세히 올릴게요 📌 궁금한 거 댓글 주세요!

#AEO #챗지피티 #콘텐츠마케팅 #GROUND #검색마케팅 #디지털마케팅"

CAP3="스압 없이 딱 3줄이면 돼요 😎

SEO는 이제 '키워드 많이 넣기'가 아니에요.
① 사람이 진짜 궁금한 걸 → ② 명확하게 답하고 → ③ 검색엔진이랑 AI 둘 다 이해하게 정리하기.

이 셋만 지켜도 절반은 먹고 들어가요.

저장해두고 글 쓸 때 꺼내보세요 🔖

#SEO #검색최적화 #마케팅꿀팁 #GROUND #검색마케팅 #디지털마케팅"

CAPTIONS=("$CAP1" "$CAP2" "$CAP3")

publish_one() {
  local img="$1" cap="$2" idx="$3"
  echo "──────── 포스팅 ${idx} ────────"
  echo "→ 컨테이너 생성: ${img}"
  local resp creation
  resp=$(curl -sS -X POST "${BASE}/${IG_ID}/media" \
    --data-urlencode "image_url=${img}" \
    --data-urlencode "caption=${cap}" \
    -d "access_token=${TOKEN}")
  creation=$(printf '%s' "$resp" | python3 -c 'import sys,json;d=json.load(sys.stdin);print(d.get("id",""))' 2>/dev/null || true)
  if [ -z "$creation" ]; then
    echo "✗ 컨테이너 생성 실패: $resp"; return 1
  fi
  # 사진은 대개 즉시 준비됨 — 안전하게 상태 확인.
  for _ in 1 2 3 4 5; do
    local st
    st=$(curl -sS "${BASE}/${creation}?fields=status_code&access_token=${TOKEN}" \
      | python3 -c 'import sys,json;print(json.load(sys.stdin).get("status_code",""))' 2>/dev/null || true)
    [ "$st" = "FINISHED" ] && break
    sleep 2
  done
  echo "→ 발행(creation_id=${creation})"
  local pub
  pub=$(curl -sS -X POST "${BASE}/${IG_ID}/media_publish" \
    -d "creation_id=${creation}" -d "access_token=${TOKEN}")
  echo "✓ 결과: $pub"
  echo
}

echo "GROUND 인스타 사진 3장 발행 시작 (영상 취소)"
for i in 0 1 2; do
  publish_one "${IMAGES[$i]}" "${CAPTIONS[$i]}" "$((i+1))" || echo "‼ 포스팅 $((i+1)) 실패 — 다음 계속"
  # 인스타 API 레이트리밋 여유 (연속 발행 간 간격)
  [ "$i" -lt 2 ] && sleep 30
done
echo "완료. @ground_geo 프로필에서 확인하세요."
