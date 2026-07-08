## 인리치드 검색결과

Google 검색은 일반적인 리치 결과 외에도 더욱 향상된 대화형 리치 결과인 _인리치드 검색결과_를 지원합니다. 인리치드 검색결과에는 일반적으로 몰입형 환경이나 기타 고급 상호작용 기능이 포함됩니다. 예를 들어 사용자가 '미국 채용정보'를 검색했을 때 다음과 같은 채용정보의 인리치드 결과가 표시될 수 있습니다.

![채용정보 인리치드 검색결과](https://developers.google.com/static/search/docs/images/jobs-search-ui.png?hl=ko)

사용자는 인리치드 결과를 통해 구조화된 데이터 항목의 다양한 속성을 검색할 수 있습니다. 예를 들어 200칼로리 이하의 치킨 수프 조리법이나 준비 시간이 1시간 이하인 조리법을 검색할 수 있습니다.

## 인리치드 검색 구현

인리치드 검색은 리치 결과의 하위 집합이며 [구조화된 데이터](https://developers.google.com/search/docs/appearance/structured-data/intro-structured-data?hl=ko)를 사용하여 구현됩니다. 일부 리치 결과 유형은 인리치드 검색 유형으로만 제공되며(예: 레시피, 채용정보, 이벤트), 다른 리치 결과 유형은 몇 가지 속성이 추가된 인리치드 검색 유형으로 확장될 수 있습니다. 리치 결과 유형에 관한 도움말에는 기본 리치 결과가 인리치드 결과로 확장될 수 있는지와 그 방법을 설명합니다.

[기술 정보 및 결과 갤러리는 여기에서 확인할 수 있습니다.](https://developers.google.com/search/docs/appearance/structured-data/search-gallery?hl=ko)

인리치드 검색은 Google 검색 순위 알고리즘에 따라 실행되며, 페이지에 적절한 구조화된 데이터를 추가하는 것 외에도 다음의 품질 가이드라인을 따라야 Google에서 제대로 페이지의 색인을 생성하고 순위를 선정할 수 있습니다.

-   [구조화된 데이터 품질 가이드라인](https://developers.google.com/search/docs/appearance/structured-data/sd-policies?hl=ko#quality-guidelines)
-   [검색 Essentials](https://developers.google.com/search/docs/essentials?hl=ko)
-   [인리치드 검색 품질 가이드라인](https://developers.google.com/search/docs/appearance/enriched-search-results?hl=ko#guidelines)

## 인리치드 검색 유형

다음 검색 유형은 인리치드 검색 환경을 지원합니다.

-   [채용정보](https://developers.google.com/search/docs/appearance/structured-data/job-posting?hl=ko)
-   [레시피](https://developers.google.com/search/docs/appearance/structured-data/recipe?hl=ko)
-   [이벤트](https://developers.google.com/search/docs/appearance/structured-data/event?hl=ko)

## 인리치드 검색 품질 가이드라인

인리치드 검색을 사용하려면 다음 스팸 정책을 준수해야 합니다. 인리치드 검색 순위 알고리즘에서 사이트 대부분이 품질 기준을 만족하지 못하는 것으로 간주되면 사이트 전체가 인리치드 검색결과에서 제외될 수 있습니다.

-   **필수 속성:** 각 인리치드 검색 유형마다 필수 속성이 정의되어 있습니다. 필수 속성이 누락된 항목에는 인리치드 검색을 적용할 수 없습니다.
-   **완전성:** 추가(권장) 속성을 많이 제공할수록 사용자에게 제공되는 항목의 품질이 더 높아집니다. 채용정보의 경우 사용자는 급여를 명시한 채용정보를 그렇지 않은 채용정보보다 선호하며, 인리치드 검색 순위에서도 이러한 특성이 고려됩니다. 조리법에 실제 사용자 리뷰와 신뢰성이 있는 별표 평점이 있는 경우 사용자가 사이트의 정보와 인리치드 검색을 더욱 신뢰하게 됩니다. 완전성은 인리치드 검색의 가장 중요한 순위 결정 신호 중 하나입니다.
-   **관련성:** 마크업된 데이터는 내가 참여 중인 인리치드 검색과 관련성이 있어야 합니다. 다음은 관련 없는 데이터의 몇 가지 예입니다.
    -   방송을 지역 이벤트로 지정하는 스포츠 실시간 스트리밍 사이트
    -   안내를 레시피로 지정하는 목공예 사이트
-   **리프 콘텐츠:** 인리치드 검색은 리프 페이지에서만 사용할 수 있으며 목록 페이지에서는 사용할 수 없습니다. 리프 페이지란 항목의 세부 속성을 설명하는 페이지를 말합니다. 반면 목록 페이지는 여러 리프 페이지와 연결되어 있는 카테고리 페이지입니다. 다음은 목록 페이지의 예입니다.
    -   '최고의 칠면조 요리법 10가지'를 설명하며 각 레시피의 링크를 포함한 페이지
    -   캘리포니아 마운틴 뷰의 모든 채용정보가 나열되어 있으며 개별 채용정보 링크를 포함한 페이지
-   **콘텐츠 정책:** 개별 인리치드 검색에는 각 데이터 유형에 관한 추가 콘텐츠별 정책이 있습니다(각 도움말에서 설명됨). 이 콘텐츠 정책을 위반하는 도움말 또는 사이트는 불리한 순위를 책정받거나 기능을 사용하지 못하게 될 수 있습니다.