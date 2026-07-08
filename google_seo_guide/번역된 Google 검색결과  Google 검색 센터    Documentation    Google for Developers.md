Google 검색에서는 모든 사용자가 정보에 액세스하여 유용하게 사용할 수 있도록 노력하고 있습니다. 사용자가 현지 언어로 검색할 때 콘텐츠 격차와 견해 차이를 줄일 수 있도록 Google에서는 가능한 경우 검색어 언어가 아닌 검색결과에 대해 검색결과의 제목 링크와 스니펫을 번역할 수도 있습니다. 번역된 검색결과를 통해 사용자는 다른 언어로 된 검색결과를 현지 언어로 볼 수 있으며 게시자가 더 많은 사용자에게 도달하는 데 도움이 될 수 있습니다.

![Google 검색에 번역된 검색결과가 표시되는 방식](https://developers.google.com/static/search/docs/images/translated-result.png?hl=ko) ![Google 검색에 번역된 뉴스 검색결과가 표시되는 방식](https://developers.google.com/static/search/docs/images/translated-news-results.png?hl=ko)

## 기능 제공 여부

현재 Google에서는 검색 결과를 아랍어, 벵골어, 영어, 프랑스어, 독일어, 구자라트어, 힌디어, 인도네시아어, 칸나다어, 한국어, 말라얄람어, 마라티어, 페르시아어, 포르투갈어, 스페인어, 타밀어, 텔루구어, 태국어, 터키어, 우르두어, 베트남어로 번역할 수 있습니다. 이 기능은 모바일과 데스크톱에서 사용할 수 있습니다.

## 번역된 검색결과의 작동 방식

사용자가 번역된 제목 링크를 클릭하면 기계 번역된 페이지가 표시됩니다. 사용자는 원래 검색결과를 확인하고 원래 언어로 된 전체 페이지에 액세스할 수도 있습니다.

Google에서는 번역된 페이지를 호스팅하지 않습니다. 번역된 검색결과를 통해 페이지를 여는 것은 [Google 번역](https://support.google.com/translate/answer/2534559?hl=ko)을 통해 원래 검색결과를 열거나 [Chrome 브라우저 내 번역](https://support.google.com/chrome/answer/173424?hl=ko)을 사용하는 것과 다르지 않습니다. 즉, 삽입된 이미지 및 기타 페이지 기능과 페이지의 자바스크립트는 일반적으로 지원됩니다.

## Search Console에서 실적 모니터링

번역된 검색결과의 클릭수와 노출수를 모니터링하려면 [실적 보고서](https://support.google.com/webmasters/answer/7576553?hl=ko)의 [검색 노출 필터](https://support.google.com/webmasters/answer/7576553?hl=ko#zippy=,search-appearance)를 사용하세요.

## 번역된 검색결과 선택 또는 선택 해제

이 기능은 사용자의 언어에 기반하여 모든 페이지와 검색결과에 적용할 수 있습니다. 이 기능을 선택하기 위해 별도의 작업을 할 필요는 없습니다.

번역된 검색결과는 Google 검색의 다른 번역 관련 기능과 같습니다. Google 검색의 모든 번역 기능을 선택 해제하려면 `meta` 태그 또는 HTTP 헤더로 구현할 수 있는 [`notranslate` 규칙](https://developers.google.com/search/docs/crawling-indexing/robots-meta-tag?hl=ko#notranslate)을 사용합니다.

```php-template
<!-- opt out of translation features on all search engines that support this rule -->
<meta name="robots" content="notranslate">
```

```php-template
<!-- opt out of translation features on Google -->
<meta name="googlebot" content="notranslate">
```

또는 다음과 같이 규칙을 HTTP 응답 헤더로 지정할 수도 있습니다.

```yaml
HTTP/1.1 200 OK
Date: Tue, 25 May 2010 21:42:43 GMT
(...)
X-Robots-Tag: notranslate
(...)
```