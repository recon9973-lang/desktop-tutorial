Google 검색에서 중복되거나 매우 비슷한 페이지의 [표준 URL](https://developers.google.com/search/docs/crawling-indexing/canonicalization?hl=ko)을 지정할 때, 여러 가지 방법을 사용해 자신이 선호하는 표준 URL이 무엇인지 나타낼 수 있습니다. 다음 방법을 사용해 자신이 선호하는 표준 URL을 알릴 수 있으며, 가장 큰 영향을 미치는 방법부터 순서대로 나열되어 있습니다.

-   [**리디렉션**](https://developers.google.com/search/docs/crawling-indexing/consolidate-duplicate-urls?hl=ko#redirects-method): 리디렉션 대상이 표준 URL이 되어야 하는 강력한 신호입니다.
-   [**`rel="canonical"` `link` 주석**](https://developers.google.com/search/docs/crawling-indexing/consolidate-duplicate-urls?hl=ko#rel-canonical-link-method): 지정된 URL이 표준 URL이 되어야 하는 강력한 신호입니다.
-   [**사이트맵 포함**](https://developers.google.com/search/docs/crawling-indexing/consolidate-duplicate-urls?hl=ko#sitemap-method): 사이트맵에 포함된 URL이 표준이 되도록 하는 약한 신호입니다.

이러한 방법들은 중첩하여 사용할 수 있으므로 함께 사용하면 더 효과적이라는 점에 유의하세요. 즉, 두 가지 이상의 방법을 사용하면 검색 결과에 선호하는 표준 URL이 표시될 가능성이 높아집니다.

이러한 방법이 필수는 아니지만 활용하는 것이 좋습니다. 선호하는 표준 URL을 지정하지 않아도 사이트는 정상적으로 작동합니다. 표준 URL을 지정하지 않아도 [Google에서 어떤 버전의 URL이 Google 검색에서 사용자에게 표시하기에 가장 적합한 버전인지 식별](https://developers.google.com/search/docs/crawling-indexing/canonicalization?hl=ko#canonical-how)해 주기 때문입니다.

## 표준 URL을 지정해야 하는 이유

<iframe frameborder="0" allowfullscreen="" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share" referrerpolicy="strict-origin-when-cross-origin" width="640" height="360" src="https://www.youtube.com/embed/gEWkYTPSEjs?origin=https%3A%2F%2Fdevelopers.google.com&amp;autoplay&amp;controls&amp;embed_domain&amp;enablejsapi=1&amp;end&amp;hl&amp;showinfo&amp;start&amp;video-id=gEWkYTPSEjs&amp;widgetid=51&amp;forigin=https%3A%2F%2Fdevelopers.google.com%2Fsearch%2Fdocs%2Fcrawling-indexing%2Fconsolidate-duplicate-urls%3Fhl%3Dko&amp;aoriginsup=1&amp;gporigin=https%3A%2F%2Fwww.google.com%2F&amp;vf=1" id="widget52" data-gtm-yt-inspected-225073684_46="true" data-gtm-yt-inspected-183356566_95="true" data-gtm-yt-inspected-26="true" data-gtm-yt-inspected-45="true" data-gtm-yt-inspected-52="true" data-title="YouTube video player" title="Canonicalization: SEO Mythbusting"></iframe>

일반적인 경우라면 여러 URL 중에서 어떤 URL을 표준으로 표시할지 지정하지 않아도 괜찮습니다. 하지만 중복 페이지 또는 유사한 페이지가 여러 개 있다면 Google에 내가 선호하는 표준 페이지를 명시적으로 알리는 것이 좋은 몇 가지 이유가 있습니다.

-   **어떤 URL이 검색 결과에서 사람들에게 표시될지 지정합니다.** 사람들이 `https://example.com/dresses/cocktail?gclid=ABCD`보다는 `https://www.example.com/dresses/green/green-dress.html`을 통해 녹색 드레스 제품 페이지에 연결되도록 하고 싶을 수 있습니다.
-   **유사하거나 중복된 페이지와 관련된 신호를 통합합니다**. 이렇게 하면 검색엔진에서 자체적으로 갖고 있는 개별 URL의 신호(예: 검색엔진으로 연결되는 링크)를 선호하는 단일 URL로 쉽게 통합할 수 있습니다. 이는 다른 사이트에서 `https://example.com/dresses/cocktail?gclid=ABCD`로 연결되는 신호가 `https://www.example.com/dresses/green/green-dress.html`(표준으로 지정된 URL)로 연결되는 링크에 통합된다는 의미입니다.
-   **단일 콘텐츠와 관련된 측정항목의 추적을 단순화합니다**. 다양한 URL을 사용하는 경우 특정 콘텐츠와 관련해 통합된 측정항목을 얻기가 더 어렵습니다.
-   **중복 페이지에 크롤링 시간을 낭비하지 않도록 방지합니다.** Googlebot이 사이트를 최대한 활용하도록 하려면 같은 콘텐츠의 중복된 버전을 모두 크롤링하는 데 시간을 낭비하게 하기보다는 사이트의 신규(또는 업데이트된) 페이지를 크롤링하게 하는 것이 좋습니다.

## 권장사항

어떤 표준화 방법을 사용하건 간에 다음 권장사항을 준수하는 것이 좋습니다.

-   표준화를 목적으로 robots.txt 파일을 사용하면 **안 됩니다**. Google은 robots.txt에서 허용되지 않는 URL의 색인을 콘텐츠 없이 생성할 수 있습니다.
-   표준화를 위해 URL 삭제 도구를 사용해서는 **안 됩니다**. 이 도구를 사용하면 Google 검색에서 _모든_ 버전의 URL을 숨깁니다.
-   다른 표준화 기술을 사용하여 서로 다른 URL을 같은 페이지의 표준 URL로 지정하면 **안 됩니다**. 예를 들어, 사이트맵에서 URL 하나를 지정하지 말고 `rel="canonical"`을 사용하여 같은 페이지에 다른 URL을 지정합니다.
-   [Google은 일반적으로 URL 프래그먼트를 지원하지 않으므로](https://developers.google.com/search/docs/crawling-indexing/url-structure?hl=ko#fragments) URL 프래그먼트를 표준으로 지정하지 **마세요**.
-   [`noindex`](https://developers.google.com/search/docs/crawling-indexing/block-indexing?hl=ko)를 사용하여 단일 사이트 내에서 표준 페이지가 선택되지 않도록 하면 페이지가 Google 검색에서 완전히 차단될 수 있으므로 **권장하지 않습니다**. `rel="canonical"` `link` 주석을 사용하는 것이 좋습니다.
-   [`hreflang` 요소](https://developers.google.com/search/docs/specialty/international/localized-versions?hl=ko)를 사용한다면 같은 언어로 표준 페이지를 지정하세요. 같은 언어의 표준 페이지가 존재하지 않는 경우 가장 유사한 언어로 된 표준 페이지를 지정하세요.
-   사이트 내에서 연결할 때는 중복 URL이 아닌 표준 URL에 연결하세요. 표준으로 간주하는 URL에 일관되게 연결하면 Google이 선호하는 페이지를 파악하는 데 도움이 됩니다.
-   JavaScript로 클라이언트 측 렌더링을 사용하는 경우 표준 URL에 관한 정보가 최대한 명확해야 합니다. 가장 좋은 방법은 HTML 소스 코드에서 표준 URL을 지정하고 JavaScript가 표준 링크 요소를 변경하지 않도록 하는 것입니다. HTML 소스 코드에서 표준 URL을 설정할 수 없는 경우 표준 URL을 제외하고 JavaScript로만 설정하세요. 이렇게 하면 표준 URL에 관한 정보가 최대한 명확해집니다.

## 표준화 방법 비교

다음 표에서는 여러 가지 표준화 방법을 비교하고, 다양한 시나리오에서 유지보수 및 효율성 측면의 장단점을 설명합니다.

| 방법 및 설명 | 방법 및 설명 |
|-------------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| [`rel="canonical" link` 요소](https://developers.google.com/search/docs/crawling-indexing/consolidate-duplicate-urls?hl=ko#rel-canonical-link-method) | 표준 페이지로 연결되는 모든 중복 페이지의 코드에 `<link>` 요소를 추가합니다.

**장점:**

-   무한히 많은 중복 페이지를 매핑할 수 있습니다.

**단점:**

-   용량이 큰 사이트 또는 URL이 자주 변경되는 사이트의 매핑을 유지하기가 복잡할 수 있습니다.
-   HTML 페이지에만 작동하며 PDF와 같은 파일에는 작동하지 않습니다. 이 경우 `rel="canonical"` HTTP 헤더를 사용할 수 있습니다. |
| [`rel="canonical"` HTTP 헤더](https://developers.google.com/search/docs/crawling-indexing/consolidate-duplicate-urls?hl=ko#rel-canonical-header-method) | 페이지 응답에 `rel="canonical"` 헤더를 전송합니다.

**장점:**

-   페이지 크기가 커지지 않습니다.
-   무한히 많은 중복 페이지를 매핑할 수 있습니다.

**단점:**

-   용량이 큰 사이트 또는 URL이 자주 변경되는 사이트의 매핑을 유지하기가 복잡할 수 있습니다. |
| [사이트맵](https://developers.google.com/search/docs/crawling-indexing/consolidate-duplicate-urls?hl=ko#sitemap-method) | 사이트맵에서 표준 페이지를 지정합니다.

**장점:**

-   특히 용량이 큰 사이트에서 쉽게 구현하고 관리할 수 있는 방법입니다.

**단점:**

-   Google에서 사이트맵에서 선언된 표준 페이지와 관련된 중복 페이지가 어떤 것인지 판단해야 합니다.
-   `rel="canonical"` 매핑 방법에 비해 Google에 덜 강력한 신호를 줍니다. |
| [리디렉션](https://developers.google.com/search/docs/crawling-indexing/consolidate-duplicate-urls?hl=ko#redirects-method) | 영구 리디렉션을 사용하여 Google에 리디렉션된 URL이 리디렉션 대상 URL보다 더 낮은 버전임을 알립니다. 이 방법은 중복 페이지를 더 이상 사용하지 않는 경우에만 사용하세요. |
| [AMP 변형](https://developers.google.com/search/docs/crawling-indexing/amp?hl=ko) | 변형 페이지 중 하나가 AMP 페이지인 경우 AMP 가이드라인에 따라 표준 페이지 및 AMP 변형 페이지를 표시합니다. |

## `rel="canonical"` `link` 주석 사용

Google에서는 [RFC 6596](https://www.rfc-editor.org/rfc/rfc6596)에 설명된 것과 같이 명시적인 `rel` canonical `link` 주석을 지원합니다. 페이지의 대체 버전을 제안하는 `rel="canonical"` 주석은 무시됩니다. 구체적으로는 `hreflang`가 있는 `rel="canonical"` 주석입니다. `lang`, `media`, `type` 속성은 표준화에 사용되지 않습니다. 대신 적절한 `link` 주석을 사용하여 페이지의 대체 버전을 지정하세요. 예를 들어 언어 및 국가 주석의 경우 `link` `rel="alternate"` [`hreflang`](https://developers.google.com/search/docs/specialty/international/localized-versions?hl=ko)입니다.

다음의 두 가지 방법으로 `rel="canonical"` `link` 주석을 제공할 수 있습니다.

-   [HTML 내의 `rel="canonical"` `link` 요소](https://developers.google.com/search/docs/crawling-indexing/consolidate-duplicate-urls?hl=ko#rel-canonical-link-method)
-   [`rel="canonical"` `link` HTTP 헤더.](https://developers.google.com/search/docs/crawling-indexing/consolidate-duplicate-urls?hl=ko#rel-canonical-header-method)

두 방법 중 하나를 선택한 다음 지속적으로 사용하는 것이 좋습니다. 두 방법을 동시에 사용하는 것도 지원되기는 하지만 오류가 발생하기 쉽습니다. 예를 들어 HTTP 헤더에 한 URL을 제공하고 `rel="canonical"` `link`에 다른 URL을 제공하는 경우 오류가 발생합니다.

### `rel="canonical"` `link` 요소

`rel="canonical"` `link` 요소(_표준 요소_라고도 함)는 HTML의 `head` 섹션에 사용되며, 페이지에 있는 콘텐츠를 대표하는 다른 페이지가 있음을 나타냅니다.

다양한 URL을 통해 이 콘텐츠에 액세스할 수 있으나, `https://example.com/dresses/green-dresses`를 표준 URL로 지정하려고 한다고 가정해 보겠습니다. 다음 단계를 사용해 이 URL이 표준 URL임을 나타내세요.

1.  `rel="canonical"` 속성이 있는 `<link>` 요소를 중복 페이지의 `<head>` 섹션에 추가하여 표준 페이지로 연결되도록 합니다. 예를 들면 다음과 같습니다.
    
    ```php-template
    <html>
    <head>
    <title>Explore the world of dresses</title>
    <link rel="canonical" href="https://example.com/dresses/green-dresses" />
    <!-- other elements -->
    </head>
    <!-- rest of the HTML -->
    ```
    
2.  표준 페이지에 별도의 URL에 있는 모바일 변형이 있는 경우 모바일 버전의 페이지를 가리키는 `rel="alternate"` `link` 요소를 해당 페이지에 추가합니다.
    
    ```php-template
    <html>
    <head>
    <title>Explore the world of dresses</title>
    <link rel="alternate" media="only screen and (max-width: 640px)"  href="https://m.example.com/dresses/green-dresses">
    <link rel="canonical" href="https://example.com/dresses/green-dresses" />
    <!-- other elements -->
    </head>
    <!-- rest of the HTML -->
    ```
    
3.  페이지에 적합한 [`hreflang`](https://developers.google.com/search/docs/specialty/international/localized-versions?hl=ko) 또는 기타 요소를 추가합니다.

`rel="canonical"` `link` 요소에는 상대 경로보다는 절대 경로를 사용하세요. 상대 경로도 Google에서 지원하지만 장기적으로 문제가 발생할 수 있으므로(예: 의도치 않게 테스트 사이트가 크롤링되도록 허용하는 경우) 권장되지 않습니다.

**좋은 예**: `https://www.example.com/dresses/green/green-dress.html`

**좋지 않은 예**: `/dresses/green/green-dress.html`

`rel="canonical"` `link element`는 HTML의 `<head>` 섹션에 포함되어 있는 경우에만 허용됩니다. 그러니 최소한 [`<head>` 섹션이 유효한 HTML](https://developers.google.com/search/docs/crawling-indexing/valid-page-metadata?hl=ko)인지 정도는 확인하는 것이 좋습니다.

JavaScript를 사용하여 `rel="canonical"` `link` 요소를 추가할 때는 [표준 링크 요소를 올바르게 삽입](https://developers.google.com/search/docs/crawling-indexing/javascript/javascript-seo-basics?hl=ko#properly-inject-canonical-links)해야 합니다.

서버 구성을 변경할 수 있다면 HTML 요소 대신 [RFC5988](https://www.rfc-editor.org/rfc/rfc5988.html#section-5.1)에 정의된 대로 `rel="canonical"` 타겟 속성이 있는 `link` [HTTP 응답 헤더](https://en.wikipedia.org/wiki/List_of_HTTP_header_fields)를 사용하여 Google 검색에서 지원되는 문서(예: PDF 파일 등 HTML이 아닌 문서)의 표준 URL을 표시할 수 있습니다.

Google은 웹 검색 결과에만 이 방법을 지원합니다.

각 자체 URL에 PDF나 Microsoft Word와 같은 여러 파일 형식으로 콘텐츠를 게시하는 경우 `rel="canonical"` HTTP 헤더를 반환하여 Googlebot에 HTML이 아닌 파일의 표준 URL을 알릴 수 있습니다. 예를 들어 `.docx` 버전의 PDF 버전을 표준 페이지로 나타내려면 콘텐츠의 `.docx` 버전에 다음 HTTP 헤더를 추가할 수 있습니다.

```python-repl
HTTP/1.1 200 OK
Content-Length: 19
...
Link: <https://www.example.com/downloads/white-paper.pdf>; rel="canonical"
...
```

`rel="canonical"` `link` 요소와 마찬가지로 `rel="canonical"` HTTP 헤더에는 절대 URL을 사용하세요.

## 사이트맵 사용

각 페이지의 표준 URL을 선택하고 이를 [사이트맵](https://developers.google.com/search/docs/crawling-indexing/sitemaps/overview?hl=ko)을 통해 제출합니다. 사이트맵에 명시된 모든 페이지는 표준 페이지로 제안됩니다. 중복 페이지가 있는 경우, Google이 콘텐츠의 유사성을 기준으로 어떤 페이지가 중복인지 판단합니다.

사이트맵에서 선호하는 표준 URL을 제공하면 대규모 사이트의 표준 URL을 간편하게 정의할 수 있습니다. 사이트맵을 사용하면 사이트에서 가장 중요하게 여기는 페이지가 무엇인지 Google에 알릴 수 있습니다.

## 리디렉션 사용

기존의 중복 페이지를 폐기하고 싶은 경우 이 방법을 사용하세요. 모든 [영구 리디렉션 방법](https://developers.google.com/search/docs/crawling-indexing/301-redirects?hl=ko)이 Google 검색에 미치는 영향은 동일합니다. 그러나 검색엔진에서 각각 다른 리디렉션 방법을 알아차리는 데 걸리는 시간이 서로 다를 수 있습니다.

가장 빠르게 효과를 내려면 HTTP(_서버 측_이라고도 함) 리디렉션을 사용하세요.

페이지를 다음과 같은 여러 경로로 방문할 수 있다고 가정해 보겠습니다.

-   `https://example.com/home`
-   `https://home.example.com`
-   `https://www.example.com`

URL 중 하나를 표준 URL로 선택하고 리디렉션을 사용하여 다른 URL에서 원하는 URL로 트래픽을 보냅니다.

## 기타 신호

Google은 명시적으로 제공되는 방법 외에도 일반적으로 사이트 설정을 기반으로 하는 표준화 신호 집합(HTTP보다 HTTPS 및 `hreflang` 클러스터의 URL 선호)을 사용합니다.

### 표준 URL에는 HTTP보다 HTTPS가 선호됨

Google은 다음과 같은 문제나 충돌하는 신호가 있는 경우가 아니라면 HTTP 페이지보다는 HTTPS 페이지를 표준 페이지로 선호합니다.

-   HTTPS 페이지에 잘못된 SSL 인증서가 있습니다.
-   HTTPS 페이지에 보안이 취약한 종속 항목(이미지 제외)이 있습니다.
-   HTTPS 페이지에서 사용자를 HTTP 페이지로 또는 HTTP 페이지를 통해 리디렉션합니다.
-   HTTPS 페이지에 HTTP 페이지로 연결되는 `rel="canonical"` `link`가 있습니다.

Google 시스템은 기본적으로 HTTP 페이지보다 HTTPS 페이지를 선호하지만, 다음 작업으로 이러한 선호도를 확실히 강화할 수 있습니다.

-   HTTP 페이지에서 HTTPS 페이지로 연결되는 리디렉션 추가
-   HTTP 페이지의 `rel="canonical"` `link`를 HTTPS 페이지에 추가
-   [HSTS](https://en.wikipedia.org/wiki/HTTP_Strict_Transport_Security) 구현

Google에서 HTTP 페이지를 표준 페이지로 잘못 사용하지 못하도록 하려면 다음 사례를 **방지**하세요.

-   잘못된 TLS/SSL 인증서 및 HTTPS에서 HTTP로의 리디렉션을 피합니다. 이러한 요소로 인해 Google이 HTTP를 매우 강력하게 선호하게 되기 때문에 HSTS를 구현해도 이렇게 강력한 선호도를 재정의할 수 없습니다.
-   사이트맵에 페이지의 HTTPS 버전이 아닌 HTTP 버전이나 [`hreflang` 주석](https://developers.google.com/search/docs/specialty/international/localized-versions?hl=ko)을 포함하지 마세요.
-   잘못된 호스트 변형과 관련된 SSL/TLS 인증서를 구현하지 마세요 (예: `example.com`에 `subdomain.example.com`의 인증서를 게시). 인증서는 전체 사이트 URL과 일치하거나 한 도메인의 여러 하위 도메인에 사용될 수 있는 와일드 카드 인증서여야 합니다.

### `hreflang` 클러스터의 URL 선호

Google에서는 사이트 현지화 작업을 도울 수 있도록 표준화 과정에서 `hreflang` 클러스터에 포함된 URL을 선호합니다. 예를 들어 `hreflang` 주석을 통해 `https://example.com/de-de/cats`와 `https://example.com/de-ch/cats`는 서로 가리키지만 `https://example.com/de-at/cats`는 가리키지 않는다면 `hreflang` 클러스터에 표시되지 않는 `/de-at/` 페이지가 아닌 `de-de` 및 `de-ch` 페이지가 표준으로 선호됩니다.

[표준화 문제 해결](https://developers.google.com/search/docs/crawling-indexing/canonicalization-troubleshooting?hl=ko)에 관해 자세히 알아보기