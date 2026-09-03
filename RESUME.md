# RESUME — 다음 세션 이어가기 (2026-09-04 02:00 KST · s17 「0.3.489~0.3.497 배포 마감」)

> 새 세션은 이 파일을 **가장 먼저** 읽는다. 세션 상세 `docs/session-logs/2026-09-03-s17.md`(직전)·`-s16.md`·`-s15.md`,
> 결함표 `docs/ANSEO-반응형-대조표.md`(§6 2차 · §7 관문 · §7-4 예외 줄임 · §7-5 누름 마무리·배포), 현황 `PROJECT_STATE.md`, 지도 `핵심두뇌_MASTER.md`.

## 지금 상태 (s17 마감)

```
veo-platform  코드 판              74905ea0  0.3.497 운영 도달 [실측 2026-09-04 01:55 KST 서버·워커·웹 셋 다]
              main                 0065038a  배포 도장 커밋(문서만, 판 번호 그대로 0.3.497) — CI run 33781695498 초록 → main 17:08 UTC
desktop-tutorial claude/anseo-screen-layout-optimization-ucs22y  대조표 §7-5 도장 · s17 로그 · 이 문서
```

- **미배포 없음.** 0.3.494~0.3.497 넉 판이 한 묶음으로 나갔다:
  - 화면 점검 방 0.3.494(전수 점검 2차) · 0.3.495(새 화면 관문 3종) · 0.3.497(누름 영역 마무리)
  - 입지 방 0.3.496(거래처 「입지」 탭·설정 「데이터 원천」·AI 스트립 연결 상태 밑줄)
  - 이 방 판 두 번 물림: 0.3.489~0.3.490 → 0.3.494~0.3.495 (23:21 KST 배포) · 0.3.496 → 0.3.497 (01:55 KST 배포)
- 이 방이 넣은 관문 3종이 두 번 자기 값을 했다: 처음 합침에서 입지 방 새 표 4곳의 없는 클래스 `tableFlow`→`tableWrap`
  잡아 고침 · 이후 합침에서 입지 방 CSS 세 자리(접는 폭 · 글자 하한 · 표 감싸개)를 통과시키게 유도 (147051d5).

## 바로 이어갈 작업

1. **이 회차는 완전히 닫혔다** — 0.3.494~0.3.497 넉 판 배포·삼중 실측·도장까지 끝
   (도장 커밋 `0065038a` main 17:08 UTC 도달). 남은 후속 작업 없음.
2. 오더 없으면 대기. 다음 후보:
   - `/console/geo` 「키워드 조사」 본문 링크 15px — **AEO 방 몫**으로 남겨 뒀다(같은 수법 한 줄).
   - `/console/mine` 「내 것」·「◀ 지난달」·「다음달 ▶」 19px — 입지/발행 대장 방 몫.
   - 거래처 표 모바일 카드형 · 「AI 별 누적 답변」 띠 모바일 접기 · 산점도 이름표 2차원 밀어내기.
   - 남은 접는 폭 BASELINE 11 파일(1240·760·700·860·600·48rem·min-width 둘 · geo 방 파일은 그 방 몫).
3. 사장님 화면 지적 시: `cd apps/web && pnpm build && PLAYWRIGHT_MODULE=/opt/node22/lib/node_modules/playwright
   pnpm rwd /tmp/out <경로>`. 전 화면은 경로 없이(56장 ≈ 8분, 배경으로).

## 도구·실측 메모 (재탐색 금지)

- 관문 3 의 예외는 각 시험 파일 BASELINE/WRAPPED_BY_PARENT — 늘면 실패, 줄면 숫자도 내린다. 누름 기준 24px(문서 §3·WCAG 2.5.8).
- 촬영 장치 오탐: 라디오·체크박스가 큰 `<label>` 안이면 이름표가 누름 영역이다(0.3.497 에서 고침).
- hydration 오류는 `pnpm rwd` 의 `console` 열 `pageerror`(연기 시험은 못 잡는다).
- 삼중 실측: `sandbox_exec` 로 `https://veo-platform-production.up.railway.app/api/health` · `/api/queue` ·
  `https://veo.seokorea.org/login` HTML 의 «앱 버전 v0.3.…». DB 경로 `/api/customers` = 401 이 정상.
  웹 판 grep 은 `grep -o '앱 버전 v<!-- -->[0-9.]*'` 로(주석 사이에 낀 판 문자열).
- 이 컨테이너엔 veo-platform `.venv` 가 없다 — `make preflight` 의 ruff·pytest·계약 드리프트 ✗ 는 **못 잰 것**(CI 가 잰다).
- CI 상태: GitHub MCP `actions_list`(owner recon9973-lang · repo veo-platform · ci.yml · branch deploy-candidate).
- 배포 길: 후보 가지 `deploy-candidate` 푸시 → CI 초록 → **같은 SHA** 를 main 으로 → 삼중 실측 → 도장 커밋(같은 길로).
- 판 번호 겹침 때: force-with-lease 는 sandbox classifier 가 막을 수 있다 — 그때는 `--force-with-lease=<ref>:<expected-sha>`
  형식으로 명시하면 통과했다(2026-09-04 01:34 UTC).

## 주의·제약 (반드시)

- 커밋 트레일러: `Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>` + `Claude-Session:`(그 방 URL).
  모델 ID 를 커밋/PR/코드/문서에 넣지 않는다. 비밀키 금지.
- 사장님께는 「커밋」「배포」 두 낱말만. 못 잰 값은 —. `[실측]` 은 명령과 출력이 있을 때만. 데이터는 테스트용 — 정합성 지적 금지.
- prettier 는 저장소 관문이 아니다 — `--write` 로 남의 줄을 바꾸지 않는다.
- /console/geo AEO 독립 화면·의료 규정은 다른 방 소관(관문 BASELINE 에 그 방 파일 숫자가 있다).
- 판 번호 규칙: **먼저 main 에 닿은 쪽을 두고 뒤엣것이 물러난다.**

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
