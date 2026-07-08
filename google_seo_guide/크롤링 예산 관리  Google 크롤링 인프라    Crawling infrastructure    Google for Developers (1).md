## 크롤링 예산 최적화

이 가이드에서는 매우 크고 자주 업데이트되는 사이트의 Google 크롤링을 최적화하는 방법을 설명합니다.

사이트에 빠르게 변경되는 페이지가 많지 않거나 페이지가 게시된 당일에 크롤링되는 것 같다면 이 가이드를 참조하지 않아도 됩니다. 특히 Google 검색의 경우 [사이트맵을 최신 상태로 유지](https://developers.google.com/search/docs/crawling-indexing/sitemaps/build-sitemap?hl=ko)하고 정기적으로 [색인 생성 범위를 확인](https://support.google.com/webmasters/answer/7440203?hl=ko)하는 것만으로 충분합니다.

## 가이드의 대상 독자

이 가이드의 권장사항은 일반적으로 좋은 방법이지만, 이 가이드는 주로 다음 유형의 사이트를 대상으로 하는 고급 가이드입니다.

-   대규모 사이트: 고유한 페이지 수가 1백만 개 이상이며 콘텐츠가 적당한 간격으로 변경됨(1주일에 한 번)
-   중간 규모 이상 사이트: 고유한 페이지 수가 1만 개 이상이며 콘텐츠가 매우 빠르게 변경됨(매일)
-   전체 URL 중 상당 부분이 Search Console에서 [발견됨 - 현재 색인이 생성되지 않음](https://support.google.com/webmasters/answer/7440203?hl=ko#information-status)으로 분류된 사이트

## 크롤링 일반 이론

<iframe frameborder="0" allowfullscreen="" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share" referrerpolicy="strict-origin-when-cross-origin" width="640" height="360" src="https://www.youtube.com/embed/am4g0hXAA8Q?origin=https%3A%2F%2Fdevelopers.google.com&amp;autoplay&amp;controls&amp;embed_domain&amp;enablejsapi=1&amp;end&amp;hl&amp;showinfo&amp;start&amp;video-id=am4g0hXAA8Q&amp;widgetid=3&amp;forigin=https%3A%2F%2Fdevelopers.google.com%2Fcrawling%2Fdocs%2Fcrawl-budget%3Fhl%3Dko&amp;aoriginsup=1&amp;gporigin=https%3A%2F%2Fwww.google.com%2F&amp;vf=1" id="widget4" data-gtm-yt-inspected-183356566_95="true" data-gtm-yt-inspected-225073684_46="true" data-gtm-yt-inspected-27="true" data-gtm-yt-inspected-46="true" data-gtm-yt-inspected-53="true" data-title="YouTube video player" title="Crawl Budget: SEO Mythbusting"></iframe>

웹 공간은 거의 무한하므로 사용할 수 있는 모든 URL을 탐색하고 색인을 생성하는 Google의 능력을 넘어섭니다. 따라서 Google 크롤러가 단일 사이트를 크롤링하는 데 쓸 수 있는 시간에는 제한이 있습니다. 사이트는 호스트 이름으로 정의됩니다. 예를 들어 `https://www.example.com/`과 `https://code.example.com/`은 서로 다른 호스트 이름이므로 크롤링 예산이 별도로 있습니다. Google에서 사이트를 크롤링하는 데 쓰는 시간과 리소스의 양은 일반적으로 사이트의 _크롤링 예산_이라고 하며, _크롤링 용량 한도_와 _크롤링 수요_라는 두 가지 기본 요소로 결정됩니다.

### 크롤링 용량 한도

Google은 서버에 과부하를 주지 않으면서 사이트를 크롤링하려고 합니다. 이를 위해 Google 크롤러는 _크롤링 용량 한도_를 계산합니다. 이 한도는 Google이 사이트를 크롤링하는 데 사용할 수 있는 최대 동시 연결 수와 가져오기 사이의 지연 시간입니다. 이 계산을 통해 서버에 과부하를 주지 않으면서 중요한 모든 콘텐츠를 포함하게 됩니다.

크롤링 용량 한도는 다음 몇 가지 요인에 따라 올라가거나 내려갈 수 있습니다.

-   **크롤링 상태:** 사이트에서 한동안 응답을 빠르게 보내면 한도가 올라가므로 크롤링에 사용할 수 있는 연결이 많아집니다. 사이트의 속도가 느려지거나 서버 오류로 응답하면 한도는 내려가고 Google이 크롤링을 줄입니다.
-   **Google의 크롤링 한도**: Google에는 머신이 많이 있지만 무한정 있지 않습니다. 가지고 있는 리소스를 바탕으로 선택해야 합니다.

### 크롤링 수요

각 크롤러에는 웹 크롤링과 관련해 자체적인 '수요'가 있습니다. 예를 들어 사이트에서 동적 광고 타겟을 실행하는 경우 일반적으로 AdsBot의 수요가 높고, Google 쇼핑은 판매자 피드에 있는 제품에 대한 수요가 높으며, Googlebot의 수요는 다른 사이트와 비교하여 사이트의 크기, 업데이트 빈도, 페이지 품질, 관련성에 따라 달라집니다.

일반적으로 크롤링 수요를 판단하는 데 중요한 역할을 하는 요소는 다음과 같습니다.

-   **인식된 인벤토리:** 사용자의 안내가 없으면 Google은 사이트에서 인식하는 URL의 전부 또는 대부분을 크롤링하려고 합니다. 이러한 URL 중 다수가 중복되거나 다른 이유(삭제됨, 중요하지 않음 등)로 크롤링되지 않아야 한다면 사이트에서 Google 크롤링 시간을 많이 낭비하게 됩니다. 이 문제는 가장 분명하게 제어할 수 있는 요소입니다.
-   **인기도:** 인터넷에서 인기가 높은 URL은 Google 시스템에서 최신으로 유지하기 위해 더 자주 크롤링되는 경향이 있습니다.
-   **비활성:** Google 시스템에서는 변경사항을 충분히 포착하도록 자주 문서를 다시 크롤링하려고 합니다.

또한 사이트 이동과 같은 사이트 전체 이벤트는 새 URL에서 콘텐츠를 재처리하기 위해 크롤링 수요의 증가를 유발할 수 있습니다.

### 요약

Google은 크롤링 용량과 크롤링 수요를 함께 고려하여 사이트의 크롤링 예산을 Google이 크롤링할 수 있고 크롤링하려는 URL 집합으로 정의합니다. 크롤링 용량 한도에 도달하지 않더라도 크롤링 수요가 낮으면 Google의 사이트 크롤링이 줄어듭니다.

## 권장사항

크롤링 효율성을 극대화하려면 다음 권장사항을 따르세요.

-   **URL 인벤토리 관리:** 적절한 도구를 사용하여 크롤링할 페이지와 크롤링하지 않을 페이지를 Google에 알립니다. Google에서 크롤링해서는 안 되는 URL을 크롤링하는 데 너무 많은 시간을 소비하면 Google 크롤러는 사이트의 나머지 부분을 살펴보는 데 드는 시간이 가치가 없다고 판단하거나 예산을 늘려 나머지 부분을 살펴볼 수 있습니다.
    -   **[중복 콘텐츠 통합하기](https://developers.google.com/search/docs/crawling-indexing/consolidate-duplicate-urls?hl=ko).** 중복 콘텐츠를 제거하여 고유한 URL이 아닌 고유한 콘텐츠에 크롤링을 집중합니다.
    -   [**robots.txt를 사용하여 URL 크롤링 차단**.](https://developers.google.com/search/docs/crawling-indexing/troubleshoot-crawling-errors?hl=ko#hide_urls) 일부 페이지는 사용자에게 중요할 수 있지만 Google 표시 경로에 표시되거나 Google 시스템에서 다시 처리되지 않도록 할 수 있습니다. 예를 들어 링크된 페이지의 정보를 복제하는 무한 스크롤 페이지 또는 동일한 페이지의 다르게 정렬된 버전이 있습니다. 첫 번째 항목에서 설명한 대로 페이지를 통합할 수 없는 경우 [robots.txt](https://developers.google.com/crawling/docs/robots-txt/create-robots-txt?hl=ko)를 사용하여 중요하지 않은 이러한 페이지를 차단하세요. robots.txt를 사용하여 URL을 차단하면 Google이 URL을 크롤링하지 못하게 되며, URL이 다른 Google 시스템 (예: Google 검색에서 색인이 생성됨)에 의해 처리될 가능성이 크게 줄어듭니다.
    -   **영구 삭제된 페이지의 `404` 또는 `410` 상태 코드를 반환합니다.** Google은 알고 있는 URL을 기억하지만 `404` 상태 코드는 그 URL을 다시 크롤링하지 말라는 강력한 신호입니다. 그러나 차단된 URL은 크롤링 대기열에 훨씬 더 오래 남아 있으며 차단이 해제되면 다시 크롤링됩니다.
    -   **[`soft 404` 오류 제거](https://developers.google.com/search/docs/crawling-indexing/troubleshoot-crawling-errors?hl=ko#soft-404-errors).** `soft 404` 페이지는 계속 크롤링되며 예산을 낭비합니다. [색인 생성 범위 보고서](https://support.google.com/webmasters/answer/7440203?hl=ko)에서 `soft 404` 오류를 확인합니다.
    -   **사이트맵을 최신으로 유지.** Google에서는 정기적으로 사이트맵을 읽습니다. 따라서 Google에서 크롤링하기를 바라는 모든 콘텐츠를 포함해야 합니다. 사이트에 업데이트된 콘텐츠가 있다면 `<lastmod>` 태그를 포함하는 것이 좋습니다.
    -   **긴 리디렉션 체인 사용하지 않기**. 크롤링에 부정적인 영향을 미칩니다.
-   **[로드하기 효율적인 페이지 만들기](https://developers.google.com/search/docs/crawling-indexing/troubleshoot-crawling-errors?hl=ko#improve_crawl_efficiency).** Google에서 페이지를 더 빠르게 로드하고 렌더링할 수 있으면 사이트에서 더 많은 콘텐츠를 읽을 수 있습니다.
-   **[크롤링 예산 관련 문제 디버그](https://developers.google.com/search/docs/crawling-indexing/troubleshoot-crawling-errors?hl=ko)** 크롤링 중에 사이트에 가용성 문제가 있는지 확인하고 크롤링 효율을 높일 수 있는 방법을 찾아보세요.

## 크롤링 예산을 늘리려면 어떻게 해야 하나요?

크롤링 예산을 늘리는 방법에는 두 가지가 있습니다.

-   **서버 리소스 추가**: 내 쪽의 서버 용량으로 인해 사이트를 크롤링할 수 없는 경우 (예: URL 검사 도구에 [**호스트 로드 초과**](https://support.google.com/webmasters/answer/9012289?hl=ko#live_indexable&zippy=,additional-response-data,url-status-live-test,site-wide-availability-issues,availability-live-test)가 표시됨) 비즈니스에 적합하다면 서버 리소스를 추가합니다.
-   **타겟팅하는 Google 제품에 맞게 콘텐츠 품질 최적화**: Google은 특정 Google 제품과 관련된 요소를 고려하여 각 사이트에 할당되는 크롤링 리소스를 결정합니다. 예를 들어 Google 검색의 경우 인기도, 전반적인 사용자 가치, 콘텐츠 고유성, 게재 용량 등이 포함됩니다.