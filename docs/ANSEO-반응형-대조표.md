# ANSEO 반응형 대조표 — PC · 태블릿 · 모바일 전 화면 실측 (2026-09-02)

> 사장님 오더: «전체 화면에서 모바일·태블릿·PC 버전으로 볼 때 각 화면 최적화가 되어 있지 않음.
> 모든 화면을 PC·태블릿·모바일 각각 캡처 후 최적화 방안 마련해서 대조하고 작업».
> 이 문서의 결함은 **전부 이 방이 찍은 PNG 로 본 것**이다. 소스만 읽고 «다르다»고 하지 않는다.
> 반영 판: veo-platform **v0.3.488** (17곳 · 운영 도달 [실측 2026-09-03 04:03 KST]) → 2차 **v0.3.489** (8곳 · §6 · 가지 `claude/anseo-screen-rwd-0.3.489` · **미배포**).

## 1. 찍은 방법 (재현 가능)

| 항목 | 값 |
| --- | --- |
| 장치 | `scratchpad/shoot-rwd.mjs` — `apps/web/test/smoke/shoot.mjs` 와 같은 방식(가짜 진단 서버 + `next start` + Playwright). 화면마다 세 폭을 찍고, `scrollWidth > clientWidth` 면 넘친 요소를 적는다 |
| PC | 1440×900 · DPR 1 |
| 태블릿 | 834×1112 · DPR 2 · 터치 |
| 모바일 | 390×844 · DPR 2 · 터치 · `isMobile` |
| 판 | 전: main 35aa51a(0.3.485) 빌드물 · 후: 이 가지(0.3.488) 빌드물 · 어두운 판 |
| 표본 ① | 빈 표본(계약 예시) — 콘솔 24 + 공개 4 = 28화면 × 3폭 = 84장(`/tools/checker` 는 화면이 아니라 404 — 목록에서 뺌) |
| 표본 ② | 덮개판(`fx-data.json`) 8화면 × 3폭 — 대시보드는 **사장님이 보내신 운영 캡처의 값**(차단 6·심각 35·중요 71·경미 203, 켬 언급 70·끔 0/273, 밀린 곳 5, 엔진 끊김 2종 51·30건), AEO·이슈는 저장소 표본(`fixtures-aeo-share.sample.json`·`fixtures-dashboard.sample.json`) |

캡처 원본은 세션 scratchpad 에 있고, 대표 전후 12장을 `docs/screens-반응형/` 에 축소본으로 뒀다.

## 2. 결함표 — 찍어서 본 것 (전 = 0.3.485, 후 = 0.3.488)

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

- 배포는 **사장님 확인 후** — veo-platform `docs/WORKLIST.md` 배포 대기 표에 0.3.485(ANSEO 방)·0.3.488(이 판) 이 쌓여 있다.
- 2차 후보(오더 받으면): 산점도 이름표 밀어내기 · 거래처 표를 모바일에서 카드형으로 · 「AI 별 누적 답변」 띠를 모바일에서 접기 단추로.

## 6. 2차 전수조사 (2026-09-03 · 0.3.488 빌드 → v0.3.489)

> 사장님 오더: «pc 테블릿 모바일 버전 자체 시뮬레이션으로 오류 및 디자인 개선 사항 폰트 위치 등 매끄럽게 적용됐는지 전수조사».

### 6-1. 잰 방법 — 1차와 달라진 것

| 항목 | 값 |
| --- | --- |
| 판 | main `c03246ac`(0.3.488 코드 그대로) 빌드물 · 어두운 판 · 덮개판 `fx-data.json` |
| 표본 | 콘솔 24 + 공개 4 = 28화면 × 3폭 = **87장**(`/tools/checker` 는 이 판에 없는 주소 — 목록에서 뺌) |
| 글꼴 | 구글 서체 3벌(Bricolage Grotesque·Inter Tight·JetBrains Mono)을 미리 받아 브라우저에 되돌려 줌 — **운영과 같은 글꼴**로 잼(1차는 샌드박스가 막아 대체 글꼴이었다) |
| 자동 측정 | 넘침 · 글자 겹침(인라인은 줄상자 단위) · 잘림 · 말줄임 · 세로 쌓임(안쪽 여백 뺀 높이) · 카드 밖 탈출 · 11px 미만 글자 · 28px 미만 누름 영역 · 브라우저 오류/요청 실패 |
| 눈 검토 | 29화면 3폭 나란히 시트 + 3000px 넘는 화면은 이어 시트(대시보드 4장) |

### 6-2. 결함표 (전 = 0.3.488 실측, 후 = 0.3.489)

| # | 화면 | 폭 | 전 (실측) | 후 (고친 것) | 파일 |
| --- | --- | --- | --- | --- | --- |
| 18 | `/console/customers` | PC·태블릿·모바일 | **React #418(hydration 불일치)** — 화면이 뜬 뒤 통째로 다시 그려짐. 개발 서버 콘솔엔 안 뜸 | 표 AEO 칸 `AeoStageCell` 이 `<td>` 안에서 또 `<td>` 를 쳐서 브라우저 DOM(`<td></td><td>…`)과 React 트리가 어긋났다 → 속만 돌려주게. 찾은 법: 외부 스크립트 막고 연 DOM ↔ hydration 뒤 DOM 을 태그·글자만 남겨 diff. 같은 길의 `Sparkline`·`TrendChart`·`MultiTrendChart` 그라데이션 id(전역 순번 — 서버는 누적·브라우저는 1부터)도 내용 해시·`useId` 로 | `customers/page.tsx` · `packages/ui` Sparkline·TrendChart·MultiTrendChart |
| 19 | 대시보드 「거래처」 4칸 카드 | PC 1440 | 점수 **«67.85» → «67.»** 로 잘리고 화살표가 카드 밖 **88px**(자동 측정 escape 11건) | 격자 안에서는 좁은 화면 규칙(이름 위 · 값 오른쪽 · 사정 아래) + 화살표 접음 | `dashboard.module.css` |
| 20 | 대시보드 「거래처 지도 — SEO × GEO」 | PC·태블릿 | 아홉 점이 SEO 52~77·GEO 45~65 에 몰려 **이름·값 열여덟 줄이 한 덩어리**(overlap 7쌍) | `dodge` 로 세로 밀어내기(이름표마다 26px 띠) + 가리킴 선 + 점 먼저·글자 나중(halo) + 점이 넘치면 값 줄 접기. 시험 2건 | `Infographic.tsx` |
| 21 | 대시보드 「SEO 평균 추이 — 12주」 | PC | 첫 값 48.00 이 오르는 선 위에, 끝값 60.10 이 끝점 위에 앉음 | 값 자리 위아래 16px 확보 + 선 방향(오르면 첫 값 아래·끝값 위)으로 자리 선택 | `packages/ui …/Sparkline.tsx` |
| 22 | `/results/[token]` 만료 화면 | 전 폭 | 제목 **«이 공유 링크는 만료되었거나…»** 가 종이 톤 위에서 안 보임(body 의 흰 글자를 상속) | 종이 래퍼가 글자색을 다시 잰다 | `results/[token]/layout.tsx` |
| 23 | 콘솔 안 없는 주소 3곳 | 전 폭 | 영문 Next 기본 **«404 This page could not be found.»** 가 콘솔 껍데기 안에 섬 | `(console)/console/not-found.tsx` — 「이 주소에는 화면이 없습니다」 + 대시보드 길 | `not-found.tsx` |
| 24 | 10px 글자 셋 | 전 폭 | 「측정 전」 칩 10px · 태그라인 10px · 표 등급 칩 점수 10.08px | 11px 하한(`max(0.72em, 11px)`) | `EngineTotalsStrip.module.css`·`ConsoleNav.module.css`·`GradeChip.module.css` |
| 25 | 누름 영역 | 태블릿·모바일 | 도움말 「?」 **21×21** · 길잡이 링크 **높이 17px** | 가짜 요소·세로 안쪽 여백으로 24px 이상(보이는 크기 그대로) | `PageHelp.module.css`·`Breadcrumb.module.css` |

**오탐으로 가른 것**(자동 측정이 잡았으나 결함 아님): 인라인 요소가 줄바꿈될 때 bounding box 가 두 줄을 덮어 겹침으로 잡힘(사용량 화면 `strong` 둘 · 거래처 이름 링크 ↔ 차단 칩) → 줄상자 단위로 고침 · 내비 「이슈」 2줄(안쪽 여백 포함 높이) · `Avatar.name`·`srOnly`(낭독기용 숨김) · 회전한 축 이름 · 「☆」 고정 단추 높이.

**안 고친 것**: 아이브로우 0.65rem(10.4px) — 정본 공식 그대로 · 발 판 버전 링크 15px(본문 속 인라인) · 모바일에서 SVG 째로 줄어드는 슬로프·추이 글자(그림 폭에 비례 — 값은 옆 글로 있다) · 연기 시험(`pnpm smoke`)은 HTML 만 보므로 hydration 오류를 못 잡는다(브라우저 관문은 다음 후보).

### 6-3. 후 실측 (0.3.489 빌드 · 같은 장치)

- `/console/customers` 세 폭: **pageerror 0**(전 3/3). 새 서버 첫 요청·둘째 요청 모두 오류 없음.
- 대시보드·거래처·사용량·이슈·404·만료 화면 24장: escape 0 · overlap 0 · clipped 0(전 escape 11 · overlap 21 · clipped 63 중 진짜 결함분 전부 해소).
- 전후 축소본: `docs/screens-반응형/09~16`.

### 6-4. 검사 (veo-platform 가지 `claude/anseo-screen-rwd-0.3.489`)

```
pnpm -r typecheck   통과
pnpm -r lint        통과(경고 1 — 기존 layout.tsx 서체 링크)
pnpm -r test        web 244 파일 2,162 통과(산점도 2건·스파크라인 id 2건 추가) · ui 343 통과
next build          통과 · pnpm smoke 24화면 통과 · 커밋 `ffd2a411`(원격 푸시)
```

## 7. 새 화면도 같은 규칙으로 (2026-09-03 · v0.3.490)

> 사장님 오더: «새로 추가되는 것도 바뀐 화면 구성에 맞게 추가될 수 있도록 조치되는지 확인».

### 7-1. 확인 결과 — 절반만 자동이었다

| 저절로 따라오는 것 | 따라오지 않던 것(관문 없음) |
| --- | --- |
| 콘솔 껍데기(상단 메뉴·테마, 좁은 폭 3단) | 접는 폭 기준 — 파일마다 640·720·860·900·960·1100px·rem 제각각 |
| 공용 쪽 틀 `styles/page.module.css`(제목·설명·표 스크롤 틀·640px 접기) | 표·카드 — 화면마다 자기 CSS, 표 20곳 중 3곳은 좁은 폭 규칙 0 |
| 공용 부품(도움말 ?·등급 칩·길잡이·추이 그림 3종) 안에 든 고침 | 글자 11px 하한 — 코드에 11px 미만 선언 30곳 안팎(안 뜬 상태라 촬영에 안 걸림) |
| 연기 시험 화면 목록 = 빌드 산출에서 자동(HTML 만) | 누름 영역 24px · hydration 오류(#18 종류) · 새 화면 규칙 문서 |
| 저장소 전체 훑기 관문 7종(클래스·토큰·대비·그림 높이·설명 60자·창구↔화면·상자) | |

### 7-2. 조치 (veo-platform 가지 `claude/anseo-screen-guards-0.3.490` · 커밋 `e8a05eeb` + `a90626f7`)

| # | 조치 | 어떻게 |
| --- | --- | --- |
| 1 | 관문 `text-is-at-least-11px` | `apps/web/src` + `packages/ui/src` CSS 의 `font-size` 를 px 환산, 11px 미만은 파일별 BASELINE 개수 그대로(늘면 실패·줄면 숫자를 내린다). 아이브로우 0.65rem 은 정본이라 BASELINE |
| 2 | 관문 `breakpoints-are-shared` | `@media` 폭은 **720 · 960 · 1100px** 세 단. 그 밖(640·900·rem)은 BASELINE — 손대는 파일부터 옮긴다 |
| 3 | 관문 `tables-fold-on-narrow-screens` | `<table>` 그리는 파일마다 `overflow-x: auto` 틀(공용 `tableWrap` 포함) 필수. 이슈·채점판 표는 [실측 390px 넘침 0] 이유와 함께 예외 |
| 4 | 촬영·측정 장치 `pnpm rwd` | s15 scratchpad 장치를 `apps/web/test/rwd/`(audit-rwd.mjs + fixture.json)로. 경로·Playwright 탐색·글꼴 되돌림 저장소 기준. `::before` 로 넓힌 누름 영역을 센다(후속 커밋). CI 밖 — 판 내기 전 손으로 |
| 5 | 문서 `docs/design/2026-09-03-SCREEN-RULES.md` | 새 화면 한 쪽 규칙(틀·폭 3단·글자·누름·표·hydration·촬영·관문 목록) |

### 7-3. 검사

```
pnpm typecheck 통과 · pnpm lint 통과(기존 경고 1) · pnpm test 247 파일 2,171 통과(관문 3 파일 9건 추가)
pnpm rwd 실행 확인: 모바일 /console/customers·/console/dashboard, 태블릿 /console/customers —
  넘침 0 · 겹침 0 · 잘림 0 · pageerror 0. 남는 표시는 아이브로우 10.4px(정본)·메뉴 화살표 9px·
  표 안 이름 링크 높이 15px(2차에서 둔 것)·구글 서체 요청 실패(샌드박스, 글꼴 폴더 없이 돌림)
```

(아래 7-4 로 판 번호가 0.3.494~0.3.495 로 물렸다.)

### 7-4. 예외 줄임 · 판 번호 물림 · 동행 배포 (2026-09-03 · s17)

사장님 오더 «남은 작업 있는지 확인하고 이어서 진행, 작업 완료되면 배포 준비하고 다른 방 배포 시작되면 같이 배포».

**남은 작업으로 잡은 것과 한 것** (veo-platform 커밋 `42e02881`, 0.3.490 안에):

| # | 무엇 | 전 | 후 |
| --- | --- | --- | --- |
| 1 | 접는 폭 예외 | `640px` 8곳 · `900px` 5곳 (BASELINE 19 파일) | 720·960 으로. BASELINE 11 파일(남은 것: geo 방 파일·메뉴 rem 값·1240·760·700·860·600·48rem·min-width 둘) |
| 2 | 상단 메뉴 화살표 | 9px (BASELINE 1) | 11px (BASELINE 0) |
| 3 | 누름 영역 | 거래처 표 이름 링크 15px · 이슈 수 19×16 · 고정 ☆ 22×24 · 고르기 원형 18 / 그림 이름 링크 14~15 / 대시보드 「보기 →」 19~20 · 사용량 링크 14 / 발 판 버전 링크 15 | 전부 24px 이상 — 가짜 요소 `inset` 음수(보이는 크기 그대로), 원형만 1.5rem |
| 4 | 장치 누름 기준 | 28px 미만 | 24px 미만 — 규칙 문서 §3·WCAG 2.5.8 과 같은 값으로 |

[실측 2026-09-03 · `pnpm rwd` · 390·834px] 거래처·대시보드: 넘침 0 · 겹침 0 · 잘림 0 · 탈출 0 · 누름 0 · pageerror 0.
전 화면 56장(모바일·태블릿 × 28): 넘침 0 · 겹침 0 · 잘림 0 · 탈출 0 · pageerror 0. 남는 누름 표시 17곳/폭 —
빈 상태 「대시보드로 가기」 19px · 이슈 제목 링크 23px · 「키워드 조사」·「JourneyMap 열기」 15px · 사용량 체크 13px ·
`/bot` 메일 링크 16px(다음 후보 — 이 판엔 안 넣음, 배포 동행이 먼저).

**판 번호 물림.** ANSEO 방이 0.3.489~0.3.493 다섯 판을 12:47 UTC 후보 가지에 올려(CI run 33757207550 초록 →
main `181f02a3`) 규칙대로 이 방 두 판이 **0.3.494(2차)·0.3.495(관문)** 로 물렸다. 겹친 파일은 판 문자열·계약 문서·
changelog·대장·HISTORY 다섯뿐 — 그 방 판 위에 이 방 파일 34개를 얹었다(가지 `claude/anseo-screen-guards-0.3.495`, 커밋 `b6ad8242`).

**관문이 첫 손님을 잡았다.** 합친 나무에서 `tables-fold-on-narrow-screens` 가 그 방 새 표 네 곳(ContentGapMap ·
PublishLedger · StandingCard · mine/page)을 잡았다 — `styles.tableFlow` 가 page.module.css 에 없는 이름이라 틀이 안 씌워지고
있었다(다른 모듈의 같은 이름을 옮겨 적은 무늬). 공용 `styles.tableWrap` 으로 한 낱말씩 바로잡았다. 관문이 없었으면
그대로 나갔을 표다.

**배포(동행).** 후보 가지 `b6ad8242` 푸시 13:05 UTC → CI → main → 삼중 실측 → 아래 도장.

