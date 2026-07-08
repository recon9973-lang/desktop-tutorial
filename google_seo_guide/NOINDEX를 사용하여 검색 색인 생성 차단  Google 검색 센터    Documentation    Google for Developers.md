`noindex`는 `<meta>` 태그 또는 HTTP 응답 헤더가 있는 규칙 집합이며 Google과 같이 `noindex` 규칙을 지원하는 검색엔진에서 콘텐츠의 색인을 생성하지 못하게 합니다. Googlebot이 페이지를 크롤링할 때 noindex 태그나 헤더를 추출하면 다른 사이트가 페이지에 연결되어 있는지와 관계없이 페이지 전체를 Google 검색 결과에서 제외합니다.

`noindex`를 사용하면 페이지별로 사이트 액세스 권한을 제어할 수 있으므로 서버에 대한 루트 액세스 권한이 없는 경우 유용합니다.

## `noindex` 구현

`noindex`는 `<meta>` 태그 및 HTTP 응답 헤더의 두 가지 방법으로 구현할 수 있습니다. 두 방법의 효과는 동일하며 사이트에 더 편리하고 콘텐츠 유형에 적절한 방법을 선택하면 됩니다. Google은 robots.txt 파일에서 `noindex` 규칙을 지정하는 것을 지원하지 않습니다.

`noindex` 규칙을 색인 생성을 제어하는 다른 규칙과 결합할 수도 있습니다. 예를 들어 `nofollow` 힌트를 `noindex` 규칙인 `<meta name="robots" content="**noindex, nofollow**" />`와 결합할 수 있습니다.

### `<meta>` 태그

`noindex` 규칙을 지원하는 _모든 검색엔진_이 사이트 페이지에서 색인을 생성하지 않도록 하려면 다음 `<meta>` 태그를 페이지의 `<head>` 섹션에 배치하세요.

```php-template
<meta name="robots" content="noindex">
```

_Google 웹 크롤러만_ 페이지의 색인을 생성하지 못하게 하려면 다음을 추가합니다.

```php-template
<meta name="googlebot" content="noindex">
```

일부 검색엔진에서는 `noindex` 규칙을 다르게 해석할 수도 있습니다. 따라서 내 페이지가 다른 검색엔진의 검색 결과에는 여전히 표시될 수 있습니다.

[`noindex` `<meta>` 태그에 관해 자세히 알아보세요](https://developers.google.com/search/docs/crawling-indexing/robots-meta-tag?hl=ko#robotsmeta).

`<meta>` 태그 대신 응답에 `noindex` 또는 `none` 값을 가진 `X-Robots-Tag` HTTP 헤더를 반환할 수 있습니다. 응답 헤더는 PDF, 동영상 파일, 이미지 파일 등 HTML이 아닌 리소스에 사용할 수 있습니다. 다음은 검색엔진이 페이지의 색인을 생성하지 않도록 지시하는 `X-Robots-Tag` 헤더가 있는 HTTP 응답의 예입니다.

```
HTTP/1.1 200 OK
(...)
X-Robots-Tag: noindex
(...)
```

[`noindex` 응답 헤더 자세히 알아보기](https://developers.google.com/search/docs/crawling-indexing/robots-meta-tag?hl=ko#xrobotstag)

### `noindex` 문제 디버깅

`<meta>` 태그와 HTTP 헤더를 확인하려면 페이지를 크롤링해야 합니다. 페이지가 계속 검색 결과에 표시된다면 `noindex` 규칙을 추가한 이후 Goggle에서 페이지를 크롤링하지 않았기 때문일 수 있습니다. 인터넷에서 페이지의 중요도에 따라 Googlebot이 페이지를 다시 방문하는 데 몇 개월이 걸릴 수 있습니다. [URL 검사 도구](https://support.google.com/webmasters/answer/9012289?hl=ko)를 사용해 Google에 페이지를 다시 크롤링하도록 요청하세요.

Google 검색 결과에서 사이트 페이지를 신속하게 삭제해야 하는 경우 [삭제에 관한 문서](https://developers.google.com/search/docs/crawling-indexing/remove-information?hl=ko)를 참고하세요.

robots.txt 파일에서 Google 웹 크롤러가 이 URL을 크롤링하지 못하도록 차단하여 Google에서 태그를 인식하지 못하는 경우에도 페이지가 검색 결과에 계속 표시됩니다. Google로부터의 페이지 차단을 해제하려면 [robots.txt 파일을 수정](https://developers.google.com/search/docs/crawling-indexing/robots/submit-updated-robots-txt?hl=ko)해야 합니다.

마지막으로 `noindex` 규칙이 Googlebot에 표시되는지 확인하세요. `noindex`가 올바르게 구현되었는지 테스트하려면 [URL 검사 도구](https://support.google.com/webmasters/answer/9012289?hl=ko)를 사용하여 페이지를 크롤링하는 동안 Googlebot에서 수신한 HTML을 확인하세요. Search Console에서 [페이지 색인 생성 보고서](https://support.google.com/webmasters/answer/7440203?hl=ko)를 사용하여 Googlebot이 `noindex` 규칙을 추출한 사이트 페이지를 모니터링할 수도 있습니다.