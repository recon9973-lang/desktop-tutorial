# RESUME — 다음 세션 이어가기 (2026-09-08 18:40 KST · s21 · 0.3.547 나감)

> 새 세션은 이 파일을 **먼저** 읽는다. 이 세션 상세는 `docs/session-logs/2026-09-08-s21.md`.

## 지금 상태

- **이 방이 오늘 내보낸 판 셋** — 전부 서버·워커 이중 실측으로 도장 찍음:
  - **0.3.541** 「입지」 자동 다시받기를 **축마다 다르게** (상권 3번 40초 · 인구 이동 4번
    100초 · 방문자 5번 300초 · 섞이면 느린 쪽 · 오래 걸리는 축은 까닭을 띠에)
  - **0.3.542** 방문자를 **하루 평균**으로 (연인원 ÷ 받은 날수 · 자른다 · 누계는 밑에 작게) ·
    숫자가 「6,836,6 / 12」 로 끊기던 것 고침 · 달 이름표에 해(`2025.09`)
  - **0.3.547** ① 상권 축이 **처음으로 살았다** — 소상공인 sdsc2 는 `header`/`body` 를 맨
    위에 준다(0.3.534 는 활용가이드만 보고 만들어 늘 「아직 못 받았습니다」였다). 두 꼴을
    다 받고, 어긋나면 응답의 **맨 위 칸 이름을 그대로 적는다**.
    ② 방문자 마지막 막대 폭락(14,777) — **받은 날수**를 통로→`days` 열→계약→화면까지 들고
    가서 그 날수로 나눈다 · 덜 찬 달은 「덜 참」 · 마이그레이션이 표를 비움(재수집)
- **실측**: 0.3.542 = 2026-09-08 16:14 KST · **0.3.547 = 18:34 KST** (서버·워커 · 뒤처진 워커 0)
- **운영 판은 그 뒤 ANSEO 방이 0.3.548·0.3.549 로 올렸다.** 우리 0.3.547 은 main 에 들어 있다.
- veo-platform 우리 가지 `claude/anseo-location-v0501` = **origin/main + 배포오더 기록 한 줄**
  (2026-09-08 재정렬 · 물림 없음) · desktop-tutorial 이 방 가지
  `claude/hospital-location-analysis-plan-6kbmqo`
- 「입지」 다섯 축 전부 실측값이 붙었다: 경쟁(심평원) · 교통 · 인구 · 인구 이동 · 상권 · 방문자

## 사장님이 하실 것

1. **「입지」 탭 한 번 열어 확인** (참사랑한의원 · **1km 고리**) —
   - **상권 상자**에 합계·업종 갈래·많은 순 막대가 뜨면 그 축은 살아난 것이다. 또 문장이
     뜨면 이번엔 **맨 위 칸 이름**이 함께 적히니 그 캡처 한 장이면 고친다.
   - **방문자 상자**는 표를 비웠으므로 처음엔 「받는 중」 띠 — 열두 달 재수집에 **몇 분**,
     화면이 5분까지 스스로 기다린다. 다 차면 막대가 고르고 덜 찬 달만 「덜 참」.
2. 남은 결정 둘: **카카오맵 열쇠**(#15) · **「입지」 이름 겹침**(#9 · 이 방 「상권」 /
   ANSEO 「자리」 / 그대로).

## 바로 이어갈 작업 (사장님 다음 오더 기다림 · 후보 순)

1. **0.3.547 뒤 첫 확인** (task #32) — 위 캡처를 받는 즉시. 상권이 또 실패 문장이면
   `apps/api/src/veo/location/store_zone.py` 의 `_envelope_of` 가 적어 준 맨 위 칸 이름으로
   맞춘다. 방문자가 덜 차 보이면 `_run_tour_pull` 이 달마다 커밋하는 탓 — 다 받으면 12개월.
2. **「입지」 다섯 축 머리 요약** — 이 방 스스로 할 수 있는 다음 판. 다섯 상자를 다 읽지
   않고도 한 줄로 자리를 판단하게 하는 머리말.
3. **카카오맵 타일**(#15 · 사장님 열쇠 뒤) · **이름 겹침 정리**(#9 · 사장님 결정 뒤).

## 대기/차단

- 열쇠·활용신청은 **전부 끝났다**. 남은 사장님 몫은 위 결정 둘.
- **판 물림이 매우 잦다** — 2026-09-07~08 이틀에 열한 번. 규칙은 **먼저 main 에 닿은 쪽을
  두고 뒤엣것이 물러난다.** 배포 직전은 물론 `deploy.sh` 가 미는 **그 순간에도** 물린다.
  rebase 가 중첩 충돌을 내면 **접고**, main 이 우리 파일을 건드렸는지
  `git diff --name-only $BASE origin/main -- <우리 파일>` 로 본 뒤 main 에서 새 가지를 떠
  우리 파일만 얹는 편이 깨끗하다. 문서(변경이력·WORKLIST·HISTORY)는 새로 쓴다.
- **커밋 전 반드시** `grep -rln '^<<<<<<< |^>>>>>>> '` — s21 에서 충돌 표시를 커밋에
  들여보낸 적이 있다.
- ANSEO 방의 **문서만 바뀐 판**이 번호를 먹는다(0.3.545·0.3.546). 규칙으로 만들지는 두 방이
  같이 정할 일 — 사장님께 여쭐 거리로 남겨 둠.

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

- 이 세션 로그 `docs/session-logs/2026-09-08-s21.md` · 직전 `docs/session-logs/2026-09-06-s20.md`
- 조사 보고서 `docs/plans/anseo-floating-population-sources.md` (전국 원천만 · 서브에이전트 셋)
- 현황 `PROJECT_STATE.md` · 지도 `핵심두뇌_MASTER.md`
