Google 검색결과에 페이지가 표시될 때 그 페이지의 출처에 해당하는 사이트의 이름이 표시됩니다. 이를 사이트 이름이라고 합니다. 참고로, 사이트 이름은 페이지별 [제목 링크](https://developers.google.com/search/docs/appearance/title-link?hl=ko)와는 다릅니다(제목 링크는 각 웹페이지에만 적용되는 반면, 사이트 이름은 전체 사이트에 적용됨).

사이트 이름 부분 주위에 강조표시된 상자가 있는 Google 검색 텍스트 검색 결과의 삽화

Burnt Toast

[팬을 사용해 토스트 만드는 방법](https://wikipedia.org/wiki/Toast_(food))

## 기능 제공 여부

사이트 이름은 모바일과 데스크톱 모두에서 Google 검색이 서비스되는 모든 언어로 사용할 수 있습니다. 도메인 수준 및 하위 도메인 수준에는 사이트 이름이 표시될 수도 있습니다. 자세한 내용은 [기술 가이드라인](https://developers.google.com/search/docs/appearance/site-names?hl=ko#technical-guidelines)을 참고하세요.

## Google 검색에서 사이트 이름이 생성되는 방식

Google 검색결과 페이지에서 Google이 사이트 이름을 생성하는 방식은 완전히 자동화되어 있으며 사이트 홈페이지의 콘텐츠와 웹에 표시되는 페이지 콘텐츠 참조 두 가지를 모두 고려합니다. Google 검색에서 사이트 이름의 목적은 각 결과의 소스를 가장 잘 표현하고 설명하는 것입니다.

사이트 이름 환경설정을 표시하려면 홈페이지에 [구조화된 `WebSite` 데이터](https://developers.google.com/search/docs/appearance/site-names?hl=ko#website)를 추가하세요. 사이트 이름 시스템은 `og:site_name` 콘텐츠, `<title>`, 제목 요소, 홈페이지에 있는 다른 텍스트도 고려합니다. 하지만 환경설정을 지정하려면 구조화된 `WebSite` 데이터가 가장 중요합니다.

자동으로 선택된 사이트 이름을 수동으로 변경할 수는 없습니다. 그러나 기본 환경설정이 선택되어 있지 않다면 Google 자동화 시스템에서 고려해 볼 만한 [대안을 표시](https://developers.google.com/search/docs/appearance/site-names?hl=ko#alternative)할 수 있습니다.

## 사이트 이름 선택하기

-   사이트의 성격을 정확하게 반영하고 사용자에게 혼란을 야기하지 않는 **고유한 이름을 선택**하세요. 선택한 이름은 [Google 검색 콘텐츠 정책](https://support.google.com/websearch/answer/10622781?hl=ko)을 준수해야 합니다.
-   **일반적으로 알려진 간결한 이름**을 사용하세요(예: 'Google, Inc' 대신 'Google' 사용). 사이트 이름의 길이에는 제한이 없지만 사이트 이름이 길면 일부 기기에서는 잘려서 표시될 수 있습니다.
-   **일반적인 이름은 사용하지 마세요**. 굉장히 널리 알려진 브랜드 이름이 아니고, '아이오와 주 최고의 치과 의사'와 같은 일반적인 이름이라면 Google 시스템에서 선택될 가능성이 작습니다.
-   **홈페이지에서 사이트 이름을 일관되게 사용**하세요. 구조화된 데이터에서 사이트 이름으로 사용하는 이름은 Google 시스템에서 고려하는 홈페이지의 [다른 소스](https://developers.google.com/search/docs/appearance/site-names?hl=ko#sources)에서 사이트를 참조할 때 사용하는 항목과 일치해야 합니다.
-   **대신 사용할 수 있는 이름을 입력하세요**. Google의 사이트 이름 시스템은 사용자가 원하는 사이트 이름을 사용하려고 합니다. 그러나 경우에 따라 해당 이름을 사용하지 못할 때도 있습니다. 예를 들어 Google 시스템에서는 본질적으로 광범위한 두 개의 서로 다른 사이트에 동일한 사이트 이름을 사용하지 않습니다. 그리고 Google 시스템에서 어떤 사이트가 전체 이름이 아닌 약어로 더 많이 알려져 있다고 판단할 때도 있습니다. 이때 `alternateName` 속성을 사용하여 대체 이름을 제공하면 Google 시스템에서 사용자의 기본 옵션을 사용할 수 없을 경우 다른 옵션을 고려합니다.

## 구조화된 데이터를 사용해 사이트 이름을 추가하는 방법

<iframe frameborder="0" allowfullscreen="" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share" referrerpolicy="strict-origin-when-cross-origin" width="640" height="360" src="https://www.youtube.com/embed/DPJ0AzJSlFE?origin=https%3A%2F%2Fdevelopers.google.com&amp;autoplay&amp;controls&amp;embed_domain&amp;enablejsapi=1&amp;end&amp;hl&amp;showinfo&amp;start&amp;video-id=DPJ0AzJSlFE&amp;widgetid=3&amp;forigin=https%3A%2F%2Fdevelopers.google.com%2Fsearch%2Fdocs%2Fappearance%2Fsite-names%3Fhl%3Dko&amp;aoriginsup=1&amp;gporigin=https%3A%2F%2Fdevelopers.google.com%2Fsearch%2Fdocs%2Fcrawling-indexing%2Famp%2Fabout-amp%3Fhl%3Dko&amp;vf=1" id="widget4" data-title="How to modify your site name in Google Search"></iframe>

구조화된 데이터는 페이지 정보를 제공하고 페이지 콘텐츠를 분류하기 위한 표준화된 형식입니다. 구조화된 데이터를 처음 사용한다면 [구조화된 데이터의 작동 방식](https://developers.google.com/search/docs/appearance/structured-data/intro-structured-data?hl=ko)을 자세히 알아보세요.

이 섹션에서는 기술 가이드라인, 필수 속성, 구조화된 사이트 이름 데이터를 추가하고 테스트하는 방법을 설명합니다.

### 가이드라인 따르기

Google에서 사이트 이름을 더 잘 파악하도록 하려면 [검색 Essentials](https://developers.google.com/search/docs/essentials?hl=ko), [구조화된 데이터 일반 가이드라인](https://developers.google.com/search/docs/appearance/structured-data/sd-policies?hl=ko), [사이트 이름 선택하기](https://developers.google.com/search/docs/appearance/site-names?hl=ko#choosing-site-name) 가이드라인과 함께 다음의 기술 가이드라인을 따르세요.

#### 기술 가이드라인

-   **사이트당 이름 1개:** 현재 Google 검색에서는 도메인 또는 하위 도메인으로 정의되는 _사이트_당 하나의 사이트 이름만 지원합니다. Google 검색에서는 하위 디렉터리 수준의 사이트 이름을 지원하지 않습니다. 일반적으로 `www` 또는 `m`로 시작하는 하위 도메인 이름은 동일한 것으로 간주됩니다.  
    **지원됨**: `https://example.com`(도메인 수준의 홈페이지)  
    **지원됨**: `https://www.example.com`(도메인 수준 홈페이지로도 간주됨)  
    **지원됨**: `https://m.example.com`(도메인 수준 홈페이지로도 간주됨)  
    **지원됨**: `https://news.example.com`(하위 도메인 수준의 홈페이지)  
    **지원되지 않음**: `https://example.com/news`(하위 디렉터리 수준의 홈페이지)  
    
-   **구조화된 데이터는 사이트의 홈페이지에 있어야 함:** [구조화된 `WebSite` 데이터](https://developers.google.com/search/docs/appearance/site-names?hl=ko#website)가 사이트의 홈페이지에 있어야 합니다. 홈페이지는 도메인 또는 하위 도메인 수준의 루트 URI를 의미합니다. 예를 들어 `https://example.com`은 도메인의 홈페이지이고 `https://example.com/de/index.html`은 홈페이지가 아닙니다.
-   **Google에서 홈페이지를 크롤링할 수 있어야 함:** 홈페이지가 [차단](https://developers.google.com/search/docs/crawling-indexing/control-what-you-share?hl=ko)되어 Google에서 콘텐츠에 액세스할 수 없는 경우 사이트 이름을 생성할 수 없습니다.
-   **홈페이지가 중복된 사이트:** 동일한 콘텐츠에 중복된 홈페이지가 있는 경우(예: 홈페이지의 HTTP 및 HTTPS 버전 또는 www가 있는 버전과 없는 버전) 표준 페이지뿐만 아니라 모든 중복 페이지에 동일한 구조화된 데이터를 사용하는지 확인하세요.
-   **사이트에 이미 `WebSite` 구조화된 데이터가 있다면** 사이트 이름 속성을 동일한 노드에 중첩해야 합니다. 즉, 가능하면 홈페이지에 구조화된 `WebSite` 데이터 블록을 추가로 만들지 마세요.

### 필수 사이트 이름 속성 추가하기

필수 속성을 JSON-LD, RDFa, 마이크로데이터 형식으로 웹사이트 홈페이지에 추가합니다. 사이트의 모든 페이지에 이 마크업을 포함할 필요는 없습니다. 이 마크업은 사이트의 홈페이지에만 추가하면 됩니다.

| 필수 속성 | 필수 속성 |
|-------|-----------------------------------------------------------------------------------------------------------------------|
| `name` | `[Text](https://schema.org/Text)`

웹사이트의 이름입니다. 웹사이트 이름은 [사이트 이름 선택 가이드라인](https://developers.google.com/search/docs/appearance/site-names?hl=ko#choosing-site-name)을 준수해야 합니다. |
| `url` | `[URL](https://schema.org/URL)`

사이트 홈페이지의 URL입니다. 사이트 도메인 또는 하위 도메인의 [표준](https://developers.google.com/search/docs/crawling-indexing/consolidate-duplicate-urls?hl=ko) 홈페이지로 설정합니다. 예를 들어 `https://example.com/` 또는 `https://news.example.com/`입니다. |

다음은 필수 입력란이 포함된 구조화된 `WebSite` 데이터의 예입니다.

[JSON-LD](https://developers.google.com/search/docs/appearance/site-names?hl=ko/#json-ld)[마이크로데이터](https://developers.google.com/search/docs/appearance/site-names?hl=ko/#마이크로데이터) 더보기

```php-template
<html>
  <head>
    <title>Example: A Site about Examples</title>
    <script type="application/ld+json">
    {
      "@context" : "https://schema.org",
      "@type" : "WebSite",
      "name" : "Example",
      "url" : "https://example.com/"
    }
  </script>
  </head>
  <body>
  </body>
</html>
```

```php-template
<html>
  <head>
    <title>Example: A Site about Examples</title>
  </head>
  <body>
  <div itemscope itemtype="https://schema.org/WebSite">
    <link itemprop="url" href="https://example.com" />
    <meta itemprop="name" content="Example"/>
  </div>
  </body>
</html>
```
          

### 대체 사이트 이름 추가하기

사이트 이름의 대체 버전(예: 약어 또는 짧은 이름)을 제공하려면 `alternateName` 속성을 추가하면 됩니다. 이는 선택사항입니다.

| 권장 속성 | 권장 속성 |
|---------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `alternateName` | `[Text](https://schema.org/Text)`

해당하는 경우 웹사이트의 대체 이름입니다(예: 일반적으로 알려진 약어 또는 더 짧은 사이트 이름이 있는 경우). 웹사이트 이름은 [사이트 이름 선택 가이드라인](https://developers.google.com/search/docs/appearance/site-names?hl=ko#choosing-site-name)을 준수해야 합니다.

대체 이름을 두 개 이상 명시할 수 있습니다. 가장 중요한 것부터 나열하여 원하는 순서대로 지정하세요. 예를 들면 다음과 같습니다.

<script type="application/ld+json">
  {
    "@context": "https://schema.org",
    "@type": "WebSite",
    "name": "Burnt Toast",
    **"alternateName": ["BT", "B-T", "Burnt Toast Shop"],**
    "url": "https://www.example.com/"
  }
</script> |

다음은 모든 필수 및 권장 입력란이 포함된 구조화된 `WebSite` 데이터의 예입니다.

[JSON-LD](https://developers.google.com/search/docs/appearance/site-names?hl=ko/#json-ld)[마이크로데이터](https://developers.google.com/search/docs/appearance/site-names?hl=ko/#마이크로데이터) 더보기

```php-template
<html>
  <head>
    <title>Example: A Site about Examples</title>
    <script type="application/ld+json">
    {
      "@context" : "https://schema.org",
      "@type" : "WebSite",
      "name" : "Example Company",
      "alternateName" : "EC",
      "url" : "https://example.com/"
    }
  </script>
  </head>
  <body>
  </body>
</html>
```

```php-template
<html>
  <head>
    <title>Example: A Site about Examples</title>
  </head>
  <body>
  <div itemscope itemtype="https://schema.org/WebSite">
  <link itemprop="url" href="https://example.com" />
    <meta itemprop="name" content="Example Company"/>
    <meta itemprop="alternateName" content="EC"/>
  </div>
  </body>
</html>
```

### 구조화된 데이터 테스트하기

1.  스키마 테스트 도구(예: [스키마 마크업 검사기](https://validator.schema.org/))로 마크업의 유효성을 검사하여 구문 오류가 없는지 확인합니다. 사이트 이름은 리치 결과 테스트에서 지원되지 않습니다.
2.  [URL 검사 도구](https://support.google.com/webmasters/answer/9012289?hl=ko)를 사용하여 Google에서 페이지를 어떻게 인식하는지 테스트합니다. 이때 Google에서 홈페이지에 액세스할 수 있으며 robots.txt 파일, `noindex` 또는 로그인 요구사항으로 인해 차단되어 있어서는 안 됩니다.
3.  페이지가 정상적으로 표시되면 [Google에 URL을 재크롤링하도록 요청](https://developers.google.com/search/docs/crawling-indexing/ask-google-to-recrawl?hl=ko)할 수 있습니다.

## 원하는 사이트 이름을 선택하지 않은 경우 해결 방법

Google 시스템은 보통 구조화된 `WebSite` 데이터에서 제공된 기본 사이트 이름을 사용하려고 합니다(표시되는 경우). 그러나 제공된 이름을 Google 시스템에서 신뢰할 수 없는 경우 [다른 소스](https://developers.google.com/search/docs/appearance/site-names?hl=ko#sources)를 사용하여 사이트 이름을 생성하거나 도메인 또는 하위 도메인 이름을 표시하는 경우가 있습니다.

Google 자동화 시스템에서 내가 원하는 사이트 이름을 선택하지 않았다면 다음 단계를 따르세요.

1.  다음 사항을 확인하세요.
    -   홈페이지의 [구조화된 `WebSite` 데이터](https://developers.google.com/search/docs/appearance/site-names?hl=ko#website)에 있는 사이트 이름이 내가 원하는 사이트 이름임
    -   구조화된 `WebSite` 데이터에 [구조화된 데이터 오류](https://support.google.com/webmasters/answer/13300873?hl=ko)가 없음 스키마 테스트 도구(예: [스키마 마크업 검사기](https://validator.schema.org/))를 사용하여 구문 오류가 없는지 확인합니다(리치 결과 테스트에서는 사이트 이름을 지원하지 않음).
    -   구조화된 데이터가 [Google 가이드라인을 준수](https://developers.google.com/search/docs/appearance/site-names?hl=ko#guidelines)함
    -   홈페이지의 [다른 소스](https://developers.google.com/search/docs/appearance/site-names?hl=ko#sources)에서 내가 원하는 사이트의 이름을 사용하는지도 확인하세요.
    -   하위 디렉터리에 사이트 이름을 설정한 것은 아닌지 확인합니다. 하위 디렉터리에는 사이트 이름이 지원되지 않습니다. 예를 들어 `https://example.com/news`은 하위 디렉터리 수준의 홈페이지이며 자체 사이트 이름은 사용할 수 없습니다. 자세한 내용은 [기술 안내](https://developers.google.com/search/docs/appearance/site-names?hl=ko#technical-guidelines)를 참고하세요.
2.  리디렉션이 의도한 대로 작동하는지 및 Googlebot이 리디렉션 대상에 액세스할 수 있는지 확인합니다. 그런 다음 [해당 페이지의 재크롤링을 요청](https://developers.google.com/search/docs/crawling-indexing/ask-google-to-recrawl?hl=ko)하세요. 페이지가 Googlebot에 표시되는 페이지로 리디렉션되는 경우 사이트 이름에 리디렉션 대상이 반영됩니다.
3.  사이트의 버전이 여러 개인 경우(예: HTTP 및 HTTPS) 동일한 사이트 이름을 일관되게 사용해야 합니다.
4.  구조화된 사이트 이름 데이터를 업데이트했다면 Google에서 새 정보를 재크롤링하고 처리할 때까지 기다려 주세요. 크롤링은 Google 시스템에서 콘텐츠를 새로고침해야 한다고 판단하는 빈도에 따라 며칠에서 몇 주까지 걸릴 수 있습니다. [URL 검사 도구](https://support.google.com/webmasters/answer/9012289?hl=ko#request_indexing)를 사용하여 페이지 재크롤링을 요청할 수 있습니다.

안내를 따랐는데도 내가 원하는 사이트 이름이 선택되지 않은 경우 다음 옵션 중 하나를 고려해 보세요.

1.  **먼저 `alternateName` 속성을 사용하여 대체 이름을 제공합니다**. Google의 사이트 이름 시스템에서 기본 이름을 사용하는 데 확신을 갖지 못하는 경우 이 옵션을 유력하게 고려합니다.
2.  **도메인 또는 하위 도메인 이름을 백업 옵션으로 제공합니다.** 도메인 또는 하위 도메인을 백업 옵션으로 제공하려면 도메인 또는 하위 도메인 이름을 [대체 이름](https://developers.google.com/search/docs/appearance/site-names?hl=ko#alternative)으로 추가합니다. Google 시스템에서 이를 사이트 이름 환경설정으로 감지하려면 도메인 또는 하위 도메인이 모두 소문자여야 합니다(예: `Example.com`가 아닌 `example.com`). 기본 이름이 선택되지 않은 경우 Google 시스템에서 이 이름을 사용하는 방안을 적극적으로 검토합니다. 이 예에서는 Burnt Toast가 가장 선호되며 BT가 그 다음입니다. 그리고 도메인 example.com이 최종 이름 환경설정으로 끝납니다.
    
    ```php-template
    <script type="application/ld+json">
      {
        "@context": "https://schema.org",
        "@type": "WebSite",
        "name": "Burnt Toast",
        "alternateName": ["BT", "B-T", "Burnt Toast Shop", "example.com"],
        "url": "https://www.example.com/"
      }
    </script>
    ```
    
3.  **그래도 문제가 해결되지 않으면 도메인 또는 하위 도메인 이름(모두 소문자)을 [기본 이름](https://developers.google.com/search/docs/appearance/site-names?hl=ko#preferred-name)으로 제공해 보세요. 최후의 수단입니다.** 선호 이름으로 도메인 또는 하위 도메인 이름을 제공하면 일반적으로 시스템에서 이 이름을 선택합니다. 최후의 수단으로만 사용하는 것이 좋습니다. 이 예시에서 유일한 선택지는 도메인 example.com입니다.
    
    ```php-template
    <script type="application/ld+json">
      {
        "@context": "https://schema.org",
        "@type": "WebSite",
        "name": "example.com",
        "url": "https://www.example.com/"
      }
    </script>
    ```
    

[문제 해결 단계](https://developers.google.com/search/docs/appearance/site-names?hl=ko#troubleshooting)를 시도한 후에도 여전히 문제가 발생하면 [Google 검색 센터 도움말 커뮤니티](https://support.google.com/webmasters/thread/227739087?hl=ko)에 질문을 올려주세요. 이는 향후 Google 시스템을 개선하는 데 도움이 됩니다.