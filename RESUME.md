# RESUME — 다음 세션 이어가기 (2026-09-06 22:26 KST · s20 + 0.3.519)

> 새 세션은 이 파일을 **먼저** 읽는다. 이 세션 상세는 `docs/session-logs/2026-09-06-s20.md`.

## 지금 상태

- **운영 판 = 0.3.521** (2026-09-06 23:42 KST 이중 실측 · 문구 정정 · 판 물림 0.3.520→0.3.521) · 0.3.519 인구 이동 22:26 KST · 0.3.517·0.3.518 은 ANSEO 방
- 이 세션이 내보낸 판 여섯: **0.3.506** 인구 원천 · **0.3.507** 인구 인포그래픽 · **0.3.509** 교통
  정류장 세부 · **0.3.512** 인구 연령 피라미드 · **0.3.513** 반경 안 인구(행정동 경계 표본점) ·
  **0.3.515** 반경 안 시간대별 유동인구(**전국 1km 격자** 116,850 · 평일/주말 24시간 · Zenodo CC BY 4.0) ·
  **0.3.516** 유동인구 연도 흐름(2022→2023→2024 낮 평균 막대 · 전년 대비 % · `trend` 열 · 새 표 없음) ·
  **0.3.519** 인구 이동(행안부 API 통로 · 열쇠 뒤 자동 수집 · 열쇠 없으면 「열쇠 넣으면 켜집니다」)
- 「입지」 탭 세 축 전부 실측값: 경쟁(심평원) · 교통(개수 + 이용량) · 인구(성별·증감 + 연령 피라미드 +
  반경 안 인구 + 시간대별 유동인구 곡선)
- veo-platform 우리 가지 `claude/anseo-location-v0501` = main `b9c4756` + 도장 커밋
- desktop-tutorial 이 방 가지 `claude/hospital-location-analysis-plan-6kbmqo`

## 사장님이 하실 것 · **한 번만** (인구 이동을 살리는 열쇠)

1. ~~활용신청~~ — **끝남** (사장님 캡처 2026-09-06: 승인 6건 · 인구이동 15108093 포함).
2. 공공데이터포털 **일반 인증키(Decoding)** 를 **Railway `veo-platform` 서비스 변수 `VEO_DATA_GO_KR_SERVICE_KEY`** 에.
   (**정정**: 콘솔 「외부 연결 열쇠」에는 공공데이터포털 자리가 **없다** — 계정별 열쇠라 금고에 안 둠 ·
   `credentials/providers.py`. 0.3.519 문구가 틀려 0.3.521 로 고침.)
3. 콘솔 「데이터 원천」에서 「심평원 병원정보 API」·「행안부 지역별 인구이동 API」 줄이 열쇠 있음으로 바뀌면 연결.
   거래처 「입지」 탭 열기 → 인구 카드 맨 밑 「인구 이동 · 최근 12개월」 이 KPI 셋 + 월별 막대로 바뀜.
   안 바뀌면 그 자리의 문장이 까닭(열쇠 거절 = 활용신청 미승인 · 형식 다름 = 첫 실호출 확정 필요 → 이 방에 알려 주십시오).

## 바로 이어갈 작업 (사장님 다음 오더 기다림 · 후보 순)

1. **인구 이동 첫 실호출 확정** — 사장님 열쇠 뒤 「입지」 탭 문장을 보고 `location/population_move.py` 의
   `lv`·항목 이름(`statsYm`·`totNmprCnt`)·봉투 꼴을 맞춘다. 응답 원문은 서버 로그(`인구 이동 받기 실패` warning
   의 detail) 로 온다. 열쇠 없는 CSV 길은 막힘(WAF · 2026-09-06) — 다시 두드리지 말 것.
2. **관광객 유입 축** — 관광공사 방문자 API 15101972 (시군구 · 현지인/외지인/외국인 · 월). 열쇠 1회.
3. **카카오맵 타일** (task #15 · 사장님 열쇠 뒤) · **「입지」 이름 겹침 정리** (#9 · 사장님 결정: 이 방 「상권」 / ANSEO 「자리」 / 그대로).
   #19 CSP 진단은 닫음 — 콘솔 호출은 서버측 · 「Failed to fetch」 는 파일 올리기 직접 POST · veo.seokorea.org CORS 허용 실측.

## 대기/차단

- **남은 후보가 전부 사장님 손이 필요**: 인구 이동·관광객 열쇠(공공데이터포털 활용신청) · 카카오맵 열쇠 · 「입지」 이름 결정.
  다음 세션은 사장님 오더가 이 중 하나를 고르면 그 판으로 들어간다.

## 주의·제약

- 채팅에 비밀 값 붙여넣기 금지 · 사장님한테 「커밋」·「배포」 두 낱말만 · 못 잰 값 = «—»
- 커밋 트레일러 (필수):
  ```
  Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>
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

- 이 세션 로그 `docs/session-logs/2026-09-06-s20.md` · 직전 `docs/session-logs/2026-09-05-s19.md`
- 조사 보고서 `docs/plans/anseo-floating-population-sources.md` (전국 원천만 · 서브에이전트 셋)
- 현황 `PROJECT_STATE.md` · 지도 `핵심두뇌_MASTER.md`
