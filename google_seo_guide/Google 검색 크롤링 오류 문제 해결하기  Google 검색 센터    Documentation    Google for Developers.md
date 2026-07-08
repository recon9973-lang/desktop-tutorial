다음은 사이트의 Google 검색 크롤링 문제를 해결하는 주요 단계입니다.

1.  [Googlebot에 사이트의 가용성 문제가 발생하는지 확인합니다](https://developers.google.com/search/docs/crawling-indexing/troubleshoot-crawling-errors?hl=ko#availability_issues).
2.  [크롤링되지 않지만 크롤링되어야 하는 페이지가 있는지 확인합니다](https://developers.google.com/search/docs/crawling-indexing/troubleshoot-crawling-errors?hl=ko#not_crawled_should_be).
3.  [사이트의 일부분이 이전보다 훨씬 빨리 크롤링되어야 하는지 확인합니다.](https://developers.google.com/search/docs/crawling-indexing/troubleshoot-crawling-errors?hl=ko#updates)
4.  [사이트의 크롤링 효율성을 개선합니다.](https://developers.google.com/search/docs/crawling-indexing/troubleshoot-crawling-errors?hl=ko#improve_crawl_efficiency)
5.  [과도한 사이트 크롤링을 처리합니다](https://developers.google.com/search/docs/crawling-indexing/troubleshoot-crawling-errors?hl=ko#emergencies).

## 사이트의 가용성 문제로 Googlebot에 문제가 발생했는지 확인하기

사이트 가용성을 개선한다고 해서 크롤링 예산이 반드시 증가하는 것은 아닙니다. 앞서 설명한 대로 Google은 크롤링 수요에 기반하여 최적의 크롤링 속도를 결정합니다. 하지만, 가용성 문제로 인해 Google에서 원하는 만큼 사이트를 크롤링하지 못합니다.

**진단:**

[크롤링 통계 보고서](https://support.google.com/webmasters/answer/9679690?hl=ko)를 사용하여 Googlebot의 사이트 크롤링 기록을 확인하세요. 보고서는 Google에 사이트의 가용성 문제가 발생한 시기를 보여줍니다. 사이트의 가용성 오류 또는 경고가 보고되면 **호스트 가용성** 그래프에서 Googlebot 요청이 빨간색 한도를 초과한 인스턴스를 찾아 그래프를 클릭하여 어떤 URL이 실패하는지 확인하고 사이트의 문제와 이러한 URL의 상관관계를 알아봅니다.

[URL 검사 도구](https://support.google.com/webmasters/answer/9012289?hl=ko)를 사용하여 사이트의 URL 몇 개를 테스트해 볼 수도 있습니다. 도구에서 [**호스트 로드 초과**](https://support.google.com/webmasters/answer/9012289?hl=ko#live_indexable&zippy=,additional-response-data,url-status-live-test,site-wide-availability-issues,availability-live-test) 경고가 반환되면 Googlebot이 사이트에서 발견한 많은 URL을 크롤링할 수 없습니다.

**처리:**

-   [크롤링 통계 보고서 문서](https://support.google.com/webmasters/answer/9679690?hl=ko)를 읽고 가용성 문제를 찾아 처리하는 방법을 알아봅니다.
-   **크롤링되지 않아야 하면 페이지가 크롤링되지 않도록 차단합니다.** _[인벤토리 관리](https://developers.google.com/crawling/docs/crawl-budget?hl=ko#manage_inventory)_를 참고하세요.
-   **페이지 로드 및 렌더링 속도를 높입니다.** _[사이트의 크롤링 효율성 개선](https://developers.google.com/search/docs/crawling-indexing/troubleshoot-crawling-errors?hl=ko#improve_crawl_efficiency)_을 참고하세요.
-   **서버 용량을 늘립니다.** Google에서 게재 용량 한도로 일관되게 사이트를 크롤링하는 것 같지만 여전히 필요한 만큼 중요한 URL이 크롤링되거나 업데이트되지 않는 경우 게재 리소스가 더 많으면 Google에서 사이트의 페이지를 더 많이 요청할 수 있습니다. [크롤링 통계 보고서](https://support.google.com/webmasters/answer/9679690?hl=ko)에서 호스트 가용성 기록을 검토하여 Google의 크롤링 속도가 한도에 자주 도달하는지 확인합니다. 자주 도달하면 한 달 동안의 게재 리소스를 늘려 같은 기간 크롤링 요청이 증가했는지 확인하세요.

## 크롤링되지 않는 사이트 일부분이 크롤링되어야 하는지 확인하기

Google은 찾을 수 있는, 사용자에게 가치 있고 고품질인 모든 콘텐츠의 색인을 생성하려고 사이트에서 필요한 만큼 많은 시간을 보냅니다. Googlebot이 중요한 콘텐츠를 누락하는 것 같다면 Googlebot이 콘텐츠를 알지 못하거나 콘텐츠가 Google에서 차단되었거나 사이트 가용성으로 인해 Google의 액세스가 제한되거나 Google에서 사이트에 과부하가 걸리지 않도록 하려는 것입니다.

**진단:**

Search Console은 URL 또는 경로로 필터링할 수 있는 사이트의 크롤링 기록을 제공하지 않지만 사이트 로그를 검사하여 [Googlebot](https://developers.google.com/search/docs/crawling-indexing/overview-google-crawlers?hl=ko)이 특정 URL을 크롤링했는지 확인할 수 있습니다. 크롤링된 URL의 색인 생성 여부는 또 다른 문제입니다.

대부분의 사이트에서는 새 페이지를 확인하는 데 최소 며칠이 걸립니다. 대다수 사이트에서는 URL의 당일 크롤링을 예상해서는 안 됩니다. 단, 뉴스 사이트와 같은 시간에 민감한 사이트는 예외입니다.

**처리:**

사이트에 페이지를 추가하는데 적절한 시간 내에 크롤링되지 않는다면 Google이 페이지를 알지 못하거나 콘텐츠가 차단되거나 사이트가 최대 게재 용량에 도달했거나 [크롤링 예산이 없는](https://developers.google.com/crawling/docs/crawl-budget?hl=ko#more-crawl-budget) 것입니다.

1.  Google에 새 페이지에 관해 알려줍니다. 사이트맵을 업데이트하여 새 URL을 반영합니다.
2.  robots.txt 규칙을 검토하여 실수로 페이지를 차단하고 있지 않은지 확인합니다.
3.  크롤링 우선순위를 검토합니다(크롤링 예산을 현명하게 사용). [인벤토리를 관리](https://developers.google.com/crawling/docs/crawl-budget?hl=ko#manage_inventory)하고 [사이트의 크롤링 효율성을 개선](https://developers.google.com/search/docs/crawling-indexing/troubleshoot-crawling-errors?hl=ko#improve_crawl_efficiency)합니다.
4.  [게재 용량이 부족하지 않은지 확인합니다](https://developers.google.com/search/docs/crawling-indexing/troubleshoot-crawling-errors?hl=ko#availability_issues). Googlebot은 서버에서 크롤링 요청에 응답하는 데 문제가 있다고 감지하면 크롤링을 줄입니다.

크롤링되었더라도 콘텐츠의 가치나 사용자 수요가 충분하지 않으면 페이지가 검색결과에 표시되지 않을 수 있습니다.

## 업데이트가 충분히 신속하게 크롤링되는지 확인하기

Google에서 사이트의 새 페이지나 업데이트된 페이지를 누락한다면 그 이유는 페이지가 표시되지 않았거나 페이지가 업데이트된 것을 확인하지 못했을 수 있습니다. 다음은 페이지 업데이트를 Google에서 인식하도록 도울 수 있는 방법입니다.

Google은 합리적으로 알맞은 시기에 페이지를 확인하고 색인을 생성하기 위해 노력하고 있습니다. 대다수 사이트에서는 3일 이상이 소요됩니다. 뉴스 사이트이거나 가치가 높고 극도로 시간에 민감한 다른 콘텐츠가 없다면 페이지를 게시한 당일에 Google에서 페이지의 색인을 생성한다고 예상하지 마세요.

**진단:**

사이트 로그를 검토하여 [Googlebot](https://developers.google.com/search/docs/crawling-indexing/overview-google-crawlers?hl=ko)이 특정 URL을 언제 크롤링했는지 확인합니다.

색인 생성 날짜를 알아보려면 URL 검사 도구를 사용하거나 업데이트한 URL을 검색하세요.

**처리:**

**해야 할 일:**

-   사이트에 뉴스 콘텐츠가 있으면 [뉴스 사이트맵](https://developers.google.com/search/docs/crawling-indexing/sitemaps/news-sitemap?hl=ko)을 사용합니다.
-   사이트맵의 `<lastmod>` 태그를 사용하여 색인이 생성된 URL이 언제 업데이트되었는지 표시합니다.
-   [크롤링 가능한 URL 구조](https://developers.google.com/search/docs/crawling-indexing/url-structure?hl=ko)를 사용하여 Google에서 페이지를 쉽게 찾도록 합니다.
-   Google에서 내 페이지를 찾을 수 있도록 [크롤링 가능한 표준 `<a>` 링크](https://developers.google.com/search/docs/crawling-indexing/links-crawlable?hl=ko#crawlable-links)를 제공합니다.
-   사이트에서 모바일 버전과 데스크톱 버전에 별도의 HTML을 사용하는 경우 데스크톱 버전과 동일한 링크 집합을 모바일 버전에 제공합니다. 모바일 버전에서 동일한 링크 집합을 제공할 수 없는 경우 [사이트맵](https://developers.google.com/search/docs/crawling-indexing/sitemaps/overview?hl=ko) 파일에 링크가 포함되어 있는지 확인하세요. Google은 [모바일 버전의 페이지만 색인을 생성](https://developers.google.com/search/docs/crawling-indexing/mobile/mobile-sites-mobile-first-indexing?hl=ko)하므로 여기에 표시되는 링크를 제한하면 새 페이지의 검색 속도가 느려질 수 있습니다.

**피해야 할 사항:**

-   변경되지 않은 동일한 사이트맵을 하루에 여러 번 제출.
-   Googlebot이 사이트맵의 모든 내용을 크롤링하거나 즉시 크롤링한다고 예상. 사이트맵은 절대적인 요구사항이 아니라 Googlebot에 유용한 제안입니다.
-   사이트맵에 [Google 검색에 표시하고 싶지 않은](https://developers.google.com/search/docs/crawling-indexing/troubleshoot-crawling-errors?hl=ko#hide_urls) URL을 포함합니다. 이렇게 하면 색인 생성을 원하지 않는 페이지에 크롤링 예산이 낭비될 수 있습니다.

## 사이트의 크롤링 효율성 개선

### 페이지 로드 속도 높이기

Google의 크롤링은 Googlebot 인스턴스의 대역폭, 시간, 가용성에 따라 제한됩니다. 서버에서 요청에 더 빠르게 응답하면 Google이 사이트에서 더 많은 페이지를 크롤링할 수 있습니다. 그러나 Google은 고품질의 콘텐츠만 크롤링하려고 하므로 품질이 낮은 페이지만 빠르게 만들면 Googlebot이 사이트를 더 많이 크롤링하지 않습니다. 반대로 사이트의 고품질 콘텐츠를 누락하고 있다고 판단되면 Google에서 예산을 늘려 고품질 콘텐츠를 크롤링할 수 있습니다.

다음은 크롤링을 위해 페이지와 리소스를 최적화할 수 있는 방법입니다.

-   robots.txt를 사용하여 Googlebot이 크지만 중요하지 않은 리소스를 로드하지 못하도록 합니다. 중요하지 않은 리소스, 즉 페이지의 목적을 파악하는 데 중요하지 않은 리소스(예: 장식 이미지)만 차단해야 합니다.
-   페이지가 빠르게 로드되어야 합니다.
-   크롤링에 부정적인 영향을 미치는 긴 리디렉션 체인에 주의합니다.
-   이미지 및 스크립트와 같은 삽입된 리소스의 로드 및 실행 시간을 포함하여 서버 요청에 응답하는 시간과 페이지를 렌더링하는 데 필요한 시간이 모두 중요합니다. 색인 생성에 필요한 크거나 느린 리소스에 유의하세요.

### HTTP 상태 코드로 콘텐츠 변경사항 지정

Google은 일반적으로 크롤링을 위한 [`If-Modified-Since` 및 `If-None-Match` HTTP 요청 헤더](https://developer.mozilla.org/docs/Web/HTTP/Headers/If-Modified-Since)를 지원합니다. Google 크롤러는 모든 크롤링 시도에 헤더를 전송하지 않으며, 요청 사용 사례에 따라 다릅니다. 예를 들어 [AdsBot](https://developers.google.com/search/docs/crawling-indexing/overview-google-crawlers?hl=ko#adsbot)은 `If-Modified-Since` 및 `If-None-Match` HTTP 요청 헤더를 설정할 가능성이 더 큽니다. Google 크롤러가 `If-Modified-Since` 헤더를 전송하는 경우의 헤더 값은 콘텐츠가 마지막으로 크롤링된 [날짜 및 시간](https://www.rfc-editor.org/rfc/rfc9110#name-if-modified-since)입니다. 이 값을 기준으로 서버에서 응답 본문 없이 `304 (Not Modified)` HTTP 상태 코드를 반환하도록 선택할 수 있으며 이 경우에 Google은 마지막으로 크롤링한 콘텐츠 버전을 다시 사용합니다. 콘텐츠가 `If-Modified-Since` 헤더에 크롤러가 지정한 날짜보다 최신인 경우에는 서버가 응답 본문과 함께 `200 (OK)` HTTP 상태 코드를 반환할 수 있습니다.

요청 헤더와 관계없이 Googlebot이 마지막으로 URL을 방문한 이후로 콘텐츠가 변경되지 않은 경우에는 Googlebot 요청에 대한 응답 본문 없이 `304 (Not Modified)` HTTP 상태 코드를 전송할 수 있습니다. 이렇게 하면 서버 처리 시간과 리소스가 절약되어 크롤링 효율성이 간접적으로 향상될 수 있습니다.

## 검색결과에 표시하고 싶지 않은 URL 숨기기

불필요한 페이지에 서버 리소스를 낭비하면 중요한 페이지에서 크롤링 활동이 줄어들 수 있으며 이로 인해 사이트에 있는 뛰어난 새 콘텐츠나 업데이트된 콘텐츠의 발견이 상당히 지연될 수 있습니다.

Google 검색의 크롤링을 원치 않는 URL을 사이트에서 많이 노출하면 사이트의 크롤링과 색인 생성에 부정적인 영향을 미칠 수 있습니다. 일반적으로 이러한 URL은 다음 카테고리로 분류됩니다.

-   [속성 탐색](https://developers.google.com/search/docs/crawling-indexing/crawling-managing-faceted-navigation?hl=ko) 및 [세션 식별자](https://developers.google.com/search/blog/2007/09/google-duplicate-content-caused-by-url?hl=ko): 속성 탐색은 일반적으로 사이트의 중복 콘텐츠이고 단순히 페이지를 정렬하거나 필터링하는 세션 식별자와 기타 URL 매개변수는 새 콘텐츠를 제공하지 않습니다. [속성 탐색 페이지의 크롤링을 관리](https://developers.google.com/search/docs/crawling-indexing/crawling-managing-faceted-navigation?hl=ko)하는 방법을 알아보세요.
-   [중복 콘텐츠](https://developers.google.com/search/docs/crawling-indexing/consolidate-duplicate-urls?hl=ko): Google에서 불필요한 크롤링을 하지 않도록 중복 콘텐츠 식별을 돕습니다.
-   [`soft 404` 페이지](https://developers.google.com/search/docs/crawling-indexing/troubleshoot-crawling-errors?hl=ko#soft-404-errors): 페이지가 더 이상 존재하지 않는 경우 `404` 코드를 반환합니다.
-   [해킹된 페이지](https://developers.google.com/search/docs/monitor-debug/security/what-is-hacked?hl=ko): [보안 문제 보고서](https://search.google.com/search-console/security-issues?hl=ko)를 확인하여 해킹된 페이지를 수정하거나 삭제해야 합니다.
-   [무한 공간](https://developers.google.com/search/blog/2008/08/to-infinity-and-beyond-no?hl=ko) 및 프록시: robots.txt를 사용하여 크롤링되지 못하도록 차단합니다.
-   [저품질 및 스팸 콘텐츠](https://developers.google.com/search/docs/essentials/spam-policies?hl=ko): 피하는 것이 분명 좋습니다.
-   장바구니 페이지, 무한 스크롤 페이지, 작업을 실행하는 페이지(예: '가입' 또는 '지금 구매' 페이지)

**해야 할 일:**

-   Google에서 리소스나 페이지를 아예 크롤링하지 않도록 하려면 robots.txt를 사용합니다.
-   공통 리소스가 여러 페이지에서 재사용되는 경우(예: 공유 이미지 또는 자바스크립트 파일) Google에서 동일한 리소스를 여러 번 요청하지 않고도 동일한 리소스를 캐시하고 재사용할 수 있도록 각 페이지에서 동일한 URL의 리소스를 참조합니다.

**피해야 할 사항:**

-   사이트의 크롤링 예산을 재할당하는 방법으로 robots.txt에서 페이지 또는 디렉터리를 정기적으로 추가하거나 삭제하지 않습니다. 장기간 Google에 표시되지 않을 페이지 또는 리소스에만 robots.txt를 사용하세요.
-   예산을 재할당하기 위해 사이트맵을 로테이션하거나 다른 임시 숨김 메커니즘을 사용하지 않습니다.

### 오류 `soft 404`개

`soft 404` 오류는 사용자에게 페이지가 존재하지 않는다고 알리는 페이지**와 [`200 (success)`](https://en.wikipedia.org/wiki/List_of_HTTP_status_codes#2xx_Success) 상태 코드**를 반환하는 URL입니다. 경우에 따라 주요 콘텐츠가 없거나 페이지가 비어 있는 경우도 있습니다.

이러한 페이지는 웹사이트의 웹 서버 또는 콘텐츠 관리 시스템이나 사용자의 브라우저에 의해 다양한 원인으로 생성될 수 있습니다. 예를 들면 다음과 같습니다.

-   서버 측 포함 파일이 누락되었습니다.
-   데이터베이스 연결이 끊어졌습니다.
-   내부 검색결과 페이지가 비어 있습니다.
-   로드 취소되었거나 자바스크립트 파일이 누락되었습니다.

`200 (success)` 상태 코드를 반환한 다음에 오류 메시지를 표시 또는 제안하거나 페이지에 특정 오류가 표시되는 것은 좋은 사용자 환경이 아닙니다. 사용자가 해당 페이지가 실제로 작동 중인 페이지라고 생각하게 되지만 그런 다음 오류 메시지가 표시되게 됩니다. 이러한 페이지는 검색에서 제외됩니다.

Google 알고리즘이 페이지의 콘텐츠를 기반으로 페이지를 실제 오류 페이지로 감지하면 Search Console은 사이트의 [페이지 색인 생성 보고서](https://support.google.com/webmasters/answer/7440203?hl=ko)에 `soft 404` 오류를 표시합니다.

#### `soft 404` 오류 수정

페이지 상태와 원하는 결과에 따라 `soft 404` 오류를 다음과 같이 여러 방법으로 해결할 수 있습니다.

-   [페이지와 콘텐츠를 더 이상 사용할 수 없음](https://developers.google.com/search/docs/crawling-indexing/troubleshoot-crawling-errors?hl=ko#pagegone)
-   [페이지나 콘텐츠가 이제 다른 위치에 있음](https://developers.google.com/search/docs/crawling-indexing/troubleshoot-crawling-errors?hl=ko#pagemoved)
-   [페이지와 콘텐츠가 여전히 있음](https://developers.google.com/search/docs/crawling-indexing/troubleshoot-crawling-errors?hl=ko#pageother)

사용자에게 가장 적합한 솔루션을 파악해 보세요.

##### 페이지와 콘텐츠를 더 이상 사용할 수 없음

페이지를 삭제했지만 사이트에 비슷한 콘텐츠가 있는 대체 페이지가 없다면 페이지에 관한 [`404 (not found)` 또는 `410 (gone)`](https://en.wikipedia.org/wiki/List_of_HTTP_status_codes#4xx_Client_errors) 응답(상태) 코드를 반환합니다. 이러한 상태 코드는 페이지가 존재하지 않으며 검색엔진이 페이지의 색인을 생성하지 않기를 원한다고 검색엔진에 알려 줍니다.

서버의 구성 파일에 액세스할 수 있다면 이러한 오류 페이지를 맞춤설정하여 사용자에게 유용하게 만들 수 있습니다. 적절한 맞춤 `404` 페이지를 사용하면 사용자가 원하는 정보를 찾도록 돕고, 사이트를 더 자세히 탐색하도록 유도하는 유용한 콘텐츠도 제공할 수 있습니다. 다음은 유용한 맞춤 `404` 페이지를 디자인하기 위한 도움말입니다.

-   요청한 페이지를 찾을 수 없음을 방문자에게 확실히 알립니다. 친근하고 호감이 가는 표현을 사용하세요.
-   `404` 페이지의 디자인(탐색 메뉴 포함)이 사이트의 나머지 부분과 같은지 확인합니다.
-   사이트 홈페이지 링크뿐 아니라 가장 인기 있는 기사나 게시물의 링크를 추가합니다.
-   깨진 링크를 신고할 수 있는 경로를 사용자에게 제공합니다.

맞춤 `404` 페이지는 사용자만을 위해 생성됩니다. 이러한 페이지는 검색엔진의 관점에서 쓸모없지만 페이지의 색인 생성을 방지하려면 서버가 `404` HTTP 상태 코드를 반환하도록 해야 합니다.

##### 페이지나 콘텐츠가 이제 다른 위치에 있음

페이지가 이동되었거나 사이트에 확실한 대체 페이지가 있다면 [`301 (permanent redirect)`](https://developers.google.com/search/docs/crawling-indexing/301-redirects?hl=ko)을 반환하여 사용자를 리디렉션합니다. 이렇게 하면 사용자의 탐색 환경을 방해하지 않으면서도 검색엔진에 페이지의 새 위치를 알릴 수 있습니다. [URL 검사 도구](https://support.google.com/webmasters/answer/9012289?hl=ko)를 사용하여 URL이 실제로 정확한 코드를 반환하는지 확인하세요.

##### 페이지와 콘텐츠가 여전히 있음

다른 우수한 페이지가 `soft 404` 오류로 신고된 경우 Googlebot에서 제대로 로드되지 않았거나, 중요한 리소스가 누락되었거나, 렌더링 중에 심각한 오류 메시지가 표시되었을 수 있습니다. [URL 검사 도구](https://support.google.com/webmasters/answer/9012289?hl=ko)를 사용하여 렌더링된 콘텐츠와 반환된 HTTP 코드를 검사합니다. 렌더링된 페이지가 전부 또는 거의 비어 있거나, 콘텐츠에 오류 메시지가 포함되어 있는 경우, 페이지에서 로드할 수 없는 리소스(이미지, 스크립트 등 텍스트가 아닌 요소)를 많이 참조하고 있기 때문일 수 있습니다. 이렇게 되면 페이지가 `soft 404`로 해석될 수 있습니다. 리소스 로드의 실패 이유는 리소스가 차단되었거나([robots.txt](https://developers.google.com/search/docs/crawling-indexing/robots/intro?hl=ko)에 의해), 페이지에 너무 많은 리소스가 있거나, 다양한 서버 오류가 발생하거나, 로드 속도가 너무 느리거나, 리소스의 크기가 너무 크기 때문일 수 있습니다.

## 과도한 사이트 크롤링 처리(긴급)

Googlebot에는 크롤링 요청으로 사이트에 과부하가 걸리지 않도록 하는 알고리즘이 있습니다. 그러나 Googlebot으로 사이트에 과부하가 걸린다고 확인하면 다음과 같은 조치를 취할 수 있습니다.

**진단**:

사이트에 과도한 Googlebot 요청이 있는지 서버를 모니터링합니다.

**처리**:

긴급 상황에서는 다음 단계를 따라 Googlebot의 과도한 크롤링 속도를 늦추는 것이 좋습니다.

1.  서버가 과부하되면 Googlebot 요청에 대해 _일시적으로_ `503` `429` HTTP 응답 상태 코드를 반환합니다. Googlebot은 약 2일 동안 이러한 URL을 다시 시도합니다. 며칠 동안 '사용 불가' 코드를 반환하면 Google에서 사이트의 URL 크롤링을 영구적으로 느리게 하거나 중지하므로 추가 단계를 따르세요.
2.  크롤링 속도가 내려가면 크롤링 요청에 `503` 또는 `429` HTTP 반환을 중지합니다. 2일 이상 `503` 또는 `429`를 반환하면 Google이 색인에서 해당 URL을 삭제하게 됩니다.
3.  시간이 지남에 따라 크롤링 및 호스트 용량을 모니터링합니다.
4.  문제가 있는 크롤러가 [AdsBot 크롤러](https://developers.google.com/search/docs/crawling-indexing/google-special-case-crawlers?hl=ko#adsbot-mobile-web) 중 하나이면 Google에서 크롤링하려는 사이트에 사용자가 [동적 검색 광고 타겟](https://support.google.com/google-ads/answer/2497706?hl=ko)을 생성한 것이 문제일 수 있습니다. 이 크롤링은 3주마다 다시 실행됩니다. 이러한 크롤링을 처리할 서버 용량이 부족한 경우 광고 타겟을 제한하거나 게재 용량을 늘립니다.