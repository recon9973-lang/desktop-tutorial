# RESUME — 다음 세션 이어가기 (2026-09-01 저녁 KST · s13 「두 방 합류 배포 · 정본 대조 재개」)

> 이 파일을 **가장 먼저** 읽는다. 상세는 `docs/session-logs/2026-09-01-s13.md`.

## 지금 상태 — 한눈에

```
veo-platform  main              82b6266  판 0.3.459  ← 운영 도달 (삼중 실측 18:56 KST)
              작업 가지         claude/anseo-console-port = 82b6266 (main 과 같음 · 미배포 없음)
desktop-tutorial                claude/image-design-workflow-analysis-efuea7
정본(Lovable)  c99930c9-…f9a913d75  ref 7ab977bc104989ae59199f5312bfd94e22d5bf8d (마지막 확인 기준)
```

**배포 대기 없음.** 0.3.455~0.3.459 가 한 묶음으로 나갔다(ANSEO 방 455 + 이 방 456~459).

## 🚀 바로 이어갈 작업 — 사장님 오더 «나머지 세 화면 정본 대조 계속해»

1. **커넥터부터 확인한다.** 앞 세션은 Lovable 이 `enabledInChat: false` 라 정본을 못 읽었다.
   `ListConnectors(["Lovable"])` 로 확인하고, 도구가 잡히면 **`get_project` 로 `latest_commit_sha`**
   를 먼저 본다(위 ref 와 다르면 정본이 바뀐 것이다).
2. **세 화면 대조** — 대시보드 · 거래처 상세 · 진단. 실물 쪽은 이미 찍어 뒀다(아래 «실물 확보»).
   결과는 `docs/ANSEO-화면대조-3차.md` 에 이어 적는다.
3. **미판정 관찰 하나** — 진단 탭 세 카드가 가로로 서면서 SEO·GEO 카드 아래가 크게 빈다
   (AEO 카드 키에 끌려 늘어남). 표본에 영역 점수가 없어 도형이 안 그려진 탓일 수 있다.
   **정본의 그 자리 배치를 보고 판단한다.** 찍기 전에 «다르다»고 하지 않는다.
4. **대조 3차 잔여**(정본 없이도 되는 것) — 발행본 본문·공유 링크·공개 체커 · 이슈 상세 ·
   키워드 · 브랜드 식별 · 원고 검수 · 설정 6화면 · 공개면.

## 실물 확보 — 다시 찍는 법

```bash
cd /home/user/veo-platform/apps/web
PATH=/opt/node22/bin:$PATH PLAYWRIGHT_BROWSERS_PATH=/opt/pw-browsers \
  SHOOT_FIXTURE=<덮개.json> node test/smoke/shoot.mjs <출력폴더> <경로...>
```

- **대시보드는 `/console/dashboard` 다.** `/console` 은 404.
- 거래처 상세는 덮개 없이는 404 — 계약 예시가 「가장 비어 있는 유효한 것」이라 판이 null 이 된다.
- 덮개 만드는 법: 계약 예시 뼈대(`test/smoke/openapi-examples.mjs` 의 `loadExamples`/`matchRoute`)를
  뜬 뒤 **값만** 채운다. 앞 세션 스크립트는 컨테이너와 함께 사라졌으니 다시 쓴다.
  거래처 상세 구조는 `sites: [{site, seo[], geo[]}]`(`SiteHistoryPayload` · `ScanHistoryEntry`).

## ⛔ 배포 — 사장님 확인 없이는 안 나간다 (2026-09-01 지시)

> «배포는 리스트업 해놓고 모아서 한 번에 확인 받고 하는 방향으로 하자»

만들고 **검사까지만** 한 뒤 `veo-platform/docs/WORKLIST.md` 「배포 대기 목록」에 쌓는다.
나갈 때 표를 통째로 보여 드리고 **한 번 여쭙는다.** **지금 대기 중인 것은 없다.**

## 이 방이 저지른 것 — 같은 실수 반복 금지

1. **지속 승인을 넓혀 썼다**(0.3.452~454) → 위 배포 방침대로만.
2. **덮개 값을 지어냈다** — 세 번째다. 이번엔 `latest_score` 를 짐작해 넣어 KPI 가 전부 «—» 로
   나왔다(창구는 `{site, seo[], geo[]}`). **덮개 값은 `apps/api/openapi.json` 에서 그대로 옮긴다.**
3. **판 번호는 방이 갈리면 부딪힌다** — 0.3.303·0.3.313·0.3.455. 규칙: **먼저 main 에 닿은 쪽을
   두고 뒤엣것이 물러난다.** 재번호 시 changelog·`__version__`·openapi 재생성·대장·HISTORY 전부 정합.

## 일하는 법 (고정)

```
① 서버 창구에 값이 있나 (apps/api/openapi.json)   ← 없을 때만 서버 판
② 값을 그리는 화면이 있나 (소스)
③ 표본 채워 찍어서 눈으로 (shoot.mjs)             ← 여기서만 «다르다»/«없다»
```

## 검사·배포 절차

```
pnpm -r test (packages 건드리면) → cd apps/web && pnpm verify → 대기 표에 올림
→ (사장님 확인) → deploy-candidate 푸시 → CI 7잡 초록 → main → 6~7분 → 삼중 실측 → 도장
```
삼중 실측(Higgsfield `sandbox_exec`): `/api/health` · `/api/queue` · `veo.seokorea.org/login`.
관문 둘이 자주 걸린다: 대장 **1200줄** 상한 · 머리말 문형은 «미배포 **없음**» 또는 «미배포 **X~Y**».

## 주의·제약

- 커밋 트레일러: `Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>` + `Claude-Session:`.
  **모델 ID 를 커밋/PR/코드/문서에 넣지 않는다.**
- 사장님께 나가는 글은 「커밋」·「배포」 두 낱말만. 못 잰 값은 «—», 지어내지 않는다.
- lovable.app 직접 접속은 막혀 있다 — **커넥터로만.** 비밀키 값은 대화에 내지 않는다.
- /console/geo AEO 독립 화면·의료 규정은 다른 방 소관.

## 참고
- 현황은 `PROJECT_STATE.md`, 지도 위치는 `핵심두뇌_MASTER.md`.
