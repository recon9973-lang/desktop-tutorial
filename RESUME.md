# RESUME — 다음 세션 이어가기 (2026-09-09 04:40 KST · s22 · 머리 요약 **못 나감**)

> 새 세션은 이 파일을 **먼저** 읽는다. 이 세션 상세는 `docs/session-logs/2026-09-09-s22.md`.

## 지금 상태

- **「입지」 머리 요약이 다 만들어져 있고 CI 를 세 번 통과했다. 그런데 못 나갔다.**
  세 번 다 **CI 통과 뒤 main 에 미는 순간** 물렸다 — ANSEO 방이 채점 20분 안에 계속 민다
  (실측: main 커밋이 15~40분 간격). 사장님 판단 2026-09-09: **「저쪽이 잠잠할 때 다시」.**
- veo-platform 가지 **`claude/anseo-location-v0501` @ `b45dd2c`** 에 밀어 뒀다.
  운영 판은 **0.3.555**(ANSEO 방). 우리 판 번호는 다음 시도 때 어차피 다시 물린다.
- 앞 세션(s21)이 내보낸 것: 0.3.541 · 0.3.542 · 0.3.547 (전부 이중 실측 도장).

## 사장님이 하실 것

1. **「입지」 탭 한 번 열어 확인** (참사랑한의원 · **1km 고리**) — 0.3.547 뒤 첫 확인이
   아직 안 됐다(task #32). 상권 상자에 숫자가 뜨면 그 축은 살아난 것이다. 또 문장이 뜨면
   이번엔 **응답 맨 위 칸 이름**이 함께 적히니 그 캡처 한 장이면 고친다.
2. 남은 결정 둘: **카카오맵 열쇠**(#15) · **「입지」 이름 겹침**(#9).

## 바로 이어갈 작업

1. **머리 요약 배포 재시도** (task #34 · 최우선) —
   ```
   ① git fetch origin main → 최근 커밋이 30분 이상 조용한지 본다
   ② rebase 하지 말 것. main 에서 새로 뜨고 코드만 얹는다:
      git checkout -B claude/anseo-location-v0501 origin/main
      git checkout b45dd2c -- <아래 여덟 파일>
      make bump-version TO=<main 판 +1> · 문서 넷은 새로 쓴다
   ③ VEO_DEPLOY_ORDER="<사장님 문장>" make deploy   (검사+배포 한 번에 · 창을 좁힌다)
   ④ 서버·워커 이중 실측
   ```
   **우리 코드 파일 여덟** (`apps/web/src/app/(console)/console/customers/[customerId]/`):
   `LocationHead.tsx` · `location-head.ts` · `head-summary-says-where-it-measured.test.ts` ·
   `LocationTab.tsx` · `LocationTab.module.css` · `visitors-read-as-a-day-not-a-pile.test.tsx`
   · `apps/web/src/app/console-boxes-do-not-vanish.test.ts`(구역 10→11) ·
   `apps/web/src/lib/location-days.ts`
2. **0.3.547 뒤 첫 확인** (#32) — 사장님 캡처를 받는 즉시.
3. **카카오맵 타일**(#15) · **이름 겹침 정리**(#9) — 둘 다 사장님 결정 뒤.

## 대기/차단

- **배포가 막혀 있다 — 코드 탓이 아니다.** 두 방이 같은 main 을 두고 미는데 우리 한 판이
  검사 15분 + CI 20분이라 속도로는 못 이긴다. **지름길(채점 뒤 main 을 섞어 밀기)은
  쓰지 않는다** — 아무도 채점하지 않은 나무가 나가는 셈이고 오류 135 가 그것이다.
- **PostgreSQL 이 세션 중 네 번 죽었다.** 로그가 종료 기록 없이 끊긴다(컨테이너가 거둬감).
  `pg_ctlcluster 16 main start`. 긴 검사에는 감시를 붙여 돌린다:
  `while kill -0 $PID; do sleep 20; pg_isready -q … || pg_ctlcluster 16 main start; done`
- **자동 물림(`claim_version.py`)은 이력 절 제목을 `### … (v0.3.55x …)` 꼴로 찾는다.**
  옆 항목을 따라 `## … 0.3.55x` 로 쓰면 배포가 거기서 멈춘다.
- **변경이력 충돌은 두 방 글을 한 항목으로 붙인다** — 판 번호 줄이 같아서다. 항목 둘로
  갈라야 한다. 대기 표를 고친 뒤에는 **줄 수를 세어** 저쪽 줄이 빠지지 않았는지 본다.
- **rebase 가 문서마다 충돌을 내면 접는다.** `git diff --name-only <base> origin/main` 으로
  main 이 우리 코드 파일을 건드렸는지 보고(s22 에서 세 번 다 안 건드렸다) main 에서 새
  가지를 떠 코드만 얹고 문서는 새로 쓴다.
- **커밋 전 반드시** `grep -rln '^<<<<<<< |^>>>>>>> '`.

## 주의·제약

- 채팅에 비밀 값 붙여넣기 금지 · 사장님한테 「커밋」·「배포」 두 낱말만 · 못 잰 값 = «—»
- 커밋 트레일러 (필수):
  ```
  Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
  Claude-Session: https://claude.ai/code/session_013Fy4opA3k1FC6gQobSVKWf
  ```
- 판 규율: 시작 전 `git fetch origin main` 으로 물림 확인 (이 세션 네 번 물림: →506 · →509 · →512 · →515)
  → `make bump-version TO=…` → 변경이력·WORKLIST·HISTORY 는 손 → `make preflight` → `bash scripts/deploy.sh`
  (5/5 는 프록시 탓 exit 22 · 바깥 샌드박스 curl 로 실측) → 도장.
- **`ruff format` 을 저장소 전체에 돌리지 말 것** — 프로젝트는 `ruff check` 만 쓴다. 전체에 돌리면 471 파일이
  바뀐다 (이 세션에서 한 번 되돌림). 시스템 ruff(0.15) 말고 `.venv/bin/ruff` · `make lint-api`.
- 관문 목록: 반올림(`.toFixed`·`Math.round` 금지) · 브레이크포인트 720/960/1100 만 · 글자 11px 이상 ·
  상자 수 표(`console-boxes-do-not-vanish` · 거래처 상세 `[14, 11, 10, 9]`) · 문장 60자(우리말 인라인 주석
  금지) · ruff 곱셈 기호 금지 · E501 100칸 · RUF009 · 손으로 적은 타입은 계약에 실재.
- 로컬 시험 DB 드리프트 나면 postgres 사용자로 `veo_test` 를 지우고 다시 만든다.
- 가지를 main 에 rebase 한 뒤 푸시는 `--force-with-lease=<가지>:<옛 sha>` (맨 `-f` 는 막힘).

## 도구·실측 메모

- **바깥 샌드박스**: Higgsfield `sandbox_exec` — 운영 curl · 외부 다운로드 · 변환. 호출 60초 · 출력 4만 자.
  긴 일은 `nohup … &` + 로그 · `background:true` 로 `sleep 840` 을 띄워 15분 임대 연장.
  파일 이 방으로: `media_upload` → desktop-tutorial **`fetch-file` 워크플로**(`actions_run_trigger` ·
  method `run_workflow` · ref main · 입력 url·out·md5·branch) → `git pull`.
- **원본 위치**: desktop-tutorial `data/mois/` (연령 CSV · 표본점 · `floating_pop_1km_2024.json.gz` ·
  `floating_trend_2022/2023.json.gz` 낮·밤 요약) ·
  veo `apps/api/data/{population,transport,floating}/` (+ `meta.json`).
- **유동인구 격자 셈법**: 반경 안(최소 800m) 1km 격자 중심점 평균 밀도 x 반경 면적. 로컬 실측 강남역 1km
  평일 13시 229,455 · 04시 83,939 (배율 2.7) · 창원 마산합포구청 1km 12시 62,464 (배율 1.2).
  연도 흐름은 `trend` 열({"2022": [평일 낮, 평일 밤, 주말 낮, 주말 밤] …}) · 새 해 추가는 샌드박스
  `trend_summary()` 논리(스크립트 머리말) → `--merge-trend` → 같은 파일 · 강남역 전년 대비 +0.8%.
- **로컬 PostgreSQL**: `pg_ctlcluster 16 main start` · DB `veo_test` (root · 5432) · 적재 시험은
  `VEO_DATABASE_URL=…veo_test` 로 alembic upgrade → `bootstrap_*_from_disk()`.
- **운영 실측**: `/api/health` · `/api/queue` (바깥 샌드박스 curl).

## 참고

- 이 세션 로그 `docs/session-logs/2026-09-09-s22.md` · 직전 `docs/session-logs/2026-09-08-s21.md`
- 조사 보고서 `docs/plans/anseo-floating-population-sources.md` (전국 원천만 · 서브에이전트 셋)
- 현황 `PROJECT_STATE.md` · 지도 `핵심두뇌_MASTER.md`
