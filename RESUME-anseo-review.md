# RESUME (검수 방 · ANSEO 96항목) — 2026-09-14 12:0x KST

> **이 저장소에 인계가 여럿이다 — 이 방 것은 이 파일이다.**
> 루트 `RESUME.md`(진단 오진 방) · `RESUME-aeo-grand.md` · `RESUME-ring-loader.md` 는 **다른 방** 것이다.
> 상세는 `docs/session-logs/2026-09-14-s23-anseo-review.md`. 현황 `PROJECT_STATE.md`, 지도 `핵심두뇌_MASTER.md`.

## 지금까지 (핵심만)

사장님이 ANSEO 96항목(SEO 59 · GEO 37)을 **수집(실제)-진단(규정 적합)-제안(효과)** 세 축으로
하나씩 검수하라고 하셨다. 검수에서 나온 결함과, 바깥 문서를 따로 조사해 나온 결함을 합쳐
**일곱 판**을 만들었고 **0.3.575 로 나갔다**(2026-09-14 11:5x KST · CI 초록 · main `81ee22a5`).

```
f96d4c9   SEO·GEO 가 같은 페이지를 반대로 읽던 두 자리 (noindex · +82 전화)
3b6f7c91  외부 근거 대장(기한 지나면 시험 실패) + GEO 1.8.0 초안
3c878ac9  크롤러 로스터 네 갈래 — 막아도 오는 대리자는 감점 안 함 [실측 48.54→51.51]
759cd3c7  llms.txt 정보 항목 + 추출성 문구 정정(구글이 부인한 전제였다)
57bddf69  GEO 1.8.0 발행 — 37→39항목 · 점수 0점 이동
f02356a2  대장 §2 머리말이 이미 나간 0.3.574 를 「미배포」라고 적고 있었다
62c13635  0.3.575 나갔다는 도장
```

가지 `claude/same-page-same-verdict`(veo-platform)는 **main 과 같다** — `make deploy` 다시 돌릴 일 없다.

## 바로 이어갈 작업

> ①은 끝났다. **②부터 시작한다.**

1. ~~워커가 0.3.575 인지 확인~~ → **끝남.** [실측 2026-09-14 · 사장님 Railway 콘솔 캡처]
   `veo-platform`(진단 서버)·`veo-worker`(진단을 실제로 돌리는 쪽) **둘 다 0.3.575 ACTIVE ·
   Deployment successful**. 이번에 나간 것(GEO 1.8.0 39항목 · 크롤러 로스터 · SEO·GEO 같은
   판정)이 실제 진단에 들어간다. **이 방은 스스로 못 잰다**(egress 403) — 다음에도 콘솔이나
   캡처로만 확인된다.

2. **배포 [5/5] 가 조용히 서는 것 고치기** — `scripts/deploy.sh` 가 `set -euo pipefail` 아래에서
   `curl` 22 를 받으면 **「못 쟀다」를 한 줄도 안 적고 죽는다** [실측 2026-09-14]. 배포는 이미
   나간 뒤라 손해는 없지만 로그만 보면 실패로 읽힌다. 대장의 「못 재는 것은 못 잼이라고
   적는다」와 어긋난다. `|| true` 로 감싸고 「못 쟀습니다」를 찍게 한다.
3. **검수 보고서 「권고 — 남은 것」 표를 위에서부터** (`docs/2026-09-13-ANSEO-96항목-수집진단제안-검수.md`)
   — 수집기 셋(검증 대상 없음 → 해당 없음 · NAP 주소 대조 · 이력 연결), 명세 개정 셋
   (GEO 접근 `is_gate` · title 길이 · 제목 중복 이중 감점), 조치 문구 하나.

## 대기/차단 — 사장님 몫

- **렌더러를 켤지** — Railway **`veo-worker`** 서비스 → Variables → `VEO_RENDERER_ENABLED=true`.
  (`veo-platform` 이 아니다.) 크롬은 이미 이미지에 실려 있다.
  **순수한 이득이 아니다** — 켜면 `seo.content.js_render_parity` 가 관문 항목이라 점수에
  곱해지고, **자바스크립트로 본문을 그리는 거래처는 점수가 내려간다.** 없던 결함이 생기는
  것이 아니라 못 보던 것이 보이는 것이지만, 거래처 화면에는 「점수가 떨어졌다」로 보인다.
  사전 대조(`apps/api/scripts/compare_lab_measurements.py`)는 **이 컨테이너에서 못 돌린다**
  (프록시가 대상 사이트를 막는다 — 스크립트 자신이 그렇게 적어 두었다).
- **배포 상한 재설정** — 상한 기간(2026-09-01)이 지나 `deploy.sh` 가 더 이상 세지 않는다.
  계속 제한할지 정하셔야 한다.

## 주의·제약

- **veo-platform 개발 환경 세우기**(컨테이너는 매 세션 초기화된다):
  ```
  PYTHON=/usr/bin/python3.12 make setup
  pnpm install --frozen-lockfile
  apt-get install -y gh
  service postgresql start
  su postgres -c "psql -c \"CREATE ROLE root LOGIN SUPERUSER PASSWORD 'veo'\""
  PGPASSWORD=veo make db-test-create
  ```
  관문은 `VEO_TEST_DATABASE_URL="postgresql+psycopg://root:veo@localhost:5432/veo_test" \
  PGPASSWORD=veo bash scripts/preflight.sh`.
  [실측 2026-09-14] 이 방에서 전부 돌았다 — ci-local 7,542 · 웹 2,574.
- **배포는 `make deploy` 만.** `VEO_DEPLOY_ORDER` 에 **사장님 원문을 그대로** 넣어야 돈다 —
  요약·짐작은 안 된다. 「진행해」류는 배포 오더가 아니다(스크립트가 그렇게 적어 두었다).
  **초록불이어도 주문 없이 밀지 않는다.**
- **이 방은 실서비스를 못 잰다** — `veo.seokorea.org`·Railway 전부 egress 403.
  못 잰 값은 `0` 이 아니라 `—`. 지어낸 수치 금지.
- 가지: veo-platform `claude/same-page-same-verdict` · desktop-tutorial `claude/friendly-mendel-mlvpsa`.
  **다른 가지로 커밋 금지.**
- 대장·변경이력에 「민다·푸시」 금지(`two-words-only` 관문) — 「커밋」·「배포」 두 낱말만.
- **다른 방 줄은 건드리지 않는다** — `STATE.md`·`WORKLIST.md` 에서 충돌이 나면 저쪽 것을
  살리고 내 줄만 넣는다. 이번 세션에 두 번 그랬다.
- 커밋 트레일러: `Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>` +
  `Claude-Session: https://claude.ai/code/session_01JLjPMtA7oQ2LnbA8hrS79J`.
  **커밋·PR·코드에 모델 ID 를 넣지 않는다.** 의료광고법 준수.

## 참고

- veo-platform 은 `add_repo`(owner `recon9973-lang`) → `/home/user/veo-platform`.
- 검수 보고서 `docs/2026-09-13-ANSEO-96항목-수집진단제안-검수.md`
- 아티팩트 https://claude.ai/code/artifact/ab36d226-a95b-4ab4-8fb1-2a9f62753fee (v3)
- 명세 판 이력: `packages/scoring-specs/specs/veo.geo.readiness/` · 근거 대장은 `basis/external-basis.yaml`
- 판 번호는 **나갈 때** `claim_version.py` 가 물린다. 미리 잡지 않는다.
