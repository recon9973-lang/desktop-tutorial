Google은 크롤러 또는 가져오기 도구를 사용하여 자동 또는 사용자 요청에 의해 트리거되는 방식으로 제품에 대한 작업을 수행합니다. 크롤러('로봇' 또는 '스파이더'라고도 함)는 일반적으로 [웹사이트를 자동으로 검색하고 스캔](https://developers.google.com/search/docs/fundamentals/how-search-works?hl=ko#crawling)하는 데 사용되는 프로그램을 가리키는 용어입니다. 가져오기 도구는 일반적으로 사용자를 대신하여 단일 요청을 실행하는 [wget](https://www.gnu.org/software/wget/)과 같은 프로그램 역할을 합니다. Google의 클라이언트는 세 가지 카테고리로 분류됩니다.

| [일반 크롤러](https://developers.google.com/crawling/docs/crawlers-fetchers/google-common-crawlers?hl=ko) | Google 제품에 사용되는 일반 크롤러(예: [Googlebot](https://developers.google.com/search/docs/crawling-indexing/googlebot?hl=ko))입니다. 자동 크롤링에 대한 robots.txt 규칙을 항상 준수합니다. |
|--------------|--------------------------------------------------------------------------------------------------------------------------------------------------|
| [예외 상황 크롤러](https://developers.google.com/crawling/docs/crawlers-fetchers/google-special-case-crawlers?hl=ko) | 예외 상황 크롤러는 일반 크롤러와 유사하지만 크롤링되는 사이트와 Google 제품 간에 크롤링 프로세스 관련 합의가 있는 특정 제품에서 사용됩니다. 예를 들어 `AdsBot`은 광고 게시자의 권한이 있는 전역 robots.txt 사용자 에이전트(`*`)를 무시합니다. |
| [사용자 트리거 가져오기](https://developers.google.com/crawling/docs/crawlers-fetchers/google-user-triggered-fetchers?hl=ko) | 사용자 트리거 가져오기 도구는 최종 사용자가 가져오기를 트리거하는 도구 및 제품 기능입니다. 예를 들어 [Google 사이트 인증 도구](https://support.google.com/webmasters/answer/9008080?hl=ko)는 사용자의 요청에 따라 작동합니다. |

## Google 크롤러 및 가져오기 도구의 기술 속성

Google 크롤러와 가져오기 도구는 웹이 확장됨에 따라 성능과 규모를 향상시키기 위해 수천 대의 컴퓨터에서 동시에 실행되도록 설계되었습니다. 대역폭 사용량을 최적화하기 위해 이 클라이언트는 전 세계 여러 데이터 센터에 분산되어 액세스할 수 있는 사이트 근처에 위치합니다. 그러므로 로그에는 여러 IP 주소에서 방문한 내역이 표시될 수 있습니다. Google은 주로 미국 IP 주소에서 이그레스합니다. Google이 미국에서 발생한 요청을 차단하는 사이트를 감지하면 다른 국가에 있는 IP 주소에서 크롤링을 시도할 수 있습니다.

### 지원되는 전송 프로토콜

Google 크롤러와 가져오기 도구는 HTTP/1.1 및 [HTTP/2](https://en.wikipedia.org/wiki/HTTP/2)를 지원합니다. 이 크롤러는 가장 우수한 크롤링 성능을 제공하는 프로토콜 버전을 사용하며 이전 크롤링 통계에 따라 크롤링 세션 간에 프로토콜을 전환할 수 있습니다. Google 크롤러에서 사용하는 기본 프로토콜 버전은 HTTP/1.1입니다. HTTP/2를 통해 크롤링하면 사이트와 Googlebot의 컴퓨팅 리소스(예: CPU, RAM)를 절약할 수 있지만 사이트에는 Google 제품별 이점이 없습니다(예: Google 검색에서 순위가 상승하지 않음). HTTP/2를 통한 크롤링을 거부하려면 Google이 HTTP/2를 통해 사이트에 액세스하려고 할 때 `421` HTTP 상태 코드로 응답하도록 사이트를 호스팅하는 서버에 지시합니다. 그렇게 할 수 없는 경우 [크롤링팀에 메시지를 보내면 됩니다](https://www.google.com/webmasters/tools/googlebot-report?hl=ko)(단, 이 방법은 일시적임).

Google 크롤러 인프라는 FTP([RFC959](https://datatracker.ietf.org/doc/html/rfc959) 및 업데이트에 정의됨) 및 FTPS([RFC4217](https://datatracker.ietf.org/doc/html/rfc4217) 및 업데이트에 정의됨)를 통한 크롤링도 지원하지만 이러한 프로토콜을 통한 크롤링은 드뭅니다.

### 지원되는 콘텐츠 인코딩

Google의 크롤러와 가져오기 도구는 다음과 같은 콘텐츠 인코딩(압축)을 지원합니다. [gzip](https://en.wikipedia.org/wiki/Gzip), [deflate](https://en.wikipedia.org/wiki/Deflate), [Brotli(br)](https://en.wikipedia.org/wiki/Brotli) 각 Google 사용자 에이전트에서 지원하는 콘텐츠 인코딩은 각 요청의 `Accept-Encoding` 헤더에 광고됩니다. 예: `Accept-Encoding: gzip, deflate, br`.

### 파일 크기 한도

기본적으로 Google 크롤러와 가져오기 도구는 파일의 처음 15MB만 크롤링하며 이 한도를 초과하는 콘텐츠는 무시됩니다. 하지만 개별 프로젝트에서는 크롤러와 가져오기 도구, 다양한 파일 형식에 대해 서로 다른 한도를 설정할 수 있습니다. 예를 들어 [Googlebot과 같은](https://developers.google.com/search/docs/crawling-indexing/googlebot?hl=ko) Google 크롤러는 크기 한도가 더 작거나(예: 2MB) PDF에 HTML보다 큰 파일 크기 한도를 지정할 수 있습니다.

### 크롤링 속도 및 호스트 로드

Google의 목표는 방문한 사이트에서 서버에 무리를 주지 않으면서 가능한 한 많은 페이지를 크롤링하는 것입니다. 사이트에서 Google의 크롤링 요청 속도를 맞추는 데 문제가 있는 경우 [크롤링 속도를 낮출](https://developers.google.com/crawling/docs/crawlers-fetchers/reduce-crawl-rate?hl=ko) 수 있습니다. Google 크롤러에 부적절한 [HTTP 응답 코드](https://developers.google.com/search/docs/crawling-indexing/http-network-errors?hl=ko)를 전송하면 Google 제품에 사이트가 표시되는 방식에 영향을 미칠 수 있습니다.

### HTTP 캐싱

Google의 크롤링 인프라는 [HTTP 캐싱 표준](https://httpwg.org/specs/rfc9111.html)에 정의된 휴리스틱 HTTP 캐싱을 지원합니다. 특히 `ETag` 응답 및 `If-None-Match` 요청 헤더, `Last-Modified` 응답 및 `If-Modified-Since` 요청 헤더를 통해 이러한 캐싱을 지원합니다.

`ETag` 및 `Last-Modified` 응답 헤더 필드가 모두 HTTP 응답에 있는 경우 Google 크롤러는 `ETag` 값을 [HTTP 표준에 따라 필요](https://www.rfc-editor.org/rfc/rfc9110.html#section-13.1.3)한 값으로 사용합니다. 특히 Google 크롤러의 경우 `Last-Modified` 헤더 대신 [`ETag`](https://www.rfc-editor.org/rfc/rfc9110#name-etag)를 사용하여 캐싱 환경설정을 나타내는 것이 좋습니다. `ETag`에는 날짜 형식 지정 문제가 없기 때문입니다.

다른 HTTP 캐싱 지시어는 지원되지 않습니다.

개별 Google 크롤러와 가져오기 도구는 연결된 제품의 필요에 따라 캐싱을 사용할 수도 있고 사용하지 않을 수도 있습니다. 예를 들어 `Googlebot`은 Google 검색의 URL을 다시 크롤링할 때 캐싱을 지원하고 `Storebot-Google`은 특정 조건에서만 캐싱을 지원합니다.

사이트에 HTTP 캐싱을 구현하려면 호스팅 또는 콘텐츠 관리 시스템 제공업체에 문의하세요.

#### `ETag` 및 `If-None-Match`

Google의 크롤링 인프라는 [HTTP 캐싱 표준](https://httpwg.org/specs/rfc9111.html)에 정의된 `ETag` 및 `If-None-Match`를 지원합니다. [`ETag`](https://www.rfc-editor.org/rfc/rfc9110#name-etag) 응답 헤더와 이에 대응하는 요청 헤더 [`If-None-Match`](https://www.rfc-editor.org/rfc/rfc9110#name-if-none-match)에 대해 자세히 알아보세요.

#### Last-Modified 및 If-Modified-Since

Google의 크롤링 인프라는 [HTTP 캐싱 표준](https://httpwg.org/specs/rfc9111.html)에 정의된 `Last-Modified` 및 `If-Modified-Since`를 지원하지만 다음과 같은 예외가 있습니다.

-   `Last-Modified` 헤더의 날짜는 [HTTP 표준](https://www.rfc-editor.org/rfc/rfc9110.html)에 따라 형식이 지정되어야 합니다. 파싱 문제를 방지하려면 다음 날짜 형식을 사용하는 것이 좋습니다. '요일, DD Mon YYYY HH:MM:SS 시간대' 예를 들면 'Fri, 4 Sep 1998 19:15:56 GMT'처럼 설정할 수 있습니다.
-   필수는 아니지만 크롤러가 특정 URL을 다시 크롤링해야 하는 시점을 파악할 수 있도록 [`Cache-Control` 응답 헤더의 `max-age` 필드](https://www.rfc-editor.org/rfc/rfc9111.html#name-max-age-2)도 설정하는 것이 좋습니다. `max-age` 필드의 값을 콘텐츠가 변경되지 않을 것으로 예상되는 시간(초)으로 설정합니다. 예를 들면 '`Cache-Control: max-age=94043`'과 같이 설정할 수 있습니다.

[`Last-Modified`](https://www.rfc-editor.org/rfc/rfc9110#name-last-modified) 응답 헤더와 이에 대응하는 요청 헤더 [`If-Modified-Since`](https://www.rfc-editor.org/rfc/rfc9110#name-if-modified-since)에 대해 자세히 알아보세요.

## Google 크롤러 및 가져오기 도구 확인

Google 크롤러는 다음 세 가지 방법으로 자신을 식별합니다.

1.  HTTP `user-agent` 요청 헤더
2.  요청의 소스 IP 주소
3.  소스 IP의 역방향 DNS 호스트 이름

이 세부정보를 사용하여 [Google 크롤러 및 가져오기 도구를 확인](https://developers.google.com/crawling/docs/crawlers-fetchers/verify-google-requests?hl=ko)하는 방법을 알아보세요.