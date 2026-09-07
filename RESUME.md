# RESUME — 다음 세션 이어가기 (2026-09-07 s23 · ANSEO 방 · **내 것 전부 나감** · ⚠️ **단독 배포 금지 — 다른 방에 얹어서만**)

> 새 세션은 이 파일을 **먼저** 읽는다. 상세는 `docs/session-logs/2026-09-07-s21.md`(직전 `-s20.md`, `-s19.md`).
> **ANSEO = `recon9973-lang/veo-platform`**(veo.seokorea.org 콘솔). desktop-tutorial 안의 venom 무료진단은 ANSEO가 **아니다**.

## ⚠️ 배포 정책 — 사장님 오더 «배포 대기하고 다른 방이 배포하면 같이 배포에 참여해» (2026-09-07)

**이 방은 단독으로 배포하지 않는다.** 내 판만 따로 내보내지 말고, 다른 방이 배포할 때 거기에 얹어 함께 나간다.

- **왜 그렇게 되나**: main 에 푸시하는 순간 Railway·Vercel 이 자동으로 굽는다 = main 푸시 = 배포. 그래서 「내 것만 main 에 밀기」가 곧 단독 배포다.
- **끼어드는 신호는 `deploy-candidate` 가지**다. 다른 방이 배포를 시작하면 그 가지가 먼저 생긴다(main 보다 앞선다). 그때가 합류 시점.
- **절차**:
  1. 내 작업은 **내 가지에 완성해 두고 대기**(CI 초록까지). main 에 밀지 않는다.
  2. `deploy-candidate` 가 생기면 → 내 가지를 그 위로 rebase → 판 번호를 그 방 것보다 뒤로 발급 → **같은 `deploy-candidate` 에 얹어 푸시** → CI 가 합친 나무를 한 번에 채점 → 둘이 함께 main 으로.
  3. 실측·도장은 그 방과 겹치지 않게. 이미 그 방이 했으면 내 판 줄만 대장에 더한다.
- **예외**: 사장님이 직접 배포 오더 문장을 주시면 그때는 단독으로 내도 된다(그 문장이 곧 허가).
- 판 번호 충돌은 늘 그렇듯 **나중에 미는 쪽이 물러난다**.

## 지금까지 (핵심만)
- **[s23 실측 2026-09-07] 운영 = `0.3.539`** (진단 서버 `/api/health` · 워커 `/api/queue` · 웹 로그인 화면 셋 다). main 도 `7ae4f40b` = 0.3.539 로 **main 과 운영이 같다**. `deploy-candidate` 가지는 지금 없음(직전 배포 뒤 정리됨). **내 것(ANSEO 속도·링) 은 0.3.530 까지 전부 나갔고 대기 중인 내 작업 없음** — 그래서 지금은 얹을 것도, 기다릴 것도 없다. 정책은 다음 작업부터 발동.
- 참고(다른 방 소관, 손대지 말 것): 대장 §2 머리말은 아직 「미배포 0.3.537~0.3.539」 라고 적혀 있으나 **실측상 셋 다 운영에 올라가 있다** — 그 방들이 실측·도장을 아직 안 적은 것으로 보인다. 내가 고치지 않는다.
- **[s22] 0.3.530 나갔다·도장 끝** [실측 2026-09-07 14:01 KST 바깥 샌드박스 curl] 서버 `/api/health` 0.3.530 · 워커 `/api/queue` ["0.3.530"] · 웹 로그인 판 0.3.530 · gzip. 다른 방 0.3.529(입지 방)도 이 배포에 실려 함께 나감. veo-platform main = 도장 커밋 `9724621e`(b0bbd793 release 위 docs 2파일 · 대장 1,195줄 · 관문 10/10). `claude/anseo-perf-web2` = main 과 같음. **미배포 없음.** 내용: 정기 진단 체크박스 2곳 refresh 제거(요청 9→1·12→1) · projects 왕복 3→1 · 404 폴백 제거 · PinButton 그대로. preflight 전부 통과. 사장님 오더 «별표는 살리고 배포해».
- 배포 재개 절차는 s21 로그 「배포 재개 절차」 4단계 그대로.
- **0.3.520 나갔다** [실측 2026-09-06 23:07 KST 바깥 샌드박스 curl] 서버·워커 `0.3.520` · 웹 링 에셋 200. 내용 = 골든 링 로딩(SEO·AEO) + 속도 전수조사 여덟. veo-platform main = 도장 커밋(`d54fd06c` 위 docs). 사장님 오더 «속도개선과 로딩 애니매이션 둘 다 배포».
- ~~링 단독 판 가지 `claude/anseo-ring-release`~~ · ~~`claude/anseo-perf-web2`~~ — **[2026-09-07 정리 완료]** 사장님이 로컬에서 원격 삭제(확인함). 지우기 전 대조: 링 코드·에셋이 main 에 내용 차이 0, 남은 커밋은 안 나간 0.3.517 판 발급 + merge 뿐이었음.
- `claude/anseo-perf-day1` = main 과 같음(도장까지). 더 쌓을 것 없음.
- 사장님 톤 지적(SEO 링 블루톤·AI스러움) → 「두 진단 성격이 다르니 컬러가 달라도 됨」으로 정리. 내가 콘솔 톤·덮개까지 건드리자고 해 **범위 초과 지적** 받음 — 오더 밖 제안 금지.
- 속도 Top 10: #10·projects·404 폴백은 s21에서 끝남(0.3.530 판). 남은 것 **#3 Redis+워커 · #5 DB 풀(사장님 결정)** 뿐.
- venom(desktop-tutorial): PR #233 main `5fa0f63` 배포됨. 사장님 검토 후 되돌릴 항목 지시 예정

## 바로 이어갈 작업
0. ~~0.3.530 배포 마무리~~ · ~~가지 원격 정리~~ — **둘 다 끝**(s22 도장 `9724621e` · 2026-09-07 가지 2개 삭제 확인). **주의: 이 컨테이너 프록시는 가지 삭제(push --delete)를 403 으로 막는다** — 커밋 푸시는 되는데 삭제만 안 됨. GitHub MCP 에도 삭제 도구 없음. 사장님 로컬에서 `cd $(mktemp -d) && git init -q && git push <저장소 URL> --delete <가지들>` 로 하시거나 웹 Branches 화면에서.
1. **운영 링 화면 실물 확인** — 사장님이 veo.seokorea.org 로그인 후 SEO 진단·AEO 관측 한 번씩. 나는 로그인 자격이 없어 못 본다. 문제 보고 오면 `RingLoader.tsx`·`ring-loader.module.css` 에서 고침.
2. **운영 전후 실측으로 속도 «—» 채우기** — 8월 값(진단 탭 2,974 ms · AEO 4,756 ms)과 같은 자리를 바깥 샌드박스 curl 로 재서 대장에 적기(요청 시).
3. 사장님 결정 대기(s20 로그 「판단 필요」): AEO 엔진별 막대 · 「SEO 점수 분석 중…」 스크린샷 출처 · venom 되돌릴 항목 · #3/#5 · fetcher.py 제외 · 서체 라틴 폴백
4. venom 되돌리기: 지시 오면 desktop-tutorial 에서 해당 커밋 revert PR

## 대기/차단
- 배포는 오더 문장 없이 금지(`scripts/deploy.sh` 가 거절) · 이 컨테이너엔 `gh` 가 없어 스크립트가 CI 대기(3단계)에서 exit 127 → 후보 가지 CI 를 GitHub 도구(`actions_list`/`actions_get`)로 `success` 확인 후 `git push origin <sha>:refs/heads/main` · 운영 실측은 Higgsfield `sandbox_exec` curl(컨테이너 프록시 403)
- 로컬 PG: `pg_ctlcluster 16 main start` · preflight/make 는 `VEO_TEST_DATABASE_URL="postgresql+psycopg://root:root@localhost:5432/veo_test" PGPASSWORD=root PGUSER=root` 주입 필수(기본값엔 비밀번호 없음)
- `pkill -f` 에 자기 명령줄이 걸려 셸이 죽는다(exit 144) → `fuser -k <port>/tcp` 또는 별도 호출

## 주의·제약
- **서브에이전트로 작업**(사장님 첫 마디). 나는 통합·검토·커밋·푸시만. 에이전트가 백그라운드 시험을 기다리며 멈추면 SendMessage 로 재개
- 다른 worktree 에서 API 시험: `PYTHONPATH=$PWD/src` 필수(공용 venv editable 이 veo-perf 를 가리킴). 웹은 node_modules 심링크 · Turbopack 불가 → `next build --webpack`
- 서버가 모르는 단계를 화면이 말하지 않는다(오류 62) · 커밋 트레일러 `Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>` / `Claude-Session: https://claude.ai/code/session_01S6ziCnWzVB8CMhzMbmzupF` · 모델 ID 코드·PR 금지
- 사장님께 「커밋」·「배포」 두 낱말만 · 못 잰 값 «—» · 지어낸 수치 금지

## 참고
- veo 클론 `/home/user/veo-platform`(main) · worktree `/home/user/veo-perf`(**지금 `claude/anseo-perf-web2` 체크아웃** · `.venv`·node_modules 여기). 콘솔 실물 캡처 방법: `scratchpad/serve.mjs`(가짜 API + next start 4599 · `SHOOT_FIXTURE`) + `shoot2.mjs`(Playwright 전역 설치 · `/api/scan`·`/api/observation` 가로채기) — 컨테이너 바뀌면 s20 로그 참고해 다시 씀. 새 컨테이너면 `add_repo` 후 재클론
- 운영 실측은 컨테이너 프록시가 막음 → Higgsfield `sandbox_exec` curl
