Google 검색 실적 데이터를 분석하는 작업은 쉽지 않지만, 시각화하고 이해하기 어려운 롱테일 검색어가 많으면 훨씬 더 까다롭습니다. [풍선형 차트](https://support.google.com/datastudio/answer/7207785?hl=ko)를 사용하면 사이트에서 어떤 검색어가 실적이 좋은지, 어떤 검색어를 개선할 수 있는지 파악하는 데 도움이 됩니다.

여기에 설명된 기법을 테스트하려면 [데이터를 Looker Studio에 연결](https://datastudio.google.com/reporting/1e5b5f6a-38d7-4547-a54b-69594681a09b/page/xFbeC/preview?hl=ko)하고 차트 설정을 다양한 방법으로 실험해 보세요.

<iframe frameborder="0" allowfullscreen="" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share" referrerpolicy="strict-origin-when-cross-origin" width="640" height="360" src="https://www.youtube.com/embed/pIZqhZWC7rA?origin=https%3A%2F%2Fdevelopers.google.com&amp;autoplay&amp;controls&amp;embed_domain&amp;enablejsapi=1&amp;end&amp;hl&amp;showinfo&amp;start&amp;video-id=pIZqhZWC7rA&amp;widgetid=97&amp;forigin=https%3A%2F%2Fdevelopers.google.com%2Fsearch%2Fdocs%2Fmonitor-debug%2Fbubble-chart-analysis%3Fhl%3Dko&amp;aoriginsup=1&amp;gporigin=https%3A%2F%2Fdevelopers.google.com%2Fsearch%2Fdocs%2Fcrawling-indexing%2Famp%2Fabout-amp%3Fhl%3Dko&amp;vf=1" id="widget98" data-title="YouTube video player" title="Analyzing Search performance data with bubble charts  - Search Console Training"></iframe>

[Search Console을 Looker Studio에 연결하기](https://developers.google.com/search/blog/2022/03/connecting-data-studio?hl=ko) 및 [Looker Studio로 검색 트래픽 모니터링하기](https://developers.google.com/search/blog/2022/03/monitoring-dashboard?hl=ko)를 아직 읽어 보지 않으셨나요? Looker Studio에서 Search Console로 어떤 작업을 할 수 있는지 자세히 알아보려면 이 두 도움말을 확인해 보세요.

## 차트 이해하기

풍선형 차트는 측정항목과 측정기준이 여러 개일 때 유용한 시각화 도구입니다. 데이터의 관계와 패턴을 더 효과적으로 확인할 수 있기 때문입니다. 여기에 나온 예에서는 검색어 및 기기 측정기준에 대한 [클릭률](https://support.google.com/webmasters/answer/7576553?hl=ko#choosingmetrics)(CTR), 평균 게재순위, 클릭수를 한번에 전부 확인할 수 있습니다.

![Search Console 풍선형 차트 요소](https://developers.google.com/static/search/docs/images/search-console-bubble-chart.png?hl=ko)

이 섹션에서는 일부 차트 요소에 대해 자세히 살펴보면서 차트에 어떤 내용이 표시되고, 어떤 내용은 표시되지 않는지 확인합니다.

### 데이터 소스

이 페이지에 표시된 풍선형 차트는 [Search Console 데이터 소스](https://support.google.com/datastudio/answer/7314895?hl=ko)를 통해 제공되는 사이트 노출수 표를 사용하며, 여기에는 사이트 및 검색어별로 집계된 [Google 검색 실적 데이터](https://support.google.com/webmasters/answer/7576553?hl=ko)가 포함되어 있습니다.

### 필터 및 데이터 관리

차트에는 데이터를 효과적으로 관리하는 데 도움이 되는 다섯 가지 맞춤설정 옵션이 있습니다.

1.  **[데이터 관리](https://support.google.com/datastudio/answer/7415591?hl=ko)**: 분석하고자 하는 Search Console 속성을 선택합니다.
2.  **기간**: 보고서에 표시할 기간을 선택합니다. 기본적으로 지난 28일 동안의 데이터가 표시됩니다.
3.  **검색어**: 집중할 검색어를 포함하거나 제외합니다. Search Console에서와 비슷한 방법으로 [데이터를 필터링](https://developers.google.com/search/blog/2021/06/regex-negative-match?hl=ko)할 수 있습니다.
4.  **국가**: 국가를 포함하거나 제외합니다.
5.  **기기**: 기기 카테고리를 포함하거나 제외합니다.

### 축

차트의 축은 평균 게재순위(y축)와 사이트 CTR(x축)이지만, 세 가지 중요한 변경사항이 있습니다.

6.  **역 y축 방향**: y축은 평균 게재순위를 표시하므로 이를 반전하면 1이 맨 위에 옵니다. 대부분의 차트에서는 최고 게재순위가 오른쪽 상단에 있으므로 평균 게재순위를 표시할 때 y축을 반전시키는 것이 더 직관적입니다.
7.  **로그 스케일**: 두 축 모두에 [로그 스케일](https://en.wikipedia.org/wiki/Logarithmic_scale)을 사용하면 차트의 맨 끝에 있는 검색어를 더 잘 파악할 수 있습니다(매우 낮은 CTR, 평균 게재순위 또는 둘 다).
8.  **[참조선](https://support.google.com/datastudio/answer/9921462?hl=ko)**: 참조선은 특정 임계값을 초과하거나 임계값 미만인 값을 강조표시하는 데 매우 유용합니다. 평균이나 중앙값, 특정 백분위수를 살펴보면 패턴의 편차에 주목할 수 있습니다.

### 풍선

차트의 각 풍선은 다음의 [스타일 속성](https://support.google.com/datastudio/answer/7207785?hl=ko#style-properties)을 가진 단일 검색어를 나타냅니다.

-   **크기**: 클릭수를 풍선 크기로 나타내면 많은 트래픽을 유도하는 검색어를 한눈에 확인할 수 있습니다. 풍선이 클수록 검색어에서 더 많은 트래픽이 생성된 것입니다.
-   **색상**: 풍선 색상을 사용하여 기기 카테고리를 구분하면 Google 검색의 모바일과 데스크톱 실적 간 차이를 파악하는 데 도움이 됩니다. 색상을 사용해 모든 측정기준을 구분할 수 있지만, 측정기준 개수가 늘어날수록 패턴을 인식하기가 어려워집니다.

## 데이터 분석

이 시각화의 목표는 검색어 최적화 기회를 확인하는 것입니다. 차트는 검색어 실적을 보여줍니다. 여기서 y축은 평균 게재순위를, x축은 CTR을, 풍선 크기는 총 클릭수를, 풍선 색상은 기기 카테고리를 나타냅니다.

빨간색 점선으로 표시되는 평균 참조선은 각 축의 평균을 보여줍니다. 이는 차트를 사분면으로 분할하여 4가지 유형의 검색어 실적을 보여줍니다. 사분면은 이 게시물에 공유된 사분면과 다르게 보일 수 있습니다. 사이트 검색어 분포 방식에 따라 달라집니다.

![네 가지 유형의 검색어 실적을 보여주는 풍선형 차트](https://developers.google.com/static/search/blog/images/query-performance-types.png?hl=ko)

차트에는 4가지 검색어 그룹이 표시되며, 이를 분석하여 Google 검색 실적을 최적화할 때 어떤 영역에 시간을 투자해야 할지 결정할 수 있습니다.

1.  **최상위 게재순위, 높은 CTR**: 이 경우에는 할 일이 별로 없습니다. 이미 잘하고 있습니다.
2.  **낮은 게재순위, 높은 CTR**: 사용자와 관련이 있어 보이는 검색어입니다. 웹사이트의 평균 검색어보다 순위는 낮지만 CTR이 높습니다. 검색어의 평균 게재순위가 올라가면 실적에 상당한 영향을 미칠 수 있습니다. 이 그룹에 속하는 검색어의 검색엔진 최적화를 개선하는 데 집중하세요. 예를 들어 정원 가꾸기 웹사이트에서 '나무 창고를 만드는 방법'이라는 인기 검색어가 2사분면에 해당할 수 있습니다. 이미 관련 페이지가 있는지 확인한 후 다음의 두 가지 방법으로 진행하세요.
    -   관련 페이지가 없다면 페이지를 만들고 웹사이트에서 이 주제와 관련된 모든 정보를 한곳에 모으는 것이 좋습니다.
    -   관련 페이지가 있다면 콘텐츠를 추가하여 사용자의 요구를 좀 더 효과적으로 해결해 보세요.
3.  **낮은 게재순위, 낮은 CTR**: CTR이 낮은 검색어(게재순위가 낮은 검색어와 높은 검색어 둘 다)를 살펴볼 때 특히 흥미로운 부분은, 풍선의 크기를 확인하여 CTR은 낮지만 상당한 트래픽을 유도하는 검색어가 있는지 확인하는 것입니다. 이 사분면의 검색어는 살펴볼 필요가 없어 보일 수 있지만 다음과 같은 두 가지 주요 그룹으로 나눌 수 있습니다.
    -   **관련 검색어**: 문제의 검색어가 중요하다면 Google 검색에 이미 표시되어 있는 것이 좋습니다. Google 검색 결과에 전혀 표시되지 않는 검색어보다 이러한 검색어를 우선합니다. 더 쉽게 최적화할 수 있습니다.
    -   **관련 없는 검색어**: 사이트에서 이 검색어와 관련된 콘텐츠를 다루지 않는다면 오히려 좋은 기회로 삼아 콘텐츠를 살짝 손보거나 관련 트래픽을 유도하는 검색어에 집중할 수 있습니다.
4.  **최상위 게재순위, 낮은 CTR**: 여러 이유로 인해 이러한 검색어는 CTR이 낮을 수 있습니다. 가장 큰 풍선을 확인하여 다음 징후가 있는지 확인해야 합니다.
    -   경쟁업체에 [구조화된 데이터 마크업](https://developers.google.com/search/docs/appearance/search-result-features?hl=ko)이 있을 수 있으며 리치 결과로 표시되어 내 검색결과가 아닌 경쟁업체의 검색결과를 클릭하도록 사용자를 유도할 수 있습니다. [Google 검색에서 가장 일반적인 시각적 요소](https://developers.google.com/search/docs/appearance/visual-elements-gallery?hl=ko)를 최적화해 보세요.
    -   사용자가 사이트와 관련하여 관심을 보이지 않는 검색어의 순위를 최적화했거나 '실수로' 순위를 매겼을 수 있습니다. 별 문제가 되지 않는다면 해당 검색어를 무시해도 됩니다. 이러한 검색어가 사용된 결과로 사이트가 표시되지 않게 하려면(예: 불쾌감을 주는 단어가 포함된 경우) 콘텐츠를 살짝 조정하여 트래픽을 유도하는 검색어의 동의어나 관련 검색어로 생각될 수 있는 언급을 삭제해 보세요.
    -   사람들이 회사의 영업시간이나 주소, 전화번호 등 필요한 정보를 이미 확인했을 수도 있습니다. 이때 어떤 검색어가 사용되었는지, 해당 정보가 포함된 URL은 무엇인지 확인하세요. 웹사이트 목표 중 하나가 고객을 매장으로 유도하는 것이라면 이는 의도한 대로 작동하는 것입니다. 사람들이 웹사이트를 방문하여 추가 정보를 확인해야 한다고 생각한다면, 제목과 설명을 최적화하여 이러한 메시지를 명확하게 전달할 수 있습니다. 자세한 내용은 다음 섹션을 참고하세요.

여기서는 기기 카테고리는 언급하지 않았습니다. 기기 카테고리는 검색어의 실적을 보여주는 추가적인 신호로 사용할 수 있기 때문입니다. 예를 들어 어떤 검색어는 사람들이 어떤 거리에서 어떤 장소를 찾으려고 할 때 좀 더 관련성이 높다고 생각해 봅시다. 이 경우 이 검색어가 휴대전화에서는 좋은 실적을 올리더라도 데스크톱에서는 실적이 저조할 수 있습니다.

## 특정 검색어의 검색엔진 최적화 개선

시간과 노력을 들일 가치가 있는 검색어를 찾으면 해당 검색어와 관련된 페이지를 최적화하거나 만들어 보세요.

이 페이지에 나온 시각화를 사용하여 쿼리를 찾은 후에는 Search Console 사용자 인터페이스에서 특정 쿼리에 대한 [쿼리 필터를 만들거나](https://support.google.com/webmasters/answer/7576553?hl=ko#filteringdata) Looker Studio를 사용해 [피벗 테이블](https://support.google.com/looker-studio/answer/7516660?hl=ko)을 만들 수 있습니다. 이 두 가지 방법을 사용하면 특정 검색어에 대해 트래픽이 발생하는 모든 페이지를 확인할 수 있습니다. 최적화할 검색어 및 관련 URL을 파악했다면 [SEO 기본 가이드](https://developers.google.com/search/docs/fundamentals/seo-starter-guide?hl=ko)를 참고하여 콘텐츠를 최적화하세요. 이때 다음 도움말을 참고하세요.

-   [제목](https://developers.google.com/search/docs/appearance/title-link?hl=ko#page-titles) 요소, [설명 메타 태그](https://developers.google.com/search/docs/appearance/snippet?hl=ko#meta-descriptions), Alt 속성이 구체적이고 정확한지 확인합니다.
-   제목 요소를 사용하여 중요한 텍스트를 강조하고 콘텐츠의 계층 구조를 만들어 사용자와 검색엔진이 문서를 더 쉽게 탐색할 수 있도록 합니다.
-   동의어, 관련 검색어 등 사용자가 내 콘텐츠를 찾을 때 다른 어떤 단어를 검색할 수 있을지 생각해 봅니다. Google Ads에서 제공하는 [키워드 플래너](https://ads.google.com/home/tools/keyword-planner/?hl=ko)를 사용하면 새로운 키워드 변형을 찾고 각 키워드의 대략적인 검색량을 확인할 수 있습니다. [Google 트렌드](https://developers.google.com/search/docs/monitor-debug/google-trends?hl=ko)를 사용하여 웹사이트와 관련된 상승 주제와 검색어를 통해 아이디어를 찾을 수도 있습니다.