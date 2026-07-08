검색결과 하위 집합을 표시하여 사용자 경험을 개선함으로써 페이지 성능을 높일 수 있습니다. 하지만 Google 크롤러가 모든 사이트 콘텐츠를 찾을 수 있도록 하려면 몇 가지 조치를 취해야 할 수 있습니다.

예를 들어 전자상거래 사이트 검색창을 사용하는 사용자에게 판매 제품의 하위 집합을 표시할 수 있습니다. 이때 일치하는 검색결과의 전체 항목이 너무 많으면 한 웹페이지에 표시할 수 없거나 가져오는 데 시간이 너무 오래 걸릴 수 있습니다.

검색결과 외에도 다음과 관련해 전자상거래 사이트에 일부 결과를 로드할 수 있습니다.

-   한 카테고리의 모든 제품이 표시되는 카테고리 페이지
-   시간이 지나면서 사이트에 게시된 블로그 게시물 또는 뉴스레터 제목
-   제품 페이지의 사용자 리뷰
-   블로그 게시물의 댓글

사용자 작업에 따라 사이트에서 콘텐츠를 점진적으로 로드하면 사용자에게 다음과 같은 이점을 제공할 수 있습니다.

-   모든 검색결과를 한 번에 로드할 때보다 초기 페이지 로드 속도가 빠르기 때문에 사용자 경험이 개선됩니다.
-   네트워크 트래픽이 줄어듭니다. 이는 휴대기기에 특히 중요합니다.
-   데이터베이스나 이와 유사한 항목에서 검색되는 콘텐츠 볼륨을 줄여 백엔드 성능이 개선됩니다.
-   목록이 지나치게 길어지는 것을 방지하므로 안정성이 개선됩니다. 목록이 지나치게 길면 리소스 제한에 도달해 브라우저와 백엔드 시스템에 오류가 발생할 수 있습니다.

## 사이트에 가장 적합한 UX 패턴 선택

대규모 목록의 하위 집합을 표시하려면 다양한 UX 패턴 중에서 선택하면 됩니다.

-   **페이지로 나누기**: 사용자가 '다음', '이전', 페이지 번호와 같은 링크를 사용하여 페이지 간에 이동할 수 있습니다. 이때 검색결과가 한 번에 한 페이지씩 표시됩니다.
-   **더 로드하기**: 사용자가 이 버튼을 클릭하여 처음에 표시된 검색결과 집합을 펼칠 수 있습니다.
-   **무한 스크롤**: 사용자가 페이지의 끝까지 스크롤하면 더 많은 콘텐츠가 로드됩니다. [무한 스크롤 검색 친화적인 권장사항](https://developers.google.com/search/docs/crawling-indexing/javascript/lazy-loading?hl=ko#paginated-infinite-scroll)에 관해 자세히 알아보세요.

![휴대기기의 일반적인 페이지로 나누기, 더 로드하기, 무한 스크롤 패턴](https://developers.google.com/static/search/docs/images/ecom-pagination-load-more-infinite-scroll.png?hl=ko)

다음 표를 참고하여 사이트에 가장 적합한 사용자 환경을 선택하세요.

| UX 패턴 | UX 패턴 |
|----------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| 페이지로 나누기 | **장점:**

-   사용자에게 검색결과의 크기 및 현재 위치와 관련된 유용한 정보 제공

**단점:**

-   사용자가 검색결과 간에 이동하는 데 사용하는 제어 방식이 다소 복잡함
-   콘텐츠가 하나의 연속 목록 형태가 아니라 여러 페이지에 걸쳐 나뉨
-   항목을 더 보려면 새로 페이지를 로드해야 함 |
| 더 로드하기 | **장점:**

-   단일 페이지에 모든 콘텐츠 포함
-   사용자에게 검색결과의 총 크기를 알릴 수 있음(버튼 위나 근처에 있음)

**단점:**

-   모든 검색결과가 단일 웹페이지에 포함되므로 검색결과가 아주 많은 경우 처리할 수 없음 |
| 무한 스크롤 | **장점:**

-   단일 페이지에 모든 콘텐츠 포함
-   직관적: 사용자가 콘텐츠를 더 보려면 계속 스크롤하면 됨

**단점:**

-   검색결과의 크기가 명확하지 않아 '스크롤하는 데 피로감'이 발생할 수 있음
-   검색결과가 아주 많은 경우 처리할 수 없음 |

## Google의 전략별 색인 생성 방법

사이트와 검색엔진 최적화에 가장 적합한 UX 전략을 선택했으면 Google 크롤러가 모든 콘텐츠를 찾을 수 있는지 확인합니다.

예를 들어 전자상거래 사이트의 새 페이지로 연결되는 링크를 사용하거나 현재 페이지를 업데이트하는 자바스크립트를 사용하여 페이지로 나누기를 구현할 수 있습니다. '더 로드하기'와 무한 스크롤은 일반적으로 JavaScript를 사용하여 구현됩니다. Google은 색인을 생성할 페이지를 찾기 위해 사이트를 크롤링할 때 일반적으로 `<a>` 요소의 `href` 속성에 있는 URL을 크롤링합니다. Google 크롤러는 버튼을 '클릭'하지 않으며 일반적으로 현재 페이지 콘텐츠를 업데이트하는 데 사용자 작업이 필요한 JavaScript 함수를 트리거하지 않습니다.

사이트에 자바스크립트를 사용한다면 [자바스크립트 검색엔진 최적화 권장사항](https://developers.google.com/search/docs/crawling-indexing/javascript/javascript-seo-basics?hl=ko)을 따르세요. 사이트에 있는 링크를 크롤링 가능하도록 만드는 등의 권장사항을 따르는 일 외에도 [사이트맵](https://developers.google.com/search/docs/crawling-indexing/sitemaps/build-sitemap?hl=ko) 파일 또는 [Google 판매자 센터 피드](https://support.google.com/merchants/answer/7439058?hl=ko)를 사용해 보세요. Google이 사이트에 있는 모든 제품을 찾는 데 도움이 됩니다.

Google에서 페이지로 나눈 콘텐츠를 크롤링하고 색인을 생성할 수 있도록 하려면 다음 권장사항을 따르세요.

-   [순차적으로 페이지 연결](https://developers.google.com/search/docs/specialty/ecommerce/pagination-and-incremental-page-loading?hl=ko#sequentially)
-   [올바른 URL 사용](https://developers.google.com/search/docs/specialty/ecommerce/pagination-and-incremental-page-loading?hl=ko#use-urls-correctly)
-   [필터 또는 다른 정렬 순서가 사용된 URL의 색인 생성 방지](https://developers.google.com/search/docs/specialty/ecommerce/pagination-and-incremental-page-loading?hl=ko#avoid-indexing-variations)

### 순차적으로 페이지 연결

검색엔진이 페이지로 나눈 콘텐츠의 페이지 간 관계를 이해하도록 하려면 `<a href>` 태그를 사용하여 각 페이지를 다음 페이지에 연결하는 링크를 포함하세요. 그러면 Googlebot(Google 웹 크롤러)이 다음 페이지를 쉽게 찾을 수 있습니다.

![페이지로 나눈 검색결과의 예](https://developers.google.com/static/search/docs/images/ecom-paginated-results.png?hl=ko)

또한 컬렉션의 모든 개별 페이지를 컬렉션의 첫 페이지로 다시 연결하여 컬렉션의 시작 부분을 Google에 강조하는 것이 좋습니다. 그렇게 하면 컬렉션의 첫 번째 페이지가 컬렉션의 다른 페이지보다 방문 페이지로 더 적합하다는 점을 Google에 알릴 수 있습니다.

### 올바른 URL 사용

-   **각 페이지에 고유한 URL을 지정합니다**. 예를 들어 페이지로 나누기 순서의 URL은 Google에서 별도의 페이지로 취급되므로 `?page=n` 쿼리 매개변수를 포함하세요.
-   **페이지로 나누기 순서의 첫 페이지는 표준 페이지로 사용하지 않습니다**. 대신 각 페이지에 고유한 [표준 URL](https://developers.google.com/search/docs/crawling-indexing/consolidate-duplicate-urls?hl=ko)을 지정하세요.
-   **컬렉션의 페이지 번호에 URL 프래그먼트 식별자(URL에서 `#` 뒤에 오는 텍스트)를 사용하지 않습니다**. Google에서는 프래그먼트 식별자를 무시합니다. Googlebot이 다음 페이지의 URL에서 `#` 뒤에 오는 텍스트만 다르다고 판단하면 이미 그 페이지를 검색했다고 간주하여 링크를 따라가지 않을 수 있습니다.
-   다음 페이지로 이동하는 사용자를 위해 **[미리 로드, 사전 연결, 미리 가져오기](https://web.dev/learn/performance/resource-hints?hl=ko)**를 사용하여 성능을 최적화하는 것이 좋습니다.

### 필터 또는 다른 정렬 순서가 사용된 URL의 색인 생성 방지

사이트에서 검색결과의 목록이 길 때 필터나 다양한 정렬 순서를 지원하도록 선택할 수 있습니다. 예를 들어 URL에 `?order=price`를 지원하여 동일한 검색결과 목록을 가격순으로 정렬하여 반환할 수 있습니다.

동일한 검색결과 목록의 색인 변형이 생성되지 않도록 하려면 [`noindex` robots `meta` 태그](https://developers.google.com/search/docs/crawling-indexing/block-indexing?hl=ko)로 원치 않는 URL의 색인이 생성되지 않도록 차단하거나 [robots.txt 파일로 특정 URL 패턴](https://developers.google.com/search/docs/crawling-indexing/robots/robots_txt?hl=ko#url-matching-based-on-path-values)이 크롤링되지 않도록 합니다.