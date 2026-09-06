# RESUME — 다음 세션 이어가기 (2026-09-06 13:05 KST · s20 마감)

> 새 세션은 이 파일을 **먼저** 읽는다. 이 세션 상세는 `docs/session-logs/2026-09-06-s20.md`.

## 지금 상태

- **운영 판 = 0.3.512** (2026-09-06 13:02 KST 이중 실측 · 서버·워커 둘 다)
- 이 세션이 내보낸 판 넷: **0.3.506** 인구 원천 · **0.3.507** 인구 인포그래픽 · **0.3.509** 교통
  정류장 세부(승/하차/환승) · **0.3.512** 인구 연령 피라미드(5세 21구간 남/여 · 비율 셋)
- 「입지」 탭 세 축 전부 실측값: 경쟁(심평원) · 교통(개수 + 이용량) · 인구(성별·증감 + 연령 피라미드)
- veo-platform 우리 가지 `claude/anseo-location-v0501` = main `ec760da` + 도장 커밋 `b2422c3`
- desktop-tutorial 이 방 가지 `claude/hospital-location-analysis-plan-6kbmqo`

## 사장님이 하실 것 · **한 번만**

브라우저 강력 새로고침 → 「입지」 탭 인구 카드 밑에 **연령 피라미드** (남 왼쪽 파랑 · 여 오른쪽
초록 · 위 고령) + 유소년·생산가능·고령 비율. 설정 「데이터 원천」에 연령 원천 한 줄
(행정동 3,598 x 21 = 75,558행) — 행 수는 사장님 화면에서 확인 (이 방은 그 창구를 못 부름).

## 바로 이어갈 작업 (사장님 다음 오더 기다림 · 후보 순)

1. **반경 안 정확 인구** — SGIS 행정동 경계 API 로 centroid → 하버사인 반경 합. 지금은 시군구 합.
   SGIS OpenAPI 인증 필요 여부 확인 → 필요하면 그때만 사장님 「외부 연결 열쇠」.
2. **카카오맵 타일** — 사장님이 콘솔 「외부 연결 열쇠」에 카카오 항목 넣으신 뒤 (task #15).
3. **유동인구 원본** — 사장님 지적 「인구 이동」 나머지 절반. 통신사 유동인구는 유료 ·
   공공데이터포털 「생활인구」(서울시만) 후보. 조사부터.
4. **「입지」 이름 겹침 정리** (task #9 · s16 부터 미결) · **웹 UI CSP 진단** (task #19).

## 대기/차단

- 없음 (사장님 손 zero 유지). 외부 인증이 필요한 판은 그 판에 들어갈 때만 요청.

## 주의·제약

- 채팅에 비밀 값 붙여넣기 금지 · 사장님한테 「커밋」·「배포」 두 낱말만 · 못 잰 값 = «—»
- 커밋 트레일러 (필수):
  ```
  Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>
  Claude-Session: https://claude.ai/code/session_013Fy4opA3k1FC6gQobSVKWf
  ```
- 판 규율: 시작 전 `git fetch origin main` 으로 물림 확인 → `make bump-version TO=…` (감사 방
  도구 · 판·계약·클라이언트·관문 넷 기계) → 변경이력·WORKLIST·HISTORY 는 손 → `make preflight`
  → `bash scripts/deploy.sh` (5/5 는 프록시 탓 exit 22 · 바깥 샌드박스 curl 로 실측) → 도장.
- 관문 목록 (이 세션에 걸린 것): 반올림(`.toFixed`·`Math.round` 금지) · 브레이크포인트 720/960/1100 만 ·
  글자 11px 이상 · 상자 수 표(`console-boxes-do-not-vanish`) · 문장 60자(`>본문<` 추출이 `=>` 를
  태그로 보니 **우리말 인라인 주석 금지**) · ruff 곱셈 기호 금지 · 손으로 적은 타입은 계약에 실재.
- 로컬 시험 DB 드리프트 나면 postgres 사용자로 `veo_test` 를 지우고 다시 만든다 (conftest 가 head 로 올림).

## 도구·실측 메모

- **바깥 샌드박스**: Higgsfield `sandbox_exec` — 운영 curl · 행안부 사이트 · 변환. 출력 4만 자 잘림.
  파일 이 방으로 옮길 땐 `media_upload` → desktop-tutorial **`fetch-file` 워크플로**(GitHub Actions
  `actions_run_trigger` · ref main · 입력 url·out·md5·branch) → `git pull`.
- **행안부 연령별 CSV 받는 법**: `apps/api/scripts/build_population_age_data.py` 머리말에 POST 주소와
  폼 값 전부 적어 둠 (5세 단위 · 전국 · 전체읍면동현황 · cp949 · 합계 행은 코드 끝 00000).
- **원본 위치**: desktop-tutorial `data/mois/` · 이 방 uploads 폴더 · veo `apps/api/data/population/`.
- **로컬 PostgreSQL**: `pg_ctlcluster 16 main start` · DB `veo_test` (root 사용자 · 로컬 5432).
- **운영 실측**: `/api/health` · `/api/queue` (바깥 샌드박스 curl).

## 참고

- 이 세션 로그 `docs/session-logs/2026-09-06-s20.md` · 직전 `docs/session-logs/2026-09-05-s19.md`
- 현황 `PROJECT_STATE.md` · 지도 `핵심두뇌_MASTER.md`
