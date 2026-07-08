## 표준화란 무엇인가요?

표준화는 콘텐츠를 대표하는 **표준** URL을 선택하는 프로세스입니다. 표준 URL은 Google이 여러 중복 페이지 중 가장 대표적이라고 선택한 페이지의 URL을 말합니다. Google에서는 중복 삭제라고도 하는 표준화 절차를 사용해 검색결과에 중복 콘텐츠 중 하나의 버전만 표시합니다.

다음과 같은 다양한 이유로 사이트에 중복 콘텐츠가 있을 수 있습니다.

-   **지역별 변형**: 예를 들어 미국과 영국을 대상으로 제공되는 콘텐츠이며 여러 URL을 통해 액세스할 수 있지만, 본질적으로는 동일한 언어로 작성된 동일한 콘텐츠인 경우입니다.
-   **기기 변형**: 예를 들어 페이지에 모바일 버전과 데스크톱 버전이 둘 다 있는 경우입니다.
-   **프로토콜 변형**: 예를 들어 사이트에 HTTP 버전과 HTTPS 버전이 있는 경우입니다.
-   **사이트 기능**: 예를 들어 카테고리 페이지에 정렬 및 필터링 기능을 사용한 결과입니다.
-   **실수로 인한 변형**: 예를 들어 사이트의 데모 버전이 실수로 크롤러가 액세스할 수 있는 상태로 남아 있을 수 있습니다.

사이트에 일부 콘텐츠가 중복인 상태는 정상이며 [Google의 스팸 정책](https://developers.google.com/search/docs/essentials/spam-policies?hl=ko)을 위반하지 않습니다. 하지만 여러 다른 URL을 통해 동일한 콘텐츠에 액세스할 수 있으면 사용자 경험이 저하될 수 있으며(예: 사람들이 어떤 페이지가 올바른 페이지이며 이 두 페이지 간에 차이가 있는지 궁금해 할 수 있음), 검색결과에서 _콘텐츠_의 실적을 추적하기 어려워질 수 있습니다.

### Google이 색인을 생성하고 표준 URL을 선택하는 방법

<iframe frameborder="0" allowfullscreen="" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share" referrerpolicy="strict-origin-when-cross-origin" width="640" height="360" src="https://www.youtube.com/embed/8j_hxBw5B4E?origin=https%3A%2F%2Fdevelopers.google.com&amp;autoplay&amp;controls&amp;embed_domain&amp;enablejsapi=1&amp;end&amp;hl&amp;showinfo&amp;start&amp;video-id=8j_hxBw5B4E&amp;widgetid=47&amp;forigin=https%3A%2F%2Fdevelopers.google.com%2Fsearch%2Fdocs%2Fcrawling-indexing%2Fcanonicalization%3Fhl%3Dko&amp;aoriginsup=1&amp;gporigin=https%3A%2F%2Fwww.google.com%2F&amp;vf=1" id="widget48" data-gtm-yt-inspected-225073684_46="true" data-gtm-yt-inspected-183356566_95="true" data-gtm-yt-inspected-26="true" data-gtm-yt-inspected-45="true" data-gtm-yt-inspected-52="true" data-title="YouTube video player" title="Canonical URLs: How Does Google Pick the One?"></iframe>

[Google에서 페이지의 색인을 생성](https://developers.google.com/search/docs/fundamentals/how-search-works?hl=ko)하면 페이지별로 주된 콘텐츠(또는 _중심 자료_)가 결정됩니다. Google에서 동일해 보이거나 주된 콘텐츠가 서로 매우 유사한 페이지를 여러 개 발견하면 색인 생성에서 수집한 요소(또는 _신호_)에 기반해 객관적으로 가장 완전하며 검색 사용자에게 유용한 페이지를 선택하고 이를 표준 페이지로 표시합니다. 표준 페이지가 가장 정기적으로 크롤링되며, 중복 페이지는 사이트의 크롤링 부담을 줄이기 위해 이보다 적게 크롤링됩니다.

표준화 과정에서 중요한 역할을 하는 요소가 몇 가지 있는데, 이러한 요소에는 페이지가 HTTP 및 HTTPS 중 어느 쪽을 통해 제공되는지, 리디렉션이 사용되는지, 사이트맵에 URL이 포함되어 있는지, `rel="canonical"` `link` 주석 등이 포함됩니다. 이러한 기술을 사용하여 [Google에 선호하는 페이지를 밝힐 수 있지만](https://developers.google.com/search/docs/crawling-indexing/consolidate-duplicate-urls?hl=ko#define-canonical), Google에서는 여러 가지 이유로 인해 소유자가 선호하는 페이지가 아닌 다른 페이지를 표준으로 선택할 수도 있습니다. 즉, 내가 표준 URL로 사용하고 싶은 URL을 명시하더라도 반드시 이 URL이 선택되는 것은 아니며 Google에 힌트만 제공하게 됩니다.

한 페이지에 여러 언어 버전이 있으면 주요 콘텐츠의 언어가 같은 경우에만 중복으로 간주합니다. 즉, 머리글, 바닥글, 기타 중요하지 않은 텍스트만 번역되어 있고 본문이 동일한 페이지는 중복으로 간주합니다. 현지화된 사이트 설정에 대해 자세히 알아보려면 [다국어 및 다지역 사이트 관리](https://developers.google.com/search/docs/specialty/international/localized-versions?hl=ko)에 관한 문서를 참고하세요.

Google은 표준 페이지를 콘텐츠와 품질을 평가하기 위한 주된 출처로 사용합니다. Google 검색결과는 대부분의 경우 표준 페이지를 표시하지만, 검색 사용자에게 명백하게 더 적합한 중복 페이지가 있을 경우 이를 보여 줍니다. 예를 들어, 데스크톱 페이지가 표준이더라도 사용자가 휴대기기를 사용하는 경우 검색결과에 모바일 페이지가 표시될 가능성이 큽니다.

[표준 URL로 선호하는 URL을 명시하는 방법과 이러한 URL을 언제 명시해야 하는지](https://developers.google.com/search/docs/crawling-indexing/consolidate-duplicate-urls?hl=ko)에 관해 자세히 알아보세요.