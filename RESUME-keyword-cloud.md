# RESUME (키워드 구름 방) — 2026-09-15 s26 마감

> **이 저장소에 인계가 여럿이다 — 이 방 것은 이 파일이다.**
> 루트 `RESUME.md`(진단 오진 방) · `RESUME-aeo-grand.md` · `RESUME-anseo-review.md` ·
> `RESUME-ring-loader.md` · `RESUME-motion-port.md` 는 **다른 방** 것이다. 건드리지 않는다.
> 상세는 `docs/session-logs/2026-09-15-s26-keyword-cloud.md`.

## 지금까지 (핵심만)

사장님이 마인드맵·워드클라우드 그림 다섯 장을 주시며 «ANSEO 안에 넣을 자리를 찾고
브레인스토밍해 보고» 하셨다. 자리 **열한 곳**을 전수로 세워 여섯을 권하고 다섯은 왜
아닌지까지 적었다(`docs/ANSEO-키워드맵-클라우드-배치제안.md` · 시안 아티팩트
https://claude.ai/artifact/47rdjeSKYLzNi4m5dWF8kR). 그중 **1·2번을 만들어 배포했다.**

```
veo-platform  main e18d3fea  ·  판 0.3.583  ·  CI 초록  [실측 2026-09-15]
  BubbleCloud 부품 + 연관 키워드 「목록/그림」(?shape=cloud · 기본 목록)
             + AEO 한눈에 언급 버블(순위 막대 위)
  UI 387 · 웹 2,634 · ci-local 7,657 · tsc 0 · eslint 0 · next build 통과
```

## 바로 이어갈 작업

1. **변경이력 번호 고침 — 정해졌다(2026-09-15 사장님 «1번으로 해줘»): 다음 배포에 함께 태운다.**
   할 일은 **합쳐서 내보내는 것 하나**다. 다음에 내보내는 방이
   `claude/keyword-bubble-cloud`(커밋 `c4412f87`)를 제 판에 합쳐 함께 낸다 —
   **판을 하나 더 내지 않는다.** 대기 표와 `docs/STATE.md`(veo-platform)에 번호 없이
   한 줄로 올려 두었으므로 인계 없이도 보인다.
   ```
   무엇   변경이력·날짜별 기록·대장·상태를 나간 번호 0.3.583 에 맞춘다. 코드 변경 0
   왜     0.3.583 이 나갈 때 claim_version 이 안 돌았다(오류 215)
   그때까지  화면 판 0.3.582 · API 판 0.3.583 — 기록 결함이고 제품은 정상
   ```

2. **도는 판 확인** — 이 방은 운영 주소에 못 닿는다(egress). 사장님이 보시는 길:
   `curl -s https://veo-platform-production.up.railway.app/api/health` 또는 콘솔 하단 판 표시.
   0.3.583 이면 화면에 그림이 떠 있다.
3. **그림을 실제 화면에서 본다** — 거래처 흐름으로 `/console/keywords?lookup=…&project=…`
   에서 「그림」을 누르고, 거래처 › AEO › 한눈에의 언급 버블을 본다. 원 크기·이름 칸이
   실제 자료에서도 읽히는지 사장님 눈으로 확인받는다.
4. (이어서 만들 것) 제안서의 **3번 인용 출처 트리맵**이 사업 가치가 가장 크다 —
   `Treemap` 부품 하나로 3·5번(리포트 종이 톤)이 함께 선다.

## 대기/차단

- **모션 방 넷(0.3.580)** 이 아직 대기 표에 있다 — 가지 `claude/anseo-motion-port`,
  main 에 없다. 이번 배포에서 사장님 지시로 **뺐다**. 그 방 몫이다.
- **이 방은 실서비스를 못 잰다** — `veo.seokorea.org`·Railway egress 403.
- **컨테이너 PostgreSQL 이 도구 호출 사이에 내려간다.** 관문을 돌릴 땐 배포 명령과
  **같은 호출 안에서** 띄운다(`service postgresql start` → `pg_isready` → `make deploy`).

## 주의·제약

- 가지: veo-platform `claude/keyword-bubble-cloud` · desktop-tutorial
  `claude/awesome-brahmagupta-7mlfxl`. **다른 가지로 커밋 금지.**
- 배포는 **`make deploy` 만.** `VEO_DEPLOY_ORDER` 에 **사장님 원문 그대로**.
  「진행해」류는 배포 오더가 아니다.
- **배포가 [1/4] 이후에 서면 `git add -A` 금지** — `__init__.py`·`openapi.json`·계약에
  적힌 새 판은 내 것이 아니다(오류 215가 그것이다). `git status` 를 눈으로 읽는다.
- 대기 표에 **이미 나간 판 줄을 남기지 않는다** — 판 물리기가 남의 줄에 새 번호를 단다.
- 못 잰 값은 `0` 이 아니라 `—`. 지어낸 수치 금지. 의료광고법 준수.
- 커밋 트레일러: `Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>` +
  `Claude-Session: https://claude.ai/code/session_01Vx22CViT3xbedxgmboTd7i`. 모델 ID 는 트레일러에만.

## 참고

- veo-platform 은 `add_repo`(owner `recon9973-lang`) → `/home/user/veo-platform`.
  환경: `PYTHON=/usr/bin/python3.12 make setup` · `pnpm install --frozen-lockfile` ·
  `service postgresql start` · `PGPASSWORD=veo make db-test-create`.
- 현황 `PROJECT_STATE.md` · 지도 `핵심두뇌_MASTER.md` · veo 쪽 현황은 그 저장소 `docs/STATE.md`.
