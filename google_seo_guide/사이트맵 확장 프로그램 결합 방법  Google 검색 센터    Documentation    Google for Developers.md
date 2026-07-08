## 사이트맵 확장 프로그램 통합 방법

사이트맵 확장 프로그램은 사이트에서 사용 중인 다양한 종류의 콘텐츠와 메타데이터를 Google에 알리는 데 매우 유용합니다. 페이지의 콘텐츠는 이미지와 동영상이 삽입된 뉴스 기사를 게시하는 것과 같이 여러 종류의 확장 프로그램에 해당할 때가 많습니다. 또한 페이지를 현지화할 수도 있습니다. 즉, 현지화된 페이지에 `hreflang` 주석을 추가할 수 있습니다.

## 네임스페이스

사이트맵에서 사용하려는 각 사이트맵 확장 프로그램에 확장 프로그램에서 지원하는 태그를 선언하는 각 네임스페이스를 지정해야 합니다. `urlset` 태그의 `xmlns` 속성을 사용하면 됩니다. Google에서 지원하는 사이트맵 확장 프로그램의 네임스페이스는 다음과 같습니다.

| 확장 프로그램 태그 및 해당 네임스페이스 정의 | 확장 프로그램 태그 및 해당 네임스페이스 정의 |
|---------------------------|-------------------------------------------------|
| `image:` | [`http://www.google.com/schemas/sitemap-image/1.1`](http://www.google.com/schemas/sitemap-image/1.1?hl=ko) |
| `news:` | [`http://www.google.com/schemas/sitemap-news/0.9`](http://www.google.com/schemas/sitemap-news/0.9?hl=ko) |
| `video:` | [`http://www.google.com/schemas/sitemap-video/1.1`](http://www.google.com/schemas/sitemap-video/1.1?hl=ko) |
| `xhtml:`(`hreflang`용) | [`http://www.w3.org/1999/xhtml`](http://www.w3.org/1999/xhtml) |

### 여러 네임스페이스 선언

여러 네임스페이스를 선언하려면 각 확장 프로그램 문서에 설명된 대로 해당 네임스페이스 참조를 사이트맵에 추가합니다. 다음은 뉴스, 동영상, xhtml(`hreflang`용) 확장 프로그램을 사이트맵에 추가하는 방법을 보여 주는 예입니다.

```xml
<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"
           xmlns:news="http://www.google.com/schemas/sitemap-news/0.9"
           xmlns:video="http://www.google.com/schemas/sitemap-video/1.1"
           xmlns:xhtml="http://www.w3.org/1999/xhtml">
  <url>
<!-- rest of the sitemap -->
```

## 사이트맵 확장 프로그램 통합

네임스페이스를 선언한 후 사용하려는 각 사이트맵 확장 프로그램 문서의 구현 세부정보를 따릅니다.

-   [이미지 사이트맵](https://developers.google.com/search/docs/crawling-indexing/sitemaps/image-sitemaps?hl=ko)
-   [뉴스 사이트맵](https://developers.google.com/search/docs/crawling-indexing/sitemaps/news-sitemap?hl=ko)
-   [동영상 사이트맵](https://developers.google.com/search/docs/crawling-indexing/sitemaps/video-sitemaps?hl=ko)
-   [`hreflang`](https://developers.google.com/search/docs/specialty/international/localized-versions?hl=ko#sitemap)

확장 프로그램을 통합하려면 사용 중인 사이트맵 확장 프로그램의 태그를 각 사이트맵 확장 프로그램 문서에 설명된 대로 적절한 `<url>` 태그에 차례로 추가합니다.

예를 들어 뉴스, 동영상, xhtml(`hreflang`) 확장 프로그램을 사이트맵에 추가하려면 다음 단계를 따르세요.

```xml
<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"
    xmlns:news="http://www.google.com/schemas/sitemap-news/0.9"
    xmlns:video="http://www.google.com/schemas/sitemap-video/1.1"
    xmlns:xhtml="http://www.w3.org/1999/xhtml">
  <url>
    <loc>https://www.example.com/english/page.html</loc>
    <!-- Starting with the news extension tags -->
    <news:news>
      <news:publication>
        <news:name>The Example Times</news:name>
        <news:language>en</news:language>
      </news:publication>
      <news:publication_date>2008-12-23</news:publication_date>
      <news:title>Companies A, B in Merger Talks</news:title>
    </news:news>
    <!-- Next we add video extension tags -->
    <video:video>
      <video:thumbnail_loc>https://www.example.com/thumbs/123.jpg</video:thumbnail_loc>
      <video:title>Lizzi is painting the wall</video:title>
      <video:description>
        Gary is watching the paint dry on the wall Lizzi painted.
      </video:description>
      <video:player_loc>
        https://player.example.com/video/987654321
      </video:player_loc>
    </video:video>
    <!-- And finally the xhtml tags for hreflang -->
    <xhtml:link
                rel="alternate"
                hreflang="de"
                href="https://www.example.de/deutsch/page.html"/>
    <xhtml:link
                rel="alternate"
                hreflang="de-ch"
                href="https://www.example.de/schweiz-deutsch/page.html"/>
    <xhtml:link
                rel="alternate"
                hreflang="en"
                href="https://www.example.com/english/page.html"/>
  </url>
<!-- Add more <url> tags -->
```

사이트맵에서 확장 프로그램 순서는 `<loc>` 태그 다음과는 관련이 없습니다. [일반 사이트맵 권장사항](https://developers.google.com/search/docs/crawling-indexing/sitemaps/build-sitemap?hl=ko#general-guidelines), 특히 파일 크기 한도에 유의하세요. 사이트맵 확장 프로그램을 통합하면 사이트맵의 파일 크기가 크게 늘어납니다.

## 사이트맵 문제 해결

사이트맵에 문제가 있는 경우 Google Search Console을 사용하여 오류를 조사할 수 있습니다. 도움이 필요한 경우 Search Console의 [사이트맵 문제 해결 가이드](https://support.google.com/webmasters/answer/7451001?hl=ko#errors)를 참고하세요.