기본 AMP 페이지를 만들고 구조화된 데이터를 추가하고 페이지를 모니터링하고 Codelab으로 연습하여 Google 검색의 [AMP](https://developers.google.com/amp?hl=ko) 콘텐츠를 향상할 수 있습니다.

## 기본 AMP 페이지 만들기

1.  [첫 번째 AMP 페이지를 만듭니다](https://www.ampproject.org/docs/get_started/create).
2.  [AMP 페이지용 Google 검색 가이드라인](https://developers.google.com/search/docs/crawling-indexing/amp?hl=ko)을 따릅니다.
3.  [페이지를 연결하여 콘텐츠를 검색 가능](https://www.ampproject.org/docs/guides/discovery)한 상태로 만듭니다. Google 검색에서 크롤링하고 색인을 생성하려면 AMP 페이지가 [표준 페이지](https://developers.google.com/search/docs/crawling-indexing/consolidate-duplicate-urls?hl=ko)에 연결되어 있어야 합니다. 표준 페이지는 페이지의 AMP가 아닌 버전이거나 AMP 페이지 자체일 수 있습니다.
4.  가능하면 사용자가 AMP 페이지에서 일치하는 표준 페이지와 동일한 콘텐츠를 경험하고 동일한 작업을 완료하도록 보장합니다.
5.  [AMP 테스트 도구](https://search.google.com/test/amp?hl=ko)를 사용해 페이지가 유효한 AMP HTML 문서를 위한 Google 검색 요구사항을 충족하는지 확인합니다.
6.  표준 페이지와 AMP 페이지 모두에서 동일한 [구조화된 데이터 마크업](https://developers.google.com/search/docs/appearance/structured-data/intro-structured-data?hl=ko)을 사용합니다.
7.  다음과 같은 일반적인 콘텐츠 권장사항을 적용합니다.
    1.  [robots.txt 파일](https://developers.google.com/search/docs/crawling-indexing/robots/robots_txt?hl=ko)이 AMP 페이지를 차단하지 않아야 합니다. 해당하는 경우 [robots `meta` 태그, `data-nosnippet`, `X-Robots-Tag`](https://developers.google.com/search/docs/crawling-indexing/robots-meta-tag?hl=ko)를 사용합니다.
    2.  [언어 및 지역 URL을 위한 hreflang](https://developers.google.com/search/docs/specialty/international/localized-versions?hl=ko) 가이드라인을 따릅니다. AMP 관련 예는 [국제화](https://amp.dev/documentation/examples/guides/internationalization/)를 참고하세요.

## CMS로 AMP 페이지 만들기

CMS(콘텐츠 관리 시스템)를 통해 웹 콘텐츠를 게재하는 경우 기존 CMS 플러그인(예: [WordPress](https://wordpress.org/plugins/amp/), [Drupal](https://www.drupal.org/project/amp), Joomla)을 사용하거나 CMS에 맞춤 기능을 구현하여 AMP 콘텐츠를 생성할 수 있습니다. CMS를 맞춤설정하려면 [기본 AMP 페이지 만들기](https://developers.google.com/search/docs/crawling-indexing/amp/enhance-amp?hl=ko#create-basic-amp) 외에 다음 가이드라인도 따르세요.

-   AMP HTML 파일을 사이트의 URL 경로 스키마에 어떻게 맞출지 고려합니다. AMP가 아닌 표준 페이지 외에 AMP 페이지를 생성하는 경우 다음 URL 스키마 중 하나를 선택하는 것이 좋습니다.
    -   https://www.example.com/myarticle/amp
    -   https://www.example.com/myarticle.amp.html
-   구조화된 데이터 마크업 템플릿을 개발합니다. 다음 가이드라인을 참고하세요.
    -   게시 중인 콘텐츠 유형의 요구사항을 기반으로 템플릿을 구성합니다.
    -   레시피, 기사, 동영상, 리뷰 관련 샘플 템플릿은 [AMP 프로젝트 메타데이터 예제](https://github.com/ampproject/amphtml/tree/main/examples/metadata-examples)를 참조하세요.

## 리치 결과 최적화하기

구조화된 데이터를 사용하여 검색결과에서 페이지의 디자인을 개선할 수 있습니다. 구조화된 데이터가 포함된 AMP 페이지는 주요 뉴스 캐러셀이나 호스트 캐러셀과 같은 [리치 결과](https://developers.google.com/search/docs/appearance/structured-data/search-gallery?hl=ko)로 표시될 수 있습니다.

1.  [구조화된 데이터를 구현합니다](https://developers.google.com/search/docs/appearance/structured-data/intro-structured-data?hl=ko).
2.  [리치 결과 테스트](https://search.google.com/test/rich-results?hl=ko)를 사용하여 구조화된 데이터가 올바르게 파싱되는지 확인합니다.
3.  [AMP 테스트 도구](https://search.google.com/test/amp?hl=ko)를 사용하여 전체 AMP 설정을 확인합니다.

## 페이지 모니터링 및 개선

다음 보고서를 모니터링하여 모든 AMP 페이지를 정기적으로 확인하세요.

-   [AMP 상태 보고서](https://search.google.com/search-console/amp?hl=ko): 많은 AMP 페이지에 영향을 미칠 수 있는 사이트 템플릿 및 기타 사이트 전체 구현 문제를 파악합니다.
-   [리치 결과 상태 보고서](https://support.google.com/webmasters/answer/7552505?hl=ko): 구조화된 데이터의 문제와 구조화된 데이터를 추가할 기회를 확인합니다.

Google 검색결과에서 AMP 페이지 게재를 중지해야 하는 경우 [Google 검색결과에서 AMP 삭제](https://developers.google.com/search/docs/crawling-indexing/amp/remove-amp?hl=ko)를 따르세요.

## Codelab으로 연습

다음은 AMP 페이지 빌드를 연습할 수 있는 몇 가지 Codelab입니다.

-   [AMP 기초 Codelab](https://codelabs.developers.google.com/codelabs/accelerated-mobile-pages-foundations/?hl=ko)으로 AMP 페이지를 빌드하는 방법을 알아봅니다.
-   [고급 개념 Codelab](https://codelabs.developers.google.com/codelabs/accelerated-mobile-pages-advanced/?hl=ko#0)으로 AMP 페이지에 분석, 동영상 삽입, 소셜 미디어 통합, 이미지 캐러셀 같은 기능을 추가합니다.
-   다양한 AMP 기능과 확장된 구성요소를 통합하는 [아름다운 대화형 표준 AMP 페이지 Codelab](https://developers.google.com/codelabs/amp-beautiful-interactive-canonical?hl=ko#0)을 빌드합니다.
-   AMP 구성요소를 사용해 [AMP+PWA Codelab](https://amp.dev/documentation/guides-and-tutorials/integrate/integrate-with-apps/)으로 [PWA](https://developers.google.com/web/progressive-web-apps?hl=ko) 환경을 빌드합니다.

## 리소스

AMP 페이지를 만들었으므로 다음은 AMP에 다른 Google 제품 통합을 자세히 알아볼 수 있는 몇가지 리소스입니다.

-   [AMP 광고 단위](https://support.google.com/adsense/answer/7183212?hl=ko)를 만드는 방법을 알아보세요.
-   [AMP 페이지에서 수익을 창출](https://support.google.com/dfp_premium/topic/7178122?hl=ko)하는 방법을 알아보세요.
-   [Google 태그 관리자](https://support.google.com/tagmanager/answer/9205783?hl=ko)를 사용해 마케팅 이니셔티브를 최적화하고 측정하세요.
-   [AMP 페이지에 분석](https://developers.google.com/analytics/devguides/collection/amp-analytics?hl=ko)을 추가하여 내장된 Google 애널리틱스 지원으로 사용자 상호작용을 추적하세요.