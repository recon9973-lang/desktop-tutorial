## 구조화된 `Product` 데이터 소개

제품 페이지에 구조화된 데이터를 추가하면 Google 검색 결과에서 더욱 풍부한 방식으로 제품 정보를 표시할 수 있습니다(예: [Google 이미지](https://images.google.com/?hl=ko) 및 [Google 렌즈](https://lens.google/?hl=ko)). 예를 들어 사용자가 검색 결과에서 가격, 재고, 리뷰 평점, 배송 정보 등을 즉시 확인할 수 있습니다.

## 어떤 마크업을 사용할지 결정하기

구조화된 제품 데이터에는 두 가지 기본 클래스가 있습니다. 사용 사례에 가장 적합한 유형에 해당하는 요구사항을 따르세요.

-   **[제품 스니펫](https://developers.google.com/search/docs/appearance/structured-data/product-snippet?hl=ko)**: 사용자가 제품을 직접 구매할 수 없는 제품 페이지입니다. 이 마크업에는 광고소재 제품 리뷰 페이지의 [장단점](https://developers.google.com/search/docs/appearance/structured-data/product-snippet?hl=ko#pros-cons-example)과 같이 리뷰 정보를 지정할 수 있는 추가 옵션이 있습니다.
-   **[판매자 등록정보](https://developers.google.com/search/docs/appearance/structured-data/merchant-listing?hl=ko)**: 고객이 제품을 구매할 수 있는 페이지에 사용합니다. 이 마크업에는 [의류 사이즈](https://developers.google.com/search/docs/appearance/structured-data/merchant-listing?hl=ko#size-specification-properties), [배송 세부정보](https://developers.google.com/search/docs/appearance/structured-data/merchant-listing?hl=ko#shipping), [반품 정책](https://developers.google.com/search/docs/appearance/structured-data/merchant-listing?hl=ko#returns) 정보 등 자세한 제품 정보를 지정할 수 있는 추가 옵션이 있습니다.

두 제품 기능 사이에는 일부 중복되는 부분이 있습니다. 일반적으로 판매자 등록정보에 [필수 제품 정보 속성](https://developers.google.com/search/docs/appearance/structured-data/merchant-listing?hl=ko#product-information)을 추가하면 제품 페이지에도 제품 스니펫을 사용할 수 있습니다. 두 기능에 모두 자체적으로 개선된 기능이 있으므로 사이트의 컨텍스트에 적합한 마크업을 결정할 때 두 가지 모두 검토해야 합니다. 추가할 수 있는 속성이 많을수록 페이지에서 더 많은 개선사항을 적용할 수 있습니다.

판매하는 개별 제품의 구조화된 데이터 외에도 `Organization` 마크업 아래에 중첩된 전자상거래 비즈니스의 정책을 정의하는 구조화된 데이터를 추가하는 것이 좋습니다.

-   **[판매자 반품 정책](https://developers.google.com/search/docs/appearance/structured-data/return-policy?hl=ko)**: 비즈니스의 반품 정책을 지정합니다.
-   **[포인트 제도](https://developers.google.com/search/docs/appearance/structured-data/loyalty-program?hl=ko)**: 제공하는 포인트 제도를 지정합니다.

이 페이지에서는 Google 검색 결과에 쇼핑 환경이 표시되는 방식을 설명합니다. 이 목록은 모든 항목을 포함하지는 않습니다. Google 검색에서는 사용자가 원하는 정보를 찾을 수 있도록 새롭고 개선된 방법을 지속적으로 모색하고 있기 때문에 시간이 지남에 따라 사용 환경이 바뀔 수 있습니다.

| ##### 제품 스니펫

평점, 리뷰 정보, 가격, 재고 등 추가 제품 정보가 포함된 [텍스트 결과](https://developers.google.com/search/docs/appearance/visual-elements-gallery?hl=ko#text-result) | ![검색결과에 표시된 제품 스니펫 프레젠테이션](https://developers.google.com/static/search/docs/images/product-snippet.png?hl=ko) |
|--------------------------------------------------------------|-------------------------|
| ##### 인기 제품

시각적으로 아름답게 표현된 판매용 제품 | ![검색결과에 표시된 인기 제품](https://developers.google.com/static/search/docs/images/popular-products.png?hl=ko) |
| ##### 쇼핑 지식 패널

판매자 목록과 함께 자세한 제품 정보를 표시(제품 식별자와 같은 세부정보 사용) | ![검색결과에 표시되는 쇼핑 지식 패널](https://developers.google.com/static/search/docs/images/shopping-knowledge-panel.png?hl=ko) |
| ##### Google 이미지

판매 가능한 제품의 이미지(주석 포함) | ![검색결과에 표시되는 Google 이미지](https://developers.google.com/static/search/docs/images/google-images.png?hl=ko) |

### 검색결과 개선하기

검색 결과 개선사항은 각 사용 환경의 상황에 따라 표시되며 시간이 지남에 따라 변경될 수 있습니다. 따라서 제품 정보를 사용할 실제 환경이 무엇이냐와 관계없이 가능한 한 많은 제품 정보를 제공하는 것이 좋습니다. 다음은 제품 리치 결과를 개선하는 몇 가지 방법입니다.

-   **평점**: [고객 리뷰 및 평점](https://developers.google.com/search/docs/appearance/structured-data/product-snippet?hl=ko#product-reviews)을 통해 검색 결과에 표시되는 모습을 개선합니다.
-   **장단점**: 제품 리뷰 설명에서 [장단점](https://developers.google.com/search/docs/appearance/structured-data/product-snippet?hl=ko#pros-cons)을 파악하여 검색결과에서 강조 표시할 수 있습니다.
-   **배송**: [배송비](https://developers.google.com/search/docs/appearance/structured-data/merchant-listing?hl=ko#shipping), 특히 무료 배송 혜택의 제공 여부를 공유하면 쇼핑객이 총비용을 파악할 수 있습니다.
-   **재고**: 현재 제품 [재고 여부](https://developers.google.com/search/docs/appearance/structured-data/merchant-listing?hl=ko#availability)를 고객에게 알릴 수 있도록 재고 데이터를 제공합니다.
-   **가격 인하**: Google에서 시간 경과에 따른 제품 가격 변동을 관찰하여 가격 인하를 계산합니다. 가격 인하가 표시된다고 보장할 수는 없습니다.
-   **반품**: 반품 정책, 반품 관련 수수료, 반품 기간 등의 [반품 정보](https://developers.google.com/search/docs/appearance/structured-data/merchant-listing?hl=ko#returns)를 공유합니다.

## Google 검색에 제품 데이터 제공하기

Google 검색에 풍부한 제품 데이터를 제공하려면 구조화된 `Product` 데이터를 웹페이지에 추가할 수도 있고, Google 판매자 센터를 통해 데이터 피드를 업로드하고 판매자 센터 콘솔에서 무료 등록정보를 선택할 수도 있고, 둘 다 할 수도 있습니다. Google 검색 센터 문서에서는 웹페이지에 있는 구조화된 데이터에 중점을 둡니다.

웹페이지의 구조화된 데이터와 판매자 센터 피드를 둘 다 제공하면 실험 환경을 사용할 수 있는 자격이 극대화되며 Google에서 데이터를 정확하게 이해하고 확인하는 데 도움이 됩니다. 일부 환경에서는 구조화된 데이터와 Google 판매자 센터 피드가 둘 다 제공된 경우 이 두 데이터를 결합하여 사용합니다. 예를 들어 가격 데이터가 페이지의 구조화된 데이터에 없는 경우 제품 스니펫에서 판매자 피드의 가격 데이터를 사용할 수 있습니다. [Google 판매자 센터 피드 문서](https://support.google.com/merchants/answer/7052112?hl=ko)에 피드 속성에 관한 추가 권장사항 및 요구사항이 포함되어 있습니다.

Google 검색 외에도 [Google 판매자 센터의 데이터 및 자격요건](https://support.google.com/merchants/answer/9199328?hl=ko)을 참고하여 [Google 쇼핑 탭](https://support.google.com/merchants/answer/9826670?hl=ko) 자격요건에 관해 자세히 알아보세요.