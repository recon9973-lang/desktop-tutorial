## 모바일 사이트 및 모바일 중심 색인 생성 권장사항

Google에서 색인을 생성하고 순위를 지정하는 데 [스마트폰 에이전트](https://developers.google.com/search/docs/crawling-indexing/overview-google-crawlers?hl=ko)로 크롤링된 모바일 버전의 콘텐츠를 사용합니다. 이를 **모바일 중심 색인 생성**이라고 합니다.

<iframe frameborder="0" allowfullscreen="" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share" referrerpolicy="strict-origin-when-cross-origin" width="640" height="360" src="https://www.youtube.com/embed/TTUzxHdx2jY?origin=https%3A%2F%2Fdevelopers.google.com&amp;autoplay&amp;controls&amp;embed_domain&amp;enablejsapi=1&amp;end&amp;hl&amp;showinfo&amp;start&amp;video-id=TTUzxHdx2jY&amp;widgetid=55&amp;forigin=https%3A%2F%2Fdevelopers.google.com%2Fsearch%2Fdocs%2Fcrawling-indexing%2Fmobile%2Fmobile-sites-mobile-first-indexing%3Fhl%3Dko&amp;aoriginsup=1&amp;gporigin=https%3A%2F%2Fwww.google.com%2F&amp;vf=1" id="widget56" data-gtm-yt-inspected-225073684_46="true" data-gtm-yt-inspected-183356566_95="true" data-gtm-yt-inspected-26="true" data-gtm-yt-inspected-45="true" data-gtm-yt-inspected-52="true" data-title="YouTube video player" title="Mobile-First Indexing"></iframe>

Google의 검색결과에 콘텐츠를 포함하기 위해 페이지의 모바일 버전이 꼭 필요한 것은 아니지만, 모바일 버전이 있는 것이 적극 권장됩니다. 이 권장사항은 일반적으로 모바일 사이트에 적용되며, 정의상 모바일 중심 색인 생성에도 적용됩니다.

사용자에게 최상의 환경을 제공할 수 있도록 이 가이드에 설명된 권장사항을 따르세요.

## 모바일 친화적인 사이트 만들기

아직 만들지 않았다면 모바일 기반 웹사이트를 만듭니다. 휴대전화를 통해 사이트를 방문하는 사용자의 이용 만족도를 높일 수 있습니다. 모바일 친화적인 사이트를 만들 때 다음과 같은 세 가지 구성 중 하나를 선택할 수 습니다.

-   [**반응형 웹 디자인:**](https://web.dev/learn/design?hl=ko) 사용자 기기(데스크톱, 태블릿, 모바일, 비시각적 브라우저)와 상관없이 동일한 URL에 동일한 HTML 코드를 게재하지만 화면 크기에 따라 콘텐츠를 다르게 표시할 수 있습니다. **Google에서는 구현 및 유지보수가 가장 쉬운 반응형 웹 디자인을 권장합니다.**
-   **동적 게재:** 기기와 관계없이 동일한 URL을 사용합니다. 이 구성은 [`user-agent` 스니핑](https://en.wikipedia.org/wiki/Browser_sniffing) 및 [`Vary: user-agent` HTTP 응답 헤더](https://developer.mozilla.org/docs/Web/HTTP/Headers/Vary)를 사용하여 다양한 기기에 서로 다른 HTML 버전을 적용합니다.
-   **별도 URL:** 각 기기 및 별도 URL에 다른 HTML을 게재합니다. 동적 게재와 마찬가지로 이 구성도 `user-agent` 및 `Vary` HTTP 헤더를 사용하여 기기에 맞는 버전으로 사용자를 리디렉션합니다.

이 가이드의 내용은 동적 게재 및 별도 URL 구성에만 적용됩니다. 반응형 디자인의 경우 콘텐츠와 메타데이터가 페이지의 모바일 버전과 데스크톱 버전에서 동일합니다.

Google이 모바일 페이지 콘텐츠 및 리소스에 액세스하고 렌더링할 수 있는지 확인하세요.

-   **모바일 및 데스크톱 사이트에 동일한 robots `meta` 태그를 사용하세요** 모바일 사이트에서 다른 robots `meta` 태그를 사용하는 경우(특히 `noindex` 또는 `nofollow` 태그) 사이트에 모바일 중심 색인 생성이 사용 설정되면 Google에서 페이지를 크롤링하거나 색인을 생성하지 못할 수 있습니다.
-   **사용자 상호작용 시 주 콘텐츠에 지연 로드 방식을 사용하지 않습니다.** Google은 로드하기 위해 사용자 상호작용(예: 스와이프, 클릭, 입력)이 필요한 콘텐츠를 로드하지 않습니다. [Google에서 지연 로드 콘텐츠를 볼 수 있어야 합니다](https://developers.google.com/search/docs/crawling-indexing/javascript/lazy-loading?hl=ko).
-   **Google에서 리소스를 크롤링할 수 있도록 합니다.** 일부 리소스의 경우 모바일 사이트와 데스크톱 사이트의 URL이 다릅니다. Google에서 URL을 크롤링하도록 하려면 [`disallow` 규칙](https://developers.google.com/search/docs/crawling-indexing/robots/robots_txt?hl=ko#disallow)으로 URL을 차단하지 않는지 확인하세요.

## 데스크톱과 모바일에서 콘텐츠가 동일한지 확인하기

동일한 콘텐츠라도 데스크톱 페이지와 모바일 페이지에서 DOM 또는 레이아웃에 차이가 있으면 Google에서 콘텐츠를 다르게 이해할 수 있습니다. 하지만 데스크톱 버전과 모바일 버전에서 동일한 콘텐츠를 사용하면 같은 키워드에 대해 두 버전 모두 순위가 지정될 수 있습니다.

-   **모바일 사이트에 데스크톱 사이트와 동일한 콘텐츠가 포함되어 있는지 확인합니다.** 모바일 사이트에 포함된 콘텐츠가 데스크톱 사이트보다 적다면 모바일 사이트의 주 콘텐츠가 데스크톱 사이트와 동일하도록 모바일 사이트를 업데이트하는 것이 좋습니다. 모바일에서는 디자인을 다르게 하여 사용자 환경을 극대화할 수 있습니다(예: 아코디언이나 탭으로 콘텐츠 이동). 사이트의 색인 생성이 모바일 사이트에서 이루어지므로 콘텐츠가 데스크톱 사이트와 동일한지만 확인하면 됩니다.
-   데스크톱 사이트와 마찬가지로 모바일 사이트에도 **명확하고 의미 있는 제목을 사용**하세요.

## 구조화된 데이터 확인하기

사이트에 구조화된 데이터가 있다면 사이트의 두 버전 모두에 있는지 확인해야 합니다. 다음과 같은 사항을 확인하세요.

-   **모바일과 데스크톱 사이트의 구조화된 데이터가 동일한지 확인합니다.** 모바일 사이트에 추가하는 데이터 유형의 우선순위를 정해야 한다면 [`Breadcrumb`](https://developers.google.com/search/docs/appearance/structured-data/breadcrumb?hl=ko), [`Product`](https://developers.google.com/search/docs/appearance/structured-data/product?hl=ko) 및 [`VideoObject`](https://developers.google.com/search/docs/appearance/structured-data/video?hl=ko) 구조화된 데이터로 시작하세요.
-   **구조화된 데이터에 올바른 URL을 사용합니다.** 모바일 버전의 구조화된 데이터에 포함된 URL을 모바일 URL로 업데이트해야 합니다.
-   **데이터 하이라이터를 사용하면 모바일 사이트에서 학습시킵니다.** [데이터 하이라이터](https://support.google.com/webmasters/answer/2692911?hl=ko)를 사용하여 구조화된 데이터를 제공하는 경우 [데이터 하이라이터 대시보드](https://www.google.com/webmasters/tools/data-highlighter?hl=ko)에서 추출 오류가 있는지 정기적으로 확인하세요.

[`title` 요소](https://developers.google.com/search/docs/appearance/title-link?hl=ko#page-titles)와 [메타 설명](https://developers.google.com/search/docs/appearance/snippet?hl=ko#meta-descriptions)이 사이트의 두 버전 모두에서 동일해야 합니다.

## 광고 게재위치 확인하기

광고가 모바일 페이지 순위에 악영향을 주지 않도록 하세요. 휴대기기에 광고를 게재할 때는 [더 나은 광고 표준(Better Ads Standard)](https://www.betterads.org/standards/)을 따르세요. 예를 들어 페이지 상단의 광고는 휴대기기에서 너무 많은 공간을 차지하여 사용자 환경을 해칠 수 있습니다.

## 시각적 콘텐츠 확인하기

### 이미지 확인하기

모바일 사이트의 이미지가 [이미지 권장사항](https://developers.google.com/search/docs/appearance/google-images?hl=ko)을 준수하는지 확인하세요. 특히 다음 사항은 따르는 것이 좋습니다.

-   **[고화질 이미지](https://developers.google.com/search/docs/appearance/google-images?hl=ko#good-quality-photos)를 제공합니다.** 모바일 사이트에서 크기가 너무 작거나 해상도가 낮은 이미지는 사용하지 마세요.
-   **[지원되는 이미지 형식](https://developers.google.com/search/docs/appearance/google-images?hl=ko#supported-image-formats)을 사용합니다.** 지원되지 않는 형식이나 태그는 사용하지 마세요. 예를 들어 Google에서 SVG 형식 이미지는 지원하지만 Google의 시스템에서 인라인 SVG 내의 `<image>` 태그에 있는 .jpg 이미지 색인을 생성할 수 없습니다.
-   **페이지가 로드될 때마다 달라지는 이미지 URL은 사용하지 않습니다.** 계속 달라지는 URL을 사용하면 Google에서 리소스를 올바르게 처리하고 색인을 생성할 수 없습니다.
-   **모바일 사이트에 데스크톱 사이트와 동일한 이미지 대체 텍스트가 있어야 합니다.** 데스크톱 사이트에서와 마찬가지로 모바일 사이트의 이미지에 [구체적인 대체 텍스트](https://developers.google.com/search/docs/appearance/google-images?hl=ko#descriptive-alt-text)를 사용하세요.
-   **모바일 페이지의 콘텐츠 품질이 데스크톱 페이지만큼 양호해야 합니다.** 모바일 사이트에서 이미지와 관련된 구체적인 [제목, 캡션, 파일 이름, 텍스트](https://developers.google.com/search/docs/appearance/google-images?hl=ko#descriptive-titles-captions-filenames)를 데스크톱 사이트와 동일하게 사용하세요.

### 동영상 확인하기

모바일 사이트의 동영상이 [동영상 권장사항](https://developers.google.com/search/docs/appearance/video?hl=ko)을 준수하는지 확인하세요. 특히 다음 사항은 따르는 것이 좋습니다.

-   **페이지가 로드될 때마다 달라지는 동영상 URL은 사용하지 않습니다.** 계속 달라지는 URL을 사용하면 Google에서 리소스를 올바르게 처리하고 색인을 생성할 수 없습니다.
-   **[지원되는 동영상 형식](https://developers.google.com/search/docs/appearance/video?hl=ko#file-types)**을 사용하고 지원되는 태그에 동영상을 배치합니다. 동영상은 페이지에서 `<video>`, `<embed>`, `<object>`와 같은 HTML 태그를 통해 식별됩니다.
-   모바일 사이트와 데스크톱 사이트에 **동일한 동영상 구조화된 데이터를 사용**합니다. 자세한 내용은 [구조화된 데이터 확인하기](https://developers.google.com/search/docs/crawling-indexing/mobile/mobile-sites-mobile-first-indexing?hl=ko#structured-data)를 참고하세요.
-   **휴대기기에서 동영상을 볼 때 페이지에서 찾기 쉬운 위치에 배치합니다.** 예를 들어 사용자가 모바일 페이지에서 동영상을 찾기 위해 너무 아래로 스크롤해야 하는 경우 동영상 순위가 낮아질 수 있습니다.

## 별도 URL에 관한 추가 권장사항

사이트의 데스크톱 및 모바일 버전에서 별도 URL(m. URL이라고도 함)을 사용하는 경우 다음의 추가 권장사항을 따르는 것이 좋습니다.

-   **데스크톱 및 모바일 사이트에서 오류 페이지 상태가 동일해야 합니다.** 데스크톱 사이트의 페이지에서 일반 콘텐츠를 게재하고 모바일 버전의 사이트 페이지에서 오류 페이지를 게재하는 경우 이 페이지는 색인 생성에서 누락됩니다.
-   **모바일 버전에 URL 프래그먼트가 없어야 합니다.** URL의 프래그먼트 부분은 `#` 기호로 시작하는 URL의 끝부분입니다. 대부분 URL 프래그먼트는 색인 생성이 불가능하며 도메인에 모바일 중심 색인 생성을 사용 설정하고 나면 이러한 페이지는 색인에서 누락됩니다.
-   **여러 콘텐츠를 게재하는 데스크톱 버전은 이에 상응하는 모바일 버전이 있어야 합니다.** 여러 URL이 같은 URL(예: 휴대기기에 있는 홈페이지)로 리디렉션되는 경우 도메인에 모바일 중심 색인 생성을 사용 설정하면 이러한 모든 페이지는 색인에서 누락됩니다.
-   **[Search Console](https://search.google.com/search-console?hl=ko)에서 사이트의 두 버전을 모두 확인**하여 두 버전 모두에 관한 데이터와 메시지에 액세스할 수 있도록 합니다. Google에서 사이트의 색인 생성을 모바일 중심으로 전환할 때 데이터에 변동이 발생할 수도 있습니다.
-   **별도의 URL에 있는 `hreflang` 링크를 확인합니다.** [다국어화](https://developers.google.com/search/docs/specialty/international/managing-multi-regional-sites?hl=ko)에 `rel=hreflang` [`link` 링크 요소](https://developers.google.com/search/docs/specialty/international/localized-versions?hl=ko)를 사용하는 경우 모바일과 데스크톱 URL을 따로 연결합니다. 모바일 URL의 `hreflang`은 모바일 URL로 연결되고, 마찬가지로 데스크톱 URL `hreflang`은 데스크톱 URL로 연결되어야 합니다.
    
    다음은 모바일 및 데스크톱에서 별도의 URL을 사용하는 사이트 홈페이지의 `hreflang` 예입니다.
    
    [모바일](https://developers.google.com/search/docs/crawling-indexing/mobile/mobile-sites-mobile-first-indexing?hl=ko/#모바일)[데스크톱](https://developers.google.com/search/docs/crawling-indexing/mobile/mobile-sites-mobile-first-indexing?hl=ko/#데스크톱) 더보기
    
    다음 예에서 모바일 사이트 URL은 `https://m.example.com/`입니다.
    
    ```bash
    <link rel="canonical" href="https://example.com/">
    <link rel="alternate" hreflang="es" href="https://m.example.com/es/">
    <link rel="alternate" hreflang="fr" href="https://m.example.com/fr/">
    <link rel="alternate" hreflang="de" href="https://m.example.com/de/">
    <link rel="alternate" hreflang="th" href="https://m.example.com/th/">
    ```
    
    다음 예에서 데스크톱 사이트 URL은 `https://example.com/`입니다.
    
    ```bash
    <link rel="canonical" href="https://example.com/">
    <link rel="alternate" media="only screen and (max-width: 640px)" href="https://m.example.com/">
    <link rel="alternate" hreflang="es" href="https://example.com/es/">
    <link rel="alternate" hreflang="fr" href="https://example.com/fr/">
    <link rel="alternate" hreflang="de" href="https://example.com/de/">
    <link rel="alternate" hreflang="th" href="https://example.com/th/">
    ```
    
-   **모바일 사이트의 용량이 충분한지 확인합니다.** 용량은 사이트의 모바일 버전에서 [크롤링 속도](https://support.google.com/webmasters/answer/35253?hl=ko)의 잠재적 증가를 처리할 수 있는 정도여야 합니다.
-   **[robots.txt 규칙](https://developers.google.com/search/docs/crawling-indexing/robots/intro?hl=ko)**이 사이트의 두 버전 모두에서 정상적으로 작동하는지 확인합니다. robots.txt 파일을 사용하면 웹사이트에서 크롤링할 부분을 지정할 수 있습니다. 대부분 사이트의 모바일 버전과 데스크톱 버전에 동일한 robots.txt 규칙을 사용해야 합니다.
-   모바일 버전과 데스크톱 버전 사이에 **올바른 `rel=canonical` 및 `rel=alternate` 링크 요소 `link`를 사용**합니다. 데스크톱 URL이 항상 표준 URL이며, 모바일 버전은 해당 URL의 대체 URL입니다.
    
    별도 URL 사이트 설정을 위한 `rel=canonical` 및 `rel=alternate`의 예는 다음과 같습니다.
    
    [모바일](https://developers.google.com/search/docs/crawling-indexing/mobile/mobile-sites-mobile-first-indexing?hl=ko/#모바일)[데스크톱](https://developers.google.com/search/docs/crawling-indexing/mobile/mobile-sites-mobile-first-indexing?hl=ko/#데스크톱) 더보기
    
    이 예에서 모바일 사이트 URL은 `https://m.example.com/`이며 데스크톱 URL을 표준 URL로 표시하는 `link` 요소를 포함합니다.
    
    ```bash
    <link rel="canonical" href="https://example.com/">
    ```
    
    이 예에서 데스크톱 사이트 URL은 `https://example.com/`이며 해당 URL을 표준 URL로 표시하는 `link` 요소와 이 URL의 대체 버전으로 모바일 버전을 표시하는 다른 `link` 요소를 포함합니다.
    
    ```bash
    <link rel="canonical" href="https://example.com/">
    <link rel="alternate" media="only screen and (max-width: 640px)" href="https://m.example.com/">
    ```
    

## 문제 해결

사이트에서 모바일 중심 색인 생성이 사용 중지되거나 사이트에 모바일 중심 색인 생성을 사용 설정한 후 순위가 떨어지는 문제를 발생시킬 수 있는 가장 일반적인 오류는 다음과 같습니다. 사이트에 모바일 중심 색인 생성을 사용 설정하지 않았거나, 사이트에 모바일 중심 색인 생성을 사용 설정한 후 순위가 떨어졌거나 Search Console에서 메시지를 받았다면 다음 일반적인 오류 목록에서 해결할 수 있는 문제가 있는지 확인해 보세요.

| 오류 | 오류 |
|-------------------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| ### 구조화된 데이터 누락 | _error_ **문제 원인**: 데스크톱 페이지에 있는 구조화된 데이터 마크업의 일부가 모바일 페이지에는 없습니다.

_done_ **문제 해결**

1.  구조화된 데이터가 사이트의 데스크톱 버전과 모바일 버전 모두에 있는지 확인합니다.
2.  모바일과 데스크톱 사이트의 구조화된 데이터가 동일한지 확인합니다.
3.  구조화된 데이터에 올바른 URL을 사용합니다. 모바일 버전의 구조화된 데이터에 포함된 URL을 올바른 URL로 업데이트해야 합니다.
4.  구조화된 데이터의 추출 오류를 확인합니다. [데이터 하이라이터](https://support.google.com/webmasters/answer/2692911?hl=ko)를 사용하여 구조화된 데이터를 제공하는 경우 [데이터 하이라이터 대시보드](https://www.google.com/webmasters/tools/data-highlighter?hl=ko)에서 추출 오류가 있는지 정기적으로 확인하세요.
5.  [URL 검사 도구](https://support.google.com/webmasters/answer/9012289?hl=ko)를 사용하여 렌더링된 페이지에 콘텐츠가 표시되는지 확인합니다. 렌더링된 페이지는 Google이 보는 페이지입니다. |
| ### 페이지의 `noindex` 태그 | _error_ **문제 원인**: `noindex` 태그로 인해 모바일 페이지의 색인 생성이 차단됐습니다.

_done_ **문제 해결**: 모바일 사이트와 데스크톱 사이트에서 동일한 robots `meta` 태그를 사용합니다. 모바일 페이지에 `noindex` 태그를 사용하지 마세요. 사용할 경우 사이트에 모바일 중심 색인 생성이 사용 설정되면 Google에서 페이지의 색인을 생성하지 않습니다. |
| ### 이미지 누락 | _error_ **문제 원인**: 데스크톱 페이지에 있는 중요한 이미지의 일부가 모바일 페이지에 없습니다.

_done_ **문제 해결**

1.  모바일 사이트에 데스크톱 사이트와 동일한 콘텐츠가 포함되어 있는지 확인합니다. 모바일 사이트에 데스크톱 사이트보다 적은 콘텐츠가 포함되어 있다면 모바일 사이트의 주 콘텐츠가 데스크톱 사이트에 상응하도록 모바일 사이트를 업데이트하는 것이 좋습니다. 모바일 사이트에 표시되는 콘텐츠만 색인 생성에 사용됩니다.
2.  모바일 사이트와 데스크톱 사이트에서 동일한 robots `meta` 태그를 사용합니다. 모바일 페이지에 `nofollow` 태그를 사용하지 마세요. 사용할 경우 사이트에 모바일 중심 색인 생성이 사용 설정되면 Google에서 페이지의 이미지를 크롤링하거나 색인을 생성하지 않습니다.
3.  [지원되는 이미지 형식 및 태그](https://developers.google.com/search/docs/appearance/google-images?hl=ko#supported-image-formats)를 사용합니다. 예를 들어 Google에서 SVG 형식 이미지는 지원하지만 Google의 시스템에서 인라인 SVG 내의 `<image>` 태그에 있는 .jpg 이미지 색인을 생성할 수 없습니다.
4.  사용자 상호작용 시 주 콘텐츠에 지연 로드 방식을 사용하지 않습니다. Google은 로드하기 위해 사용자 상호작용(예: 스와이프, 클릭, 입력)이 필요한 콘텐츠를 로드하지 않습니다. [Google에서 지연 로드 콘텐츠를 볼 수 있어야 합니다](https://developers.google.com/search/docs/crawling-indexing/javascript/lazy-loading?hl=ko). |
| ### 차단된 이미지 | _error_ **문제 원인**: robots.txt로 인해 모바일 페이지에 있는 중요한 이미지가 차단되었습니다.

_done_ **문제 해결**: Google에서 리소스를 크롤링할 수 있도록 합니다. 일부 이미지의 경우 모바일 사이트와 데스크톱 사이트의 URL이 다릅니다. Google에서 URL을 크롤링하도록 하려면 [`disallow` 규칙](https://developers.google.com/search/doc/crawling-indexing/robots/robots_txt?hl=ko#disallow)으로 URL을 차단하지 마세요. |
| ### 품질이 낮은 이미지 | _error_ **문제 원인**: 모바일 페이지의 중요한 이미지가 너무 작거나 해상도가 낮습니다.

_done_ **문제 해결**: [고화질 이미지](https://developers.google.com/search/docs/appearance/google-images?hl=ko#good-quality-photos)를 제공합니다. 모바일 사이트에서 크기가 너무 작거나 해상도가 낮은 이미지는 사용하지 마세요. |
| ### 대체 텍스트 누락 | _error_ **문제 원인**: 모바일 페이지의 중요한 이미지에 대체 텍스트가 없습니다.

_done_ **문제 해결**: 데스크톱 사이트의 이미지와 동일한 [구체적인 대체 텍스트](https://developers.google.com/search/docs/appearance/google-images?hl=ko#descriptive-alt-text)를 모바일 사이트의 이미지에 사용합니다. |
| ### 페이지 제목 누락 | _error_ **문제 원인**: 모바일 페이지에 제목이 없습니다.

_done_ **문제 해결**: [제목](https://developers.google.com/search/docs/appearance/title-link?hl=ko#page-titles)과 [메타 설명](https://developers.google.com/search/docs/appearance/snippet?hl=ko#meta-descriptions)이 사이트의 두 버전에서 동일한지 확인합니다. |
| ### 메타 설명 누락 | _error_ **문제 원인**: 모바일 페이지에 메타 설명이 없습니다.

_done_ **문제 해결**: [제목](https://developers.google.com/search/docs/appearance/title-link?hl=ko#page-titles)과 [메타 설명](https://developers.google.com/search/docs/appearance/snippet?hl=ko#meta-descriptions)이 사이트의 두 버전에서 동일한지 확인합니다. |
| ### 모바일 URL이 오류 페이지임 | _error_ **문제 원인**: 모바일 페이지가 오류 페이지입니다.

_done_ **문제 해결**: 데스크톱 및 모바일 사이트에서 오류 페이지 상태가 동일한지 확인합니다. 데스크톱 사이트의 페이지에서 일반 콘텐츠를 게재하고 모바일 버전의 사이트 페이지에서 오류 페이지를 게재하는 경우 이 페이지는 색인 생성에서 누락됩니다. |
| ### 모바일 URL에 앵커 프래그먼트가 있음 | _error_ **문제 원인**: 모바일 URL에 앵커 프래그먼트가 포함되어 있습니다. Google에서는 프래그먼트가 포함된 URL의 색인을 생성할 수 없습니다.

_done_ **문제 해결**: 모바일 버전에 URL 프래그먼트가 없는지 확인합니다. 대부분 프래그먼트 URL은 색인 생성이 불가능하며 이러한 페이지는 도메인에 모바일 중심 색인 생성을 사용 설정하고 나면 색인에서 누락됩니다. |
| ### 모바일 페이지가 robots.txt로 차단됨 | _error_ **문제 원인**: robots.txt 규칙으로 인해 모바일 페이지가 차단되었습니다.

_done_ **문제 해결**: robots.txt 규칙과 robots `meta` 태그가 사이트의 두 버전에서 정상적으로 작동하는지 확인합니다. 사이트의 모바일 및 데스크톱 버전 모두에 동일한 robots.txt 규칙을 사용하세요. |
| ### 모바일 페이지 대상이 중복됨 | _error_ **문제 원인**: 여러 데스크톱 페이지가 동일한 모바일 페이지로 리디렉션됩니다.

_done_ **문제 해결**: 여러 콘텐츠를 게재하는 데스크톱 버전에 상응하는 모바일 버전이 있어야 합니다. 휴대기기에서 여러 URL이 동일한 URL로 리디렉션되는 경우 도메인에 모바일 중심 색인 생성을 사용 설정하면 이러한 모든 페이지는 색인에서 누락됩니다. |
| ### 데스크톱 사이트가 모바일 홈페이지로 리디렉션됨 | _error_ **문제 원인**: 데스크톱 사이트에 있는 대부분의 페이지 또는 모든 페이지가 모바일 사이트 홈페이지로 리디렉션됩니다.

_done_ **문제 해결**: 데스크톱 버전에 동일한 모바일 버전이 있어야 합니다. 서로 다른 URL이 휴대기기의 홈페이지로 리디렉션되는 경우 이러한 페이지는 도메인이 모바일 중심 색인 생성으로 이전되고 나면 색인에서 누락됩니다. |
| ### 페이지 품질 문제 | _error_ **문제 원인**: 모바일 페이지에 광고 문제가 있거나 페이지에서 콘텐츠, 제목 또는 이미지 설명 요소가 누락되었습니다.

_done_ **문제 해결**

1.  광고가 모바일 페이지 순위에 악영향을 주지 않도록 하세요. 휴대기기에 광고를 게재할 때는 [더 나은 광고 표준(Better Ads Standard)](https://www.betterads.org/standards/)을 따르세요.
2.  모바일 사이트에 데스크톱 사이트와 동일한 콘텐츠가 포함되어 있는지 확인합니다. 모바일 사이트에 데스크톱 사이트보다 적은 콘텐츠가 포함되어 있다면 모바일 사이트의 주 콘텐츠가 데스크톱 사이트에 상응하도록 모바일 사이트를 업데이트하는 것이 좋습니다. 모바일 사이트에 표시되는 콘텐츠만 색인 생성에 사용됩니다.
3.  데스크톱 사이트와 마찬가지로 모바일 사이트에도 명확하고 의미 있는 제목을 사용해야 합니다.
4.  모바일 사이트에서 이미지와 관련된 [구체적인 제목, 캡션, 파일 이름, 텍스트](https://developers.google.com/search/docs/appearance/google-images?hl=ko#descriptive-titles-captions-filenames)를 데스크톱 사이트와 동일하게 사용하세요. |
| ### 동영상 문제 | _error_ **문제 원인**: 모바일 페이지에 있는 동영상이 지원되지 않는 형식이거나, 찾기 힘든 위치에 있거나, 메타 설명이 누락되었거나, 매우 느리게 로드됩니다.

_done_ **문제 해결**

1.  [지원되는 동영상 형식](https://developers.google.com/search/docs/appearance/video?hl=ko#file-types)을 사용하고 지원되는 태그에 동영상을 배치합니다. 동영상은 페이지에서 `<video>`, `<embed>`, `<object>`와 같은 HTML 태그를 통해 식별됩니다.
2.  사용자 상호작용 시 주 콘텐츠에 지연 로드 방식을 사용하지 않습니다. Google은 로드하기 위해 사용자 상호작용(예: 스와이프, 클릭, 입력)이 필요한 콘텐츠를 로드하지 않습니다. [Google에서 지연 로드 콘텐츠를 볼 수 있어야 합니다](https://developers.google.com/search/docs/crawling-indexing/javascript/lazy-loading?hl=ko).
3.  모바일 사이트에서 쉽게 찾을 수 있는 위치에 동영상을 배치합니다. 예를 들어 사용자가 모바일 페이지에서 동영상을 찾기 위해 너무 아래로 스크롤해야 하는 경우 동영상 순위가 낮아질 수 있습니다. |
| ### 호스트 로드 문제 | _error_ **문제 원인**: 일부 호스트의 호스트 로드가 부족합니다.

_done_ **문제 해결**: 사이트의 모바일 버전에서 잠재적인 [크롤링 속도](https://support.google.com/webmasters/answer/35253?hl=ko) 증가를 처리할 수 있을 정도로 모바일 사이트의 용량이 충분한지 확인합니다. |