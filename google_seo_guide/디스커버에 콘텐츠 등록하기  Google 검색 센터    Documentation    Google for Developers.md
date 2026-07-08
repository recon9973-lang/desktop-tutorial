## 디스커버 및 웹사이트

[디스커버](https://support.google.com/websearch/answer/2819496?hl=ko)는 Google 검색의 일부로서 [웹 및 앱 활동](https://support.google.com/websearch/answer/54068?hl=ko)을 기반으로 사용자의 관심분야와 관련된 콘텐츠를 표시합니다. 이 페이지에서는 콘텐츠가 디스커버에 표시되는 방식과 사이트 소유자가 고려해야 할 권장사항에 대해 자세히 알아봅니다.

![휴대전화에 표시되는 디스커버 화면](https://developers.google.com/static/search/docs/images/google-discover.png?hl=ko)

## 디스커버에 콘텐츠가 표시되는 방식

[Google에서 콘텐츠의 색인을 생성](https://developers.google.com/search/docs/essentials/technical?hl=ko)했으며 콘텐츠가 디스커버 [콘텐츠 정책](https://support.google.com/websearch/answer/9982767?hl=ko)을 충족시키는 경우 콘텐츠는 자동으로 디스커버에 표시될 자격을 갖추게 됩니다. 특별한 태그나 구조화된 데이터는 필요하지 않습니다. 하지만 디스커버에 표시될 자격을 갖췄다고 해서 반드시 표시된다고 보장되는 것은 아닙니다.

디스커버에 표시될 수 있는 콘텐츠에는 사용자의 관심분야와 일치하는 다양한 주제가 포함됩니다. 사용자의 관심사를 기준으로 이전 콘텐츠가 유용하며 관련성이 높은 경우 표시될 수 있습니다.

디스커버는 Google 검색의 일부로서 Google 검색에서 사용하는 것과 동일한 여러 신호와 [시스템](https://developers.google.com/search/docs/appearance/ranking-systems-guide?hl=ko)을 사용하여 사용자 중심의 유용한 콘텐츠를 결정합니다. 따라서 디스커버를 제대로 활용하려면 [유용하고 신뢰할 수 있는 사용자 중심 콘텐츠 만들기](https://developers.google.com/search/docs/fundamentals/creating-helpful-content?hl=ko)에 관한 조언을 참조해야 합니다.

콘텐츠가 디스커버에 표시될 가능성을 높이려면 다음 방법을 사용하는 것이 좋습니다.

-   더 흥미롭게 보이기 위해 미리보기 콘텐츠(제목, 스니펫 또는 이미지)에 오해의 소지가 있거나 과장된 세부정보를 사용하거나 콘텐츠의 내용을 이해하는 데 필요한 핵심 정보를 제공하지 않음으로써 인위적으로 참여를 유도하는 클릭베이트 및 유사한 전략은 지양합니다.
-   콘텐츠의 핵심을 보여주는 페이지 제목과 광고 제목을 사용합니다.
-   병적인 호기심, 자극, 격분하는 감정을 충족하기 위해 흥미를 조작하는 선정적인 전략은 지양합니다.
-   최근 관심이 집중되는 분야의 콘텐츠를 전달하거나 효과적으로 스토리를 전달하거나 특색있는 관점을 제공합니다.
-   콘텐츠에 관련성 있고 눈길을 끄는 고품질 이미지, 특히 디스커버를 통해 방문자가 유입될 가능성이 높은 큰 이미지를 포함합니다. 다음 사양을 충족하는 이미지를 사용하는 것이 좋습니다.
    -   너비가 1200픽셀 이상
    -   총 픽셀 수가 300,000개를 초과하는 고해상도 (예: 1280x720픽셀의 16:9 이미지는 총 픽셀 수가 921,600개이므로 이 사양을 충족함)
    -   16x9 가로세로 비율
    -   [`max-image-preview:large` 설정](https://developers.google.com/search/docs/crawling-indexing/robots-meta-tag?hl=ko#max-image-preview) 또는 [AMP](https://www.ampproject.org/) 사용을 통해 사용 설정
-   [schema.org 마크업](https://developers.google.com/search/docs/appearance/google-images?hl=ko#schema-primary-image-of-page) 또는 `og:image` `meta` 태그를 사용하여 웹페이지와 관련이 있고 웹페이지를 대표하는 큰 이미지를 지정합니다. 이렇게 하면 디스커버에서 썸네일로 선택되는 이미지에 영향을 줄 수 있습니다. [선호하는 이미지를 지정하는 방법 자세히 알아보기](https://developers.google.com/search/docs/appearance/google-images?hl=ko#specify-preferred-image)
    -   schema.org 마크업 또는 `og:image` `meta` 태그에 일반적인 이미지 (예: 사이트 로고)를 사용하지 마세요.
    -   최상의 결과를 얻으려면 schema.org 마크업 또는 `og:image` `meta` 태그에 텍스트가 많은 이미지를 사용하지 마세요.
-   전반적으로 우수한 페이지 경험을 제공하세요. 자세한 내용은 [Google 검색 결과의 페이지 경험 이해하기](https://developers.google.com/search/docs/appearance/page-experience?hl=ko)에 관한 도움말 페이지를 확인하세요.

디스커버에서는 우수한 사용자 환경을 제공하기 위해 기사와 동영상 등 관심사 기반 피드에 적합한 콘텐츠를 제공하고, 독자가 원치 않거나 독자에게 혼동을 줄 수 있는 콘텐츠를 필터링하려고 노력합니다. 예를 들어 디스커버에서 맥락이 없는 구직 지원, 청원, 양식, 코드 저장소, 풍자 콘텐츠는 추천되지 않을 수 있습니다. Discover는 [SafeSearch](https://developers.google.com/search/docs/crawling-indexing/safesearch?hl=ko)를 사용하지만 그 외에 충격적이거나 예상치 못한 것으로 간주되는 콘텐츠를 필터링합니다.

## 시간 경과에 따라 디스커버 트래픽이 변할 수 있는 이유

디스커버의 트래픽은 키워드 기반 검색 방문에 비해 예측 및 신뢰성이 낮습니다. 뜻밖의 발견을 가능하게 하는 디스커버의 특성상 디스커버 트래픽은 키워드 기반 검색 트래픽을 보완하는 것으로 생각해야 합니다. 다음은 디스커버 트래픽이 변동될 수 있는 몇 가지 이유입니다.

-   **관심분야 변경**: 디스커버는 사용자의 관심 분야에 부합하는 콘텐츠를 표시하도록 설계되고 항상 개선되고 있으며, 그 중 일부는 사용자의 검색 활동을 기반으로 할 수 있습니다. 사용자가 특정 주제에 더 이상 관심이 없다면(예: 검색 빈도 감소) 디스커버 피드에 사용자가 더 관심이 있는 콘텐츠가 표시될 수 있습니다. 이로 인해 게시자의 트래픽에 변동이 생길 수 있습니다.
-   **콘텐츠 유형**: 디스커버는 피드에 표시될 수 있는 콘텐츠 유형을 사용자가 찾는 내용에 더 잘 부합하도록 계속해서 조정합니다. 디스커버에서는 오픈 웹의 스포츠, 건강, 엔터테인먼트, 라이프스타일 콘텐츠를 포함하되 이에 국한되지 않는 콘텐츠를 정기적으로 표시합니다.
-   **Google 검색 업데이트**: Google에서는 사용자에게 유용한 콘텐츠 링크를 더 효과적으로 제공하기 위해 정기적으로 [Google 검색을 업데이트](https://status.search.google.com/products/rGHU1u87FJnkP6W2GwMi/history?hl=ko)합니다. 디스커버는 Google 검색의 확장 프로그램이므로 업데이트로 인해 트래픽이 변동될 수도 있습니다. 업데이트 후 웹사이트 실적에 변화가 있다면 [Google 검색의 핵심 업데이트 및 웹사이트](https://developers.google.com/search/docs/appearance/core-updates?hl=ko) 문서를 검토하는 것이 좋습니다.

## 디스커버 실적 모니터링

디스커버에 콘텐츠가 있으면 [디스커버 실적 보고서](https://support.google.com/webmasters/answer/9216516?hl=ko)를 사용하여 실적을 모니터링할 수 있습니다. 데이터가 최소 노출수 한도에 도달한 경우 지난 16개월 동안 디스커버에 노출된 콘텐츠의 노출수, 클릭수, CTR이 보고서에 표시됩니다. 디스커버 실적 보고서에는 [Chrome 트래픽](https://developers.google.com/search/blog/2021/02/search-console-performance-discover-chrome?hl=ko)이 포함되며 사용자가 디스커버와 상호작용하는 모든 표시 경로에서 사이트의 디스커버 트래픽을 전부 추적할 수 있습니다.