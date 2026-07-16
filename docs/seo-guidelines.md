# SEO 진단 기준 — 공식 가이드 정합화 근거

> 베놈 종합 진단 센터의 **SEO 점수 체크** 도구가 사용하는 평가 항목과, 각 항목의 **공식 출처**를 정리한 근거 문서입니다.
> 구현: `venom-wordpress/preview/index.html` 의 `_renderFastSEO()` / `_runSEOPSI()`.

## 출처 (1차 자료)

- **Google** — [SEO 시작 가이드](https://developers.google.com/search/docs/fundamentals/seo-starter-guide?hl=ko), [How Search Works](https://developers.google.com/search/docs/fundamentals/how-search-works), [Helpful Content](https://developers.google.com/search/docs/fundamentals/creating-helpful-content), [생성형 AI 최적화](https://developers.google.com/search/docs/fundamentals/ai-optimization-guide), [Technical SEO](https://developers.google.com/search/docs/fundamentals/get-started), [URL 구조](https://developers.google.com/search/docs/crawling-indexing/url-structure), [Link 모범사례](https://developers.google.com/search/docs/crawling-indexing/links-crawlable), [Sitemap](https://developers.google.com/search/docs/crawling-indexing/sitemaps/overview)
- **네이버** — [서치어드바이저 SEO 가이드](https://searchadvisor.naver.com/guide)
- **성능(속도)** — Google PageSpeed Insights / Lighthouse (실측, 정밀 분석 시)

## 채점 구조

기본 분석(원본 HTML 파싱, ~1–2초) = **90점 만점**. 정밀 분석(PSI, 선택) 시 속도 10점이 합산되어 **100점 만점**.

| 카테고리 | 배점 | 측정 방식 |
|---|---|---|
| 콘텐츠 & 메타 | 38 | HTML 파싱 |
| 기술 · 크롤링 | 30 | HTML + robots.txt |
| 검색 노출 강화 | 22 | HTML + robots.txt |
| 속도 최적화 | 10 | PSI(Lighthouse) 정밀 분석 |

## 항목별 기준 및 출처

### 콘텐츠 & 메타 (38)
| 항목 | 배점 | 출처 | 규칙 |
|---|---|---|---|
| 제목(title) 태그 | 8 | 공통 | 존재 + **단일**(네이버: 2개+ 감점) + 길이 10~60자 |
| 메타 디스크립션 | 8 | 공통 | 존재 + **단일**(중복 감점) + 길이 50~160자 |
| H1 대표 제목 | 6 | 네이버 | **정확히 1개**(0=없음, 2개+=구조 혼란) |
| 이미지 ALT 텍스트 | 7 | 공통 | 속성 누락만 집계(`alt=""`·추적픽셀 제외), ≤10% 허용 |
| 의미있는 링크 텍스트 | 5 | Google | "여기 클릭"·맨 URL·빈 텍스트 지양, 이미지링크는 alt로 평가 |
| 서술형 URL | 4 | Google | 의미있는 단어, 세션ID·임의ID·과다 파라미터 지양 |

### 기술 · 크롤링 (30)
| 항목 | 배점 | 출처 | 규칙 |
|---|---|---|---|
| HTTPS 보안 연결 | 6 | 공통 | SSL 적용 |
| 검색로봇 수집 허용 | 6 | 공통 | robots.txt가 Googlebot·**Yeti(네이버)**·`*` 차단 안 함 (RFC 9309 그룹 파싱) |
| 인덱싱 허용 | 5 | 공통 | meta robots `noindex` 미설정 |
| Canonical 태그 | 5 | 공통 | 중복 URL 정규화 |
| Viewport(모바일) | 4 | 공통 | 모바일 우선 인덱싱 |
| HTML lang 속성 | 4 | Google | 페이지 언어 명시 |

### 검색 노출 강화 (22)
| 항목 | 배점 | 출처 | 규칙 |
|---|---|---|---|
| 구조화 데이터 | 7 | Google | Schema.org JSON-LD — 리치결과 자격(필수 아님) |
| Open Graph 태그 | 6 | 네이버 | og:title + og:description — 공유 미리보기 |
| sitemap.xml 선언 | 4 | 공통 | robots.txt의 `Sitemap:` 선언 (소규모 사이트는 선택) |
| 파비콘 | 2 | Google | 검색결과 사이트 아이콘 |
| robots.txt 존재 | 3 | 공통 | 수집 규칙 파일 제공 |

### 속도 최적화 (10, PSI 정밀 분석)
성능 점수·텍스트 압축·이미지 최적화·렌더링 차단 — Google Lighthouse 실측 + CrUX 현장 데이터.

## 의도적으로 감점하지 않는 것 (Google이 "중요치 않다"고 명시)

- **헤딩 순서·개수** — "Google 검색 관점에서 순서 무관"(접근성 목적일 뿐)
- **콘텐츠 단어 수** — "길이 자체는 순위와 무관, 마법의 글자 수 없음"
- **키워드 밀도/메타 keywords** — 키워드 스터핑은 스팸 정책 위반
- **구조화 데이터 필수화** — 생성형 AI 검색에 필수 아님(리치결과용 권장일 뿐)
- **llms.txt / AI 전용 마크업** — Google이 사용하지 않음
- **도메인 키워드·TLD·서브도메인 vs 서브디렉터리** — 순위 영향 미미

## 정직성 원칙 (Google 서드파티 도구 가이드)

- 본 진단은 **공식 가이드에 근거한 참고용 휴리스틱**이며, 서드파티 도구는 Google 내부 순위 데이터에 접근할 수 없음.
- **검색 순위를 보장하지 않음.**
- 1차 데이터는 [Google Search Console](https://search.google.com/search-console) · [네이버 서치어드바이저](https://searchadvisor.naver.com)에서 확인 권장.
- JS 렌더링 사이트(SPA)는 원본 HTML이 비어 있으므로, Google이 실제 브라우저로 렌더링하는 **정밀 분석(PSI)**으로 자동 전환.
