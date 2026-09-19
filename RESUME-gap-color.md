# RESUME (경고색 방) — **둘 다 나갔다** (0.3.612 · 0.3.617 · 2026-09-19 11:44 KST 실측)

<!-- 가지: claude/compassionate-newton-kyz1sm -->
<!-- 고친 것은 **ANSEO(veo-platform)** 다. 이 저장소(베놈 마케팅 사이트)에는 코드가 없다 -->

> 상세는 `docs/session-logs/2026-09-19-s01-gap-color.md`.
> 현황 `PROJECT_STATE.md` · 지도 `핵심두뇌_MASTER.md`.
> ANSEO 쪽 현황은 `veo-platform` 의 `docs/STATE.md` · 대장은 `docs/WORKLIST.md`.

## 지금까지 (핵심만)

사장님 오더 둘을 끝내 **둘 다 내보냈다.**

1. **그래프의 「아직 못 채운 쪽」을 한 색으로**(0.3.612) — 부족분 토큰
   `--veo-gap-fg`·`--veo-gap-step-1..4` 를 두고 SEO·GEO·AEO 의 그림 **열 자리**를 그 한 색으로
   모았다. 못 잰 것은 안 칠한다(ADR 0002). 관문 `shortfall-is-one-colour.test.ts`(16건) 신설.
2. **배포 담당을 「만든 방」으로**(0.3.617) — 사장님 «만든 방이 바로 배포해». 네 번째 바뀜이라
   갈린 확정에 차례를 다 적었고, 부딪힘을 피하는 법 셋과 클라우드 방에서 `[5/5]` 가 늘
   실패하는 사정까지 §2 에 넣었다.

```
[실측 2026-09-19 11:44 KST · 러너 「도는 판 확인」 실행 35416544838]
  웹 · 진단 서버 · 워커 1대  셋 다 0.3.617 (뒤처진 워커 0)
  발행본  GEO 1.10.0 · SEO 1.15.0
```

커밋(veo-platform · 이 가지): `712e7944` · `8b2a132a` · `9d6231e4` · `afe883e2` · `6c33b521`.
대기 표는 비웠다(0.3.616·0.3.617 둘 다 도는 것 확인).

## 바로 이어갈 작업

**이 방에 남은 것은 없다.** 아래는 이 방이 **찾아서 적어만 둔 것**이라 다른 방이 가져가도
된다 — 둘 다 `veo-platform` 대장 §4-A 에 한 줄씩 있다.

1. **배포 전 점검 ⑤(지출 한도)가 클라우드 작업 방에서는 늘 「못 쟀다」로 지나간다.**
   ⑤ 는 `gh` 로 묻는데 이 방엔 `gh` 가 없고 `scripts/preflight.sh` 가 `scripts/gh_fallback.sh` 를
   안 부른다. 부르게 하면 되는데 **흉내를 두 군데 넓혀야 한다** — ⑤ 는 `--repo` 없이
   `gh run list` 를 부르고(흉내는 `--repo` 없으면 2 로 거절), `--jq` 가 아니라 `-q` 를 쓴다
   (흉내가 `-q` 를 버린다). `tests/release/` 에 그 두 모양을 먼저 적는다.
   → 2026-09-19 에 이것 때문에 점검 15분을 다 쓰고 CI 에서야 예산 막힘이 드러났다.
2. **판 물림이 「이미 나간 항목」을 못 알아보는 구멍.** `claim_version._refuse_to_relabel` 이
   내 맨 위 항목을 `origin/main` 의 **지금** 맨 위 항목과 견준다 — 가지를 딴 뒤 main 이 한 판
   더 나가면 관문이 지나가고 **이미 나간 항목에 새 번호가 달린다**(실제로 0.3.614 → 0.3.616).
   견줄 자리를 **merge-base 이후 main 이 낸 항목 전부**로 넓히면 닫힌다.
   `test_claim_version.py` 에 이 경우를 먼저 적는다.

## 대기/차단

- 없다. (GitHub Actions 예산은 **사장님이 2026-09-19 에 올려 주셨다** — 풀린 것 확인함.)

## 주의·제약

- **여기는 ANSEO 가 아니다.** 진단 화면 이야기가 나오면 `veo-platform` 을 `add_repo` 로 붙인다.
  이 저장소를 고쳐서 ANSEO 가 바뀌는 일은 없다.
- **배포는 만든 방이 바로 한다**(사장님 2026-09-19). `make deploy` 만 쓰고, 주문 없이 안 민다.
- 이 방 컨테이너는 **운영 주소로 못 나간다(403)**. `[5/5]` 는 늘 「못 쟀다」로 끝난다 —
  배포 실패가 아니다. 실제로 도는 판은 러너 `rollout-check.yml` 을
  `mcp__github__actions_run_trigger` 로 불러 잰다.
- 배포 전 점검을 돌리려면 이 컨테이너에서: PostgreSQL 켜기(`service postgresql start`) ·
  `PGHOST=/var/run/postgresql PGUSER=root`
  `VEO_TEST_DATABASE_URL="postgresql+psycopg:///veo_test?host=/var/run/postgresql"` ·
  venv 는 **Python 3.12** 로 만든다(3.11 은 `veo-api` 가 거절한다).
- 커밋·PR·코드에 모델 ID 를 넣지 않는다. 지어낸 수치 금지, 못 잰 값은 «—».

## 참고

- 현황 `PROJECT_STATE.md` · 지도 `핵심두뇌_MASTER.md` · 세션 기록
  `docs/session-logs/2026-09-19-s01-gap-color.md`.
