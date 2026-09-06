# RESUME — 다음 세션 이어가기 (2026-09-06 s20 마감 · ANSEO 방)

> 새 세션은 이 파일을 **먼저** 읽는다. 상세는 `docs/session-logs/2026-09-06-s20.md`(직전 `-s19.md`).
> **ANSEO = `recon9973-lang/veo-platform`**(veo.seokorea.org 콘솔). desktop-tutorial 안의 venom 무료진단은 ANSEO가 **아니다**.

## 지금까지 (핵심만)
- veo-platform 원격 main = `225bf4b7`(v0.3.515 · 입지 방 · 미배포). 0.3.514 는 판 2 가 가져가 **나갔다**.
- 브랜치 2개 **푸시됨 · PR 없음 · 배포 안 됨 · 둘 다 main 합류 완료 · 둘 다 판 미발급**:
  - `claude/anseo-perf-day1` (head `90fa32f4`+대장 커밋) — 1일차 셋(#1 gzip · #2 레이아웃 병렬 · #8 load_only) + **2주차 다섯**(#4 httpx 수명 · #6 readAllPages 병렬 · #7 next/font · GEO 폼 dynamic · #9 customers/overview). 전체 pytest·vitest·check-contracts 통과
  - `claude/anseo-diagnosis-ring-loader` (`1e7a3567`) — 골든 링 로딩. 수동 0.3.514 는 물러나 판 파일 셋 main 값. changelog 항목 원문 `b0d57fc9`
- 속도 Top 10 원문: `docs/plans/anseo-veo-speed-audit-2026-09-06.md`(이 저장소). 남은 것: #3 Redis+워커 · #5 DB 풀(사장님) · #10 router.refresh 32곳 · `lib/projects.ts` 3회 조인
- venom(desktop-tutorial): PR #233 main `5fa0f63` 배포됨. 사장님 검토 후 되돌릴 항목 지시 예정

## 바로 이어갈 작업
1. **사장님 결정 대기**(s20 로그 「판단 필요」 5건): AEO 엔진별 막대 · 스크린샷 출처 · venom 되돌릴 항목 · #3/#5 · fetcher.py 제외 수용 · 서체 라틴 폴백
2. **배포 오더 문장 받으면**: perf-day1 에 ring-loader 를 merge(파일 안 겹침 · 대장 두 파일만 손 해소) → `make bump-version TO=0.3.5xx`(main 최신 판 +1 · 다른 방 확인) + `changelog.ts` 에 링 항목(`b0d57fc9` 원문) + 속도 항목 + WORKLIST 대기 표 「판 미발급」 교체 → `make check-contracts` → `VEO_DEPLOY_ORDER="문장" bash scripts/deploy.sh`. 다른 방이 main 을 밀었으면 merge, force-with-lease 는 사장님 승인
3. 배포 뒤: 다음 웹 판에서 `fetchCompaniesLegacy`+`readCompanyBoards` 제거 · 운영 전후 실측으로 «—» 채우기
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
- veo 클론 `/home/user/veo-platform`(ring 가지) · worktree `/home/user/veo-perf`(perf 가지 · `.venv` 여기). w2 worktree 셋은 합류 뒤 제거. 새 컨테이너면 `add_repo` 후 재클론
- 운영 실측은 컨테이너 프록시가 막음 → Higgsfield `sandbox_exec` curl
