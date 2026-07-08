<iframe frameborder="0" allowfullscreen="" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share" referrerpolicy="strict-origin-when-cross-origin" width="640" height="360" src="https://www.youtube.com/embed/IIvIRgpCOqc?origin=https%3A%2F%2Fdevelopers.google.com&amp;autoplay&amp;controls&amp;embed_domain&amp;enablejsapi=1&amp;end&amp;hl&amp;showinfo&amp;start&amp;video-id=IIvIRgpCOqc&amp;widgetid=85&amp;forigin=https%3A%2F%2Fdevelopers.google.com%2Fsearch%2Fdocs%2Fmonitor-debug%2Fdebugging-search-traffic-drops%3Fhl%3Dko&amp;aoriginsup=1&amp;gporigin=https%3A%2F%2Fdevelopers.google.com%2Fsearch%2Fdocs%2Fcrawling-indexing%2Famp%2Fabout-amp%3Fhl%3Dko&amp;vf=1" id="widget86" data-title="YouTube video player" title="Analyzing drops in Google Search traffic - Google Search Console Training"></iframe>

자연 검색 트래픽 감소는 여러 가지 이유로 발생할 수 있으며 사이트에 어떤 문제가 발생했는지 정확히 파악하기 어려울 수 있습니다. 이 가이드에서는 Search Console [실적 보고서](https://support.google.com/webmasters/answer/7576553?hl=ko) 및 [Google 트렌드](https://trends.google.com/?hl=ko)를 사용하여 검색 트래픽 감소의 원인을 조사하고 해결하는 방법을 설명합니다.

## 자연 검색 트래픽 감소의 주요 원인

Google 검색 트래픽에 영향을 미치는 요소를 알아보려면 이미지에 있는 스케치를 확인해 보세요. 트래픽에 영향을 줄 수 있는 요인과 그래프 모양이 어떻게 표시될지 대략적으로 확인할 수 있습니다.

트래픽 감소 그래프와 잠재적 원인을 보여주는 스케치

알고리즘 업데이트, 사이트 전체 보안 또는 스팸 문제로 인한 대폭 하락

계절성

사이트 전반의 기술적 문제, 관심분야 변화

오류 신고 ¯\\\_(ツ)\_/¯

다음 섹션에서는 트래픽 감소의 원인을 분석할 때 조사해야 하는 주요 원인을 설명합니다. 또한 Search Console의 [데이터 이상 페이지](https://support.google.com/webmasters/answer/6211453?hl=ko)에서 사이트에 적용할 수 있는 항목이 있는지 확인하세요. 데이터 처리 변경이나 로깅 오류로 인해 감소가 발생했을 수 있습니다.

### 알고리즘 업데이트

Google에서는 항상 콘텐츠 평가 방식을 개선하고 그에 따라 적절하게 검색 순위 및 게재 알고리즘을 업데이트합니다. [핵심 업데이트](https://developers.google.com/search/updates/core-updates?hl=ko)와 기타 소규모 업데이트로 인해 Google 검색 결과에서 일부 페이지의 실적이 변경될 수 있습니다. Google에서는 [순위 업데이트 목록 페이지](https://status.search.google.com/products/rGHU1u87FJnkP6W2GwMi/history?hl=ko)에 시스템 개선사항에 관한 글을 게시합니다. 이 페이지에서 사이트에 적용할 수 있는 사항이 있는지 확인해 보세요.

알고리즘 업데이트로 인해 트래픽이 발생했다고 생각되면 근본적으로 콘텐츠 문제가 아닐 수 있다는 점을 이해하는 것이 중요합니다. 변경이 필요한지 확인하려면 다음과 같이 Search Console에서 상위 페이지를 검토하고 순위를 평가하세요.

-   **[게재순위 소폭 하락이란?](https://developers.google.com/search/docs/monitor-debug/debugging-search-traffic-drops?hl=ko#small)** 예를 들어 게재순위가 2위에서 4위로 떨어지는 것입니다.
-   **[게재순위 대폭 하락이란?](https://developers.google.com/search/docs/monitor-debug/debugging-search-traffic-drops?hl=ko#large)** 예를 들어 게재순위가 4위에서 29위로 떨어지는 것입니다.

### 게재순위 소폭 하락

_게재순위가 소폭 하락_은 상위 검색 결과에서 게재순위가 조금 변동한 경우입니다(예: 검색어의 게재순위가 2위에서 4위로 하락). Search Console에서 노출수에는 큰 변화가 없는데도 트래픽이 눈에 띄게 감소하는 것을 볼 수 있습니다.

게재순위의 미세한 변동은 언제든지 발생할 수 있습니다(별도의 작업 없이 원래 게지순위로 다시 이동 포함). 이미 페이지 실적이 우수한 경우라면 급격한 변경사항을 적용하지 않는 것이 좋습니다.

### 게재순위 대폭 하락

_게재순위 대폭 하락_은 광범위한 검색어에 대한 최상위 결과에서 눈에 띄는 감소가 나타나는 것을 말합니다(예: 결과 게재순위 10위에서 29위로 하락).

이 경우 개별 페이지뿐만 아니라 웹사이트 전체를 자체 평가하여 [유용하고 신뢰할 수 있으며 사람 중심](https://developers.google.com/search/docs/fundamentals/creating-helpful-content?hl=ko)의 웹사이트인지 확인하세요. 사이트를 변경한 경우 변경사항이 적용되기까지 시간이 걸릴 수 있습니다. 일부 변경사항은 며칠 이내에 적용되지만 몇 개월이 걸리는 경우도 있습니다. 예를 들어, Google 시스템이 사이트가 장기적으로 유용한 콘텐츠를 생산하고 있다고 판단하기까지 몇 달이 걸릴 수 있습니다. 일반적으로 몇 주 후에 Search Console에서 사이트를 다시 분석하여 이러한 조치가 게재순위에 긍정적인 영향을 미쳤는지 확인하는 것이 좋습니다.

### 기술적 문제

기술적 문제란 Google에서 페이지를 크롤링하거나 색인을 생성하거나 사용자에게 제공하는 것을 막는 오류입니다(예: 서버 가용성, robots.txt 가져오기, 페이지를 찾을 수 없음 등).

이는 사이트 전체의 문제(예: 웹사이트 다운)일 수도 있고 페이지 전체의 문제(예: Google이 페이지를 크롤링하는 데 의존하는 잘못 배치된 `noindex` 태그, 이로 인해 트래픽이 보다 서서히 감소)일 수도 있습니다.

[크롤링 통계 보고서](https://search.google.com/search-console/settings/crawl-stats?hl=ko) 및 [페이지 색인 생성 보고서](https://search.google.com/search-console/index?hl=ko)에서 이러한 감소에 상응하는 급증이 발생하고 있는지 확인하세요. 이렇게 하면 문제를 정확히 파악하는 데 도움이 될 수 있습니다.

### 보안 문제

사이트에 멀웨어나 피싱 같은 [보안상의 위협](https://developers.google.com/search/docs/monitor-debug/security?hl=ko)이 있는 경우 Google에서 사용자가 사이트에 도달하기 전에 경고나 인터스티셜 페이지를 통해 사용자에게 알릴 수 있으며 이로 인해 Google 검색 트래픽이 감소할 수 있습니다.

[보안 문제 보고서](https://search.google.com/search-console/security-issues?hl=ko)를 확인하여 Google에서 웹사이트의 보안 위협을 감지했는지 확인합니다.

### 스팸 문제

Google에서는 Google 검색 스팸 정책을 위반하는 행위를 자동화 시스템으로 감지하고 필요에 따라 사람의 검토를 통해 확인하여 [직접 조치](https://search.google.com/search-console/manual-actions?hl=ko)를 취할 수 있습니다. 사이트가 [Google 웹 검색의 스팸 정책](https://developers.google.com/search/docs/essentials/spam-policies?hl=ko)을 준수하지 않는 경우 콘텐츠 순위가 낮아지거나 아예 검색 결과에 표시되지 않을 수 있습니다.

스팸 정책 위반으로 인해 트래픽이 감소한 것으로 의심되는 경우, Google의 [스팸 정책](https://developers.google.com/search/docs/essentials/spam-policies?hl=ko)을 검토하여 Google 자동화 시스템에서 감지할 수 있는 스팸 행위에 관여하지 않는지 확인하세요. 또한 Search Console의 [직접 조치 보고서](https://search.google.com/search-console/manual-actions?hl=ko)에서 웹사이트에 해당하는 직접 조치 문제가 있는지 확인합니다.

### 계절성 및 관심분야 변화

새로운 트렌드나 연중 계절성에 따른 사용자 행동의 변화로 인해 특정 검색어 수요가 변경되기도 합니다. 즉, 외부 영향으로 트래픽이 감소할 수 있습니다.

[실적 보고서](https://search.google.com/search-console/performance/search-analytics?hl=ko)에서 한 번에 하나의 검색어만 포함하도록 [필터를 적용](https://support.google.com/webmasters/answer/7576553?hl=ko#filteringdata)하여 클릭수와 노출수가 감소한 쿼리를 찾습니다. 즉, 가장 많은 트래픽을 얻은 검색어를 선택합니다. 그런 다음 [Google 트렌드](https://trends.google.com/trends/?hl=ko)에서 이러한 감소가 웹사이트에서만 발생한 것인지, 아니면 웹 전체에서 발생한 것인지 파악합니다.

### 사이트 이전 및 마이그레이션

사이트의 기존 페이지 URL을 변경하면 Google에서 사이트를 다시 크롤링하고 색인을 다시 생성하는 동안 순위가 변동될 수 있습니다. 일반적으로 보았을 때, 중간 규모의 웹사이트의 경우 Google이 변경사항을 인식하는 데 대개 몇 주 정도 걸릴 수 있으며 대형 사이트는 더 오래 걸립니다.

사이트를 이전한 후 감소가 발생했으나 트래픽이 원래대로 돌아오지 않는다면 [사이트 이전 문제 해결 섹션](https://developers.google.com/search/docs/crawling-indexing/site-move-with-url-changes?hl=ko#troubleshooting)에서 URL을 변경하면서 사이트를 이전할 때 흔히 저지르게 되는 실수를 확인하세요.

## Google 검색 트래픽 감소 패턴 분석

트래픽에 무슨 일이 발생했는지 파악하는 가장 좋은 방법은 많은 정보를 요약해서 보여주는 Search Console 실적 보고서의 기본 차트를 확인하는 것입니다.

노출수와 클릭수가 모두 감소한 경우 그 원인이 될 수 있는 [가장 일반적인 이유 목록](https://developers.google.com/search/docs/monitor-debug/debugging-search-traffic-drops?hl=ko#main-causes)을 확인하세요. 노출수는 동일하지만 클릭수가 감소하는 경우, 가능한 최적의 [페이지 제목](https://developers.google.com/search/docs/appearance/title-link?hl=ko)과 [스니펫](https://developers.google.com/search/docs/appearance/snippet?hl=ko)을 생성하지 못하여 사용자가 내 페이지의 콘텐츠를 이해하지 못하거나 다른 사이트에서 더 매력적인 [리치 결과](https://developers.google.com/search/docs/appearance/structured-data/search-gallery?hl=ko)를 얻은 것일 수도 있습니다.

[Google 검색 실적 보고서](https://search.google.com/search-console/performance/search-analytics?hl=ko)로 이동하여 다음 섹션에 설명된 대로 데이터에 [필터를 적용](https://support.google.com/webmasters/answer/7576553?hl=ko#filteringdata)해 보세요.

### 16개월을 포함하도록 기간을 변경합니다

차트 상단에서 **날짜** 필터를 선택하고 **지난 16개월**을 선택합니다. 이렇게 하면 맥락을 고려하여 트래픽 감소를 분석할 뿐만 아니라 축제 행사나 트렌드로 인해 매년 발생하는 감소가 아닌지 확인할 수 있습니다. 16개월보다 더 긴 기간을 사용하려면 [Search Analytics API](https://developers.google.com/webmaster-tools/search-console-api-original/v3/searchanalytics?hl=ko) 또는 [일괄 데이터 내보내기](https://support.google.com/webmasters/answer/12917675?hl=ko)를 사용하여 데이터를 가져와 시스템에 저장하면 됩니다.

![Search Console의 실적 보고서에 지난 16개월을 표시하는 기간 필터](https://developers.google.com/static/search/docs/images/performance-report-date-range.png?hl=ko)

다음 차트는 연간 시즌성(16개월 데이터)의 실적 차트를 보여줍니다. 보시다시피 최근의 트래픽 감소는 작년에도 정확히 같은 패턴으로 발생했던 현상입니다.

![Search Console의 실적 보고서에 표시된 연간 시즌성](https://developers.google.com/static/search/docs/images/yearly-seasonality-chart.png?hl=ko)

### 트래픽이 감소한 기간을 비슷한 기간과 비교합니다

차트 상단에서 **날짜** 필터를 선택하고 **비교** 탭을 선택한 다음 **최근 3개월과 이전 기간 비교** 또는 **전년 대비 최근 3개월 동안의 데이터 비교**를 선택합니다. 이렇게 하면 정확히 무엇이 달라졌는지 검토할 수 있습니다. 모든 탭을 클릭하여 특정 검색어나 URL, 국가, 기기, 검색 노출에 대해서만 변화가 발생했는지 확인합니다. [비교 필터](https://support.google.com/webmasters/answer/7576553?hl=ko#comparingdata) 만드는 방법을 알아보세요.

![기간 필터 비교](https://developers.google.com/static/search/docs/images/search-console-date-range-filter-comparison.png?hl=ko)

다음 차트는 3개월 동안의 실적 차트를 비교한 것입니다. 전체 선(지난 3개월)과 점선(이전 3개월)을 비교하면 트래픽 감소가 어떻게 나타나는지 명확하게 확인할 수 있습니다.

![트래픽 감소를 보여주는 실적 보고서 비교 모드](https://developers.google.com/static/search/docs/images/search-traffic-drop-comparison.png?hl=ko)

### 다양한 검색 유형을 개별적으로 분석합니다

차트 상단에서 **검색 유형** 필터를 선택하고 여러 가지 옵션을 사용해 봅니다. 이렇게 하면 감소가 발생한 위치(웹 검색이나 Google 이미지, 동영상 또는 뉴스 탭 등)를 파악할 수 있습니다.

![Search Console의 실적 보고서에 있는 검색 유형 필터](https://developers.google.com/static/search/docs/images/performance-search-type-filter.png?hl=ko)

### 검색결과의 평균 게재순위를 모니터링합니다

차트 위의 **평균 게재순위**를 클릭합니다. 일반적으로 보자면 절대적인 개재순위에만 너무 신경써서도 안 됩니다. 궁극적으로 사이트의 성공 척도가 되는 것은 노출수와 클릭수이기 때문입니다. 하지만 게재순위가 계속해서 급격하게 떨어지는 것이 확인된다면 [콘텐츠 자체 평가](https://developers.google.com/search/docs/fundamentals/creating-helpful-content?hl=ko#self-assess)를 통해 콘텐츠가 유용하며 신뢰할 만한지 가늠해 보세요.

![Search Console의 실적 보고서에 표시된 평균 게재순위 하락](https://developers.google.com/static/search/docs/images/search-average-position-decline.png?hl=ko)

### 영향을 받은 페이지에서 패턴을 확인합니다

차트 아래의 **페이지** 표를 검토하여 감소 원인을 설명할 수 있는 패턴을 찾아 봅니다. 예를 들어 한 가지 중요한 요소는 감소가 사이트 전체나 페이지 그룹에서 발생했는지, 아니면 사이트의 매우 중요한 페이지에서만 발생했는지 파악하는 것입니다. 감소 기간을 비슷한 기간과 비교하고, 많은 클릭수 손실이 발생한 페이지를 비교하세요. **클릭수 차이**를 선택하면 트래픽이 가장 많이 감소한 페이지를 기준으로 정렬됩니다.

사이트 전체 문제인 경우 [페이지 색인 생성 보고서](https://search.google.com/search-console/index?hl=ko)를 확인합니다. 특정 페이지 그룹에서만 트래픽 감소가 나타난다면 [URL 검사 도구](https://support.google.com/webmasters/answer/9012289?hl=ko)를 사용하여 일부 페이지를 조사합니다.

![Search Console의 실적 보고서에 표시된 페이지 비교](https://developers.google.com/static/search/docs/images/search-console-performance-page-comparison.png?hl=ko)

## 전반적인 업계 동향 조사

좀 더 자세히 분석하려면 [Google 트렌드를 사용](https://developers.google.com/search/docs/monitor-debug/trends-start?hl=ko)하여 감소가 좀 더 광범위한 추세인지, 아니면 내 사이트에만 발생하는지 파악할 수 있습니다. 이러한 변화가 발생하는 데는 2가지 요인이 있습니다.

1.  **관심분야 변경하기** 사용자의 검색 내용과 방법에 큰 변화가 생기면 사용자가 다른 검색어를 검색하거나 기기를 다른 용도로 사용할 수 있습니다. 또한 특정 브랜드를 온라인으로 판매하는 경우 동일한 검색어를 사용하는 새 제품이 있을 수 있습니다.
2.  **[계절성](https://en.wikipedia.org/wiki/Seasonality)**. 예를 들어 [음식 웹사이트의 패턴](https://rhythm-of-food.net/)을 통해 음식 관련 검색어는 계절의 영향을 상당히 많이 받는다는 사실을 수 있습니다. 즉, 1월에는 다이어트, 11월에는 칠면조, 12월에는 샴페인이 많이 검색되는 검색어입니다. 계절성의 정도는 업종마다 다릅니다.

다양한 업종의 동향을 분석하려면 Google 트렌드를 사용하면 됩니다. 이를 통해 거의 필터링되지 않은 실제 Google 검색 요청 샘플을 확인할 수 있습니다. 이 실제 검색 요청 샘플은 익명처리되고 분류, 집계됩니다. 이를 통해 Google은 여러 가지 주제에 대해 전 세계 또는 도시 수준에서 드러난 관심도를 표시할 수 있습니다.

내 웹사이트로 트래픽을 유도하는 검색어를 확인하여 연중 특정 시기에 명백한 감소가 있는지 살펴봅니다. 예를 통해 3가지의 트렌드 유형을 확인할 수 있습니다([데이터 확인](https://trends.google.com/trends/explore?date=today+5-y&geo=US&q=turkey%2Cchicken%2Ccoffee&hl=ko)).

1.  칠면조는 계절성이 강하고 매년 11월에 정점에 이릅니다.
2.  치킨은 계절성이 약간 있지만 칠면조에 비해서는 두드러지지 않습니다.
3.  커피는 훨씬 더 안정적입니다. 커피에 대한 수요는 1년 내내 유지되는 것으로 보입니다.

![Google 트렌드의 칠면조, 닭고기, 커피 트렌드](https://developers.google.com/static/search/docs/images/google-trends-analysis.png?hl=ko)

Google 검색 트래픽과 관련해 도움이 될 수 있는 다른 흥미로운 유용한 정보도 확인해 보세요.

-   Search Console의 실적 보고서에서 확인할 수 있는 바와 같이 **지역 내 인기 검색어를 확인하고 내 사이트로의 트래픽을 발생시키는 검색어와 비교합니다**. 내 사이트의 트래픽에는 없는 검색어가 있다면 그 주제에 관한 콘텐츠가 있는지 확인하고 해당 콘텐츠가 크롤링되고 색인이 생성되도록 합니다.
-   **중요한 주제와 관련된 검색어를 확인합니다**. 이렇게 하면 상승하는 관련 검색어를 확인할 수 있으므로 이렇게 새로운 주제를 다루는 관련 콘텐츠를 추가하는 등의 방식으로 사이트를 준비할 수 있습니다.