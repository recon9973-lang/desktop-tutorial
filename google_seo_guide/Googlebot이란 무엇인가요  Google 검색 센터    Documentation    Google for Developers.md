Googlebot은 Google 검색에서 사용하는 두 가지 유형의 [웹 크롤러](https://developers.google.com/search/docs/fundamentals/how-search-works?hl=ko)의 일반적인 이름입니다.

-   [**Googlebot 스마트폰**](https://developers.google.com/search/docs/crawling-indexing/google-common-crawlers?hl=ko#googlebot-smartphone): 휴대기기 사용자를 시뮬레이션하는 모바일 크롤러입니다.
-   [**Googlebot 데스크톱**](https://developers.google.com/search/docs/crawling-indexing/google-common-crawlers?hl=ko#googlebot-desktop): 데스크톱 사용자를 시뮬레이션하는 데스크톱 크롤러입니다.

요청의 [HTTP `user-agent` 요청 헤더](https://developers.google.com/search/docs/crawling-indexing/overview-google-crawlers?hl=ko)를 통해 Googlebot의 하위 유형을 확인할 수 있지만, 크롤러 유형은 robots.txt에 있는 동일한 제품 토큰(사용자 에이전트 토큰)을 따르므로 robots.txt를 사용하여 Googlebot 스마트폰 또는 Googlebot 데스크톱 중 하나를 선택적으로 타겟팅할 수는 없습니다.

대부분의 사이트에서 Google 검색은 주로 [모바일 버전 콘텐츠의 색인을 생성](https://developers.google.com/search/docs/crawling-indexing/mobile/mobile-sites-mobile-first-indexing?hl=ko)합니다. 따라서 대부분의 Googlebot 크롤링 요청에 모바일 크롤러가 사용되며 그 외 소수의 요청에 데스크톱 크롤러가 사용됩니다.

## Googlebot이 사이트에 액세스하는 방법

대부분의 경우 Googlebot은 평균적으로 몇 초에 한 번 정도만 사이트에 액세스합니다. 하지만 지연으로 인해 단기적으로 빈도가 약간 높아질 수도 있습니다. 사이트에서 Google의 크롤링 요청 속도를 맞추는 데 문제가 있는 경우 [크롤링 속도를 낮출](https://developers.google.com/search/docs/crawling-indexing/reduce-crawl-rate?hl=ko) 수 있습니다.

Google 검색을 위해 크롤링할 때 Googlebot은 [지원되는 파일 형식](https://developers.google.com/search/docs/crawling-indexing/indexable-file-types?hl=ko)의 처음 2MB와 PDF 파일의 처음 64MB를 크롤링합니다. 렌더링 관점에서 HTML에서 참조되는 각 리소스(예: CSS 및 JavaScript)는 개별적으로 가져오며 각 리소스 가져오기는 PDF 파일을 제외한 다른 파일에 적용되는 동일한 파일 크기 제한을 따릅니다.  
차단 한도에 도달하면 Googlebot은 가져오기를 중지하고 이미 다운로드된 파일 부분만 색인 생성을 위해 전송합니다. 파일 크기 한도는 압축되지 않은 데이터에 적용됩니다. Googlebot 동영상 및 Googlebot 이미지 등 다른 Google 크롤러의 한도는 [다를](https://developers.google.com/crawling/docs/crawlers-fetchers/overview-google-crawlers?hl=ko#file-size-limits) 수도 있습니다.

미국의 IP 주소를 통해 크롤링할 때 Googlebot의 시간대는 [태평양 표준시](https://g.co/kgs/WSf8oR)입니다.

[Googlebot의 기타 기술 속성](https://developers.google.com/search/docs/crawling-indexing/overview-google-crawlers?hl=ko#crawl-technical-props)은 Google 크롤러 개요에 설명되어 있습니다.

## Googlebot에서 사이트를 방문하지 못하도록 차단하기

Googlebot은 이전에 크롤링한 페이지에 삽입된 링크에서 주로 크롤링할 새 URL을 발견합니다. 링크를 게시하지 않는 방법으로 사이트를 비밀로 유지하는 것은 거의 불가능합니다. 예를 들어 누군가 '비밀' 사이트의 링크를 클릭하여 다른 사이트로 연결되면 '비밀' 사이트 URL은 리퍼러 태그에 나타날 수 있으며, 리퍼러 로그에 포함된 다른 사이트에 의해 저장되고 게시될 수 있습니다.

Googlebot이 사이트의 콘텐츠를 크롤링하지 못하게 하려는 경우 [여러 가지 방법을 사용할 수 있습니다](https://developers.google.com/search/docs/crawling-indexing/control-what-you-share?hl=ko). _크롤링_과 _색인 생성_에는 차이가 있습니다. Googlebot이 페이지를 크롤링하지 못하도록 차단한다고 해서 페이지의 URL이 검색 결과에 표시되는 것까지 차단되는 것은 아닙니다.

-   **Googlebot이 페이지를 크롤링하지 못하게 하시겠어요?** [robots.txt 파일](https://developers.google.com/search/docs/crawling-indexing/robots/intro?hl=ko)을 사용하세요.
-   **Google에서 페이지의 색인을 생성하지 않도록 하고 싶으신가요?** [`noindex`](https://developers.google.com/search/docs/crawling-indexing/block-indexing?hl=ko)를 사용하세요.
-   **크롤러나 사용자 둘 다 페이지에 액세스할 수 없도록 차단해야 하나요?** [다른 방법(예: 비밀번호 보호)](https://developers.google.com/search/docs/crawling-indexing/control-what-you-share?hl=ko)을 사용하세요.

Googlebot을 차단하면 Google 검색(디스커버 및 모든 Google 검색 결과 기능 포함) 및 기타 제품(예: Google 이미지, Google 동영상, Google 뉴스)에 영향을 미칩니다.

## Googlebot인지 확인하기

Googlebot을 차단하기 전에 다른 크롤러가 Googlebot에서 사용되는 HTTP `user-agent` 요청 헤더로 위장하는 경우가 많다는 점에 유의하세요. 문제가 되는 요청이 실제로 Google에서 보낸 것인지 확인해야 합니다. 실제로 Googlebot에서 보낸 요청인지 확인하는 가장 좋은 방법은 요청의 소스 IP에 [역방향 DNS 조회를 사용](https://developers.google.com/search/docs/crawling-indexing/verifying-googlebot?hl=ko#manual)하거나 소스 IP를 [Googlebot IP 범위](https://developers.google.com/search/docs/crawling-indexing/verifying-googlebot?hl=ko#use-automatic-solutions)와 일치시킵니다.