<iframe frameborder="0" allowfullscreen="" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share" referrerpolicy="strict-origin-when-cross-origin" width="640" height="360" src="https://www.youtube.com/embed/ViwW9D-brTQ?origin=https%3A%2F%2Fdevelopers.google.com&amp;autoplay&amp;controls&amp;embed_domain&amp;enablejsapi=1&amp;end&amp;hl&amp;showinfo&amp;start&amp;video-id=ViwW9D-brTQ&amp;widgetid=101&amp;forigin=https%3A%2F%2Fdevelopers.google.com%2Fsearch%2Fdocs%2Fmonitor-debug%2Fgoogle-analytics-search-console%3Fhl%3Dko&amp;aoriginsup=1&amp;gporigin=https%3A%2F%2Fdevelopers.google.com%2Fsearch%2Fdocs%2Fcrawling-indexing%2Famp%2Fabout-amp%3Fhl%3Dko&amp;vf=1" id="widget102" data-title="YouTube video player" title="Demystifying Google Analytics and Search Console data"></iframe>

[Search Console](https://developers.google.com/search/docs/monitor-debug/search-console-start?hl=ko)과 [Google 애널리틱스](https://developers.google.com/analytics?hl=ko)를 함께 사용하면 잠재고객이 웹사이트를 찾고 이용하는 방식을 더 종합적으로 파악하여 사이트의 검색엔진 최적화를 개선할 때 더 정확한 정보를 바탕으로 결정을 내릴 수 있습니다. 이 가이드에서는 [Looker Studio](https://support.google.com/looker-studio/answer/6283323?hl=ko)를 사용하여 Search Console 및 Google 애널리틱스의 측정항목을 모니터링하고, 데이터를 함께 시각화하고, 도구 간 데이터 불일치를 해결하는 방법을 설명합니다.

## Google 애널리틱스 및 Search Console 정보

이 두 도구를 함께 사용하면 잠재고객과 잠재고객이 사이트에 방문하기 전후로 웹사이트를 경험하는 방식을 더 잘 이해할 수 있습니다. 이를 통해 사이트의 Google 검색 실적, 다른 트래픽 소스와의 관계를 빠르게 파악할 수 있습니다.

-   **Search Console**: **Google 검색 결과에서 웹사이트 실적**에 관한 데이터(예: 웹사이트가 검색 결과에 표시된 횟수(노출수), 사용자가 검색에서 사이트를 방문하기 위해 클릭한 횟수(클릭수), 사용자가 웹사이트로 유입되는 검색어(검색어))를 제공합니다. Google 검색에서 사용자가 웹사이트에 도착하기 전에 발생한 활동에 중점을 둡니다.
-   **Google 애널리틱스**: 방문자가 방문한 페이지, 체류 시간, 취한 액션 등 **방문자가 웹사이트와 상호작용하는 방식**에 관한 데이터를 제공합니다. 또한 잠재고객이 어디에서 유입되는지에 관한 데이터를 표시하므로 이메일, 다른 웹사이트 또는 소셜 플랫폼의 추천, 유료 검색, 자연 검색과 같은 트래픽 채널의 효과를 측정하는 데 도움이 됩니다.

### Google 애널리틱스와 Search Console의 데이터 비교하기

Search Console 실적 데이터를 Google 애널리틱스 자연 트래픽과 비교하면 전환(예: 전자상거래 거래, 뉴스레터 가입, 리드 생성 양식 작성) 기여도를 Google 검색 트래픽에 부여하는 데 특히 유용합니다. 하지만 이러한 도구는 서로 다른 측정항목과 시스템을 사용하므로 데이터가 완전히 일치하지는 않으며 각 도구를 방문하면 더 많은 측정항목에 액세스할 수 있습니다.

데이터의 일반적인 패턴을 파악하려면 다음 두 측정항목에 집중하는 것이 좋습니다. 이 두 측정항목은 가장 비교하기 쉽기 때문입니다.

| **Search Console 클릭수**

_[클릭](https://support.google.com/webmasters/answer/7042828?hl=ko#click)_은 사용자가 Google 검색 결과에서 웹사이트로 연결되는 링크를 클릭할 때 발생합니다. | **Google 애널리틱스 세션수**

_[세션](https://support.google.com/analytics/answer/9191807?hl=ko)_은 사용자가 웹사이트 또는 앱과 상호작용하는 기간입니다. |
|-------------------------------------------------------------------------|-----------------------------------------------------|

## Looker Studio에서 Google 자연 검색 트래픽 모니터링하기

<iframe frameborder="0" allowfullscreen="" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share" referrerpolicy="strict-origin-when-cross-origin" width="640" height="360" src="https://www.youtube.com/embed/3ezmohvavzI?origin=https%3A%2F%2Fdevelopers.google.com&amp;autoplay&amp;controls&amp;embed_domain&amp;enablejsapi=1&amp;end&amp;hl&amp;showinfo&amp;start&amp;video-id=3ezmohvavzI&amp;widgetid=103&amp;forigin=https%3A%2F%2Fdevelopers.google.com%2Fsearch%2Fdocs%2Fmonitor-debug%2Fgoogle-analytics-search-console%3Fhl%3Dko&amp;aoriginsup=1&amp;gporigin=https%3A%2F%2Fdevelopers.google.com%2Fsearch%2Fdocs%2Fcrawling-indexing%2Famp%2Fabout-amp%3Fhl%3Dko&amp;vf=1" id="widget104" data-title="YouTube video player" title="Monitoring organic Google Search traffic in Looker Studio"></iframe>

Looker Studio를 사용하면 Search Console과 Google 애널리틱스의 사이트 자연 검색 트래픽을 하나의 보기로 시각화할 수 있습니다. 자체 데이터로 모니터링을 시작하려면 [Looker Studio 대시보드 템플릿](https://lookerstudio.google.com/reporting/408e669d-07d1-4353-a1dc-94f06bde27ef/page/Hqrp/preview?hl=ko)을 사용하세요.

### 대시보드 설정하기

대시보드 템플릿을 처음 열면 여러 오류가 표시됩니다. 차트를 보려면 먼저 자체 데이터를 구성해야 하기 때문에 이 문제가 발생합니다.

1.  [대시보드 템플릿](https://lookerstudio.google.com/reporting/408e669d-07d1-4353-a1dc-94f06bde27ef/page/Hqrp/preview?hl=ko)을 엽니다.
2.  **자체 데이터 사용**을 클릭합니다.
3.  데이터 소스를 구성합니다.
    1.  [Search Console에 연결](https://cloud.google.com/looker/docs/studio/connect-to-search-console?hl=ko)하고 표 패널에서 **URL 노출수**를 선택합니다.
    2.  [Google 애널리틱스에 연결](https://cloud.google.com/looker/docs/studio/connect-to-google-analytics?hl=ko)합니다.
4.  각 차트를 관련 데이터 소스에 계속 연결합니다.

### 대시보드 이해하기

대시보드에는 Google 애널리틱스 데이터와 Search Console 데이터가 나란히 표시됩니다. 각 데이터 소스를 쉽게 인식할 수 있도록 대시보드의 모든 차트에서 Google 애널리틱스에는 주황색을, Search Console에는 파란색을 사용합니다.

#### 필터 및 데이터 관리

Google 자연 검색 트래픽에 더 집중하기 위해 Google 애널리틱스 데이터는 이미 `Session source = google` 및 `Session medium = organic`의 세션만 포함하도록 필터링되어 있습니다.

![Looker Studio에서 세션 소스 및 세션 매체 필터링하기](https://developers.google.com/static/search/docs/images/scga-session-source-medium.png?hl=ko)

대시보드에는 데이터를 효과적으로 관리하는 데 도움이 되는 다음 필터와 데이터 컨트롤이 포함되어 있습니다.

![Looker Studio의 필터 및 데이터 컨트롤](https://developers.google.com/static/search/docs/images/scga-filters-data-controls.png?hl=ko)

1.  **[데이터 컨트롤](https://support.google.com/datastudio/answer/7415591?hl=ko)**: 분석하고자 하는 Search Console 및 Google 애널리틱스 속성을 선택합니다. 속성 간 전환은 여러 계정에 액세스할 수 있고 계정 간에 전환하려는 경우에 특히 유용합니다.
2.  **국가 및 기기**: 국가 및 기기 카테고리를 포함하거나 제외합니다.
3.  **기간**: 대시보드에 표시할 기간을 선택합니다. 보고서의 기본 기간은 '지난 28일'이지만 Search Console 데이터는 며칠 지연될 수 있습니다. 필요에 따라 언제든지 기간을 변경할 수 있습니다.

#### 측정항목

대시보드에서는 웹사이트의 자연 검색 트래픽의 양과 품질을 전반적으로 파악할 수 있는 5가지 측정항목을 사용합니다.

![Looker Studio 대시보드의 측정항목: 세션수, 참여율, 재방문자, 클릭수, CTR](https://developers.google.com/static/search/docs/images/scga-metrics.png?hl=ko)

| 대시보드의 측정항목 | 대시보드의 측정항목 |
|---------------------------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **1. 세션수**<br>(Google 애널리틱스) | 사용자가 웹사이트와 상호작용하는 기간입니다. 웹사이트 컨텍스트에서 세션은 사용자가 웹사이트에서 페이지 또는 화면을 보고 활성화된 세션이 없을 때(예: 이전 세션이 타임아웃되었을 때) 시작됩니다. 자연 검색으로 인해 발생한 웹사이트 트래픽 양을 표시합니다. [세션이 계산되는 방식](https://support.google.com/analytics/answer/9191807?hl=ko)에 대해 자세히 알아보세요. |
| **2. 참여율**<br>(Google 애널리틱스) | 콘텐츠를 사용한 세션의 비율입니다. 참여 세션은 다음 기준 중 하나를 충족하는 세션입니다.

-   _[주요 이벤트](https://support.google.com/analytics/answer/9355848?hl=ko)_가 발생한 세션
-   10초 이상 지속된 세션
-   페이지 조회수가 2회 이상인 세션

[참여율](https://support.google.com/analytics/answer/11109416?hl=ko)에 대해 자세히 알아보세요. |
| **3. 재방문자 수**<br>(Google 애널리틱스) | 이전 세션을 하나 이상 시작한 후 웹사이트로 돌아온 사용자의 비율입니다. 자연 검색을 통해 사용자가 웹사이트로 돌아오는지 여부를 보여줍니다. [재방문자](https://support.google.com/analytics/answer/12253918?hl=ko)에 대해 자세히 알아보세요. |
| **4. 클릭수**<br>(Search Console) | 사용자를 웹사이트로 연결하는 Google 검색 결과의 총 클릭수입니다. [클릭수가 집계되는 방식](https://support.google.com/webmasters/answer/7042828?hl=ko#click)에 대해 자세히 알아보세요. |
| **5. 클릭률(CTR)**<br>(Search Console) | 클릭수를 노출수로 나눈 값입니다. Google 검색 결과에서 웹사이트를 본 사용자가 링크를 클릭하여 웹사이트를 방문하는 빈도를 보여줍니다. |

#### 차트

대시보드에는 여러 차트도 포함되어 있어 Google 자연 검색을 통해 잠재고객이 사이트를 방문하는 방식을 더 효과적으로 분석할 수 있습니다. 주황색은 Google 애널리틱스 데이터, 파란색은 Search Console 데이터를 나타냅니다.

이러한 차트는 특정 상황이 발생하는 시점을 파악하는 데 도움이 되는 패턴에 중점을 둡니다. 대시보드의 목표는 데이터를 자세히 살펴보는 것이 아니라 트래픽의 변화를 신속하게 파악하는 것입니다.

![Looker Studio 대시보드의 차트: 시간 경과에 따른 세션수 및 참여율, 시간 경과에 따른 자연 검색 트래픽 비율, 시간 경과에 따른 클릭수 및 CTR, 클릭 및 CTR별 상위 페이지 및 검색어, 상위 국가 표](https://developers.google.com/static/search/docs/images/scga-charts.png?hl=ko)

1.  **시간 경과에 따른 자연 세션수 및 참여율**: 세션수는 Google 검색에서 발생하는 트래픽의 양을 나타내고 참여율은 트래픽의 품질을 나타냅니다. 이 두 가지를 함께 사용하면 자연 검색 트래픽의 실적을 평가하는 데 도움이 됩니다.
    -   **자연 트래픽에 큰 변화가 있는 경우** Search Console로 이동하여 추가 분석을 진행하세요. [트래픽이 감소하는 경우 취해야 할 조치](https://developers.google.com/search/docs/monitor-debug/debugging-search-traffic-drops?hl=ko)를 설명하는 문서가 있습니다.
    -   **참여율이 감소하는 경우** 콘텐츠를 분석하고 콘텐츠를 자연 검색 잠재고객과 더 관련성 높게 만들 수 있는지 확인합니다(예: 페이지 콘텐츠가 잠재고객이 내 콘텐츠를 찾는 데 사용하는 검색어와 밀접한 관련이 있게 하기).
2.  **시간 경과에 따른 자연 검색 트래픽 비율**: 이 비율은 잠재고객과 비즈니스에 따라 다르므로 좋거나 나쁜 비율은 없습니다. 동향이 크게 변동되었지만 세션 및 참여율 차트가 변동되지 않았다면 Google 애널리틱스로 이동하여 [트래픽 획득 보고서](https://support.google.com/analytics/answer/12923437?hl=ko)를 검토하세요. 다른 트래픽 소스가 크게 증가하거나 감소하여 자연 검색 비율이 높아지거나 낮아질 수 있습니다.
3.  **시간 경과에 따른 클릭수 및 CTR**: 클릭수와 CTR은 Google 검색에서의 실적 규모와 품질을 보여줍니다. 사용자가 검색 결과에서 내 사이트를 클릭하는지, 검색 [스니펫](https://developers.google.com/search/docs/appearance/snippet?hl=ko)이 사용자의 클릭을 유도하는 데 성공하는지 보여줍니다. 평소 패턴에 변화가 있는 경우 [하락 또는 급증이 발생한](https://developers.google.com/search/docs/monitor-debug/debugging-search-traffic-drops?hl=ko) 특정 검색어와 페이지를 확인하세요.
4.  **클릭 및 CTR 기준 상위 페이지 및 검색어:** 클릭수가 가장 많은 특정 페이지 및 검색어입니다. 이 표와 국가 표에는 기간 선택 도구에서 선택한 이전 기간 대비 사용 가능한 측정항목이 얼마나 달라졌는지 보여주는 열도 포함되어 있습니다.
5.  **상위 국가 표**: 사이트가 여러 국가 또는 지역에 서비스를 제공하는 경우 이러한 통계를 자세히 살펴보는 것이 좋습니다. Google 애널리틱스([보고서 필터](https://support.google.com/analytics/answer/11377859?hl=ko) 사용) 또는 Search Console([실적 필터](https://support.google.com/webmasters/answer/7576553?hl=ko#filteringdata) 사용)에서 모두 수행할 수 있습니다. 특정 국가만 포함하도록 데이터를 필터링한 후 시간 경과에 따른 페이지 또는 검색어의 변화를 확인할 수 있습니다.

## Google 애널리틱스 및 Search Console에서 자세히 조사하기

검색 실적의 신뢰할 수 있는 소스는 항상 Search Console이며, 사이트 내 행동의 신뢰할 수 있는 소스는 Google 애널리틱스입니다. Google 자연 검색 트래픽 대시보드를 사용하면 검색 트래픽을 쉽게 모니터링할 수 있지만 트래픽 문제를 디버그하고 해결책을 찾을 수는 없습니다(각 도구에 직접 액세스할 수 있음).

Google 애널리틱스에서 다음 보고서는 사이트의 자연 검색 실적을 심층적으로 살펴보고 조사하는 데 특히 유용합니다.

-   **[트래픽 확보 보고서](https://support.google.com/analytics/answer/12923437?hl=ko)**: 세션 소스를 조사합니다. 여기에서 채널 '자연 검색'과 소스 'Google'에서 발생한 세션수를 확인할 수 있습니다. 이를 통해 Google 검색 트래픽에 대해 자세히 알아볼 수 있습니다. 예를 들어 사용자가 웹사이트에서 취한 액션, 최종적으로 구매했는지 또는 콘텐츠를 구독했는지 여부 등을 파악할 수 있습니다.
-   **Google 자연 검색에서 발생한 세션만 포함하도록 필터링된 [방문 페이지 보고서](https://support.google.com/analytics/answer/12931766?hl=ko)**: 페이지가 자연 트래픽에 얼마나 유용한지, 웹사이트에서 사용자 참여와 전환을 유도하는 데 페이지가 얼마나 효과적인지 파악할 수 있습니다.

Search Console에서 실적 보고서는 트래픽 변동을 파악하는 데 가장 유용합니다. 먼저 [실적 보고서 일반 작업](https://support.google.com/webmasters/answer/7576553?hl=ko#common_tasks)을 검토하여 데이터를 파악하고 필요한 경우 도구에서 [사용 가능한 다른 보고서](https://developers.google.com/search/docs/monitor-debug/search-console-start?hl=ko)를 사용해 보세요.

## Google 애널리틱스와 Search Console 간의 데이터 불일치 이해하기

이러한 도구 간의 데이터를 비교해 보면 가장 유사한 측정항목인 세션수와 클릭수도 정확하게 일치하지 않는 것을 알 수 있습니다. 총 개수는 정확하게 일치하지 않지만 중요한 것은 일반적인 동향의 패턴이 동일하다는 것입니다. 이 섹션에서는 차이가 발생하는 이유와 큰 불일치를 최소화하는 방법(해당하는 경우)을 설명합니다.

-   **사소한 불일치**: 차이가 작으면 불일치를 무시해도 됩니다. 시스템이 다르므로 수치가 약간 다른 것은 정상적이며 수정할 필요가 없습니다.
-   **큰 불일치**: 차이가 큰 경우 [다음 이유](https://developers.google.com/search/docs/monitor-debug/google-analytics-search-console?hl=ko#big-discrepancy)를 자세히 살펴보세요. 차이를 최소화하거나 숫자가 다른 이유를 파악할 수 있습니다.

### 클릭수와 세션수에서 큰 불일치가 발생하는 주요 이유

자연 Google 검색 트래픽 대시보드를 보거나 도구에서 내보낸 세션수와 클릭수 데이터를 비교할 때 Google 애널리틱스 데이터와 Search Console 데이터 간에 차이가 있을 수 있습니다. 데이터에 불일치가 있는 경우 다음 시나리오 중 하나가 사이트에 적용되는지 확인합니다. 사이트 구성, 잠재고객, 트래픽 구성에 따라 이유가 여러 개일 수 있습니다.

| 클릭수와 세션수의 큰 차이가 발생하는 이유 | 클릭수와 세션수의 큰 차이가 발생하는 이유 |
|-------------------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **Google 애널리틱스에서의 구현** | Google 애널리틱스는 웹사이트 또는 앱에 태그를 구현하여 행동 데이터를 수집할 수 있는 도구이므로, 구현하는 내용과 방식에 따라 달라집니다. Google 애널리틱스에는 데이터 품질에 영향을 미칠 수 있는 구현 및 구성 문제가 있습니다. 예를 들어 웹사이트에 애널리틱스 태그가 누락된 페이지가 있을 수 있습니다. 애널리틱스가 올바르게 설정되었는지 확인하려면 [설정 가이드](https://support.google.com/analytics/answer/9304153?hl=ko)의 단계를 따르세요.

반면 Search Console은 Google에서 모든 속성에 대해 균일하게 처리하는 Google 검색 데이터에 액세스할 수 있게 해주는 도구입니다. 즉, 설정을 구성하는 방식이 데이터에 미치는 영향이 적습니다. |
| **쿠키 또는 추적** | 사이트에서 사용자에게 추적을 수락하도록 요청하고 사용자가 거부하면 Google 애널리틱스 데이터가 왜곡될 수 있습니다. 애널리틱스 관점에서 이 문제를 처리하는 방법을 자세히 알아보려면 [사용자 동의 관리 소개](https://support.google.com/analytics/answer/12329599?hl=ko)를 참고하세요. |
| **시간대** | Google 애널리틱스에서는 시간대를 선택할 수 있지만 Search Console에서는 시간대를 맞춤설정할 수 없으며 [기본 시간대는 태평양 표준시(PT)](https://support.google.com/webmasters/answer/7576553?hl=ko#timezone)입니다. 이는 Google 애널리틱스의 시간대를 PT와 차이가 큰 위치로 설정하는 경우(예: 사이트에서 주로 오스트레일리아 사용자를 대상으로 하는 경우) 특히 두드러집니다. |
| **기여 분석** | Google 애널리틱스에서는 [세 가지 기여 분석 모델](https://support.google.com/analytics/answer/10596866?hl=ko)을 사용할 수 있지만 Search Console에서는 Google 검색의 모든 클릭을 집계합니다. 사용 가능한 가장 유사한 기여 분석 모델은 Google 애널리틱스의 기본 모델입니다. |
| **표준 URL** | Search Console은 [Google 검색 표준 URL에 관해서만 보고](https://support.google.com/webmasters/answer/7042828?hl=ko#url)하는 반면, Google 애널리틱스는 추적 코드가 포함된 모든 URL에 관해서 보고합니다. 즉, Google 애널리틱스에 더 많은 URL이 표시될 수 있습니다. |
| **트래픽 분류** | Search Console은 웹, 이미지, 동영상, 뉴스, 디스커버별로 트래픽을 분류합니다. 이러한 카테고리 분류는 Google 애널리틱스에서는 다릅니다. |
| **비 HTML 페이지** | 사이트에 비 HTML 페이지(예: PDF)가 있는 경우 Search Console에는 이러한 페이지가 검색에 표시되거나 클릭되면 기본적으로 포함됩니다. Google 애널리틱스가 이를 측정하도록 구성되지 않았을 수 있습니다. [향상된 측정 이벤트](https://support.google.com/analytics/answer/9216061?hl=ko)를 사용 설정하는 것이 좋습니다. |
| **봇 트래픽** | Google 애널리틱스는 [알려진 크롤러와 스파이더의 트래픽을 자동으로 제외](https://support.google.com/analytics/answer/9888366?hl=ko)하지만 Search Console에서는 이를 꼭 필터링하지는 않습니다. |

## Search Console과 Google 애널리틱스를 함께 사용하는 방법에 관한 리소스

Search Console과 Google 애널리틱스를 함께 분석하고 시각화하는 다른 방법을 알아보려면 다음 리소스를 확인하세요.

-   **[Search Console을 Google 애널리틱스에 연결](https://support.google.com/analytics/answer/10737381?hl=ko)**: 이렇게 하면 Google 애널리틱스 내에서 몇 가지 Search Console 보고서를 사용할 수 있습니다. 이는 웹사이트로의 Google 자연 검색 트래픽을 유도한 검색어와 방문 페이지에 빠르게 액세스하려는 경우에 유용합니다.
-   **[WordPress용 Site Kit 플러그인](https://sitekit.withgoogle.com/documentation/getting-started/connecting-services/)**: 사이트가 WordPress에 있는 경우 WordPress 내의 단일 대시보드에서 Google 애널리틱스와 Search Console 데이터를 모두 볼 수 있습니다.
-   **Search Console 대량 데이터 내보내기 및 Google 애널리틱스 BigQuery 내보내기**: 세부정보를 최대한 많이 확인하고 데이터 불일치를 최소화하려면 [Search Console 데이터를 BigQuery로 내보내기](https://support.google.com/webmasters/answer/12917675?hl=ko)하고 [Google 애널리틱스 BigQuery 내보내기](https://support.google.com/analytics/answer/9358801?hl=ko)의 데이터와 병합하는 것이 좋습니다.