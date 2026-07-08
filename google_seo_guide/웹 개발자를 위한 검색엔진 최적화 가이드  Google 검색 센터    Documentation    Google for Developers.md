관련성이 더욱 높은 사용자가 내 콘텐츠를 보게 하기 위해서는 검색에 최적화된 콘텐츠를 만드는 것이 중요합니다. 이를 검색엔진 최적화(SEO)라고 하며, 이를 통해 더 많은 관심을 가진 사용자가 사이트를 방문하게 할 수 있습니다. Google 검색이 내 페이지를 파악하는 데 문제가 있는 경우 페이지에서 중요한 트래픽 소스를 놓치고 있을 수도 있습니다.

이 가이드에서는 사이트가 Google 검색에서 원활하게 작동하도록 개발자가 무엇을 할 수 있는지 알아봅니다. 이 가이드에 포함된 사항 외에도 사이트는 [안전하고](https://web.dev/explore/secure?hl=ko), [빠르고](https://web.dev/explore/fast?hl=ko), [누구나 액세스할 수 있으며](https://web.dev/explore/accessible?hl=ko), [모든 기기에서 작동](https://developers.google.com/search/docs/crawling-indexing/mobile/mobile-sites-mobile-first-indexing?hl=ko)해야 합니다.

## 사이트가 Google에 표시되는 방법

먼저 Google이 사이트를 어떻게 인식하는지 확인하기 위해 [URL 검사 도구](https://search.google.com/search-console?hl=ko) 또는 [리치 결과 테스트](https://search.google.com/test/rich-results?hl=ko)에서 사이트를 테스트해 보세요. [Googlebot은 Google의 웹 크롤링 봇](https://developers.google.com/search/docs/crawling-indexing/googlebot?hl=ko)으로, Google 색인에 표시할 새로운 페이지 및 업데이트된 페이지를 찾습니다. 이 프로세스에 관해 자세히 알아보려면 [Google 검색 작동 방식](https://developers.google.com/search/docs/fundamentals/how-search-works?hl=ko)을 참고하세요.

브라우저에 표시되는 모든 내용을 Google이 항상 확인하고 있는 것은 아닙니다. 다음 예시의 페이지는 Googlebot에서 지원하지 않는 자바스크립트 기능을 사용하므로 Google에서 이 페이지에 이미지가 있음을 인식하지 못합니다.

[사용자 뷰](https://developers.google.com/search/docs/fundamentals/get-started-developers?hl=ko/#사용자-뷰)[Google 뷰](https://developers.google.com/search/docs/fundamentals/get-started-developers?hl=ko/#google-뷰) 더보기

다음은 사용자가 페이지를 보는 방식입니다. 사용자는 브라우저에서 이미지와 텍스트를 볼 수 있습니다.

![6가지의 서로 다른 고양이 이미지를 보여주는 웹사이트 웹사이트의 제목은 Cute cat content chronicles입니다.](https://developers.google.com/static/search/docs/images/get-started01.png?hl=ko)

다음은 Google이 페이지를 보는 방식입니다. 페이지가 Google에서 지원하지 않는 자바스크립트 기능을 사용하므로 Google은 이 페이지에 이미지가 있음을 인식하지 못합니다.

![웹사이트의 제목이 표시된 웹사이트 페이지에 고양이 이미지가 표시되어야 하지만, 로드 아이콘만 표시됩니다.](https://developers.google.com/static/search/docs/images/get-started02.png?hl=ko)

## 링크 확인

Googlebot은 링크, 사이트맵, 리디렉션을 가져오고 파싱하여 URL 사이를 이동합니다. Googlebot은 사이트에서 발견하는 모든 URL을 첫 번째이자 유일한 URL로 취급합니다. Googlebot이 사이트의 모든 URL을 확인할 수 있게 하려면 다음을 따르세요.

-   [Google에서 크롤링할 수 있는 `<a>` 요소](https://developers.google.com/search/docs/crawling-indexing/links-crawlable?hl=ko#crawlable-links)를 사용합니다. 검색할 수 있는 다른 페이지의 링크에서 사이트의 모든 페이지가 연결될 수 있는지 확인합니다. 참조된 링크에는 타겟 페이지와 관련된 텍스트나 Alt 속성(이미지의 경우)이 포함되어야 합니다.
-   [사이트맵을 빌드하고 제출](https://developers.google.com/search/docs/crawling-indexing/sitemaps/build-sitemap?hl=ko)하여 Googlebot이 사이트를 더 지능적으로 크롤링하도록 합니다. 사이트맵은 사이트에 있는 페이지, 동영상 및 기타 파일과 각 관계에 관한 정보를 제공하는 파일입니다.
-   HTML 페이지가 하나만 있는 자바스크립트 앱의 경우 각 화면 또는 개별 콘텐츠마다 URL이 있어야 합니다.

## 자바스크립트 사용 방법 확인

Google은 자바스크립트를 실행하지만, 크롤러가 콘텐츠에 액세스하고 렌더링하는 방법을 수용하려면 페이지와 애플리케이션을 설계할 때 몇 가지 차이점과 제한사항을 고려해야 합니다. [자바스크립트 검색엔진 최적화의 기본사항](https://developers.google.com/search/docs/guides/javascript-seo-basics?hl=ko) 또는 [검색과 관련된 자바스크립트 문제를 해결](https://developers.google.com/search/docs/guides/fix-search-javascript?hl=ko)하는 방법을 자세히 알아보세요.

Google이 크롤링, 렌더링, 색인 생성 시 자바스크립트를 처리하는 방법을 알아보려면 다음 동영상을 참조하세요.

<iframe frameborder="0" allowfullscreen="" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share" referrerpolicy="strict-origin-when-cross-origin" width="640" height="360" src="https://www.youtube.com/embed/Mqi9aLZElgc?origin=https%3A%2F%2Fdevelopers.google.com&amp;autoplay&amp;controls&amp;embed_domain&amp;enablejsapi=1&amp;end&amp;hl&amp;showinfo&amp;start&amp;video-id=Mqi9aLZElgc&amp;widgetid=23&amp;forigin=https%3A%2F%2Fdevelopers.google.com%2Fsearch%2Fdocs%2Ffundamentals%2Fget-started-developers%3Fhl%3Dko&amp;aoriginsup=1&amp;gporigin=https%3A%2F%2Fwww.google.com%2F&amp;vf=1" id="widget24" data-gtm-yt-inspected-225073684_46="true" data-gtm-yt-inspected-183356566_95="true" data-gtm-yt-inspected-26="true" data-gtm-yt-inspected-45="true" data-gtm-yt-inspected-52="true" data-title="YouTube video player" title="When does JavaScript SEO matter? - JavaScript SEO"></iframe>

## 콘텐츠 변경 시 Google에 알리기

Google에서 신규 또는 업데이트된 페이지를 빠르게 확인할 수 있도록 다음을 따르세요.

-   [사이트맵 제출](https://developers.google.com/search/docs/crawling-indexing/sitemaps/build-sitemap?hl=ko)
-   [Google에 URL 재크롤링 요청](https://developers.google.com/search/docs/crawling-indexing/ask-google-to-recrawl?hl=ko)

계속해서 페이지의 색인을 생성하는 데 문제가 발생하는 경우 서버 로그에서 오류를 확인하세요.

## 페이지에서 텍스트로 표현하기

Googlebot은 텍스트로 표시되는 콘텐츠만 확인할 수 있습니다. 예를 들어 동영상의 텍스트는 Googlebot이 보지 못합니다. 다음을 참조하여 Google 검색이 페이지 주제가 무엇인지 알 수 있도록 하세요.

-   **시각적 콘텐츠가 텍스트 형식으로 표현되어야 합니다.** 예를 들어 각 이미지에 관한 텍스트 정보 없이 셔츠의 이미지 목록만 포함된 제품 카테고리 페이지는 적합하지 않습니다. 제품 카테고리 페이지는 각 이미지를 설명한 텍스트를 포함해야 합니다.
-   **모든 페이지에는 [구체적인 제목](https://developers.google.com/search/docs/appearance/title-link?hl=ko#page-titles)과 [메타 설명](https://developers.google.com/search/docs/appearance/snippet?hl=ko#meta-descriptions)이 있어야 합니다**. 고유한 제목과 메타 설명이 있으면 Google에서 페이지가 사용자와 얼마나 관련되어 있는지 표시하는 데 도움이 되므로 검색 트래픽이 증가할 수 있습니다.
-   **의미론적 HTML을 사용합니다**. Googlebot은 HTML, PDF 콘텐츠, 이미지, 동영상의 색인을 생성하지만 플러그인이 필요한 콘텐츠(예: 자바, Silverlight) 또는 캔버스에서 렌더링되는 콘텐츠의 색인은 생성하지 못합니다. 가능하다면 플러그인을 사용하는 대신 콘텐츠에 의미론적 HTML 마크업을 사용하세요.
-   **[DOM](https://developer.mozilla.org/en-US/docs/Web/API/Document_Object_Model/Introduction)에서 텍스트 콘텐츠에 액세스할 수 있어야 합니다.** [예를 들어](https://developer.mozilla.org/en-US/docs/Web/API/Document_Object_Model/Introduction) [CSS `content` 속성](https://developer.mozilla.org/en-US/docs/Web/CSS/content)을 통해 추가된 콘텐츠는 DOM에 해당하지 않으므로 현재 Google 검색에서는 이를 무시합니다. 장식용 콘텐츠에는 `content` 속성을 사용할 수 있으나 Google 검색에서는 이 콘텐츠의 색인을 생성하지 않을 수 있습니다.

## 콘텐츠의 다른 버전을 Google에 알리기

Google은 사이트 또는 콘텐츠의 여러 버전이 있음을 자동으로 인식하지 못합니다. 예를 들면 모바일 및 데스크톱 버전 또는 사이트의 해외 버전은 인식하지 못합니다. Google이 사용자에게 올바른 버전을 제공할 수 있도록 다음을 따르세요.

-   [중복 URL 통합](https://developers.google.com/search/docs/crawling-indexing/consolidate-duplicate-urls?hl=ko)
-   [Google에 사이트의 현지화된 버전 알리기](https://developers.google.com/search/docs/specialty/international/localized-versions?hl=ko)
-   [AMP 페이지를 검색 가능하게 만들기](https://www.ampproject.org/docs/fundamentals/discovery)

## Google이 보는 콘텐츠 제어

Googlebot을 차단하는 몇 가지 방법이 있습니다.

-   Google이 내 페이지를 찾지 못하게 하려면 콘텐츠 액세스 권한을 로그인한 사용자로 제한하세요(예: 로그인 페이지 사용 또는 [페이지를 비밀번호로 보호](https://developers.google.com/search/docs/crawling-indexing/control-what-you-share?hl=ko)).
-   Googlebot이 페이지를 크롤링하지 못하게 하려면 [robots.txt를 만드세요](https://developers.google.com/search/docs/crawling-indexing/robots/create-robots-txt?hl=ko).
-   Google이 내 페이지의 색인을 생성하지 못하게 차단하지만 크롤링은 계속 허용하려면 [`noindex` 태그를 추가](https://developers.google.com/search/docs/crawling-indexing/robots-meta-tag?hl=ko#noindex)합니다.

콘텐츠가 Google 검색에 표시되지 않는 경우 표시되게 하려면 아래 단계를 따르세요.

-   [URL 검사 도구](https://support.google.com/webmasters/answer/9012289?hl=ko)를 사용하여 Googlebot이 페이지에 액세스할 수 있는지 확인하세요.
-   [robot.txt 파일을 테스트](https://support.google.com/webmasters/answer/6062598?hl=ko)하여 의도치 않게 Googlebot의 사이트 크롤링을 차단했는지 확인합니다.
-   `meta` 태그에서 `noindex` 규칙에 관한 HTML을 확인합니다.

## 사이트에 리치 결과 사용

리치 결과에는 사이트가 Google 검색결과에서 더 눈에 띄게 표시되는 데 도움이 되는 스타일, 이미지 또는 기타 상호작용 기능이 포함됩니다. 페이지 의미에 관한 명확한 단서와 함께 [페이지의 구조화된 데이터](https://developers.google.com/search/docs/appearance/structured-data/intro-structured-data?hl=ko)를 제공하여 Google이 페이지를 더 잘 파악하도록 도움을 주고 Google 검색에서 페이지의 리치 결과가 표시되게 할 수 있습니다. 어떻게 시작해야 할지 모르겠다면 [사용 가능한 기능 갤러리를 둘러보세요](https://developers.google.com/search/docs/guides/search-gallery?hl=ko).

![검색결과에 표시된 레시피 캐러셀](https://developers.google.com/static/search/docs/images/recipe-host-carousel-rich-result.png?hl=ko)