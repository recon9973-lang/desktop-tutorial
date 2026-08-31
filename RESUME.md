# RESUME — 다음 세션 이어가기 (2026-08-31 · s10 Lovable 정본 이식)

> 새 세션은 이 파일을 **가장 먼저** 읽는다. 이번 세션 상세는
> `docs/session-logs/2026-08-31-s10.md`(+ 직전 `2026-08-30-s09.md`).

## 지금 상태 — 한눈에

```
veo-platform  main               4588714  판 0.3.438  ← 삼중 실측 마감(22:35 KST)
              deploy-candidate   ab2f786  판 0.3.439  ← CI 런 333 진행 중
              (로컬)             0.3.440  ← 커밋 대기(verify 중 — 439 초록 후 밀기)
운영 삼중 실측 마감: ~0.3.438 (서버·워커·웹 — 오늘 24판: 409~438)
desktop-tutorial                 이 가지(claude/image-design-workflow-analysis-efuea7)
```

- **정본 = Lovable 시안(ANSEO 콘솔 v1.1.0)**, 커넥터 mcp__Lovable__* 로 접근
  (프로젝트 `c99930c9-cf5b-4586-855c-f9a913d79f15`, ref `216233be…`).
  프리뷰는 **비공개**(Lovable 게이트) — 콘솔 픽셀 캡처는 자동 로그인이 실행 환경
  권한에 막혀 보류, **정본 소스 전문 판독 대조**로 진행(원문이 완전한 사양).
  캡처 계정 capture@anseo.local 존치(삭제는 후속 — 사장님 고지됨).
- **활성 오더**: «ㄱㄱ 대시보드부터 통이식 — 새 화면 기준, 기존은 맥락 필요분만».
  진행: 438 머리줄 셸 → 439 «이번 주 실행»+단계→큐 거르기 → 440 AEO 깔때기.
  다음 후보: 거래처 목록 → 거래처 상세 탭 → 이슈 → 리포트 순 화면별 통이식.
- 배포 사이클: verify→deploy-candidate(+anseo-console-port)→CI 초록→main ff→
  6분→Higgsfield sandbox_exec 삼중 실측(/api/health·/api/queue·웹 grep)→도장.
  CI 도는 중 재푸시 금지(cancel-in-progress) — 다음 판은 로컬로 쌓기.

## 🚀 바로 이어갈 작업

1. **(즉시)** CI 런 333(0.3.439, ab2f786) 초록 확인 → main ff → 440 커밋·푸시
   → 6분 → 삼중 실측 → 도장(«미배포 없음» + 오더 로그 26번째까지 반영 완료).
2. **대시보드 통이식 잔여**: 정본 대비 남은 격차 = 조직 이름 제목(원천 없음 —
   서버 확장 후보) · 대시보드 커버리지 와플(원천 조사) · LeverageBar(품 없음 —
   판 A 대기). 이후 거래처 목록 화면 통이식(0.3.441~).
3. 후순위: 발행본 문서 톤 · 통합 이슈 띠(서버) · 판 A 품 저작(사장님 확인) ·
   판 B 기한. AEO 독립 화면·의료 규정은 다른 방.

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

- (해소) S3 KPI = «?접기» 확정(08-31) — 재론 금지.
- 이월(다른 방): #36 GSC env · #37 erp-v1 PR 허락 · #40 misojin v3 Drive 업로드.
