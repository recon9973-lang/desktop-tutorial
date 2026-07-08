Google의 자동화된 [크롤러](https://developers.google.com/crawling/docs/crawlers-fetchers/overview-google-crawlers?hl=ko)는 [로봇 제외 프로토콜(REP)](https://www.rfc-editor.org/rfc/rfc9309.html)을 지원합니다. 즉, 사이트를 크롤링하기 전에 Google 크롤러는 사이트의 robots.txt 파일을 다운로드하고 파싱하여 사이트에서 크롤링할 수 있는 부분에 관한 정보를 추출합니다. REP는 사용자가 제어하는 Google 크롤러(예: 피드 구독)나 사용자 안전을 강화하는 데 사용되는 크롤러(예: 멀웨어 분석)에는 적용되지 않습니다.

이 페이지에서는 Google의 REP 해석에 관해 설명합니다. 원래 표준에 관해서는 [RFC 9309](https://www.rfc-editor.org/rfc/rfc9309.html)를 확인하세요.

## robots.txt 파일이란 무엇인가요?

크롤러가 사이트의 섹션에 액세스하지 못하도록 하려면 적절한 규칙으로 robots.txt 파일을 만들면 됩니다. robots.txt 파일은 어떤 크롤러가 사이트의 어느 부분에 액세스할 수 있는지에 관한 규칙이 포함된 텍스트 파일입니다. 예를 들어, example.com의 robots.txt 파일은 다음과 같을 수 있습니다.

```makefile
# This robots.txt file controls crawling of URLs under https://example.com.
# All crawlers are disallowed to crawl files in the "includes" directory, such
# as .css, .js, but Google needs them for rendering, so Googlebot is allowed
# to crawl them.
User-agent: *
Disallow: /includes/

User-agent: Googlebot
Allow: /includes/

Sitemap: https://example.com/sitemap.xml
```

robots.txt를 처음 사용한다면 [robots.txt 소개](https://developers.google.com/search/docs/crawling-indexing/robots/intro?hl=ko)부터 시작하세요. [robots.txt 파일 만들기 팁](https://developers.google.com/crawling/docs/robots-txt/create-robots-txt?hl=ko)도 참고할 수 있습니다.

## 파일 위치 및 유효성 범위

robots.txt 파일은 지원되는 프로토콜에서 사이트의 최상위 디렉터리에 있어야 합니다. robots.txt 파일의 URL은 다른 URL에서와 같이 대소문자를 구분합니다. Google 검색의 경우 지원되는 프로토콜은 HTTP, HTTPS, FTP입니다. HTTP와 HTTPS에서 크롤러는 HTTP 비조건부 `GET` 요청으로 robots.txt 파일을 가져옵니다. FTP에서 크롤러는 익명 로그인을 사용하여 표준 `RETR (RETRIEVE)` 명령어를 사용합니다.

robots.txt 파일에 나열된 규칙은 robots.txt 파일이 호스팅되는 호스트와 프로토콜, 포트 번호에만 적용됩니다.

## 유효한 robots.txt URL의 예

다음 표에는 robots.txt URL의 예와 유효한 URL 경로가 나와 있습니다. 첫 번째 열에는 robots.txt 파일의 URL이 포함되고 두 번째 열에는 robots.txt 파일이 적용되거나 적용되지 않는 도메인이 포함됩니다.

| robots.txt URL 예 | robots.txt URL 예 |
|---------------------------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `https://example.com/robots.txt` | 일반적인 경우로, 다른 하위 도메인이나 프로토콜, 포트 번호에는 유효하지 않습니다. 같은 호스트와 프로토콜, 포트 번호의 모든 하위 디렉터리에 있는 모든 파일에는 유효합니다.

유효함:

-   `https://example.com/`
-   `https://example.com/folder/file`

유효하지 않음:

-   `https://other.example.com/`
-   `http://example.com/`
-   `https://example.com:8181/` |
| `https://www.example.com/robots.txt` | 하위 도메인의 robots.txt는 해당 하위 도메인에서만 유효합니다.

유효함: `https://www.example.com/`

유효하지 않음:

-   `https://example.com/`
-   `https://shop.www.example.com/`
-   `https://www.shop.example.com/` |
| `https://example.com/folder/robots.txt` | 유효한 robots.txt 파일이 아닙니다. 크롤러는 하위 디렉터리의 robots.txt 파일은 확인하지 않습니다. |
| `https://www.exämple.com/robots.txt` | IDN은 punycode 버전과 같습니다. [RFC 3492](https://www.ietf.org/rfc/rfc3492.txt)도 참조하세요.

유효함:

-   `https://www.exämple.com/`
-   `https://xn--exmple-cua.com/`

유효하지 않음: `https://www.example.com/` |
| `ftp://example.com/robots.txt` | 유효함: `ftp://example.com/`

유효하지 않음: `https://example.com/` |
| `https://212.96.82.21/robots.txt` | 호스트 이름으로 IP 주소를 사용한 robots.txt는 이 IP 주소를 호스트 이름으로 크롤링하는 경우에만 유효합니다. 이러한 IP 주소에 호스팅된 모든 웹사이트에서 자동으로 유효하지 않습니다. 하지만 robots.txt 파일을 공유할 수 있으며 이 경우 공유된 호스트 이름으로 사용할 수 있습니다.

유효함: `https://212.96.82.21/`

유효하지 않음: `https://example.com/`(`212.96.82.21`에 호스팅된 경우도 포함) |
| `https://example.com:443/robots.txt` | 표준 포트 번호(HTTP: `80`, HTTPS: `443`, FTP: `21`)는 기본 호스트 이름과 같습니다.

유효함:

-   `https://example.com:443/`
-   `https://example.com/`

유효하지 않음: `https://example.com:444/` |
| `https://example.com:8181/robots.txt` | 비표준 포트 번호의 robots.txt 파일은 이러한 포트 번호를 통해 사용할 수 있는 콘텐츠에서만 유효합니다.

유효함: `https://example.com:8181/`

유효하지 않음: `https://example.com/` |

## 오류 및 HTTP 상태 코드 처리

robots.txt 파일을 요청할 때 서버 응답의 HTTP 상태 코드는 Google 크롤러에서 robots.txt 파일을 사용하는 방식에 영향을 미칩니다. 다음 표는 Googlebot이 다양한 HTTP 상태 코드에 맞게 robots.txt 파일을 처리하는 방식을 요약한 것입니다.

| 오류 및 HTTP 상태 코드 처리 | 오류 및 HTTP 상태 코드 처리 |
|---------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `2xx (success)` | 성공을 알리는 HTTP 상태 코드는 Google 크롤러가 서버에서 제공한 robots.txt 파일을 처리하도록 합니다. |
| `3xx (redirection)` | Google에서는 [RFC 1945](https://www.ietf.org/rfc/rfc1945.txt)에 정의된 대로 5개 이상의 리디렉션 홉을 따른 다음 중지하고 이를 robots.txt 파일의 `404`로 처리합니다. 이는 리디렉션 체인의 허용되지 않는 URL에도 적용됩니다. 크롤러가 리디렉션으로 인해 규칙을 가져올 수 없기 때문입니다.

Google은 robots.txt 파일의 논리적 리디렉션(프레임, JavaScript, 메타 새로고침 유형 리디렉션)을 따르지 않습니다. |
| `4xx (client errors)` | Google 크롤러는 `429`를 제외한 모든 `4xx` 오류를 유효한 robots.txt 파일이 없는 것처럼 처리합니다. 즉, Google은 크롤링 제한이 없다고 가정합니다. |
| `5xx (server errors)` | Google이 robots.txt 파일을 찾았지만 가져올 수 없는 경우 Google은 다음 동작을 따릅니다.

1.  처음 12시간 동안 Google은 사이트 크롤링을 중단하지만 계속 robots.txt 파일을 가져오려고 시도합니다.
2.  새 버전을 가져올 수 없는 경우 향후 30일 동안 Google은 유효한 최종 버전을 사용하면서 새 버전을 가져오려고 시도합니다. `503 (service unavailable)` 오류로 인해 재시도가 상당히 빈번하게 발생합니다. 사용 가능한 캐시된 버전이 없는 경우 Google은 크롤링 제한이 없는 것으로 간주합니다.
3.  30일이 지나도 오류가 해결되지 않으면 다음과 같이 동작합니다.
    -   사이트를 Google에서 일반적으로 사용할 수 있는 경우 Google에서는 robots.txt 파일이 없는 것처럼 동작하면서 새 버전이 있는지 계속 확인합니다.
    -   사이트에 일반 안정화 버전 문제가 있는 경우 Google에서 사이트 크롤링을 중단하는 동시에 주기적으로 robots.txt 파일을 요청합니다. |
| 기타 오류 | 시간 초과, 잘못된 응답, 연결 재설정/중단, HTTP 청킹 오류와 같은 DNS 또는 네트워크 문제로 인해 가져올 수 없는 robots.txt 파일은 [서버 오류](https://developers.google.com/crawling/docs/robots-txt/robots-txt-spec?hl=ko#server-error)로 처리됩니다. |

## 캐싱

Google은 일반적으로 robots.txt 파일의 콘텐츠를 최대 24시간 동안 캐시하지만 캐시된 버전을 새로고침할 수 없는 때(예: 시간 초과나 `5xx` 오류로 인해)는 더 오래 캐시할 수도 있습니다. 캐시된 응답은 다른 크롤러에 의해 공유될 수 있습니다. Google은 [max-age Cache-Control](https://www.rfc-editor.org/rfc/rfc9110.html) HTTP 헤더를 기반으로 하여 캐시 기간을 늘리거나 줄일 수 있습니다.

## 파일 형식

robots.txt 파일은 [UTF-8](https://en.wikipedia.org/wiki/UTF-8)로 인코딩된 일반 텍스트 파일이어야 하고 행은 `CR`이나 `CR/LF`, `LF`로 구분해야 합니다.

Google은 robots.txt 파일 시작 부분의 유니코드 [바이트 순서 표시](https://en.wikipedia.org/wiki/Byte_order_mark)(BOM)를 비롯하여 robots.txt 파일의 잘못된 행을 무시하고 유효한 행만 사용합니다. 예를 들어 다운로드한 콘텐츠가 robots.txt 규칙이 아닌 HTML이면 Google은 콘텐츠를 파싱하고 규칙을 추출하며 나머지는 모두 무시하려고 합니다.

마찬가지로 robots.txt 파일의 문자 인코딩이 UTF-8이 아니면 Google은 UTF-8 범위에 속하지 않는 문자를 무시할 수 있으므로 robots.txt 규칙이 무효화될 수 있습니다.

Google은 robots.txt 파일 크기를 500[키비바이트](https://en.wikipedia.org/wiki/Kibibyte)(KiB)로 제한합니다. 최대 파일 크기를 넘는 콘텐츠는 무시됩니다. robots.txt 파일이 너무 커질 수 있는 규칙을 통합하면 robots.txt 파일 크기를 줄일 수 있습니다. 예를 들어, 제외된 자료를 별도의 디렉터리에 배치합니다.

## 구문

유효한 robots.txt 행은 필드와 콜론, 값으로 구성됩니다. 필드 이름은 대소문자를 구분하지 않습니다 (예: `User-agent`와 `user-agent`는 동일하게 취급됨). 공백은 선택사항이지만 가독성 향상을 위해 사용하는 것이 좋습니다. 행의 시작과 끝에 있는 공백은 무시됩니다. 주석을 포함하려면 주석 앞에 `#` 문자를 붙입니다. `#` 문자 다음에 오는 모든 내용은 무시됩니다. 일반적인 형식은 `<field>:<value><#optional-comment>`입니다.

Google에서는 다음 필드를 지원합니다(`crawl-delay`와 같은 다른 필드는 지원되지 않음).

-   `user-agent`: 규칙이 적용되는 크롤러를 식별합니다.
-   `allow`: 크롤링할 수 있는 URL 경로입니다.
-   `disallow`: 크롤링할 수 없는 URL 경로입니다.
-   `sitemap`: 사이트맵의 전체 URL입니다.

`allow` 및 `disallow` 필드는 규칙 또는 지시어이라고도 합니다. 규칙은 항상 `rule: [path]` 형식으로 지정되며, 여기에서 `[path]`는 선택사항입니다. 기본적으로 지정된 크롤러에 관한 크롤링의 제한은 없습니다. 크롤러는 `[path]`가 없는 규칙을 무시합니다.

지정되는 경우 `[path]` 값은 같은 프로토콜과 포트 번호, 호스트, 도메인 이름을 사용하여 robots.txt 파일을 가져온 웹사이트의 루트를 기준으로 합니다. 경로값은 `/` 기호로 시작하여 루트를 지정해야 하고 값은 대소문자를 구분합니다. [경로값에 기반한 URL 일치](https://developers.google.com/crawling/docs/robots-txt/robots-txt-spec?hl=ko#url-matching-based-on-path-values) 자세히 알아보기

### `user-agent`

`user-agent` 행은 적용되는 크롤러 규칙을 식별합니다. robots.txt 파일에서 사용할 수 있는 user-agent 문자열의 전체 목록은 [Google의 크롤러 및 user-agent 문자열](https://developers.google.com/crawling/docs/crawlers-fetchers/overview-google-crawlers?hl=ko)을 참고하세요.

`user-agent` 필드 이름과 값은 모두 대소문자를 구분하지 않습니다.

### `disallow`

`disallow` 규칙은 `disallow` 규칙이 그룹화된 `user-agent` 행으로 식별된 크롤러가 액세스하면 안 되는 경로를 지정합니다. 크롤러는 경로가 없는 규칙을 무시합니다.

Google은 크롤링이 허용되지 않는 페이지의 콘텐츠 색인을 생성할 수 없지만 여전히 URL의 색인을 생성하여 스니펫 없이 검색 결과에 표시할 수 있습니다. [색인 생성 차단](https://developers.google.com/search/docs/crawling-indexing/block-indexing?hl=ko) 방법 알아보기

필드 이름 (`disallow`)은 대소문자를 구분하지 않지만 값은 대소문자를 구분합니다.

사용:

```
disallow: [path]
```

### `allow`

`allow` 규칙은 지정된 크롤러가 액세스할 수 있는 경로를 지정합니다. 경로를 지정하지 않으면 규칙이 무시됩니다.

필드 이름 (`allow`)은 대소문자를 구분하지 않지만 값은 대소문자를 구분합니다.

사용:

```
allow: [path]
```

### `sitemap`

Google, Bing, 기타 주요 검색엔진에서는 [sitemaps.org](https://sitemaps.org/)에 정의된 대로 robots.txt의 `sitemap` 필드를 지원합니다.

필드 이름 (`sitemap`)은 대소문자를 구분하지 않지만 값은 대소문자를 구분합니다.

사용:

```
sitemap: [absoluteURL]
```

`[absoluteURL]` 행은 사이트맵 또는 사이트맵 색인 파일의 위치를 가리킵니다. 프로토콜과 호스트를 비롯하여 정규화된 URL이어야 하고 URL로 인코딩되지 않아도 됩니다. URL은 robots.txt 파일과 같은 호스트에 있지 않아도 됩니다. 여러 `sitemap` 필드를 지정할 수 있습니다. 사이트맵 필드는 특정 사용자 에이전트와 연결되지 않고 크롤링이 허용되는 경우 모든 크롤러가 따를 수 있습니다.

예:

```makefile
user-agent: otherbot
disallow: /kale

sitemap: https://example.com/sitemap.xml
sitemap: https://cdn.example.org/other-sitemap.xml
sitemap: https://ja.example.org/テスト-サイトマップ.xml
```

## 행 및 규칙 그룹

각 크롤러에 `user-agent` 행을 반복하여 여러 사용자 에이전트에 적용되는 규칙을 그룹화할 수 있습니다.

예:

```makefile
user-agent: a
disallow: /c

user-agent: b
disallow: /d

user-agent: e
user-agent: f
disallow: /g

user-agent: h
```

이 예에는 네 가지 고유한 규칙 그룹이 있습니다.

-   사용자 에이전트 'a' 그룹
-   사용자 에이전트 'b' 그룹
-   사용자 에이전트 'e' 및 'f' 그룹
-   사용자 에이전트 'h' 그룹

그룹에 관한 기술적 설명은 [REP 섹션 2.1](https://www.rfc-editor.org/rfc/rfc9309.html#section-2.1-2.4)을 참고하세요.

## 사용자 에이전트 우선순위

특정 크롤러에 하나의 그룹만 유효합니다. Google 크롤러는 robots.txt 파일에서 크롤러의 사용자 에이전트와 일치하는 가장 구체적인 사용자 에이전트가 있는 그룹을 찾아서 올바른 규칙 그룹을 결정합니다. 다른 그룹은 무시됩니다. 일치하지 않는 모든 텍스트는 무시됩니다. 예를 들어 `googlebot/1.2`와 `googlebot*`은 모두 `googlebot`과 같습니다. robots.txt 파일 내 그룹의 순서는 관련이 없습니다.

사용자 에이전트에 두 개 이상의 특정 그룹이 선언된 경우 특정 사용자 에이전트에 적용되는 그룹의 모든 규칙이 내부적으로 하나의 그룹에 결합됩니다. 사용자 에이전트 특정 그룹과 전역 그룹(`*`)은 결합되지 않습니다.

### 예

#### `user-agent` 필드 일치

```sql
user-agent: googlebot-news
(group 1)

user-agent: *
(group 2)

user-agent: googlebot
(group 3)
```

다음은 크롤러가 관련 그룹을 선택하는 방법입니다.

| 크롤러마다 이어지는 그룹 | 크롤러마다 이어지는 그룹 |
|---------------------------|------------------------------------------------------------------------------------------------------------------|
| Googlebot 뉴스 | `googlebot-news`는 그룹 1을 따릅니다. 그룹 1이 가장 구체적인 그룹이기 때문입니다. |
| Googlebot(웹) | `googlebot`은 그룹 3을 따릅니다. |
| Googlebot StoreBot | `Storebot-Google`는 그룹 2를 따릅니다. 특정 `Storebot-Google` 그룹이 없기 때문입니다. |
| Googlebot 뉴스(이미지를 크롤링할 때) | 이미지를 크롤링할 때 `googlebot-news`는 그룹 1을 따릅니다. `googlebot-news`는 Google 이미지의 이미지를 크롤링하지 않으므로 그룹 1만 따릅니다. |
| 다른 검색 로봇(웹) | 다른 Google 크롤러는 그룹 2를 따릅니다. |
| 다른 검색 로봇(뉴스) | 뉴스 콘텐츠를 크롤링하지만 `googlebot-news`로 식별되지 않는 다른 Google 크롤러는 그룹 2를 따릅니다. 연관된 크롤러를 위한 항목이 있다 하더라도 구체적으로 일치하는 경우에만 유효합니다. |

#### 규칙 그룹화

robots.txt 파일에 특정 사용자 에이전트와 관련된 그룹이 여러 개 있다면 Google 크롤러는 내부적으로 이 그룹을 병합합니다. 예:

```makefile
user-agent: googlebot-news
disallow: /fish

user-agent: *
disallow: /carrots

user-agent: googlebot-news
disallow: /shrimp
```

크롤러는 다음 예와 같이 사용자 에이전트에 기반하여 내부적으로 규칙을 그룹화합니다.

```makefile
user-agent: googlebot-news
disallow: /fish
disallow: /shrimp

user-agent: *
disallow: /carrots
```

`allow`, `disallow`, `user-agent` 외의 다른 규칙은 robots.txt 파서에서 무시됩니다. 즉, 다음 robots.txt 스니펫이 하나의 그룹으로 처리되므로 `user-agent` `a`와 `b`는 모두 `disallow: /` 규칙의 영향을 받습니다.

```makefile
user-agent: a
sitemap: https://example.com/sitemap.xml

user-agent: b
disallow: /
```

크롤러는 robots.txt 규칙을 처리할 때 `sitemap` 행을 무시합니다. 예를 들어 크롤러가 이전 robots.txt 스니펫을 인식하는 방식은 다음과 같습니다.

```makefile
user-agent: a
user-agent: b
disallow: /
```

## 경로값에 의한 URL 일치

Google에서는 `allow` 및 `disallow` 규칙의 경로값에 기반하여 사이트의 특정 URL에 규칙이 적용되는지를 결정합니다. 크롤러가 가져오려고 하는 URL의 경로 구성요소와 규칙을 비교하면 됩니다. [RFC 3986](https://www.ietf.org/rfc/rfc3986.txt)에 따라 UTF-8 문자 또는 퍼센트 이스케이프 처리된 UTF-8 인코딩된 문자로 7비트가 아닌 ASCII 문자가 경로에 포함될 수 있습니다.

Google, Bing, 기타 주요 검색엔진에서는 경로값에 제한된 형태의 _와일드 카드_를 지원합니다. 지원되는 와일드 카드 문자는 다음과 같습니다.

-   `*` 기호는 0개 이상의 유효한 문자를 나타냅니다.
-   `$` 기호는 URL의 끝을 나타냅니다.

다음 표는 다양한 와일드 카드 문자가 파싱에 미치는 영향을 보여줍니다.

| 경로 일치의 예 | 경로 일치의 예 |
|------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `/` | 루트 및 그 이하 수준의 모든 URL과 일치합니다. |
| `/*` | `/`와 같습니다. 뒤쪽 와일드 카드는 무시됩니다. |
| `/$` | 루트하고만 일치합니다. 모든 하위 수준 URL의 크롤링이 허용됩니다. |
| `/fish` | `/fish`로 시작하는 모든 경로와 일치합니다. 일치 여부에서는 대소문자를 구분합니다.

일치 항목:

-   `/fish`
-   `/fish.html`
-   `/fish/salmon.html`
-   `/fishheads`
-   `/fishheads/yummy.html`
-   `/fish.php?id=anything`

일치하지 않음:

-   `/Fish.asp`
-   `/catfish`
-   `/?id=fish`
-   `/desert/fish` |
| `/fish*` | `/fish`와 같습니다. 뒤쪽 와일드 카드는 무시됩니다.

일치 항목:

-   `/fish`
-   `/fish.html`
-   `/fish/salmon.html`
-   `/fishheads`
-   `/fishheads/yummy.html`
-   `/fish.php?id=anything`

일치하지 않음:

-   `/Fish.asp`
-   `/catfish`
-   `/?id=fish`
-   `/desert/fish` |
| `/fish/` | `/fish/` 폴더의 모든 항목과 일치합니다.

일치 항목:

-   `/fish/`
-   `/fish/?id=anything`
-   `/fish/salmon.htm`

일치하지 않음:

-   `/fish`
-   `/fish.html`
-   `/animals/fish/`
-   `/Fish/Salmon.asp` |
| `/*.php` | `.php`가 포함된 모든 경로와 일치합니다.

일치 항목:

-   `/index.php`
-   `/filename.php`
-   `/folder/filename.php`
-   `/folder/filename.php?parameters`
-   `/folder/any.php.file.html`
-   `/filename.php/`

일치하지 않음:

-   `/`(/index.php에 매핑하는 경우에도 해당)
-   `/windows.PHP` |
| `/*.php$` | `.php`로 끝나는 모든 경로와 일치합니다.

일치 항목:

-   `/filename.php`
-   `/folder/filename.php`

일치하지 않음:

-   `/filename.php?parameters`
-   `/filename.php/`
-   `/filename.php5`
-   `/windows.PHP` |
| `/fish*.php` | `/fish` 및 `.php`가 순서대로 포함된 모든 경로와 일치합니다.

일치 항목:

-   `/fish.php`
-   `/fishheads/catfish.php?parameters`

일치하지 않음:

`/Fish.PHP` |

## 규칙 우선순위

robots.txt 규칙을 URL과 일치시킬 때 크롤러는 규칙 경로 길이에 따라 가장 구체적인 규칙을 사용합니다. 와일드 카드가 있는 규칙을 포함하여 충돌하는 규칙의 경우 Google은 가장 제한이 적은 규칙을 사용합니다.

다음 예는 Google 크롤러가 주어진 URL에 적용할 규칙을 보여줍니다.

| 샘플 상황 | 샘플 상황 |
|---------------------------------|-------------------------------------------------------------------------------------------------------------|
| `https://example.com/page` | allow: /p
disallow: /

**적용 가능한 규칙**: `allow: /p`, 더 구체적이기 때문입니다. |
| `https://example.com/folder/page` | allow: /folder
disallow: /folder

**적용 가능한 규칙**: `allow: /folder`, 충돌하는 규칙의 경우 Google은 가장 제한이 적은 규칙을 사용하기 때문입니다. |
| `https://example.com/page.htm` | allow: /page
disallow: /*.htm

**적용 가능한 규칙**: `disallow: /*.htm`, 규칙 경로가 더 길고 URL 문자 중 일치하는 문자가 더 많아 더 구체적이기 때문입니다. |
| `https://example.com/page.php5` | allow: /page
disallow: /*.ph

**적용 가능한 규칙**: `allow: /page`, 충돌하는 규칙의 경우 Google은 가장 제한이 적은 규칙을 사용하기 때문입니다. |
| `https://example.com/` | allow: /$
disallow: /

**적용 가능한 규칙**: `allow: /$`, 더 구체적이기 때문입니다. |
| `https://example.com/page.htm` | allow: /$
disallow: /

**적용 가능한 규칙**: `disallow: /`, `allow` 규칙이 기준 URL에서만 적용되기 때문입니다. |