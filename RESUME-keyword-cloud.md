# RESUME (키워드 구름 방) — 2026-09-15 s26 마감

> **이 저장소에 인계가 여럿이다 — 이 방 것은 이 파일이다.**
> 루트 `RESUME.md`(진단 오진 방) · `RESUME-aeo-grand.md` · `RESUME-anseo-review.md` ·
> `RESUME-ring-loader.md` · `RESUME-motion-port.md` 는 **다른 방** 것이다. 건드리지 않는다.
> 상세는 `docs/session-logs/2026-09-15-s26-keyword-cloud.md`.

## 지금까지 (핵심만)

사장님이 마인드맵·워드클라우드 그림 다섯 장을 주시며 «자리를 찾고 브레인스토밍해 보고»
하셨다. 자리 **열한 곳**을 세워 여섯을 권하고 다섯은 왜 아닌지까지 적었다
(`docs/ANSEO-키워드맵-클라우드-배치제안.md` · 시안 https://claude.ai/artifact/47rdjeSKYLzNi4m5dWF8kR).
그중 **1·2·3번을 만들어 두 판으로 배포했다.**

```
0.3.583  main e18d3fea   연관 키워드 「목록/그림」 + AEO 언급 버블 (BubbleCloud)
0.3.587  main d20925b5   인용 출처 트리맵 (Treemap) + 나간 판 번호 기록 고침
                         ↑ 다른 방 셋(업종 자료화·콘솔 좁은 폭·판 물리기)도 함께 실림
[실측 2026-09-16] UI 263 · 웹 2,647 · ci-local 초록 · tsc 0 · eslint 0 · next build 통과
```

**축이 없는 그림의 규칙**이 부품으로 굳었다(`packages/ui/src/components/figure`) —
읽는 법 넉 줄(크기·색·자리·못 잰 값)이 **타입 필수**이고 관문이 화면에 그려지는지 본다.
못 잰 값은 원·칸이 되지 않고 곁의 칩 줄로 간다. 좁아서 못 그릴 칸은 **묶거나 밖으로**
낸다 — 최소 크기를 억지로 주지 않는다(그 순간 넓이가 값을 거짓말한다).

## 바로 이어갈 작업

1. ~~도는 판 확인~~ — **끝났다. 두 판 다 운영에 떠 있다.**
   [실측 2026-09-16 11:44 KST · **다른 방**이 쟀다 · 대장 §2 머리말] 진단 서버 **0.3.588**
   · 웹 **0.3.588** · 5xx 0. 0.3.588 을 적어 넣은 커밋(`1d09f22a`)이 이 방의 트리맵
   커밋 `d20925b5` 를 품는다(`merge-base --is-ancestor` 로 확인). **이 방이 직접 잰 것은
   아니다** — 운영 주소는 여전히 egress 403 이다.
2. **화면에서 눈으로 본다** — 실제 자료로 트리맵의 칸이 읽히는지, 「기타 N곳」이 뜻대로
   묶이는지 사장님 확인을 받는다. 연관 키워드 「그림」 탭도 같이.
3. (이어서 만들 것) 제안서 **4번 개체 지도**(GEO 탭 · JSON-LD 노드-간선) — ANSEO 고유.
   **선행 하나**: 지금 채점은 개수만 싣는다. 노드·간선 목록을 싣는 창구가 필요하다
   (`geo/collectors/entity_clarity.py` 의 `observed`).
4. 그다음 **5번 리포트 트리맵**(공유본 종이 톤) — 3번 부품을 그대로 쓴다.
5. **대기 표에 이 방 한 줄이 쌓여 있다**(번호 미정 1건 · 문서만) — 배포 오더 대장에
   0.3.587 줄 되살리기. 가지 `claude/keyword-bubble-cloud` 2커밋
   (`fc2e1af3`·`1ce0e50e`). **다음 배포 오더가 있을 때 같이 나간다** — 이것만으로
   배포를 돌리지 않는다.

## 대기/차단

- **모션 방은 다 나갔다** — 0.3.580(넷) · 0.3.586(둘). 대기 표에서 뺐다.
- **이 방은 실서비스를 못 잰다** — `veo.seokorea.org`·Railway egress 403.
  도는 판은 **다른 방의 실측**을 대장 §2 머리말에서 읽는다(지어내지 않는다).
- **배포는 오더 대장 줄을 판이 나간 뒤에 적는다** — 그 줄이 나무에만 남고 커밋이
  안 되면 기록이 빈다. 배포가 끝나면 `git status` 로 `DEPLOY-ORDER-LOG.md` 를 본다.
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
