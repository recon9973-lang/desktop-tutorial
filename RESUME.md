# RESUME — 다음 세션 이어가기 (2026-09-07 21:0x KST · s19 마감 · 자동 진단 방)

> 새 세션은 이 파일을 **먼저** 읽는다. 상세는 `docs/session-logs/2026-09-07-s19.md`.
> 현황 `PROJECT_STATE.md`, 지도 `핵심두뇌_MASTER.md`.

## 지금까지 (핵심만)

- **나갔다.** veo-platform **v0.3.544** 가 2026-09-08 17:0x KST 에 **main 에 들어갔다**
  (커밋 `8a001cfb` · `git ls-remote` 로 직접 확인). 담긴 것 다섯:
  1. **정기 재진단이 하루 두 번 돌던 결함** — `seo/rescan.py` 가 도는 날은 KST 로 고르면서
     멱등키 날짜만 UTC 로 적어 **09:00 KST(=00:00 UTC)** 경계에서 한국의 하루가 열쇠 둘로
     갈렸다. 사장님 캡처의 00:0x·09:0x 두 줄이 그것. `daily_idempotency_key` 한 곳으로.
  2. **진단 이력 실행자 칸에 「자동」** — 근거는 스케줄 멱등키 하나뿐. 없으면 「기록 없음」 그대로.
  3. **GEO 탭에서도 「자동」** — 한 진단이 SEO·GEO 두 실행으로 저장되는데 동반 GEO 저장만
     작업 식별자를 안 받아 탭마다 다른 말을 했다.
  4. **서버가 여러 대여도 청소가 안 끊긴다** — 같은 열쇠로 동시에 넣으면 진 쪽이 예외로
     죽어 그 판 청소가 통째로 중단됐다. 저장점 안에서 넣고 지면 이긴 쪽을 돌려준다.
  5. 배포 오더 기록(`DEPLOY-ORDER-LOG.md`).
  새 시험 11건 · 마이그레이션 없음 · 잰 값 무변경.
- **아직 못 잰 것 — 실서비스 도달.** `make deploy` 의 [5/5] 가 오류 22 로 끝났다.
  그 단계는 `veo-platform-production.up.railway.app` 의 `/api/health`·`/api/queue` 에 직접
  묻는데 **이 방은 그 주소로 못 나간다**(프록시가 CONNECT 에서 403 · 두 주소 다 확인).
  **배포 실패가 아니라 확인을 못 한 것**이지만, 못 잰 것은 못 잰 것이다.
- **오늘 판이 열 번 부딪혔다** — 0.3.531~0.3.536 · 0.3.540 두 번 · 0.3.541·0.3.542 ·
  0.3.543 두 번. **앞질러 잡는 것은 안 통한다**(방끼리 말을 못 하니 안 닿는다).
  번호는 main 에 먼저 닿는 쪽이 갖고, 물러나는 값은 싸다(판 물림 + 문서 넷).
- **한 번은 내가 남의 것을 덮었다**(2a19042a 가 002f1b45 를) — 12분짜리를 걸어 놓고
  중간에 main 을 안 봤다. 두 번째에는 다른 방이 도는 것을 보고 **배포를 멈췄다가**
  그 방이 나간 뒤에 섰다. 상세는 세션 로그 §2-6·§2-7.

## 바로 이어갈 작업

1. **실측 도장** (제일 먼저) — 바깥에서 이 둘을 재야 한다. **이 방은 못 나간다(403).**
   ```
   https://veo-platform-production.up.railway.app/api/health   → 0.3.544 인가
   https://veo-platform-production.up.railway.app/api/queue    → worker_versions 가 0.3.544 인가
   ```
   **서버와 워커 둘 다** 0.3.544 여야 완전히 나간 것이다 — 다른 방 대장에
   「0.3.540 이 반만 나가 있다 · 워커 ✗」가 있다. 숫자를 받으면:
   - `docs/WORKLIST.md` §2 머리말의 미배포 범위와 「배포 대기」 표에서 **0.3.544 줄만** 지운다
     (둘이 일치해야 `worklist.test.ts` 통과). **다른 방 줄(0.3.541~0.3.543)은 건드리지 않는다.**
   - `docs/WORKLIST-HISTORY.md` 의 0.3.544 절 제목에 「나감」.
2. **별도 판 몫** — 키워드 추이 기간을 한국 날짜로(`keywords/service.py` `_collect_trends`).
   대장 §4-A 에 적어 뒀다. 고칠 때 **바뀐 값이 어디까지 움직이는지 먼저 재서 적을 것.**
3. **구조 문제 정리** — 채점 자리(`deploy-candidate`)가 **하나뿐인데 방마다 따로 돈다.**
   오늘 세 방이 같은 12분 창에서 서로를 밀어냈고, 판 충돌 열 번 · CI 5회를 썼다.
   사장님께 제안할 것을 정리해 두면 좋다(순번 잡는 법 · 방마다 다른 자리 · 판 번호를
   main 에 닿을 때 정하기 등).

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
