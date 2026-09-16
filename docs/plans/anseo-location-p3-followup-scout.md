# §7 P3 · 정찰 뒤 미결 세 자리 (2026-09-16 · 잠결 세션이 남기는 것)

> **이 문서의 뜻**. s16 (2026-09-04) 이후 이 방을 열이틀 자던 어시스턴트 세션이
> 2026-09-16 owner 트리거로 깨어나 확인해 보니, 이 방의 실제 진행은 다른 세션 (`013F…`)
> 손으로 **s22 (2026-09-09)** 까지 나갔다. s16 P3 도면 (`anseo-location-p3-plan.md`)
> 은 그대로 남아 있으나, 그 사이 코드가 훨씬 앞으로 달렸다. 정찰 요원 준서(Explore)가
> 잠결 세션 요청으로 현재 코드를 훑어 **s22 시점에도 여전히 유효한 미결 세 자리**를 짚었다.
>
> **결정 권한 없음.** 이 문서는 참고 · 다음 세션 (또는 사장님) 이 s16 P3 도면을 다듬을 때 쓴다.
> 값·비밀은 넣지 않는다.

## 준서가 본 현재 상태 (veo-platform · `origin/main` = `c9ecf707` 기준)

### 이미 나간 것
- `apps/api/src/veo/location/sources.py` — 실제 로더 함수 여덟 개 이상 심김
  (`_hira_file`·`_hira_api`·`_transport_files`·`_usage_file`·`_population_files`·`_population_age_file`·`_population_points_file`·`_floating_file`·`_move_api`·`_store_api`·`_tour_api`)
- 웹 `LocationTab.tsx` (1746 줄) — 지도가 **카카오 타일**로 바뀜:
  `<KakaoTileMap reading={reading} fallback={<RingMap reading={reading} />} />` (161행).
  같은 폴더 `KakaoTileMap.tsx`·`KakaoTileMap.test.tsx` 존재
- 교통·인구 축 «—» 사라짐 — `Transport`·`Population`·`FloatingPopulation`·`TourVisitors`·`PopulationMoveBlock`·`StoreZone`·`CompetitionList` 등 실제 값 그림
- 「올리기 단추» 이미 심김: `UploadForm.tsx` + `upload-action.ts` (다만 화이트리스트가 `molit_bus_stops`·`molit_subway_stations` 둘로 좁음)

### 여전히 스텁 (`_PLANNED`)
- `sgis_boundary` — 행정동 경계 API (반경 방식 인구 셈용 · 지금은 시군구로 우회) · `KEY_MISSING`
- `kakao_geocoding` — 카카오 로컬 지오코딩 (주소→좌표) · `KEY_MISSING`

## 미결 세 자리 (s16 P3 도면과 어긋난 곳)

### ⓐ `kakao_map_js` 원천 표 행이 없다 · **실제 코드 미결**

화면 `KakaoTileMap` 이 이미 카카오 JavaScript SDK 를 소비하는데, `sources.py` 는 `kakao_geocoding` 한 줄만 있고 지도 열쇠용 자리가 없다. 결과 = **SUPER_ADMIN 이 실제로 쓰이는 열쇠를 「데이터 원천」 화면에서 못 잡는다.**

- 붙이는 자리 = `sources.py` `_PLANNED` 튜플에 한 줄 더 (`_planned(key="kakao_map_js", ...)`).
- 혹은 `kakao_geocoding` 행 한 개에 두 용도(지도·지오코딩) 합쳐 표기 — 다만 열쇠 두 종은 실제로 다름 (JS 열쇠 · REST 열쇠) 이라 분리가 맞음.
- 사장님 결정 #15 「카카오맵 열쇠」와 직결. 값은 화면·문서·요약에 새로 뿌리지 않음.

### ⓑ 12칸 `mk-grid` 이미 촘촘 · **추계 환자 수 카드 자리 없음**

`LocationTab.tsx` 의 12칸 그리드가 네 묶음으로 이미 꽉 참:
- 입지·경쟁 = c12 + c12
- 사는 사람 = c6 × 4
- 오가는 사람 = c8 + c4 + c12
- 상권 = c12

s16 P3 도면이 상정한 «추계 환자 수 카드가 앉을 빈 자리» 사실상 없다. 도면 재설계 필요:
- (a) 어느 묶음에 넣을지
- (b) 옆 카드 크기 재분배 (예: `Competition` c12 → c8, 추계 c4)
- (c) 어떤 축 자료로 잴지 (연령 인구 × 진료과 방문율 등)

**«—» 규범 지킴**: 세 축 중 하나라도 없으면 카드 전체 «—»·색+글자 병용 — 이 부분은 s16 도면 그대로.

### ⓒ 이름 충돌 · **«비교» 낱말 이미 AEO 가 씀**

`environment-compare.test.tsx` = 상권이 아니라 **AEO 「환경 대조»** (`CounterfactualCard` · 사본 vs 실검색) 시험. 이름만 겹침. s16 도면의 «비교 모드» 이름은 다른 낱말로 갈아 시험 이름 충돌·화면 라벨 혼선 예방:

- 제안: **«상권 대조»** 또는 **«두 곳 나란히 보기»**
- 라우트 키 `compare` 는 이미 쓰이므로 `align`·`side-by-side` 등으로 회피

## 다음 세션에 넘기는 세 가지

1. **`kakao_map_js` 행 추가** — 사장님 결정 #15 열리는 시점 (열쇠 다시 발급 또는 기존 값 그대로) 에 `sources.py` `_PLANNED` 에 한 줄 · SUPER_ADMIN 화면이 열쇠를 잡게 · 값은 안 담음
2. **s16 P3 도면 재설계** — mk-grid 자리 재분배 + 이름 갈이 (§ⓑ·§ⓒ) — s16 도면 갱신 커밋
3. **`sgis_boundary` 반경 방식** — 스텁 두 개 중 이건 상권 축 정밀도 실질 업. 다음 판에 자연스러움

## 이 세션(잠결·Opus 4.7) 이 손대지 않은 것

- veo-platform 코드 · main 브랜치 · 카카오 열쇠 값 (s16 에 사장님이 넘긴 것) · WORKLIST.md · s22 이후 다른 세션 판단
- 이 파일 하나만 이 방 브랜치에 남김 · 다음 세션 (Opus 5) 참고용

## 참고

- s22 마감 RESUME.md (원격 최신) — 「저쪽이 잠잠할 때 다시」 판단 · 배포 재시도 대기 상태
- s16 P3 도면 `docs/plans/anseo-location-p3-plan.md` (여전히 살아 있음 · s22 시점에는 낡음)
- s16 시뮬 13호 `docs/ANSEO-상권-P3-시뮬레이션.html` (여전히 살아 있음)
- 준서 정찰 세션 tokens: 85,601 · 46 tool_uses · 294 s
