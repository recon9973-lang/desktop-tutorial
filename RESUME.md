# RESUME — 다음 세션 이어가기 (2026-09-06 05:20 KST · s19 마감 · ANSEO 방)

> 새 세션은 이 파일을 **먼저** 읽는다. 상세는 `docs/session-logs/2026-09-06-s19.md`(직전 `2026-09-05-s18.md`).
> **ANSEO = `recon9973-lang/veo-platform`**(veo.seokorea.org 콘솔). desktop-tutorial 안의 venom 무료진단은 ANSEO가 **아니다** — s18에서 그 착각으로 venom에 배포했고 사장님이 되돌릴 항목을 검토 중.

## 지금까지 (핵심만)
- veo-platform(main `86a44f1`)에 브랜치 2개 **푸시됨 · PR 없음 · 배포 안 됨**:
  - `claude/anseo-perf-day1` (5커밋) — GZip · 콘솔 layout 병렬 · load_only 5+1곳. 테스트 전부 통과. **판 미발급**
  - `claude/anseo-diagnosis-ring-loader` (`b0d57fc9`) — SEO 진단(`seo/ScanForm.tsx`)·AEO 관측(`geo/JobWatch.tsx`) 로딩을 `RingLoader`로 교체. 판 0.3.514 **수동** 기입(다른 방 충돌 가능)
- 속도 전수조사 Top 10: `scratchpad`에만(컨테이너 소멸 시 사라짐) → 요지는 s19 로그 「미해결」. 1일차 셋(#1·#2·#8) 완료, 나머지 착수 전
- venom(desktop-tutorial): PR #233으로 main `5fa0f63` 배포됨. 사장님 검토 후 되돌릴 항목 지시 예정

## 바로 이어갈 작업
1. **사장님 결정 대기** (s19 로그 「판단 필요」 6건): 특히 ③ AEO 엔진별 막대 복원 여부(8-25 지시와 충돌) · ④ 「SEO 점수 분석 중…」 스크린샷 출처 · ⑥ venom 되돌릴 항목
2. **배포 오더 문장 받으면**: 두 브랜치를 하나로 합쳐(perf-day1 ← ring-loader merge, 충돌 없어야 함: 파일 안 겹침) 판 번호 하나 발급(`make bump-version TO=0.3.5xx` + `lib/changelog.ts` + WORKLIST §2 「판 미발급」 교체, `make check-contracts`) → veo-platform 규율대로 `VEO_DEPLOY_ORDER="문장" bash scripts/deploy.sh`. 다른 방이 main을 밀었으면 rebase, force-with-lease는 사장님 승인
3. 속도 2주차: #4 httpx.Client 수명(11곳 공용 팩토리) → #7 next/font self-host → GEO `PromptSetForm` next/dynamic → #6 readAllPages 병렬 → #9 `/api/customers/overview`. 사장님 결정: #3 Redis+워커, #5 DB 풀
4. venom 되돌리기: 지시 오면 desktop-tutorial에서 해당 커밋 revert PR

## 대기/차단
- 배포는 오더 문장 없이 금지(veo-platform `scripts/deploy.sh`가 거절)
- 판 번호 충돌 규칙: 나중에 미는 쪽이 물러남
- 로컬 PG(veo 테스트): `pg_ctlcluster 16 main start`, `VEO_TEST_DATABASE_URL="postgresql+psycopg://root:root@localhost:5432/veo_test"`(pg_hba 수정 차단 → root 비밀번호 방식)

## 주의·제약
- **서브에이전트로 작업**(사장님 첫 마디). 나는 통합·검토·커밋·푸시만
- 서버가 모르는 단계를 화면이 말하지 않는다(veo 규율 오류 62) — 캡션은 `SCAN_STAGES`·`OBSERVATION_STAGES` 실제 값
- 링 에셋 WebM 우선 + mp4 폴백 + 포스터 상시, screen 블렌드, 래퍼에 스택 컨텍스트 금지
- 커밋 트레일러 `Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>` / `Claude-Session: https://claude.ai/code/session_01S6ziCnWzVB8CMhzMbmzupF`. 모델 ID 코드·PR 금지
- 사장님께 「커밋」·「배포」 두 낱말만 · 못 잰 값 «—» · 지어낸 수치 금지

## 참고
- veo 클론 `/home/user/veo-platform`(ring 브랜치 체크아웃) · worktree `/home/user/veo-perf`(perf 브랜치). 새 컨테이너면 `add_repo` 후 재클론
- 운영 실측은 컨테이너 프록시가 막음 → Higgsfield `sandbox_exec` curl
