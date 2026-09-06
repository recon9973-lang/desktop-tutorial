# RESUME — 다음 세션 이어가기 (2026-09-06 s20 · ANSEO 방 · 0.3.517 = 로딩 애니메이션만 · 배포 대기)

> 새 세션은 이 파일을 **먼저** 읽는다. 상세는 `docs/session-logs/2026-09-06-s20.md`(직전 `-s19.md`).
> **ANSEO = `recon9973-lang/veo-platform`**(veo.seokorea.org 콘솔). desktop-tutorial 안의 venom 무료진단은 ANSEO가 **아니다**.

## 지금까지 (핵심만)
- **사장님 재확인(2026-09-06)**: «ANSEO = veo.seokorea.org 맞는지 · 로딩 애니메이션만 적용되는지 확인» → 속도 개선과 묶었던 판을 풀었다. **0.3.517 = 골든 링 로딩 화면만.**
- veo-platform 원격 main = `6cc82db6`(v0.3.516 · 입지 방 · 미배포).
- **배포 대기 가지 `claude/anseo-ring-release`** head `0110e6f0` = main 0.3.516 + 링 가지 + v0.3.517 발급. 링 파일 16개 + 판 파일 셋 + 대장. 대장 관문·ring 시험 27 · tsc 0 · ledger facts · check-contracts 통과. preflight 는 s20 마지막에 돌리던 중(로그 `scratchpad/preflight3.log` — 컨테이너 바뀌면 다시 `VEO_TEST_DATABASE_URL=…root:root… make preflight`).
- 속도 가지 `claude/anseo-perf-day1`(head `1f5c8576`)은 **0.3.517 을 잘못 달고 있다** — 링 판이 나간 뒤 별도 지시가 있을 때 main 합류 + `make bump-version TO=<main+1>` + changelog 맨 위 항목 version/대장 고쳐 재발급. 사장님 지시 없이 내보내지 않는다.
- 사장님 톤 지적: SEO 링이 «너무 블루톤·AI스럽다» → 「두 진단 성격이 다르니 컬러가 달라도 된다」로 정리. 스펙(검정 반투명 + 블러 + 가운데 링 + 카운터 + 한 줄)은 그대로.
- venom(desktop-tutorial): PR #233 main `5fa0f63` 배포됨. 사장님 검토 후 되돌릴 항목 지시 예정

## 바로 이어갈 작업
1. **배포 오더 문장 받으면** (`/home/user/veo-perf` · 가지 `claude/anseo-ring-release`): `git fetch origin main` → main 이 움직였으면 merge(대장 충돌 양쪽 살림 · 판 겹치면 `make bump-version TO=<main+1>` + changelog·대장) → `VEO_TEST_DATABASE_URL="postgresql+psycopg://root:root@localhost:5432/veo_test" make preflight` → `VEO_DEPLOY_ORDER="문장" bash scripts/deploy.sh` → 이중 실측(서버·워커 `version` · 웹 링 화면) → 대장 도장 커밋. force-with-lease 는 사장님 승인
2. 배포 뒤 운영에서 링 화면 실물 확인(SEO 진단·AEO 관측 한 번씩) → 사장님께 캡처
3. 속도 가지 재발급은 별도 지시 때(위 참고). 사장님 결정 대기(s20 로그 「판단 필요」)는 그대로
4. venom 되돌리기: 지시 오면 desktop-tutorial 에서 해당 커밋 revert PR

## 대기/차단
- 배포는 오더 문장 없이 금지(`scripts/deploy.sh` 가 거절) · 판 번호 충돌은 나중에 미는 쪽이 물러남
- 로컬 PG: `pg_ctlcluster 16 main start` · `VEO_TEST_DATABASE_URL="postgresql+psycopg://root:root@localhost:5432/veo_test"`(에이전트마다 `veo_test_<이름>` 따로)

## 주의·제약
- **서브에이전트로 작업**(사장님 첫 마디). 나는 통합·검토·커밋·푸시만. 에이전트가 백그라운드 시험을 기다리며 멈추면 SendMessage 로 재개
- 다른 worktree 에서 API 시험: `PYTHONPATH=$PWD/src` 필수(공용 venv editable 이 veo-perf 를 가리킴). 웹은 node_modules 심링크 · Turbopack 불가 → `next build --webpack`
- 서버가 모르는 단계를 화면이 말하지 않는다(오류 62) · 커밋 트레일러 `Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>` / `Claude-Session: https://claude.ai/code/session_01S6ziCnWzVB8CMhzMbmzupF` · 모델 ID 코드·PR 금지
- 사장님께 「커밋」·「배포」 두 낱말만 · 못 잰 값 «—» · 지어낸 수치 금지

## 참고
- veo 클론 `/home/user/veo-platform`(ring 가지 원본) · worktree `/home/user/veo-perf`(**지금 `claude/anseo-ring-release` 체크아웃** · `.venv`·node_modules 여기). 콘솔 실물 캡처 방법: `scratchpad/serve.mjs`(가짜 API + next start 4599 · `SHOOT_FIXTURE`) + `shoot2.mjs`(Playwright 전역 설치 · `/api/scan`·`/api/observation` 가로채기) — 컨테이너 바뀌면 s20 로그 참고해 다시 씀. 새 컨테이너면 `add_repo` 후 재클론
- 운영 실측은 컨테이너 프록시가 막음 → Higgsfield `sandbox_exec` curl
