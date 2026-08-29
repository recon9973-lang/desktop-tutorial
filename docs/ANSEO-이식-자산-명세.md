# ANSEO 이식 자산 명세 (v1)

> 이식 프로젝트의 **단일 기준 문서**. 4개 소스(① ANSEO 시안 `c99930c9` HEAD ② CFO 원형 동일 저장소 ref `b0cb2b8` ③ Sales Attribution `6a7cf747` ④ RevOps `cb49243c`)에서 추출한 자산을 5축으로 확정한다.
> 이후 단계는 이 명세만 참조한다: **1** 라인·파이프라인 시뮬레이션 → **2** SEO·GEO 화면 → **3** AEO 화면 → **4** 전체 통합 → **5** 실물 이식.
> 근거 상세는 `ANSEO-콘솔-디자인-워크플로우-인포그래픽-분석.md`(제6~8부), 선행 검증은 `ANSEO-이식-시뮬레이션.html`.
> 표의 «단계» 열 = 그 자산이 처음 투입되는 시뮬레이션 단계.

---

## A. 데이터 (모델·구조) — 화면보다 먼저 옮겨야 하는 것

| # | 자산 | 출처 | 핵심 정의 (그대로 가져갈 값) | 단계 |
|---|---|---|---|---|
| A1 | 판정 4종 + 채점 결과형 | ①`src/lib/scoring-spec.ts` | `Verdict = pass·fail·unknown·not_applicable`. unknown→분모 제외+`unmeasured` 별도 집계, not_applicable→분모 제외. `normalized`는 잴 배점 없으면 **null**(0 아님). `ScorableCheck{area,key,verdict,weight,lost}` | 1 |
| A2 | 관측 칸 + 집계형 | ①`scoring-spec.ts` | `ObservationCell{engineId, mode:on/off, mentioned:bool/null}` — null=못 잼. `AeoSummary{measuredCells, unmeasuredCells, mentions, mentionRate:null허용, byEngine[]}`. `aeoStageFor`: none→draft→published→**measured(잰 칸≥20)** | 1 |
| A3 | 이슈 생애 상태 | ①`repo.ts`·`issue-life` | 상태 5종(open·in_progress·awaiting_rescan·closed·unknown) 중 **사람이 만질 수 있는 것은 `HUMAN_STATES=[open,in_progress,awaiting_rescan]`뿐**. 전 전이는 `issue_events` 감사 행. 승격은 slug 멱등 | 1 |
| A4 | 처분(disposition) 분해 | ④`src/lib/rf/engine.ts` | 단계 진입분 = **advanced + pending(신선 창 안 미완) + dropped(사유 categorical)**. 사유는 고정 목록(prose 금지). «파생이지 작성이 아니다» | 1·3 |
| A5 | 파이프라인 정의 데이터 | ①`src/data/site-map.ts` | `PipelineStage{no,label,question,input,work[],output,screens[],runtime}` + 불변 규칙 5조. **확장: 4(관측)와 5(실행) 사이에 4a 콘텐츠 추출·4b 분석·4c 제안 삽입** | 1 |
| A6 | 브랜드 식별 레코드 | ①`anseo-identity.ts` | 5필드(domain·locality·phone·distinctTerms·aliases)+가중치, status 3종, collisionRisk, pendingMentions. «도메인만 결정적» | 3 |
| A7 | 정체성·원칙 단일 소스 | ①`src/lib/brand.ts` | `MEASUREMENT_PRINCIPLES` 5개조, `NOT_MEASURED="—"`, disclaimer, CHANGELOG 구조 | 1 |
| A8 | 모델 전환 데이터 계약 | ③`data/attribution.ts` 구조 | 전환 대상은 «같은 총량의 다른 절단» — **총합 불변 검증을 데이터 계층에 둔다**(판 전환·필터에 준용) | 2 |
| A9 | 결정적 표본 시드 | ④`rf/data.ts` | mulberry32 고정 시드 — SSR/클라 동일 렌더. 표본은 «최근 주차에 pending 비율 실재» 규율 | 1 |

## B. 기능 (동작 규칙)

| # | 자산 | 출처 | 규칙 | 단계 |
|---|---|---|---|---|
| B1 | 서버 채점 단일화 | ①`diagnosis.functions.ts` | 점수 계산은 서버 함수 한 곳(«화면마다 다른 점수» 금지). zod 검증+인증 미들웨어. 시뮬레이션에서는 «순수 함수 1벌 공유»로 대신 검증 | 1 |
| B2 | 출처 3원 배지 | ①`repo.ts`+`DataBanner` | 화면 데이터 출처를 **db(저장됨)/sample(표본)/spec(명세)**로 항상 표기. 폴백 사실 자체가 정보 | 1 |
| B3 | 재채점·집계 조작부 | ①`rescore.tsx` | «지금 명세로 다시 접기»·«저장된 관측을 다시 세기» 버튼+결과 4칸(환산/받은/직전 대비/판정 못 함) | 2·3 |
| B4 | 등록 검증 | ①`customers.new` | 사설 IP 차단·http 경고·**같은 도메인 수집 상한 450장/시 공유 경고**·브랜드 표기=AEO 분모 필수·«등록은 분모 확정» | 1 |
| B5 | 검수 3판정 | ①`console.review` | 이 고객 맞음/다른 업체/**보류**. 판정 전=«진단 못 함»(언급 안 됨과 합산 금지) | 3 |
| B6 | 자격증명 3상태 | ①`credentials` | 켜짐/열쇠 없음/열쇠가 틀림 + **플레이스홀더=틀림** + 막히는 화면 역링크 | 1 |
| B7 | IA 자리 5종+0-E | ①`navigation.ts` | BRAND/MENU/GROUP/TOOL/ABSORBED + `enteredFrom` 의무(«부를 수 없는 기능은 없는 기능») + industry 게이트 | 1·4 |
| B8 | 발행 불변 | ①리포트 계열 | sha256·버전 고정, 수기 입력 0, 콘솔/공유 단일 컴포넌트(variant) | 4 |
| B9 | what-if 재계산 | ②`HiringDrag` | 입력(스냅 단위)→파생값 실시간 재계산, 경계(구간 진입) 경고. ANSEO 대응: 큐 선택→예상 환산 | 2 |
| B10 | 판 비교 금지 | ①`scoring-versions` | 배점 이동 시 판 간 총점 병렬 비교 차단, 판 체크섬 | 2 |

## C. 디자인 (컴포넌트·토큰)

| # | 자산 | 출처 | 사양 | 단계 |
|---|---|---|---|---|
| C1 | 카드 문법 | ① Panel | eyebrow(자간 .09em)+**질문형 제목**+우측 aside+하단 **오독 방지 각주**. 전 화면 예외 없음 | 1 |
| C2 | 시맨틱 토큰 | ①styles.css | signal(우리/중립)·mint(통과/+)·ember(경고/pending)·destructive(차단/−)·**unknown(못 잼 전용 무채색)**+soft 변형. 검증값(다크): `#5b9dff/#2fd39c/#e9b13e/#ff5d7d/#8b93a3` — CVD·일반분리·대비 PASS(시뮬 v1) | 1 |
| C3 | 타이포 2원 | ①·④ | 본문 산세리프+**전 수치 JetBrains Mono tabular**. 티어: display-figure(페이지당 1개)·section-title·eyebrow | 1 |
| C4 | 빈 값 3종 어휘 | ①전반 | `0`(측정·없음) / `—`(분모 제외) / 점선 칸·빈 마커(판정 못 함). 파생 어휘: **no-credit 점선 슬롯**(③), **maturing 점선+빈 마커+밴드**(④), `defined:false` 선 끊기(④) | 2·3 |
| C5 | 근거 접기+토크나이저 | ①`check-list.tsx` | 판정 근거→실측 코드 조각(정규식 자동 색칠: 태그=signal·값=mint·실패=destructive·주석=ember)→수정 절차+«고치면 +N» | 2 |
| C6 | 채점표 행 | ①SEO/GEO 탭 | 받은/깎인/배점(공통 눈금)/4회차 Sparkline(**천장 점선=배점**)/달성률. LossBar 색=남은 여지 | 2 |
| C7 | 버터플라이 퍼널 | ④`FunnelShape` | 단일 units-per-record 스케일·좌 dropped/우 pending 날개·이유 가닥+«외 N건» 풀링·라벨 3단 배치(내부→축약→레일+리더)·sr-only 표·모바일 동일 frac 칩(제2 기하 금지) | 3 |
| C8 | 고정 길이 레일 | ③`revenue-rail` | 분모 고정 스택, 경계=inset 헤어라인, 라벨 78px 미만 숨김, 툴팁에 타조건 값 병기 | 3 |
| C9 | 분산 워터폴 | ②`VarianceWaterfall` | 앵커+델타 공통 스케일, 증가=바닥/감소=꼭대기 origin, 연결 점선, 해설 출처 점 마커 | 2 |
| C10 | 응답 곡선 산점 | ③`scatter-panel` | 버블=√예산, 실측 실선/외삽 점선, 타깃 점선, 라벨 헤일로(paintOrder), 미해당 항목 각주 행 유지 | 2 |
| C11 | 중앙값 사분면 산점 | ④`ScatterChart` | 중앙값 십자+코너 힌트, **면적 스케일 반경** | 1·4 |
| C12 | 여정 칩 | ③`paths-panel` | 칩+화살표, 조건부 점등(색·테두리·12% 배경), 다색 분할 ShareBar | 3 |
| C13 | 팬 차트+밴드 | ②`CashFanChart` | P10-90/P25-75 이중 밴드+중앙선, 데이터 부족 시 점선 빈 상태 | 4(선택) |
| C14 | 기존 ANSEO 18종 | ①분석 §4 | 도넛(값+% 범례)·와플(회색=못 잼)·히트맵(점선 —·농도>0.55 글자 반전)·롤리팝·덤벨·슬로프·회차 판정 띠·감소 깔때기 등 — 그대로 유지 | 2·3 |

## D. 애니메이션 (타이밍 규격)

| # | 자산 | 출처 | 규격 | 단계 |
|---|---|---|---|---|
| D1 | 카운트업+글라이드 | ②`motion.ts useCountUp` | 최초 0→값 **1400ms ease-out cubic**(하우스 커브), 정착 후 변경은 **현재값→새값 520ms**(리셋 금지) | 1 |
| D2 | 로드 오케스트레이션 | ②`useStage`+①`stage` | 단일 시퀀스: 카드 rise 620ms(cubic-bezier(.22,1,.36,1))+90ms 스태거, 티커 220+110i ms. **정적 상태=보임**(keyframe from만 숨김 — 시뮬 v1 교훈) | 1 |
| D3 | 데이터 보간 전환 | ③`use-transition-snapshot`+`interp` | **720ms ease-in-out cubic, 전 지표 lerp, 전환 중단 시 현 지점 재시작, NaN은 t=.5 스냅**. 값 변경 모션의 기본 전략 | 2 |
| D4 | one-shot 재키잉 | ④`rf-*` | rise 420·open 240·grow 520·draw 720·scale-x 420/380ms(transform-box:fill-box)+날개 스태거 70ms. **모드 전환=animKey 재키잉으로 정확히 1회** — «다른 그림»이 될 때만 사용 | 3 |
| D5 | 워터폴 3층 시차 | ②`VarianceWaterfall` | 막대 scaleY 520ms·i×130ms → 연결선 +140 → 숫자 +240(모두 동일 커브) | 2 |
| D6 | rAF 기하 모프 | ②`SankeyFlow` | collapse 시작 프레임→1150ms(초회)/760ms(전환), easeInOut — 흐름형 그림 전용 | 4(선택) |
| D7 | clip-path 드로잉 | ②`CashFanChart` | inset(0 100% 0 0)→0, **1.5s**+0.15s 지연 — 추이가 «그려지는» 등장 | 2 |
| D8 | reduced-motion 전면 스위치 | 전 소스 공통 | 모든 animation/transition 무효화+dashoffset 강제 0. **필수 동반** | 1 |

## E. 이펙트 (마이크로 인터랙션)

| # | 자산 | 출처 | 규격 | 단계 |
|---|---|---|---|---|
| E1 | 경로 추적 lit/dim | ②④ | opacity 토큰 3단 **rest .62/lit .95/dim .12**(라이트 .72/1/.16 — 테마별 별도 튜닝), 220ms | 3 |
| E2 | 이동 점선 정책 | ②④ | dash 3 26·4.2s linear. **reveal cue이지 실시간 신호 아님** — ②는 정착 6s 후 정지, 호버 경로만 지속 | 3 |
| E3 | 호버 양방향 연동 | ①Donut·RadialBars | 차트 세그먼트↔범례 행 상호 하이라이트(굵기 14→18/디밍 .35) | 2 |
| E4 | 투명 히트 영역 | ①TrendLine·③워터폴 | 작은 점 r=9 투명 원, 좁은 막대 전체 열 히트 — 잡기 쉬움을 기하로 | 2 |
| E5 | 툴팁 표준 | ①chart-tip·③ | 이름+색점 / 주값 / **직전 대비 ±p** 또는 타조건 병기. 터치 대비: E6 | 2 |
| E6 | 입력 수단별 트리거 분리 | ②`KpiStrip` FLIP | hover=마우스 포인터만(pointerType)·focus=`:focus-visible`만·탭=pin 토글 — 셋 독립(터치 잠김·탭 래치 방지). 툴팁 의존 지점의 표준 해법 | 2 |
| E7 | 라벨 자기방어 | ③레일·②생키 | 실측폭<78px 라벨 숨김 / 텍스트 헤일로(stroke=surface, paintOrder) / 배치 엔진(내부→축약→레일+리더, 폭은 과대추정) | 3 |
| E8 | 드래그 핸들 | ②`HiringDrag` | pointer capture+창 단위 move, 스냅 단위 반올림, 드래그 중 scale 1.15+글로우(color-mix 22%), 키보드 ←→/Home/End+aria-valuetext | 2 |
| E9 | 접근성 로빙 커서 | ②`SankeyFlow` | 복잡 다이어그램=탭 스톱 1+`aria-activedescendant`, 화살표가 **흐름을 따라** 이동, sr-only 요약 | 3(퍼널 적용) |

---

## 기각·보류 (이유 명시)

- **생키를 점수에 사용** — 기각. 점수는 보존량이 아니다(3축 합산 금지 원칙과 충돌). 보존량이 성립하는 관측 흐름(질문→엔진→인용 문서)에는 4단계에서 선택 검토(D6·C13과 함께).
- **방사형 동심 아크(RadialBars)** — 보류. 코드의 레이더-기각 논리는 타당하나 반지름 왜곡이 남음. 엔진별 값은 수평 막대+분모 병기로 대체(분석 §7-1).
- **framer-motion 의존(③표 재정렬)** — 시뮬레이션 단계에서는 FLIP 수제 구현으로 대체 검토, 실물 이식 시 라이브러리 채택 여부 결정.

## 단계별 투입 요약

```
1 파이프라인   A1 A2 A3 A4 A5 A7 A9 · B1 B2 B4 B6 B7 · C1 C2 C3 C11 · D1 D2 D8
2 SEO·GEO     A8 · B3 B9 B10 · C4 C5 C6 C9 C10 C14 · D3 D5 D7 · E3 E4 E5 E6 E8
3 AEO         A4 A6 · B3 B5 · C4 C7 C8 C12 C14 · D4 · E1 E2 E7 E9
4 전체 통합    B7 B8 · C13(선택) · D6(선택) + 1~3 전부
5 실물 이식    위 전부 — veo-platform 규약(브랜치·검증·two-words)에 따라
```

---

## 외부 참고 검토 — NXT «SEO 점수 체크» (2026-08-29)

**채택 (v3 반영)**
- **등급제 표기(사장님 규격)**: 100점 만점, A+(95~100)/A(90~94)/B+(85~89)/B(80~84)/C+(75~79)/C(70~74)/D+(65~69)/D(60~64)/E+(55~59)/E(50~54)/F(0~49). **등급을 크게, 점수를 작게.** 적용 위치: 환산 게이지·예상 환산(what-if 등급 전환 표기 «F → E»)·등급 사다리(기존 5구간 대체)·GEO 헤더 배지. 등급 색은 기존 구간 시맨틱 유지(90+ mint / 75+ signal / 50+ ember / 그 외 destructive).

**이관 (해당 단계에서 반영)**
- 키워드 입력+월간 검색량 카드 → 3단계 AEO(키워드 라인)의 입력 UI 참고.
- «SEO 점수 TOP 5» 경쟁 도메인 순위 사이드 카드 → 4단계 전역 화면(경쟁 도메인) 참고.
- 검사 항목 후보: 보안 헤더 4종(HSTS·X-Frame-Options·X-Content-Type-Options·Referrer-Policy)·HTTP/2·Gzip·robots 정책 세분 — 채점 명세 확장 백로그(5단계 실물 이식 시 명세 버전 업으로).

**기각**
- 코드 스니펫 상시 노출 → ANSEO의 접기(근거→코드→수정) 문법이 밀도·스캔성에서 우위. 유지.
- 항목별 전부 초록 체크 나열 → 판정 4종(감점/통과/판정 못 함/해당 없음) 구분이 ANSEO 원칙이라 이진 체크로 축소하지 않음.

---

## 실물 확정 반영 (2026-08-29) — SEO 진단 규모·관리 목표

실물 ANSEO 콘솔 SEO 탭 스크린샷(정사각형의원 · 79.57점 · 명세 1.10.0)으로 확정.

- **SEO 진단 항목 규모 = 배점 49 + 미배점 10 (총 59개).** 시뮬레이션의 표본 12개는 대표치이며,
  이식 시 항목 리스트는 59행 스케일을 전제로 설계한다 — 판정 필터 칩 + 근거 접기(C5)를 유지하고,
  **미배점 항목은 별도 구획**으로 접어 둔다(감점 없이 관측만: 콘솔 연결·제출 상태 등 운영 근거).
  미배점은 판정 4종(감점/통과/판정 못 함/해당 없음)과 다른 제5의 부류다 — 점수 세계 밖에 있으므로
  게이지·구성·워터폴 어디에도 넣지 않는다.
- **진단 이력 목표선 규격(사장님 확정)**: 취약 탈출 **E(50)** + 관리 목표 **A(90)**. 도달 예상은
  현재 판 실측 기울기 기반의 관측값으로만 표기(보장 아님 단서 필수), 반사실(what-if) 카드로 연결.
- 실물 화면에 이미 있는 것 재확인: 날짜별 진단 목록 표·점수 흐름 차트·신뢰도 병기·명세 판 표기 —
  이식 2단계 시뮬레이션의 이력 카드 문법과 정합. 이식 시 실물 데이터 소스에 그대로 연결한다.
