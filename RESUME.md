# RESUME — 다음 세션 이어가기 (2026-09-03 · s16 「새 화면도 같은 규칙으로 · v0.3.490 준비」)

> 새 세션은 이 파일을 **가장 먼저** 읽는다. 세션 상세 `docs/session-logs/2026-09-03-s16.md`(직전)·`-s15.md`,
> 결함표 `docs/ANSEO-반응형-대조표.md`(§6 = 2차 결함 8곳 · §7 = 새 화면 관문), 현황 `PROJECT_STATE.md`, 지도 `핵심두뇌_MASTER.md`.

## 지금 상태 (s16 마감)

```
veo-platform  main                              c03246ac (0.3.488 운영 도달 [실측 2026-09-03 04:03 KST])
              claude/anseo-screen-rwd-0.3.489       ffd2a411  2차 결함 8곳 (미배포)
              claude/anseo-screen-guards-0.3.490    a90626f7  ← 위 가지 위 2커밋: 관문 3·pnpm rwd·규칙 문서 (원격 푸시 · 미배포)
desktop-tutorial claude/anseo-screen-layout-optimization-ucs22y  대조표 §6·§7 · s15·s16 로그 · 이 문서
```

- 사장님 오더(09-03) «새로 추가되는 것도 바뀐 화면 구성에 맞게 추가될 수 있도록 조치되는지 확인» → 확인(절반만 자동)
  → «이어서 진행» → **끝났다.** 관문 3종(글자 11px · 접는 폭 720/960/1100 · 표 스크롤 틀, BASELINE 방식) +
  촬영·측정 장치 `apps/web/test/rwd/`(`pnpm rwd`) + `docs/design/2026-09-03-SCREEN-RULES.md` = **v0.3.490**.
- 검사 초록(typecheck · lint 기존 경고 1 · test 247 파일 2,171). `pnpm rwd` 저장소에서 실행 확인.
- **미배포 0.3.489~0.3.490** — 배포 오더가 오면 아래 절차.

## 바로 이어갈 작업

1. **배포 오더가 오면**: 가지 `claude/anseo-screen-guards-0.3.490`(0.3.489 포함)을 main 에 얹는다. 다른 방이 먼저
   main 에 닿아 0.3.489/0.3.490 을 썼으면 규칙대로 물러나 번호를 올린다(s14 로그 방법: main 에서 새 가지·파일
   checkout·판 문서만 다시 적음). 후보 가지 → CI → main → 삼중 실측(바깥 샌드박스 curl) → 도장 커밋.
2. 사장님 추가 지적 시: `cd apps/web && pnpm build && PLAYWRIGHT_MODULE=/opt/node22/lib/node_modules/playwright
   pnpm rwd /tmp/out <경로>` 로 그 화면만 찍어 고친다(글꼴 폴더 없으면 대체 글꼴 — 겹침·잘림 값은 참고로만).
3. 오더 없으면 대기. 다음 후보: 손대는 파일부터 BASELINE 줄이기(640·900 → 720·960) · 거래처 표 모바일 카드형 ·
   「AI 별 누적 답변」 띠 모바일 접기.

## 도구·실측 메모 (재탐색 금지)

- 관문 3 의 예외 목록은 각 시험 파일 BASELINE/WRAPPED_BY_PARENT — 늘면 실패, 줄면 숫자도 내린다.
- hydration 오류는 `pnpm rwd` 의 `console` 열 `pageerror` 로 잡힌다(연기 시험은 못 잡는다).
- 대시보드 덮개 창구·관문(`dashboard-layout.test.ts §1-1`)은 s14 메모 그대로.

## 주의·제약 (반드시)

- 커밋 트레일러: `Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>` + `Claude-Session:`(그 방 URL).
  모델 ID 를 커밋/PR/코드/문서에 넣지 않는다. 비밀키 금지.
- 사장님께는 「커밋」「배포」 두 낱말만. 못 잰 값은 —. `[실측]` 은 명령과 출력이 있을 때만.
- prettier 는 저장소 관문이 아니다 — `--write` 로 남의 줄을 바꾸지 않는다.
- /console/geo AEO 독립 화면·의료 규정은 다른 방 소관(관문 BASELINE 에 그 방 파일 숫자가 있다 — 그 방이 줄이면 숫자도 같이).

---

## 이전 RESUME (s13 · 2026-08-30) — 참고용

# RESUME — 다음 세션 이어가기 (2026-08-30 · s13 체크포인트)

> 새 세션은 이 파일을 **가장 먼저** 읽는다. 세션 상세는 `docs/session-logs/2026-08-30-s13.md`(직전)·`-s12.md`,
> 현황은 `PROJECT_STATE.md`, 지도는 `핵심두뇌_MASTER.md`.

## 지금 상태 (s13 마감)

- 27화면 전수 시뮬 정본 완료(대조표 머리말=목록) · 시뮬 라벨·점선(확정 08-29) 정리 완료.
- **실물 라벨 41곳 정리 = v0.3.390** — 이 방이 직접 반영(사장님 지시 «여기방에서»).
  veo-platform 가지 `claude/anseo-console-port` 커밋 `8cd84d4`, web verify 초록. **미배포 이 한 판.**
- 운영 실측 0.3.389(그 방 배포분). 그 방은 내 desktop-tutorial 커밋을 아티팩트로 동기화한다.
- 인계 정본: `docs/ANSEO-톤앤매너-전수감사.md`(§7 반영 완료 표시 — 다른 방 중복 금지) · `docs/ANSEO-화면-대조표.md`.

## 바로 이어갈 작업

1. **v0.3.390 배포 결과 확인** — 사장님이 ANSEO 방에서 `make deploy` 실행 예정(s13 로그에 절차 있음).
   배포 후 바깥 샌드박스 curl로 운영 version=0.3.390 실측 확인해 보고.
2. 시뮬 피드백 오면 해당 파일만 수정→검증→같은 URL 재발행→커밋. 실물 추가 라벨 지적은 이 방이 직접 반영해도 됨(사장님 확정 «여기방에서» — 판 규율 준수).
3. 새 오더 없으면 대기.

## 대기/차단·다른 방 소관 (이 방에서 하지 말 것)

- **배포·배포 확인**: 사장님 확정 — 이 방은 하지 않는다. 최종 화면 후 ANSEO 방.
- **실물 톤앤매너 재작업(위반 8곳)**: ANSEO 방 — 인계 문서 `docs/ANSEO-톤앤매너-전수감사.md` 완료
  (1순위: 공개 체커/공유 등급 칩 실패색 하드코딩 — A+도 빨강).
- ANSEO 방 미배포 0.3.387~389(AEO 재구성)는 **원격에 없음**(그 방 로컬) — 새 판은 0.3.390부터가 안전.
- 이월: #36 GSC env · #37 erp-v1 PR 허락 · #40 misojin v3 Drive 업로드.

## 도구·실측 메모 (재탐색 금지)

- **운영 실측 우회**: 이 방 프록시가 운영 주소 403 → Higgsfield MCP `sandbox_exec`(바깥 샌드박스) curl로
  `/api/health`·`/api/queue`·웹 번들 판 확인 가능. 마지막 실측(08-30 06:01): 서버·워커·웹 전부 **0.3.386**.
- **실물 화면 캡처 장치**: `scratchpad/capture-screens.mjs` — smoke의 가짜 진단 서버+`next start :4601`+
  Playwright(쿠키 `veo_console_session=smoke-…`, 다크 1440px). 빌드물 필요(`apps/web/.next`).
- Playwright: `/opt/node22/lib/node_modules/playwright/index.mjs`, chromium `/opt/pw-browsers/chromium-1194/chrome-linux/chrome`, `--no-sandbox`.
- veo-platform 로컬 클론 `/home/user/veo-platform`(main=21fd12b). `gh` 2.45 apt 설치했지만 **컨테이너 리셋 시 소멸**.

## 주의·제약 (반드시)

- 브랜치: 이 방 산출물은 desktop-tutorial `claude/image-design-workflow-analysis-efuea7`, 체크포인트만 main.
  veo-platform은 이 방에서 더 이상 커밋하지 않는다(화면 작업은 시뮬만).
- 커밋 트레일러: `Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>` +
  `Claude-Session: https://claude.ai/code/session_019pLvoUJ8uv46QhpsR2su5k`(방 바뀌면 그 방 URL). 모델 ID 금지·비밀키 금지.
- 사장님께는 「커밋」「배포」 두 낱말만. 데이터는 테스트용 — 정합성 지적 금지.
- 확정 규격(되묻지 말 것): 등급 11단(A+95~F0-49, E+/E 포함·발행 완료)·등급 크게 점수 작게·톤 4단(90/75/60)·
  목표선 50/90+도달 예상(보장 아님)·AI 7종·판 다르면 비교 금지·못 잰 값 —·색+글자 병용·의료광고법 준수.

## 참고

- 세션 상세 `docs/session-logs/2026-08-30-s12.md` · `-s11.md` / 격차표 `docs/ANSEO-실물-이식-격차표.md`
- 시뮬 4종: 파이프라인 · SEO-GEO(1160bf6a…) · AEO(000e361e… v5) · 전체-통합(65ba7d78…) + 리포트(b35d70de…)
