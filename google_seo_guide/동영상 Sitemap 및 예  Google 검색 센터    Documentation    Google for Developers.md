## 동영상 사이트맵 및 대안

동영상 사이트맵은 페이지에 호스팅된 동영상의 추가 정보가 포함된 [사이트맵](https://developers.google.com/search/docs/crawling-indexing/sitemaps/overview?hl=ko)입니다. 동영상 사이트맵을 만들면 사이트의 동영상 콘텐츠, 특히 새로 추가되었거나 Google의 일반적인 크롤링 메커니즘을 통해 찾을 수 없는 콘텐츠를 Google이 찾고 파악할 수 있도록 하는 데 유용합니다.

Google은 동영상 사이트맵 사용을 권장하지만 [mRSS 피드](https://developers.google.com/search/docs/crawling-indexing/sitemaps/video-sitemaps?hl=ko#sitemap_alternatives)도 지원합니다.

## 동영상 사이트맵 권장사항

동영상 사이트맵은 일반적인 사이트맵을 기반으로 하므로 동영상 사이트맵에도 [일반 사이트맵 권장사항](https://developers.google.com/search/docs/crawling-indexing/sitemaps/build-sitemap?hl=ko#general-guidelines)이 적용됩니다. 동영상 전용의 사이트맵이나 mRSS 피드를 별도로 만들 수도 있고, 기존의 [사이트맵](https://developers.google.com/search/docs/crawling-indexing/sitemaps/build-sitemap?hl=ko#xml) 내에 동영상 사이트맵 태그를 추가할 수도 있습니다. 선호하는 방법을 선택하면 됩니다.

동영상 사이트맵에는 다음의 요구사항도 적용됩니다.

-   호스트 페이지의 콘텐츠와 관련 없는 동영상은 표시하지 마세요. 예를 들어 페이지의 소소한 부록이거나 기본 텍스트 콘텐츠와는 관련이 없는 동영상이 여기에 해당합니다.
-   Googlebot이 동영상 사이트맵에서 참조된 모든 파일에 액세스할 수 있어야 합니다. 즉, 동영상 사이트맵의 모든 URL은 다음 조건을 충족해야 합니다.
    
    -   [robots.txt](https://developers.google.com/search/docs/crawling-indexing/robots/intro?hl=ko) 규칙에 의해 크롤링이 차단되어서는 안 됨
    -   메타 파일이 없고 로그인하지 않아도 액세스할 수 있어야 함
    -   방화벽이나 유사한 메커니즘에 의해 차단되어서는 안 됨
    -   지원되는 프로토콜인 HTTP 및 FTP에서 액세스할 수 있어야 함(스트리밍 프로토콜은 지원되지 않음)
    
    스팸 발송자가 `<player_loc>` 또는 `<content_loc>` URL의 동영상 콘텐츠에 액세스하지 못하도록 하려면 [서버에 액세스하는 모든 봇이 실제로 Googlebot인지 확인하세요](https://developers.google.com/search/docs/crawling-indexing/verifying-googlebot?hl=ko).
    

Google 검색의 동영상에 관해 자세히 알아보려면 [동영상 권장사항](https://developers.google.com/search/docs/appearance/video?hl=ko)을 참고하세요.

## 동영상 사이트맵 예

다음 예는 동영상 확장 프로그램이 포함된 일반 사이트맵을 보여줍니다. 여기에는 하나의 `<url>` 태그에 중첩된 두 개의 동영상 항목이 포함됩니다. 첫 번째 `<video>` 항목에는 Google에서 사용할 수 있는 모든 태그가 포함되지만 두 번째 항목에는 필수 태그만 포함됩니다.

```xml
<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"
    xmlns:video="http://www.google.com/schemas/sitemap-video/1.1">
  <url>
    <loc>https://www.example.com/videos/some_video_landing_page.html</loc>
    <video:video>
      <video:thumbnail_loc>https://www.example.com/thumbs/123.jpg</video:thumbnail_loc>
      <video:title>Grilling steaks for summer</video:title>
      <video:description>
        Alkis shows you how to get perfectly done steaks every time
      </video:description>
      <video:content_loc>
        http://streamserver.example.com/video123.mp4
      </video:content_loc>
      <video:player_loc>
        https://www.example.com/videoplayer.php?video=123
      </video:player_loc>
      <video:duration>600</video:duration>
      <video:expiration_date>2021-11-05T19:20:30+08:00</video:expiration_date>
      <video:rating>4.2</video:rating>
      <video:view_count>12345</video:view_count>
      <video:publication_date>2007-11-05T19:20:30+08:00</video:publication_date>
      <video:family_friendly>yes</video:family_friendly>
      <video:restriction relationship="allow">IE GB US CA</video:restriction>
      <video:platform relationship="allow">web tv</video:platform>
      <video:requires_subscription>yes</video:requires_subscription>
      <video:uploader
        info="https://www.example.com/users/grillymcgrillerson">GrillyMcGrillerson
      </video:uploader>
      <video:live>no</video:live>
      <video:tag>steak</video:tag>
      <video:tag>meat</video:tag>
      <video:tag>summer</video:tag>
    </video:video>
    <video:video>
      <video:thumbnail_loc>https://www.example.com/thumbs/345.jpg</video:thumbnail_loc>
      <video:title>Grilling steaks for winter</video:title>
      <video:description>
        In the freezing cold, Roman shows you how to get perfectly done steaks every time.
      </video:description>
      <video:content_loc>
        http://streamserver.example.com/video345.mp4
      </video:content_loc>
      <video:player_loc>
        https://www.example.com/videoplayer.php?video=345
      </video:player_loc>
    </video:video>
  </url>
</urlset>
```

#### 예시 더보기

다음 예는 동영상 사이트맵에 Vimeo 삽입 동영상을 추가하는 방법을 보여줍니다.

```xml
예시 더보기<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"
    xmlns:video="http://www.google.com/schemas/sitemap-video/1.1">
  <url>
    <loc>https://www.example.com/videos/some_video_landing_page.html</loc>
    <video:video>
      <video:thumbnail_loc>https://www.example.com/thumbs/123.jpg</video:thumbnail_loc>
      <video:title>Lizzi is painting the wall</video:title>
      <video:description>
        Gary is watching the paint dry on the wall Lizzi painted.
      </video:description>
      <video:player_loc>
        https://player.vimeo.com/video/987654321
      </video:player_loc>
    </video:video>
  </url>
</urlset>
```

다음 예는 동영상 사이트맵에 YouTube 삽입 동영상을 추가하는 방법을 보여줍니다.

```xml
예시 더보기<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"
    xmlns:video="http://www.google.com/schemas/sitemap-video/1.1">
  <url>
    <loc>https://www.example.com/videos/some_video_landing_page.html</loc>
    <video:video>
      <video:thumbnail_loc>https://www.example.com/thumbs/345.jpg</video:thumbnail_loc>
      <video:title>John teaches cheese</video:title>
      <video:description>
        John explains the differences between a banana and cheese.
      </video:description>
      <video:player_loc>
        https://www.youtube.com/embed/1a2b3c4d
      </video:player_loc>
    </video:video>
  </url>
</urlset>
```

## 동영상 사이트맵 참조

`video` 태그는 동영상 사이트맵 네임스페이스에 정의됩니다. [`http://www.google.com/schemas/sitemap-video/1.1`](http://www.google.com/schemas/sitemap-video/1.1?hl=ko) 각 태그는 달리 지정하지 않는 한 동영상당 한 번만 추가할 수 있습니다.

Google에서 동영상 사이트맵을 사용할 수 있도록 하려면 다음과 같은 필수 태그를 사용해야 합니다.

| 필수 태그 | 필수 태그 |
|-----------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `<video:video>` | `<loc>` 태그로 지정된 페이지에 있는 단일 동영상에 관한 모든 정보의 상위 요소입니다. `<loc>` 태그에 여러 개의 `<video:video>` 태그를 중첩할 수 있으며, 호스팅 페이지에 있는 동영상 1개마다 태그를 하나씩 설정합니다. |
| `<video:thumbnail_loc>` | 동영상 썸네일 이미지 파일을 가리키는 URL입니다. [동영상 썸네일 요구사항](https://developers.google.com/search/docs/appearance/video?hl=ko#thumbnails)을 따릅니다. |
| `<video:title>` | 동영상 제목입니다. 모든 HTML 항목은 이스케이프 처리되거나 [`CDATA` 블록](http://wikipedia.org/wiki/CDATA)에 래핑되어야 합니다. 동영상이 삽입된 웹페이지에 표시되는 동영상 제목과 일치하는 것이 좋습니다. |
| `<video:description>` | 동영상 설명입니다. 최대 2,048자(영문 기준)까지 허용됩니다. 모든 HTML 항목은 이스케이프 처리되거나 [`CDATA` 블록](http://wikipedia.org/wiki/CDATA)에 래핑되어야 합니다. 동영상이 삽입된 웹페이지에 표시되는 설명과 일치해야 하지만, 단어 하나하나가 전부 일치해야 하는 것은 아닙니다. |
| `<video:content_loc>` | 실제 동영상 미디어 파일을 가리키는 URL입니다. 파일은 [지원되는 형식](https://developers.google.com/search/docs/appearance/video?hl=ko#file-types) 중 하나여야 합니다.

**추가 가이드라인**

-   HTML 및 플래시 형식은 지원되지 않습니다.
-   상위 `<loc>` 태그의 URL과 같아서는 안 됩니다.
-   구조화된 데이터의 `[VideoObject.contentUrl](https://developers.google.com/search/docs/appearance/structured-data/video?hl=ko)`과 동일합니다.
-   **권장사항:** 콘텐츠의 액세스를 제한하되 크롤링되기를 원한다면 [Googlebot 확인](https://developers.google.com/search/docs/crawling-indexing/verifying-googlebot?hl=ko)을 사용하여 Googlebot이 콘텐츠에 액세스할 수 있도록 해야 합니다. |
| `<video:player_loc>` | **특정** 동영상의 플레이어를 가리키는 URL입니다. 보통 `<embed>` 태그의 `src` 속성에 있는 정보입니다.

**추가 가이드라인**

-   `<loc>` URL과 같아서는 안 됩니다.
-   Vimeo, YouTube 및 `iframe` 동영상을 통한 동영상 삽입을 허용하는 동영상 호스팅 플랫폼의 경우 `video:content_loc` 대신 이 값이 사용됩니다. 구조화된 데이터의 `[VideoObject.embedUrl](https://developers.google.com/search/docs/appearance/structured-data/video?hl=ko)`과 동일합니다.
-   **권장사항:** 콘텐츠의 액세스를 제한하되 크롤링되기를 원한다면 [Googlebot 확인](https://developers.google.com/search/docs/crawling-indexing/verifying-googlebot?hl=ko)을 사용하여 Googlebot이 콘텐츠에 액세스할 수 있도록 해야 합니다. |

또한 다음의 선택적 태그를 사용하면 Google에서 동영상과 속성을 더 잘 이해하는 데 도움이 됩니다.

| 선택적 태그 | 선택적 태그 |
|-------------------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `<video:duration>` | 동영상의 길이(초)입니다. 값은 `1` 이상 `28800`(8시간) 이하여야 합니다. |
| `<video:expiration_date>` | 동영상을 더 이상 사용할 수 없게 되는 날짜로, [W3C 형식](http://www.w3.org/TR/NOTE-datetime)입니다. 동영상이 만료되지 않은 경우 이 태그를 생략하세요. 이 태그가 있는 경우 Google 검색에서 이 날짜 이후로 동영상을 표시하지 못하게 됩니다. 동일한 URL에서 반복된 동영상이 필요한 경우 만료일을 새 만료일로 업데이트합니다.

지원되는 값은 완전한 날짜(`YYYY-MM-DD`) 또는 완전한 날짜에 시, 분, 초와 시간대를 추가한 값입니다(`YYYY-MM-DDThh:mm:ss+TZD`).

**예:** `2012-07-16T19:20:30+08:00` |
| `<video:rating>` | 동영상 등급입니다. 지원되는 값은 `0.0`(최저)~`5.0`(최고)의 부동 소수점 숫자입니다(0.0과 5.0 포함). |
| `<video:view_count>` | 동영상의 조회수입니다. |
| `<video:publication_date>` | 동영상이 처음 게시된 날짜로, [W3C 형식](http://www.w3.org/TR/NOTE-datetime)입니다. 지원되는 값은 완전한 날짜(`YYYY-MM-DD`) 또는 완전한 날짜에 시, 분, 초와 시간대를 추가한 값입니다(`YYYY-MM-DDThh:mm:ss+TZD`).

**예:** `2007-07-16T19:20:30+08:00` |
| `<video:family_friendly>` | [SafeSearch](https://developers.google.com/search/docs/crawling-indexing/safesearch?hl=ko)를 사용 설정했을 때 동영상이 표시되는지 여부를 나타냅니다. 이 태그를 생략하면 세이프서치를 사용 중일 때 동영상이 표시됩니다.

**지원되는 값**:

-   `yes`: 세이프서치를 사용 설정한 경우 동영상이 표시됩니다.
-   `no`: 세이프서치를 사용 중지한 경우에만 동영상이 표시됩니다. |
| `<video:restriction>` | 특정 국가의 검색결과에서 동영상을 표시하거나 숨길지 여부입니다.

공백으로 구분된 [ISO 3166 형식](http://wikipedia.org/wiki/ISO_3166)의 국가 코드 목록을 지정합니다. `<video:restriction>` 태그가 없으면 동영상은 모든 위치에서 표시될 수 있는 것으로 간주됩니다. _이 태그는 검색결과에만 영향을 미칩니다. 사용자가 다른 방법을 통해 제한된 위치에서 동영상을 찾거나 재생하는 것을 방지하지는 않습니다._ [국가 제한 적용에 관해 자세히 알아보기](https://developers.google.com/search/docs/appearance/video?hl=ko#restrict_by_country)

**속성:**

상위 태그 `<video:restriction>`를 사용하는 경우 다음 속성이 필요합니다.

-   `relationship`: 지정된 국가의 검색결과에서 동영상이 허용되거나 거부되는지 나타냅니다. 지원되는 값은 다음과 같습니다.
    -   `allow`: 명시된 국가는 허용되며 명시되어 있지 않은 국가는 거부됩니다.
    -   `deny`: 명시된 국가는 거부되며 명시되어 있지 않은 국가는 허용됩니다.

**예:** 이 예에서 동영상 검색결과는 캐나다 및 멕시코에서만 표시됩니다.

`<video:restriction relationship="allow">CA MX</video:restriction>` |
| `<video:platform>` | 지정된 플랫폼 유형에서 검색결과에 동영상을 표시하거나 숨길지를 나타냅니다. 이는 공백으로 구분된 플랫폼 유형의 목록입니다. _이 태그는 지정된 기기 유형에서의 검색 결과에만 영향을 미칩니다. 즉, 사용자가 제한된 플랫폼에서 동영상을 재생하지 못하도록 하지는 않습니다._

`<video:platform>` 태그가 없으면 Google에서 해당 동영상은 모든 플랫폼에서 재생 가능하다고 여깁니다. [플랫폼 제한 적용에 관해 자세히 알아보기](https://developers.google.com/search/docs/appearance/video?hl=ko#restrict_by_platform)

**지원되는 값**:

-   `web`: 데스크톱 및 노트북의 컴퓨터 브라우저입니다.
-   `mobile`: 스마트폰이나 태블릿 등의 모바일 브라우저입니다.
-   `tv`: Google TV 기기 및 게임 콘솔을 통해 사용할 수 있는 것과 같은 TV 브라우저입니다.

**속성:**

상위 태그 `<video:platform>`을 사용하는 경우 다음 속성이 필요합니다.

-   `relationship`: 특정 플랫폼에서 동영상이 제한되는지 또는 허용되는지 지정합니다. 지원되는 값은 다음과 같습니다.
    -   `allow`: 생략된 플랫폼이 거부됩니다.
    -   `deny`: 생략된 플랫폼이 허용됩니다.

**예:** 다음 예에서는 웹이나 TV를 사용하는 사용자는 허용하되 휴대기기를 사용하는 사용자는 허용하지 않습니다.<br>`<video:platform relationship="allow">web tv</video:platform>` |
| `<video:requires_subscription>` | 동영상을 시청하기 위해 유료 또는 무료 구독을 반드시 해야 하는지를 나타냅니다. 지원되는 값은 다음과 같습니다.

-   `yes`: 구독이 필요합니다.
-   `no`: 구독이 필요하지 않습니다. |
| `<video:uploader>` | 동영상 업로더의 이름입니다. 문자열 값은 최대 255자(영문 기준)까지 가능합니다.

**속성:**

-   `info`[_선택_] 이 업로더에 관한 추가 정보가 있는 웹페이지의 URL을 지정합니다. 이 URL은 `<loc>` 태그와 동일한 도메인에 있어야 합니다. |
| `<video:live>` | 동영상이 실시간 스트림인지를 나타냅니다. 지원되는 값은 다음과 같습니다.

-   `yes`: 라이브 스트리밍 동영상입니다.
-   `no`: 라이브 스트리밍 동영상이 아닙니다. |
| `<video:tag>` | 동영상을 설명하는 임의의 문자열 태그입니다. 태그는 일반적으로 동영상 또는 콘텐츠의 일부분과 연관된 핵심 개념에 관한 아주 짧은 설명입니다. 하나의 동영상은 단 하나의 카테고리에만 속할 수 있지만 태그는 여러 개가 있을 수 있습니다. 예를 들어 구이 요리에 관한 동영상은 '구이' 카테고리에 포함되어 있지만 '스테이크', '고기', '여름', '야외'로 태그될 수 있습니다. 동영상과 관련된 태그마다 새로운 `<video:tag>` 요소를 만드세요. 동영상당 최대 32개의 태그가 허용됩니다. |

### 지원 중단된 태그 및 속성

문서에서 다음 태그 및 속성을 삭제했습니다. `<video:category>`, `<video:gallery_loc>`, `<video:player_loc>` 태그의 `autoplay` 및 `allow_embed` 속성, `<video:price>` 태그 및 속성, `<video:tvshow>` 태그 및 속성 자세한 내용은 [지원 중단 공지사항](https://developers.google.com/search/blog/2022/05/spring-cleaning-sitemap-extensions?hl=ko)을 참고하세요.

## 사이트맵 대안: mRSS

Google은 동영상 Sitemap 사용을 권장하지만 mRSS 피드도 지원합니다.

Google은 [RSS 2.0](http://cyber.law.harvard.edu/rss/rss.html)의 요소 기능을 보완하는 RSS 모듈인 [mRSS](http://www.rssboard.org/media-rss)를 지원합니다. mRSS 피드는 동영상 사이트맵과 아주 비슷하고 사이트맵처럼 테스트, 제출, 업데이트할 수 있습니다.

미디어 피드에 관한 자세한 내용은 [공식 미디어 RSS 문서](http://www.rssboard.org/media-rss)를 참고하세요.

다음은 Google이 사용하는 모든 태그를 제공한 mRSS 피드의 사용 예입니다.

```xml
<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:media="http://search.yahoo.com/mrss/" xmlns:dcterms="http://purl.org/dc/terms/">
  <channel>
    <title>Example MRSS</title>
    <link>https://www.example.com/examples/mrss/</link>
    <description>MRSS Example</description>
    <item xmlns:media="http://search.yahoo.com/mrss/" xmlns:dcterms="http://purl.org/dc/terms/">
      <link>https://www.example.com/examples/mrss/example.html</link>
      <media:content url="https://www.example.com/examples/mrss/example.flv" fileSize="405321"
                        type="video/x-flv" height="240" width="320" duration="120" medium="video" isDefault="true">
        <media:player url="https://www.example.com/shows/example/video.swf?flash_params" />
        <media:title>Grilling Steaks for Summer</media:title>
        <media:description>Get perfectly done steaks every time</media:description>
        <media:thumbnail url="https://www.example.com/examples/mrss/example.png" height="120" width="160"/>
        <media:price price="19.99" currency="EUR" />
        <media:price type="subscription" />
      </media:content>
      <media:restriction relationship="allow" type="country">us ca</media:restriction>
      <dcterms:valid xmlns:dcterms="http://purl.org/dc/terms/">end=2020-10-15T00:00+01:00; scheme=W3C-DTF</dcterms:valid>
      <dcterms:type>live-video</dcterms:type>
    </item>
  </channel>
</rss>
```

[전체 mRSS 사양](http://www.rssboard.org/media-rss)에는 여러 선택적 태그, 권장사항, 예가 포함됩니다.

Google에서 mRSS 피드를 사용할 수 있도록 하려면 다음과 같은 필수 태그를 사용해야 합니다.

| 필수 태그 | 필수 태그 |
|---------------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `<media:content>` | 동영상에 관한 정보를 포함합니다.

속성:

-   `medium`: 콘텐츠 유형입니다. `video`로 설정합니다.
-   `url`: 원본 동영상 콘텐츠의 직접 URL입니다. **이 태그가 지정되지 않으면 `<media:player>` 태그를 지정해야 합니다.**
-   `duration`[_선택, 권장됨_] 동영상 길이(초)입니다.

`<media:content>` 태그의 다른 모든 선택적 속성 및 하위 필드에 관해 알아보려면 [mRSS 사양](http://www.rssboard.org/media-rss)을 참고하세요. |
| `<media:player>` | **`<media:content>`에서 `<media:player>` 또는 `url` 속성 중 하나 이상을 지정해야 합니다.**

**특정** 동영상의 플레이어를 가리키는 URL입니다. 일반적으로 이는 `<embed>` 태그의 `src` 속성에 있는 정보이며 `<loc>` 태그의 콘텐츠와 같아서는 안 됩니다. `<link>` 태그와 동일한 URL이어서는 안 됩니다. `<link>` 태그는 동영상을 호스팅하는 페이지의 URL을 가리키고 이 태그는 플레이어를 가리킵니다. |
| `<media:title>` | 동영상 제목입니다. 최대 100자(영문 기준)까지 허용됩니다. 모든 HTML 항목은 이스케이프 처리되거나 [CDATA 블록](http://wikipedia.org/wiki/CDATA)에 래핑되어야 합니다. |
| `<media:description>` | 동영상 설명입니다. 최대 2,048자(영문 기준)까지 허용됩니다. 모든 HTML 항목은 이스케이프 처리되거나 [CDATA 블록](http://wikipedia.org/wiki/CDATA)에 래핑되어야 합니다. |
| `<media:thumbnail>` | 미리보기 썸네일을 가리키는 URL입니다. [동영상 썸네일 요구사항](https://developers.google.com/search/docs/appearance/video?hl=ko#thumbnails)을 따릅니다. |

또한 다음의 선택적 태그를 사용하면 Google에서 동영상과 속성을 더 잘 이해하는 데 도움이 됩니다.

| 선택적 태그 | 선택적 태그 |
|---------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `<dcterms:valid>` | 동영상의 게시일 및 만료일입니다. [`dcterms:valid` 태그의 전체 사양](https://www.dublincore.org/specifications/dublin-core/dcmi-terms/terms/valid/)은 다음과 같습니다.

**예:**

<dcterms:valid>
start=2002-10-13T09:00+01:00;
end=2002-10-17T17:00+01:00;
scheme=W3C-DTF
<dcterms:valid> |
| `<media:restriction>` | 동영상이 재생되거나 재생될 수 없는 공백으로 구분된 국가의 목록([ISO 3166 형식](http://wikipedia.org/wiki/ISO_3166))입니다. `<media:restriction>` 태그가 없으면 동영상이 모든 국가에서 재생 가능한 것으로 간주됩니다.

**속성:**

상위 태그 `<media:restriction>`을 사용하는 경우 다음 속성이 필요합니다.

-   `type`: `type` 속성을 `country`로 설정합니다. 국가별 제한사항만 지원됩니다.
-   `relationship`: 지정된 국가 목록에서 동영상을 재생할지 지정합니다. 지원되는 값은 다음과 같습니다.
    -   `allow`: 명시된 국가는 허용되며 명시되어 있지 않은 국가는 거부됩니다.
    -   `deny`: 명시된 국가는 거부되며 명시되어 있지 않은 국가는 허용됩니다.

[국가별 제한사항에 관해 자세히 알아보기](https://developers.google.com/search/docs/appearance/video?hl=ko#restrict_by_country)

예:

<media:restriction relationship="allow" type="country">us ca</media:restriction> |
| `<media:price>` | 동영상을 다운로드하거나 시청하는 가격입니다. 비용 지불 없이 제공되는 동영상에는 이 태그를 사용하지 마세요. 두 개 이상의 `<media:price>` 요소가 표시될 수 있습니다. 예를 들어 여러 통화 또는 구매 옵션을 지정하는 경우입니다.

**속성:**

상위 태그 `<media:price>`을 사용하는 경우 다음 속성이 필요합니다.

-   `currency`: [ISO 4217 형식](https://en.wikipedia.org/wiki/ISO_4217)으로 표시된 통화입니다.
-   `type`: 구매 옵션입니다. 지원되는 값은 다음과 같습니다.
    -   `rent`: 대여할 수 있는 동영상입니다.
    -   `purchase`: 구매할 수 있는 동영상입니다.
    -   `package`: 패키지 거래의 일부인 동영상입니다.
    -   `subscription`: 구독하면 볼 수 있는 동영상입니다. |

## 사이트맵 문제 해결

사이트맵에 문제가 있는 경우 Google Search Console을 사용하여 오류를 조사할 수 있습니다. 도움이 필요한 경우 Search Console의 [사이트맵 문제 해결 가이드](https://support.google.com/webmasters/answer/7451001?hl=ko#errors)를 참고하세요.