robots.txt 파일을 사용하여 사이트에서 [크롤러가 액세스할 수 있는 파일을 제어](https://developers.google.com/search/docs/crawling-indexing/robots/intro?hl=ko)할 수 있습니다.

robots.txt 파일은 사이트의 루트에 위치합니다. 따라서 `www.example.com` 사이트의 경우 robots.txt 파일은 `www.example.com/robots.txt`에 있습니다. robots.txt는 [robots 배제 표준](https://en.wikipedia.org/wiki/Robots_exclusion_standard#About_the_standard)을 따르는 일반 텍스트 파일입니다. robots.txt 파일은 하나 이상의 규칙으로 구성됩니다. 각 규칙은 모든 또는 특정 크롤러가 robots.txt 파일이 호스팅되는 도메인 또는 하위 도메인에서 지정된 파일 경로에 액세스하는 것을 차단하거나 허용합니다. robots.txt 파일에서 다르게 지정하지 않는 한 모든 파일은 암시적으로 크롤링에 허용됩니다.

다음은 두 가지 규칙이 포함된 간단한 robots.txt 파일입니다.

```makefile
User-agent: Googlebot
Disallow: /nogooglebot/

User-agent: *
Allow: /

Sitemap: https://www.example.com/sitemap.xml
```

**이 robots.txt 파일의 의미는 다음과 같습니다.**

1.  이름이 Googlebot인 사용자 에이전트는 `https://example.com/nogooglebot/`으로 시작하는 URL을 크롤링할 수 없습니다.
2.  그 외 모든 사용자 에이전트는 전체 사이트를 크롤링할 수 있습니다. 이 부분을 생략해도 결과는 동일합니다. 사용자 에이전트가 전체 사이트를 크롤링할 수 있도록 허용하는 것이 기본 동작입니다.
3.  사이트의 [사이트맵 파일](https://developers.google.com/search/docs/crawling-indexing/sitemaps/overview?hl=ko)은 `https://www.example.com/sitemap.xml`에 있습니다.

더 많은 예는 [구문](https://developers.google.com/crawling/docs/robots-txt/create-robots-txt?hl=ko#create_rules) 섹션을 참고하세요.

## robots.txt 파일 만들기 기본 가이드라인

robots.txt 파일을 만들어 일반적으로 액세스 가능하고 유용하게 하려면 네 단계가 필요합니다.

1.  [robots.txt라는 파일을 만듭니다](https://developers.google.com/crawling/docs/robots-txt/create-robots-txt?hl=ko#format_location).
2.  [robots.txt 파일에 규칙을 추가합니다](https://developers.google.com/crawling/docs/robots-txt/create-robots-txt?hl=ko#create_rules).
3.  [robots.txt 파일을 사이트 루트에 업로드합니다](https://developers.google.com/crawling/docs/robots-txt/create-robots-txt?hl=ko#upload).
4.  [robots.txt 파일을 테스트합니다](https://developers.google.com/crawling/docs/robots-txt/create-robots-txt?hl=ko#testing).

## Robots.txt 파일 만들기

거의 모든 텍스트 편집기를 사용하여 robots.txt 파일을 만들 수 있습니다. 예를 들어 메모장, TextEdit, vi, emacs는 유효한 robots.txt 파일을 만들 수 있습니다. 워드 프로세서는 사용하지 마세요. 워드 프로세서는 파일을 고유의 형식으로 저장하는 경우가 많고, 둥근 따옴표와 같은 예상치 못한 문자를 추가하여 크롤러에 문제를 일으킬 수 있습니다. 파일 저장 대화상자에서 메시지가 표시되면 UTF-8 인코딩으로 파일을 저장해야 합니다.

**형식 및 위치 규칙**

-   파일 이름은 robots.txt로 지정해야 합니다.
-   사이트에는 robots.txt 파일이 하나만 있어야 합니다.
-   robots.txt 파일은 파일이 적용되는 사이트 호스트의 루트에 있어야 합니다. 예를 들어, `https://www.example.com/` 아래 모든 URL에 관한 크롤링을 제어하려면 robots.txt 파일이 `https://www.example.com/robots.txt`에 있어야 합니다. 이 파일을 하위 디렉터리(예: `https://example.com/pages/robots.txt`)에 배치하면 _안 됩니다_. 사이트 루트에 액세스하는 방법을 잘 모르거나 액세스 권한이 필요한 경우 웹 호스팅 서비스 제공업체에 문의하세요. 사이트 루트에 액세스할 수 없다면 [`meta` 태그](https://developers.google.com/search/docs/crawling-indexing/block-indexing?hl=ko)와 같은 다른 차단 방법을 사용하세요.
-   robots.txt 파일을 하위 도메인(예: `https://**site**.example.com/robots.txt`) 또는 비표준 포트(예: `https://example.com:**8181**/robots.txt`)에 게시할 수 있습니다.
-   robots.txt 파일은 파일이 게시된 프로토콜, 호스트, 포트 내의 경로에만 적용됩니다. 즉, `https://example.com/robots.txt`의 규칙은 `https://example.com/`의 파일에만 적용되며 `https://m.example.com/`과 같은 하위 도메인이나 `http://example.com/`과 같은 대체 프로토콜에는 적용되지 않습니다.
-   robots.txt 파일은 UTF-8로 인코딩된 텍스트 파일이어야 합니다(ASCII 포함). Google은 UTF-8 범위에 속하지 않는 문자를 무시할 수 있으므로 robots.txt 규칙이 무효화될 수 있습니다.

## robots.txt 규칙 작성 방법

규칙은 크롤러가 크롤링할 수 있는 사이트의 부분에 관한 지침입니다. robots.txt 파일에 규칙을 추가할 때 다음 가이드라인을 따르세요.

-   robots.txt 파일은 하나 이상의 그룹(규칙의 집합)으로 구성됩니다.
-   각 그룹은 한 행에 하나의 규칙(지시어라고도 함)으로 구성됩니다. 각 그룹은 그룹의 대상을 지정하는 `User-agent` 행으로 시작합니다.
-   그룹은 다음과 같은 정보를 제공합니다.
    -   그룹이 적용되는 대상(사용자 에이전트)
    -   에이전트가 액세스_할 수 있는_ 디렉터리나 파일
    -   에이전트가 액세스_할 수 없는_ 디렉터리나 파일
-   크롤러는 위에서 아래로 그룹을 처리합니다. 사용자 에이전트는 주어진 사용자 에이전트와 일치하는 가장 구체적인 첫 번째 그룹인 한 가지 규칙 집합에만 연결될 수 있습니다. 동일한 사용자 에이전트에 여러 그룹이 있는 경우 처리가 진행되기 전에 여러 그룹이 하나의 그룹으로 결합됩니다.
-   기본적인 가정은 사용자 에이전트에서 `disallow` 규칙으로 차단되지 않은 페이지나 디렉터리를 크롤링할 수 있다는 것입니다.
-   규칙은 대소문자를 구분합니다. 예를 들어, `disallow: /file.asp`는 `https://www.example.com/file.asp`에 적용되지만 `https://www.example.com/FILE.asp`에는 적용되지 않습니다.
-   `#` 문자는 주석의 시작 부분을 표시합니다. 댓글은 처리 중에 무시됩니다.

**Google 크롤러는 robots.txt 파일에서 다음 규칙을 지원합니다.**

-   `user-agent:` \[필수, 그룹당 하나 이상\] 규칙은 규칙이 적용되는 검색엔진 크롤러(자동화 클라이언트)의 이름을 지정합니다. 이 명령은 모든 규칙 그룹의 첫 행입니다. Google 사용자 에이전트 이름은 [Google 사용자 에이전트 목록](https://developers.google.com/crawling/docs/crawlers-fetchers/overview-google-crawlers?hl=ko)에 나열되어 있습니다. 별표(`*`)를 사용하면 이름을 명시적으로 지정해야 하는 여러 AdsBot 크롤러를 제외한 모든 크롤러에 규칙을 적용할 수 있습니다. 예를 들면 다음과 같습니다.
    
    ```makefile
    # Example 1: Block only Googlebot
    User-agent: Googlebot
    Disallow: /
    
    # Example 2: Block Googlebot and Adsbot
    User-agent: Googlebot
    User-agent: AdsBot-Google
    Disallow: /
    
    # Example 3: Block all crawlers except AdsBot (AdsBot crawlers must be named explicitly)
    User-agent: *
    Disallow: /
    ```
    
-   `disallow:` \[규칙당 하나 이상의 `disallow` 또는 `allow` 항목 필요\] 사용자 에이전트가 크롤링하지 않도록 하려는 루트 도메인 관련 디렉터리 또는 페이지입니다. 규칙이 페이지를 참조하는 경우 브라우저에 표시되는 전체 페이지 이름이어야 합니다. `/` 문자로 시작해야 하고 디렉터리를 참조하는 경우 `/` 기호로 끝나야 합니다.
-   `allow:` \[규칙당 하나 이상의 `disallow` 또는 `allow` 항목 필요\] 방금 언급한 사용자 에이전트가 크롤링할 수 있는 루트 도메인 관련 디렉터리 또는 페이지입니다. 이는 `disallow` 규칙을 재정의하여 허용되지 않은 디렉터리에 있는 하위 디렉터리 또는 페이지를 크롤링할 수 있도록 합니다. 단일 페이지의 경우 브라우저에 표시된 전체 페이지 이름을 지정합니다. `/` 문자로 시작해야 하고 디렉터리를 참조하는 경우 `/` 기호로 끝나야 합니다.
-   `sitemap:` \[선택사항, 파일당 0개 이상\] 사이트의 사이트맵 위치입니다. 사이트맵 URL은 정규화된 URL이어야 합니다. Google은 http, https, www를 포함하는 URL과 포함하지 않는 대체 URL을 가정하거나 확인하지 않습니다. 사이트맵은 Google에서 크롤링_할 수 있거나_ _할 수 없는_ 콘텐츠를 표시하는 것이 아니라 크롤링을 해야 하는 콘텐츠를 표시할 때 좋은 방법입니다. [사이트맵에 관해 자세히 알아보기](https://developers.google.com/search/docs/crawling-indexing/sitemaps/overview?hl=ko) **예:**
    
    ```bash
    Sitemap: https://example.com/sitemap.xml
    Sitemap: https://www.example.com/sitemap.xml
    ```
    

`sitemap`을 제외한 모든 규칙은 경로 접두사, 접미사 또는 전체 문자열에 `*` 와일드 카드를 지원합니다.

다음 규칙과 일치하지 않는 행은 무시됩니다.

각 규칙에 관한 자세한 내용은 [Google의 robots.txt 사양 해석](https://developers.google.com/crawling/docs/robots-txt/robots-txt-spec?hl=ko) 페이지를 참고하세요.

## robots.txt 파일 업로드

robots.txt 파일을 컴퓨터에 저장했다면 검색엔진 크롤러에서 사용할 수 있습니다. 이 작업에 도움이 되는 한 가지 도구는 없습니다. robots.txt 파일을 사이트에 업로드하는 방법은 사이트와 서버 아키텍처에 따라 달라지기 때문입니다. 호스팅 업체에 문의하거나 호스팅 업체의 문서를 검색하세요. 예를 들어 '업로드 파일 infomaniak'를 검색합니다.

robots.txt 파일을 업로드한 후 공개적으로 액세스할 수 있는지, Google에서 파싱할 수 있는지 테스트합니다.

## robots.txt 마크업 테스트

새로 업로드한 robots.txt 파일에 공개적으로 액세스할 수 있는지 테스트하려면 브라우저에서 [시크릿 브라우징 창](https://support.google.com/chrome/answer/95464?hl=ko)(또는 이에 상응하는 창)을 열고 robots.txt 파일 위치로 이동합니다. 예를 들면 `https://example.com/robots.txt`로 이동할 수 있습니다. robots.txt 파일의 콘텐츠가 표시되면 마크업을 테스트할 수 있습니다.

Google에서는 다음과 같이 robots.txt 마크업 문제를 해결하는 2가지 옵션을 제공합니다.

1.  Search Console의 [robots.txt 보고서](https://support.google.com/webmasters/answer/6062598?hl=ko). 이 보고서는 사이트에서 이미 액세스할 수 있는 robots.txt 파일에만 사용할 수 있습니다.
2.  개발자는 Google 검색에서도 사용되는 [Google의 오픈소스 robots.txt 라이브러리](https://github.com/google/robotstxt)를 확인하고 빌드합니다. 이 도구는 컴퓨터에서 로컬로 robots.txt 파일을 테스트하는 데 사용할 수 있습니다.

## robots.txt 파일을 Google에 제출

robots.txt 파일을 업로드하여 테스트한 후에는 Google 크롤러가 자동으로 robots.txt 파일을 찾아 사용하기 시작합니다. 다른 작업이 필요하지 않습니다. robots.txt 파일을 업데이트한 후 최대한 빨리 Google의 캐시된 사본을 새로고침해야 한다면 [업데이트된 robots.txt 파일 제출 방법](https://developers.google.com/crawling/docs/robots-txt/submit-updated-robots-txt?hl=ko)을 참고하세요.