## 추천 스니펫 및 웹사이트

추천 스니펫이란 일반적인 검색결과와는 반대로 설명 형식의 [스니펫](https://developers.google.com/search/docs/appearance/snippet?hl=ko)이 먼저 표시되는 특수한 상자입니다. 추천 스니펫은 [관련 질문 그룹](https://developers.google.com/search/docs/appearance/visual-elements-gallery?hl=ko#related-questions-group)('People Also Ask'라고도 함) 내에 표시될 수도 있습니다. [Google의 추천 스니펫 작동 방식 자세히 알아보기](https://support.google.com/websearch/answer/9351707?hl=ko)

검색결과에 표시된 추천 스니펫을 보여주는 그림

7~10분

[삶은 달걀 만드는 방법](https://wikipedia.org/wiki/Boiled_egg)

## 추천 스니펫을 사용 중지하려면 어떻게 해야 하나요?

다음 두 가지 방법으로 추천 스니펫을 사용 중지할 수 있습니다.

-   [추천 및 일반 검색 스니펫 모두 차단](https://developers.google.com/search/docs/appearance/featured-snippets?hl=ko#block-both)
-   [추천 스니펫만 차단](https://developers.google.com/search/docs/appearance/featured-snippets?hl=ko#block-fs)

### 모든 스니펫 차단

특정 페이지에 모든 스니펫(추천 스니펫과 일반 스니펫 포함)이 표시되지 않도록 차단하려면 페이지에 [`nosnippet` 규칙](https://developers.google.com/search/docs/crawling-indexing/robots-meta-tag?hl=ko#nosnippet)을 추가합니다.

-   [`data-nosnippet` HTML 속성](https://developers.google.com/search/docs/crawling-indexing/robots-meta-tag?hl=ko#data-nosnippet-attr)으로 표시된 텍스트는 추천 스니펫 또는 일반 스니펫에 표시되지 않습니다.
-   페이지에 `nosnippet`과 `data-nosnippet` 규칙이 모두 표시되는 경우 `nosnippet`의 우선순위가 높으며 페이지의 스니펫이 표시되지 않습니다.

### 추천 스니펫만 차단

일반 형식의 검색결과에는 스니펫을 유지하되 추천 스니펫에는 표시하지 않으려면 [`max-snippet` 규칙](https://developers.google.com/search/docs/crawling-indexing/robots-meta-tag?hl=ko#max-snippet)을 짧은 길이로 설정하여 실험해 봐야 합니다. 추천 스니펫은 유용한 추천 스니펫을 생성할 정도로 충분한 텍스트가 표시되는 경우에만 나타납니다.

페이지가 계속 추천 스니펫에 표시된다면 값을 더 낮춰 보세요. 일반적으로 `max-snippet` 규칙 설정이 짧을수록 페이지가 추천 스니펫으로 표시될 가능성이 낮아집니다.

Google에서는 추천 스니펫으로 표시하는 데 필요한 최소 길이를 정확하게 제공하지 않습니다. 최소 길이는 스니펫에 포함된 정보, 언어, 플랫폼(휴대기기, 앱, 데스크톱) 등 여러 요인에 따라 달라지기 때문입니다.

`max-snippet` 값을 낮게 설정하더라도 페이지가 계속 추천 스니펫에 표시될 수 있습니다. 확실한 해결방법이 필요하다면 `nosnippet` 규칙을 사용하세요.

## 내 페이지를 추천 스니펫으로 표시하려면 어떻게 해야 하나요?

그렇게 할 수 없습니다. Google 시스템에서 사용자의 검색 요청에 적합한 추천 스니펫을 표시할 수 있다고 판단하면 페이지를 검색결과 상단에 표시합니다.

## 사용자가 추천 스니펫을 클릭하면 어떻게 되나요?

사용자가 추천 스니펫을 클릭하면 추천 스니펫에 표시된 페이지 섹션으로 바로 이동됩니다. 사이트에서 사이트설정을 추가하지 않아도 스니펫이 표시된 위치로 자동 스크롤됩니다. 브라우저가 필요한 기반 기술을 지원하지 않거나 Google 시스템에서 클릭을 연결할 페이지 내 정확한 위치를 확실히 결정하지 못하는 경우, 추천 스니펫을 클릭하면 사용자가 소스 웹페이지의 최상단으로 이동됩니다.