## 지연 로드 콘텐츠 문제 해결하기

중요하지 않거나 표시되지 않는 콘텐츠의 로드 지연(대개 '지연 로드'라고도 함)은 일반적인 성능 및 UX 권장사항입니다. 자세한 내용은 [web.dev의 이미지 및 동영상 지연 로드 리소스](https://web.dev/fast?hl=ko#lazy-load-images-and-video)를 참고하세요. 그렇지만 이 기술이 제대로 구현되지 않는 경우 의도치 않게 Google에서 콘텐츠를 보지 못할 수도 있습니다. 이 문서에서는 Google이 지연 로드 콘텐츠를 크롤링하고 색인 생성할 수 있도록 설정하는 방법을 설명합니다.

## 표시 영역에 표시될 때 콘텐츠 로드하기

Google이 페이지의 모든 콘텐츠를 볼 수 있게 하려면 표시 영역에 콘텐츠가 표시될 때마다 지연 로드 구현이 관련 콘텐츠를 모두 로드하는지 확인합니다. 다음은 지연 로드를 구현하는 몇 가지 방법입니다.

-   이미지 및 iframe의 [브라우저 내장 지연 로드](https://web.dev/articles/browser-level-image-lazy-loading?hl=ko)
-   [IntersectionObserver API](https://web.dev/articles/intersectionobserver?hl=ko) 및 [polyfill](https://github.com/GoogleChromeLabs/intersection-observer)
-   표시 영역에 들어올 때 데이터 로드를 지원하는 자바스크립트 라이브러리

위에 언급된 방법은 스크롤이나 클릭과 같은 사용자 작업에 의존하지 않고 콘텐츠를 로드합니다. 이는 Google 검색이 페이지와 상호작용하지 않으므로 중요합니다.

사용자가 페이지를 열 때 즉시 표시될 가능성이 높은 콘텐츠에는 지연 로드를 추가하지 마세요. 이로 인해 콘텐츠가 브라우저에 로드되고 표시되는 데 시간이 더 오래 걸릴 수 있으며 이는 사용자에게 매우 눈에 띌 수 있습니다.

[구현을 테스트](https://developers.google.com/search/docs/crawling-indexing/javascript/lazy-loading?hl=ko#test)하는 것을 잊지 마세요.

대략적으로 무한 스크롤은 사용자가 긴 페이지를 아래로 스크롤할 때 더 많은 콘텐츠와 고유한 페이지를 로드하는 기법입니다. 긴 기사를 여러 청크로 나눈 것일 수도 있고, 청크로 나눈 항목 모음일 수도 있습니다. 색인을 생성할 수 있는 방식으로 무한 스크롤을 구현하려면 다음을 실행하여 웹사이트에서 이러한 청크의 페이지 나누기 로드를 지원하는지 확인하세요.

-   각 청크에 고유하고 영구적인 URL을 지정합니다.
-   각 URL에 표시되는 콘텐츠가 브라우저에 로드될 때마다 동일하게 유지되는지 확인합니다. 이를 위한 한 가지 방법은 URL에서 절대 페이지 번호를 사용하는 것입니다(예: `?page=12`를 쿼리 매개변수로 사용).
-   이러한 URL에서는 `?date=yesterday`와 같은 상대 요소를 사용하지 마세요. 이렇게 하면 검색엔진과 사용자가 지정된 URL에서 동일한 콘텐츠를 일관되게 찾을 수 있으므로 검색엔진이 더 쉽게 콘텐츠의 색인을 생성하고 사용자가 콘텐츠의 해당 부분을 공유하고 다시 이용할 수 있습니다.
-   검색엔진이 페이지로 나눈 세트에서 URL을 검색할 수 있도록 개별 URL에 순차적으로 연결합니다. [페이지로 나누기 구현 시 권장사항](https://developers.google.com/search/docs/specialty/ecommerce/pagination-and-incremental-page-loading?hl=ko#best-practices-when-implementing-pagination)을 자세히 알아보세요.
-   사용자가 스크롤하는 데 대한 응답으로 새 페이지 청크가 로드되고 이 청크가 사용자에게 표시되는 기본 요소가 되면 [History API](https://developer.mozilla.org/en-US/docs/Web/API/History_API)를 사용하여 표시된 URL을 업데이트합니다. 이를 통해 사용자는 브라우저에 표시된 현재 URL을 새로고침, 공유, 연결할 수 있습니다.

## 테스트

구현을 설정한 후 제대로 작동하는지 확인해야 합니다. Search Console의 [URL 검사 도구](https://support.google.com/webmasters/answer/9012289?hl=ko)를 사용하여 모든 콘텐츠가 로드되었는지 확인할 수 있습니다. 렌더링된 HTML을 확인하여 URL 검사 도구에서 콘텐츠가 렌더링된 HTML에 있는지 확인합니다. 렌더링된 HTML의 `<img>` 또는 `<video>` 요소에 있는 `src` 속성에 이미지 또는 동영상 URL이 표시되면 설정이 올바르게 작동하는 것입니다.