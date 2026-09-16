# RESUME — 다음 세션 이어가기 (2026-09-16 · s25 · ANSEO 방 · `/api/queue` 8초 고침 **완료·미배포** · main 0.3.594 합침 완료)

> 새 세션은 이 파일을 **먼저** 읽는다. 상세는 `docs/session-logs/2026-09-16-s25.md`(직전 `-s21.md`, `-s20.md`, `-s19.md`).
> **ANSEO = `recon9973-lang/veo-platform`**(veo.seokorea.org 콘솔). desktop-tutorial 안의 venom 무료진단은 ANSEO 가 **아니다**.

## 지금까지 (핵심만)

- **`/api/queue` 8초 문제는 원인 확정 + 수정 완료.** 가지 `claude/anseo-queue-warmup`(veo-platform) 에 커밋 넷:
  `cbe326c2`(ㄷ 캐시 오염 방지) · `4e1c1660`(ㄴ 배경 예열 25초) · `db69a4b4`(대장) · `8a2244e3`(main 0.3.594 합침).
  **푸시 안 함 · 판 번호 미발급 · 배포 안 함.**
- **원인**: 브로커 왕복 2회(`control.ping` + `veo_version` 방송)가 `destination` 없이 돌아, kombu 수거 루프가 답을 다 받고도 상한(2.0초)이 찰 때까지 기다린다 → **구조적 하한 4.0초**, 실측 **7.96·8.08·8.10초**(캐시 적중 0.280초). 콘솔 「변경 이력」이 이 창구를 3초에서 끊어 **항상 «진단 못 함»** 이었다.
- **실측 효과**(가짜 8초 브로커 · 70초 창 · 5초마다): 최대 대기 **8.004 → 0.000초** · 3초 초과 2건 → **0건**.
- **여드레 공백** — 2026-09-08 「고쳐」 뒤 배포 오더를 기다리며 서 있었고 main 이 0.3.55x → **0.3.594**(367커밋) 나아갔다. 2026-09-16 예약 점검이 깨워 재합침.
- **내 변경은 아직 쓸모 있다** — main 0.3.594 에 `queue_warmup`·`_Probe`·예열이 **없다**. **나갈 것 1건.**
- venom(desktop-tutorial): PR #233 main `5fa0f63` 배포됨. 사장님 검토 후 되돌릴 항목 지시 예정(여전히 미지시).

## 바로 이어갈 작업

1. **합침 뒤 재검사 결과 확인** — 서브에이전트가 `/home/user/veo-perf` 에서 의존성 재설치 + 전체 검사(ruff · mypy · `make ci-local` · `make test-db` · 웹 typecheck/lint/build/test · 대장 관문) 중. **합침 전 기준으로는 전부 초록**(ci-local 7,223 passed · test-db 1,241 · 웹 2,866 · 관문 10 + 새 관문 16). 빨간 게 나오면 고치고, 내 작업과 무관한 main 쪽 실패면 적어만 둔다.
2. **배포 — 사장님 오더 문장이 있어야 한다.** 오더 오면: 판 번호 발급(`claim_version`) → 후보 가지 CI 를 GitHub 도구(`actions_list`/`actions_get`)로 `success` 확인 → `git push origin <sha>:refs/heads/main` → 운영 실측 도장.
3. **배포 담당 이관 확인** — veo-platform `docs/WORKLIST.md` 에 **「배포 담당은 ANSEO 방이다」(사장님 지시 2026-09-09 «ANSEO방에 배포이관»)** 와 **「대기 표를 통째로 보여드리고 한 번에 승인받는다」**(2026-09-01) 가 적혀 있다. 사실이면 **이 방이 다른 방들 대기 건까지 모아 올리는 자리**다. 확인해서 사장님께 보고.
4. **운영 링 화면 실물 확인** — 사장님이 veo.seokorea.org 로그인 후 SEO 진단·AEO 관측 한 번씩. 나는 로그인 자격이 없다. 문제 보고 오면 `RingLoader.tsx`·`ring-loader.module.css` 에서 고침.
5. 운영 전후 실측으로 속도 «—» 채우기 — 8월 값(진단 탭 2,974 ms · AEO 4,756 ms) 자리를 바깥 샌드박스 curl 로 재서 대장에 적기(요청 시).
6. venom 되돌리기: 지시 오면 desktop-tutorial 에서 해당 커밋 revert PR.

## 대기/차단

- **배포는 사장님 오더 문장 없이 금지** (`scripts/deploy.sh` 가 `VEO_DEPLOY_ORDER` 없으면 거절).
- 이 컨테이너엔 `gh` 가 없어 `deploy.sh` 가 CI 대기(3단계)에서 exit 127 → 후보 가지 CI 를 GitHub MCP 도구로 확인 후 `git push origin <sha>:refs/heads/main`.
- **가지 삭제(`push --delete`)를 프록시가 403 으로 막는다** — 커밋 푸시는 됨. 사장님 로컬에서 `cd $(mktemp -d) && git init -q && git push <저장소 URL> --delete <가지들>`.
- 운영 실측은 컨테이너 프록시가 막음 → Higgsfield `sandbox_exec` curl.
- 로컬 PG: `pg_ctlcluster 16 main start` · preflight/make 는 `VEO_TEST_DATABASE_URL="postgresql+psycopg://root:root@localhost:5432/veo_test" PGPASSWORD=root PGUSER=root` 주입 필수.
- `pkill -f` 에 자기 명령줄이 걸려 셸이 죽는다(exit 144) → `fuser -k <port>/tcp`.
- 명령 실행 60초 천장 → 긴 것은 `nohup ... > 로그 &` + 로그 폴링.

## 주의·제약

- **서브에이전트로 작업**(사장님 첫 마디). 나는 통합·검토·커밋·푸시만.
- **uvicorn `--workers` 를 늘리면 예열 설계가 깨진다** — 캐시·예열이 프로세스마다 따로 돈다. 주석·대장·커밋에 적었으나 **관문으로는 못 막았다.**
- **ㄱ(핑 상한 2.0초 줄이기)은 안 건드렸다** — 워커 실제 응답 시간을 아무도 안 쟀다. 느낌으로 낮추면 워커 수를 적게 세는 오류가 난다. `limit=1` 은 쓰면 안 됨.
- 다른 worktree 에서 API 시험: `PYTHONPATH=$PWD/src` 필수. 웹은 Turbopack 불가 → `next build --webpack`.
- 서버가 모르는 단계를 화면이 말하지 않는다(오류 62) · 못 잰 값 «—» · 지어낸 수치 금지 · 사장님께는 「커밋」·「배포」 두 낱말만.
- 커밋 트레일러: `Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>` / `Claude-Session: https://claude.ai/code/session_01S6ziCnWzVB8CMhzMbmzupF` · **모델 ID 를 코드·커밋·PR 에 넣지 않는다.**

## 참고

- veo 클론 `/home/user/veo-platform`(main) · worktree `/home/user/veo-perf`(**`claude/anseo-queue-warmup` 체크아웃** · `.venv`·node_modules 여기). 새 컨테이너면 `add_repo` 후 재클론.
- 현황은 `PROJECT_STATE.md`, 무엇이 어디 있는지는 `핵심두뇌_MASTER.md`.
