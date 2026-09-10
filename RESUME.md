# RESUME — 다음 세션 이어가기 (2026-09-09 16:0x KST · s21 마감 · 진단 오진 방)

> 새 세션은 이 파일을 **먼저** 읽는다. 상세는 `docs/session-logs/2026-09-09-s21.md`.
> 현황 `PROJECT_STATE.md`, 지도 `핵심두뇌_MASTER.md`.

## 지금까지 (핵심만)

사장님이 캡처 한 장을 주셨다 — 「HTTP 상태 코드가 정상(2xx)인가 · **실패 · BLOCKER** ·
`http://www.venomad.com/`」. *"다른 AI 는 정상이라는데 진짜가 뭔지 검토."*

**사이트는 멀쩡했다.** 네이버 77건·구글 모두 `https://www.venomad.com/` 로 색인돼 있고,
진단서 자신도 103개 중 102개가 정상이라고 적었다. **진짜 결함은 진단기 쪽 셋**이었고,
전부 고쳐 `veo-platform` 가지 `claude/diagnostic-abnormal-review-hbskaa` 에 커밋 5건이
올라가 있다. **`make preflight` 초록 — 「준비됨」.**

```
e05dea5  인증서 만료일을 한국 경유 수집에서도 잰다
cc7e3ac  진입 주소를 평문에서 https 로 올린다 — 강하의 거울상
d64b573  2xx 인 못 읽은 응답을 「2xx 가 아니다」로 적지 않는다   ← 이번 오진의 원인
b8624aa  막히는 사이트의 보고서를 끝에서 끝까지 잰다 (시험)
7b85336  https 승격 문턱을 조인다 — 제목·설명이 둘 다 있을 때만 (사장님 오더)
```

핵심은 셋째다. `_status_ok` 가 `site.unreadable` 을 **상태 무관하게** 실패로 더해,
200 으로 답한 762바이트 차단 페이지를 「2xx 가 아닌 상태 코드」로 적었다. 그래서 **같은
관측이 한 화면에 두 번, 서로 반대로** 나갔다 — 수집 고지는 「사이트의 결함이 아니라 우리
수집의 상태입니다」, 이슈는 「BLOCKER · 검색 유입이 사라집니다」.

대장 `docs/WORKLIST.md` 대기 표에 **판 28**(번호 없음 — 나갈 때 정한다)로 올렸고,
오류 대장 `docs/CORRECTIONS.md` **192** 에 내가 세 번 틀린 것을 적었다.

## 배포 — **나갔다** (사장님 승인 2026-09-09 «배포 승인»)

이 방이 `make deploy` 를 돌린 것이 아니다. **다른 방(`work/shareboard-tune`)이 이 가지를
자기 판에 합쳐 함께 내보냈다.** 이 방은 나중에 그 사실을 확인만 했다.

```
[실측 2026-09-09 · gh]
  내 커밋 5건        전부 origin/main 의 조상   (merge-base --is-ancestor 로 5/5)
  main 끝 커밋       9d29ad5793b6…  판 0.3.557
  채점받은 커밋      9d29ad5793b6…  CI success · 15:29 KST
                     → 채점한 커밋과 나간 커밋이 같다(오류 135 가 막으려던 그 자리)
```

**`make deploy` 를 다시 돌릴 일이 없다** — 가지가 main 보다 앞선 커밋이 **0건**이다.

## 바로 이어갈 작업

1. **도는 판 실측** — 배포는 나갔는데 **Railway·Vercel 이 실제로 0.3.557 을 서비스하는지는
   이 방에서 못 쟀다**(워크플로 띄우기가 403 · `actions:write` 없음). 재는 길 둘 —
   ```
   워크플로 「도는 판 확인」(workflow_dispatch) 를 사장님이 실행
   또는 콘솔 화면 하단의 판 표시를 눈으로 확인
   ```
2. **venomad 재진단 한 번** — 0.3.557 이 도는 것이 확인되면 진단을 다시 돌려 두 줄을 본다.
   ```
   status_ok                     실패·BLOCKER  →  통과
   certificate_not_expiring      진단 못 함    →  「만료까지 N일 남았습니다」
   수집 고지                      그대로(정확함)
   ```
3. **대장 대기 표 정리** — 위 둘이 확인되면 `docs/WORKLIST.md` 배포 대기 목록에서
   **이 방 줄만** 지운다(「진단 이상값 정리」). **다른 방 줄은 건드리지 않는다.**
   지금 대기 표는 다른 방이 다섯 묶음을 0.3.557 한 판으로 정리해 둔 상태다.

## 대기/차단

- **`gh` 는 방마다 다시 깔아야 한다** — `apt-get install -y gh`(우분투 universe, 2.45.0).
  릴리스 tarball 은 못 받는다: `cli/cli` 가 이 방의 GitHub 범위 밖이라 API 가 거절한다.
  `GH_TOKEN` 은 이미 환경에 있고 붙어 있는 저장소에는 잘 닿는다.
- **이 방의 `gh` 로 못 하는 것 둘** — GraphQL(`gh workflow run`)과
  workflow_dispatch(`actions:write`)가 **403** 이다. REST 조회는 된다.
- **사장님 몫 — 사이트 설정.** `http://www.venomad.com/` 80포트가 **403** 이다.
  **301 to https** 로 바꾸셔야 명함·인쇄물·옛 링크 유입과 그 신뢰도가 살아난다.
  `www` 없는 주소도 함께 점검(PSI 가 아예 처리를 못 했다). 코드로 못 고친다.
- **CI 를 필수 검사로**(s19 부터 남은 것) — `Settings → Branches → main →
  Require status checks → CI`. 이게 없어 빨간불 PR 이 main 에 들어온 적이 있다.

## 주의·제약

- **veo-platform 개발 환경 세우기**(컨테이너는 매번 초기화된다):
  ```
  PYTHON=/usr/bin/python3.12 make setup
  pnpm install --frozen-lockfile
  service postgresql start
  su postgres -c "psql -c \"CREATE ROLE root LOGIN SUPERUSER PASSWORD 'veo'\""
  PGPASSWORD=veo make db-test-create
  PGPASSWORD=veo VEO_TEST_DATABASE_URL="postgresql+psycopg://root:veo@localhost:5432/veo_test" make test-db
  ```
  [실측 2026-09-09] 이 방에서 전부 돌았다 — `ci-local` 7,276 · DB 1,242 · 웹 2,534.
- **이 방은 실서비스를 못 잰다** — `venomad.com`·Railway·`pagespeed.web.dev`·`archive.org`
  전부 egress 403. `www.googleapis.com` 계열만 열려 있다(PSI 공용 몫은 하루 한도 소진).
- **못 재는 자리에서는 가설을 가설이라고만 말한다.** 이번에 세 번 단언하고 세 번 갈렸고
  **발견자가 세 번 다 사장님**이었다(오류 대장 192).
- 이 가지 외로 푸시 금지. 배포는 **`make deploy` 만**, 오더 없이 밀지 않는다.
- 대장·변경이력에 「민다·푸시」 금지(`two-words-only` 관문) — 「커밋」·「배포」 두 낱말만.
- 커밋 트레일러: `Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>` +
  `Claude-Session: https://claude.ai/code/session_01RkCSy2RcrHt6i2FyRmDyYs`.
  모델 ID 는 트레일러에만.
- 사장님께는 「커밋」·「배포」 두 낱말만. 못 잰 값 «—», 지어낸 수치 금지, 의료광고법 준수.

## 참고

- veo-platform 은 `add_repo` 로 붙인다(owner `recon9973-lang`) → `/home/user/veo-platform`.
- 대장은 `docs/WORKLIST.md`(615줄 규격 · 1,200줄 상한). 날짜별 기록은 `WORKLIST-HISTORY.md`
  이고 **평소에 열지 않는다.**
- 판 번호는 **나갈 때** `claim_version.py` 가 물린다. 미리 잡지 않는다.
