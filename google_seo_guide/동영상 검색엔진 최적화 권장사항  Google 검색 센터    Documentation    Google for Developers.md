## 동영상 검색엔진 최적화 권장사항

사이트에 동영상이 있는 경우 다음 동영상 SEO 권장사항을 따르세요. 더 많은 사용자가 Google의 동영상 검색 결과를 통해 내 사이트를 찾을 수 있습니다. 동영상은 기본 검색 결과 페이지, 동영상 모드, Google 이미지, [디스커버](https://developers.google.com/search/docs/appearance/google-discover?hl=ko) 등 Google의 여러 위치에 표시될 수 있습니다.

![Google 검색 결과, 동영상 탭, 디스커버의 동영상 콘텐츠](https://developers.google.com/static/search/docs/images/video-on-google.png?hl=ko)

Google에 표시될 수 있도록 다음 권장사항에 따라 동영상을 최적화하세요.

<iframe frameborder="0" allowfullscreen="" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share" referrerpolicy="strict-origin-when-cross-origin" width="640" height="360" src="https://www.youtube.com/embed/1Zqkz8Y_kFw?origin=https%3A%2F%2Fdevelopers.google.com&amp;autoplay&amp;controls&amp;embed_domain&amp;enablejsapi=1&amp;end&amp;hl&amp;showinfo&amp;start&amp;video-id=1Zqkz8Y_kFw&amp;widgetid=73&amp;forigin=https%3A%2F%2Fdevelopers.google.com%2Fsearch%2Fdocs%2Fappearance%2Fvideo%3Fhl%3Dko&amp;aoriginsup=1&amp;gporigin=https%3A%2F%2Fdevelopers.google.com%2Fsearch%2Fdocs%2Fcrawling-indexing%2Famp%2Fabout-amp%3Fhl%3Dko&amp;vf=1" id="widget74" data-title="YouTube video player" title="Video best practices for Google Search &amp; Discover"></iframe>

1.  [Google이 내 동영상을 찾을 수 있도록 돕기](https://developers.google.com/search/docs/appearance/video?hl=ko#help-google-find)
2.  [동영상 색인이 생성될 수 있는지 확인](https://developers.google.com/search/docs/appearance/video?hl=ko#indexing-criteria)
3.  [특정 동영상 기능 사용 설정](https://developers.google.com/search/docs/appearance/video?hl=ko#enable-search-features)
4.  [필요에 따라 동영상 삭제, 제한 또는 업데이트](https://developers.google.com/search/docs/appearance/video?hl=ko#remove)
5.  [Search Console로 동영상 모니터링](https://developers.google.com/search/docs/appearance/video?hl=ko#monitor)
6.  [동영상 문제 해결](https://developers.google.com/search/docs/appearance/video?hl=ko#troubleshoot)

Google 검색 결과에 콘텐츠를 표시하기 위한 [기술 요구사항](https://developers.google.com/search/docs/essentials/technical?hl=ko)은 동영상에도 적용됩니다. 동영상이 Google 검색에서 검색, 크롤링, 색인 생성될 수 있도록 하기 위한 추가 요구사항은 다음과 같습니다.

-   동영상을 삽입할 때 일반적으로 사용되는 HTML 요소를 사용합니다. Google은 `<video>`, `<embed>`, `<iframe>` 또는 `<object>` 요소에서 참조하는 동영상을 찾을 수 있습니다.
-   [프래그먼트 식별자](https://wikipedia.org/wiki/URI_fragment)를 사용하여 동영상을 로드하지 않습니다. Google 검색은 일반적으로 URL 프래그먼트를 지원하지 않기 때문입니다.
-   JavaScript를 사용하여 동영상을 삽입하는 경우 [URL 검사 도구에서 렌더링된 HTML에 표시](https://developers.google.com/search/docs/crawling-indexing/javascript/javascript-seo-basics?hl=ko)되는지 확인합니다.
-   미디어 API(예: [Media Source API](https://developer.mozilla.org/en-US/docs/Web/API/Media_Source_Extensions_API))를 사용하고 있다면 동영상에 관한 메타데이터를 제공하고 있는지 확인하는 것 외에도, 미디어 API 호출에 실패하더라도 HTML 동영상 컨테이너 요소가 여전히 삽입되는지 확인하세요. 이렇게 하면 미디어 API 호출에 문제가 있더라도 Google에서 동영상 컨테이너의 위치를 계속 찾을 수 있습니다.
-   동영상을 로드할 때 스와이프, 클릭, 입력과 같은 사용자 동작에만 의존하지 않습니다.

Google에서 동영상을 더 쉽게 찾을 수 있도록 동영상에 관한 메타데이터를 제공하는 것이 좋습니다. [구조화된 데이터](https://developers.google.com/search/docs/appearance/structured-data/video?hl=ko), [동영상 사이트맵](https://developers.google.com/search/docs/crawling-indexing/sitemaps/video-sitemaps?hl=ko), [Open Graph 프로토콜(OGP)](https://ogp.me/)을 지원합니다.

## 동영상 색인이 생성될 수 있는지 확인

동영상 기능을 사용하려면 동영상이 다음의 색인 생성 요구사항을 충족해야 합니다.

-   [보기 페이지](https://developers.google.com/search/docs/appearance/video?hl=ko#watch-page)의 색인이 생성되어야 합니다.
-   색인이 생성된 보기 페이지가 검색에서 우수한 실적을 보여야 동영상의 색인 생성이 고려될 수 있습니다.
-   동영상이 보기 페이지에 삽입되어야 합니다.
-   동영상은 다른 요소 뒤에 숨길 수 없습니다.
-   동영상에 [안정적인 URL](https://developers.google.com/search/docs/appearance/video?hl=ko#stable-url)에서 사용 가능한 [유효한 썸네일](https://developers.google.com/search/docs/appearance/video?hl=ko#valid-thumbnail)이 있어야 합니다.

### 지원되는 동영상 파일 형식 사용

동영상 기능을 사용하려면 지원되는 동영상 파일 형식을 사용하세요. Google은 3GP, 3G2, ASF, AVI, DivX, M2V, M3U, M3U8, M4V, MKV, MOV, MP4, MPEG, OGV, QVT, RAM, RM, VOB, WebM, WMV, XAP동영상 파일 형식을 가져올 수 있습니다.

[데이터 URL](https://developer.mozilla.org/en-US/docs/Web/HTTP/Basics_of_HTTP/Data_URLs)은 지원되지 않습니다.

### 안정적인 URL 사용

일부 CDN은 빠르게 만료되는 URL을 사용합니다. 동영상의 썸네일 URL이 너무 자주 변경되면 Google에서 동영상 색인을 생성하지 못할 수 있습니다. 동영상의 색인이 생성되도록 하려면 각 동영상에 고유하고 안정적인 썸네일 URL 하나를 사용하세요.

동영상이 주요 순간 및 동영상 미리보기와 같은 [특정 기능을 사용할 수](https://developers.google.com/search/docs/appearance/video?hl=ko#enable-search-features) 있도록 하려면 동영상 파일을 안정적인 URL에서 사용할 수 있도록 해야 합니다. 이렇게 하면 Google에서 동영상을 일관되게 발견 및 처리하고, 동영상이 여전히 사용 가능한 상태인 수 있는지 확인하고, 동영상에서 신호를 수집할 수 있습니다.

악의적인 행위자(예: 해커 또는 스팸 발생자)가 콘텐츠에 액세스하는 것이 우려되는 경우 미디어 URL의 안정적인 버전을 표시하기 전에 [Googlebot을 확인](https://developers.google.com/search/docs/crawling-indexing/verifying-googlebot?hl=ko)할 수 있습니다. 예를 들어 [`contentUrl`](https://developers.google.com/search/docs/appearance/structured-data/video?hl=ko#content-url) 속성을 Googlebot과 같은 신뢰할 수 있는 크롤러에만 제공하고 페이지에 액세스하는 다른 클라이언트에는 이 필드가 표시되지 않도록 선택할 수 있습니다. 이 설정을 사용하면 신뢰할 수 있는 클라이언트만 동영상 파일의 위치에 액세스할 수 있습니다.

### 동영상별로 전용 보기 페이지 만들기

동영상 기능(기본 검색 결과 페이지의 동영상 결과, 동영상 모드, [주요 순간](https://developers.google.com/search/docs/appearance/video?hl=ko#key-moments), [라이브 배지](https://developers.google.com/search/docs/appearance/video?hl=ko#live-badge) 및 기타 리치 형식)을 사용하려면 비즈니스에 적합하다고 판단되는 경우 동영상별로 전용 보기 페이지를 만드세요.

![동영상이 페이지의 주요 콘텐츠인 웹페이지](https://developers.google.com/static/search/docs/images/dedicated-video-page.png?hl=ko)

_보기 페이지_의 주목적은 사용자에게 단일 동영상을 표시하는 것입니다. 다음 페이지는 보기 페이지입니다. 사용자가 해당 페이지를 방문하는 주된 이유가 개별 동영상을 시청하기 위함이기 때문입니다.

-   동영상 방문 페이지
-   TV 에피소드 동영상 플레이어 페이지
-   뉴스 동영상 보기 페이지
-   스포츠 하이라이트 페이지
-   이벤트 클립 페이지

다음 페이지는 보기 페이지가 아닙니다. 동영상이 페이지의 나머지 콘텐츠를 보완하기 때문입니다.

-   삽입된 동영상을 리뷰하는 블로그 게시물
-   제품의 360도 동영상이 포함된 제품 페이지
-   가시도가 동일한 여러 동영상을 나열하는 동영상 카테고리 페이지
-   영화 트레일러가 삽입된 영화 리뷰 페이지

각 보기 페이지에 동영상별 페이지 제목과 설명이 있어야 합니다. 좋은 [제목](https://developers.google.com/search/docs/appearance/title-link?hl=ko#page-titles)과 [설명](https://developers.google.com/search/docs/appearance/snippet?hl=ko#meta-descriptions)을 작성하기 위한 권장사항을 참고하세요.

### 삽입된 서드 파티 플레이어 사용

웹사이트에 YouTube, Vimeo, Facebook 등 서드 파티 플랫폼의 동영상을 삽입하는 경우 Google에서 사용자의 웹페이지와 이에 상응하는 서드 파티 플랫폼의 페이지 둘 다에서 동영상의 색인을 생성할 수 있습니다. 페이지가 [동영상 색인 생성 기준](https://developers.google.com/search/docs/appearance/video?hl=ko#indexing-criteria)을 충족하는 한 두 가지 버전 모두 Google의 동영상 기능에 표시될 수 있습니다.

서드 파티 플레이어를 삽입한 본인의 보기 페이지에서 여전히 [구조화된 데이터를 제공](https://developers.google.com/search/docs/appearance/video?hl=ko#structured-data)하는 것이 좋고 [동영상 사이트맵](https://developers.google.com/search/docs/crawling-indexing/sitemaps/video-sitemaps?hl=ko)에 이 페이지를 포함할 수도 있습니다. 더 많은 동영상 기능을 사용하려면 동영상 호스트가 Google이 [동영상 파일을 가져오도록](https://developers.google.com/search/docs/appearance/video?hl=ko#allow-fetch) 허용하는지 확인하세요.

## 동영상 URL의 구분

동영상과 연결된 URL이 여러 개 있습니다. 다음은 주요 URL의 요약입니다.

![동영상 페이지의 URL](https://developers.google.com/static/search/docs/images/diagram-urls-in-page.png?hl=ko)

| 동영상과 관련된 URL | 동영상과 관련된 URL |
|--------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **1. 보기 페이지** | 동영상이 삽입된 보기 페이지의 URL입니다. 동영상 사이트맵을 사용하는 경우 이 URL은 `<loc>` 동영상 사이트맵 태그의 값입니다.

<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"
    xmlns:video="http://www.google.com/schemas/sitemap-video/1.1">
<url>
<loc>**https://example.com/videos/some_video_landing_page.html**</loc>
  <video:video>
  ... |
| **2. 동영상 플레이어** | 동영상의 특정 플레이어 URL입니다. 보기 페이지의 HTML 내 `<iframe>` 요소의 값이 `src`인 경우가 많습니다.

<iframe src="**https://example.com/videoplayer.php?video=123**" width="640" height="360" frameborder="0" allow="autoplay; fullscreen; picture-in-picture" allowfullscreen></iframe>

___

**URL을 제공하는 방법**

구조화된 데이터를 사용하는 경우 동영상 플레이어 URL을 `VideoObject.embedUrl` 속성 값으로 제공합니다.

"embedUrl": "**https://example.com/videoplayer.php?video=123**"

동영상 사이트맵을 사용하는 경우 동영상 플레이어 URL을 `<video:player_loc>` 태그 값으로 제공합니다.

<video:player_loc>**https://example.com/videoplayer.php?video=123**</video:player_loc> |
| **3. 동영상 파일** | 동영상 파일의 실제 콘텐츠 바이트 URL입니다. 삽입 사이트, CDN 또는 스트리밍 서비스에 호스팅될 수 있습니다.

`<object>` 요소에서 동영상 파일의 URL은 `data` 속성의 값입니다.

<object data="**https://streamserver.example.com/video/123/file.mp4**" width="400" height="300"></object>

`<video>` 요소에서 동영상 파일의 URL은 `<source>` 요소의 `src` 속성 값입니다.

<video controls width="250">
  <source src="**https://streamserver.example.com/video/123/file.webm**" type="video/webm" />
  <source src="**https://streamserver.example.com/video/123/file.mp4**" type="video/mp4" />
</video>

`<embed>` 요소에서 동영상 파일의 URL은 `src` 속성의 값입니다.

<embed type="video/webm" src="**https://streamserver.example.com/video/123/file.mp4**" width="400" height="300"></embed>

___

**URL을 제공하는 방법**

구조화된 데이터를 사용하는 경우 동영상 파일의 URL을 `VideoObject.contentUrl` 속성의 값으로 제공합니다.

"contentUrl": "**https://streamserver.example.com/video/123/file.mp4**"

동영상 사이트맵을 사용하는 경우 동영상 파일의 URL을 `<video:content_loc>` 태그 값으로 제공합니다.

<video:content_loc>**https://streamserver.example.com/video/123/file.mp4**</video:content_loc> |

### 고화질 동영상 썸네일 제공

동영상을 동영상 기능에 표시하려면 동영상에 올바른 썸네일 이미지가 있어야 합니다. [Google이 동영상 파일을 가져오도록 허용](https://developers.google.com/search/docs/appearance/video?hl=ko#allow-fetch)하면 Google에서 자동으로 썸네일을 생성하려고 시도합니다.

하지만 다음 메타데이터 소스 중 하나를 통해 선호하는 썸네일을 제공하여 동영상 기능에 표시되는 썸네일에 영향을 미칠 수 있습니다.

-   `<video>` HTML 요소를 사용하는 경우 `poster` 속성을 지정합니다.
-   동영상 사이트맵(mRSS 포함)에서 `<video:thumbnail_loc>` 태그(또는 각각 `<media:thumbnail>`)를 지정합니다.
-   구조화된 데이터의 경우 ``[`thumbnailUrl`](https://developers.google.com/search/docs/appearance/structured-data/video?hl=ko#thumbnail-url)`` 속성을 지정합니다.
-   [OGP](https://ogp.me/)의 경우 `og:video:image` 속성을 지정합니다.

여러 메타데이터 소스를 지정하는 경우(예: 사이트맵 및 구조화된 데이터 모두에서 썸네일 지정) 모든 메타데이터 전반에서 동영상별로 동일한 썸네일 URL을 사용해야 합니다.

| 동영상 썸네일 사양 | 동영상 썸네일 사양 |
|-------------|--------------------------------------------------------------------------------------------------------------------------------------|
| **지원되는 썸네일 형식** | BMP, GIF, JPEG, PNG, WebP, SVG, AVIF |
| **크기** | 최소 60x30픽셀이며, 클수록 좋습니다. |
| **위치** | 썸네일 파일은 Googlebot 및 Googlebot 이미지가 액세스할 수 있어야 합니다. 썸네일 파일을 [robots.txt](https://developers.google.com/search/docs/crawling-indexing/robots/intro?hl=ko) 또는 로그인으로 요구사항으로 가려서는 안 됩니다. [안정적인 URL](https://developers.google.com/search/docs/appearance/video?hl=ko#stable-url)에서 일관되게 파일을 사용할 수 있어야 합니다. |
| **투명성** | 썸네일 픽셀의 80% 이상은 알파(투명도) 값이 250보다 커야 합니다. |

### 구조화된 데이터에 일관되고 고유한 정보 제공

Google에 동영상이 표시되는 방식에 영향을 주려면 [구조화된 데이터](https://developers.google.com/search/docs/appearance/structured-data/video?hl=ko)로 동영상을 설명합니다. 반드시 구조화된 데이터에 제공하는 정보가 실제 동영상 콘텐츠 및 제공하는 기타 메타데이터와 일치해야 합니다. 사이트의 각 동영상에 `thumbnailUrl`, `name`, `description` 속성에 대한 고유한 정보를 제공해야 합니다.

## 특정 동영상 기능 사용 설정

### 동영상 미리보기

![검색결과의 동영상 미리보기](https://developers.google.com/static/search/docs/images/video-preview.gif?hl=ko)

Google에서는 사용자가 동영상의 내용을 더 잘 이해할 수 있도록 동영상에서 몇 초를 선택하여 이동 미리보기를 표시합니다. 동영상에 미리보기 기능을 사용하려면 [Google이 동영상 파일을 가져오도록 허용](https://developers.google.com/search/docs/appearance/video?hl=ko#allow-fetch)하세요. [`max-video-preview`](https://developers.google.com/search/docs/crawling-indexing/robots-meta-tag?hl=ko#max-video-preview) robots `meta` 태그를 사용하여 동영상 미리보기의 최대 길이를 설정할 수 있습니다.

### 중요한 부분

![검색결과에 중요한 부분이 표시된 동영상](https://developers.google.com/static/search/docs/images/video-key-moments.png?hl=ko)

중요한 부분 기능은 사용자가 책의 장처럼 동영상 세그먼트를 탐색하는 방법으로, 사용자의 콘텐츠 참여도를 높이는 데 도움이 됩니다. Google 검색에서는 자동으로 동영상의 세그먼트를 감지하여 사용자에게 중요한 부분을 표시하려고 하며, 개발자가 따로 취해야 할 조치는 없습니다. 또는 개발자가 동영상의 중요한 부분을 Google에 알려도 됩니다. 구조화된 데이터나 YouTube 설명을 통해 사용자가 설정한 중요한 부분에 우선순위가 부여됩니다.

-   **동영상이 웹페이지에 삽입되어 있거나 동영상 플랫폼을 운영하는 경우** 다음과 같은 두 가지 방법으로 중요한 부분을 사용 설정할 수 있습니다.
    -   [구조화된 `Clip` 데이터](https://developers.google.com/search/docs/appearance/structured-data/video?hl=ko#clip): 각 세그먼트의 시작 시간과 종료 시간을 정확하게 지정하고 각 세그먼트에 표시할 라벨을 지정합니다. 이 기능은 Google 검색이 서비스되는 모든 언어로 사용할 수 있습니다.
    -   [구조화된 `SeekToAction` 데이터](https://developers.google.com/search/docs/appearance/structured-data/video?hl=ko#seek): URL 구조의 일반적인 타임스탬프 위치를 Google에 알려 주면 Google에서 자동으로 중요한 부분을 식별해 동영상 내 해당 지점으로 사용자를 연결할 수 있습니다. 한국어, 영어, 스페인어, 포르투갈어, 이탈리아어, 중국어, 프랑스어, 일본어, 독일어, 터키어, 네덜란드어, 러시아어로 사용할 수 있습니다.
-   **동영상이 YouTube에 호스팅되는 경우** YouTube의 동영상 설명에 타임스탬프와 라벨을 정확히 지정합니다. [YouTube 설명에 타임스탬프를 표시하기 위한 권장사항](https://developers.google.com/search/docs/appearance/structured-data/video?hl=ko#best-practices-youtube)을 확인하세요. 이 기능은 Google 검색이 서비스되는 모든 언어로 사용할 수 있습니다. YouTube에서 동영상 챕터를 사용 설정하려면 다음 [추가 가이드라인](https://support.google.com/youtube/answer/9884579?hl=ko)을 따르세요.

중요한 부분 기능을 완전히 선택 해제하려면(동영상의 중요한 부분을 자동으로 표시하기 위해 Google에서 할 수 있는 모든 작업 포함) [`nosnippet`](https://developers.google.com/search/docs/appearance/snippet?hl=ko#nosnippet) `meta` 태그를 사용하세요.

### 실시간 배지

![검색결과에 실시간 배지가 표시된 동영상](https://developers.google.com/static/search/docs/images/video-livestream.png?hl=ko)

실시간 스트리밍 동영상의 경우 [`BroadcastEvent` 구조화된 데이터](https://developers.google.com/search/docs/appearance/structured-data/video?hl=ko#broadcast-event)를 사용하여 검색 결과에 빨간색 '실시간' 배지를 표시할 수 있습니다.

## Google이 내 동영상 파일을 가져오도록 허용

Google은 동영상 파일의 실제 바이트를 가져와서 [동영상 미리보기](https://developers.google.com/search/docs/appearance/video?hl=ko#video-previews), [주요 순간](https://developers.google.com/search/docs/appearance/video?hl=ko#key-moments)과 같은 기능을 사용 가능하도록 할 수 있습니다.

다음 권장사항에 따라 Google이 동영상 파일을 찾아 가져오도록 허용하세요.

-   Google이 동영상의 스트리밍 파일 URL(예: M3U8)을 가져오도록 허용합니다. [`noindex`](https://developers.google.com/search/docs/crawling-indexing/block-indexing?hl=ko) 규칙 또는 [robots.txt](https://developers.google.com/search/docs/crawling-indexing/robots/intro?hl=ko) 파일이 포함된 실제 동영상 바이트 URL을 차단하지 않습니다.
-   동영상 파일은 [안정적인 URL](https://developers.google.com/search/docs/appearance/video?hl=ko#stable-url)에서 사용할 수 있어야 합니다.
-   구조화된 데이터를 사용하여 [지원되는 파일 형식](https://developers.google.com/search/docs/appearance/video?hl=ko#supported-video-files)의 [`contentURL`](https://developers.google.com/search/docs/appearance/structured-data/video?hl=ko#content-url) 값을 제공합니다.
-   동영상 보기 페이지의 호스트와 실제 동영상을 스트리밍하는 서버에는 크롤링을 지원하기에 충분한 서버 리소스가 있어야 합니다. 따라서 `example.com/puppies.html`의 방문 페이지에 `streamserver.example.com`에서 제공하는 강아지 동영상이 삽입되어 있는 경우 `example.com` 및 `streamserver.example.com` 모두 [Google 검색의 기술 요구사항](https://developers.google.com/search/docs/essentials/technical?hl=ko)을 충족하고 [사용 가능한 서버 용량](https://developers.google.com/search/docs/crawling-indexing/troubleshoot-crawling-errors?hl=ko#availability_issues)이 있어야 합니다.

## 동영상 삭제 또는 제한

### 동영상 삭제

사이트에서 동영상을 삭제하려면 다음 중 하나를 따르세요.

-   삭제되었거나 만료된 동영상이 삽입된 보기 페이지에 **`404 (Not found)`를 반환**합니다. `404` 응답 코드 외에도 페이지의 HTML을 반환하여 대부분의 사용자에게 변경사항을 투명하게 공개할 수 있습니다.
-   삭제되거나 만료된 동영상을 삽입하는 보기 페이지에 **[`noindex`](https://developers.google.com/search/docs/crawling-indexing/robots-meta-tag?hl=ko) robots `meta` 태그를 포함**합니다. 이렇게 하면 방문 페이지의 색인이 생성되지 않도록 차단할 수 있습니다.
-   구조화된 데이터([`expires`](https://developers.google.com/search/docs/appearance/structured-data/video?hl=ko#expires) 속성) 또는 동영상 사이트맵(`<video:expiration_date>` 요소 사용)에 **만료일을 명시**합니다. 동영상의 만료일이 2009년 11월인 동영상 사이트맵 예는 다음과 같습니다.
    
    ```php-template
    <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"
        xmlns:video="http://www.google.com/schemas/sitemap-video/1.1">
    <url>
    <loc>https://example.com/videos/some_video_landing_page.html</loc>
    <video:video>
      <video:thumbnail_loc>
          https://example.com/thumbs/123.jpg
      </video:thumbnail_loc>
      <video:title>
          Grilling steaks for summer
      </video:title>
      <video:description>
          Bob shows you how to grill steaks perfectly every time
      </video:description>
      <video:player_loc>
          https://example.com/videoplayer?video=123
      </video:player_loc>
      <video:expiration_date>2009-11-05T19:20:30+08:00</video:expiration_date>
    </video:video>
    </url>
    </urlset>
    ```
    

동영상의 만료일이 과거 날짜이면 동영상 검색 결과에 동영상이 표시되지 않습니다. 보기 페이지는 동영상 썸네일 없이 텍스트 검색 결과로 계속 표시될 수 있습니다. 여기에는 사이트맵, 구조화된 데이터, [`meta` 태그](https://developers.google.com/search/docs/crawling-indexing/robots-meta-tag?hl=ko#unavailable-after)의 만료일이 포함됩니다. 각 동영상의 만료일이 올바른지 확인하세요. 만료일 후 더 이상 사용할 수 없는 동영상이라면 유용하지만 이렇게 하면 사용 가능한 동영상에 실수로 과거 날짜를 설정하기 쉽습니다. 만료되지 않는 동영상에는 만료 정보를 포함하지 마세요.

### 사용자의 위치에 따라 동영상 제한

사용자의 위치에 따라 동영상의 검색결과를 제한할 수 있습니다. 국가 제한이 없는 동영상의 경우 국가 제한 태그를 생략하세요.

#### 구조화된 데이터를 사용하여 제한

[`VideoObject` 구조화된 데이터](https://developers.google.com/search/docs/appearance/structured-data/video?hl=ko)를 사용하여 동영상을 설명한다면 [`regionsAllowed`](https://developers.google.com/search/docs/appearance/structured-data/video?hl=ko#regions-allowed) 속성을 설정하여 동영상 검색 결과가 표시될 지역을 지정하세요. 이 속성을 생략하면 모든 지역의 검색결과에 동영상이 표시될 수 있습니다.

또는 [`ineligibleRegion`](https://developers.google.com/search/docs/appearance/structured-data/video?hl=ko#ineligible-region) 속성을 사용하여 동영상 검색 결과를 가져올 수 없는 지역을 지정할 수 있습니다.

#### 동영상 사이트맵을 사용하여 제한

동영상 사이트맵에서 [`<video:restriction>`](https://developers.google.com/search/docs/crawling-indexing/sitemaps/video-sitemaps?hl=ko#country-restriction) 태그를 사용하면 지정된 국가에서의 동영상 표시를 허용하거나 거부할 수 있습니다. `<video:restriction>` 태그는 동영상 항목마다 한 개씩만 허용됩니다.

`<video:restriction>` 태그에는 공백으로 구분된 [ISO 3166-1 두 자리 또는 세 자리 국가 코드](https://en.wikipedia.org/wiki/ISO_3166-1)가 하나 이상 포함되어 있어야 합니다. 필수 `relationship` 속성은 제한 유형을 지정합니다.

-   `relationship="allow"`: 지정된 국가에서만 동영상이 표시됩니다. 국가를 지정하지 않으면 어떤 국가에서도 동영상이 표시되지 않습니다.
-   `relationship="deny"`: 지정된 국가를 제외한 모든 국가에서 동영상이 표시됩니다. 국가를 지정하지 않으면 모든 국가에서 동영상이 표시됩니다.

이 동영상 사이트맵 예에서 동영상은 캐나다와 멕시코에서만 검색결과에 표시됩니다.

```php-template
<url>
  <loc>https://example.com/videos/some_video_landing_page.html</loc>
  <video:video>
    <video:thumbnail_loc>
            https://example.com/thumbs/123.jpg
    </video:thumbnail_loc>
    <video:title>Grilling steaks for summer</video:title>
    <video:description>
        Bob shows you how to get perfectly done steaks every time
    </video:description>
    <video:player_loc>
          https://example.com/player?video=123
    </video:player_loc>
    <video:restriction relationship="allow">ca mx</video:restriction>
  </video:video>
</url>
```

## 세이프서치에 맞게 최적화하기

세이프서치는 Google 검색 결과에 선정적인 이미지, 동영상, 웹사이트를 표시할지 차단할지 지정하는 Google 사용자 계정 설정입니다. Google에서 사이트의 특성을 파악하여 적절한 경우 사이트에 세이프서치 필터를 적용할 수 있도록 합니다. [세이프서치 페이지 라벨 지정에 관해 자세히 알아보기](https://developers.google.com/search/docs/crawling-indexing/safesearch?hl=ko)

## Search Console로 동영상 보기 페이지 모니터링

다음 Search Console 보고서 및 도구를 사용하면 Google 검색에서 동영상 콘텐츠의 실적을 모니터링하고 최적화할 수 있습니다.

-   [동영상 색인 생성 보고서](https://support.google.com/webmasters/answer/9495631?hl=ko): 색인이 생성된 보기 페이지 중 색인 생성된 동영상이 포함된 보기 페이지 수와 다른 동영상의 색인이 생성되지 않은 이유를 확인합니다.
-   [동영상 리치 결과 보고서](https://support.google.com/webmasters/answer/7552505?hl=ko): `VideoObject` 구조화된 데이터 구현 관련 문제를 검토하고 수정합니다.
-   [실적 보고서](https://support.google.com/webmasters/answer/7576553?hl=ko#by_search_appearance&zippy=,search-appearance): 동영상 검색 노출 필터를 사용하여 Google 검색에서의 동영상 실적을 모니터링합니다.

## 동영상 문제 해결

Search Console을 사용하여 동영상 문제를 해결할 수 있습니다. 도움이 필요한 경우 [동영상 문제 해결 가이드](https://support.google.com/webmasters/answer/9495631?hl=ko#troubleshooting)를 참고하세요.