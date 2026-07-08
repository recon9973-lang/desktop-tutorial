## 크롤링 및 색인 생성 관련 주제 개요

이 섹션에 포함된 주제에서는 Google 검색 및 기타 Google 서비스에 콘텐츠를 표시하기 위해 콘텐츠를 찾고 파싱하는 Google의 기능을 제어하는 방법과 Google이 사이트의 특정 콘텐츠를 크롤링하지 못하게 하는 방법을 설명합니다.

다음은 각 페이지의 간략한 설명입니다. 크롤링 및 색인 생성에 관한 개요를 보려면 [Google 검색 작동 방식](https://developers.google.com/search/docs/fundamentals/how-search-works?hl=ko) 가이드를 참고하세요.

| 주제 | 주제 |
|-----------------------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| [Google에서 색인을 생성할 수 있는 파일 형식](https://developers.google.com/search/docs/crawling-indexing/indexable-file-types?hl=ko) | Google은 대부분의 페이지 및 파일 형식의 콘텐츠를 색인 생성할 수 있습니다. Google 검색에서 색인을 생성할 수 있는 가장 일반적인 파일 형식 목록을 살펴보세요. |
| [URL 구조](https://developers.google.com/search/docs/crawling-indexing/url-structure?hl=ko) | 콘텐츠를 정리하여 URL을 논리적이고 가장 이해하기 쉬운 방식으로 구성하는 것이 좋습니다. |
| [사이트맵](https://developers.google.com/search/docs/crawling-indexing/sitemaps/overview?hl=ko) | 사이트의 새 페이지 또는 업데이트된 페이지에 관해 Google에 알립니다. |
| 크롤러 관리 | -   [Google에 URL 재크롤링 요청하기](https://developers.google.com/search/docs/crawling-indexing/ask-google-to-recrawl?hl=ko)
-   [속성 탐색 URL 크롤링 관리하기](https://developers.google.com/search/docs/crawling-indexing/crawling-managing-faceted-navigation?hl=ko)
-   [크롤링 예산 관리를 위한 대규모 사이트 소유자 가이드](https://developers.google.com/search/docs/crawling-indexing/large-site-managing-crawl-budget?hl=ko)
-   [HTTP 상태 코드, 네트워크 및 DNS 오류가 Google 검색에 미치는 영향](https://developers.google.com/search/docs/crawling-indexing/http-network-errors?hl=ko)
-   [Google 크롤러](https://developers.google.com/search/docs/crawling-indexing/overview-google-crawlers?hl=ko) |
| [robots.txt](https://developers.google.com/search/docs/crawling-indexing/robots/intro?hl=ko) | robots.txt 파일은 검색엔진 크롤러에 크롤러가 사이트에 요청할 수 있거나 요청할 수 없는 페이지 또는 파일을 알려 줍니다. |
| [표준화](https://developers.google.com/search/docs/crawling-indexing/consolidate-duplicate-urls?hl=ko) | URL 정규화의 정의, 그리고 과도한 크롤링을 방지하기 위해 사이트의 중복 페이지에 관해 Google에 알리는 방법을 알아보세요. Google에서 중복 콘텐츠를 자동으로 감지하는 방법, 중복 콘텐츠를 처리하는 방법, 발견된 중복 페이지 그룹에 _표준 페이지_를 할당하는 방법을 알아보세요. |
| [모바일 사이트](https://developers.google.com/search/docs/crawling-indexing/mobile?hl=ko) | 모바일 기기에 맞게 사이트를 최적화하고 적절하게 크롤링하고 색인을 생성하는 방법을 알아보세요. |
| [AMP](https://developers.google.com/search/docs/crawling-indexing/amp?hl=ko) | AMP 페이지가 있다면 Google 검색에서 AMP가 어떻게 작동하는지 알아보세요. |
| [JavaScript](https://developers.google.com/search/docs/crawling-indexing/javascript/javascript-seo-basics?hl=ko) | 크롤러가 콘텐츠에 액세스하고 렌더링하는 방법을 반영하려면 페이지와 애플리케이션을 설계할 때 몇 가지 차이점과 제한사항을 고려해야 합니다. |
| [페이지 및 콘텐츠 메타데이터](https://developers.google.com/search/docs/crawling-indexing/special-tags?hl=ko) | -   [유효한 HTML을 사용하여 페이지 메타데이터 명시하기](https://developers.google.com/search/docs/crawling-indexing/valid-page-metadata?hl=ko)
-   [Google에서 인식하는 모든 `meta` 태그](https://developers.google.com/search/docs/crawling-indexing/special-tags?hl=ko)
-   [Robots `meta` 태그, `data-nosnippet` 및 X-Robots-Tag 사양](https://developers.google.com/search/docs/crawling-indexing/robots-meta-tag?hl=ko)
-   [`noindex` `meta` 태그로 색인 생성 차단하기](https://developers.google.com/search/docs/crawling-indexing/block-indexing?hl=ko)
-   [링크를 크롤링 가능하게 설정](https://developers.google.com/search/docs/crawling-indexing/links-crawlable?hl=ko)
-   [`rel` 속성을 사용하여 Google에 발신 링크의 관계 알리기](https://developers.google.com/search/docs/crawling-indexing/qualify-outbound-links?hl=ko) |
| 삭제 | -   [Google과 공유하는 정보 관리하기](https://developers.google.com/search/docs/crawling-indexing/control-what-you-share?hl=ko)
-   [사이트에 호스팅된 페이지를 Google에서 삭제하기](https://developers.google.com/search/docs/crawling-indexing/remove-information?hl=ko)
-   [검색결과에서 페이지에 호스팅된 이미지 삭제하기](https://developers.google.com/search/docs/crawling-indexing/prevent-images-on-your-page?hl=ko)
-   [Google 검색에서 수정된 정보 제외하기](https://developers.google.com/search/docs/crawling-indexing/keep-redacted-information-out?hl=ko) |
| 사이트 이전 및 변경 | -   [리디렉션 및 Google 검색](https://developers.google.com/search/docs/crawling-indexing/301-redirects?hl=ko)
-   [사이트 이전하기](https://developers.google.com/search/docs/crawling-indexing/site-move-with-url-changes?hl=ko)
-   [Google 검색에서 A/B 테스트 영향 최소화](https://developers.google.com/search/docs/crawling-indexing/website-testing?hl=ko)
-   [일시적으로 웹사이트 중지 또는 사용 중지하기](https://developers.google.com/search/docs/crawling-indexing/pause-online-business?hl=ko) |

달리 명시되지 않는 한 이 페이지의 콘텐츠에는 [Creative Commons Attribution 4.0 라이선스](https://creativecommons.org/licenses/by/4.0/)에 따라 라이선스가 부여되며, 코드 샘플에는 [Apache 2.0 라이선스](https://www.apache.org/licenses/LICENSE-2.0)에 따라 라이선스가 부여됩니다. 자세한 내용은 [Google Developers 사이트 정책](https://developers.google.com/site-policies?hl=ko)을 참조하세요. 자바는 Oracle 및/또는 Oracle 계열사의 등록 상표입니다.

최종 업데이트: 2025-12-31(UTC)