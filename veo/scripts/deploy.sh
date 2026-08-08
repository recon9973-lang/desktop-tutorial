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

# --------------------------------------------------------------------------- #
# 하루 배포 횟수 상한 — 무료 Actions 시간을 지키는 관문
#
# **왜 있는가.** 2026-08-08 전수 집계(실행 206건, 잡별 분 단위 올림):
#
#     2026-07   실행  52건    455분
#     2026-08   실행 154건  2,155분   ← 무료 2,000분을 8일 만에 넘겼다
#
#     main             1,500분 (114건)   ← 같은 커밋 재검사. 워크플로에서 없앴다
#     deploy-candidate   655분 ( 40건)   ← 남는 것. 배포 1회당 16.4분
#
# 남은 것만으로 계산하면 655 ÷ 8일 = 81.9분/일, 31일이면 2,538분이다. 2,000분을
# 27% 넘는다. 배포 1회가 16.4분이므로 무료로 감당되는 것은 2,000 ÷ 16.4 = 122회/월,
# 하루 3.9회다. 8월 첫 8일의 실제 속도는 하루 5.0회였다.
#
# 사장님 지시(2026-08-09): **이번 달 배포는 하루 1~2회로 제한.**
#
# 상한을 글로 적어 두면 지켜지지 않는다(사장님 CLAUDE.md). 그래서 여기 둔다 —
# 넘기려면 다른 행동을 해야 하는 자리에.
#
# **후보 가지로 밀기 전에 센다.** 밀고 나면 CI 가 돌기 시작하고 분은 이미 나간다.
#: 하루에 허용하는 배포 횟수.
DEPLOY_LIMIT_PER_DAY="${VEO_DEPLOY_LIMIT_PER_DAY:-2}"
#: 이 날짜부터는 상한을 적용하지 않는다. 9월 1일에 무료 2,000분이 다시 채워진다.
#: 조용히 사라지지 않게, 지난 뒤에는 한 줄로 알리고 통과시킨다.
DEPLOY_LIMIT_UNTIL="2026-09-01"

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

if [ -n "$(git status --porcelain -- "$PREFIX")" ]; then
    echo "✗ 커밋하지 않은 변경이 $PREFIX/ 에 있습니다. 먼저 커밋하십시오." >&2
    git status --short -- "$PREFIX" >&2
    exit 1
fi

REPO="$(git remote get-url "$REMOTE" | sed -E 's#.*github\.com[:/]##; s#\.git$##')"

# --------------------------------------------------------------------------- #
# 하루 상한 검사 — 미는 것보다 먼저
# --------------------------------------------------------------------------- #

# 한국 날짜로 센다. GitHub 은 UTC 로 기록하므로 오늘 0시(KST)를 UTC 로 옮겨 묻는다.
# 그냥 UTC 날짜로 세면 아침 9시 전에 한 배포가 어제 것으로 잡힌다.
today_kst="$(TZ=Asia/Seoul date +%Y-%m-%d)"
since_utc="$(python3 - <<'PY'
from datetime import datetime, timedelta, timezone
kst = timezone(timedelta(hours=9))
midnight = datetime.now(kst).replace(hour=0, minute=0, second=0, microsecond=0)
print(midnight.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"))
PY
)"

if [[ "$today_kst" < "$DEPLOY_LIMIT_UNTIL" ]]; then
    # 실패한 실행도 분을 쓴다. 그러니 결과를 가리지 않고 전부 센다.
    today_count="$(gh api \
        "repos/$REPO/actions/runs?branch=$CANDIDATE&created=%3E%3D$since_utc&per_page=100" \
        --jq '[.workflow_runs[]] | length' 2>/dev/null || echo 0)"

    echo "==> [0/4] 오늘($today_kst) 배포 $today_count / $DEPLOY_LIMIT_PER_DAY 회"

    if [ "$today_count" -ge "$DEPLOY_LIMIT_PER_DAY" ]; then
        cat >&2 <<MSG
✗ 오늘 배포 상한($DEPLOY_LIMIT_PER_DAY회)에 이미 닿았습니다. 밀지 않았습니다.

  왜 막나 — 무료 Actions 2,000분을 8월 8일 만에 다 썼습니다(전수 실측 2,155분).
  배포 1회가 약 16.4분입니다. 하루 1~2회로 두면 무료 안에서 돌아갑니다.

  급하면 — 여러 커밋을 **한 번에** 묶어서 미십시오. 오늘처럼 네 판을 한 번에
  올리면 배포 한 번입니다. 그것이 이 상한이 바라는 행동입니다.

  그래도 지금 밀어야 한다면(장애 대응 등) 이렇게 하십시오:

      VEO_DEPLOY_LIMIT_PER_DAY=99 make deploy

  이 상한은 $DEPLOY_LIMIT_UNTIL 부터 자동으로 풀립니다(무료 분량 초기화).
MSG
        exit 1
    fi
else
    echo "==> [0/4] 배포 상한 기간($DEPLOY_LIMIT_UNTIL)이 지났습니다 — 세지 않습니다."
    echo "    무료 분량이 초기화됐을 것입니다. 계속 제한할지 다시 정하십시오."
    echo "    (근거와 숫자: scripts/deploy.sh 위쪽 주석)"
fi

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
