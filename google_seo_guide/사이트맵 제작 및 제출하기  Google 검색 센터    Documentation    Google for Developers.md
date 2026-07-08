## 사이트맵 제작 및 제출하기

이 페이지에서는 사이트맵을 만들고 Google에서 사용할 수 있도록 하는 방법을 설명합니다. 사이트맵을 처음 사용한다면 [먼저 소개 부분을 참고하세요](https://developers.google.com/search/docs/crawling-indexing/sitemaps/overview?hl=ko).

Google에서는 [사이트맵 프로토콜](https://www.sitemaps.org/protocol.html#otherformats)에 따라 정의된 사이트맵 형식을 지원합니다. 형식마다 고유한 장단점이 있습니다. 사이트 및 설정에 가장 적합한 옵션을 선택하세요. Google에서 특별히 선호하는 옵션은 없습니다. 다음 표는 여러 가지 사이트맵 형식을 비교하여 보여줍니다.

| 사이트맵 비교 | 사이트맵 비교 |
|---------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| [XML 사이트맵](https://developers.google.com/search/docs/crawling-indexing/sitemaps/build-sitemap?hl=ko#xml) | XML 사이트맵은 가장 다양한 용도로 사용할 수 있는 사이트맵 형식입니다. 확장할 수 있으며 [이미지](https://developers.google.com/search/docs/crawling-indexing/sitemaps/image-sitemaps?hl=ko), [동영상](https://developers.google.com/search/docs/crawling-indexing/sitemaps/video-sitemaps?hl=ko), [뉴스](https://developers.google.com/search/docs/crawling-indexing/sitemaps/news-sitemap?hl=ko) 콘텐츠뿐 아니라 페이지의 [현지화된 버전](https://developers.google.com/search/docs/specialty/international/localized-versions?hl=ko)에 관한 추가적인 데이터를 제공하는 데 사용할 수도 있습니다.

**장점:**

-   확장 가능하며 다양한 용도로 사용할 수 있습니다.
-   URL에 관해 가장 많은 정보를 제공할 수 있습니다.
-   대부분의 콘텐츠 관리 시스템(CMS)에서 자동으로 사이트맵을 생성하거나 CMS 사용자는 다양한 사이트맵 플러그인을 찾을 수 있습니다.

**단점:**

-   사용하기에 번거로울 수 있습니다.
-   용량이 큰 사이트 또는 URL이 자주 변경되는 사이트의 매핑을 유지하기가 복잡할 수 있습니다. |
| [RSS, mRSS, Atom 1.0](https://developers.google.com/search/docs/crawling-indexing/sitemaps/build-sitemap?hl=ko#rss) | RSS, mRSS, Atom 1.0 사이트맵은 XML 사이트맵과 구조는 비슷하지만, CMS에서 자동으로 생성되므로 가장 간편하게 제공할 수 있습니다.

**장점:**

-   대부분의 CMS가 RSS 및 Atom 피드를 자동으로 생성합니다.
-   Google에 동영상에 대한 정보를 제공할 때 사용할 수 있습니다.

**단점:**

-   [HTML 및 색인 생성이 가능한 기타 텍스트 콘텐츠](https://developers.google.com/search/docs/crawling-indexing/indexable-file-types?hl=ko) 외에 이미지나 뉴스가 아닌 동영상에 관한 정보만 제공할 수 있습니다.
-   사용하기에 번거로울 수 있습니다. |
| [텍스트 사이트맵](https://developers.google.com/search/docs/crawling-indexing/sitemaps/build-sitemap?hl=ko#text) | 가장 간단한 사이트맵 형식으로 HTML 및 기타 색인 생성이 가능한 페이지의 URL만 표시할 수 있습니다.

**장점:**

-   특히 용량이 큰 사이트에서 쉽게 사용하고 관리할 수 있는 방법입니다.

**단점:**

-   HTML 및 기타 색인 생성이 가능한 텍스트 콘텐츠에만 사용할 수 있습니다. |

## 사이트맵 권장사항

사이트맵 권장사항은 [사이트맵 프로토콜](https://www.sitemaps.org/protocol.html)로 정의됩니다. 크기 제한, 사이트맵 위치, 사이트맵에 포함된 URL 관련 권장사항이 가장 잘 지켜지지 않는 편입니다.

**사이트맵 크기 제한:** 형식과 관계없이 사이트맵은 1개당 50MB(압축하지 않은 파일 기준) 또는 URL 50,000개로 제한됩니다. 파일이 더 크거나 URL이 더 많은 경우, 사이트맵을 여러 개의 사이트맵으로 나눠야 합니다. [사이트맵 색인](https://developers.google.com/search/docs/crawling-indexing/sitemaps/large-sitemaps?hl=ko) 파일을 만들어 Google에 색인 파일 하나만 제출하는 방법도 있습니다(선택사항). 즉, Google에 여러 개의 사이트맵 및 사이트맵 색인 파일을 제출하면 됩니다. Search Console에서 개별 사이트맵의 검색 실적을 추적하려는 경우 이러한 방식이 유용할 수 있습니다.

**사이트맵 파일 인코딩 및 위치:** 사이트맵 파일은 UTF-8로 인코딩되어야 합니다. 사이트의 어디에나 사이트맵을 호스팅할 수 있지만 [Search Console](https://developers.google.com/search/docs/crawling-indexing/sitemaps/build-sitemap?hl=ko#addsitemap)을 통해 사이트맵을 제출하지 않으면 사이트맵은 상위 디렉터리의 하위 요소에만 영향을 미칩니다. 따라서 사이트 루트에 게시된 사이트맵은 사이트의 모든 파일에 영향을 줄 수 있으므로 여기에 게시하는 것을 권장합니다.

**참조 URL의 속성:** 사이트맵에서 정규화된 절대 URL을 사용하세요. Google은 표시된 그대로 URL을 크롤링하려고 시도합니다. 예를 들어 사이트가 `https://www.example.com/`에 있다면 `/mypage.html`(상대 URL)과 같은 URL을 지정하지 말고 완전한 절대 URL(`https://www.example.com/mypage.html`)을 사용하세요.

사이트맵에 Google 검색결과에 표시하려는 URL을 포함합니다. Google은 일반적으로 검색결과에 [표준 URL](https://developers.google.com/search/docs/crawling-indexing/consolidate-duplicate-urls?hl=ko)을 표시하는데, 사이트맵을 사용해 이 표준 URL에 영향을 줄 수 있습니다. 페이지의 모바일 버전과 데스크톱 버전 URL이 다르다면 사이트맵에서 한 버전에만 연결하는 것이 좋습니다. 하지만, 두 URL을 모두 가리키도록 하려면 URL에 [주석](https://developers.google.com/search/docs/crawling-indexing/mobile/mobile-sites-mobile-first-indexing?hl=ko#additional-best-practices)을 추가하여 데스크톱 버전과 모바일 버전을 표시합니다.

전체 권장사항 목록은 [사이트맵 프로토콜](https://www.sitemaps.org/protocol.html)을 확인하세요.

## XML 사이트맵

XML 사이트맵은 지원되는 형식 중 가장 다양한 용도로 사용할 수 있는 사이트맵 형식입니다. Google에서 지원하는 사이트맵 확장 프로그램을 사용하면 [이미지](https://developers.google.com/search/docs/crawling-indexing/sitemaps/image-sitemaps?hl=ko), [동영상](https://developers.google.com/search/docs/crawling-indexing/sitemaps/video-sitemaps?hl=ko), [뉴스](https://developers.google.com/search/docs/crawling-indexing/sitemaps/news-sitemap?hl=ko)콘텐츠 및 페이지의 [현지화된 버전](https://developers.google.com/search/docs/specialty/international/localized-versions?hl=ko)에 관한 추가 정보도 제공할 수 있습니다.

다음은 단일 URL 위치를 포함하는 매우 기본적인 XML 사이트맵입니다.

```xml
<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url>
    <loc>https://www.example.com/foo.html</loc>
    <lastmod>2022-06-04</lastmod>
  </url>
</urlset>
```

[sitemaps.org](https://www.sitemaps.org/protocol.html)에서 복잡한 예와 전체 문서를 확인할 수 있습니다.

### XML 사이트맵 관련 추가 참고사항

-   모든 XML 파일과 마찬가지로 모든 태그 값은 [엔티티 이스케이프 처리](https://www.sitemaps.org/protocol.html#escaping)되어야 합니다.
-   Google에서는 `<priority>` 및 `<changefreq>` 값을 무시합니다.
-   Google에서는 `<lastmod>` 값이 일관되고 정확성을 검증(예: 페이지의 마지막 수정사항과 비교)할 수 있는 경우에 이 값을 사용합니다.

CMS에서 RSS 또는 Atom 피드를 생성하는 경우 피드의 URL을 사이트맵으로 제출할 수 있습니다. 대부분의 CMS는 자동으로 피드를 생성하지만 이 피드는 최근 URL에 관한 정보만 제공합니다.

### RSS, mRSS, Atom 1.0에 관한 추가 참고사항

-   Google에서는 RSS 2.0 및 Atom 1.0 피드를 사용할 수 있습니다.
-   [mRSS(media RSS) 피드](https://developers.google.com/search/docs/crawling-indexing/sitemaps/video-sitemaps?hl=ko)를 사용하여 사이트의 동영상 콘텐츠에 대한 세부정보를 Google에 제공할 수 있습니다.
-   모든 XML 파일과 마찬가지로 모든 태그 값은 [엔티티 이스케이프 처리](https://www.sitemaps.org/protocol.html#escaping)되어야 합니다.

## 텍스트 사이트맵

웹 페이지 URL만 제공하려면 한 줄에 하나의 URL이 포함된 일반 텍스트 파일을 만들어 Google에 제출할 수 있습니다. 예를 들어 사이트에 두 페이지가 있다면 다음과 같이 `https://www.example.com/sitemap.txt`에 있는 텍스트 사이트맵에 추가할 수 있습니다.

```bash
https://www.example.com/file1.html
https://www.example.com/file2.html
```

### 텍스트 파일 사이트맵에 관한 추가 참고사항

-   사이트맵 파일에 URL이 아닌 다른 항목을 넣으면 안 됩니다.
-   `.txt` 확장자(예: sitemap.txt)만 있다면 텍스트 파일의 이름을 원하는 대로 정할 수 있습니다.

## 사이트맵 만드는 방법

<iframe frameborder="0" allowfullscreen="" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share" referrerpolicy="strict-origin-when-cross-origin" width="640" height="360" src="https://www.youtube.com/embed/zLKuG0C7dUw?origin=https%3A%2F%2Fdevelopers.google.com&amp;autoplay&amp;controls&amp;embed_domain&amp;enablejsapi=1&amp;end&amp;hl&amp;showinfo&amp;start&amp;video-id=zLKuG0C7dUw&amp;widgetid=39&amp;forigin=https%3A%2F%2Fdevelopers.google.com%2Fsearch%2Fdocs%2Fcrawling-indexing%2Fsitemaps%2Fbuild-sitemap%3Fhl%3Dko&amp;aoriginsup=1&amp;gporigin=https%3A%2F%2Fwww.google.com%2F&amp;vf=1" id="widget40" data-gtm-yt-inspected-225073684_46="true" data-gtm-yt-inspected-183356566_95="true" data-gtm-yt-inspected-26="true" data-gtm-yt-inspected-45="true" data-gtm-yt-inspected-52="true" data-title="YouTube video player" title="3 tips for setting up a sitemap"></iframe>

사이트맵을 만들면 검색결과에 표시할 URL을 검색엔진에 알려주게 됩니다. 이러한 URL이 [표준 URL](https://developers.google.com/search/docs/crawling-indexing/consolidate-duplicate-urls?hl=ko)입니다. 여러 URL에서 동일한 콘텐츠에 액세스할 수 있는 경우 동일한 콘텐츠로 연결되는 모든 URL 대신 원하는 URL을 선택하여 사이트맵에 포함합니다.

사이트맵에 포함할 URL을 정한 후 사이트 아키텍처와 크기에 따라 다음 방법 중 하나를 선택하여 사이트맵을 만듭니다.

-   [CMS에서 사이트맵을 생성하도록 합니다](https://developers.google.com/search/docs/crawling-indexing/sitemaps/build-sitemap?hl=ko#cmssitemap).
-   URL이 수십 개 미만인 사이트맵의 경우 [사이트맵을 수동으로 생성](https://developers.google.com/search/docs/crawling-indexing/sitemaps/build-sitemap?hl=ko#manualsitemap)할 수 있습니다.
-   URL이 수십 개 이상인 사이트맵의 경우 [사이트맵을 자동으로 생성](https://developers.google.com/search/docs/crawling-indexing/sitemaps/build-sitemap?hl=ko#autositemap)합니다.

### CMS에서 사이트맵을 생성하도록 하기

WordPress, Wix, Blogger와 같은 CMS를 사용하는 경우 CMS가 이미 검색엔진에 제공할 수 있는 사이트맵을 만들었을 수 있습니다. CMS에서 사이트맵을 생성하는 방법 또는 CMS가 사이트맵을 자동으로 생성하지 않는 경우 사이트맵을 만드는 방법에 관한 정보를 검색해 보세요. 예를 들어 Wix의 경우 'wix 사이트맵', Blogger의 경우 'Blogger RSS'라고 검색합니다.

### 수동으로 사이트맵 생성하기

URL이 수십 개 미만인 사이트맵의 경우 사이트맵을 수동으로 생성할 수 있습니다. 수동으로 생성하려면 [Windows 메모장](https://www.microsoft.com/en-us/search?q=windows+notepad) 또는 [Nano(Linux, MacOS)](https://www.nano-editor.org/)와 같은 텍스트 편집기를 열고 [사이트맵 형식](https://developers.google.com/search/docs/crawling-indexing/sitemaps/build-sitemap?hl=ko#sitemapformat) 섹션에 설명된 구문을 따릅니다. [URL에 허용되는 문자](https://developers.google.com/maps/url-encoding?hl=ko)라면 파일 이름을 원하는 대로 지정할 수 있습니다.

수동으로도 더 큰 사이트맵을 만들 수는 있지만 지루한 작업을 해야 하며 장기적으로 유지하기가 어렵습니다.

### 도구로 사이트맵 자동 생성하기

URL이 수십 개 이상인 사이트맵의 경우 사이트맵을 생성해야 합니다. [사이트맵을 생성](https://www.google.com/search?q=generate+sitemap&hl=ko)할 수 있는 다양한 도구가 있습니다. 그러나 가장 좋은 방법은 웹사이트 소프트웨어에서 생성하게 하는 것입니다. 예를 들어 웹사이트 데이터베이스에서 사이트 URL을 추출한 다음 웹 서버의 화면이나 실제 파일로 URL을 내보낼 수 있습니다. 이 솔루션에 관해서는 개발자나 서버 관리자에게 문의하세요. 코드에 관한 아이디어가 필요하면 [타사 사이트맵 생성기](http://code.google.com/p/sitemap-generators/wiki/SitemapGenerators?hl=ko)의 이전 컬렉션(관리되지 않고 있음)을 확인하세요.

사이트맵의 URL이 표시되는 순서는 중요하지 않습니다. Google에서는 이를 중요하게 여기지 않습니다. [사이트맵의 크기 요구사항](https://developers.google.com/search/docs/crawling-indexing/sitemaps/build-sitemap?hl=ko#general-guidelines)에 유의하세요. 사이트맵이 너무 커지면 크기가 작은 여러 개의 사이트맵으로 분할해야 합니다. [대규모 사이트맵 관리](https://developers.google.com/search/docs/crawling-indexing/sitemaps/large-sitemaps?hl=ko)에 관해 자세히 알아보세요.

사이트맵을 제출하는 것은 힌트를 주는 정도밖에 안 됩니다. Google에서 사이트맵을 다운로드하거나 사이트의 URL 크롤링에 사이트맵을 사용한다고 보장하지 않습니다. Google에 사이트맵을 제공하는 데 몇 가지 방법이 있습니다.

-   [사이트맵 보고서](https://support.google.com/webmasters/answer/7451001?hl=ko)를 사용하여 **Search Console에서 사이트맵을 제출**하세요. 이렇게 하면 Googlebot이 사이트맵에 액세스한 시점과 잠재적인 처리 오류도 확인할 수 있습니다.
-   **Search Console API를 사용**하여 프로그래매틱 방식으로 [사이트맵을 제출](https://developers.google.com/webmaster-tools/v1/sitemaps/submit?hl=ko)하세요.
-   **robots.txt 파일 내 아무 곳에나 다음 행을 삽입**하여 사이트맵으로 연결되는 경로를 지정합니다. 그렇게 하면 Google에서 다음번에 robots.txt 파일을 크롤링할 때 경로를 확인하게 됩니다.
    
    ```
    Sitemap: https://example.com/my_sitemap.xml
    ```
    
-   Atom 또는 RSS를 사용하는 경우 [WebSub](https://www.w3.org/TR/websub/)를 사용하여 Google을 포함한 검색엔진에 변경사항을 브로드캐스트할 수 있습니다.

## 여러 사이트의 사이트맵을 교차 제출하는 방법

웹사이트가 여러 개 있는 경우 확인된 모든 사이트의 URL을 포함하는 사이트맵을 하나 이상 만들고 사이트맵을 한곳에 저장하면 사이트맵 제출 과정이 단순해집니다. 다음을 사용하도록 선택할 수 있습니다.

-   다른 도메인의 사이트를 비롯하여 여러 웹사이트의 URL을 포함하는 단일 사이트맵. 예를 들어 `https://host1.example.com/sitemap.xml`에 있는 사이트맵에는 다음 URL이 포함될 수 있습니다.
    -   `https://host1.example.com`
    -   `https://host2.example.com`
    -   `https://host3.example.com`
    -   `https://host1.example1.com`
    -   `https://host1.example.ch`
-   모두 한곳에 위치한 개별 사이트맵(사이트당 하나). 예를 들어 `https://host1.example.com`는 다음과 같은 모든 사이트맵을 호스팅할 수 있습니다.
    -   `https://host1.example.com/host1-example-sitemap.xml`
    -   `https://host1.example.com/host2-example-sitemap.xml`
    -   `https://host1.example.com/host3-example-sitemap.xml`
    -   `https://host1.example.com/host1-example1-sitemap.xml`
    -   `https://host1.example.com/host1-example-ch-sitemap.xml`

단일 위치에서 호스팅되는 크로스 사이트 사이트맵을 제출하려면 Search Console 또는 robots.txt를 사용할 수 있습니다.

### Search Console로 사이트맵 교차 제출

1.  사이트맵에 추가할 모든 사이트의 [소유권을 확인](https://support.google.com/webmasters/answer/35181?hl=ko)하세요.
2.  원하는 모든 사이트의 URL을 포함하는 [사이트맵을 만듭니다](https://developers.google.com/search/docs/crawling-indexing/sitemaps/build-sitemap?hl=ko#createsitemap)(원하는 경우 추가 생성). 원하는 경우 사이트맵을 [사이트맵 색인](https://developers.google.com/search/docs/crawling-indexing/sitemaps/large-sitemaps?hl=ko) 파일에 포함할 수 있으며 여기에서 사이트맵 색인을 사용할 수 있습니다.
3.  Google Search Console을 사용하여 [사이트맵이나 사이트맵 색인 파일을 제출](https://support.google.com/webmasters/answer/7451001?hl=ko)합니다.

### robots.txt로 사이트맵 교차 제출

1.  각 사이트에 [사이트맵을 하나 이상 만듭니다](https://developers.google.com/search/docs/crawling-indexing/sitemaps/build-sitemap?hl=ko#createsitemap). 각 사이트맵 파일에는 특정 사이트의 URL만 포함해야 합니다.
2.  제어 권한이 있는 단일 사이트에 모든 사이트맵을 업로드합니다(예: `https://sitemaps.example.com`).
3.  각 사이트에 대해 robots.txt 파일이 개별 사이트의 사이트맵을 참조해야 합니다. 예를 들어 `https://example.com/`의 사이트맵을 만들고 `https://sitemaps.example.com/sitemap-example-com.xml`에서 이 사이트맵을 호스팅하는 경우 `https://example.com/robots.txt`에 있는 robots.txt 파일의 사이트맵을 참조합니다.
    
    ```cpp
    # robots.txt file of https://example.com/
    sitemap: https://sitemaps.example.com/sitemap-example-com.xml
    ```
    

## Troubleshooting sitemaps

If you're having trouble with your sitemap, you can investigate the errors with Google Search Console. See Search Console's [sitemaps troubleshooting guide](https://support.google.com/webmasters/answer/7451001?hl=ko#errors) for help.