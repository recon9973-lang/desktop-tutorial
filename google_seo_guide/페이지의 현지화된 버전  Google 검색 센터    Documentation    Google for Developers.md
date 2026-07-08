서로 다른 언어 또는 지역별로 여러 버전의 페이지가 있는 경우 Google에 여러 페이지 버전을 알려주세요. 그렇게 하면 Google 검색에서 언어나 지역별로 가장 적절한 버전의 페이지로 사용자를 연결하는 데 도움이 됩니다.

별도의 조치를 취하지 않아도 Google에서 페이지의 다른 언어 버전을 찾을 수 있지만, 일반적으로는 언어별 또는 지역별 페이지를 명시적으로 지정하는 것이 좋습니다.

다음은 대체 페이지 지정이 권장되는 몇 가지 예입니다.

-   **콘텐츠 본문은 단일 언어로 유지**하고 탐색 및 바닥글과 같은 **템플릿만 번역**하는 경우입니다. 일반적으로 포럼과 같이 사용자 제작 콘텐츠가 포함된 페이지가 여기에 해당됩니다.
-   단일 언어로 된 유사한 콘텐츠에 **약간의 지역적인 차이**가 있는 경우입니다. 예를 들어 미국, 영국, 아일랜드를 타겟팅하는 영어로 된 콘텐츠가 여기에 해당됩니다.
-   사이트 콘텐츠가 **여러 언어로 완전히 번역**되어 있는 경우입니다. 예를 들어 페이지마다 독일어와 영어 버전이 모두 있는 경우입니다.

페이지의 현지화된 버전은 페이지의 주요 콘텐츠가 번역되지 않은 상태인 경우에만 [중복](https://developers.google.com/search/docs/crawling-indexing/consolidate-duplicate-urls?hl=ko)으로 간주됩니다.

<iframe frameborder="0" allowfullscreen="" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share" referrerpolicy="strict-origin-when-cross-origin" width="640" height="360" src="https://www.youtube.com/embed/8ce9jv91beQ?origin=https%3A%2F%2Fdevelopers.google.com&amp;autoplay&amp;controls&amp;embed_domain&amp;enablejsapi=1&amp;end&amp;hl&amp;showinfo&amp;start&amp;video-id=8ce9jv91beQ&amp;widgetid=131&amp;forigin=https%3A%2F%2Fdevelopers.google.com%2Fsearch%2Fdocs%2Fspecialty%2Finternational%2Flocalized-versions%3Fhl%3Dko&amp;aoriginsup=1&amp;gporigin=https%3A%2F%2Fdevelopers.google.com%2Fsearch%2Fdocs%2Fcrawling-indexing%2Famp%2Fabout-amp%3Fhl%3Dko&amp;vf=1" id="widget132" data-title="YouTube video player" title="Expanding your site to more languages"></iframe>

## 대체 페이지를 지정하는 방법

Google에 페이지의 여러 언어/지역 버전을 명시하는 방법에는 세 가지가 있습니다.

-   [HTML](https://developers.google.com/search/docs/specialty/international/localized-versions?hl=ko#html)
-   [HTTP 헤더](https://developers.google.com/search/docs/specialty/international/localized-versions?hl=ko#http)
-   [사이트맵](https://developers.google.com/search/docs/specialty/international/localized-versions?hl=ko#sitemap)

세 가지 방법은 Google의 관점에서 보았을 때 동일하므로 사이트에 가장 편리한 방법을 선택하면 됩니다. 세 가지 방법을 동시에 사용하는 것도 가능하지만 Google 검색에는 도움이 되지 않습니다. 실제로 하나만 선택하는 대신 세 가지 구현을 관리하는 것이 훨씬 더 어려울 수 있습니다.

`hreflang` 속성을 사용하여 Google에 콘텐츠 버전에 관해 알려 주세요. 이렇게 하면 Google에서는 그러한 페이지가 동일한 콘텐츠의 현지화된 버전임을 알 수 있습니다. Google에서는 페이지의 언어를 감지하는 데 `hreflang` 또는 HTML `lang` 속성을 사용하지 않습니다. 대신 알고리즘을 사용하여 언어를 파악합니다.

### 언어 버전을 명시하는 모든 방법에 관한 가이드라인

-   각 언어 버전은 해당 언어**뿐만 아니라** 다른 모든 언어 버전을 나열해야 합니다.
-   대체 URL은 다음과 같이 전송 방법(http/https)을 포함하여 정규화되어야 합니다.  
    `//example.com/foo` 또는 `/foo`가 **아닌** `https://example.com/foo`
-   대체 URL이 같은 도메인에 있을 필요는 없습니다.
-   동일한 언어를 사용하지만 지역이 다른 사용자를 타겟팅하는 여러 개의 대체 URL이 있는 경우, 지정되지 않은 지역에 있는 해당 언어 사용자를 위한 포괄 URL도 함께 제공하는 것이 좋습니다. 예를 들어 아일랜드(`en-ie`), 캐나다(`en-ca`), 오스트레일리아(`en-au`)에 거주하는 영어 사용자를 위한 특정 URL이 있더라도 미국, 영국 및 기타 모든 영어권의 검색 사용자를 위한 일반 영어(`en`) 페이지를 제공해야 합니다. 이러한 페이지를 특정 페이지 중 하나로 선택할 수도 있습니다.
-   두 페이지가 서로를 가리키지 않는 경우 태그가 무시됩니다. 이는 다른 사이트에 있는 사용자가 페이지의 대체 버전으로 이름을 지정하여 태그를 임의로 만들 수 없도록 하기 위함입니다.
-   모든 언어마다 완전한 양방향 링크 세트를 유지하기 어려운 경우 일부 페이지에서 특정 언어를 제외할 수 있습니다. Google에서는 계속해서 서로를 가리키는 페이지를 처리합니다. 그러나 새로 확장된 언어 페이지는 기본/주요 언어의 페이지와 양방향으로 연결해야 합니다. 예를 들어 원래 만든 사이트가 `.fr`로 된 URL의 프랑스어 사이트인 경우 새로운 멕시코(`.mx`) 및 스페인(`.es`) 페이지를 인지도가 높은 `.fr`과 양방향으로 연결하는 것이 새 스페인어 버전 페이지( `.mx`와 `.es`)끼리 양방향으로 연결하는 것보다 좋습니다.
-   특히 언어/국가 선택기 또는 자동으로 리디렉션되는 홈페이지의 경우 다른 페이지와 연결되지 않은 언어를 위한 대체 페이지를 추가하는 것이 좋습니다. [`x-default` 값](https://developers.google.com/search/docs/specialty/international/localized-versions?hl=ko#xdefault)을 사용합니다.  
    `<link rel="alternate" href="https://example.com/" hreflang="x-default" />`

### HTML 태그

페이지 헤더에 `<link rel="alternate" hreflang="lang_code"... >` 요소를 추가하여 페이지의 언어 및 지역 버전을 Google에 모두 알립니다. 이 방법은 사이트맵이 없거나 사이트에 HTTP 응답 헤더를 지정할 수 없는 경우 유용합니다.

각 페이지 버전의 경우 `<head>` 요소에 일련의 `<link>` 요소를 포함합니다. **기본 페이지를 포함**하여 페이지 버전별로 링크를 하나씩 넣습니다. 링크 집합은 페이지의 모든 버전에서 동일합니다. [추가 가이드라인을 참고하세요](https://developers.google.com/search/docs/specialty/international/localized-versions?hl=ko#all-method-guidelines).

다음은 각 `link` 요소의 구문입니다.

```bash
<link rel="alternate" hreflang="lang_code" href="url_of_page" />
```

| 구문 | 구문 |
|-----------|---------------------------------------------------------------------------------------------|
| `lang_code` | 페이지의 이 버전에서 타겟팅하는 [지원되는 언어/지역 코드](https://developers.google.com/search/docs/specialty/international/localized-versions?hl=ko#language-codes) 또는 페이지의 `hreflang` 태그에 의해 명시적으로 나열되지 않은 모든 언어에 해당하는 `x-default` |
| `url_of_page` | 이 페이지의 지정된 언어/지역별 버전의 정규화된 URL |

`<link>` 태그는 HTML의 [제대로 형식이 지정된 `<head>` 섹션](https://developers.google.com/search/docs/crawling-indexing/valid-page-metadata?hl=ko) 안에 있어야 합니다. 확실하지 않다면 렌더링된 페이지의 코드를 [HTML 검사기](https://validator.w3.org/)에 붙여넣어 링크가 `<head>` 요소 내에 있는지 확인하세요. 또한 문서 대체 표현을 위해 `link` 태그를 결합하지 마세요. 예를 들어 `hreflang` 주석과 코드를 단일 `<link>` 태그의 `media`와 같은 다른 속성과 결합하지 마세요.

#### 예

Example Widgets, Inc는 미국, 영국, 독일의 사용자에게 웹사이트를 제공합니다. 다음 URL에서는 지역적인 변형이 있을 뿐 실제로 동일한 콘텐츠를 제공합니다.

| 지역적인 변형이 있는 URL | 지역적인 변형이 있는 URL |
|-------------------------------------|-------------------------------------------------------------|
| `https://en.example.com/page.html` | 일반 영어로 된 홈페이지이며 미국에서 발송되는 해외 배송 요금의 정보가 포함되어 있습니다. |
| `https://en-gb.example.com/page.html` | 영국 파운드로 가격을 표시하는 영국 홈페이지입니다. |
| `https://en-us.example.com/page.html` | 미국 달러로 가격을 표시하는 미국 홈페이지입니다. |
| `https://de.example.com/page.html` | 독일어 홈페이지입니다. |
| `https://www.example.com/` | 특정 언어/지역을 타겟팅하지 않는 기본 페이지로서 선택기를 통해 사용자가 언어/지역을 선택할 수 있습니다. |

Google에서는 페이지의 타겟층을 결정하는 데 이러한 URL의 언어별 하위 도메인(`en`, `en-gb`, `en-us`, `de`)을 사용하지 않으므로, 타겟 대상을 명시적으로 매핑해야 합니다.

다음은 [지역적인 변형이 있는 URL 테이블](https://developers.google.com/search/docs/specialty/international/localized-versions?hl=ko#regional-variations-table)에 나열된 모든 페이지의 `<head>` 섹션에 있을 수 있는 HTML입니다. 이렇게 하면 미국, 영국, 일반 영어 사용자 및 독일어 사용자는 현지화된 페이지로 연결되며 기타 모든 사용자는 일반 홈페이지로 연결됩니다. Google 검색에서는 사용자의 브라우저 설정에 따라 사용자에게 적절한 결과를 표시합니다.

```php-template
<head>
 <title>Widgets, Inc</title>
  <link rel="alternate" hreflang="en-gb"
       href="https://en-gb.example.com/page.html" />
  <link rel="alternate" hreflang="en-us"
       href="https://en-us.example.com/page.html" />
  <link rel="alternate" hreflang="en"
       href="https://en.example.com/page.html" />
  <link rel="alternate" hreflang="de"
       href="https://de.example.com/page.html" />
 <link rel="alternate" hreflang="x-default"
       href="https://www.example.com/" />
</head>
```

### HTTP 헤더

페이지의 GET 응답을 통해 [HTTP 헤더](https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers)를 반환하여 Google에 페이지의 모든 언어 및 지역 버전을 알릴 수 있습니다. PDF와 같이 HTML이 아닌 파일에 유용합니다.

다음은 헤더의 형식입니다.

```vbnet
Link: <url1>; rel="alternate"; hreflang="lang_code_1", <url2>; rel="alternate"; hreflang="lang_code_2", ...
```

| 구문 | 구문 |
|-----------|--------------------------------------------------------------------------------------------------------------|
| `<url_x>` | 연결된 `hreflang` 속성에 할당된 언어 문자열에 해당하는 대체 페이지의 정규화된 URL. URL은 `<` 및 `>` 표시로 둘러싸여 있어야 합니다. **예:** `<https://www.google.com>` |
| `lang_code_x` | 페이지의 이 버전에서 타겟팅하는 [지원되는 언어/지역 코드](https://developers.google.com/search/docs/specialty/international/localized-versions?hl=ko#language-codes) 또는 페이지의 `hreflang` 태그에 의해 명시적으로 나열되지 않은 모든 언어에 해당하는 `x-default`. |

**요청된 버전을 포함**하여 페이지의 모든 버전에 `<url>`, `rel="alternate"` 및 `hreflang` 값 집합을 지정해야 하며, 다음 예처럼 쉼표로 구분해야 합니다. 페이지의 모든 버전에서 반환되는 `Link:` 헤더는 동일합니다. [추가 가이드라인을 참고하세요.](https://developers.google.com/search/docs/specialty/international/localized-versions?hl=ko#all-method-guidelines)

#### 예

다음은 영어 사용자, 스위스의 독일어 사용자, 기타 모든 독일어 사용자를 위한 3가지 버전의 PDF 파일이 있는 사이트에서 반환된 `Link:` 헤더의 예입니다.

```bash
Link: <https://example.com/file.pdf>; rel="alternate"; hreflang="en",
      <https://de-ch.example.com/file.pdf>; rel="alternate"; hreflang="de-ch",
      <https://de.example.com/file.pdf>; rel="alternate"; hreflang="de"
```

### 사이트맵

[XML 사이트맵](https://developers.google.com/search/docs/crawling-indexing/sitemaps/overview?hl=ko)을 사용하여 각 URL의 언어 및 지역 버전을 Google에 모두 알릴 수 있습니다. 이렇게 하려면 단일 URL을 지정하는 `<loc>` 요소와 함께 페이지 자체를 포함해 페이지의 모든 언어/지역 버전을 나열하는 하위 `<xhtml:link>` 항목을 추가해야 합니다. 따라서 페이지에 3가지 버전이 있는 경우 사이트맵에 각 버전의 URL 항목이 포함되며 이 항목마다 3개의 동일한 하위 항목이 추가됩니다.

**사이트맵 규칙:**

-   xhtml 네임스페이스를 다음과 같이 지정합니다.
    
    ```vbnet
    xmlns:xhtml="http://www.w3.org/1999/xhtml"
    ```
    
-   다른 사이트맵에서와 마찬가지로 각 URL에 별도의 `<url>` 요소를 만듭니다.
-   각 `<url>` 요소는 페이지 URL을 나타내는 `<loc>` 하위 요소를 포함해야 합니다.
-   각 `<url>` 요소에는 **페이지 자체를 포함해** 페이지의 모든 대체 버전을 나열하는 하위 요소 `<xhtml:link rel="alternate" hreflang="[supported_language-code](https://developers.google.com/search/docs/specialty/international/localized-versions?hl=ko#language-codes)">`가 있어야 합니다. 이러한 하위 `<xhtml:link>` 요소의 순서는 중요하지 않지만, 오류가 있는지 쉽게 확인할 수 있도록 동일한 순서를 유지하는 것이 좋습니다. 하위 요소는 사이트맵의 URL 한도에 포함되지 않습니다.
-   사이트 맵을 적용할 수 있는 사이트의 디렉터리에 사이트 맵을 업로드하세요. 사이트맵은 사이트맵이 호스팅되는 디렉터리의 하위 요소 URL만 포함할 수 있습니다.
-   [사이트맵 문서](https://developers.google.com/search/docs/crawling-indexing/sitemaps/build-sitemap?hl=ko)는 사이트맵 확장 프로그램에도 적용됩니다. [일반 사이트맵](https://developers.google.com/search/docs/crawling-indexing/sitemaps/build-sitemap?hl=ko#general-guidelines) 가이드라인을 준수하시기 바랍니다.
-   [추가 가이드라인을 참고하세요.](https://developers.google.com/search/docs/specialty/international/localized-versions?hl=ko#all-method-guidelines)

#### 예

다음은 전 세계 영어 사용자를 타겟팅하는 영어 페이지와 이 페이지에 상응하는 전 세계 독일어 사용자 및 스위스 내 독일어 사용자를 타겟팅하는 페이지 버전입니다. 다음은 사이트에 있는 모든 URL입니다.

-   영어 사용자를 타겟팅하는 `www.example.com/english/page.html`
-   독일어 사용자를 타겟팅하는 `www.example.de/deutsch/page.html`
-   스위스에 있는 독일어 사용자를 타겟팅하는 `www.example.de/schweiz-deutsch/page.html`

다음은 위에 나열된 페이지 3개의 사이트맵입니다.

```xml
<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"
  xmlns:xhtml="http://www.w3.org/1999/xhtml">
  <url>
    <loc>https://www.example.com/english/page.html</loc>
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
  <url>
    <loc>https://www.example.de/deutsch/page.html</loc>
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
  <url>
    <loc>https://www.example.de/schweiz-deutsch/page.html</loc>
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
</urlset>
```

## 지원되는 언어 및 지역 코드

`hreflang` 속성의 값은 대시로 구분된 1개 또는 2개(선택사항)의 값으로 구성됩니다. 예: `en-US` `hreflang` 속성의 첫 번째 코드는 언어 코드([ISO 639-1](https://en.wikipedia.org/wiki/List_of_ISO_639-1_codes) 형식)이고 이어지는 두 번째 코드(선택사항)는 대체 URL의 지역 코드([ISO 3166-1 Alpha 2](https://en.wikipedia.org/wiki/ISO_3166-1_alpha-2) 형식)를 나타냅니다. ISO 639-1에 나열된 언어 코드와 ISO 3166-1 Alpha 2에 나열된 지역 코드만 지원됩니다. 이러한 표준에 나열되지 않은 다른 코드(예: es-419)는 지원되지 않습니다.

벨기에에서 다른 언어 사용자를 타겟팅하려면 다음과 같은 언어 및 지역 코드를 사용할 수 있습니다.

-   **좋음(벨기에에 있는 사용자를 위한 독일어)**: `de-be`
-   **좋음(벨기에에 있는 사용자를 위한 네덜란드어)**: `nl-be`
-   **좋음(벨기에에 있는 사용자를 위한 프랑스어)**: `fr-be`
-   **첫 번째 코드가 언어용이므로 잘못됨(`be`는 벨라루스어 코드임)**: `be`

라벨 지정을 단순화하기 위해 언어 코드만 지정할 수 있습니다. 예를 들면 다음과 같습니다.

-   `de`: 지역과는 무관한 독일어 콘텐츠
-   `en-GB`: 영국 사용자를 위한 영어 콘텐츠
-   `de-ES`: 스페인 사용자를 위한 독일어 콘텐츠

**언어 스크립트 변형의 경우** 국가에 따라 적합한 스크립트가 파생됩니다. 예를 들어 타이완에 있는 사용자를 위해 `zh-TW`를 사용하면 언어 스크립트가 자동으로 파생됩니다(이 예에서는 중국어 번체). 또한 다음과 같이 [ISO 15924](https://unicode.org/iso15924/iso15924-codes.html)를 사용하여 스크립트 자체를 명시적으로 지정할 수 있습니다.

-   `zh-Hant`: 중국어(번체)
-   `zh-Hans`: 중국어(간체)

다른 언어 코드와 마찬가지로 선택사항인 지역을 지정할 수도 있습니다. 예를 들어 `zh-Hans-US`를 사용하여 미국 사용자의 중국어(간체)를 지정할 수 있습니다.

### 일치하지 않는 언어에 `x-default` 값 사용

사용자의 브라우저 설정과 일치하는 언어/지역이 없는 경우 예약된 값 `x-default`가 사용됩니다. 이 값은 언어 설정이 사이트의 현지화 버전과 일치하지 않는 사용자의 대체 페이지를 지정하는 데 권장됩니다. 모든 페이지에 `x-default` 값을 사용할 수 있지만, 이 값은 언어 선택기 페이지용으로 설계되었으므로 해당 페이지에서 가장 원활하게 작동합니다.

`x-default` 값의 언어 코드를 지정하지 않아도 됩니다. 페이지가 사이트에서 언어 설정이 일치하지 않는 사용자에게 타겟팅되어 있으므로 페이지의 언어는 관련이 없습니다.

사이트에서 사용자의 언어를 지원하지 않는 경우에 `hreflang="x-default"` 주석을 구현하려면 `link` 태그를 기존 `hreflang` 주석에 추가하고 `href` 속성을 사용자가 방문하게 할 URL로 설정합니다. HTML 구현 예시는 다음과 같습니다.

```bash
<link rel="alternate" href="https://example.com/en-gb" hreflang="en-gb" />
<link rel="alternate" href="https://example.com/en-us" hreflang="en-us" />
<link rel="alternate" href="https://example.com/en-au" hreflang="en-au" />
<link rel="alternate" href="https://example.com/country-selector" hreflang="x-default" />
```

## 문제해결

### 흔히 발생하는 실수

다음은 `hreflang` 사용 시 가장 자주 발생하는 실수입니다.

-   **반환 링크 누락**: 페이지 X가 페이지 Y로 연결되는 경우 반대로 페이지 Y에서 페이지 X로도 연결되어야 합니다. `hreflang` 사이트설정을 사용하는 모든 페이지의 연결이 이렇게 되어 있지 않으면 사이트설정이 무시되거나 잘못 해석될 수 있습니다. 예를 들어 `https://de.example.com/index.html`의 다음 링크를 가정해 보겠습니다.
    
    ```bash
    <link rel="alternate" hreflang="en-gb" href="https://en-gb.example.com/index.html" />
    ```
    
    콘텐츠의 `de` 버전을 다시 가리키는 `https://en-gb.example.com/index.html`의 `hreflang` 링크도 있어야 합니다.
    
    ```bash
    <link rel="alternate" hreflang="de" href="https://de.example.com/index.html" />
    ```
    
-   **잘못된 언어 코드**: 사용하는 모든 언어 코드가 언어(ISO 639-1 형식)를 지정하며 필요시 대체 URL의 지역(ISO 3166-1 Alpha 2 형식)을 지정하는지 확인하세요. 지역만 지정하면 유효하지 않습니다.
-   **잘못된 지역 코드**: 식별하려는 지역에 공식적으로 할당된 코드 요소([ISO 3166-1 Alpha 2 형식](https://en.wikipedia.org/wiki/ISO_3166-1_alpha-2))를 사용하고 있는지 확인하세요. 다른 용도로 예약된 것으로 표시된 코드를 사용하면 Google 검색에서 주석의 해당 부분을 무시합니다. 예를 들어 `hreflang` 주석에서 `EU`나 `UN`, `UK`를 사용해도 Google 검색에 영향을 미치지 않습니다.

### `hreflang` 오류 디버깅

`hreflang` 주석을 디버그하는 데 사용할 수 있는 다양한 서드 파티 도구가 있습니다. 다음은 몇 가지 자주 사용되는 도구입니다. 이 도구는 Google에서 관리하거나 검사하지 않습니다.

-   [Aleyda Solis의 `hreflang` 태그 생성기](https://www.aleydasolis.com/english/international-seo-tools/hreflang-tags-generator/) - `hreflang` 태그 생성 또는 수정
-   [Merkle 검색엔진 최적화 `hreflang` 태그 테스트 도구](https://technicalseo.com/seo-tools/hreflang/) 단일 라이브 페이지에서 `hreflang` 태그 유효성 검사