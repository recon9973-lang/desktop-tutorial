<iframe frameborder="0" allowfullscreen="" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share" referrerpolicy="strict-origin-when-cross-origin" width="640" height="360" src="https://www.youtube.com/embed/-uUuaAAXF6I?origin=https%3A%2F%2Fdevelopers.google.com&amp;autoplay&amp;controls&amp;embed_domain&amp;enablejsapi=1&amp;end&amp;hl&amp;showinfo&amp;start&amp;video-id=-uUuaAAXF6I&amp;widgetid=7&amp;forigin=https%3A%2F%2Fdevelopers.google.com%2Fsearch%2Fdocs%2Fappearance%2Fstructured-data%2Fintro-structured-data%3Fhl%3Dko&amp;aoriginsup=1&amp;gporigin=https%3A%2F%2Fdevelopers.google.com%2Fsearch%2Fdocs%2Fcrawling-indexing%2Famp%2Fabout-amp%3Fhl%3Dko&amp;vf=1" id="widget8" data-title="YouTube video player" title="Korean | Google 검색에서 돋보이기: 구조화된 데이터와 리치 결과"></iframe>

Google 검색은 페이지의 콘텐츠를 파악하기 위해 노력합니다. 페이지에 구조화된 데이터를 포함하면 Google에 페이지 의미에 관한 확실한 단서를 제공하여 내용을 파악하는 데 도움이 됩니다. 구조화된 데이터는 페이지에 관한 정보를 제공하고 페이지 콘텐츠를 분류하기 위한 표준화된 형식으로 예를 들어 레시피 페이지의 경우 재료, 조리 시간, 온도, 칼로리 등이 여기에 해당합니다.

## 왜 페이지에 구조화된 데이터를 추가하나요?

구조화된 데이터를 추가하면 사용자에게 더욱 눈길을 끄는 검색결과를 제공하여 웹사이트와 더 많이 상호작용하도록 유도할 수 있으며, 이를 _리치 결과_라고 합니다. 사이트에 구조화된 데이터를 구현한 웹사이트의 우수사례를 살펴보면 다음과 같습니다.

-   Rotten Tomatoes에서는 100,000개의 개별 페이지에 구조화된 데이터를 추가함으로써 구조화된 데이터로 개선한 페이지의 클릭률을 구조화된 데이터가 없는 페이지 대비 25% 높였습니다.
-   Food Network에서는 페이지의 80%에 검색 기능을 추가하여 방문자 수를 35% 늘렸습니다.
-   Rakuten에서는 사용자가 구조화된 데이터가 구현된 페이지에 구조화된 데이터가 없는 페이지보다 1.5배 더 오래 머무르며, 검색 기능이 있는 AMP 페이지의 상호작용 발생률이 검색 기능이 없는 AMP 페이지보다 3.6배 높았다고 밝혔습니다.
-   Nestlé의 측정에 따르면 검색에 리치 결과로 표시되는 페이지의 클릭률이 일반 검색결과로 표시되는 페이지보다 82% 더 높은 것으로 나타났습니다.

## Google 검색에서 구조화된 데이터가 작동하는 방식

Google에서는 웹에서 찾은 구조화된 데이터를 사용하여 페이지의 콘텐츠를 파악할 뿐 아니라 마크업에 포함된 개인, 책, 회사에 관한 정보 등 웹 및 전반적인 세상에 관한 정보를 수집합니다. 예를 들어 레시피 페이지에 레시피 제목, 레시피 작성자, 기타 세부정보를 설명하는 구조화된 [JSON-LD](https://json-ld.org/) 데이터가 있는 경우 Google 검색은 해당 정보를 사용하여 레시피에 관한 리치 결과를 표시할 수 있습니다.

![레시피 웹페이지의 구조화된 데이터가 Google 검색의 리치 결과에 미치는 영향](https://developers.google.com/static/search/docs/images/structured-data-explainer.png?hl=ko)

구조화된 데이터는 레시피의 개별 요소에 라벨을 지정하므로 사용자는 재료, 칼로리, 조리 시간 등으로 레시피를 검색할 수 있습니다.

<iframe frameborder="0" allowfullscreen="" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share" referrerpolicy="strict-origin-when-cross-origin" width="640" height="360" src="https://www.youtube.com/embed/hUHjeDylhE8?origin=https%3A%2F%2Fdevelopers.google.com&amp;autoplay&amp;controls&amp;embed_domain&amp;enablejsapi=1&amp;end&amp;hl&amp;showinfo&amp;start&amp;video-id=hUHjeDylhE8&amp;widgetid=9&amp;forigin=https%3A%2F%2Fdevelopers.google.com%2Fsearch%2Fdocs%2Fappearance%2Fstructured-data%2Fintro-structured-data%3Fhl%3Dko&amp;aoriginsup=1&amp;gporigin=https%3A%2F%2Fdevelopers.google.com%2Fsearch%2Fdocs%2Fcrawling-indexing%2Famp%2Fabout-amp%3Fhl%3Dko&amp;vf=1" id="widget10" data-title="YouTube video player" title="Structured data for web developers"></iframe>

구조화된 데이터는 정보가 적용되는 페이지에 인페이지 마크업을 사용하여 코딩됩니다. 페이지의 구조화된 데이터는 페이지의 콘텐츠를 설명합니다. 구조화된 데이터를 보관하기만 하는 빈 페이지를 만들지 마세요. 또한 정보가 정확하더라도 사용자에게 표시되지 않는 정보에 관한 구조화된 데이터를 추가하지 마세요. 자세한 기술 및 품질 가이드라인은 [구조화된 데이터 일반 가이드라인](https://developers.google.com/search/docs/guides/sd-policies?hl=ko)을 참고하세요.

[리치 결과 테스트](https://search.google.com/test/rich-results?hl=ko)는 구조화된 데이터의 유효성을 검사하고 경우에 따라 Google 검색에서 기능을 미리 볼 수 있는 쉽고 유용한 도구입니다. 한번 사용해 보세요.

## 구조화된 데이터 용어 및 형식

이 문서에서는 Google 검색에 특별한 의미가 있는 구조화된 데이터의 필수, 권장 또는 선택적 속성을 설명합니다. Google 검색의 구조화된 데이터는 대부분 [schema.org](https://schema.org/) 용어를 사용하지만, Google 검색 동작의 경우 schema.org 문서가 아니라 Google 검색 센터 문서를 최종적으로 참고해야 합니다. schema.org에는 Google 검색에 필요하지 않은 더 많은 속성과 객체가 있습니다. 하지만 이들 항목은 다른 검색엔진과 서비스, 도구, 플랫폼에 유용할 수 있습니다.

개발 중에는 [리치 결과 테스트](https://search.google.com/test/rich-results?hl=ko)로, 배포 후에는 [리치 결과 상태 보고서](https://support.google.com/webmasters/answer/7552505?hl=ko)로 구조화된 데이터를 확인하여 템플릿이나 게재 문제로 배포 후 오류가 발생할 수 있는 페이지 유효성을 모니터링해야 합니다.

Google 검색에 향상된 디스플레이로 객체를 표시하려면 필수 속성을 모두 포함해야 합니다. 일반적으로 권장 속성을 많이 정의할수록 Google 검색결과에 향상된 디스플레이로 정보가 표시될 가능성이 커집니다. **그렇지만** 완전하지 않고 잘못 구성되었거나 부정확한 데이터로 사용 가능한 모든 권장 속성을 제공하기보다는 적지만 완전하고 정확한 권장 속성을 적용하는 것이 더 중요합니다.

여기에 설명된 속성과 객체 외에도 Google에서는 [`sameAs`](https://schema.org/sameAs) 속성 및 기타 구조화된 [schema.org](https://schema.org/) 데이터를 일반적으로 사용합니다. 이 중 일부 요소는 유용하다고 판단되는 경우 향후 Google 검색 기능에 사용될 수 있습니다.

### 지원되는 형식

Google 검색은 달리 문서화되지 않는 한 다음 형식의 구조화된 데이터를 지원합니다. 일반적으로 구현 및 유지보수가 가장 쉬운 형식(대부분의 경우 JSON-LD)을 사용하는 것이 좋습니다. 마크업이 유효하고 기능 문서에 따라 제대로 구현되는 한 3가지 형식 모두 Google에서 똑같이 사용할 수 있습니다.

| 형식 | 형식 |
|-------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| [JSON-LD](https://json-ld.org/)***(권장)** | HTML 페이지의 `<head>`, `<body>` 요소에 있는 `<script>` 태그 내에 삽입되는 JavaScript 표기입니다. 마크업은 중첩된 데이터 항목(예: `Event`의 `MusicVenue`의 `PostalAddress`의 `Country`)을 더 쉽게 표현하며 사용자가 볼 수 있는 텍스트와 함께 표시되지 않습니다. 또한 Google에서는 JavaScript 코드나 콘텐츠 관리 시스템에 삽입된 위젯과 같이 JSON-LD 데이터가 [페이지의 콘텐츠에 동적으로 삽입](https://developers.google.com/search/docs/guides/generate-structured-data-with-javascript?hl=ko)될 때 JSON-LD 데이터를 읽을 수 있습니다. |
| [마이크로데이터](https://html.spec.whatwg.org/multipage/microdata.html#microdata) | HTML 콘텐츠 내에 구조화된 데이터를 중첩하는 데 사용되는 개방형 커뮤니티 HTML 사양입니다. RDFa와 같이 HTML 태그 속성을 사용해 구조화된 데이터로 표시하려는 속성의 이름을 지정합니다. 대게 `<body>` 요소에 사용되지만 `<head>` 요소에 사용될 수도 있습니다. |
| [RDFa](https://rdfa.info/) | 사용자에게 표시되며 검색엔진에 제시하려는 콘텐츠에 해당하는 [HTML 태그 속성](https://www.w3.org/TR/rdfa-lite/#the-attributes)을 도입하여 연결된 데이터를 지원하는 HTML5 확장입니다. RDFa는 일반적으로 HTML 페이지의 `<head>`, `<body>` 섹션 모두에 사용됩니다. |

## 구조화된 데이터 가이드라인

[구조화된 데이터 일반 가이드라인](https://developers.google.com/search/docs/appearance/structured-data/sd-policies?hl=ko)과 사용하는 구조화된 데이터 유형 관련 가이드라인을 따르세요. 그러지 않으면 구조화된 데이터가 Google 검색의 리치 결과에 표시되지 않을 수 있습니다.

## 구조화된 데이터 시작하기

구조화된 데이터를 처음 사용한다면 [구조화된 데이터에 관한 schema.org 초보자 가이드](https://schema.org/docs/gs.html)를 확인하세요. 이 가이드는 마이크로데이터에 중점을 두지만 기본 아이디어는 JSON-LD 및 RDFa와 관련이 있습니다.

구조화된 데이터의 기본사항에 익숙해지면 [Google 검색의 구조화된 데이터 기능 목록](https://developers.google.com/search/docs/appearance/structured-data/search-gallery?hl=ko)을 살펴본 후 구현할 기능을 선택합니다. 각 가이드에서는 사이트가 Google 검색의 리치 결과 노출에 적합하도록 구조화된 데이터를 구현하는 방법을 자세히 설명합니다.

[기능 선택하기](https://developers.google.com/search/docs/appearance/structured-data/search-gallery?hl=ko)

## 구조화된 데이터의 효과 측정

검색 기능을 힘들게 구현한 가치가 있었는지 확인하려면 구조화된 데이터를 구현한 페이지와 구현하지 않은 페이지의 실적을 비교해 보시기 바랍니다. 이를 비교하는 가장 좋은 방법은 [사이트의 몇 페이지에 걸쳐서 전후 테스트](https://developers.google.com/search/docs/crawling-indexing/website-testing?hl=ko)를 실행하는 것입니다. 단일 페이지의 페이지 조회수는 여러 가지 이유로 달라질 수 있기 때문에 이 작업은 까다로울 수 있습니다.

1.  사이트에서 구조화된 데이터를 사용하지 않는 일부 페이지를 가져와서 Search Console에서 몇 개월 치 데이터를 확보합니다. 페이지 콘텐츠의 연도나 시기에 영향을 받지 않는 페이지를 선택합니다. 많이 변경되지 않지만 여전히 인기가 있어서 의미 있는 데이터를 생성할 만큼 자주 읽혀지는 페이지를 사용합니다.
2.  구조화된 데이터 또는 기타 기능을 페이지에 추가합니다. 마크업이 유효한지, Google이 페이지에서 [URL 검사 도구](https://support.google.com/webmasters/answer/9012289?hl=ko)를 사용하여 구조화된 데이터를 찾았는지 확인합니다.
3.  몇 개월 동안의 실적을 [실적 보고서](https://support.google.com/webmasters/answer/7576553?hl=ko#by_search_appearance)에 기록하고, URL별로 필터링하여 페이지의 실적을 비교합니다.