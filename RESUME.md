# RESUME — 다음 세션 이어가기 (2026-09-07 21:0x KST · s19 마감 · 자동 진단 방)

> 새 세션은 이 파일을 **먼저** 읽는다. 상세는 `docs/session-logs/2026-09-07-s19.md`.
> 현황 `PROJECT_STATE.md`, 지도 `핵심두뇌_MASTER.md`.

## 지금까지 (핵심만)

- **고친 것**: veo-platform 의 SEO 정기 재진단이 **하루에 두 번** 돌던 결함.
  `seo/rescan.py` 가 도는 날은 KST 로 고르면서 멱등키 날짜만 UTC 로 적어, **09:00 KST
  (=00:00 UTC)** 경계에서 한국의 하루가 열쇠 둘로 갈렸다. 사장님 캡처의 00:0x·09:0x 두 줄이 그것.
  + 진단 이력 **실행자 칸에 「자동」** 표기(근거는 스케줄 멱등키 하나뿐 — 없으면 「기록 없음」 그대로).
- **어디에**: 저장소 `recon9973-lang/veo-platform`(이 저장소 아님) ·
  가지 `claude/auto-diagnosis-schedule-check-vhmz2j` · 커밋 **`a9de20fa`**(4건) · 판 **0.3.540** · **미배포**
  (앞 커밋 `702cc84c` 는 채점 자리에서 **CI 잡 7개 전부 초록**이었다 — 그 뒤 다른 방이 0.3.539 를 main 에
  넣어 `origin/main`=`7ae4f40b` 위로 다시 리베이스했다. 충돌 다섯: 판 둘(`__init__.py`·`openapi.json`,
  0.3.540 유지) · `changelog.ts` · `WORKLIST.md`(머리말 `0.3.537~0.3.540` + 대기 표에 0.3.540 줄) ·
  `WORKLIST-HISTORY.md`. **판은 다시 안 물렸다** — 0.3.540 > 0.3.539.)
- **그 뒤 반쪽을 더 찾아 같은 판에 얹었다**(커밋 `0a46ee5c`) — 한 번의 진단은 같은 크롤로
  SEO·GEO **두 실행**을 저장하는데(`geo/companion.py`) 동반 GEO 저장만 작업 식별자를 안 받아,
  정기 진단이 돌면 **SEO 탭은 「자동」·GEO 탭은 「실행자 기록 없음」**. 사람이 부른 진단은
  이름이 적히니 자동에서만 드러나는 어긋남이었다. `run_console_scan` → 동반 채점 → 저장으로
  `job_id` 를 잇고 관문 둘(부르는 자리가 넘기는가 · GEO 절반이 「자동」으로 읽히는가).
  같은 종류를 더 찾으려 하루 열쇠 만드는 자리를 전부 봤다 — 둘뿐이고 관측 쪽은 멀쩡하다.
- **같은 종류 훑기를 끝냈다**(커밋 `c278a91a`) — 결함의 모양은 「순간을 어느 시간대의 달력날짜로
  바꾸는가」. 하루 열쇠 둘 · `ScanRun` 만드는 자리 하나 · SQL 날짜 묶기 0건 · 화면은 시간대를
  못 박는 관문(`seoul-time.gate.test.ts`) 있음. **남은 하나**: `keywords/service.py`
  `_collect_trends` 가 네이버 데이터랩에 UTC 날짜로 묻는다 — **안 고쳤다**(월 단위·365일 창이라
  어긋나는 건 매월 1일 아홉 시간 동안 이번 달 칸 하나뿐인데, 고치면 잰 값이 움직여
  「잰 값 무변경」이던 이 판의 성질을 잃는다). 대장 §4-A 에 적어 별도 판 몫으로 남겼다.
  대장 줄 상한(1200)에 걸려 끝난 줄 하나(심평원 광주 라벨 보정 v0.3.477, 변경이력에 있음)를 지웠다.
- **열쇠가 서버 여러 대에서도 참인지 확인하고 고쳤다**(커밋 `a9de20fa`) — 청소부는 **API
  프로세스마다** 하나씩 돈다(단일 인스턴스 표시 없음). 조회와 넣기 사이 틈은 DB 유일 제약
  (`uq_jobs_org_type_idempotency_key`)이 이미 막고 있었으나, **깨진 뒤** `submit` 이 예외를
  그대로 올려 진 쪽 청소가 그 판째 중단됐다(나머지 사이트는 다음 주기까지 안 돈다).
  저장점 안에서 넣고 깨지면 이긴 쪽을 돌려준다. 관문 하나, 반증 확인함.
- **검증**: `690682ff` 에서 **preflight 전체 초록**(ci-local 7,179 · pnpm -r test 2,259 ·
  test-db · typecheck · lint · build · smoke · 계약 · 대소문자 · 충돌 표시 0).
  그 위 `0a46ee5c`·`c278a91a` 는 **부분 검증만** — ruff 0 · mypy 0(456) ·
  `tests/seo/test_geo_companion.py` + `test_scan_history.py` 49건 · 대장 관문 16건 ·
  check-contracts. **배포 전 preflight 를 다시 돌려야 한다**(규칙: 나갈 그 커밋에서).
  새 시험 10건. 마이그레이션 없음. 잰 값 무변경.
- **판 번호를 앞질러 잡았다** — 오늘 6회 부딪혀서(0.3.531~0.3.536, ANSEO·입지 방) 0.3.540 을
  확보하고 537~539 를 비웠다. 이제 main 이 움직여도 판을 다시 안 물려도 된다.

## 바로 이어갈 작업

1. **배포 — 사장님 지시 «배포는 모아서 하고»** 로 **보류 중**이다. 가지는 초록 상태로 대기.
   낼 때는 아래 3단계이고, **main 이 또 움직였으면 §2 처럼 리베이스부터** 한다.
   이 방은 `make deploy` 가 권한 관문에 막혀 대신 못 한다(손으로 흉내 내면 그 관문을 우회하는 것).
   ```
   cd $(mktemp -d) && git init -q
   git fetch https://github.com/recon9973-lang/veo-platform.git claude/auto-diagnosis-schedule-check-vhmz2j
   git push --force https://github.com/recon9973-lang/veo-platform.git FETCH_HEAD:refs/heads/deploy-candidate
   ```
   → CI 초록불 확인(actions?query=branch%3Adeploy-candidate) →
   ```
   git push https://github.com/recon9973-lang/veo-platform.git FETCH_HEAD:refs/heads/main
   ```
   3단계는 `--force` 금지. 거절되면 다른 방이 닿은 것 — **문서 충돌만** 풀면 된다(2분).
2. **main 이 움직였으면** veo-platform 에서 `git rebase origin/main` → 충돌은
   `changelog.ts`·`WORKLIST.md`(머리말+대기 표)·`WORKLIST-HISTORY.md` 셋 → `make preflight`.
   **판 0.3.540 은 그대로 둔다**(관문은 「내 판 > main 판」만 본다).
3. 배포 뒤 **실측 도장**: `veo.seokorea.org/login` 판 표시·`/api/health`·`/api/queue` 가
   0.3.540 인지 → 대장 §2 머리말·대기 표에서 그 줄 지우고 HISTORY 제목에 「나감」.
   **이 방은 그 주소로 못 나간다**(403) — 바깥에서 재야 한다.
4. `docs/DEPLOY-ORDER-LOG.md` 에 오더 줄이 안 남았다(스크립트가 시작조차 못 했다). 배포 뒤 채운다.
5. **별도 판 몫** — 키워드 추이 기간을 한국 날짜로(`keywords/service.py` `_collect_trends`).
   0.3.540 에 안 섞은 까닭은 위에 적었다. 고칠 때 **바뀐 값이 어디까지 움직이는지 먼저 재서 적을 것.**

## 대기/차단

- **`make deploy` 권한** — `.claude/settings.json` 에 아래를 넣고 **방을 새로 시작**해야 듣는다.
  에이전트가 제 권한을 넓히는 건 관문이 막으므로 **사장님이 직접** 넣으셔야 한다.
  ```json
  "permissions": { "allow": [
    "Bash(make deploy)", "Bash(make deploy:*)",
    "Bash(make preflight)", "Bash(make preflight:*)",
    "Bash(export VEO_DEPLOY_ORDER=*)"
  ] },
  ```
- **방 공조** — 클라우드 방끼리 직접 호출이 안 된다(`ListAgents` 에 안 잡히고 세션 ID 로도 거절).
  사장님이 전달자. 입지 방·ANSEO 방에 「0.3.540 은 자동진단 방, 537~539 비움」을 알려야 한다.

## 주의·제약

- 이 가지 외로 푸시 금지. 체크포인트 문서는 desktop-tutorial main 에 커밋(CLAUDE.md 규칙).
- 배포는 **`make deploy` 만**. 오더 없이 밀지 않는다. `VEO_DEPLOY_ORDER` 에 사장님 원문 인용.
- `deploy-candidate` 는 덮어쓰는 채점 자리라 **`--force` 가 정상**. main 은 절대 force 금지.
- 대장·변경이력에 **「민다·푸시」 금지**(`two-words-only` 관문) — 「커밋」·「배포」 두 낱말만.
- 대기 표와 §2 머리말의 **미배포 범위가 일치**해야 한다(`worklist.test.ts`). 오늘 여기서 한 번 걸렸다.
- 커밋 트레일러: `Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>` +
  `Claude-Session: https://claude.ai/code/session_01SmorTxHEe4BY34eFSpBBnX`. 모델 ID 는 트레일러에만.
- 사장님께는 「커밋」·「배포」 두 낱말만. 못 잰 값 «—», 지어낸 수치 금지, 의료광고법 준수.

## 참고

- veo-platform 환경 세우기: `PYTHON=/usr/bin/python3.12 make setup` · `pnpm install` ·
  로컬 PostgreSQL(`service postgresql start`, role `root`/비번 `veo`, DB `veo_test`, `alembic upgrade head`) ·
  `gh` 는 릴리스 tarball 로 설치(`/usr/local/bin/gh`).
- preflight 실행: `PGPASSWORD=veo VEO_TEST_DATABASE_URL="postgresql+psycopg://root:veo@localhost:5432/veo_test" make preflight`
