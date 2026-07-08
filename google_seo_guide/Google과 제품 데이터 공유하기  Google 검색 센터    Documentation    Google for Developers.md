더 관련성이 높은 트래픽을 유도하기 위해 사이트를 더욱 [다채로운 방식으로 노출하고 더 많은 Google 플랫폼에 표시](https://developers.google.com/search/docs/specialty/ecommerce/where-ecommerce-data-can-appear-on-google?hl=ko)하려면 전자상거래 제품 데이터를 Google과 공유하세요. 이러한 이점을 활용하려면 다음 조치를 취하는 것이 좋습니다.

-   **사이트의 제품 페이지에 구조화된 데이터를 포함합니다**. [웹페이지에 구조화된 데이터를 추가](https://developers.google.com/search/docs/specialty/ecommerce/share-your-product-data-with-google?hl=ko#add-structured-data)할 때의 이점을 자세히 알아보세요.
-   [Google 판매자 센터](https://support.google.com/merchants/answer/188924?hl=ko)에 피드를 업로드하여 **Google에 표시하려는 제품을 Google에 직접 알립니다**. Google 판매자 센터는 상거래 데이터를 자세히 파악하고 있는 Google 서비스입니다. [Google 판매자 센터의 이점](https://developers.google.com/search/docs/specialty/ecommerce/share-your-product-data-with-google?hl=ko#upload-product-data)을 자세히 알아보세요.

## 웹페이지에 구조화된 제품 데이터 추가하기

가능하다면 구조화된 데이터를 제품 페이지에 추가하세요. 구조화된 데이터를 Google 검색결과에 표시할 필요는 없지만 이를 통해 Google에서 페이지를 더 잘 파악하여 리치 결과로 표시할 수 있습니다. 예를 들면 다음과 같습니다.

-   구조화된 데이터를 사용하면 [제품 리치 결과](https://developers.google.com/search/docs/appearance/structured-data/product?hl=ko)에 표시될 가능성이 커집니다.
-   구조화된 데이터를 사용하면 페이지에 나와 있는 가격, 할인, 배송비 등 Google이 인식하는 콘텐츠의 정확성을 개선할 수 있습니다. Google 판매자 센터에서 사이트를 대상으로 한 제품 피드 확인의 정확성도 개선될 수 있습니다.

구현할 준비가 되셨나요? 자세한 내용은 [전자상거래와 관련된 구조화된 데이터 포함하기](https://developers.google.com/search/docs/specialty/ecommerce/include-structured-data-relevant-to-ecommerce?hl=ko)를 참고하세요.

Google에서는 페이지에서 데이터를 추출하기 위해 다른 방법을 사용할 수 있습니다. 페이지의 콘텐츠를 사용하여 스니펫을 생성하지 않도록 Google에 명시적으로 알리려면 [`data-nosnippet` 속성](https://developers.google.com/search/docs/crawling-indexing/robots-meta-tag?hl=ko#data-nosnippet-attr)을 HTML 요소에 추가하세요.

## Google 판매자 센터에 데이터 업로드하기

Google 판매자 센터에 제품 데이터를 업로드하는 것이 Google 검색결과에 표시되는 데 필수는 아니지만 Google에서 제품을 더 잘 파악하는 데 도움이 될 수는 있습니다. Google 쇼핑 탭의 목록과 같은 일부 Google 표시 경로에 제품을 표시하려는 경우에는 Google 판매자 센터에 참여해야 합니다.

업데이트 빈도가 적은 소규모 사이트의 경우 크롤링된 웹 콘텐츠에서 [자동 피드를 사용하여 제품 데이터를 빌드](https://support.google.com/merchants/answer/7538732?hl=ko)할 수 있습니다(구조화된 데이터는 데이터 추출의 정확성을 개선하는 데 도움이 될 수 있음). 이는 적은 노력으로 시작하는 데도 유용할 수 있습니다.

대규모 사이트나 콘텐츠가 자주 변경되는 사이트의 경우 주기적으로 Google 판매자 센터에 [새 데이터 피드 파일을 업로드](https://support.google.com/merchants/answer/188477?hl=ko)합니다(또는 즉시 업데이트하려면 [Content API](https://developers.google.com/shopping-content/guides/quickstart?hl=ko) 사용). 이를 통해 Google에서 데이터를 더 세밀하게 관리할 수 있습니다. 피드 파일 업로드의 이점은 다음과 같습니다.

-   **Google에서 사용자의 제품을 모두 알고 있다는 확신이 높아집니다**. 웹 크롤링으로 사이트의 모든 제품을 찾을 것이라는 보장은 없습니다.
-   **업데이트 시기를 더 세밀하게 관리합니다**. Google에서는 사이트의 변경사항이 크롤링을 통해 처리되기까지 걸리는 시간을 정확히 알 수 없습니다. 피드는 원하는 시간에 매주, 매일 또는 매시간 업데이트에 사용할 수 있습니다. Content API를 사용하면 즉시 콘텐츠를 업데이트할 수 있으므로 재고 수준 업데이트에 특히 유용합니다.
-   **웹사이트에 없는 데이터를 공유합니다**. 오프라인 상점 수준 인벤토리 데이터와 같은 일부 정보는 웹사이트에 포함하기에 적절하지 않다고 판단할 수 있습니다. 피드와 Content API를 사용하면 이 데이터를 웹사이트에 표시하지 않고도 Google과 공유할 수 있습니다.

[Google 판매자 센터에 가입](https://support.google.com/merchants/answer/188924?hl=ko)하는 방법을 자세히 알아보세요.

## Google에서 구조화된 데이터와 Google 판매자 센터 데이터를 사용하는 방법

다음은 Google에서 웹페이지에 삽입된 구조화된 데이터와 다양한 환경을 위한 Google 판매자 센터 데이터를 사용하는 방법을 보여주는 예입니다. 환경은 국가, 기기, 기타 요소에 따라 다를 수 있습니다.

| 환경 | 구조화된 데이터 | Google 판매자 센터 |
|----------------------------|--------------------------------------------------------------|------------------------------------------------------------|
| **Google 검색의 제품 리치 결과** | Google 검색에서는 [구조화된 제품 데이터](https://developers.google.com/search/docs/appearance/structured-data/product?hl=ko)를 사용하여 제품 리치 결과를 표시합니다. | Google 검색에서는 Google 판매자 센터 데이터를 사용하여 제품 리치 결과를 표시할 수 있습니다. |
| **제품 주석이 포함된 Google 이미지 검색결과** | Google 이미지에서는 [구조화된 제품 데이터](https://developers.google.com/search/docs/appearance/structured-data/product?hl=ko)를 사용하여 이미지에 제품 주석을 표시합니다. | Google 이미지에서는 Google 판매자 센터에 등록된 이미지를 사용합니다. |
| **Google 쇼핑 탭** | 구조화된 데이터를 추가하면 때때로(예: 데이터 확인 중) Google 판매자 센터에 도움이 될 수 있습니다. | Google 쇼핑 탭에 표시되려면 Google 판매자 센터에 참여해야 합니다. |
| **Google 렌즈 이미지 검색결과** | Google 렌즈에서는 가능한 경우 [구조화된 이미지 데이터 속성](https://developers.google.com/search/docs/appearance/structured-data/sd-policies?hl=ko#images)을 사용합니다. | Google 이미지에서는 Google 판매자 센터에 등록된 이미지를 사용합니다. |

## 업데이트 지연 문제 해결하기

Google에서 웹사이트와 Google 판매자 센터 피드의 데이터를 결합할 때 지연으로 인해 데이터 불일치 문제가 발생할 수 있습니다. 예를 들어 제품이 매진되면 웹사이트에서는 일반적으로 구매 불가로 표시하지만, 특히 피드를 사용하고 있다면 Google 판매자 센터는 일정 시간이 지날 때까지 업데이트되지 않을 수 있습니다.

이러한 가격 및 재고 데이터의 잠재적 충돌(동기화 문제의 일반적인 원인)을 방지하려면 이러한 불일치가 발견될 때 웹사이트 콘텐츠를 기반으로 [제품 데이터 사본을 자동으로 업데이트](https://support.google.com/merchants/answer/3246284?hl=ko)하도록 Google 판매자 센터에 알립니다.

Googlebot과 Google 판매자 센터가 함께 작동하는 방식을 자세히 알아보려면 검색 센터 라이트닝 토크 시리즈의 [제품을 Google 검색에 표시하는 방법](https://www.youtube.com/watch?v=UQtdv_hoGuM&hl=ko)을 참고하세요.

<iframe frameborder="0" allowfullscreen="" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share" referrerpolicy="strict-origin-when-cross-origin" width="640" height="360" src="https://www.youtube.com/embed/UQtdv_hoGuM?origin=https%3A%2F%2Fdevelopers.google.com&amp;autoplay&amp;controls&amp;embed_domain&amp;enablejsapi=1&amp;end&amp;hl&amp;showinfo&amp;start&amp;video-id=UQtdv_hoGuM&amp;widgetid=123&amp;forigin=https%3A%2F%2Fdevelopers.google.com%2Fsearch%2Fdocs%2Fspecialty%2Fecommerce%2Fshare-your-product-data-with-google%3Fhl%3Dko&amp;aoriginsup=1&amp;gporigin=https%3A%2F%2Fdevelopers.google.com%2Fsearch%2Fdocs%2Fcrawling-indexing%2Famp%2Fabout-amp%3Fhl%3Dko&amp;vf=1" id="widget124" data-title="YouTube video player"></iframe>