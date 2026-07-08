Google의 크롤러 인프라는 사이트에 가장 적합한 크롤링 속도를 결정하는 정교한 알고리즘을 사용합니다. Google의 목표는 방문한 사이트에서 서버에 무리를 주지 않으면서 가능한 한 많은 페이지를 크롤링하는 것입니다. 경우에 따라 Google에서 사이트를 크롤링하면 인프라에 심각한 부하가 발생하거나 중단된 기간에 원치 않는 비용이 발생할 수 있습니다. 이 문제를 완화하려면 Google 크롤러가 생성하는 요청 횟수를 줄여달라고 선택하세요.

## 크롤링이 급격히 증가한 원인 파악하기

비효율적인 사이트 구조나 사이트 관련 문제로 인해 크롤링이 급격히 증가할 수 있습니다. 이전에 접수된 신고를 바탕으로 보았을 때 이러한 상황이 발생하는 가장 일반적인 원인은 다음과 같습니다.

-   사이트의 URL이 비효율적으로 구성되어 있으며 일반적으로 사이트의 특정 기능으로 인해 발생함
    -   속성 탐색 또는 사이트의 기타 정렬 및 필터링 기능
    -   특정 날짜의 URL이 많은 캘린더
-   [동적 검색 광고 타겟](https://developers.google.com/search/docs/crawling-indexing/troubleshoot-crawling-errors?hl=ko#adsbot)

호스팅 회사에 문의하여 서버의 최근 액세스 로그에서 트래픽 소스를 파악한 다음, 앞서 언급한 크롤링 급증의 일반적인 원인에 해당하는지 확인하는 것이 좋습니다. 그런 다음 [속성 탐색 URL 크롤링 관리](https://developers.google.com/search/docs/crawling-indexing/crawling-managing-faceted-navigation?hl=ko) 및 [크롤링 효율성 최적화](https://developers.google.com/search/docs/crawling-indexing/troubleshoot-crawling-errors?hl=ko#improve_crawl_efficiency)에 관한 가이드를 확인하세요.

## 크롤러 트래픽을 긴급하게 줄이기(긴급 상황의 경우)

짧은 기간 동안(예: 2~3시간 또는 1~2일) 긴급하게 크롤링 속도를 낮춰야 한다면 `200` 대신 `500`, `503` 또는 `429` HTTP 응답 상태 코드를 크롤링 요청으로 반환하세요. `500`, `503` 또는 `429` HTTP 응답 상태 코드가 포함된 URL을 다수 발견하게 되면(예: [웹사이트를 사용 중지한 경우](https://developers.google.com/search/docs/crawling-indexing/pause-online-business?hl=ko)) Google의 크롤링 인프라에서 사이트의 크롤링 속도를 낮춥니다. 크롤링 속도가 감소하면 사이트의 전체 호스트 이름(예: `subdomain.example.com`), 오류를 반환하는 URL 크롤링 및 콘텐츠를 반환하는 URL 모두에 영향을 줍니다. 이러한 오류의 수가 줄어들면 크롤링 속도가 자동으로 다시 높아집니다.

## 크롤링 속도 감소를 위한 예외적인 요청

인프라에서 Google 크롤러에 오류를 제공할 수 없다면 [특별 요청을 제출](https://search.google.com/search-console/googlebot-report?hl=ko)하여 크롤링 속도가 비정상적으로 높은 문제를 신고하고, 요청할 때 사이트에 적합한 최적의 속도를 언급하세요. 크롤링 속도를 높여달라고 요청할 수 없으며 요청이 평가되고 처리되는 데 며칠이 걸릴 수 있습니다.