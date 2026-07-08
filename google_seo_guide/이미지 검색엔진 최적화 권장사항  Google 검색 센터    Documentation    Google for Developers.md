Google에서는 [텍스트 검색 결과 이미지](https://developers.google.com/search/docs/appearance/visual-elements-gallery?hl=ko#text-result-image), Google 디스커버, Google 이미지와 같이 사용자가 웹에서 시각적으로 정보를 찾도록 도움을 주는 여러 Google 검색 기능과 제품을 제공합니다. 각 기능 및 제품은 서로 다르게 보이지만, 해당 항목에 이미지를 표시하기 위한 일반적인 권장사항은 동일합니다.

![Google 검색결과, 이미지 탭, 디스커버의 이미지를 보여주는 그림](https://developers.google.com/static/search/docs/images/images-on-google.png?hl=ko)

다음 권장사항에 따라 Google 검색 결과에 표시되는 이미지를 최적화할 수 있습니다.

1.  [Google의 이미지 탐색 및 색인 생성 돕기](https://developers.google.com/search/docs/appearance/google-images?hl=ko#discover-images)
2.  [이미지 방문 페이지 최적화하기](https://developers.google.com/search/docs/appearance/google-images?hl=ko#optimize-landing-page)

## Google의 이미지 탐색 및 색인 생성 돕기

<iframe frameborder="0" allowfullscreen="" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share" referrerpolicy="strict-origin-when-cross-origin" width="640" height="360" src="https://www.youtube.com/embed/SfC27XgelgE?origin=https%3A%2F%2Fdevelopers.google.com&amp;autoplay&amp;controls&amp;embed_domain&amp;enablejsapi=1&amp;end&amp;hl&amp;showinfo&amp;start&amp;video-id=SfC27XgelgE&amp;widgetid=25&amp;forigin=https%3A%2F%2Fdevelopers.google.com%2Fsearch%2Fdocs%2Fappearance%2Fgoogle-images%3Fhl%3Dko&amp;aoriginsup=1&amp;gporigin=https%3A%2F%2Fdevelopers.google.com%2Fsearch%2Fdocs%2Fcrawling-indexing%2Famp%2Fabout-amp%3Fhl%3Dko&amp;vf=1" id="widget26" data-title="YouTube video player" title="SEO for Google Images"></iframe>

Google 검색 결과에 콘텐츠를 표시하기 위한 [기술 요구사항](https://developers.google.com/search/docs/essentials/technical?hl=ko)은 이미지에도 적용됩니다. 이미지는 HTML과 상당히 다른 형식이므로 이미지의 색인을 생성하려면 추가 요구사항이 있습니다. 예를 들어 사이트에서 이미지를 찾는 것이 다르고, 이미지 표시도 이미지의 색인 생성 여부와 알맞은 키워드에 영향을 줍니다.

### HTML 이미지 요소를 사용하여 이미지 삽입하기

표준 HTML 이미지 요소를 사용하면 크롤러가 이미지를 찾고 처리할 수 있습니다. Google에서 `<img>` 요소의 `src` 속성 이미지를 찾을 수 있음(`<picture>` 요소와 같이 다른 요소의 하위 요소인 경우에도) Google에서는 CSS 이미지의 색인을 생성하지 않습니다.

**맞는 예:**

> <img src="puppy.jpg" alt="골든 리트리버 강아지" />

**나쁜 예:**

> <div style="background-image:url(puppy.jpg)">골든 리트리버 강아지</div>

### 이미지 사이트맵 사용하기

[이미지 사이트맵을 제출](https://developers.google.com/search/docs/crawling-indexing/sitemaps/image-sitemaps?hl=ko)하여 Google이 다른 방법으로는 발견하지 못할 수도 있는 이미지의 URL을 제공하세요.

일반 사이트맵과 달리 이미지 사이트맵의 `<image:loc>` 요소에 다른 도메인의 URL을 포함할 수 있습니다. 따라서 콘텐츠 전송 네트워크(CDN)를 사용하여 이미지를 호스팅할 수 있습니다. CDN을 사용하는 경우 Google에서 알려 드릴 수 있도록 Search Console에서 CDN 도메인 이름의 [소유자를 확인](https://support.google.com/webmasters/answer/9008080?hl=ko)하세요.

### 반응형 이미지

반응형 웹페이지를 설계하면 사용자가 다양한 기기 유형에서 웹페이지에 액세스할 수 있으므로 더 나은 사용자 환경을 제공합니다. 웹사이트에서 이미지를 처리하기 위한 권장사항은 [반응형 이미지 가이드](https://web.dev/articles/responsive-images?hl=ko)에서 확인하세요.

웹페이지는 `img` 요소의 `<picture>` 요소 또는 `srcset` 속성을 사용하여 반응형 이미지를 지정합니다. 그러나 일부 브라우저와 크롤러는 이러한 속성을 인식하지 못하므로 항상 `src` 속성을 사용해 대체 URL을 지정하는 것이 좋습니다.

`srcset` 속성을 사용하면 화면 크기별로 같은 이미지의 서로 다른 버전을 지정할 수 있습니다. 예:

```php-template
<img
  srcset="maine-coon-nap-320w.jpg 320w, maine-coon-nap-480w.jpg 480w, maine-coon-nap-800w.jpg 800w"
  sizes="(max-width: 320px) 280px, (max-width: 480px) 440px, 800px"
  src="maine-coon-nap-800w.jpg"
  alt="A watercolor illustration of a maine coon napping leisurely in front of a fireplace">
```

`<picture>` 요소는 같은 이미지의 서로 다른 `<source>` 버전을 그룹화하는 데 사용되는 컨테이너입니다. 이 요소는 대체 접근방식을 지원하므로 브라우저에서 픽셀 밀도, 화면 크기 등 기기 기능에 따라 적절한 이미지를 선택할 수 있습니다. `picture` 요소는 아직 새 형식을 지원하지 않을 수 있는 클라이언트를 위한 단계적 성능 저하 기능이 내장된 새 이미지 형식을 사용할 때도 유용합니다.

[HTML 표준의 섹션 4.8.1](https://html.spec.whatwg.org/multipage/embedded-content.html#the-picture-element)에 따라 다음 형식을 사용하여 `picture` 요소를 사용할 때 대체용으로 `img` 요소를 `src` 속성과 함께 제공해야 합니다.

```bash
<picture>
  <source type="image/svg+xml" srcset="pyramid.svg">
  <source type="image/webp" srcset="pyramid.webp">
  <img src="pyramid.png" alt="An 1800s oil painting of The Great Pyramid">
</picture>
```

### 지원되는 이미지 형식 사용

Google 검색은 다음 파일 형식의 `img` 코드 `src` 속성에서 참조되는 이미지를 지원합니다. BMP, GIF, JPEG, PNG, WebP, SVG, AVIF파일 이름 확장자를 파일 형식과 일치시키는 것도 좋습니다.

이미지를 데이터 URI의 형식으로 인라인으로 삽입할 수도 있습니다. 데이터 URI를 사용하면 이미지와 같은 파일을 인라인으로 삽입할 수 있습니다. 다음 형식을 사용해 `img` 요소의 `src` 속성을 Base64로 인코딩된 문자열로 설정하세요.

```php-template
<img src="data:image/svg+xml;base64,[data]">
```

이미지를 인라인으로 삽입하면 HTTP 요청이 줄어들 수 있지만 페이지의 크기가 상당히 늘어날 수 있으므로 이를 신중하게 판단하여 사용합니다. 자세한 내용은 [web.dev 페이지에서의 인라인 이미지의 장점과 단점](https://web.dev/articles/responsive-images?hl=ko#inlining_pros_cons)을 참고하세요.

### 속도 및 품질 최적화하기

<iframe frameborder="0" allowfullscreen="" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share" referrerpolicy="strict-origin-when-cross-origin" width="640" height="360" src="https://www.youtube.com/embed/_6Tz_-3_4ok?origin=https%3A%2F%2Fdevelopers.google.com&amp;autoplay&amp;controls&amp;embed_domain&amp;enablejsapi=1&amp;end&amp;hl&amp;showinfo&amp;start&amp;video-id=_6Tz_-3_4ok&amp;widgetid=27&amp;forigin=https%3A%2F%2Fdevelopers.google.com%2Fsearch%2Fdocs%2Fappearance%2Fgoogle-images%3Fhl%3Dko&amp;aoriginsup=1&amp;gporigin=https%3A%2F%2Fdevelopers.google.com%2Fsearch%2Fdocs%2Fcrawling-indexing%2Famp%2Fabout-amp%3Fhl%3Dko&amp;vf=1" id="widget28" data-title="YouTube video player" title="4 tips for faster images on your website"></iframe>

고화질 사진은 흐리고 선명하지 않은 이미지보다 사용자에게 매력적으로 다가갑니다. 또한 선명한 이미지는 검색 결과 썸네일 이미지에서 사용자에게 더 매력적으로 보이므로 사용자의 트래픽을 유도할 가능성이 높아질 수 있습니다. 즉, 이미지는 전체 페이지 크기를 결정하는 가장 큰 요인으로, 이미지로 인해 페이지가 느려지고 로드 비용이 높아질 수 있습니다. 속도가 빠른 양질의 사용자 환경을 제공하려면 [최신 이미지 최적화](https://web.dev/fast?hl=ko#optimize-your-images) 및 [반응형 이미지 기술](https://web.dev/learn/design?hl=ko)을 사용하세요.

[PageSpeed Insights](https://pagespeed.web.dev/?hl=ko)로 사이트 속도를 분석하고 [속도가 중요한 이유](https://web.dev/learn/performance/why-speed-matters?hl=ko)를 방문하여 웹사이트 성능을 향상하기 위한 권장사항과 기술을 알아보세요.

## 이미지 방문 페이지 최적화하기

즉시 명확해지는 것은 아니지만 이미지가 포함된 페이지의 콘텐츠와 메타데이터는 이미지가 Google 검색 결과에 표시되는 방법과 위치에 큰 영향을 미칠 수 있습니다.

### 메타데이터를 사용하여 선호하는 이미지 지정

Google의 이미지 미리보기 선택은 완전히 자동화되어 있으며, 다양한 소스를 고려하여 특정 페이지의 이미지를 Google에 표시할지 선택합니다 (예: [텍스트 검색 결과 이미지](https://developers.google.com/search/docs/appearance/visual-elements-gallery?hl=ko#text-result-image) 또는 디스커버의 미리보기 이미지).

다음 메타데이터 소스 중 하나를 통해 선호하는 이미지를 제공하여 이미지 선택에 영향을 미칠 수 있습니다.

-   `URL` 또는 `ImageObject`를 사용하여 schema.org [`primaryImageOfPage`](https://schema.org/primaryImageOfPage) 속성을 지정합니다.
    
    ```php-template
    <script type="application/ld+json">{
      "@context": "https://schema.org",
      "@type": "WebPage",
      "url": "https://example.com/url",
      "primaryImageOfPage": "https://example.com/images/cat.png"
    }</script>
    ```
    
    또는 이미지 `URL` 또는 `ImageObject` 속성을 지정하고 이를 기본 항목에 연결합니다 (schema.org [`mainEntity`](https://schema.org/mainEntity) 또는 [`mainEntityOfPage`](https://schema.org/mainEntityOfPage) 속성 사용).
    
    ```php-template
    <script type="application/ld+json">{
      "@context": "https://schema.org",
      "@type": "BlogPosting",
      "mainEntityOfPage": "https://example.com/url",
      "image": "https://example.com/images/cat.png"
    }</script>
    ```
    
-   [`og:image`](https://ogp.me/) `meta` 태그를 지정합니다.
    
    ```php-template
    <meta property="og:image" content="https://example.com/images/cat.png">
    ```
    

schema.org 마크업 또는 `og:image` `meta` 태그에 사용할 이미지를 선택할 때는 다음 권장사항을 따르세요.

-   페이지와 관련이 있고 페이지를 대표하는 이미지를 선택합니다.
-   일반 이미지 (예: 사이트 로고) 또는 schema.org 마크업이나 `og:image` `meta` 태그에 텍스트가 포함된 이미지는 사용하지 마세요.
-   가로세로 비율이 극단적인 이미지 (예: 너무 좁거나 지나치게 넓은 이미지)는 사용하지 마세요.
-   가능하면 고해상도를 사용하세요.

### 페이지 제목 및 설명 확인하기

Google 검색은 각 검색 결과를 가장 효과적으로 설명하고 사용자 검색어와 검색 결과의 연관성을 보여 주는 제목 링크와 스니펫을 자동 생성합니다. 이렇게 하면 사용자가 검색 결과를 클릭할지 결정하는 데 도움이 됩니다. 다음은 Google 검색 결과 페이지에서 제목 링크와 스니펫이 어떻게 표시되는지 보여주는 예입니다.

![이미지 검색 결과의 제목과 설명을 보여주는 그림](https://developers.google.com/static/search/docs/images/titles-descriptions-in-image-results.png?hl=ko)

Google에서는 각 페이지의 `title`과 `meta` 태그에 포함된 정보 등의 다양한 소스를 사용하여 이러한 정보를 생성합니다.

Google의 [제목](https://developers.google.com/search/docs/appearance/title-link?hl=ko) 및 [스니펫](https://developers.google.com/search/docs/appearance/snippet?hl=ko) 가이드라인을 따르면 페이지를 설명하는 제목 링크 및 스니펫의 품질을 향상시킬 수 있습니다.

### 구조화된 데이터 추가하기

구조화된 데이터를 추가하면 Google에서 이미지를 Google 이미지의 [눈에 잘 띄는 배지](https://developers.google.com/search/blog/2017/08/badges-on-image-search-help-users-find?hl=ko)와 같은 [리치 결과](https://developers.google.com/search/docs/appearance/structured-data/search-gallery?hl=ko)로 표시할 수 있습니다. 이렇게 하면 사용자에게 페이지에 관해 유용한 정보를 제공하고, 더욱 효과적으로 타겟팅된 트래픽을 사이트로 유도할 수 있습니다.

[구조화된 데이터에 관한 일반적인 가이드라인](https://developers.google.com/search/docs/appearance/structured-data/sd-policies?hl=ko) 및 사용 중인 구조화된 데이터에 해당하는 가이드라인을 준수하세요. 그러지 않으면 구조화된 데이터가 Google 이미지에 리치 결과로 표시되지 못할 수도 있습니다. Google 이미지에서 배지 및 리치 결과를 표시하려면 각 구조화된 데이터 유형에 이미지 속성이 있어야 합니다. 다음은 Google 이미지에서 리치 결과가 표시되는 방식을 보여주는 두 가지 예입니다.

![리치 결과가 Google 이미지에 어떻게 표시되는지 보여주는 그림](https://developers.google.com/static/search/docs/images/structured-data-in-image-results.png?hl=ko)

### 구체적인 파일 이름, 제목, 대체 텍스트 사용

Google에서는 캡션 및 이미지 제목을 비롯한 페이지 콘텐츠에서 이미지 주제에 관한 정보를 추출합니다. 가능한 경우 이미지를 관련 텍스트 근처와 이미지 주제와 관련 있는 페이지에 배치하세요.

파일 이름도 마찬가지로 Google에서 이미지 주제를 간단하게 파악하는 데 도움이 됩니다. 가능한 경우 짧지만 충분한 설명이 담긴 파일 이름을 사용하세요. 예를 들어 `my-new-black-kitten.jpg`이 `IMG00023.JPG`보다 더 좋습니다. 가능한 경우 `image1.jpg`, `pic.gif`, `1.jpg`와 같은 일반적인 파일 이름은 사용하지 마세요. 사이트에 수천 개의 이미지가 있으면 이미지의 이름을 자동 지정하는 것이 좋습니다. 이미지를 현지화하는 경우 파일 이름도 번역해야 합니다. 라틴어 이외의 문자 또는 특수문자를 사용하는 경우 [URL 인코딩 가이드라인](https://developers.google.com/search/docs/crawling-indexing/url-structure?hl=ko)을 준수하세요.

<iframe frameborder="0" allowfullscreen="" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share" referrerpolicy="strict-origin-when-cross-origin" width="640" height="360" src="https://www.youtube.com/embed/3NbuDpB_BTc?origin=https%3A%2F%2Fdevelopers.google.com&amp;autoplay&amp;controls&amp;embed_domain&amp;enablejsapi=1&amp;end&amp;hl&amp;showinfo&amp;start&amp;video-id=3NbuDpB_BTc&amp;widgetid=29&amp;forigin=https%3A%2F%2Fdevelopers.google.com%2Fsearch%2Fdocs%2Fappearance%2Fgoogle-images%3Fhl%3Dko&amp;aoriginsup=1&amp;gporigin=https%3A%2F%2Fdevelopers.google.com%2Fsearch%2Fdocs%2Fcrawling-indexing%2Famp%2Fabout-amp%3Fhl%3Dko&amp;vf=1" id="widget30" data-title="YouTube video player" title="Matt Cutts discusses the alt attribute"></iframe>

이미지에 더 많은 메타데이터를 제공할 때 가장 중요한 속성은 대체 텍스트(이미지를 설명하는 텍스트)로 스크린 리더를 사용하거나 낮은 대역폭 연결을 사용하는 사용자를 비롯하여 웹페이지에서 이미지를 볼 수 없는 사람들의 접근성도 향상합니다.

Google은 대체 텍스트와 함께 컴퓨터 비전 알고리즘과 페이지 콘텐츠를 사용하여 이미지의 주제를 파악합니다. 또한 이미지의 대체 텍스트는 이미지를 링크로 사용할 때 앵커 텍스트로 활용할 수 있습니다.

대체 텍스트를 작성할 때는 키워드를 적절히 사용하고 페이지 콘텐츠의 맥락에 맞는 유용하고 정보가 풍부한 콘텐츠를 만드는 데 중점을 두세요. `alt` 속성을 키워드로 채우는 것([유인 키워드 반복](https://developers.google.com/search/docs/essentials/spam-policies?hl=ko#keyword-stuffing))은 좋지 않습니다. 사용자 환경에 악영향을 미치고 스팸 사이트로 간주될 수 있기 때문입니다.

**나쁜 예(대체 텍스트 누락됨)**:

> <img src="puppy.jpg"/>

**나쁜 예(유인 키워드 반복)**:

> <img src="puppy.jpg" alt="강아지 개 아기 강아지 멍멍이 애완견 새끼 강아지 리트리버 래브라도 울프하운드 세터 포인터 강아지 잭 러셀 테리어 강아지 개 사료 저렴한 개 사료 강아지 먹이"/>

**좋은 예**:

> <img src="puppy.jpg" alt="강아지"/>

**가장 좋은 예**:

> <img src="puppy.jpg" alt="가져오기 놀이를 하는 새끼 달마시안"/>

또한 [W3 가이드라인](https://www.w3.org/WAI/tutorials/images/)에 따라 대체 텍스트의 접근성을 고려합니다. `<img>` 요소의 경우 요소의 `alt` 속성을 추가할 수 있고 인라인 `<svg>` 요소에는 `<title>` 요소를 사용할 수 있습니다. 예:

```php-template
<svg aria-labelledby="svgtitle1">
  <title id="svgtitle1">Googlebot wearing an apron and chef hat, struggling to make pancakes on the stovetop</title>
</svg>
```

[접근성을 검사](https://developer.chrome.com/docs/devtools/accessibility/reference?hl=ko)하고 [느린 네트워크 연결 에뮬레이터를 사용](https://developer.chrome.com/docs/devtools/network/reference?hl=ko#throttling)하여 콘텐츠를 테스트하는 것이 좋습니다.

대규모 웹사이트에 속한 여러 페이지에서 이미지가 참조되는 경우 [사이트의 전체 크롤링 예산](https://developers.google.com/search/docs/crawling-indexing/large-site-managing-crawl-budget?hl=ko)을 고려하세요. 특히 Google에서 이미지를 여러 번 요청하지 않고도 이미지를 캐시하고 재사용할 수 있도록 동일한 URL을 통해 이미지를 일관되게 참조합니다.

## Google 이미지 인라인 연결 선택 해제

원하는 경우 Google 이미지 검색결과에서 인라인 연결을 선택 해제하여 검색결과 페이지에 원본 크기의 이미지가 표시되지 않게 할 수 있습니다. **인라인 연결을 선택 해제하려면 다음 단계를 따르세요.**

1.  이미지가 요청되면 요청의 [HTTP 리퍼러 헤더](https://en.wikipedia.org/wiki/HTTP_referer)를 검사합니다.
2.  Google 도메인에서 받은 요청이 있으면 내용 없이 `200` HTTP 상태 코드 또는 `204` HTTP 상태 코드를 포함하여 응답합니다.

Google에서는 여전히 페이지를 크롤링하고 이미지를 확인할 수 있지만 크롤링 시 검색결과에 생성된 미리보기 이미지를 표시합니다. 이 설정은 언제든지 선택 해제할 수 있으며 웹사이트 이미지를 다시 처리하지 않아도 됩니다. 이 동작은 이미지 [클로킹](https://developers.google.com/search/docs/essentials/spam-policies?hl=ko#cloaking)으로 간주되지 않으며 직접 조치로 이어지지 않습니다.

[이미지가 검색 결과에 완전히 표시되지 않도록 차단](https://developers.google.com/search/docs/crawling-indexing/prevent-images-on-your-page?hl=ko)할 수도 있습니다.

## 세이프서치에 맞게 최적화하기

세이프서치는 Google 검색 결과에 선정적인 이미지, 동영상, 웹사이트를 표시, 흐리게 처리 또는 차단할지 지정하는 Google 사용자 계정 설정입니다. Google에서 사이트의 특성을 파악하여 적절한 경우 사이트에 세이프서치 필터를 적용할 수 있도록 합니다. [세이프서치 페이지 라벨 지정에 관해 자세히 알아보기](https://developers.google.com/search/docs/crawling-indexing/safesearch?hl=ko)