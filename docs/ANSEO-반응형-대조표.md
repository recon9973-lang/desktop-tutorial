# ANSEO 반응형 대조표 — PC · 태블릿 · 모바일 전 화면 실측 (2026-09-02)

> 사장님 오더: «전체 화면에서 모바일·태블릿·PC 버전으로 볼 때 각 화면 최적화가 되어 있지 않음.
> 모든 화면을 PC·태블릿·모바일 각각 캡처 후 최적화 방안 마련해서 대조하고 작업».
> 이 문서의 결함은 **전부 이 방이 찍은 PNG 로 본 것**이다. 소스만 읽고 «다르다»고 하지 않는다.
> 반영 판: veo-platform **v0.3.486** (17곳) (가지 `claude/anseo-screen-layout-optimization-ucs22y`, 배포 대기 표 등재 · **미배포**).

## 1. 찍은 방법 (재현 가능)

| 항목 | 값 |
| --- | --- |
| 장치 | `scratchpad/shoot-rwd.mjs` — `apps/web/test/smoke/shoot.mjs` 와 같은 방식(가짜 진단 서버 + `next start` + Playwright). 화면마다 세 폭을 찍고, `scrollWidth > clientWidth` 면 넘친 요소를 적는다 |
| PC | 1440×900 · DPR 1 |
| 태블릿 | 834×1112 · DPR 2 · 터치 |
| 모바일 | 390×844 · DPR 2 · 터치 · `isMobile` |
| 판 | 전: main 35aa51a(0.3.485) 빌드물 · 후: 이 가지(0.3.486) 빌드물 · 어두운 판 |
| 표본 ① | 빈 표본(계약 예시) — 콘솔 24 + 공개 4 = 28화면 × 3폭 = 84장(`/tools/checker` 는 화면이 아니라 404 — 목록에서 뺌) |
| 표본 ② | 덮개판(`fx-data.json`) 8화면 × 3폭 — 대시보드는 **사장님이 보내신 운영 캡처의 값**(차단 6·심각 35·중요 71·경미 203, 켬 언급 70·끔 0/273, 밀린 곳 5, 엔진 끊김 2종 51·30건), AEO·이슈는 저장소 표본(`fixtures-aeo-share.sample.json`·`fixtures-dashboard.sample.json`) |

캡처 원본은 세션 scratchpad 에 있고, 대표 전후 12장을 `docs/screens-반응형/` 에 축소본으로 뒀다.

## 2. 결함표 — 찍어서 본 것 (전 = 0.3.485, 후 = 0.3.486)

| # | 화면 | 폭 | 전 (실측) | 후 (고친 것) | 파일 |
| --- | --- | --- | --- | --- | --- |
| 1 | 대시보드 「AEO 언급 — 검색 켬 vs 끔」 | PC·태블릿·모바일 | 엔진 이름표 다섯(9.67~24.19%)이 14px 안에 겹쳐 **한 글자 얼룩** — 사장님 지적 «중복이 심해서 읽을 수 없는 화면» | 이름표를 `dodge`(순수 함수·시험 4건)로 12단위씩 비키고, 비킨 글자는 가는 선으로 점과 잇는다. 자에 0·50·100% 눈금 | `Infographic.tsx` |
| 2 | 대시보드 「경보 — 열린 이슈」 칩 | PC·태블릿·모바일 | 이름표가 **«차/단»·«진단/밀린/곳/(14일/넘음)»** 처럼 한 글자씩 세로로 부러짐(플렉스 칸이 긴 이름 목록에 밀림). **빨간 바탕에 빨간 글자**([계산] 4.5:1) | `inline-flex`→`block`, 이름표 `nowrap`+경보색·굵게, 본문은 본문색([계산] 14.9:1). 급함은 테두리·이름표·굵은 수가 말한다 | `dashboard/page.tsx`·`dashboard.module.css` |
| 3 | 전 콘솔 화면 전역 메뉴 | 모바일 390 | 「AEO 관측」「운영」 묶음 단추가 **한 글자씩 세로**로 서고 오른쪽으로 81px 넘침 → 모든 콘솔 화면이 가로 스크롤 | ≤31.99rem 에서 메뉴 `flex-wrap` + 묶음 단추 `nowrap` | `ConsoleNav.module.css` |
| 4 | 전 콘솔 화면 머리줄 | 태블릿 834 | 태그라인이 남아 계정 메뉴가 **둘째 줄**로 떨어짐(머리 두 줄) | 태그라인 접는 폭 640px→60rem | `ConsoleNav.module.css` |
| 5 | 업체 등록 `/console/customers/new` | 전 폭 | **상단 메뉴가 없다** — `isCustomerScopePath` 가 `new` 를 거래처 상세로 오인해 전역 줄이 빠짐 | `new` 제외 + 시험 1건 | `ConsoleNav.tsx`·`.test.tsx` |
| 6 | 대시보드 SEO·GEO·AEO 눈금 카드 | 태블릿 834 | 15rem 최소폭이라 **2+1** 로 접히고 셋째 칸 옆이 통째로 빔 | 최소폭 14rem → 셋이 한 줄 | `dashboard.module.css` |
| 7 | 대시보드 슬로프 그림 | 태블릿(한 칸 배치) | viewBox 360 을 카드 폭 780px 로 늘려 **11px 글자가 24px** — 그림이 아니라 글자 더미 | `max-width: 30rem` 가운데 정렬 | `infographic.module.css` |
| 8 | 거래처 상세 AEO 탭 「질문 전체 언급률」 | 태블릿·모바일 | 큰 숫자 **«46.8/7»** 로 두 줄(바탕 `overflow-wrap: anywhere` 가 숫자 안에서 꺾음) | `clamp(2.25rem, 5.5vw, 3.75rem)` + `nowrap` | `mention-share.module.css` |
| 9 | 거래처 목록 표 | 태블릿·모바일 | 열 열 개가 눌려 **«측/정/U/R/L/없/음»** 세로 글자, 390px 는 이름 칸이 한 글자 폭 | `min-width: 56rem` → 감싸개 안에서 가로로 흐름 | `companies.module.css` |
| 10 | 이슈 축×심각도 매트릭스 | 모바일 | 축 이름 **«GE/O»** 꺾임 | `th` nowrap(감싸개가 흐름) | `issues.module.css` |
| 11 | AEO 흐름(1 키워드 조사 → … → 4 결과 보기) | 모바일 | 두 줄로 접히며 **화살표가 줄 끝에 매달림** | ≤40rem 2칸 격자·화살표 접음(번호가 차례) | `aeo-flow.module.css` |
| 12 | 「AI 별 언급 — 몇 번 나왔나」 막대(대시보드·거래처 AEO 탭) | 모바일 | 수 칸(«18/196 (9.18%)»·«이번 관측에서 안 물었습니다»)이 화면 밖으로 **14~56px 넘침** — 좁은 폭 규칙이 `display: contents` 인 `.row` 에 걸려 죽어 있었다 | 열을 격자(`.bars`)로 옮김: 이름 윗줄, 막대·수 아랫줄, 수는 줄바꿈 허용 | `packages/ui …/RatioBars.module.css` |
| 13 | 거래처 표 «측정 URL 없음» | 태블릿 | 세 줄로 꺾여 경고가 낱말 더미로 읽힘 | `nowrap`(표는 감싸개가 흐름) | `companies.module.css` |
| 14 | 거래처 AEO 탭 「저장된 집합」 상자 | 모바일 | 최소폭 340px 고정이라 칸보다 넓어 **28px 넘침** | `minmax(min(340px, 100%), 1fr)` | `geo.module.css` |
| 15 | 거래처 AEO 탭 「회차별 언급률 변화」 그림 | 모바일 | 오른쪽 계열 이름표가 그림 밖(`overflow: visible`)으로 그려져 **20px 넘침** | ≤40rem 이름표 접고 그림을 칸 안에(위 순위 목록이 같은 이름·값을 말함) | `mention-share.module.css` |
| 16 | 거래처 AEO 탭 「언급 현황 — 우리 대 타사」 순위 줄 | 모바일 | 이름 10rem·값 6rem 고정 칸이 카드 안폭을 넘겨 값이 **11px 넘침** | ≤40rem 번호·이름·값 윗줄, 막대 아랫줄 | `mention-share.module.css` |
| 17 | 거래처 AEO 탭 「추천 위치」·「실행 가능 노출」 카드 | 모바일 | 짝 격자 최소폭 20rem(320px)이 칸보다 넓어 **20px 넘침** | `minmax(min(20rem, 100%), 1fr)` | `geo.module.css` |

### 전후 축소본 (`docs/screens-반응형/`)

| 파일 | 무엇 |
| --- | --- |
| `01-dashboard-pc-slope-alert.png` | #1 슬로프 이름표 · #2 경보 칩 (PC 오른쪽 기둥) |
| `02-dashboard-mobile-nav.png` | #3 모바일 전역 메뉴 |
| `03-dashboard-tablet-header.png` | #4 태블릿 머리줄 한 줄 |
| `04-dashboard-tablet-scales.png` | #6 눈금 카드 3열 · #7 슬로프 최대폭 |
| `05-customers-tablet-table.png` | #9 거래처 표 가로 흐름(+경고 한 줄) |
| `06-aeo-tablet-hero.png` | #8 언급률 큰 숫자 |
| `07-customers-new-pc-header.png` | #5 업체 등록 머리줄 |
| `08-aeo-mobile-ratiobars.png` | #12 「AI 별 언급」 막대 모바일 |

### 고치지 않고 기록만 한 것

| 화면 | 폭 | 관찰 | 왜 안 고쳤나 |
| --- | --- | --- | --- |
| 대시보드 「거래처 지도」 산점도 | 전 폭 | 아홉 점의 이름이 한 자리에 겹침 | 점이 같은 좌표(표본 값) — 자료 성질. 실측 값이 퍼지면 안 겹친다. 이름표 밀어내기를 산점도에도 넣으려면 2차원이라 별도 판 |
| 대시보드 왼쪽 카드 아래 빈 자리 | PC | 오른쪽 기둥(슬로프+경보)이 길어 왼쪽 산점도 카드 아래가 빔 | `dashboard-layout.test.ts §1-1 지도·경보의 아래가 같은 줄` 관문이 `stretch` 를 요구 — 사장님 주문 2026-08-21 |
| 거래처 상세 진단 탭 | PC·태블릿 | AEO 카드 하나만 서고 옆이 빔 | RESUME 미판정 유지 — 정본(Lovable) 배치를 보고 판단 |
| 「AI 별 누적 답변」 띠 | 모바일 | 세 줄로 접힘 | 감추지 않는 것이 규칙(엔진 7종 전부 선다). 가로 스크롤로 바꾸면 뒤 엔진이 안 보인다 |
| `/results/[token]` 공유 화면 | 전 폭 | 흰 바탕 | 공개 공유면은 밝은 판이 정본(«흰 종이») |

## 3. 화면별 판정 (28화면 × 3폭)

빈 표본으로 찍은 84장 가운데 **가로 넘침이 잡힌 것은 모바일 대시보드 하나**(전역 메뉴 #3 — 후 판에서 0). 나머지 27화면은 세 폭 다 한 기둥으로 접히고 넘치지 않는다. 데이터가 차야 보이는 결함(#1·2·6~17)은 덮개판에서 잡았다.

| 화면 | PC | 태블릿 | 모바일 | 비고 |
| --- | --- | --- | --- | --- |
| /console/dashboard | #1·#2 → 고침 | #4·#6·#7 → 고침 | #3·#12 → 고침 | 덮개판 실측 |
| /console/customers | 양호 | #4·#9·#13 → 고침 | #3·#9 → 고침 | |
| /console/customers/[id] (진단·SEO·GEO·AEO·콘텐츠·이슈·리포트 탭) | 양호 | #8 → 고침 | #8·#12·#14~#17 → 고침 · 탭 줄은 가로 스크롤(기존 규칙) | 거래처 줄은 폭마다 접힘 확인 |
| /console/customers/new · projects · [id]/edit · journey | #5 → 고침(new) | 양호 | 양호 | edit·journey 는 표본 없어 404 확인만 |
| /console/issues · issues/[id] | 양호 | 양호 | #10 → 고침 | |
| /console/geo | 양호 | 양호 | #11 → 고침 | |
| /console/reports · [id] · [id]/[v] | 양호 | 양호 | 양호 | 발행본은 표본 없어 빈판 |
| /console/review · keywords · medical · competitors · seo | 양호 | 양호 | #3 → 고침 | |
| /console/usage · team · account · credentials · scoring-versions · changelog | 양호 | 양호 | #3 → 고침 · changelog 는 모바일 74,817px(전 판 이력 — 길이는 자료) | |
| / (로그인) · /bot · /invite · /results | 양호 | 양호 | 양호 | 공개면은 메뉴가 달라 #3 무관 |

## 4. 검사 (veo-platform · 이 가지)

```
tsc --noEmit     통과
eslint           0 오류 · 1 경고(기존, layout.tsx 서체 링크)
vitest           web 244 파일 2,159 통과(dodge 4건 · isCustomerScopePath 1건 추가) · ui RatioBars 8 통과
next build       통과 · pnpm smoke 통과
```

## 5. 다음

- 배포는 **사장님 확인 후** — veo-platform `docs/WORKLIST.md` 배포 대기 표에 0.3.485(ANSEO 방)·0.3.486(이 판) 이 쌓여 있다.
- 2차 후보(오더 받으면): 산점도 이름표 밀어내기 · 거래처 표를 모바일에서 카드형으로 · 「AI 별 누적 답변」 띠를 모바일에서 접기 단추로.
