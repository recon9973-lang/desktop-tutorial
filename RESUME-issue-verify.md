<!-- 가지: claude/tender-curie-9eniaq -->
# RESUME (이슈 진단 방 · ANSEO 「진단 요청」 단추) — 2026-09-28 · 오더 1건 · **ANSEO 방에 인계 대기**

## 한 줄
사장님 화면 캡처(ANSEO 이슈 탭): noindex 감점 해제 뒤 「진단 요청」을 누르니 «'확인함'(ACKNOWLEDGED) 상태에서
'진단 대기'(VERIFYING)(으)로는 전이할 수 없습니다». → **ANSEO(`veo-platform`)에서 고쳐 가지에 커밋했다. 배포는 ANSEO 방 몫.**

## 어느 사이트였나
**ANSEO(veo.seokorea.org)** — 캡처 머리에 「ANSEO」. 이 저장소(베놈 사이트)에는 코드 변경 없음(이 인계본만).

## 어디에 무엇이 있나
- 코드: `veo-platform` 가지 **`claude/tender-curie-9eniaq`** · 커밋 `1ee4769` · 판 **0.3.665**(잠정 · 09-27 인계와 같은 모양 · `__init__.py` 는 0.3.664 그대로)
- 인계 문서: `veo-platform/docs/HANDOFF-2026-09-28-verify-from-any-state-to-anseo.md` · 대장 §2 머리말 「미배포 **0.3.665**」 + 대기 표 줄
- 관문 [실측 2026-09-28]: tsc 0 · eslint 0 · vitest 342 파일/2,933 건 · next build 통과 · PR 열지 않음

## 원인 (한 줄)
서버 표(`lifecycle.py`)는 진단 요청을 「수정했다고 보고됨」·「진단 실패」에서만 받는데, 이슈 화면 1번 「진단 요청」 단추
(`VerificationPanel.tsx`)가 상태를 안 보고 요청만 보냈다. 0.3.649 에서 상태 단추 셋을 뺀 뒤로 「확인함」 이슈에서 누를 수
있는 단추가 이 막힌 것 하나였다. noindex 감점 해제 칸(`IssueNoindexAccept.tsx`)은 이미 걸음을 대신 밟고 있었다.

## 고친 것 (웹만 · 서버·계약 무변화)
1. `issue-noindex.ts` — `walkToVerification`(조치 중 → 수정 보고 → 진단 요청을 순서대로 · 거절 문장 그대로 던짐) · `describeStepsKo`
2. `VerificationPanel.tsx` — 1번 단추가 그 손을 쓴다 · 단추 아래 «이 단추가 조치 중 → 수정했다고 보고됨 → 진단 대기 순서로 대신 옮깁니다» · 이미 진단 대기면 2번으로 안내 · 진단으로 닫힌 이슈엔 단추 없음
3. `IssueNoindexAccept.tsx` — 같은 손을 쓴다(동작 동일)

## 다음
- 사장님께 「인계」 알림 → ANSEO 방이 `make deploy`(받는 법은 인계 문서 §1). 이 방은 배포하지 않는다.
- main 이 0.3.665 에 먼저 닿으면 세 자리(`changelog.ts` 맨 위 · `WORKLIST.md` 머리말+대기 표 · `WORKLIST-HISTORY.md` 절 제목)를 다음 번호로 옮긴다.
- 배포 뒤 사장님이 같은 이슈에서 「진단 요청」 → 2번에서 진단 고르기까지 밟아 보시면 된다. 「걸린 주소가 모두 이미 해제돼 있습니다」는 맞는 말이고, 해제는 다음 진단부터 반영된다.
