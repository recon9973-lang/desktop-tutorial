## 사이트맵 알아보기

<iframe frameborder="0" allowfullscreen="" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share" referrerpolicy="strict-origin-when-cross-origin" width="640" height="360" src="https://www.youtube.com/embed/JlamLfyFjTA?origin=https%3A%2F%2Fdevelopers.google.com&amp;autoplay&amp;controls&amp;embed_domain&amp;enablejsapi=1&amp;end&amp;hl&amp;showinfo&amp;start&amp;video-id=JlamLfyFjTA&amp;widgetid=35&amp;forigin=https%3A%2F%2Fdevelopers.google.com%2Fsearch%2Fdocs%2Fcrawling-indexing%2Fsitemaps%2Foverview%3Fhl%3Dko&amp;aoriginsup=1&amp;gporigin=https%3A%2F%2Fwww.google.com%2F&amp;vf=1" id="widget36" data-gtm-yt-inspected-225073684_46="true" data-gtm-yt-inspected-183356566_95="true" data-gtm-yt-inspected-26="true" data-gtm-yt-inspected-45="true" data-gtm-yt-inspected-52="true" data-title="YouTube video player" title="Sitemaps in Search Console - Google Search Console Training"></iframe>

_사이트맵_은 사이트에 있는 페이지, 동영상 및 기타 파일과 각 관계에 관한 정보를 제공하는 파일입니다. Google과 같은 검색엔진은 이 파일을 읽고 사이트를 더 효율적으로 크롤링합니다. 사이트맵은 내가 사이트에서 중요하다고 생각하는 페이지와 파일을 검색엔진에 알리고 중요한 관련 정보를 제공합니다. 관련 정보의 예로는 페이지가 마지막으로 업데이트된 시간, 페이지의 대체 언어 버전이 있습니다.

사이트맵을 사용하여 [동영상](https://developers.google.com/search/docs/crawling-indexing/sitemaps/video-sitemaps?hl=ko), [이미지](https://developers.google.com/search/docs/crawling-indexing/sitemaps/image-sitemaps?hl=ko), [뉴스](https://developers.google.com/search/docs/crawling-indexing/sitemaps/news-sitemap?hl=ko) 콘텐츠 등 페이지의 특정 콘텐츠 유형에 관한 정보를 제공할 수 있습니다. 예:

-   사이트맵 _동영상 항목_은 동영상 길이, 등급, 연령 적합성 등급을 지정할 수 있습니다.
-   사이트맵 _이미지 항목_은 페이지에 있는 이미지의 위치를 포함할 수 있습니다.
-   사이트맵 _뉴스 항목_은 기사 제목과 게시 날짜를 포함할 수 있습니다.

## 사이트맵이 필요한가요?

사이트 페이지가 제대로 링크되었다면 대개 Google에서 대부분의 사이트를 찾을 수 있습니다. 올바른 연결이란 사이트의 메뉴나 페이지에 배치한 링크와 같이 일부 탐색 형식을 통해 중요하다고 생각하는 모든 페이지에 도달할 수 있다는 것을 의미합니다. 그렇다 하더라도 사이트맵을 사용하면 크고 복잡한 사이트나 전문화된 파일의 크롤링을 개선할 수 있습니다.

**다음과 같은 경우 사이트맵이 필요할 수 있습니다.**

-   **사이트 크기가 큽니다.** 일반적으로 대규모 사이트에서는 모든 페이지가 사이트에서 하나 이상의 다른 페이지에 연결되도록 하기 어렵습니다. 크기로 인해 [Googlebot](https://developers.google.com/search/docs/crawling-indexing/googlebot?hl=ko)이 새 페이지를 발견하지 못할 가능성이 큽니다.
-   **연결되는 외부 링크가 많지 않은 새로운 사이트.** Googlebot 및 기타 웹 크롤러는 이전에 크롤링된 페이지에서 찾은 URL에 액세스하여 웹을 크롤링합니다. 따라서 다른 사이트가 페이지에 링크되어 있지 않으면 Googlebot이 페이지를 찾지 못할 수도 있습니다.
-   **리치 미디어 콘텐츠(동영상, 이미지)가 많거나 Google 뉴스에 표시되는 사이트.** Google에서 Google 검색에 표시할지 여부를 결정할 때 사이트맵의 추가 정보를 고려할 수 있습니다.

**다음과 같은 경우 사이트맵이 필요하지 않을 수 있습니다.**

-   **크기가 '작은' 사이트.** 이는 사이트에 있는 페이지가 500개 이하임을 의미합니다. 페이지 합계에는 검색결과에 표시되어야 한다고 생각하는 페이지만 포함됩니다.
-   **내부적으로 긴밀히 연결된 사이트.** Googlebot은 홈페이지에서 시작되는 링크를 따라가서 사이트에 있는 중요한 페이지를 모두 발견할 수 있습니다.
-   검색결과에 표시하려는 **미디어 파일(동영상, 이미지) 또는 뉴스 페이지가 많지 않음**. 사이트맵이 있으면 Google에서 사이트의 동영상, 이미지 파일 또는 뉴스 기사를 찾고 이해하는 데 도움을 줍니다. 이러한 검색결과가 Google 검색에 표시되지 않아도 된다면 사이트맵을 사용하지 않아도 됩니다.

## 사이트맵 만들기

사이트맵이 필요하다고 생각되면 [사이트맵을 만드는 방법을 자세히 알아보세요](https://developers.google.com/search/docs/crawling-indexing/sitemaps/build-sitemap?hl=ko).