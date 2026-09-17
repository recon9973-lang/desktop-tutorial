# RESUME — 다음 세션 이어가기 (2026-09-17 03:5x KST · s20 마감 · 재진단 텀 방)

> 새 세션은 이 파일을 **먼저** 읽는다. 상세는 `docs/session-logs/2026-09-17-s20.md`.
> 현황 `PROJECT_STATE.md`, 지도 `핵심두뇌_MASTER.md`.

## 지금까지 (핵심만)

**끝났다.** 사장님 첫 물음 «SEO 진단 30분 텀에서 요금 부담이 없다면 재진단에 텀 없애줘»
에서 시작해 둘을 냈다. **둘 다 main 에 있다.**

- **v0.3.556 — 재진단에 텀이 없다** (`93628efd`). 텀은 요금이 아니라 **호스트 예산**
  때문이었다 — 한 판이 최대 211회(200장 + 사이트맵 10 + robots 1)인데 예산이 450/시간
  이라 두 판이 한계였고, 세 판째는 막히는 게 아니라 **도중에 잘려** 「재진단했더니 점수가
  내려간 것」이 됐다. 이제 시간이 아니라 **판을 센다**(예산 ÷ 한 판 = 9판/시간). 예산은
  450 → 2,000. **순간 부하는 안 변한다** — `HostPacer` 가 연결당 1초 × 동시 2 = 초당
  최대 2회를 따로 지킨다(의뢰서 §5.2).
- **v0.3.598 — 겹친 판 번호를 합친다 + 안 그려지던 조각 제거** (`6806d955`).
  겹친 판 여섯 쌍. **번호는 새로 안 매겼다** — 어느 항목이 어느 판으로 나갔는지는 배포
  기록에만 있고, 짐작해 적으면 오류 190 과 같은 모양이다. 대신 한 항목으로 합쳤다.
- **오류 대장 190** — 콘솔 크롤이 **판마다 리미터를 새로 만들고** 있었다. 「동일 호스트
  시간당 요청」이 한 시간의 총량이 아니라 한 판 안에서의 상한으로만 돌았고, `/bot` 안내
  페이지의 공개 약속을 **지키는 자리가 없었다.** 조립을 `console_crawler()` 한 곳으로 모음.
- **이 방은 실서비스로 못 나간다**(egress). `make deploy` 의 [5/5] 도달 확인이 늘 실패한다
  — **배포 실패가 아니라 확인을 못 한 것**이다. 워크플로 「도는 판 확인」을 러너에서 돌려
  바깥에서 잰다.
- **배포는 다섯 번 걸어 한 번 닿았다.** CI 는 걸 때마다 초록이었고 막힌 자리는 늘 마지막
  한 걸음 — preflight 12분 + CI 8분 = 20분 창 사이에 다른 방이 먼저 닿는다. 판이 이 일
  하나에 **네 번** 물렸다(554→556 · 595→596 · 596→597 · 597→598).

## 바로 이어갈 작업

1. **도는 판 실측** (가벼움 · TODO #1). 이 방이 마지막으로 잰 것은
   [실측 2026-09-17 03:04 KST · 러너 35132077886] **0.3.598** — 서버·워커·웹 셋 다 ·
   뒤처진 0. 그 뒤 main 은 **0.3.603** 까지 갔는데 도는지 **못 쟀다.**
   ```
   워크플로 「도는 판 확인」(.github/workflows/rollout-check.yml) · workflow_dispatch · ref=main
   ```
   잰 뒤 `docs/WORKLIST.md` §2 머리말의 실측 줄을 그 값으로 고치고, 나간 판이 확인되면
   대기 표에서 그 줄을 뺀다(감사 A-07·B-07).
2. **미배포 없음** — 이 방 가지는 main 과 같다. 남은 작업 변경이 없다.

## 대기/차단

- **판 경쟁** — 방이 여럿이라 20분 창 사이에 main 이 계속 움직인다. 배포가 [4/5] 에서
  거절되면 그 까닭이고, 도구가 스스로 «리베이스하고 다시 내면 됩니다» 라고 적어 두었다.
  **접을 때는 접는다** — 이번에 문서 변경 하나는 다른 방이 같은 일을 먼저 해서 접었다.
- **`make deploy` 는 이 방에서 된다** — 이번 세션에 다섯 번 걸어 한 번 닿았다.

## 주의·제약

- 이 가지(`claude/seo-diagnosis-interval-removal-othn8e`) 외로 푸시 금지. main 직접 커밋 금지.
- 배포는 **`make deploy` 만**. 오더 없이 밀지 않는다.
- **문서만 바꾸는 판에도 변경이력 항목을 쓴다** — 안 쓰면 `claim_version.py` 가 main 의
  이미 나간 기록에 새 번호를 달고, 그 자리를 관문이 [1/4] 에서 세운다.
- **저장소의 산문을 근거로 쓸 때 `[실측]` 표시가 있는지 먼저 본다**(오류 190 의 처방).
  없으면 그것은 남이 추론한 것이고, 인용하는 순간 내 주장이 된다.
- 커밋 트레일러: `Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>` +
  `Claude-Session: https://claude.ai/code/session_016xfzF9WQrak6JdFWyWtLTi`. 모델 ID 는 트레일러에만.
- 사장님께는 「커밋」·「배포」 두 낱말만. 못 잰 값 «—», 지어낸 수치 금지, 의료광고법 준수.

## 참고 — 이 방 환경 세우기

```
git clone --depth 1 https://github.com/recon9973-lang/veo-platform /home/user/veo-platform
.venv/bin/pip install -e "apps/api[dev]"      (또는 PYTHON=/usr/bin/python3.12 make setup)
pnpm install
service postgresql start                       role root / 비번 veo / DB veo_test
  alembic 은 VEO_DATABASE_URL 도 함께 줘야 붙는다
시험: PGPASSWORD=veo VEO_TEST_DATABASE_URL="postgresql+psycopg://root:veo@localhost:5432/veo_test" \
        ../../.venv/bin/python -m pytest tests -q        (apps/api 에서)
웹:   npx vitest run · npx tsc --noEmit · npx next build  (apps/web 에서)
배포: VEO_DEPLOY_ORDER="<사장님 원문>" PGPASSWORD=veo VEO_TEST_DATABASE_URL=... \
        PY=/home/user/veo-platform/.venv/bin/python make deploy
```
