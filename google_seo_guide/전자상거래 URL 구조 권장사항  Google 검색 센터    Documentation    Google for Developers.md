잘 설계된 URL을 사용하면 Google이 전자상거래 사이트에서 웹페이지를 더 효율적으로 찾아서 가져올 수 있습니다. URL의 구조를 직접 관리하는 경우(예: 사이트를 처음부터 빌드하는 경우), 이 가이드를 활용하여 Google에서 전자상거래 사이트의 색인 생성 문제가 발생하지 않도록 URL 구조를 결정하세요.

## URL 구조가 중요한 이유

URL 구조를 효과적으로 설계하면 Google이 사이트를 크롤링하고 색인을 생성하는 데 도움이 되는 반면, URL 구조가 좋지 않으면 다음과 같은 문제가 발생할 수 있습니다.

-   **콘텐츠가 누락될 수 있습니다**. 크롤러는 URL 하나만 검색할 수 있으므로(다른 하나는 중복이므로 삭제) Googlebot이 URL 2개가 동일한 콘텐츠를 반환한다고 잘못 판단하는 경우입니다. `#fragment`와 같은 프래그먼트 식별자를 사용하여 다른 콘텐츠를 표시하는 경우에 이렇게 될 수 있습니다. Google은 색인 생성에 프래그먼트 식별자를 사용하지 않습니다.
    
    **예:** Google은 `/product/t-shirt#black` 및 `/product/t-shirt#white`를 동일한 페이지로 간주합니다.
    
-   **크롤러가 동일한 콘텐츠를 여러 번 검색할 수 있습니다**. URL 2개가 서로 다르지만 반환되는 페이지는 동일하다고 Google이 잘못 판단하는 경우입니다. 이로 인해 사이트 크롤링 속도가 느려지고 웹 서버에 불필요한 추가 부하가 발생할 수 있습니다.
    
    **예:** `/product/black-t-shirt`와 `/product?sku=1234`가 동일한 제품 페이지를 반환할 수 있지만, Google은 URL만 보아서는 이를 확인할 수 없습니다.
    
-   **크롤러가 사이트에 포함된 페이지 수가 무한하다고 판단할 수 있습니다**. URL에 계속 변경되는 값(예: 타임스탬프)이 포함된 경우입니다. 그 결과 Google이 사이트에서 유용한 콘텐츠를 모두 찾는 데 시간이 더 걸릴 수 있습니다.
    
    **예:** `/about?now=12:34am`과 `/about?now=12:35am` 모두 동일한 페이지를 표시하지만 Google은 다른 URL로 취급할 수 있습니다.
    

Google이 사이트를 크롤링하고 사이트의 색인을 생성하는 방법에 관한 자세한 내용은 [Google 검색 작동 방식](https://developers.google.com/search/docs/fundamentals/how-search-works?hl=ko) 및 [Google 사이트 크롤러의 사이트 색인 생성 방법](https://www.google.com/search/howsearchworks/crawling-indexing/?hl=ko)을 참고하세요.

## 효과적인 URL 구조 설계 권장사항

Google에서 웹사이트를 크롤링하고 색인을 생성하는 방법을 최적화하려면 URL 구조 설계 방법에 관한 다음 권장사항을 따르세요.

### 일반적인 URL 권장사항

-   동일한 콘텐츠를 반환하는 대체 URL 수를 최소화하여 Google이 사이트에 필요 이상으로 많은 요청을 보내지 않도록 하세요. Google은 두 URL이 모두 검색될 때까지 동일한 페이지가 반환된다는 사실을 인식하지 못할 수 있습니다.
-   URL의 대소문자 텍스트가 웹 서버에서 동일하게 처리되는 경우 모든 텍스트의 대소문자를 동일하게 변환하세요. 그러면 Google에서 URL이 동일한 페이지를 참조한다고 더 쉽게 판단할 수 있습니다.
-   페이지로 나눈 각 검색결과 페이지에 고유한 URL을 사용하세요. 페이지로 나누기 URL 구조에서 URL 오류가 가장 많이 발생합니다.
-   URL 경로에 설명하는 단어를 추가하세요. URL의 단어는 Google이 페이지를 더 잘 이해하는 데 도움이 될 수 있습니다.
    
    **권장**: `/product/black-t-shirt-with-a-white-collar`
    
    **권장하지 않음**: `/product/3243`
    

### URL 쿼리 매개변수 권장사항

Google이 사이트를 정상적으로 크롤링하고 색인을 생성할 수 있도록 쿼리 매개변수를 사용할 때 다음 권장사항을 따르세요.

-   가능하면 URL 매개변수로 `?value` 대신 `?key=value`를 사용하세요. URL 매개변수를 사용하면 Google 검색에서 사이트의 구조를 파악하여 더 효율적으로 크롤링하고 색인을 생성할 수 있습니다.
    
    **권장**: `/photo-frames?page=2`, `/t-shirt?color=green`
    
    **권장하지 않음**: `/photo-frames?2`, `/t-shirt?green`
    
-   같은 매개변수를 두 번 사용하지 않도록 하세요. Googlebot이 매개변수 값 중 하나를 무시할 수도 있습니다.
    
    **권장**: `?type=candy,sweet`
    
    **권장하지 않음**: `?type=candy&type=sweet`
    
-   세션 ID, 추적 코드, 사용자 관련 값(`location=nearby`, `time=last-week`), 현재 시간 같은 임시 매개변수를 내부 링크로 연결하지 마세요. 그러면 수명이 짧은 URL이나 동일한 페이지의 중복 URL이 생성될 수 있습니다. Google 검색에서 최상의 결과를 얻으려면 장기적으로 사용할 수 있는 영구 URL을 사용하세요.
    
    **권장**: `/t-shirt?location=UK`
    
    **권장하지 않음**: `/t-shirt?location=nearby`, `/t-shirt?current-time=12:02`, `/t-shirt?session=123123123`
    

### Google이 제품 옵션의 URL을 이해하는 방법

일반적으로 전자상거래 사이트에서는 제품을 여러 크기 또는 색상으로 제공할 때 URL을 구조화하는 방법을 고려해야 합니다. 각 제품 속성의 조합을 _제품 옵션_이라고 합니다. Google에서 제품 옵션을 이해할 수 있도록 각 옵션을 별도의 URL로 식별할 수 있는지 확인하세요. 옵션 URL에는 다음 URL 구조를 사용하는 것이 좋습니다.

-   경로 세그먼트(예: `/t-shirt/green`)
-   쿼리 매개변수(예: `/t-shirt?color=green`)

자세한 내용은 [구조화된 제품 옵션 데이터 문서](https://developers.google.com/search/docs/appearance/structured-data/product-variants?hl=ko)를 참고하세요.

선택적 쿼리 매개변수를 사용하여 옵션을 식별하는 경우 쿼리 매개변수가 생략된 URL을 [표준 URL](https://developers.google.com/search/docs/crawling-indexing/consolidate-duplicate-urls?hl=ko)로 사용합니다. 이렇게 하면 Google이 제품 옵션 간의 관계를 이해하는 데 도움이 됩니다.

![색상 쿼리 매개변수가 없는 표준 파란색 티셔츠 및 색상 쿼리 매개변수가 지정된 비표준 초록색 티셔츠](https://developers.google.com/static/search/docs/images/ecom-variants-and-canonical.png?hl=ko)

## 콘텐츠에 URL 사용하기

Google 검색 및 Google 쇼핑에서 제품 및 제품 옵션 간의 관계를 제대로 식별하도록 하려면 콘텐츠에 URL을 사용할 때 다음 권장사항을 따르세요.

-   내부 링크, 사이트맵 파일 및 [`<link rel="canonical">` 태그](https://developers.google.com/search/docs/crawling-indexing/consolidate-duplicate-urls?hl=ko)에서 동일한 URL을 사용합니다. 예를 들어 1페이지가 기본 페이지일 때 쿼리 매개변수를 사용하여 페이지로 나뉜 시퀀스의 첫 번째 페이지에 링크로 연결하는 경우, 사이트 전체의 URL에 일관성 있게 `?page=1`을 포함하거나 제외합니다.
-   색인을 생성할 수 있는 모든 페이지에 자체 참조 [`<link rel="canonical">` 태그](https://developers.google.com/search/docs/crawling-indexing/consolidate-duplicate-urls?hl=ko)(태그의 URL이 현재 페이지를 가리킴)를 사용하고 이러한 URL을 [sitemap](https://developers.google.com/search/docs/crawling-indexing/sitemaps/build-sitemap?hl=ko) 파일에 포함합니다.
-   옵션마다 고유한 URL이 있는 제품의 경우 `<link rel="canonical">` 태그를 사용하여 모든 옵션 페이지에 표준 제품 URL을 포함합니다. 자세한 내용은 [Google 판매자 센터의 `canonical_link` 속성](https://support.google.com/merchants/answer/9340054?hl=ko)을 참고하세요.
-   `<a href>` 태그를 사용하여 페이지에 직접 링크를 포함합니다. 자바스크립트를 사용하여 페이지 간에 이동하지 마세요. Googlebot은 자바스크립트 코드에서 이동을 감지하지 못할 수 있습니다. Google에서 자바스크립트를 처리하는 방법을 자세히 알아보려면 [자바스크립트 검색엔진 최적화의 기본사항 이해하기](https://developers.google.com/search/docs/guides/javascript-seo-basics?hl=ko)를 참고하세요.
-   가능하면 `<a href>`와 `</a>` 태그 사이에 의미 있는 텍스트(예: 링크로 연결된 제품의 제목)를 포함합니다. '여기를 클릭하세요'와 같은 일반적인 문구를 사용하지 마세요.
-   유용한 콘텐츠가 없는 페이지에 링크로 연결하지 말고, 최소한 색인은 생성하지 않도록 합니다. 카테고리에 항목이 없으면 [`noindex` robots `meta` 태그](https://developers.google.com/search/docs/crawling-indexing/robots-meta-tag?hl=ko#noindex)를 사용합니다. 사이트에서 비어 있는 카테고리를 감지하고 사이트 내 검색 및 탐색에서 자동으로 해당 카테고리를 삭제하는 경우 페이지의 `404 (not found)` HTTP 상태 코드를 반환하는 것이 좋습니다.