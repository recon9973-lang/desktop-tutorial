## 이미지 사이트맵

이미지 사이트맵을 사용하면 특히 Google이 찾을 수 없는 이미지 (예: 사이트에서 자바스크립트 코드를 통해 도달하는 이미지)를 비롯하여 사이트의 다른 이미지를 Google에 알릴 수 있습니다. 별도의 이미지 사이트맵을 만들거나 기존 사이트맵에 이미지 사이트맵 태그를 추가할 수 있으며, 두 방식 모두 Google에서 사용할 수 있습니다.

이미지 사이트맵은 일반적인 사이트맵을 기반으로 하므로 이미지 사이트맵에도 [일반 사이트맵 권장사항](https://developers.google.com/search/docs/crawling-indexing/sitemaps/build-sitemap?hl=ko#general-guidelines)이 적용됩니다. 또한 [이미지 게시에 관한 일반 권장사항](https://developers.google.com/search/docs/appearance/google-images?hl=ko)을 따르는 것이 좋습니다.

## 이미지 사이트맵 예

다음은 두 개의 `<url>` 요소가 있는 이미지 사이트 맵 확장 프로그램을 사용하는 일반 사이트 맵의 예입니다.

-   `https://example.com/sample1.html`, 이미지 2개 포함
-   `https://example.com/sample2.html`, 이미지 1개 포함

```xml
<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"
    xmlns:image="http://www.google.com/schemas/sitemap-image/1.1">
  <url>
    <loc>https://example.com/sample1.html</loc>
    <image:image>
      <image:loc>https://example.com/image.jpg</image:loc>
    </image:image>
    <image:image>
      <image:loc>https://example.com/photo.jpg</image:loc>
    </image:image>
  </url>
  <url>
    <loc>https://example.com/sample2.html</loc>
    <image:image>
      <image:loc>https://example.com/picture.jpg</image:loc>
    </image:image>
  </url>
</urlset>
```

## 이미지 사이트맵 참조

`image` 태그는 이미지 사이트맵 네임스페이스에 정의됩니다. [`http://www.google.com/schemas/sitemap-image/1.1`](http://www.google.com/schemas/sitemap-image/1.1?hl=ko)

Google에서 이미지 사이트맵을 사용할 수 있도록 하려면 다음과 같은 필수 태그를 사용해야 합니다.

| 필수 태그 | 필수 태그 |
|---------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `<image:image>` | 단일 이미지의 모든 정보를 포함합니다. 각 `<url>` 태그는 최대 1,000개의 `<image:image>` 태그를 포함할 수 있습니다. |
| `<image:loc>` | 이미지의 URL입니다.

이미지 URL이 기본 사이트와 같은 도메인에 있지 않은 경우도 있습니다. Search Console에서 두 도메인을 확인한다면 문제없습니다. 예를 들어, Google 사이트 도구와 같은 콘텐츠 전송 네트워크를 사용하여 이미지를 호스팅하려면 호스팅 사이트가 Search Console에서 확인되어야 합니다. 또한 [robots.txt](https://developers.google.com/search/docs/crawling-indexing/robots/intro?hl=ko) 파일이 색인을 생성하고자 하는 콘텐츠의 크롤링을 차단하지 않도록 해야 합니다. |

### 지원 중단된 태그 및 속성

문서에서 다음 태그 및 속성을 삭제했습니다. `<image:caption>`, `<image:geo_location>`, `<image:title>`, `<image:license>` 자세한 내용은 [지원 중단 공지사항](https://developers.google.com/search/blog/2022/05/spring-cleaning-sitemap-extensions?hl=ko)을 참고하세요.

## 사이트맵 문제 해결

사이트맵에 문제가 있는 경우 Google Search Console을 사용하여 오류를 조사할 수 있습니다. 도움이 필요한 경우 Search Console의 [사이트맵 문제 해결 가이드](https://support.google.com/webmasters/answer/7451001?hl=ko#errors)를 참고하세요.