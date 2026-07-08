## 동적 렌더링을 사용하여 대처

일부 웹사이트에서는 페이지가 브라우저에서 열릴 때 JavaScript가 추가 콘텐츠를 로드합니다. 이를 [클라이언트 측 렌더링](https://web.dev/articles/rendering-on-the-web?hl=ko#client-side)이라고 합니다. Google 검색에서는 웹사이트의 HTML에 있는 콘텐츠와 함께 이 콘텐츠를 확인합니다. [Google 검색에는 JavaScript에 몇 가지 제한사항](https://developers.google.com/search/docs/crawling-indexing/javascript/javascript-seo-basics?hl=ko#write-compatible-code)이 있으며 일부 페이지에서는 렌더링된 HTML에 콘텐츠가 표시되지 않는 문제가 발생할 수 있습니다. 다른 검색엔진은 JavaScript를 무시할 수 있으며 JavaScript 생성 콘텐츠가 표시되지 않습니다.

동적 렌더링은 검색엔진에서 자바스크립트 생성 콘텐츠를 사용할 수 없는 웹사이트가 사용할 수 있는 임시방편입니다. 동적 렌더링 서버는 JavaScript로 생성된 콘텐츠와 관련해 문제가 있을 수 있는 크롤러를 감지하여 이러한 크롤러에는 JavaScript를 사용하지 않고 서버에서 렌더링된 버전을 제공하는 한편 사용자에게는 클라이언트 측 렌더링 버전의 콘텐츠를 표시합니다.

동적 렌더링은 임시방편이며, 상황을 더욱 복잡하게 만들고 추가적인 리소스도 필요하기 때문에 권장되는 해결책이 아닙니다.

<iframe frameborder="0" allowfullscreen="" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share" referrerpolicy="strict-origin-when-cross-origin" width="640" height="360" src="https://www.youtube.com/embed/CrzUP6MmBW4?origin=https%3A%2F%2Fdevelopers.google.com&amp;autoplay&amp;controls&amp;embed_domain&amp;enablejsapi=1&amp;end&amp;hl&amp;showinfo&amp;start&amp;video-id=CrzUP6MmBW4&amp;widgetid=9&amp;forigin=https%3A%2F%2Fdevelopers.google.com%2Fsearch%2Fdocs%2Fcrawling-indexing%2Fjavascript%2Fdynamic-rendering%3Fhl%3Dko&amp;aoriginsup=1&amp;gporigin=https%3A%2F%2Fdevelopers.google.com%2Fsearch%2Fdocs%2Fcrawling-indexing%2Famp%2Fabout-amp%3Fhl%3Dko&amp;vf=1" id="widget10" data-title="YouTube video player" title="Dynamic Rendering for JavaScript web apps - JavaScript SEO"></iframe>

## 동적 렌더링을 사용할 수 있는 사이트

동적 렌더링은 빠르게 변화하며 색인 생성이 가능한 공개 JavaScript 생성 콘텐츠 또는 원하는 [크롤러에서 지원하지 않는 JavaScript 기능](https://developers.google.com/search/docs/guides/rendering?hl=ko)을 사용하는 콘텐츠에 적용할 수 있는 임시방편입니다. 모든 사이트가 동적 렌더링을 사용해야 하는 것은 아니며, [웹 렌더링 개요](https://web.dev/articles/rendering-on-the-web?hl=ko)에 설명된 것처럼 동적 렌더링보다 더 나은 해결책이 있습니다.

## 동적 렌더링 작동 방식 이해하기

동적 렌더링을 사용하려면 웹 서버에서 크롤러를 감지해야 합니다(예: 사용자 에이전트 확인). 웹 서버가 JavaScript 또는 콘텐츠 렌더링에 필요한 JavaScript 기능을 지원하지 않는 크롤러의 요청을 식별하면 이 요청은 렌더링 서버로 라우팅됩니다. JavaScript 문제가 없는 사용자 및 크롤러의 요청은 정상적으로 제공됩니다. 렌더링 서버는 크롤러에 적합한 콘텐츠 버전으로 요청에 응답합니다(예: 정적 HTML 버전을 제공할 수 있음). 동적 렌더러는 모든 페이지에 또는 페이지별로 사용하도록 설정할 수 있습니다.

![동적 렌더링 작동 방식을 보여주는 다이어그램입니다. 다이어그램은 브라우저에 직접 초기 HTML과 JavaScript 콘텐츠를 제공하는 서버를 보여줍니다. 반대로 이 다이어그램은 렌더러에 초기 HTML과 JavaScript를 제공하는 서버를 보여줍니다. 이 경우 렌더러는 초기 HTML과 JavaScript를 정적 HTML로 변환합니다. 콘텐츠가 변환되면 렌더러가 정적 HTML을 크롤러에 제공합니다.](https://developers.google.com/static/search/docs/images/how-dynamic-rendering-works.png?hl=ko)

## 동적 렌더링은 클로킹이 아님

Googlebot은 일반적으로 동적 렌더링을 [클로킹](https://developers.google.com/search/docs/essentials/spam-policies?hl=ko#cloaking)으로 간주하지 않습니다. 동적 렌더링이 유사한 콘텐츠를 생성하는 한 Googlebot은 동적 렌더링을 클로킹으로 간주하지 않습니다.

동적 렌더링을 설정하는 동안 사이트에 오류 페이지가 생성될 수 있습니다. Googlebot은 이 오류 페이지를 클로킹으로 간주하지 않으며 [오류를 다른 오류 페이지와 마찬가지로 처리](https://developers.google.com/search/docs/crawling-indexing/javascript/javascript-seo-basics?hl=ko#use-meaningful-http-status-codes)합니다.

동적 렌더링을 사용하여 사용자와 크롤러를 대상으로 완전히 다른 콘텐츠를 제공하는 것은 클로킹으로 간주될 수 있습니다. 예를 들어 사용자에게는 고양이와 관련된 페이지를 제공하고 크롤러에는 개와 관련된 페이지를 제공하는 웹사이트는 클로킹입니다.