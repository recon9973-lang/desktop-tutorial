# ANSEO · 상권 축 §7 P3 도면 — 카카오맵 · 추계 환자 수 · 비교 모드

> 이 도면은 **다른 방(P2)** 이 심는 「교통·인구 실적재」위에 **얹기만** 한다.
> 새 원천 표(`SourceRow`)는 P2 가 정하고 여기서는 이름만 참조한다.
> 판 번호는 이 방이 정하지 않는다.
>
> **작성** 2026-09-04 (s16) · **뿌리**: 지훈 형(도면) · 서연 씨(카카오맵·산식 조사)
> **선행** = 기획안 §7 P2 배포 마감 (다른 방)
> **후행** = 이 도면대로 코드 얹기 (다음 세션·이 방)

## §0. 이 판이 무엇인가

기획안 `docs/plans/anseo-location-analysis-plan.md` §7 의 세 번째 우선:

- **ⓐ 카카오맵 타일** — 지금 SVG 로만 그려지는 지도에 진짜 지도 얹기
- **ⓑ 추계 환자 수 카드** — 반경 안 인구·유병률·수진율로 하루/월 잠재 환자 산정
- **ⓒ 비교 모드** — 두 거래처를 나란히 놓고 상권 축 비교

세 항목 모두 **다른 방 §7 P2** (교통·인구·경계 실적재) 위에 앉는다. P2 가 먼저 배포되어야 여기 산식이 «—» 아닌 진짜 값을 낸다.

## §1. 세 항목 · 한 줄 요지

| 항목 | 지금 상태 | 이 판이 심는 것 | 열쇠 필요 |
|---|---|---|---|
| ⓐ 카카오맵 타일 | SVG 등거리(회색 배경) | 카카오 JS SDK 조건부, SVG 는 폴백으로 남김 | JavaScript 열쇠 (도메인 화이트리스트) |
| ⓑ 추계 환자 수 | 없음 (Density 자리 한 줄만) | 診療圏 형 산식 카드 · 3단 상태(정상/근사/못 잼) | 진료과별 수진율 표 (HIRA 근거 · 우리가 만들어야) |
| ⓒ 비교 모드 | 없음 | 두 거래처 2단 나란히 · 같은 판일 때만 | — |

## §2. ⓐ 카카오맵 타일

### 지금

`apps/web/src/app/(console)/console/customers/[customerId]/LocationTab.tsx:154-252` 의 `RingMap`이 **타일 없는 SVG**다. 파일 머리말 34행 못박음: *«지도 타일(카카오맵)은 열쇠·약관이 따로 있어 다음 판이다»*. 이 판이 그 «다음 판» 이다.

### 붙일 자리

- `LocationTab.tsx:154` 의 `RingMap` 을 **그대로 두고** 같은 폴더에 `RingMapKakao.tsx` 신규
- 상위 (`LocationTab.tsx:120` 근처)에서 `kakaoJsKey` 있으면 `RingMapKakao`, 없으면 SVG
- 창구는 하나 더 안 판다. `readLocation` 응답에 `map_provider: { kind, client_key }` 한 필드 추가

### 카카오맵 실측 (서연 씨 조사)

- **SDK 열쇠 종류**: 지도 SDK = JavaScript 열쇠, 서버 REST = REST 열쇠. **섞으면 안 됨**. 도메인 화이트리스트 필수.
- **로딩 URL**: `https://dapi.kakao.com/v2/maps/sdk.js?appkey=…&libraries=services,clusterer,drawing`
- **요금**: 무료 쿼터(개편 중) + 초과 시 지도 타일 건당 0.1원, 좌표→주소 0.5원. 로컬 API는 2026 프로모션 건당 10원(정상가 50원 예정). 상용은 「비즈월렛 + 유료 API 활성화」.
- **오버레이**: Marker·Circle·Polygon·Polyline·CustomOverlay 모두 지원 — 반경 링은 `kakao.maps.Circle` 다섯 개.
- **좌표계**: SDK 는 WGS84 그대로 받음. **VWorld·SGIS 는 UTM-K** 라 우리는 WGS84 통일 규칙.
- **다크 모드**: **공식 미지원**. CSS invert 는 회색지대. **안전책 = 지도만 라이트 고정**, 우리 UI 는 테마 따름.

### 대안

| 지도 | 무료 | 상용 | 한국 POI |
|---|---|---|---|
| 카카오 | 개편 중 | 비즈월렛 유료 API | ★★★ |
| 네이버 | 월 1,000만건 무료·모바일 무제한 | 표준 | ★★ |
| VWorld | 무제한 | **국외 반출 금지** | ★★★ |
| OSM | 무제한 | 자유 | ★ (한국 POI 빈약) |

**결정**: 카카오 (POI 최강). 네이버는 대안 후보로 남김.

### 열쇠 두 자리

⑴ 환경변수 `VEO_KAKAO_MAP_JS_KEY` (`core/settings.py:154` 부근 `ProviderCredentials` 에 추가)
⑵ 「데이터 원천」 표에 `kakao_map_js` 행 추가 (기존 `kakao_geocoding` 옆). 열쇠 없으면 `KEY_MISSING`(정상 상태, 색 안 칠함).

### 폴백 (SVG 로 되돌아감)

- 열쇠 없음 → SVG
- SDK 스크립트 로드 실패(오프라인·차단·API 죽음) → `useEffect` 안 `onerror`/타임아웃 3초에서 잡아 SVG
- 위 어느 경우든 한 줄 안내 (색+글자 병용): 「지도가 안 열려 등거리 SVG 로 그렸습니다」

### 시험

`LocationTab.test.tsx`(신규):
- ① `client_key: null` → SVG 가 그려진다
- ② `client_key` 있음 → 카카오 SDK 스크립트 태그가 head 에 삽입 (모킹)
- ③ SDK 로드 3초 안에 안 오면 SVG 로 되돌아간다

파이썬: `tests/location/test_router.py:payload` 에 `map_provider` 키 존재 검사.

## §3. ⓑ 추계 환자 수 카드

### 지금

없다. `LocationTab.tsx:318` 의 `Density` 가 «인구 1만 명당은 인구 자료 적재 후» 라 못박아 두었다 — 이 카드가 그 후속.

**HIRA 는 기관 좌표·진료과목만** 있고 **유병률·수진율 자료는 저장소에 없다** (`grep prevalence|유병|수진` = 0건).

### 산식 (일본 診療圏 형)

```
추계 환자 수 = Σ(연령·성별 칸) 반경 안 인구 × 진료과 유병률 × 수진율
경쟁 조정치 = 추계 환자 수 ÷ (반경 안 같은 과 기관 수 + 1)   ← 자기 자신 포함
```

반경 안 인구는 **원과 행정동 경계 겹치는 면적 비율**로 나눈다 (SGIS 경계 — 다른 방 P2 가 심는다).

### 국내 원천 실측 (서연 씨 조사)

- **표준식**: `診療圏 인구 × 진료과별 수진율 ÷ (경쟁 의원 수 + 1)`. 일본 컨설팅사 공통.
- **국내에 「진료과별 수진율 상수표」 공식판은 없음.** HIRA 지역별 통계 + 인구총조사로 **우리가 만들어야** 함.
- **진료과 코드**: 법제처 별표3 — 26개 표시과목 코드. HIRA 코드조회 마스터 확보 가능.
- **국내 SaaS/컨설팅** (브랜드본담·개원닷컴·스타닥·브레인스펙·HIRA 개원 입지 예측): 방법론 전부 **비공개** — 일본식 診療圏 이식 + 정성 리포트 판매로 추정.
- **광역 유입 진료과**(성형·안과·산부인과 특수 등): 산식대로면 <1명/일 → **산식 부적합**. 별도 배지.

### 붙일 자리

`LocationTab.tsx:132-133` 의 `Density` **아래**, `<div className={own.axes}>` 시작 전. 카드 제목 「추계 환자 수 — 반경 안, 이 진료과 기준」. 상단 요약 + 하단 산식 펼침(`<details>`).

### 카드 상태 3단 (색+글자 병용)

| 상태 | 뜻 | 색 | 글자 라벨 |
|---|---|---|---|
| 정상 | 세 축 다 있고 산식 적합 | 초록 | 「추계 재는 중」 |
| 근사 | 산식은 도는데 광역 유입 진료과라 값이 크게 흔들림 | 노랑 | 「산식 부적합 — 참고만」 |
| 못 잼 | 인구·유병률·수진율 하나라도 없음 | 회색 (색 안 칠함) | 「«—» · 어느 자료가 없어서 못 재는지 문장」 |

### 새 API 응답

`schemas.py` 에 `PatientEstimatePayload(BaseModel)`:

```python
class PatientEstimatePayload(BaseModel):
    available: bool
    note_ko: str                      # 못 잘 때 사유
    subject_ko: str                   # 「내과」 등 — 중심 기관 첫 과목
    radius_m: int
    population_in_ring: int | None
    prevalence_rate: float | None
    utilization_rate: float | None
    raw_estimate: int | None
    competitor_adjusted: int | None
    missing_axes: list[str]           # ["POPULATION", "PREVALENCE", "UTILIZATION"]
    formula_fit: str                  # "OK" | "WIDE_AREA_UNFIT"
    basis_month: str                  # HIRA
    population_month: str | None      # P2 원천
```

`LocationPayload` 에 `patient_estimate: PatientEstimatePayload` 필드 추가 (라우터 `router.py:80-121` 응답 조립부).

계산은 `service.py` 안 `_patient_estimate_of(session, center, radius_m, population_reader, prevalence_table)` 순수 함수. 못 잰 축이 하나라도 있으면 `available=False` + `missing_axes` 채워 리턴.

### 사장님 열쇠·파일

- **인구·경계**는 다른 방(P2) 가 심는다 — 여기서는 loader 이름만 참조
- **유병률·수진율은 새로 심어야** 한다:
  - `apps/api/data/hira_disease/<판>/prevalence.csv` (진료과 · 연령대 · 성별 · 유병률 · 수진율)
  - 원천 = 심평원 「진료비 통계지표」 공개자료 · 사장님이 공공데이터포털에서 받아 `scripts/load_hira_disease.py` (신규) 돌림
  - 「데이터 원천」 표에 `hira_disease_stats` 행 추가 — `axis=POPULATION`, `method=FILE`

### 시험

`apps/api/tests/location/test_patient_estimate.py`(신규):
- ⑴ 세 축 다 있음 → 값 나옴 (고정 소수 비교)
- ⑵ 인구만 없음 → `available=False`, `missing_axes==["POPULATION"]`, 최종 카드값 null
- ⑶ 중심 기관 과목 없음 → 전체 `available=False` + 「중심 기관 과목을 몰라 재지 않습니다」
- ⑷ 광역 유입 진료과 → `formula_fit="WIDE_AREA_UNFIT"`, 노랑 상태

웹: `LocationTab.test.tsx` — 카드 자리에 «—» 와 사유 문장이 함께 뜬다 (색+글자).

### 폴백

- 한 축이라도 «—» → 카드 몸통 = 문장 하나 「인구(행정안전부) 아직 적재되지 않아 재지 않습니다 — 데이터 원천에서 적재하십시오」. 링크는 SUPER_ADMIN 만 활성 (`PermissionGate`).
- 카드 밑줄 **붉은 글씨(색+글자)**: **「내부 산정 · 광고 문구로 옮기지 마십시오 (의료광고법)」**
- 경쟁 조정치는 분모 0 나오면 원값과 같이 두지 않고 `null` + 「반경 안 같은 과 기관이 0곳이라 조정하지 않았습니다」

## §4. ⓒ 비교 모드

### 지금

상권 탭에는 없다. 유사한 「비교 판」은 이미 있다 — `apps/web/src/lib/comparisons.ts` + `apps/api/src/veo/competitors/comparison.py` 의 **`allow_scope_variance` · `blocking_differences` · `refused` · `baseline`** 문법 (ADR 0010). 상권은 그 규율만 재활용한다.

### 진입

- 거래처 목록(`console/customers/page.tsx`) 체크칸(`BatchScanBar` 옆) 그대로 씀
- 두 곳 골라졌을 때만 상단에 「상권 나란히 보기」 단추가 뜬다
- 세 곳 이상 고르면 단추 비활성 + 「두 곳까지 나란히 봅니다」 (색+글자)
- 진입 URL: `/console/customers/{leftId}?tab=location&compare={rightId}&radius=1000` — 라우트 키 `location` 은 사장님 확정(2026-09-03) 그대로
- 왼쪽이 기준(baseline), `?compare=` 가 상대

### 화면 레이아웃

- `LocationTab.tsx` 상단에서 `?compare=` 읽어 (→ `page.tsx` 의 `sp['compare']` 프롭스로 흘림), 있으면 `LocationCompareTab` 으로 바꾼다 (같은 폴더 신규 `LocationCompareTab.tsx`)
- 2단 그리드 (`grid-template-columns: 1fr 1fr`, 좁으면 세로 1단)
- 왼쪽·오른쪽 컬럼 각자 지금 `LocationTab` 이 그리는 것과 **같은 뼈대**: 중심 카드 · 반경 표 · 지도 · 밀도 · 추계 환자 수 · 축 3종
- **스티키 헤더** — 각 컬럼 상단 「거래처 이름 · 심평원 기준월 · 반경」 (`position: sticky; top: var(--console-bar-h)`)
- 반경 칩은 **한 벌**만 위 가운데 (같은 반경 공유해야 나란히 볼 뜻이 있음)

### 새 API

- `GET /customers/{left_id}/location/compare?right={right_id}&radius_m=...`
- `LocationComparePayload { left: LocationPayload, right: LocationPayload, comparable: bool, refusal_ko: str | null, blocking_differences: [...] }`
- 서버 `service.py` 에 `compare_location(db, left, right, radius_m)` — 두 `read_location` 을 부른 뒤 **판 비교 관문**:

| 차이 항목 | 판정 |
|---|---|
| `center.basis_month` 다름 | blocking («심평원 기준월 다릅니다: 2026-06 ↔ 2026-03») |
| `population_month` 다름 | blocking («인구 판 다릅니다») |
| `radius_m` 다름 | blocking (프론트가 강제 통일하지만 방어) |
| 둘 중 하나 center 없음 | blocking («중심 못 잡은 거래처가 있습니다») |
| subjects 겹침 0 | warning (경쟁 축 비교 불가지만 다른 축 나란히) |

blocking 하나라도 있으면 `comparable=False`, 화면은 두 컬럼을 그대로 그리되 **가운데에 굵은 사유 띠** (색+글자).

라우트: `router.py` 에 `@router.get("/compare")` 하나 추가 (기존 `_customer` 두 번 부름 — 양쪽 tenant scope 검사).

### 사장님 열쇠·파일

없다. ⓑ 가 심는 것 위에서만 돎.

### 시험

`apps/api/tests/location/test_compare.py`(신규):
- ⑴ 같은 기준월·같은 인구 판 → `comparable=True`, 두 payload 나온다
- ⑵ 기준월 다름 → `comparable=False`, `blocking_differences` 에 판별 문장
- ⑶ 오른쪽 거래처가 다른 조직 → 404 (테넌트 격리 · `_customer` 이 이미 막음)

웹: `LocationCompareTab.test.tsx`:
- ① 두 컬럼이 같은 반경 칩 공유
- ② `blocking_differences` 있으면 데이터가 나란히 안 그려지고 사유 띠만
- ③ 「두 곳까지」 규칙 (세 곳 고르면 단추 비활성)

### 폴백

- `?compare=` 유효하지 않은 UUID → 무시하고 단일 모드
- 상대 거래처 못 읽음 (권한·삭제) → 왼쪽만 그리고 상단 띠 「비교 상대 못 불렀습니다: {사유}」 (색+글자)
- 두 판 정렬 안 맞으면 **비교 안 그림** — ADR 0010 재확인 (판 다르면 그럴듯한 거짓)

## §5. 사장님 확정 결정 세 개 (2026-09-04)

**세 항목 모두 서연 씨 추천 그대로 확정.** 재논의 없이 이 판 코드 얹을 때 이대로 심는다.

⑴ ✅ **지도 = 카카오맵 웹 SDK · 열쇠는 SUPER_ADMIN 페이지 관리** — JS 열쇠는 프론트(도메인 화이트리스트), REST 열쇠는 서버 프록시. 대안(네이버) 은 포기하지 않고 열쇠 자리만 바꾸면 붙게 코드 씀.

⑵ ✅ **산식 = 診療圏 국내 이식판 표준식** — 「인구 × 유병률 × 수진율」 분해형은 v2 로 미룸. 광역 유입 진료과(성형·안과 특수 등)는 「산식 부적합」 노란 배지.

⑶ ✅ **초기엔 진료과별 수진율 상수 표 하나 (JSON 하드코딩)** — HIRA 근거 · 산정식 · 업데이트일을 파일 머리말에 못박음. v2 에서 시군구 편차 · 유입 보정계수 컬럼 추가.

## §6. 이 판 뛰기 순서 (다른 방 §2 마감 뒤)

1. 다른 방 P2 배포 도장 확인 (`veo-platform main` 에 다음 판 뜸 · `sources.py:_PLANNED` 가 실제 로더로 바뀜)
2. 새 가지 (예: `claude/anseo-location-p3`) 로 갈아탐
3. `sources.py` 에 `hira_disease_stats` · `kakao_map_js` 두 행 추가
4. `core/settings.py` 에 `VEO_KAKAO_MAP_JS_KEY` 추가
5. `schemas.py` 에 `PatientEstimatePayload` · `LocationComparePayload` 추가
6. `service.py` 에 `_patient_estimate_of` · `compare_location` 추가
7. `router.py` 에 `/compare` 엔드포인트 · 응답에 `patient_estimate` · `map_provider` 붙임
8. 웹: `RingMapKakao.tsx` · `LocationCompareTab.tsx` 신규 · `LocationTab.tsx` 조건 분기
9. 시험 4벌 (파이썬 2 + 웹 2)
10. `pnpm rwd` 로 화면 관문 (720·960·1100px · 11px 하한 · 표 감싸개) 통과 확인
11. 커밋 · 이 방은 판 안 정함 · 다른 방/사장님 도장 대기

## §7. 4대 규범 (도면 전체에 걸림)

- **판 다르면 비교 금지** — ⓒ 는 같은 `basis_month` (심평원) · 같은 인구 스냅샷 판 위에서만 나란히
- **못 잰 값 «—»** — 인구·유병률·수진율 하나만 없어도 카드 «—» + 어느 자료 없는지 문장 (0 을 그리지 않음 · ADR 0002)
- **의료광고법** — 「추계 환자 수」는 **사장님 뷰 내부 산정치** · 광고에 못 옮김 · 카드 밑줄에 못박음
- **색+글자 병용** — 상태 뱃지·경고는 색만으로 뜻 만들지 않음 (`datasources/page.tsx` 의 `own.warn` 방식 그대로)

## §8. 참고

- 이 방 세션 로그: `docs/session-logs/2026-09-04-s16.md` (이 판)
- 다른 방 조사: `docs/plans/anseo-github-data-inventory.md` §2 (교통·지리·행정)
- 기획안 원본: `docs/plans/anseo-location-analysis-plan.md` §7 (P1·P2·P3 우선순위)
- 벤치마크: `docs/plans/anseo-location-benchmark.md`
- 시뮬 13호: `docs/ANSEO-상권-P3-시뮬레이션.html` (이 판)
- 팀 인물표: `docs/team/에이전트-역할.md`
- 서연 씨 세부 조사: `/tmp/claude-0/.../scratchpad/research.md` (요약은 §2·§3 에 인용)
