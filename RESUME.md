# RESUME — 다음 세션 이어가기 (2026-09-06 s20 마감 · ANSEO 방 · **0.3.520 배포 완료**)

> 새 세션은 이 파일을 **먼저** 읽는다. 상세는 `docs/session-logs/2026-09-06-s20.md`(직전 `-s19.md`).
> **ANSEO = `recon9973-lang/veo-platform`**(veo.seokorea.org 콘솔). desktop-tutorial 안의 venom 무료진단은 ANSEO가 **아니다**.

## 지금까지 (핵심만)
- **0.3.520 나갔다** [실측 2026-09-06 23:07 KST 바깥 샌드박스 curl] 서버·워커 `0.3.520` · 웹 링 에셋 200. 내용 = 골든 링 로딩(SEO·AEO) + 속도 전수조사 여덟. veo-platform main = 도장 커밋(`d54fd06c` 위 docs). 사장님 오더 «속도개선과 로딩 애니매이션 둘 다 배포».
- 링 단독 판 가지 `claude/anseo-ring-release`(0.3.517 · 안 나감)는 **폐기 대상** — 내용이 0.3.520 에 포함됨. 원격에 남아 있으니 지워도 된다.
- `claude/anseo-perf-day1` = main 과 같음(도장까지). 더 쌓을 것 없음.
- 사장님 톤 지적(SEO 링 블루톤·AI스러움) → 「두 진단 성격이 다르니 컬러가 달라도 됨」으로 정리. 내가 콘솔 톤·덮개까지 건드리자고 해 **범위 초과 지적** 받음 — 오더 밖 제안 금지.
- 속도 Top 10 원문: `docs/plans/anseo-veo-speed-audit-2026-09-06.md`. 남은 것: #3 Redis+워커 · #5 DB 풀(사장님) · #10 router.refresh 32곳 · `lib/projects.ts` 3회 조인 · 404 폴백(`fetchCompaniesLegacy`) 제거는 다음 웹 판.
- venom(desktop-tutorial): PR #233 main `5fa0f63` 배포됨. 사장님 검토 후 되돌릴 항목 지시 예정

## 바로 이어갈 작업
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
- veo 클론 `/home/user/veo-platform`(ring 가지 원본) · worktree `/home/user/veo-perf`(**지금 `claude/anseo-ring-release` 체크아웃** · `.venv`·node_modules 여기). 콘솔 실물 캡처 방법: `scratchpad/serve.mjs`(가짜 API + next start 4599 · `SHOOT_FIXTURE`) + `shoot2.mjs`(Playwright 전역 설치 · `/api/scan`·`/api/observation` 가로채기) — 컨테이너 바뀌면 s20 로그 참고해 다시 씀. 새 컨테이너면 `add_repo` 후 재클론
- 운영 실측은 컨테이너 프록시가 막음 → Higgsfield `sandbox_exec` curl
