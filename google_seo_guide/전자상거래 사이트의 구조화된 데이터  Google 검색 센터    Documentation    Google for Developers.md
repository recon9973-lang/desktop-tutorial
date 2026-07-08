## 전자상거래와 관련된 구조화된 데이터 포함하기

Google은 다른 웹사이트에서와 마찬가지로 전자상거래 웹사이트를 [크롤링하고 색인을 생성](https://developers.google.com/search/docs/fundamentals/how-search-works?hl=ko)하며, 콘텐츠와 용도를 파악하기 위해 알고리즘을 적용합니다. 구조화된 데이터는 페이지에 관한 정보를 제공하고 컴퓨터가 인식할 수 있는 표준화된 형식입니다. 이를 통해 Google은 콘텐츠를 더 정확하게 파악할 수 있습니다.

구조화된 데이터는 대개 전자상거래와 관련이 없지만, 일부 구조화된 데이터 유형의 경우 전자상거래와 관련이 있습니다. 다음 리소스는 전자상거래 웹사이트의 구조화된 데이터를 자세히 알아보는 데 유용합니다.

-   Google에서 구조화된 데이터를 사용하는 방법에 관한 소개는 [구조화된 데이터 작동 방식 이해](https://developers.google.com/search/docs/guides/intro-structured-data?hl=ko)를 참고하세요.
-   전자상거래 웹사이트의 구조화된 데이터(스키마 마크업이라고도 함)의 범위를 자세히 알아보려면 [schema.org](https://schema.org/)를 참고하세요. Google에서는 schema.org에서 정의한 구조화된 데이터 유형 중 상당 부분을 지원하지만 모두를 지원하지는 않습니다.

다음은 전자상거래 웹사이트와 특히 관련이 있는 구조화된 데이터 유형입니다. 쇼핑객이 각자의 쇼핑 여정에서 서로 다른 단계에 있으며 제품 페이지 외에 더 많은 것을 찾고 있을 수 있다는 점에 유의해야 합니다.

| 전자상거래의 구조화된 데이터 유형 | 전자상거래의 구조화된 데이터 유형 |
|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|------------------------------|
| #### [`BreadcrumbList`](https://developers.google.com/search/docs/appearance/structured-data/breadcrumb?hl=ko)

Google에서 사이트의 페이지 계층 구조를 이해할 수 있도록 하려면 [탐색경로 마크업 문서](https://developers.google.com/search/docs/appearance/structured-data/breadcrumb?hl=ko)를 참고하세요. Google에서 검색결과에 더 의미 있는 탐색경로를 표시할 수 있습니다. | ![구조화된 데이터를 사용하는 탐색경로 목록의 예](https://developers.google.com/static/search/docs/images/breadcrumb.png?hl=ko) |
| #### [`LocalBusiness`](https://developers.google.com/search/docs/appearance/structured-data/local-business?hl=ko)

오프라인 상점이 있는 경우 구조화된 [`LocalBusiness`](https://developers.google.com/search/docs/appearance/structured-data/local-business?hl=ko) 데이터를 사용하여 상점 위치, 영업시간 등 비즈니스 정보 페이지에서 비즈니스에 대한 자세한 내용을 Google에 알리세요.

다음 조치를 취하는 것도 좋습니다.

#### [`LocalBusiness`](https://developers.google.com/search/docs/appearance/structured-data/local-business?hl=ko)

-   직접 [Google 마이 비즈니스](https://www.google.com/business/?hl=ko)에 비즈니스를 등록하세요.
-   Google 판매자 센터에 사용할 [오프라인 상점 위치와 판매점 코드](https://support.google.com/business/answer/4542487?hl=ko)를 등록하세요.
-   [판매자 센터 가이드라인](https://support.google.com/merchants/answer/6363310?hl=ko)에서 사이트에 반품 정책을 공유하는 방법 등에 관한 자세한 지침을 확인하세요. | ![구조화된 데이터를 사용하는 지역 비즈니스 정보의 예](https://developers.google.com/static/search/docs/images/local-business01.png?hl=ko) |
| #### [`Organization`](https://developers.google.com/search/docs/appearance/structured-data/organization?hl=ko)

로고, 연락처 정보, 비즈니스 식별자, 비즈니스 전반의 반품 정책 등 전반적인 비즈니스 세부정보를 Google에 자세히 알리려면 구조화된 [`Organization`](https://developers.google.com/search/docs/appearance/structured-data/organization?hl=ko) 데이터 문서를 참조하세요. | ![조직 정보를 보여주는 지식 패널 그림](https://developers.google.com/static/search/docs/images/organization.png?hl=ko) |
| #### [`Product`](https://developers.google.com/search/docs/appearance/structured-data/product?hl=ko) 및 [`ProductGroup`](https://developers.google.com/search/docs/appearance/structured-data/product-variants?hl=ko)

제품에 관한 자세한 내용을 Google에 알리려면 [구조화된 `Product` 데이터 문서](https://developers.google.com/search/docs/appearance/structured-data/product?hl=ko) 및 [제품 옵션](https://developers.google.com/search/docs/appearance/structured-data/product-variants?hl=ko)(해당하는 경우)을 참조하세요. Google 플랫폼에서의 쇼핑 관련 경험 참여를 개선하려면 Google 판매자 센터 문서에서 [판매자 센터의 구조화된 데이터 설정](https://support.google.com/merchants/answer/7331077?hl=ko)도 확인해 보세요. | ![검색 결과에 표시된 쇼핑 지식 패널](https://developers.google.com/static/search/docs/images/shopping-knowledge-panel.png?hl=ko) |
| #### [`Review`](https://developers.google.com/search/docs/appearance/structured-data/review-snippet?hl=ko)

Google이 사이트의 제품 리뷰와 함께 리뷰가 적절한지 손쉽게 파악할 수 있도록 하려면 [리뷰 스니펫](https://developers.google.com/search/docs/appearance/structured-data/review-snippet?hl=ko)을 참고하세요. | ![검색결과에 표시된 리뷰 스니펫의 예](https://developers.google.com/static/search/docs/images/reviews04.png?hl=ko) |
| #### [`VideoObject`](https://developers.google.com/search/docs/appearance/structured-data/video?hl=ko)

웹사이트에 주로 개별 동영상에 관한 페이지가 포함되어 있는 경우 사전 녹화된 동영상(예: 제품 페이지) 또는 라이브 스트림 이벤트를 적절하게 마크업하면 Google에서 동영상을 Google 검색결과에 적절하게 표시하는 데 도움이 됩니다. 자세한 내용은 [동영상 스키마 마크업 문서](https://developers.google.com/search/docs/appearance/structured-data/video?hl=ko) 를 참조하세요. | ![구조화된 데이터를 사용하는 동영상 목록의 예](https://developers.google.com/static/search/docs/images/video-on-google.png?hl=ko) |