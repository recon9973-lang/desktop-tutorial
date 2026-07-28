# SEO 진단 제품 권장 점수 모델 v0.1

## 설계 원칙

하나의 “순위 점수”를 만들지 말고 기술 준비도, 검색엔진별 준비도, 검색 성과를 분리합니다. 기본 종합 점수는 사이트가 검색엔진에 발견·해석·제공될 기술적 준비가 되어 있는지를 나타내며 실제 순위 예측값이 아닙니다.

## 권장 카테고리와 가중치

| 카테고리 | 가중치 | 대표 측정값 |
|---|---:|---|
| Crawl & Indexability | 25 | robots, noindex, 상태코드, sitemap, canonical, redirect chain, orphan URL |
| On-page Semantics | 15 | title, description, H1, headings, lang, alt, anchor text, duplicate metadata |
| Content & Information Architecture | 15 | 중복/박약 콘텐츠 신호, 내부 링크 깊이, topic cluster, pagination, breadcrumb |
| Performance & UX | 15 | LCP, INP/대체 lab TBT, CLS, FCP, mobile viewport, HTTPS |
| Structured Data | 10 | JSON-LD 유효성, 필수/권장 속성, Google/Naver 지원 유형 |
| Search Engine Integration | 10 | GSC 소유권·데이터, Naver 등록·IndexNow, sitemap 제출과 처리 상태 |
| Observability & Outcomes | 5 | 노출, 클릭, CTR, 평균 순위, 색인 커버리지 추세, 데이터 신선도 |
| Off-page & Entity Signals | 5 | 참조 도메인, 브랜드 일관성, 연관 채널, 스팸 위험 신호 |

총합 100점입니다. Google, Naver, AEO/GEO 점수는 별도 프로필로 계산하고 종합 점수 옆에 나란히 보여주는 것을 권장합니다.

## 계산법

각 검사 항목 `i`의 점수는 0–1 사이로 정규화합니다.

```text
coverage_i = 영향받은 중요도 가중 URL / 검사 대상 중요도 가중 URL
penalty_i = severity_i × coverage_i × confidence_i
category_score = 100 × max(0, 1 - Σ penalty_i / category_budget)
overall_score = Σ(category_score × category_weight)
```

권장 심각도 계수:

- Blocker: 1.00
- Critical: 0.60
- Major: 0.30
- Minor: 0.10
- Info: 0.00

`confidence_i`는 직접 관측 1.0, API 기반 0.9, 휴리스틱 0.5–0.8, 외부 추정 0.3–0.6처럼 근거 수준을 반영합니다.

## 사이트 전역 차단 규칙

평균만 사용하면 치명적 오류가 가려지므로 점수 상한을 둡니다.

| 조건 | 종합 점수 상한 |
|---|---:|
| 홈페이지 또는 전체 사이트가 robots/noindex로 차단 | 25 |
| 주요 템플릿이 5xx 또는 렌더링 불가 | 35 |
| canonical이 다른 도메인으로 대량 지정 | 40 |
| sitemap의 과반이 비정상/비색인 가능 URL | 55 |
| HTTPS 또는 모바일 접근에 중대한 실패 | 60 |

상한 적용 사실은 점수 옆에 명시하고, 문제를 해결하면 자동 해제해야 합니다.

## URL 중요도 가중치

- 핵심 전환·대표 페이지: 3.0
- 카테고리·허브 페이지: 2.0
- 일반 콘텐츠/상품 페이지: 1.0
- 태그·필터·보조 페이지: 0.5
- noindex가 의도된 페이지: 관련 검사 분모에서 제외

중요도는 sitemap priority에만 의존하지 말고 내부 링크, 트래픽, 전환, URL 패턴과 사용자 설정을 함께 사용합니다.

## 점수 외에 반드시 보여줄 값

- 영향받은 URL 수와 비율
- 이슈별 예시 URL과 검출 근거
- 데이터 소스, 실행 시각, crawler/user-agent, 모바일/데스크톱
- 이전 실행 대비 신규·해결·재발 이슈
- Google/Naver 공식 요구사항 링크
- 순위 영향의 확실성: 직접/강한 근거/간접/추정

## 점수 구간

- 90–100: Ready — 치명적 장애 없음, 잔여 개선 중심
- 75–89: Good — 주요 템플릿 일부 개선 필요
- 50–74: At risk — 색인·품질에 영향을 줄 수 있는 문제가 넓게 존재
- 25–49: Poor — 주요 기술 장애 또는 광범위한 오류
- 0–24: Blocked — 발견·크롤링·색인에 치명적 차단 가능성

구간명은 검색 순위 수준이 아니라 진단 준비도임을 UI에 표시합니다.

