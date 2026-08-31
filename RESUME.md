# RESUME — 다음 세션 이어가기 (2026-08-31 · s10 Lovable 정본 이식)

> 새 세션은 이 파일을 **가장 먼저** 읽는다. 이번 세션 상세는
> `docs/session-logs/2026-08-31-s10.md`(+ 직전 `2026-08-30-s09.md`).

## 지금 상태 — 한눈에

```
veo-platform  main               ed7dccf  판 0.3.421  ← 운영 도달(삼중 실측 17:34 KST)
              deploy-candidate   8602fe9  docs 도장 커밋(421 실측) ← CI 대기, 초록이면 main ff
              anseo-console-port 8602fe9  (= deploy-candidate)
운영 삼중 실측 마감: 0.3.391~0.3.421 (서버·워커·웹 — 오늘 13판: 409~421)
desktop-tutorial                 이 가지(claude/image-design-workflow-analysis-efuea7)
```

> ✅ 배포 봉쇄 해제(2026-08-31 13:15 KST경 — 사장님이 Actions 예산 $10→$20).
> 이후 런 301~312 전부 초록(307 하나는 관문 걸림→핫픽스), 파이프라인 정상.

- **정본 = Lovable 시안(ANSEO 콘솔 v1.1.0)**, 커넥터 mcp__Lovable__* 로 접근
  (프로젝트 `c99930c9-cf5b-4586-855c-f9a913d79f15`, ref `216233be…`).
  lovable.app 직접 egress 는 차단 — 커넥터만, 재시도 금지.
- **보존 확정 2건**: ①대시보드 상단 검색창(DoNow — SEO·GEO용) ②거래처 진단 탭
  상단 그래프 박스 3개(SEO·GEO 레이더 + AEO 진단 카드). 둘 다 유지된 채 이식 중.
- 배포는 이 방이 직접(사장님 «모든 권한 승인»): verify 초록 → `deploy-candidate`
  커밋 → GitHub MCP `actions_list` CI 초록 → main fast-forward → Higgsfield
  `sandbox_exec` curl 삼중 실측(서버 `/api/health` · 워커 `/api/queue` ·
  웹 veo.seokorea.org/login 번들 — 호스트는 veo-platform-production.up.railway.app).
  판마다 «어디에 얼마나 배포됐는지» 실측 보고(사장님 오더).

## 🚀 바로 이어갈 작업

1. **(활성 오더) 화면 구성 «최대한 반영» 이식 — `docs/ANSEO-화면구성-격차표-v2.md`
   의 판 순서대로.** 사장님 오더(«새 화면 구성을 최대한 많이 반영, 다시 비교 분석
   해서 적용») → 격차표 v2 작성 완료(V1~V12 · 기각 8건 사유 명기). 판 배정:
   0.3.422 실행 큐 승격 → 423 대시보드 상반부 재배치 → 424 손실 도넛 →
   425 진단 실행 카드+한계 자백 카드 → 426 이슈 판정 띠 → 427 환산 구성 스택 →
   428 모션 → 429~ eyebrow·전역 도넛·상태 구성. 매 판 상시 오더 사이클(verify→
   deploy-candidate→CI→main ff→삼중 실측→도장).
2. 8602fe9(docs 도장)는 main 반영 확인 완료 — 운영 0.3.421 · 미배포 없음.
   이월(다른 방): #36 GSC env · #37 erp-v1 PR 허락 · #40 misojin v3 Drive 업로드.
3. 새 세션 배움(s10 로그 16:50·17:35 절): API 판 로컬 정산에 tests/ 루트 관문
   포함 · vitest 4 는 --reporter=basic 불가 · 판 N+1 커밋이 판 N 도장을 나른다 ·
   새 구역은 박스 대장 선등재(1차 verify 가 잡음).

## 사장님 확정 (되묻지 말 것)

- 등급 11단·등급 크게 점수 작게·톤 4단(90+/75~89/60~74/<60)·목표선 취약탈출50/
  관리목표90·**곡선·실선**(시안 점선은 실선로 번역)·판 다르면 비교 금지·못 잰 값 —·
  발행 불변·의료광고법 준수·«토큰 사용량» 어휘 유지.
- 사장님께 나가는 글은 「커밋」·「배포」 두 단어만.

## 주의·제약 (반드시)

- 커밋 트레일러: `Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>` +
  `Claude-Session: https://claude.ai/code/session_019pLvoUJ8uv46QhpsR2su5k`
  (새 세션은 자기 세션 URL 로). 모델 ID 를 커밋/PR/코드/문서에 넣지 않는다.
- 관문 무력화 금지 · 계약 재생성(`export_openapi.py`→api-client generate) ·
  WORKLIST 1,200줄 한도 · §2 머리말=표 범위 일치(worklist.test) · 박스 대장
  변경 시 사유 주석 · 60자 화면 문구 · score-display(toFixed 금지).
- s10 배움 6건은 세션 로그 «오류·배움» 절 — 같은 실수 반복 금지(특히: 백그라운드
  verify 는 exit 코드를 로그에 직접 적기 · API 판은 ruff 포함 · mypy 는 apps/api
  에서 · KST 는 date 실측 · CSS 모듈은 import 경로 확인).
- veo-platform 가지 `claude/anseo-console-port`, desktop-tutorial 은 이 가지 유지.

## 개발 환경 (이 방 재구성)

- PostgreSQL 16 재기동: `sudo -u postgres /usr/lib/postgresql/16/bin/pg_ctl -D
  /var/lib/postgresql/veo-test -o '-p 5432 -k /var/run/postgresql' -l
  /var/lib/postgresql/veo-test/log start` (턴 사이 죽음).
  `VEO_TEST_DATABASE_URL='postgresql+psycopg://postgres@/veo_test?host=/var/run/postgresql&port=5432'`
- PATH=/opt/node22/bin · PLAYWRIGHT_BROWSERS_PATH=/opt/pw-browsers ·
  web verify: `cd apps/web && pnpm verify`(로그 파일에 exit 기록).

## 대기/차단 (사용자 액션)

- S3 KPI 펼침 vs ?접기 — 사장님 확인 필요(위 3).
- 이월(다른 방): #36 GSC env · #37 erp-v1 PR 허락 · #40 misojin v3 Drive 업로드.
