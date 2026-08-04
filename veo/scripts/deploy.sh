#!/usr/bin/env bash
#
# 배포 — CI 가 초록불일 때만 main 에 닿는다.
#
# **왜 이 파일이 있는가.** 2026-08-04, CI 가 12번 연속 빨간불인 채로 배포가 계속됐다.
# 그중 하나는 v0.3.34 에서 들어간 `read_captures` 미정의였고, 그 창구는 열자마자 500 이
# 났다. ruff 가 그것을 첫 판부터 잡아 두었는데 아무도 보지 않았다. 매번 "배포 완료" 라고
# 보고됐다.
#
# GitHub 의 가지 보호로 막으려 했으나, 비공개 저장소 + 무료 요금제에서는 규칙이
# **적용되지 않는다**:
#
#     $ gh api repos/.../rules/branches/main
#     Upgrade to GitHub Pro or make this repository public to enable this feature. (403)
#
# 규칙을 만들어 두면 화면에는 Active 로 보이지만 아무것도 막지 않는다. 그래서 관문을
# 여기에 둔다 — 돈을 쓰지 않고, 사람의 기억에 기대지 않는 자리에.
#
# **순서가 이 파일의 전부다.**
#
#   1. veo/ 만 떼어낸 커밋을 만든다(`git subtree split`).
#   2. 그 커밋을 **후보 가지**로 민다. main 은 아직 건드리지 않는다.
#   3. CI 가 그 커밋을 채점할 때까지 기다린다.
#   4. **초록불일 때만** 같은 커밋을 main 으로 민다.
#
# 3번에서 빨간불이면 4번은 실행되지 않는다. main 은 그대로이고 Railway·Vercel 은
# 옛 판을 계속 서비스한다 — 깨진 것이 나가는 것보다 낫다.
#
# 후보 가지는 배포마다 덮어쓴다. 이력을 남기는 곳이 아니라 **채점을 받는 자리**다.

set -euo pipefail

REMOTE="veo-platform"
CANDIDATE="deploy-candidate"
PREFIX="veo"
#: CI 는 3~4분 걸린다. 20분을 넘기면 기다리는 쪽이 잘못된 것으로 본다.
TIMEOUT_SECONDS=1200
POLL_SECONDS=15

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

if [ -n "$(git status --porcelain -- "$PREFIX")" ]; then
    echo "✗ 커밋하지 않은 변경이 $PREFIX/ 에 있습니다. 먼저 커밋하십시오." >&2
    git status --short -- "$PREFIX" >&2
    exit 1
fi

REPO="$(git remote get-url "$REMOTE" | sed -E 's#.*github\.com[:/]##; s/\.git$##')"

echo "==> [1/4] $PREFIX/ 를 떼어낸 커밋을 만듭니다"
SHA="$(git subtree split --prefix="$PREFIX" HEAD)"
echo "    $SHA"

echo "==> [2/4] 후보 가지($CANDIDATE)로 밉니다 — main 은 아직 그대로입니다"
git push --force --quiet "$REMOTE" "$SHA:refs/heads/$CANDIDATE"

echo "==> [3/4] CI 채점을 기다립니다 (최대 $((TIMEOUT_SECONDS / 60))분)"
deadline=$(( $(date +%s) + TIMEOUT_SECONDS ))
run_id=""
conclusion=""

while [ "$(date +%s)" -lt "$deadline" ]; do
    # 이 커밋을 채점하는 실행만 본다. 후보 가지의 **지난** 실행을 보고 초록불이라
    # 판단하면 관문이 있으나 마나다.
    row="$(gh run list --repo "$REPO" --branch "$CANDIDATE" --limit 10 \
             --json headSha,databaseId,status,conclusion \
             --jq ".[] | select(.headSha == \"$SHA\") | \"\(.databaseId)\t\(.status)\t\(.conclusion)\"" \
           2>/dev/null | head -1)"

    if [ -n "$row" ]; then
        run_id="$(echo "$row" | cut -f1)"
        status="$(echo "$row" | cut -f2)"
        conclusion="$(echo "$row" | cut -f3)"
        if [ "$status" = "completed" ]; then
            break
        fi
        printf '\r    실행 %s — %s ' "$run_id" "$status"
    else
        printf '\r    실행이 아직 잡히지 않았습니다 '
    fi
    sleep "$POLL_SECONDS"
done
echo

if [ -z "$run_id" ]; then
    echo "✗ CI 실행을 찾지 못했습니다. 워크플로가 이 가지에서 도는지 확인하십시오" >&2
    echo "  (.github/workflows/ci.yml 의 push.branches 에 $CANDIDATE 가 있어야 합니다)" >&2
    exit 1
fi

if [ "$conclusion" != "success" ]; then
    echo "✗ CI 가 통과하지 못했습니다 ($conclusion). main 을 건드리지 않았습니다." >&2
    echo "  무엇이 깨졌는지: gh run view $run_id --repo $REPO --log-failed" >&2
    exit 1
fi

echo "==> [4/4] CI 통과. main 으로 밉니다"
git push --quiet "$REMOTE" "$SHA:refs/heads/main"
echo "    배포됨: $SHA"
echo "    확인:   gh run list --repo $REPO --limit 1"
