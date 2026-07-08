## 사이트맵 색인 파일로 사이트맵 관리

[크기 제한](https://developers.google.com/search/docs/crawling-indexing/sitemaps/build-sitemap?hl=ko)을 초과하는 사이트맵이 있는 경우 각 새 사이트맵이 크기 제한 미만이 되도록 대규모 사이트맵을 여러 개의 사이트맵으로 분할해야 합니다. 사이트맵을 분할한 후 사이트맵 색인 파일을 사용하여 한 번에 여러 사이트맵을 제출할 수 있습니다.

## 사이트맵 색인 권장사항

사이트맵 색인 파일의 XML 형식은 사이트맵 파일의 XML 형식과 매우 비슷하며 [사이트맵 프로토콜](https://www.sitemaps.org/protocol.html#index)로 정의됩니다. 즉, 모든 사이트맵 요구사항이 사이트맵 색인 파일에도 적용됩니다.

참조된 사이트맵은 사이트맵 색인 파일과 동일한 사이트에서 호스팅되어야 합니다. [크로스 사이트 제출](https://developers.google.com/search/docs/crawling-indexing/sitemaps/build-sitemap?hl=ko#cross-submit)을 설정하면 이 요구사항이 면제됩니다.

사이트맵 색인 파일에서 참조되는 사이트맵은 사이트맵 색인 파일과 동일한 디렉터리에 있거나 사이트 계층 구조에서 더 낮은 위치에 있어야 합니다. 예를 들어 사이트맵 색인 파일이 `https://example.com/public/sitemap_index.xml`에 있다면 동일하거나 더 하위 디렉터리(예: `https://example.com/public/shared/...`)에 있는 사이트맵만 포함할 수 있습니다.

Search Console 계정에서 사이트맵 색인 파일을 사이트당 500개까지 제출할 수 있습니다.

## 사이트맵 색인의 예

다음은 두 개의 사이트맵이 있는 XML 형식 사이트맵 색인의 예입니다.

```xml
<?xml version="1.0" encoding="UTF-8"?>
<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <sitemap>
    <loc>https://www.example.com/sitemap1.xml.gz</loc>
    <lastmod>2024-08-15</lastmod>
  </sitemap>
  <sitemap>
    <loc>https://www.example.com/sitemap2.xml.gz</loc>
    <lastmod>2022-06-05</lastmod>
  </sitemap>
</sitemapindex>
```

## 사이트맵 색인 참조

사이트맵 색인 태그는 일반 사이트맵과 동일한 네임스페이스로 정의됩니다. [`http://www.sitemaps.org/schemas/sitemap/0.9`](http://www.sitemaps.org/schemas/sitemap/0.9)

Google에서 사이트맵 색인을 사용할 수 있도록 하려면 다음과 같은 필수 태그를 사용해야 합니다.

| 필수 태그 | 필수 태그 |
|--------------|--------------------------------------------------------------------------------------|
| `sitemapindex` | XML 트리의 루트 태그입니다. 여기에는 다른 모든 태그가 포함됩니다. |
| `sitemap` | 파일에 나열된 각 사이트맵의 상위 태그입니다. `sitemapindex` 태그의 유일한 직접 하위 요소입니다. |
| `loc` | 사이트맵의 위치(URL)입니다. `sitemap` 태그의 하위 요소입니다. 사이트맵 색인 파일에는 최대 50,000개의 `loc` 태그가 포함될 수 있습니다. |

또한 다음의 선택적 태그를 사용하면 Google에서 사이트맵 크롤링 일정을 예약하는 데 도움이 됩니다.

| 선택적 태그 | 선택적 태그 |
|---------|---------------------------------------------------------------------------------------------|
| `lastmod` | 해당 사이트맵 파일이 수정된 시간을 식별합니다. `sitemap` 태그의 하위 요소일 수 있습니다. `lastmod` 태그 값은 [W3C Datetime 형식](https://www.w3.org/TR/NOTE-datetime)이어야 합니다. |

## 사이트맵 문제 해결

사이트맵에 문제가 있는 경우 Google Search Console을 사용하여 오류를 조사할 수 있습니다. 도움이 필요한 경우 Search Console의 [사이트맵 문제 해결 가이드](https://support.google.com/webmasters/answer/7451001?hl=ko#errors)를 참고하세요.