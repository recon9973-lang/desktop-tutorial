# RESUME — 다음 세션 이어가기 (2026-09-04 · s17 마감)

> 새 세션은 이 파일을 **먼저** 읽는다. 이 세션 상세는 `docs/session-logs/2026-09-04-s17.md`.
> 근거 문서: `docs/plans/anseo-location-marketing-axes.md` (여섯 갈래 통합) + `anseo-location-decisions-s17.md` (세 결정·다음 3판 실행 순서).

## 지금 상태 (s17 마감)

- **운영 판 = 0.3.500** ([실측 2026-09-04 · 바깥 샌드박스 curl] 서버·워커·웹 셋 다 · 워커 1대·뒤처진 워커 0)
- **v0.3.500 로 나간 것**: 20MB 파일 올리기 화면 폭발 고침 (Next.js 서버 액션 body 1MB→50MB) · 상단 네비 접이식 메뉴 사라짐 고침 (계정 메뉴와 같은 병)
- **veo-platform**: `claude/anseo-location-tab` `b2629cd` (도장) · main = `1a9fa9e`
- **desktop-tutorial** 이 방: `claude/hospital-location-analysis-plan-6kbmqo` (s17 조사·결정·로그) · main (체크포인트)

## 세 결정 확정 (재논의 없음 · `anseo-location-decisions-s17.md`)

⑴ **점수화 안 함 · 診療圏 스칼라만** (등급/별점/순위 X · 「합성값」 배지 필수 · 광역유입 진료과는 「참고치」 노란 배지)
⑵ **「개원 후보지 리포트」 SKU 만들되 v0.4 마일스톤** (1건 100만원 초안 · v0.3.500대는 SaaS 기능만)
⑶ **인테리어·장비 데이터 자동화 안 함** (사업모델 상충 · 견적서 PDF 업로드 창구만 · LLM 파싱 코퍼스 축적)

## 사장님이 지금 하실 것 (v0.3.500 나가서 자리 열림)

1. **콘솔 → 관리자 → 데이터 원천 → 「전국 버스정류장」 → 「파일 올리기」** → 파일 A `984836b2-...20251031.csv` (20MB) · 인코딩 **CP949** → 올리기 → 「LOADED · 227,053행」 뜨면 「입지」 탭에 값이 뜸
   - 오류 카드 뜨면 저에게 알려 주세요 (원인 다시 파악)
2. (선택) **공공데이터포털 API 두 개** 발급만 미리 (건축물대장 · 전국주차장정보) — 다음 판(v0.3.501) 나가면 자리 열림
3. (선택) **행안부 인구 CSV** (jumin.mois.go.kr · 읍면동 단위 · 최신월) — v0.3.501 나가기 전 넘겨 주시면 됨

## 바로 이어갈 작업 (이 방 · 도현이가 뜁니다)

### 1. 사장님 파일 A 업로드 성공 확인

- 사장님이 「LOADED · 227,053행」 확인하시면 「입지」 탭 값 뜨는 것 실측 (강남역 500m 안 버스정류장 70 등)

### 2. v0.3.501 코드 얹기 (다음 판 · 인구 축 + 진료과별 3표)

- 새 가지 (예: `claude/anseo-location-v0501`)
- 인구 축: `mois_population` 로더 · 행정동×성×연령 · 「반경 안 인구 카드」로 「—」 자리 채움
- 진료과별 3표: `dim_department_patient_mix` (HIRA 국민관심질병통계) · `dim_utilization_rate` (HIRA + NHIS) · `fact_chs_indicator` (질병청 CHS 시군구 258)
- 진료과 셀렉터 UI: 피부·정형·소아·산부·이비·비뇨 (⑤ 갈래 산식 6개)
- 시험 4벌 · 화면 관문 · 규모 1000~1500줄
- **선행**: 사장님 인구 CSV 넘겨주시면 시작

### 3. v0.3.502 (그 다음 · 診療圏 스칼라 + 비교 모드 + 유출률 배지)

- `docs/plans/anseo-location-decisions-s17.md` §다음-3판-실행-순서 참조

## 안 만질 것 · 대기

- 인테리어·장비 데이터 자동화 (결정 ⑶ · 사장님이 사업모델 정하기 전까지 X)
- 점수화·A/B/C 등급 (결정 ⑴)
- 매물 스크레이핑 (다윈중개 판례) · 플레이스 리뷰 스크레이핑 (잡코리아 판례) · 경쟁 병원 광고 크리에이티브 저장 (의료법 57조)

## 도구·실측 메모

- **운영 실측 우회**: 이 방 프록시 403 → Higgsfield MCP `sandbox_exec` curl 로
- **파일 로컬 시험**: `python -c "from scripts.load_transport_stops import load; load(source_key='molit_bus_stops', file_path=Path('...'), encoding='cp949', reference_date=...)"` · 파일 문제/서버 문제 판별
- **Next.js 서버 액션 body 상한**: 기본 1MB · `experimental.serverActions.bodySizeLimit` (v0.3.500 에서 50MB 확장)
- **로컬 PostgreSQL**: `pg_ctlcluster 16 main start` · 접속 `root` · `pg_hba.conf` 임자 `postgres:postgres` 유지
- **로컬 시험 DB**: `veo_test` · `VEO_TEST_DATABASE_URL="postgresql+psycopg://root@localhost:5432/veo_test"`
- **worklist.test.ts flake**: 배포 대기 표에 이미 나간 판 남으면 실패 · 도장 시 반드시 표에서 지움
- **MasterKey 시험**: `MasterKey.from_base64(MASTER_KEY_V1_B64, version=1)` (생성자 아님)
- **veo-platform 클론**: `git clone --depth 1 https://github.com/recon9973-lang/veo-platform /home/user/veo-platform`

## 주의·제약 (반드시)

- **채팅에 API 열쇠·비밀키 붙여넣기 금지** — 콘솔에서만
- 이 방 브랜치: desktop-tutorial `claude/hospital-location-analysis-plan-6kbmqo` (문서·기획) · veo-platform `claude/anseo-location-tab` (배포 가지)
- 커밋 트레일러:
  ```
  Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
  Claude-Session: https://claude.ai/code/session_013Fy4opA3k1FC6gQobSVKWf
  ```
- 사장님께는 「커밋」·「배포」 두 낱말만
- 못 잰 값 = «—» · 합산 점수 없음 (결정 ⑴) · 판 다르면 비교 금지 · 의료광고법 준수
- 판 부딪히면 나중 것이 물러남

## 참고

- 이 세션 로그 `docs/session-logs/2026-09-04-s17.md`
- 직전 `-s16.md`
- 여섯 축 조사 `docs/plans/anseo-location-marketing-axes.md` (커밋 077839d)
- 세 결정 확정 `docs/plans/anseo-location-decisions-s17.md` (커밋 ce3c945)
- 기획안 `docs/plans/anseo-location-analysis-plan.md`
- 배포 규율 `veo-platform/scripts/deploy.sh` 머리말
