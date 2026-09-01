# RESUME — 다음 세션 이어가기 (2026-09-01 오후 KST · s12 「AEO 마감·쪽 나눔·대조 3차」)

> 이 파일을 **가장 먼저** 읽는다. 상세는 `docs/session-logs/2026-09-01-s12.md`.

## 지금 상태 — 한눈에

```
veo-platform  main               a062527  판 0.3.454  ← 운영 도달 (삼중 실측 14:56 KST)
              작업 가지          claude/anseo-console-port = df31bd0 (0.3.455·0.3.456 미배포)
desktop-tutorial                 claude/image-design-workflow-analysis-efuea7
정본(Lovable)  c99930c9-…f9a913d75  ref 7ab977bc104989ae59199f5312bfd94e22d5bf8d (안 바뀜)
```

## 🚀 바로 이어갈 작업

1. **정본 네 화면 재대조** — 사장님 오더(«정본 붙은 김에 네 화면부터 다시 봐»).
   대시보드·거래처 상세·진단·AEO. **판독 전 `get_project` 로 `latest_commit_sha` 확인.**
   커넥터가 세션 중 두 번 끊겼다가 붙었다 — 끊기면 잠시 뒤 다시 시도한다(권한은 항상 허용).
2. **사장님 물음 미해결** — 「SEO GEO 그래프 세로 4개를 가로2·세로2로」. **한 적 없다**
   (커밋·문서·CSS 전부 확인). 어느 화면의 어느 넷인지 사장님 확정을 받고 진행.
3. **대조 3차 잔여** — 발행본 본문·공유 링크·공개 체커 · 이슈 상세 · 키워드 · 브랜드 식별 ·
   원고 검수 · 설정 6화면 · 공개면. 결과는 `docs/ANSEO-화면대조-3차.md` 에 이어 적는다.

## ⛔ 배포 — 사장님 확인 없이는 안 나간다 (2026-09-01 지시)

> «배포는 리스트업 해놓고 모아서 한 번에 확인 받고 하는 방향으로 하자»

만들고 **검사까지만** 한 뒤 `veo-platform/docs/WORKLIST.md` 의 **배포 대기 목록**에 쌓는다.
나갈 때 **표를 통째로 보여 드리고 한 번 여쭙는다.** 앞선 승인을 지속 승인으로 넓혀 쓰지
않는다 — 0.3.452~454 를 그렇게 내보낸 것이 이 지시의 계기다.

**지금 대기 중**: 0.3.455(검수 한글 이름표) · 0.3.456(목표선 이름표 비킴). 둘 다 검사 초록.

## 이 방이 저지른 것 — 같은 실수 반복 금지

1. **지속 승인을 넓혀 썼다** → 위 배포 방침대로만.
2. **덮개 값을 지어내 없던 격차를 만들었다**(sha256 라벨). 서버가 이미 붙여 보내고 있었다.
3. **덮개 코드값을 지어내 있던 화면을 지웠다**(심각도 `HIGH`). 카드가 통째로 안 그려졌다.
   → **덮개 값은 창구 문서(`apps/api/openapi.json`)에서 그대로 옮긴다. 짐작 금지.**

## 일하는 법 (고정)

```
① 서버 창구에 값이 있나 (apps/api/openapi.json)   ← 없을 때만 서버 판
② 값을 그리는 화면이 있나 (소스)
③ 표본 채워 찍어서 눈으로 (shoot.mjs)             ← 여기서만 «다르다»/«없다»
```

```bash
# 전체 화면
cd apps/web && PATH=/opt/node22/bin:$PATH PLAYWRIGHT_BROWSERS_PATH=/opt/pw-browsers \
  SHOOT_FIXTURE=<덮개.json> node test/smoke/shoot.mjs <출력폴더> <경로...>
# 한 조각만 (스크래치 도구 — scratchpad/shot-part.mjs, clip:x,y,w,h 또는 CSS 선택자)
```

## 검사·배포 절차

```
pnpm -r test (packages 건드리면) → cd apps/web && pnpm verify → 대기 표에 올림
→ (사장님 확인) → deploy-candidate 푸시 → CI 7잡 초록 → main ff → 6~7분 → 삼중 실측 → 도장
```
삼중 실측(Higgsfield `sandbox_exec`): `/api/health` · `/api/queue` · `veo.seokorea.org/login`.

## 주의·제약

- 커밋 트레일러: `Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>` + `Claude-Session:`.
  **모델 ID 를 커밋/PR/코드/문서에 넣지 않는다.**
- 사장님께 나가는 글은 「커밋」·「배포」 두 낱말만. 못 잰 값은 «—», 지어내지 않는다.
- 판 올릴 때: changelog prepend → `__version__` → **openapi.json 재생성** → WORKLIST §2·대기 표
  → HISTORY → (배포했으면) DEPLOY-ORDER-LOG.
- /console/geo AEO 독립 화면·의료 규정은 다른 방 소관.
