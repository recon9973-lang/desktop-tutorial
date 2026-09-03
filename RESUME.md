# RESUME — 다음 세션 이어가기 (2026-09-03 · s15 「화면 전수조사 2차 · v0.3.489 준비」)

> 새 세션은 이 파일을 **가장 먼저** 읽는다. 세션 상세 `docs/session-logs/2026-09-03-s15.md`(직전)·`2026-09-02-s14.md`,
> 결함표 `docs/ANSEO-반응형-대조표.md`(§6 = 2차), 현황 `PROJECT_STATE.md`, 지도 `핵심두뇌_MASTER.md`.

## 지금 상태 (s15 마감)

```
veo-platform  main                          c03246ac (0.3.488 코드 34136f4d · 운영 도달 [실측 2026-09-03 04:03 KST])
              claude/anseo-screen-rwd-0.3.489   ← 이 방 2차 판 v0.3.489 (main 위 1커밋 · 원격 푸시됨 · 미배포)
desktop-tutorial claude/anseo-screen-layout-optimization-ucs22y  대조표 §6·축소본 09~16·s15 로그·이 문서
```

- 사장님 오더(09-03) «pc 테블릿 모바일 버전 자체 시뮬레이션으로 오류 및 디자인 개선 사항 폰트 위치 등 매끄럽게
  적용됐는지 전수조사» → **끝났다.** 0.3.488 빌드로 29화면 × 3폭 87장(운영 글꼴) 자동 측정 8종 + 눈 검토.
  결함 8곳 고쳐 **v0.3.489** 로 커밋(가지 `claude/anseo-screen-rwd-0.3.489`). 표는 대조표 §6.
  가장 큰 것: `/console/customers` React #418(표 AEO 칸 `<td>` 안의 `<td>`) — 세 폭 전부, 개발 서버에선 안 보였다.
- 검사 전부 초록(pnpm -r typecheck·lint·test web 2,162·ui 343 · build · smoke 24화면). 재촬영 24장 pageerror 0.
- **미배포 v0.3.489** — 배포 오더가 오면 아래 절차.

## 바로 이어갈 작업

1. **배포 오더가 오면**: 가지 `claude/anseo-screen-rwd-0.3.489` 를 main 에 얹는다(다른 방이 먼저 main 에 닿아
   0.3.489 를 썼으면 규칙대로 물러나 0.3.490 으로 다시 얹음 — s14 로그의 방법: main 에서 새 가지·파일 checkout·
   판 문서만 다시 적음). 그다음 후보 가지 → CI → main → 삼중 실측(바깥 샌드박스 curl) → 도장 커밋.
2. 사장님이 캡처를 보시고 추가 지적하면 그 화면만 `audit-rwd.mjs`(scratchpad 소멸 — s15 로그대로 다시 쓴다)로 찍어 고친다.
3. 다음 후보(오더 없으면 대기): 연기 시험에 브라우저 관문(pageerror = hydration 오류) 추가 · 거래처 표 모바일 카드형 ·
   「AI 별 누적 답변」 띠 모바일 접기.

## 도구·실측 메모 (재탐색 금지)

- 캡처: `pnpm install --frozen-lockfile && pnpm build`(apps/web) 뒤 `SHOOT_FIXTURE=fx-data.json SHOOT_PORT=46xx
  node audit-rwd.mjs <출력> [경로…]`. 구글 서체는 `fonts/`(css2.css + woff2 16개)로 `context.route` 되돌림.
  Playwright `/opt/node22/lib/node_modules/playwright`, chromium `/opt/pw-browsers`, PIL 있음.
- hydration 오류 찾기: 외부 스크립트(`/_next/static/**.js`)를 막고 연 DOM 과 정상 로드 DOM 을 태그·글자만 남겨
  difflib — 개발 서버 콘솔·React 오류 번호로는 못 찾는다(s15 로그 `hydration-diff3.mjs`).
- 대시보드 덮개 창구·관문(`dashboard-layout.test.ts §1-1`)은 s14 메모 그대로.

## 주의·제약 (반드시)

- 커밋 트레일러: `Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>` + `Claude-Session:`(그 방 URL).
  모델 ID 를 커밋/PR/코드/문서에 넣지 않는다. 비밀키 금지.
- 사장님께는 「커밋」「배포」 두 낱말만. 못 잰 값은 —. `[실측]` 은 명령과 출력이 있을 때만.
- prettier 는 저장소 관문이 아니다(기존 파일도 안 맞음) — `--write` 로 남의 줄을 바꾸지 않는다.
- /console/geo AEO 독립 화면·의료 규정은 다른 방 소관.

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
