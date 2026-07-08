## 검색결과에 표시할 파비콘 정의하기

사이트에 [파비콘](https://www.google.com/search?q=what+is+a+favicon&hl=ko)이 있는 경우 사이트의 Google 검색결과에 파비콘을 포함할 수 있습니다.

검색결과에 파비콘이 어떻게 표시되는지 보여주는 삽화

파비콘

## 구현

다음은 Google 검색결과에 파비콘을 표시할 수 있게 사이트를 설정하는 방법입니다.

1.  [가이드라인](https://developers.google.com/search/docs/appearance/favicon-in-search?hl=ko#guidelines)을 준수하는 파비콘을 만듭니다.
2.  다음 구문을 사용하여 [홈페이지 헤더](https://developers.google.com/search/docs/appearance/favicon-in-search?hl=ko#guidelines)에 `<link>` 태그를 추가합니다.
    
    ```bash
    <link rel="icon" href="/path/to/favicon.ico">
    ```
    
    Google에서는 파비콘 정보를 추출하기 위해 `link` 요소의 다음 속성을 사용합니다.
    
    | 속성 | 속성 |
    |------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
    | `rel` | 다음은 Google에서 지원하는 파비콘 지정 `rel` 속성 값으로 사용 사례에 적합한 것을 사용하세요.
    
    `icon`
    
    [HTML 표준](https://html.spec.whatwg.org/#rel-icon)에 정의된 대로 사이트를 나타내는 아이콘입니다.
    
    `apple-touch-icon`
    
    [Apple의 개발자 문서](https://developer.apple.com/library/archive/documentation/AppleApplications/Reference/SafariWebContent/ConfiguringWebApplications/ConfiguringWebApplications.html)에 따라 사이트를 나타내는 iOS 친화적인 아이콘입니다.
    
    `apple-touch-icon-precomposed`
    
    [Apple 개발자 문서](https://developer.apple.com/library/archive/documentation/AppleApplications/Reference/SafariWebContent/ConfiguringWebApplications/ConfiguringWebApplications.html)에 따라 이전 버전 iOS의 대체 아이콘입니다. |
    | `href` | 파비콘의 URL입니다. URL은 상대 경로(`/smile.ico`) 또는 절대 경로(`https://example.com/smile.ico`)일 수 있습니다. 사이트에서 URL을 호스팅하지 않아도 됩니다(예: 파비콘은 콘텐츠 전송 네트워크(CDN)에서 호스팅할 수 있음). |
    
3.  Google에서 홈페이지의 새로운 정보를 다시 크롤링하고 처리하는 동안 기다립니다. 크롤링은 Google 시스템에서 콘텐츠를 새로고침해야 한다고 판단하는 빈도에 따라 며칠에서 몇 주까지 걸릴 수 있습니다. URL 검사 도구를 사용하여 사이트 홈페이지의 [색인 생성을 요청](https://developers.google.com/search/docs/crawling-indexing/ask-google-to-recrawl?hl=ko)할 수 있습니다.

## 가이드라인

Google 검색결과에 파비콘을 표시하려면 다음 가이드라인을 준수해야 합니다.

-   Google 검색에서는 사이트당 파비콘이 하나만 지원되며 _사이트_는 호스트 이름으로 정의됩니다. 예를 들어 `https://www.example.com/`과 `https://code.example.com/`이라는 사이트 두 개는 서로 다르므로 두 개의 다른 파비콘을 보유할 수 있습니다. 그러나 `https://www.example.com/sub-site`는 사이트의 하위 디렉터리이며, `https://www.example.com/`에는 파비콘을 하나만 설정할 수 있습니다. 해당 파비콘은 사이트와 사이트의 하위 디렉터리에 적용됩니다.  
    **지원됨**: `https://example.com`(도메인 수준의 홈페이지)  
    **지원됨**: `https://news.example.com`(하위 도메인 수준의 홈페이지)  
    **지원되지 않음**: `https://example.com/news`(하위 디렉터리 수준의 홈페이지)
-   Googlebot 이미지가 파비콘 파일을 크롤링할 수 있어야 하고 Googlebot이 홈페이지를 크롤링할 수 있어야 합니다. 크롤링을 [차단](https://developers.google.com/search/docs/crawling-indexing/control-what-you-share?hl=ko)할 수 없습니다.
-   사용자가 검색결과를 살펴볼 때 사이트를 빠르게 식별할 수 있도록 파비콘은 웹사이트 브랜드를 시각적으로 잘 나타내야 합니다.
-   파비콘은 정사각형(가로세로 비율 1:1)이어야 하며 크기는 8x8픽셀 이상이어야 합니다. 최소 크기는 8x8px이지만, 다양한 표시 경로에서 보기 좋도록 48x48px보다 큰 크기의 파비콘을 사용하는 것이 좋습니다. 모든 [유효한 파비콘 형식](https://en.wikipedia.org/wiki/Favicon#Image_file_format_support)이 지원됩니다.
-   파비콘 URL은 안정적이어야 합니다. URL을 자주 변경하지 마세요.
-   Google에서는 포르노, 증오심을 나타내는 상징(예: 만자 표시) 등 부적절하다고 간주되는 파비콘을 표시하지 않습니다. 이러한 유형의 이미지가 파비콘 내에 발견되면 기본 아이콘으로 교체됩니다.

## 검색 결과의 파비콘에 대한 의견 제출

검색 결과에서 Google의 파비콘 처리에 관한 의견이 있으면 [파비콘 의견 양식을 작성](https://forms.gle/KVBeuGWTg1yTwy7p9)해 주세요. 여기에 제출된 의견은 Google 검색의 전반적인 시스템을 개선하기 위한 것이며, 개별적으로 조치가 취해진다고 보장하지는 않습니다.