속성 탐색은 방문자가 페이지에 항목(예: 제품, 기사, 이벤트)이 표시되는 방식을 변경할 수 있도록 허용하는 웹사이트의 일반적인 기능입니다. 이 기능은 인기가 많고 유용하지만 URL 매개변수를 기반으로 하는 가장 일반적인 구현은 무한한 URL 공간을 생성하여 다음과 같은 여러 가지 방법으로 웹사이트에 해를 끼칠 수 있습니다.

-   **과도한 크롤링**: 속성 탐색을 위해 생성된 URL은 새로운 것처럼 보이며 크롤러는 먼저 크롤링하지 않고는 URL이 유용할지 여부를 판단할 수 없으므로 크롤러의 프로세스가 URL이 실제로는 쓸모없다고 판단하기 전에 크롤러는 일반적으로 매우 많은 수의 속성 탐색 URL에 액세스합니다.
-   **느린 탐색 크롤링**: 이전 사항에서 알 수 있듯이 크롤링이 쓸모없는 URL에 사용되면 크롤러가 유용한 새 URL에 소비할 시간이 줄어듭니다.

일반적인 속성 탐색 URL에는 필터링하는 항목의 속성과 관련된 다양한 매개변수가 쿼리 문자열에 포함될 수 있습니다. 예를 들면 다음과 같습니다.

```
https://example.com/items.shtm?products=fish&color=radioactive_green&size=tiny
```

URL 매개변수 `products`, `color`, `size` 중 하나를 변경하면 기본 페이지에 다른 항목 모음이 표시됩니다. 이는 필터의 가능한 조합이 매우 많다는 것을 의미하며, 이는 가능한 URL이 매우 많다는 뜻입니다. 리소스를 절약하려면 다음 방법 중 하나로 이러한 URL을 처리하는 것이 좋습니다.

-   색인이 생성될 수 있는 속성 탐색 URL이 필요하지 않은 경우 이러한 URL의 크롤링을 방지합니다.
-   색인이 생성될 수 있는 속성 탐색 URL이 필요한 경우 URL이 다음 섹션에 설명된 권장사항을 준수하는지 확인합니다. 속성 URL을 크롤링하면 페이지를 렌더링하는 데 필요한 URL과 작업의 양이 많아 사이트에 많은 컴퓨팅 리소스가 소요될 수 있습니다.

## 속성 탐색 URL 크롤링 방지하기

서버 리소스를 절약하고 Google 검색 또는 다른 Google 제품에 속성 탐색 URL이 표시되지 않도록 하려면 다음 방법 중 하나를 사용하여 이러한 URL의 크롤링을 방지할 수 있습니다.

-   **[robots.txt](https://developers.google.com/crawling/docs/robots-txt/create-robots-txt?hl=ko)를 사용하여 속성 탐색 URL의 크롤링을 허용하지 않습니다.** 필터링된 항목의 크롤링을 허용할 만한 타당한 이유가 없는 경우가 많습니다. 필터링된 항목을 크롤링하면 서버 리소스가 소모되지만 이로 인한 이익은 거의 또는 전혀 없기 때문입니다. 대신 필터가 적용되지 않은 모든 제품을 표시하는 전용 등록정보 페이지와 함께 개별 항목 페이지만 크롤링하도록 허용합니다.```makefile
    user-agent: Googlebot
    disallow: /*?*products=
    disallow: /*?*color=
    disallow: /*?*size=
    allow: /*?products=all$
    ```
    
-   **URL 프래그먼트를 사용하여 필터 지정** 필터링 메커니즘이 URL 프래그먼트를 기반으로 하는 경우 크롤링에 (긍정적이든 부정적이든) 영향을 미치지 않습니다. 예를 들어 URL 매개변수 대신 URL 프래그먼트를 사용합니다.
    
    ```perl
    https://example.com/items.shtm#products=fish&color=radioactive_green&size=tiny
    ```
    

크롤링할 속성 탐색 URL(또는 크롤링하지 않을 URL)의 환경설정을 알리는 다른 방법은 `rel="canonical"` `link` 요소와 `rel="nofollow"` 앵커 속성을 사용하는 것입니다. 하지만 이러한 방법은 일반적으로 앞에서 언급한 방법보다 장기적으로 효과가 떨어집니다.

-   **[`rel="canonical"`](https://developers.google.com/search/docs/crawling-indexing/consolidate-duplicate-urls?hl=ko#rel-canonical-link-method)을 사용하여 속성 탐색 URL의 표준 버전이 되는 URL을 지정**하면 시간이 지남에 따라 이러한 URL의 비표준 버전의 크롤링 수가 줄어들 수 있습니다. 예를 들어 필터링된 페이지 유형이 3개인 경우 `rel="canonical"`을 필터링되지 않은 버전으로 가리키는 것이 좋습니다. `https://example.com/items.shtm?products=fish&color=radioactive_green&size=tiny`는 `<link rel="canonical" href="https://example.com/items.shtm?products=fish" >`를 지정합니다.
-   **필터링된 결과 페이지를 가리키는 앵커에 [`rel="nofollow"`](https://developers.google.com/search/docs/crawling-indexing/qualify-outbound-links?hl=ko#nofollow) 속성을 사용**하면 도움이 될 수 있지만, 효과를 내려면 특정 URL을 가리키는 모든 앵커에 `rel="nofollow"` 속성이 있어야 합니다.

## 속성 탐색 URL이 웹에 최적의 선택인지 확인하기

속성 탐색 URL을 크롤링하고 색인 생성할 수 있어야 하는 경우 사이트에서 잠재적인 URL을 다량 크롤링할 때 발생하는 부정적인 영향을 최소화하기 위해 다음 권장사항을 따르세요.

1.  **업계 표준 URL 매개변수 구분자 '`&`'을 사용합니다.** 쉼표(`,`), 세미콜론(`;`), 대괄호(`[` 및 `]`)와 같은 문자는 크롤러가 매개변수 구분자로 감지하기가 어렵습니다. 대부분의 경우 구분자가 아니기 때문입니다.
2.  URL 경로에 필터를 인코딩하는 경우(예: `/products/**fish**/**green**/**tiny**`) 필터의 논리적 순서가 항상 동일하게 유지되고 중복 필터가 존재할 수 없는지 확인합니다.
3.  **필터 조합이 결과를 반환하지 않는 경우 HTTP `404` 상태 코드를 반환합니다.** 사이트 인벤토리에 녹색 물고기가 없는 경우 사용자와 크롤러 모두 적절한 HTTP 상태 코드(`404`)와 함께 '찾을 수 없음' 오류를 수신해야 합니다. URL에 중복 필터 또는 다른 의미 없는 필터 조합이 포함되어 있거나 페이지로 나누기 URL이 없는 경우에도 마찬가지입니다. 마찬가지로 필터 조합에 결과가 없는 경우 일반적인 '찾을 수 없음' 오류 페이지로 리디렉션하지 마세요. 대신 오류가 발생한 URL 아래에 `404` HTTP 상태 코드와 함께 'not found' 오류를 표시합니다.