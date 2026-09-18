#!/usr/bin/env bash
# SessionStart 훅 — 이 방 인계를 세션 시작 컨텍스트에 넣는다.
#
# ## 이름이 아니라 가지로 고른다
#
# 전에는 `RESUME.md` 라는 **이름** 하나만 폈다. 방이 여럿이라 그 이름이 자리
# 다툼이 됐다 — 같은 이름에 쓰면 마지막 방만 남아 앞 방 인계가 조용히 사라지고,
# 제 이름으로 가르면 안 지워지는 대신 훅이 영영 안 읽었다. 둘 다 실제로 났다
# [실측 2026-09-10 · 이 파일의 옛 주석].
#
# 이제 **가지로 고른다.** 방 파일 머리 스무 줄 안에 이 표시를 둔다.
#
#     <!-- 가지: claude/<가지-이름> -->
#
# 훅은 지금 가지와 같은 표시를 단 파일 **하나만** 편다. 그래서 이름이 무엇이든
# 제 방 것이 실린다 — `RESUME.md` 라는 이름에 값이 없어지고 다툴 까닭도 없어진다.
#
# 표시가 없거나 짝이 없으면 **전처럼** 목록을 보이고 `RESUME.md` 본문만 편다.
# 물러서는 길을 남겨 둔 것이라 표시를 아직 안 단 방도 굶지 않는다.
set -eu
dir="${CLAUDE_PROJECT_DIR:-.}"
# `symbolic-ref` 는 커밋이 하나도 없는 새 가지에서도 이름을 준다(`rev-parse` 는 «HEAD» 를
# 내놓아 엉뚱한 짝을 부를 수 있다). 머리가 떨어져 있으면 빈 값이 되고 아래에서 물러선다.
branch="$(git -C "$dir" symbolic-ref --short -q HEAD 2>/dev/null || true)"

files=""
if [ -f "$dir/RESUME.md" ]; then files="$dir/RESUME.md"; fi
for f in "$dir"/RESUME-*.md; do
  if [ -f "$f" ]; then files="$files $f"; fi
done
if [ -z "$files" ]; then exit 0; fi

# ① 가지로 제 방 것 찾기
mine=""
if [ -n "$branch" ] && [ "$branch" != "HEAD" ]; then
  for f in $files; do
    if head -20 "$f" | grep -qF "<!-- 가지: $branch -->"; then mine="$f"; break; fi
  done
fi

if [ -n "$mine" ]; then
  echo "===== 이어갈 작업: $(basename "$mine") — 이 방 것 (가지 $branch) ====="
  cat "$mine"
  echo "===== RESUME 끝 · 위 '바로 이어갈 작업'부터 재개하세요 ====="
  exit 0
fi

# ② 짝이 없다 — 목록을 보이고 RESUME.md 만 편다(본문을 다 펴면 방 수만큼 토큰이 분다)
count=0
for f in $files; do count=$((count + 1)); done

echo "===== 이어갈 작업: 인계(RESUME) ====="
if [ "$count" -gt 1 ]; then
  echo "[인계 파일 ${count}개 · 이 가지(${branch:-«못 잼»})에 짝이 없다] **제 방 것을 직접 읽어라.**"
  for f in $files; do
    title=$(head -5 "$f" | grep -m1 '^# ' || true)
    echo "  · $(basename "$f")${title:+  — ${title#\# }}"
  done
  echo
  echo "제 방 것을 찾았으면 그 파일 머리에 «<!-- 가지: ${branch:-<가지>} -->» 를 한 줄 달아라."
  echo "다음 세션부터 훅이 그 파일만 펴 준다(목록을 훑을 일이 없어진다)."
  echo
fi
if [ -f "$dir/RESUME.md" ]; then cat "$dir/RESUME.md"; fi
echo "===== RESUME 끝 · 위 '바로 이어갈 작업'부터 재개하세요 ====="
exit 0
