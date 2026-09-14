# RESUME (검수 방 · ANSEO 96항목) — 2026-09-14 13:5x KST

> **이 저장소에 인계가 여럿이다 — 이 방 것은 이 파일이다.**
> 루트 `RESUME.md`(진단 오진 방) · `RESUME-aeo-grand.md` · `RESUME-ring-loader.md` 는 **다른 방** 것이다.
> 상세는 `docs/session-logs/2026-09-14-s24-anseo-review.md`. 현황 `PROJECT_STATE.md`, 지도 `핵심두뇌_MASTER.md`.

## 지금까지 (핵심만)

96항목 검수의 「권고 — 남은 것」 표를 **끝까지** 내려갔다. 두 판이 나갔다.

```
0.3.576   main 9c35d958   수집기 넷 + 배포 도구 둘
0.3.577   main 1a801344   명세 개정 셋 + 작업 단계 표
```

가지 `claude/same-page-same-verdict` 는 **main 과 같다**(미배포 0) — `make deploy` 다시
돌릴 일 없다. 표에 남은 것은 **사장님 몫 둘**뿐이다(아래 「대기/차단」).

큰 것 셋:

- **GEO 1.9.0** — 붉은 「노출 차단」 띠와 점수가 반대로 말하던 것을 끝냈다(사장님 «ⓑ로 가자»).
  [실측] 멀쩡한 사이트 **100.000 → 100.000** · noindex **95.062 → 0.000**
- **SEO 1.13.0** — 제목 중복 이중 감점. [실측] 겹침 53.96 → **64.06** · 안 겹침 그대로
- **제목 길이를 폭으로** — SEO 60 · GEO 80 으로 갈려 있던 규칙을 `veo/common/text_width.py` 하나로

## 바로 이어갈 작업

1. **0.3.577 이 실제로 도는지 확인** — 이 방은 못 잰다(운영 주소 egress 403).
   Railway 콘솔에서 **`veo-platform`·`veo-worker` 둘 다 0.3.577 ACTIVE** 인지 본다.
   워커만 옛 판이면 나간 것이 화면에만 있고 진단에는 안 먹는다.
   **GEO 1.9.0 은 거래처 숫자를 크게 움직인다** — 노출이 막힌 거래처 점수가 0 으로 보인다.
2. **조치 문구 — 명세·계약 개정으로 올린다.** 「연결하면 잴 수 있다」가 네이버처럼
   **열쇠를 받아도 못 재는** 자리에도 나간다. 문구가 명세의 `availability` 별로 정해지고
   값이 셋뿐(`CUSTOMER_GRANTED`·`PAID_PROVIDER`·`REFERENCE_ONLY`)이라 그 자리를 가리킬
   이름이 없다. `ProviderState.NOT_AVAILABLE` 이 알고 있지만 `CheckOutcome` 이 안 싣는다.
   **새 `availability` 값**이거나 **`CheckOutcome` 에 한 칸** — 어느 쪽이든 판을 올린다.
3. **서치콘솔을 진단에 배선** — `previous_indexed` 는 그 뒤의 일이다.
   `search_console_payload`·`search_console_for` 가 **자기 모듈 밖에서 불리지 않는다.**
   그래서 `seo.outcome.index_coverage_healthy` 는 지난 수치가 없어서가 아니라 **조회 자체를
   못 해서** 진단 못 함이다. 「이으면 된다」로 적어 두면 다음 사람이 헛일을 한다.

## 대기/차단 — 사장님 몫

- **렌더러를 켤지** — Railway **`veo-worker`** → Variables → `VEO_RENDERER_ENABLED=true`.
  **순수한 이득이 아니다** — 켜면 `seo.content.js_render_parity` 가 SEO 관문 항목이라 점수에
  곱해지고, **자바스크립트로 본문을 그리는 거래처 점수가 내려간다.** 못 보던 것이 보이는
  것이지만 화면에는 「점수가 떨어졌다」로 보인다. 사전 대조 스크립트는 이 컨테이너에서
  못 돌린다(프록시가 대상 사이트를 막는다).
- **배포 상한 재설정** — 상한 기간(2026-09-01)이 지나 `deploy.sh` 가 더 이상 세지 않는다.
  배포 관문 ⑤ 는 여전히 「오늘 2건 — 상한을 다 썼다」고 말하지만 **막지는 않는다.**
  계속 제한할지 정하셔야 한다.

## 주의·제약

- **개발 환경 세우기**(컨테이너는 매 세션 초기화된다):
  ```
  PYTHON=/usr/bin/python3.12 make setup
  pnpm install --frozen-lockfile        # ← cd 가 백그라운드 첫 작업에만 걸린다, 주의
  service postgresql start
  su postgres -c "psql -c \"CREATE ROLE root LOGIN SUPERUSER PASSWORD 'veo'\""
  PGPASSWORD=veo make db-test-create
  ```
  관문은 `VEO_TEST_DATABASE_URL="postgresql+psycopg://root:veo@localhost:5432/veo_test" \
  PGPASSWORD=veo bash scripts/preflight.sh`.
  [실측 2026-09-14] 이 방에서 전부 돌았다 — ci-local 7,600 · 웹 2,578.
- **`make test-api` 와 `make ci-local` 은 범위가 다르다.** 단계 표 누락은 `ci-local` 에서만
  걸렸다 — 커밋 전에 좁은 쪽만 돌리면 배포 관문에서 걸린다.
- **`ci-local` 을 직접 돌릴 때 DB 주소를 줘야 한다** — 안 주면 오류 1,240건이 난다(관문은 준다).
- **판 목록은 `available_specs()` 로 본다.** `ls | tail` 은 사전순이라 `1.10.0` 이 `1.9.2` 보다
  앞에 온다 — 이번에 그것에 속아 **이미 발행된 1.10.0 을 덮어썼다**(되돌렸다). 발행본은
  불변이다(ADR 0012).
- **판 번호는 나갈 때 물린다.** 선 배포가 실패하면 `__init__.py`·`openapi.json`·
  `changelog.ts` 에 새 판을 적어 놓고 죽는다 — `git add -A` 로 쓸어담지 말고 되돌린다.
- **배포는 `make deploy` 만.** `VEO_DEPLOY_ORDER` 에 **사장님 원문 그대로.** 「진행해」류는
  배포 오더가 아니다. 초록불이어도 주문 없이 밀지 않는다.
- **이 방은 실서비스를 못 잰다** — `veo.seokorea.org`·Railway 전부 egress 403.
  못 잰 값은 `0` 이 아니라 `—`. 지어낸 수치 금지.
- 가지: veo-platform `claude/same-page-same-verdict` · desktop-tutorial `claude/friendly-mendel-mlvpsa`.
  **다른 가지로 커밋 금지.**
- 대장·변경이력에 「민다·푸시」 금지(`two-words-only` 관문) — 「커밋」·「배포」 두 낱말만.
- **다른 방 줄은 건드리지 않는다** — `STATE.md`·`WORKLIST.md` 충돌은 저쪽을 살리고 내 줄만.
- 커밋 트레일러: `Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>` +
  `Claude-Session: https://claude.ai/code/session_01JLjPMtA7oQ2LnbA8hrS79J`.
  **커밋·PR·코드에 모델 ID 를 넣지 않는다.** 의료광고법 준수.

## 참고

- veo-platform 은 `add_repo`(owner `recon9973-lang`) → `/home/user/veo-platform`.
- 검수 보고서 `docs/2026-09-13-ANSEO-96항목-수집진단제안-검수.md` — 표의 남은 줄이 곧 할 일.
- 이번 세션에 세운 관문 넷: `test_deploy_says_what_it_could_not_measure.py` ·
  `test_one_ruler_measures_the_title.py` · `test_one_defect_is_charged_once.py` ·
  `test_the_gate_and_the_band_agree.py`.
- 명세 판 이력: `packages/scoring-specs/specs/veo.{seo,geo}.readiness/` ·
  근거 대장은 `basis/external-basis.yaml`.
