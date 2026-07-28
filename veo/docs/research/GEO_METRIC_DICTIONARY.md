# GEO 측정 지표 사전

## 1. GEO 준비도(정적·기술 진단)

| 지표 | 정의 | 증거 |
|---|---|---|
| AI crawler accessibility | robots, HTTP 상태, WAF/CDN, 인증, 렌더링이 지정 봇 접근을 허용하는지 | 실제 요청·로그 |
| Search eligibility | 색인 가능성, canonical, noindex, snippet controls, 주요 검색엔진 상태 | URL 검사/API |
| Extractability | 핵심 답변·주장·표·목록이 독립 문맥으로 추출 가능한지 | DOM/본문 분석 |
| Evidence density | 중요한 주장에 검증 가능한 출처·날짜·작성자·방법이 연결되는지 | 페이지 분석 |
| Entity clarity | 조직·제품·인물·지역의 명칭과 관계가 모호하지 않은지 | 페이지+외부 출처 |
| Structured data validity | 보이는 콘텐츠와 일치하는 유효 schema가 있는지 | 파서/검증기 |
| Freshness signals | published/modified, 변경 내용, sitemap lastmod 등이 신뢰 가능한지 | 페이지+사이트맵 |
| Source consistency | 자사 사이트·공식 프로필·주요 외부 출처 간 핵심 사실 일치 | 교차 출처 |

## 2. 관측 AI 가시성

| 지표 | 권장 산식 |
|---|---|
| Mention rate | 브랜드가 1회 이상 언급된 실행 수 / 전체 유효 실행 수 |
| Citation rate | 자사 도메인이 1회 이상 인용된 실행 수 / 전체 유효 실행 수 |
| Prompt coverage | 한 번 이상 언급/인용된 고유 프롬프트 수 / 전체 프롬프트 수 |
| Citation share of voice | 자사 인용 수 / 선택한 경쟁군 전체 인용 수 |
| Mention share of voice | 자사 언급 응답 수 / 경쟁군 전체 언급 응답 수 |
| Weighted visibility | 프롬프트 중요도 × 엔진 중요도 × 언급/인용 결과의 가중 평균 |
| Source diversity | 자사를 뒷받침하며 인용된 고유 도메인·URL·콘텐츠 유형 수 |
| Stability | 동일 조건 반복 실행에서 결과가 유지되는 비율 또는 변동계수 |

한 응답에 같은 브랜드가 여러 번 나와도 `mention event`는 1회로 세는 것이 중복 부풀림을 줄인다. 원시 언급 횟수는 별도 보조 지표로 저장한다.

## 3. 답변 품질·브랜드 위험

| 지표 | 판정 질문 |
|---|---|
| Claim accuracy | 브랜드에 관한 핵심 주장이 공식 사실과 일치하는가? |
| Citation entailment | 인용 출처가 해당 문장을 실제로 뒷받침하는가? |
| Citation completeness | 검증이 필요한 주요 주장에 출처가 붙는가? |
| Entity disambiguation | 동명 브랜드·제품·지점을 혼동하지 않는가? |
| Recommendation inclusion | 추천/비교 목록에 포함되는가? |
| Sentiment | 긍정·중립·부정과 그 근거는 무엇인가? |
| Staleness | 가격·기능·주소·정책 등 시간 민감 정보가 오래됐는가? |

## 4. 사업 성과

- AI 추천 링크의 세션·사용자·전환(UTM/referrer 기반)
- AI 유입 보조 전환과 신규 고객 비율
- 브랜드 검색량·직접 방문의 변화(인과관계로 단정하지 않음)
- 노출 개선 작업의 비용, 수정 소요, 재검증 성공률

## 5. 금지해야 할 표현

- “이 점수면 ChatGPT 1위”
- “스키마를 넣으면 인용 보장”
- “한 번의 질문 결과가 시장 점유율”
- “인용 수가 곧 답변 내 순위·권위”
- 측정 엔진·모델·날짜·지역·표본을 숨긴 단일 점수
