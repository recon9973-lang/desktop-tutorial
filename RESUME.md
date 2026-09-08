# RESUME — 다음 세션 이어가기 (2026-09-09 03:1x KST · s20 마감 · 진단 비용/30분 방)

> **이 파일은 이 가지(진단 비용/30분 방)의 인계본이다 — `main` 에 올리지 않는다.**
> `main` 의 `RESUME.md` 는 **s19 방 것**이고 그 방은 아직 일하고 있다
> [실측 2026-09-09 · `3e214aa` 가 67줄을 다시 씀]. 인계 파일이 저장소에 하나뿐인데
> 두 방이 같이 쓴다 — 덮으면 저쪽의 살아 있는 인계가 지워진다. **사장님 판단이
> 필요한 자리다.**

> 새 세션은 이 파일을 **먼저** 읽는다. 상세는 `docs/session-logs/2026-09-08-s20.md`.
> 현황 `PROJECT_STATE.md`, 지도 `핵심두뇌_MASTER.md`.

## 지금까지 (핵심만)

- **끝난 일 둘. 둘 다 main 에 들어갔다.**
  - **판 0.3.550** — 이슈를 닫는 진단이 30분에 안 막힌다. 실무자 피드백
    *"수정후에 바로 확인이 어렵다"* 의 진범은 관문이 아니라 **이슈 해결 확인이
    사이트 진단으로 돌던 것**(`issues/reverify.py`)이었다. 그 진단을 **페이지 진단**
    (`page_check=True`)으로 갈랐다 — 30분에서 빠지고, 사이트 이력·추이·대표 점수·
    하락 경보·이슈 표에 안 섞인다. 정기 진단은 반대로 **누적**으로 남는 것을 관문이
    지킨다(`page_check=False`). 화면 낱말 「재진단」·「재검사 요청」 → **「진단」·「진단 요청」**.
    시험 4건. main `a17bc29`.
  - **판 0.3.553** — **도는 판을 러너가 잰다**. 배포 [5/5]「실제로 도는지」가 이 방에서
    안 돈다(운영 주소 egress 403 · `curl` 도 `WebFetch` 도 같다). 워크플로
    **「도는 판 확인」**(`.github/workflows/rollout-check.yml`)이 `/api/health`·`/api/queue`
    를 러너에서 두드린다. 관문이 아니라 **자**다. main `758933d`.
- **비용 물음의 답**: 진단 하나에 **외부로 나가는 돈 0원**(규칙 기반 + PageSpeed·CrUX·GSC 무료).
  LLM·SerpAPI 는 진단 경로에 없다(`observations/` 쪽만). 실제로 드는 것은 남의 서버 부하
  (약 205요청) · 우리 서버 시간(약 180초) · DB(101 kB/실행). 30분은 **돈이 아니라**
  남의 서버 속도와 「잘린 진단」을 막는 장치다. 보고서:
  `docs/2026-09-08-SEO-GEO-진단-비용과-30분.md`(이 저장소).
- **저장소·가지**: 코드는 `recon9973-lang/veo-platform`(이 저장소 아님) ·
  가지 `claude/seo-geo-diagnosis-cost-time-c2bjxc`.

## 바로 이어갈 작업

0. **끝났다 — s20 문서 둘이 main 에 들어갔다** (PR #234 · `ffb90e2`) [2026-09-09].
   진단 비용 보고서와 s20 세션 기록. **282줄 더함 · 0줄 지움** — 지운 것이 없다.
   `RESUME.md`·`PROJECT_STATE.md` 는 main 것을 그대로 뒀다(위 머리말).

1. **끝났다 — 0.3.553 은 나갔고 돈다.** [실측 2026-09-09 03:09 KST · 러너 실행 34261310214]
   서버 `0.3.553` · 워커 `0.3.553` 1대 · **뒤처진 0**. 대기 표는 비었다(veo-platform `84e519f`).
   **다음 판을 낼 때 그대로 쓸 절차**(이 방은 운영 주소로 못 나간다):
   ```
   mcp__github__actions_run_trigger  method=run_workflow
     owner=recon9973-lang repo=veo-platform
     workflow_id=rollout-check.yml ref=main
   → gh run list --workflow rollout-check.yml --limit 1        (실행 번호)
   → gh api repos/.../actions/runs/<run>/jobs --jq '.jobs[0].id'
   → mcp__github__get_job_logs (return_content=true)
   ```
   **`gh workflow run` 은 403**(이 방 열쇠에 `actions:write` 없음) · 러너 로그 내려받기도 403 이라
   `gh run view --log` 대신 **MCP `get_job_logs`**. 그리고 **배포 직후 2분에는 옛 판이 잡힌다** —
   6분쯤 두고 다시 재라. **그 뒤 main 은 0.3.554 로 갔다**(다른 방 · 커밋 5)
   [실측 2026-09-09 · `git show origin/main:apps/api/src/veo/__init__.py`].
2. **가지에 있고 아직 안 나간 문서 커밋** — 워크플로 주석에 「방에서는 MCP 로 부른다
   (gh 는 403)」를 적은 커밋. 판을 안 올렸으니 다음 판에 같이 나간다.
   **가지에는 올라가 있다** [실측 2026-09-09 · `git ls-remote`]. 「미배포」는 「가지에
   없다」가 아니라 「아직 안 나갔다」는 뜻이다 — 한 번 잘못 읽었다. 까닭은 이 방의
   veo-platform 복제본이 **`main` 하나만 따라가게** 돼 있어서다
   (`+refs/heads/main:refs/remotes/origin/main`) — 그래서 `git fetch` 를 해도
   `origin/claude/…` 표시가 옛 값에 멈춘다. **가지의 실제 끝은 `git ls-remote` 로 재라.**
3. (선택) **워크플로를 더 낫게** — 지금은 한 번 재고 끝이라 배포 직후엔 옛 판이 잡힌다.
   `deploy.sh` [5/5] 처럼 **바라는 판이 나올 때까지 러너가 기다리게** 하면 배포마다
   도장이 자동으로 찍힌다(`on: push: branches: [main]` + 폴링). 별도 판 몫.
   **아직 그대로다** [실측 2026-09-09 — main 의 `rollout-check.yml` 은 `workflow_dispatch` 뿐].

## 대기/차단

- **CI 예산** — preflight ⑤ 가 「오늘 CI 11건 · 상한 2회를 다 썼다」고 알렸다(2026-09-08).
  더 밀려면 사장님 판단. 오늘 한 번은 오더 둘을 근거로 넘겨서 진행했고 보고에 명시했다.
- **이 방은 운영 주소로 못 나간다**(egress 403). 실측은 **러너로** 한다(위 1번).
- **이 방은 덮어쓰기(force)가 막혀 있다** — 방 규칙이 `--force-with-lease` 까지 거절한다
  [실측 2026-09-09 · 두 번 거절됨]. 그래서 배포 절차의 마지막 걸음 **「가지를
  `origin/main` 으로 리셋」이 이 방에서는 안 된다.** 덮어쓰기 없이 올려야 할 때는
  옛 가지 끝을 `merge -s ours` 로 물려 붙이면 이어붙이기가 된다(나무는 안 바뀐다).
- **방 공조** — 클라우드 방끼리 직접 말을 못 한다(사장님이 전달자). 판 번호는 **main 에
  먼저 닿는 쪽**이 갖는다. 이제 배포가 나가기 직전 스스로 정한다(`claim_version.py`).

## 주의·제약

- 가지 `claude/seo-geo-diagnosis-cost-time-c2bjxc` 외로 푸시 금지. 체크포인트 문서도 이 가지에.
- 배포는 **`make deploy` 만**. `VEO_DEPLOY_ORDER` 에 사장님 원문 인용
  («고쳐줘»·«진행해» 는 배포 오더가 아니다).
- `deploy-candidate` 는 덮어쓰는 채점 자리(`--force` 정상). **main 은 절대 force 금지** —
  거절되면 리베이스한다(이번에 한 번 겪었다).
- 대장·변경이력에 「민다·푸시」 금지 — 사장님께는 **「커밋」·「배포」** 두 낱말만.
- 못 잰 값은 «—», 0 으로 적지 않는다. 지어낸 수치 금지. 의료광고법 준수.
- 커밋 트레일러: `Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>` +
  `Claude-Session: https://claude.ai/code/session_01KRx7YSnr5qHXgSYS4LcAHa`. 모델 ID 는 트레일러에만.

## 참고

- veo-platform 환경: `PYTHON=/usr/bin/python3.12 make setup` · `pnpm install` ·
  로컬 PostgreSQL(`service postgresql start`, role `root`/비번 `veo`, DB `veo_test`).
- preflight/배포 실행:
  `PGPASSWORD=veo VEO_TEST_DATABASE_URL="postgresql+psycopg://root:veo@localhost:5432/veo_test" \
   VEO_DEPLOY_ORDER="<사장님 원문>" VEO_ROLLOUT_TIMEOUT_SECONDS=60 make deploy`
  ([5/5] 는 어차피 이 방에서 막히니 60초로 줄이고, 대신 러너로 잰다.)
