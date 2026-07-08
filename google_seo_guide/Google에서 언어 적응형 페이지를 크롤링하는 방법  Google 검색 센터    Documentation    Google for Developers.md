사이트에 _언어 적응형_ 페이지(감지된 국가 또는 방문자가 선호하는 언어에 따라 다른 콘텐츠를 반환하는 페이지)가 있는 경우 Google에서 일부 언어의 콘텐츠를 크롤링하거나, 색인 생성하거나, 순위를 지정하지 못할 수도 있습니다. 이는 Googlebot 크롤러가 기본적으로 미국에 위치한 것으로 감지되는 IP 주소를 사용하기 때문입니다. 또한 크롤러는 요청 헤더에 `Accept-Language`를 설정하지 않은 상태로 HTTP 요청을 보냅니다.

## 지역 분산 크롤링

Googlebot은 미국에 위치한 IP 주소 외에도 미국 외에 위치한 IP 주소로도 크롤링합니다.

Google에서 항상 권장하는 바와 같이 Googlebot의 출처로 감지되는 국가에 있는 사용자를 대하는 방식과 동일하게 Googlebot을 취급하시기 바랍니다. 즉, 미국에 있는 사용자는 콘텐츠에 액세스하지 못하도록 차단하고 오스트레일리아 방문자는 콘텐츠를 볼 수 있도록 허용하는 경우, 서버에서 출처가 미국으로 감지되는 Googlebot은 차단하지만 오스트레일리아로 감지되는 Googlebot의 액세스는 허용해야 합니다.

### 기타 고려사항

-   Googlebot은 모든 크롤링 설정에 동일한 사용자 에이전트 문자열을 사용합니다. [Google 크롤러에서 사용하는 사용자 에이전트 문자열](https://developers.google.com/search/docs/crawling-indexing/overview-google-crawlers?hl=ko)에 관해 자세히 알아보세요.
-   역방향 DNS 조회를 사용하여 [Googlebot 지역 분산 크롤링](https://developers.google.com/search/docs/crawling-indexing/verifying-googlebot?hl=ko)을 확인할 수 있습니다.
-   사이트에서 [_로봇 제외 프로토콜_](https://www.rfc-editor.org/rfc/rfc9309.html)을 사용하는 경우 언어별로 일관되게 적용해야 합니다. 즉, 각 언어에서 [robots `meta` 태그](https://developers.google.com/search/docs/crawling-indexing/robots-meta-tag?hl=ko)와 [robots.txt 파일](https://developers.google.com/search/docs/crawling-indexing/robots/create-robots-txt?hl=ko)에 지정하는 규칙이 동일해야 합니다.