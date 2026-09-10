#!/usr/bin/env bash
# SessionStart 훅 — 인계(RESUME)를 세션 시작 컨텍스트로 주입한다.
# 다음 세션이 "저장한 프롬프트 불러오기"를 자동으로 수행하는 장치.
#
# ## 방이 여럿이면 이름 하나로는 모자란다
#
# 전에는 `RESUME.md` **하나만** 읽었다. 방이 여럿인데 이름이 하나라 두 길로 깨진다:
#
#     같은 이름에 쓴다   → 마지막에 쓴 방만 남고 **앞 방 인계가 조용히 사라진다**
#     제 이름에 쓴다     → 안 지워지는 대신 **훅이 영영 안 읽는다**
#
# [실측 2026-09-10] 둘 다 실제로 났다. 「자동 진단 방」이 남의 것을 안 덮으려고
# `RESUME-aeo-grand.md` 로 갈랐더니, 그 방 인계가 시작 컨텍스트에 한 줄도 안 실렸다.
#
# 그래서 **있는 것을 전부 이름으로 먼저 보인다.** 본문은 `RESUME.md` 만 편다 —
# 다 펴면 방 수만큼 토큰이 불어난다(그것을 아끼려고 만든 장치다). 제 방 것이
# 따로 있으면 목록에서 보고 그 파일을 열면 된다.
set -eu
dir="${CLAUDE_PROJECT_DIR:-.}"

# 방별 인계. 없으면 빈 값이다(`nullglob` 대신 존재 검사로 — sh 이식성).
rooms=""
for f in "$dir"/RESUME-*.md; do
  [ -f "$f" ] && rooms="$rooms $f"
done

[ -f "$dir/RESUME.md" ] || [ -n "$rooms" ] || exit 0

# 인계가 **하나뿐이면** 이름이 무엇이든 그것을 편다 — 목록만 주면 그 방은 제 인계를
# 못 받는다. 여럿일 때만 목록을 앞세우고 본문은 `RESUME.md` 만 편다.
count=0
[ -f "$dir/RESUME.md" ] && count=$((count + 1))
for f in $rooms; do count=$((count + 1)); done

echo "===== 이어갈 작업: 인계(RESUME) ====="

if [ "$count" -gt 1 ]; then
  echo "[인계 파일 ${count}개] 이 저장소에 인계가 여럿이다 — **제 방 것을 읽어라.**"
  [ -f "$dir/RESUME.md" ] && echo "  · RESUME.md (아래 본문)"
  for f in $rooms; do
    # 첫 제목 줄로 어느 방 것인지 보인다. 없으면 파일 이름만.
    title=$(head -5 "$f" | grep -m1 '^# ' || true)
    echo "  · $(basename "$f")${title:+  — ${title#\# }}"
  done
  echo
fi

if [ -f "$dir/RESUME.md" ]; then
  cat "$dir/RESUME.md"
elif [ "$count" -eq 1 ]; then
  for f in $rooms; do cat "$f"; done
fi
echo "===== RESUME 끝 · 위 '바로 이어갈 작업'부터 재개하세요 ====="
exit 0
