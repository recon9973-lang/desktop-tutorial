<!-- 가지: claude/auto-diagnosis-schedule-check-vhmz2j -->
# RESUME — 자동 진단 방 (2026-09-18 마감 · 상세 `docs/session-logs/2026-09-18-auto-diagnosis.md`)

> 새 세션은 이 파일을 **먼저** 읽는다. 현황 `PROJECT_STATE.md`, 지도 `핵심두뇌_MASTER.md`.

## 이 방이 낸 것 (전부 main 에 있다)

```
v0.3.544  정기 진단이 하루 두 번 돌던 것 · 실행자 「자동」 · GEO 탭도 「자동」
v0.3.546  대장 도장
v0.3.551  판 번호를 나갈 때 정한다            (구조 제안 1)
v0.3.554  채점 자리를 방마다 나눈다            (구조 제안 2)
v0.3.555  지금 누가 도는지 알려 준다            (구조 제안 3)
v0.3.613  판을 물릴 때 이미 나간 항목·기록·줄에 손대지 않는다  ← 이번 회차 · **나갔다**
v0.3.614  그 도장(문서만) — 0.3.613 이 도는 것을 확인하고 대기 표에서 지움
```

**여섯 판의 실서비스 확인이 끝났다** — [실측 2026-09-18 21:10 KST · 러너 「도는 판
확인」 실행 35343309570] 화면·진단 서버·워커 모두 **0.3.607**. 앞 회차가 「사장님이 한
번 재 주셔야 한다」고 넘긴 일을 **다른 방이 만든 러너가 대신했다.**

## 이번 회차에서 안 것

- `claim_version.py` 가 세 자리에서 **이미 나간 것**에 새 번호를 달 수 있었다.
  절 제목(실측 `72f9d3cd`) · 대기 표 줄(오늘 시늉으로 재현) · **변경이력 항목**
  (실측 `cd6496d5` → `1a80d707` — 그래서 한때 main 에 **0.3.609 항목이 없었다**).
  셋 다 막았고 시험 일곱을 세웠다(고침을 빼면 넷이 빨간불).
- **남의 기록은 안 건드렸다.** 그 방 항목을 가르는 것은 그 방 몫이다 — 일어난 일과
  자리만 대장에 적었다.

## 바로 이어갈 작업

1. **이 방에 남은 코드 일감은 없다.** 새 오더를 받으면 그때부터다.
2. **0.3.614(도장 · 문서만)가 도는지만 재면 된다** — Actions 의 「도는 판 확인」을
   `mcp__github__actions_run_trigger` 로 부른다(`gh workflow run` 은 이 방 열쇠로 403).
   확인되면 대장 §2 대기 표에서 **이 방 줄만** 지우고 변경이력 절에 「나갔다」.
   **반영 직후에 재면 반만 보인다** — [실측] 00:25 에는 웹만 새 판이고 서버·워커는 앞
   판이었고, 7분 뒤 셋이 같아졌다. 재는 시각이 사실의 일부다.
3. **사장님 몫 하나 — CI 를 필수 검사로.** `GitHub → Settings → Branches → main →
   Require status checks → CI`. 대장 §5 에 있다.

## 주의·제약

- 이 가지 외로 푸시 금지. 체크포인트 문서는 desktop-tutorial main 에 커밋.
- 배포는 **`make deploy` 만**. `VEO_DEPLOY_ORDER` 에 사장님 원문 인용.
- **판 번호는 세 번 집혔다**(0.3.610·0.3.611·0.3.612 → 0.3.613). 배포 한 번은 [4/5]
  에서 거절됐다(CI 8분 사이 다른 방이 먼저 닿음) — 리베이스해서 다시 내보내면 된다. main 을 받아 온 뒤에는
  `make bump-version TO=<main+1>` 로 올려 두고 변경이력·대기 표·절 제목을 그 번호로
  적는다 — main 과 같은 번호로 두면 변경이력 중복 관문이 점검에서 잡는다.
- 대장·변경이력에 **「민다·푸시」 금지**(`two-words-only`) — 「커밋」·「배포」만.
- 대기 표와 §2 머리말의 **미배포 범위가 일치**해야 한다(`worklist.test.ts`).
- 커밋 트레일러: `Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>` +
  `Claude-Session: https://claude.ai/code/session_01SmorTxHEe4BY34eFSpBBnX`.
- 이 방은 운영 주소로 못 나간다(CONNECT 403) — `[5/5]` 는 늘 오류 22. **배포 실패가 아니다.**
- 못 잰 값 «—», 지어낸 수치 금지, 의료광고법 준수.

## 환경 세우기

```
PYTHON=/usr/bin/python3.12 make setup   ·   pnpm install
service postgresql start                (role root / 비번 veo / DB veo_test 는 이미 있다)
PGPASSWORD=veo VEO_TEST_DATABASE_URL="postgresql+psycopg://root:veo@localhost:5432/veo_test" make preflight
```
