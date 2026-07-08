![Google 검색 결과의 웹 스토리를 보여주는 그림](https://developers.google.com/static/search/docs/images/web-stories-single-result.png?hl=ko)

웹 스토리는 동영상, 오디오, 이미지, 애니메이션, 텍스트를 조합하여 동적 소비 환경을 만드는 웹 기반 버전의 인기 '스토리' 형식입니다. 이 시각적 형식을 사용하면 콘텐츠를 탭하거나 한 콘텐츠에서 다음 콘텐츠로 스와이프하여 원하는 속도로 콘텐츠를 탐색할 수 있습니다.

이 가이드에서는 [디스커버](https://developers.google.com/search/docs/appearance/google-discover?hl=ko)를 비롯한 웹 스토리가 Google 검색에 표시되도록 하는 방법을 설명합니다.

다음은 Google에서 웹 스토리를 사용 설정하는 방법의 개요입니다.

1.  [웹 스토리 만들기](https://developers.google.com/search/docs/appearance/enable-web-stories?hl=ko#create)
2.  [웹 스토리가 유효한 AMP인지 확인](https://developers.google.com/search/docs/appearance/enable-web-stories?hl=ko#valid-amp)
3.  [메타데이터 확인](https://developers.google.com/search/docs/appearance/enable-web-stories?hl=ko#metadata)
4.  [웹 스토리의 색인이 생성되었는지 확인](https://developers.google.com/search/docs/appearance/enable-web-stories?hl=ko#indexed)
5.  [웹 스토리 콘텐츠 정책](https://developers.google.com/search/docs/guides/web-stories-content-policy?hl=ko) 준수

## 기능 제공 여부

웹 스토리는 Google 검색에서 하나의 검색 결과로 표시될 수 있으며, Google 검색이 제공되는 모든 지역 및 언어에서 사용할 수 있습니다.

디스커버 피드에 웹 스토리가 단일 카드로 표시되어 스토리를 탭하여 살펴볼 수 있습니다. Google 디스커버를 사용할 수 있는 모든 지역 및 언어에서 사용할 수 있지만 미국, 브라질, 인도에서 표시될 가능성이 가장 높습니다.

## 웹 스토리 만들기

웹 스토리는 근본적으로는 웹페이지이므로 일반 웹페이지 게시에 적용되는 가이드라인과 권장사항을 따라야 합니다. 다음 두 가지 방법으로 시작하면 됩니다.

-   코딩 없이 스토리를 만들려면 여러 [스토리 편집기 도구](https://amp.dev/documentation/tools/stories/) 중 하나를 선택합니다.
-   엔지니어링 리소스가 있는 경우 [AMP를 시작](https://amp.dev/about/stories)할 수 있습니다. 웹 스토리가 적절히 렌더링되도록 하려면 [Chrome 개발자 도구](https://developers.google.com/web/tools/chrome-devtools/device-mode?hl=ko#device)를 사용하여 다양한 기기 크기와 형식을 시뮬레이션하는 것이 좋습니다.

프로세스를 원활하게 하려면 [웹 스토리 만들기 권장사항](https://developers.google.com/search/docs/guides/web-stories-creation-best-practices?hl=ko)을 검토하세요.

<iframe frameborder="0" allowfullscreen="" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share" referrerpolicy="strict-origin-when-cross-origin" width="640" height="360" src="https://www.youtube.com/embed/uzRHCXKQZY4?origin=https%3A%2F%2Fdevelopers.google.com&amp;autoplay&amp;controls&amp;embed_domain&amp;enablejsapi=1&amp;end&amp;hl&amp;showinfo&amp;start&amp;video-id=uzRHCXKQZY4&amp;widgetid=81&amp;forigin=https%3A%2F%2Fdevelopers.google.com%2Fsearch%2Fdocs%2Fappearance%2Fenable-web-stories%3Fhl%3Dko&amp;aoriginsup=1&amp;gporigin=https%3A%2F%2Fdevelopers.google.com%2Fsearch%2Fdocs%2Fcrawling-indexing%2Famp%2Fabout-amp%3Fhl%3Dko&amp;vf=1" id="widget82" data-title="YouTube video player" title="Getting started with Web Stories"></iframe>

## 웹 스토리가 유효한 AMP인지 확인

스토리를 만든 후 웹 스토리가 유효한 AMP인지 확인해야 합니다. 유효한 AMP 스토리는 다양한 [AMP 사양](https://amp.dev/documentation/guides-and-tutorials/learn/webstory_technical_details/)을 준수합니다. 이렇게 하면 최적의 성능과 최고의 환경을 제공할 수 있습니다. 다음 도구를 사용하여 웹 스토리가 유효한 AMP인지 확인할 수 있습니다.

-   [웹 스토리 Google 테스트 도구](https://search.google.com/test/amp?hl=ko): 웹 스토리가 유효한지 확인합니다.
-   [URL 검사 도구](https://support.google.com/webmasters/answer/9012289?hl=ko): 웹 스토리가 유효한 AMP인지 확인하고 URL의 Google 색인 생성 상태를 확인합니다.
-   [AMP Linter](https://github.com/ampproject/amp-toolbox/tree/main/packages/linter): 명령줄을 사용하여 개발 중에 웹 스토리의 유효성을 확인합니다.

웹 스토리가 Google 검색이나 Google 디스커버에 표시되도록 하려면 미리보기에 웹 스토리가 올바르게 표시되도록 필요한 메타데이터를 제공합니다.

1.  [전체 메타데이터 목록](https://amp.dev/documentation/components/amp-story/#metadata-guidelines)을 참고하세요.
2.  [웹 스토리 Google 테스트 도구](https://search.google.com/test/amp?hl=ko)에서 웹 스토리 미리보기가 올바르게 표시되는지 확인합니다.

`publisher-logo-src`, `poster-portrait-src`, `title`, `publisher` 필드는 모든 웹 스토리에 필요합니다.

![publisher-logo-src, poster-portrait-src, title, publisher 필드는 모든 웹 스토리에 필요합니다.](https://developers.google.com/static/search/docs/images/web-stories-fields.png?hl=ko)

## 웹 스토리의 색인이 생성되었는지 확인

Google 검색에서 웹 스토리의 색인을 생성했는지 확인합니다. [URL 검사 도구](https://support.google.com/webmasters/answer/9012289?hl=ko)를 사용하여 개별 URL을 제출하거나 [페이지 색인 생성 보고서](https://developers.google.com/search/docs/crawling-indexing/ask-google-to-recrawl?hl=ko) 또는 [사이트맵 보고서](https://support.google.com/webmasters/answer/7440203?hl=ko)를 통해 상태를 검토합니다. 웹 스토리의 색인이 생성되지 않은 경우 다음을 실행합니다.

1.  Google에서 웹 스토리를 쉽게 찾을 수 있도록 사이트에서 웹 스토리에 연결하거나 웹 스토리 URL을 사이트맵에 추가합니다.
2.  모든 웹 스토리는 표준이어야 합니다. 각 웹 스토리에 자체 [`link rel="canonical"`](https://amp.dev/documentation/guides-and-tutorials/optimize-and-measure/discovery/)이 있는지 확인하세요. 예: `<link rel="canonical" href="https://www.example.com/url/to/webstory.html">`
3.  웹 스토리 URL이 robots.txt 파일 또는 `noindex` 태그에 의해 [Googlebot에서 차단](https://developers.google.com/search/docs/crawling-indexing?hl=ko)되지 않는지 확인합니다.