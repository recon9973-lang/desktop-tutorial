# RESUME — 다음 세션 이어가기 (2026-09-07 21:0x KST · s19 마감 · 자동 진단 방)

> 새 세션은 이 파일을 **먼저** 읽는다. 상세는 `docs/session-logs/2026-09-07-s19.md`.
> 현황 `PROJECT_STATE.md`, 지도 `핵심두뇌_MASTER.md`.

## 지금까지 (핵심만)

- **고친 것**: veo-platform 의 SEO 정기 재진단이 **하루에 두 번** 돌던 결함.
  `seo/rescan.py` 가 도는 날은 KST 로 고르면서 멱등키 날짜만 UTC 로 적어, **09:00 KST
  (=00:00 UTC)** 경계에서 한국의 하루가 열쇠 둘로 갈렸다. 사장님 캡처의 00:0x·09:0x 두 줄이 그것.
  + 진단 이력 **실행자 칸에 「자동」** 표기(근거는 스케줄 멱등키 하나뿐 — 없으면 「기록 없음」 그대로).
- **어디에**: 저장소 `recon9973-lang/veo-platform`(이 저장소 아님) ·
  가지 `claude/auto-diagnosis-schedule-check-vhmz2j` · 커밋 **`2a19042a`**(5건) · 판 **0.3.541** · **미배포 — 판을 0.3.543 으로 물려야 한다**
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
- **판이 또 부딪혀 0.3.541 로 물렸다** — 다른 방(ANSEO 판 8~13)이 **같은 0.3.540** 을 먼저
  main 에 넣었다(`9436a6cb`, 2026-09-08 새벽). 앞질러 잡아 둔 번호였는데 방끼리 말을 못 하니
  닿기 전에 집혔다. 리베이스(충돌 넷: 변경이력 · 대장 머리말 · 대기 표 둘) 뒤
  `make bump-version TO=0.3.541`. 대기 표의 **그 방 0.3.540 줄은 그대로 뒀다** — main 엔
  들어갔지만 실측 도장은 그 방 몫이다.
- **검증**: 나갈 그 커밋 **`2a19042a` 에서 preflight 전체 초록** [2026-09-08 02:0x KST] —
  ci-local **7,182** · pnpm -r test **2,371** · test-db · typecheck · lint · build · smoke ·
  계약 · 대소문자 · 충돌 표시 0 · 미배포 5 커밋 · 판 0.3.541 > main 0.3.540.
  **부분 검증인 커밋은 없다.** 새 시험 11건. 마이그레이션 없음. 잰 값 무변경.
  (CI 예산 상한 2회 중 **1회 남음**.)
- **`make deploy` 가 처음으로 돌았고, 마지막 한 걸음에서 거절됐다**(2026-09-08 16:0x KST).
  preflight 초록 → 채점 자리 → **CI 통과(실행 34198340336)** → `main` 넣기
  `! [rejected] (non-fast-forward)`. **코드는 문제 없다** — 나갈 그 나무에서 CI 가 초록이었다.
  막힌 것은 그 12분 사이에 main 이 움직였다는 것 하나다.
  - **내 잘못 둘**: 긴 작업을 걸어 놓고 **중간에 main 을 다시 안 봤다** · 다른 방이 방금
    올린 채점 자리(`002f1b45`)를 **덮어썼다**(그 방은 다시 올려야 한다).
  - **main 은 이제 `7e12c2e3` · 판 0.3.542** — 입지 방이 물리면서 **0.3.541 까지 가져갔다**.
    오늘 아홉 번째 판 충돌.
  - 다시 나가려면 **리베이스 → `make bump-version TO=0.3.543` → preflight 재실행 →
    `VEO_DEPLOY_ORDER=... make deploy`**. 점검이 「오늘(KST) CI 상한을 다 썼다」고 세웠으므로
    한 번 더 쓰는 판단이 필요하다.
  - **배울 것: 긴 작업은 시작 직전과 직후에 재야 한다.** 12분이면 이 저장소에서 main 이
    두 번 움직인다 — 오늘 그 12분 안에 다른 방이 배포 한 판을 통째로 끝냈다.
- **지금 채점 자리는 내 것(`2a19042a`)이 잡고 있다** — 다른 방이 덮어써도 정상이다.
- **판 번호는 앞질러 잡아도 소용없다** — 오늘 여덟 번 부딪혔다(0.3.531~0.3.536 · 0.3.540 두 번).
  방끼리 말을 못 하니 앞질러 잡아도 안 닿는다. **번호는 main 에 먼저 닿는 쪽이 갖는다.**
  대신 물러나는 값이 싸다 — 관문이 「내 판 > main 판」만 보므로 판 물림 하나와 문서 넷이면 된다.

## 바로 이어갈 작업

1. **배포 — 사장님 지시 «배포 대기하고 다른 방이 배포하면 같이 배포에 참여해»**.
   가지는 초록 상태로 대기하고, **다른 방이 움직이면 붙는다.**
   - 지켜보는 법: `git ls-remote origin refs/heads/main refs/heads/deploy-candidate` 를
     3분마다 재서 **바뀌면** 신호다. 채점 자리가 바뀌면 다른 방이 **시작**한 것이고,
     main 이 바뀌면 다른 방이 **나간** 것이다. (이 세션은 감시를 걸어 뒀다 —
     새 세션이면 다시 걸어야 한다.)
   - 붙는 순서: main 이 움직였으면 **리베이스 → preflight 재실행 → 3단계**.
     채점 자리는 **한 자리뿐**이라 방끼리 겹치면 안 된다 — 다른 방 CI 가 끝난 뒤에 올린다.
   낼 때는 아래 3단계이고, 안 움직였으면 위 초록이 그대로 유효하다.
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
   **판 0.3.541 은 그대로 둔다**(관문은 「내 판 > main 판」만 본다). 다만 다른 방이 0.3.541 을
   먼저 가져갔으면 그때는 물려야 한다 — 오늘 그 일이 두 번 있었다.
3. 배포 뒤 **실측 도장**: `veo.seokorea.org/login` 판 표시·`/api/health`·`/api/queue` 가
   0.3.541 인지 → 대장 §2 머리말·대기 표에서 **0.3.541 줄만** 지우고 HISTORY 제목에 「나감」.
   **그 방 0.3.540 줄은 건드리지 않는다** — 그 도장은 그 방 몫이다.
   **이 방은 그 주소로 못 나간다**(403) — 바깥에서 재야 한다.
4. `docs/DEPLOY-ORDER-LOG.md` 에 오더 줄이 안 남았다(스크립트가 시작조차 못 했다). 배포 뒤 채운다.
5. **별도 판 몫** — 키워드 추이 기간을 한국 날짜로(`keywords/service.py` `_collect_trends`).
   0.3.541 에 안 섞은 까닭은 위에 적었다. 고칠 때 **바뀐 값이 어디까지 움직이는지 먼저 재서 적을 것.**

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
  사장님이 전달자. **앞질러 잡는 것은 안 통한다는 것이 오늘 두 번 확인됐다**(0.3.540 을
  ANSEO 방이 먼저 가져갔다) — 번호는 main 에 먼저 닿는 쪽이 갖는다. 알릴 것은
  「이 방이 0.3.541 로 대기 중」 하나이고, 물러나는 값은 싸다(판 물림 + 문서 넷).

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
