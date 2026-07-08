이 문서에서는 페이지 및 텍스트 수준 설정을 사용하여 Google 검색 결과에 나오는 콘텐츠를 제어하는 방법을 설명합니다. HTML 페이지나 HTTP 헤더에 `meta` 태그를 삽입하여 페이지 수준 설정을 지정할 수 있습니다. 페이지 내 HTML 요소에 `data-nosnippet` 속성을 사용하여 텍스트 수준 설정을 지정해도 됩니다.

이 설정은 크롤러가 해당 설정이 포함된 페이지에 액세스할 수 있어야만 읽히고 적용될 수 있습니다.

`<meta name="robots" content="noindex">` 규칙은 검색엔진 크롤러에 적용됩니다. `AdsBot-Google`과 같은 비검색 크롤러를 차단하려면 특정 크롤러에 타겟팅된 규칙(예: `<meta name="AdsBot-Google" content="noindex">`)을 추가해야 할 수 있습니다.

robots `meta` 태그를 사용하면 개별 페이지의 색인이 생성되는 방식과 Google 검색 결과에서 페이지가 사용자에게 게재되는 방식을 제어하는 자세한 페이지별 접근방식을 활용할 수 있습니다. 다음과 같이 robots `meta` 태그를 페이지의 `<head>` 섹션에 삽입합니다.

```php-template
<!DOCTYPE html>
<html><head>
  <meta name="robots" content="noindex">
  (…)
</head>
<body>(…)</body>
</html>
```

이 예에서 robots `meta` 태그는 검색엔진에 해당 페이지를 검색결과에 표시하지 말라고 지시합니다. `name` 속성의 값(`robots`)은 규칙이 모든 크롤러에 적용됨을 지정합니다. `name` 및 `content` 속성은 대소문자를 구분하지 않습니다. 특정 크롤러를 지정하려면 `name` 속성의 `robots` 값을 지정하려는 크롤러의 사용자 에이전트 토큰으로 바꿉니다. Google은 robots `meta` 태그에서 사용자 에이전트 토큰 2개를 지원하며 다른 값은 무시됩니다.

1.  `googlebot`: 모든 텍스트 결과에 적용됩니다.
2.  `googlebot-news`: 뉴스 검색결과에 적용됩니다.

예를 들어 Google이 검색 결과에 스니펫을 표시하지 않도록 구체적으로 지시하려면 `googlebot`을 `meta` 태그 이름으로 지정할 수 있습니다.

```php-template
<meta name="googlebot" content="nosnippet">
```

Google 웹 검색 결과에는 전체 스니펫을 표시하고 Google 뉴스에는 스니펫을 표시하지 않으려면 `googlebot-news`를 `meta` 태그 이름으로 지정합니다.

```php-template
<meta name="googlebot-news" content="nosnippet">
```

여러 개의 크롤러를 개별적으로 지정하려면 다음과 같이 robots `meta` 태그를 여러 개 사용합니다.

```php-template
<meta name="googlebot" content="notranslate">
<meta name="googlebot-news" content="nosnippet">
```

PDF 파일, 동영상 파일, 이미지 파일 등 HTML이 아닌 리소스의 색인 생성을 차단하려면 [`X-Robots-Tag` 응답 헤더](https://developers.google.com/search/docs/crawling-indexing/robots-meta-tag?hl=ko#xrobotstag)를 대신 사용합니다.

## `X-Robots-Tag` HTTP 헤더 사용

`X-Robots-Tag`는 지정한 URL에 대한 HTTP 헤더 응답의 요소로 사용될 수 있습니다. robots `meta` 태그에서 사용할 수 있는 규칙은 `X-Robots-Tag`로도 지정할 수 있습니다. 다음은 페이지의 색인을 생성하지 않도록 크롤러에 지시하는 `X-Robots-Tag`가 있는 HTTP 응답의 예입니다.

```yaml
HTTP/1.1 200 OK
Date: Tue, 25 May 2010 21:42:43 GMT
(…)
X-Robots-Tag: noindex
(…)
```

여러 `X-Robots-Tag` 헤더를 HTTP 응답에 결합하거나 쉼표로 구분된 규칙 목록을 지정할 수 있습니다. 다음은 `noimageindex` `X-Robots-Tag`와 `unavailable_after` `X-Robots-Tag`가 결합되어 있는 HTTP 헤더 응답의 예입니다.

```yaml
HTTP/1.1 200 OK
Date: Tue, 25 May 2010 21:42:43 GMT
(…)
X-Robots-Tag: noimageindex
X-Robots-Tag: unavailable_after: 25 Jun 2010 15:00:00 PST
(…)
```

`X-Robots-Tag`는 규칙 앞에 사용자 에이전트를 지정하기도 합니다. 예를 들어 다음 `X-Robots-Tag` HTTP 헤더 집합은 다양한 검색엔진에서 조건에 따라 페이지를 검색 결과에 표시하는 데 사용될 수 있습니다.

```yaml
HTTP/1.1 200 OK
Date: Tue, 25 May 2010 21:42:43 GMT
(…)
X-Robots-Tag: googlebot: nofollow
X-Robots-Tag: otherbot: noindex, nofollow
(…)
```

사용자 에이전트 없이 지정된 규칙은 모든 크롤러에 유효합니다. HTTP 헤더, 사용자 에이전트 이름, 지정된 값은 대소문자를 구분하지 않습니다.

## 유효한 색인 생성 및 게재 규칙

[기계 판독 가능 형식](https://developers.google.com/static/search/apis/ipranges/robots-tags.json?hl=ko)으로도 제공되는 다음 규칙을 사용하여 robots `meta` 태그 및 `X-Robots-Tag`와 함께 [스니펫](https://developers.google.com/search/docs/appearance/snippet?hl=ko)의 색인 생성 및 게재를 제어할 수 있습니다. 각 값은 특정 규칙을 나타냅니다. [여러 개의 규칙](https://developers.google.com/search/docs/crawling-indexing/robots-meta-tag?hl=ko#combined)을 쉼표로 구분된 목록 또는 별도의 `meta` 태그로 결합할 수 있습니다. 이러한 규칙은 대소문자를 구분하지 않습니다.

| 규칙 | 규칙 |
|------------------------------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| ### `all` | 색인 생성이나 게재 제한이 없습니다. 이 규칙은 기본값이므로 명시적으로 표시해도 아무 효과가 없습니다. |
| ### `noindex` | 검색결과에 이 페이지, 미디어 또는 리소스를 표시하지 않습니다. 이 규칙을 지정하지 않으면 페이지, 미디어 또는 리소스가 색인 생성되어 검색결과에 표시될 수 있습니다.

Google에서 정보를 삭제하려면 [단계별 안내](https://developers.google.com/search/docs/crawling-indexing/remove-information?hl=ko)를 따르세요. |
| ### `nofollow` | 이 페이지의 링크를 따라가지 않습니다. 이 규칙을 지정하지 않으면 Google에서는 페이지의 링크를 사용하여 링크된 페이지를 검색할 수 있습니다. [`nofollow`](https://developers.google.com/search/docs/crawling-indexing/qualify-outbound-links?hl=ko)에 관해 자세히 알아보세요. |
| ### `none` | `noindex, nofollow`와 같습니다. |
| ### `nosnippet` | 이 페이지에 관한 검색결과에 텍스트 스니펫 또는 동영상 미리보기를 표시하지 않습니다. 사용자 환경 개선을 위해 정적 썸네일 이미지(사용 가능한 경우)는 계속 표시될 수 있습니다. 이는 모든 형태의 검색 결과(Google 웹 검색, Google 이미지, 디스커버, AI 개요, AI 모드)에 적용되며 콘텐츠가 AI 개요 및 AI 모드에 직접 입력으로 사용되는 것을 방지합니다.

이 규칙을 지정하지 않으면 Google은 페이지에 있는 정보를 기반으로 텍스트 스니펫과 동영상 미리보기를 생성할 수 있습니다.

콘텐츠의 특정 섹션이 검색 결과 스니펫에 표시되지 않도록 하려면 [`data-nosnippet` HTML 속성](https://developers.google.com/search/docs/crawling-indexing/robots-meta-tag?hl=ko#data-nosnippet-attr)을 사용하세요. |
| ### `indexifembedded` | Google은 `noindex` 규칙이 사용되더라도 [`iframes`](https://developer.mozilla.org/docs/Web/HTML/Element/iframe) 또는 유사한 HTML 태그를 통해 다른 페이지에 삽입된 페이지 콘텐츠에 대한 색인을 생성할 수 있습니다.

`indexifembedded`는 `noindex`를 수반하는 경우에만 효과가 있습니다. |
| ### `max-snippet:` [number] | 이 검색결과의 텍스트 스니펫에 최대 [number]자(영문 기준)를 사용합니다. 참고로 URL 한 개가 검색결과 페이지 내에서 검색결과로 여러 번 표시될 수 있습니다. 이는 이미지 또는 동영상 미리보기에 영향을 주지 않으며 이는 모든 형태의 검색 결과(Google 웹 검색, Google 이미지, 디스커버, 어시스턴트, AI 개요, AI 모드)에 적용되며 콘텐츠가 AI 개요 및 AI 모드에 직접 입력으로 사용되는 것을 방지합니다. 그러나 이 제한은 게시자가 콘텐츠 사용 권한을 별도로 부여한 경우에는 적용되지 않습니다. 예를 들어 게시자가 콘텐츠를 구조화된 인페이지 데이터의 형태로 제공하거나 Google과 라이선스 계약을 체결했다면 더 구체적으로 사용이 허용된 작업은 이 설정으로 인한 제약을 받지 않습니다. 이 규칙은 파싱 가능한 [number]가 지정되지 않으면 무시됩니다.

규칙을 지정하지 않으면 Google에서 스니펫의 길이를 선택합니다.

특수 값:

-   `0`: 표시할 스니펫이 없습니다. `nosnippet`과 같습니다.
-   `-1`: Google에서 사용자가 콘텐츠를 발견하고 사용자를 사이트로 유도하는 데 가장 효과적인 스니펫 길이를 선택합니다.

예:

검색결과에 스니펫이 표시되지 않도록 하려면 다음과 같이 입력합니다.

<meta name="robots" content="max-snippet:0">

스니펫에 최대 20자(영문 기준)만 표시되도록 하려면 다음과 같이 입력합니다.

<meta name="robots" content="max-snippet:20">

스니펫에 표시할 수 있는 문자 수 제한을 없애려면 다음과 같이 입력합니다.

<meta name="robots" content="max-snippet:-1"> |
| ### `max-image-preview:` [setting] | 검색결과에 이 페이지가 표시될 때 사용할 미리보기 이미지의 최대 크기를 설정합니다.

`max-image-preview` 규칙을 지정하지 않으면 Google에서는 기본 크기의 미리보기 이미지를 표시할 수 있습니다.

허용되는 [setting] 값은 다음과 같습니다.

-   `none`: 표시할 미리보기 이미지가 없습니다.
-   `standard`: 기본 미리보기 이미지가 표시될 수 있습니다.
-   `large`: 미리보기 이미지가 표시 영역 너비까지 더 크게 표시될 수 있습니다.

이는 Google 웹 검색, Google 이미지, 디스커버, 어시스턴트 등 모든 형태의 검색결과에 적용됩니다. 그러나 이 제한은 게시자가 콘텐츠 사용 권한을 별도로 부여한 경우에는 적용되지 않습니다. 예를 들어 게시자가 콘텐츠를 구조화된 인페이지 데이터 형태로 제공하거나(예: 기사의 AMP 및 표준 버전) Google과 라이선스 계약을 체결했다면 더 구체적으로 사용이 허용된 작업은 이 설정으로 인한 제약을 받지 않습니다.

Google 검색이나 디스커버에서 기사의 AMP 페이지와 표준 버전이 표시될 때 Google에서 더 큰 썸네일 이미지를 사용하는 것을 원하지 않으면 `max-image-preview` 값을 `standard`나 `none`으로 지정합니다.

예:

<meta name="robots" content="max-image-preview:standard"> |
| ### `max-video-preview:` [number] | 검색결과에서 이 페이지의 동영상 스니펫에 최대 [number]초를 사용합니다.

`max-video-preview` 규칙을 지정하지 않으면 Google에서 검색결과에 동영상 스니펫을 표시할 수 있습니다. 미리보기 시간은 Google에서 결정하게 됩니다.

특수 값:

-   `0`: `max-image-preview` 설정에 따라 정적 이미지만 사용할 수 있습니다.
-   `-1`: 제한이 없습니다.

이는 Google 웹 검색, Google 이미지, Google 비디오, 디스커버, 어시스턴트 등 모든 형태의 검색결과에 적용됩니다. 이 규칙은 파싱 가능한 [number]가 지정되지 않으면 무시됩니다.

예:

<meta name="robots" content="max-video-preview:-1"> |
| ### `notranslate` | 검색결과에 이 페이지의 번역을 제공하지 않습니다. 이 규칙을 지정하지 않으면 Google에서 검색어 언어로 되어 있지 않은 검색결과의 [제목 링크 및 스니펫 번역](https://developers.google.com/search/docs/appearance/translated-results?hl=ko)을 제공할 수 있습니다. 사용자가 번역된 제목 링크를 클릭하면 이후 사용자와 페이지 간의 모든 상호작용은 Google 번역을 통해 이루어지며, 따라서 어떤 링크로 이동하든 자동으로 번역됩니다. |
| ### `noimageindex` | 이 페이지의 이미지를 색인 생성하지 않습니다. 값을 지정하지 않으면 페이지의 이미지가 색인 생성되고 검색결과에 표시될 수 있습니다. |
| ### `unavailable_after:` [date/time] | 지정된 날짜/시간 후에는 검색결과에 이 페이지를 표시하지 않습니다. 날짜/시간은 [RFC 822](https://www.ietf.org/rfc/rfc0822.txt), [RFC 850](https://www.ietf.org/rfc/rfc0850.txt), [ISO 8601](https://www.iso.org/iso-8601-date-and-time-format.html) 등 널리 사용되는 형식으로 표현해야 합니다. 유효한 날짜/시간을 지정하지 않으면 규칙이 무시됩니다. 기본적으로 콘텐츠의 만료일은 없습니다.

이 규칙을 지정하지 않으면 이 페이지가 무기한으로 검색결과에 표시될 수 있습니다. Googlebot은 지정된 날짜와 시간이 지나면 URL의 크롤링 속도를 상당히 낮춥니다.

예:

<meta name="robots" content="unavailable_after: 2020-09-21"> |

### 과거 및 기타 사용되지 않는 규칙 참조

다음 규칙은 Google 검색에서 사용되지 않으며 무시됩니다. 그러나 사용자가 자주 묻거나 Google에서 과거에 사용했던 규칙이기 때문에 여기에 포함시켰습니다.

### 과거 및 기타 사용되지 않는 규칙 참조

### 과거 및 기타 사용되지 않는 규칙 참조

| 과거 및 기타 사용되지 않는 규칙 | 과거 및 기타 사용되지 않는 규칙 |
|--------------------------|-----------------------------------------------------------------------------------------------------------------|
| ### `noarchive` | 저장된 페이지 링크 기능이 더 이상 존재하지 않으므로 Google 검색에서는 저장된 페이지 링크가 검색 결과에 표시되는지 여부를 제어하는 데 이 `noarchive` 규칙을 더 이상 사용하지 않습니다. |
| ### `nocache` | Google 검색에서는 `nocache` 규칙을 사용하지 않습니다. |
| ### `nositelinkssearchbox` | 해당 기능이 더 이상 존재하지 않으므로 Google 검색에서 특정 페이지에 대한 사이트링크 검색창 표시 여부를 제어하는 데 이 `nositelinkssearchbox` 규칙을 더 이상 사용하지 않습니다. |

## 결합된 색인 생성 및 게재 규칙 처리

robots `meta` 태그 규칙을 쉼표로 결합하거나 여러 개의 `meta` 태그를 사용하여 여러 규칙이 포함된 지침을 만들 수 있습니다. 다음은 페이지의 색인을 생성하지 말고 페이지에 있는 어떤 링크도 크롤링하지 않도록 웹 크롤러에 지시하는 robots `meta` 태그의 예입니다.

[쉼표로 구분된 목록](https://developers.google.com/search/docs/crawling-indexing/robots-meta-tag?hl=ko/#쉼표로-구분된-목록)[여러 `meta` 태그](https://developers.google.com/search/docs/crawling-indexing/robots-meta-tag?hl=ko/#여러-meta-태그) 더보기

```php-template
<meta name="robots" content="noindex, nofollow">
```

```php-template
<meta name="robots" content="noindex">
<meta name="robots" content="nofollow">
```

다음은 텍스트 스니펫을 20자(영문 기준)로 제한하고 큰 미리보기 이미지를 허용하는 예입니다.

```php-template
<meta name="robots" content="max-snippet:20, max-image-preview:large">
```

여러 크롤러가 다른 규칙과 함께 지정된 경우 검색엔진은 부정 규칙을 모두 사용합니다. 예를 들면 다음과 같습니다.

```php-template
<meta name="robots" content="nofollow">
<meta name="googlebot" content="noindex">
```

이러한 `meta` 태그를 포함하는 페이지는 Googlebot이 크롤링할 때 `noindex, nofollow` 규칙이 있는 것으로 해석됩니다.

## `data-nosnippet` HTML 속성 사용

HTML 페이지의 텍스트 중에서 스니펫으로 사용하지 않을 텍스트를 지정할 수 있습니다. 이 작업은 `span`, `div` 및 `section` 요소에 `data-nosnippet` HTML 속성을 사용해 HTML 요소 수준에서 할 수 있습니다. `data-nosnippet`은 [불리언 속성](https://html.spec.whatwg.org/multipage/common-microsyntaxes.html#boolean-attributes)으로 간주됩니다. 모든 부울 속성과 마찬가지로, 지정된 모든 값은 무시됩니다. 인식 정확도를 높이려면 HTML 섹션이 유효한 HTML이어야 하며 모든 태그가 제대로 닫혀 있어야 합니다.

예:

```php-template
<p>This text can be shown in a snippet
<span data-nosnippet>and this part would not be shown</span>.</p>

<div data-nosnippet>not in snippet</div>
<div data-nosnippet="true">also not in snippet</div>
<div data-nosnippet="false">also not in snippet</div>
<!-- all values are ignored -->

<div data-nosnippet>some text</html>
<!-- unclosed "div" will include all content afterwards -->

<mytag data-nosnippet>some text</mytag>
<!-- NOT VALID: not a span, div, or section -->

<p>This text can be shown in a snippet.</p>
<div data-nosnippet>
<p>However, this is not in snippet.</p>
<ul>
  <li>Stuff not in snippet</li>
  <li>More stuff not in snippet</li>
</ul>
</div>
```

일반적으로 Google은 페이지 색인 생성을 위해 페이지를 렌더링하지만 렌더링이 보장되지는 않습니다. 이 때문에 렌더링 전후에 모두 `data-nosnippet` 추출이 발생할 수 있습니다. 렌더링에서 비롯되는 불확실성을 피하기 위해 JavaScript를 통해 기존 노드의 `data-nosnippet` 속성을 추가하거나 삭제하면 안 됩니다. JavaScript를 통해 DOM 요소를 추가할 때 페이지의 DOM에 요소를 처음 추가한다면 필요에 따라 `data-nosnippet` 속성을 추가합니다. 맞춤 요소를 사용하는 경우 `data-nosnippet`을 사용해야 하면 `div`, `span` 또는 `section` 요소를 사용하여 래핑하거나 렌더링합니다.

## 구조화된 데이터 사용

Robots `meta` 태그는 Google이 검색 결과로 표시하기 위해 웹 페이지에서 자동으로 추출하는 콘텐츠의 양을 지정합니다. 하지만 대다수 게시자가 특정 정보의 [검색 표시](https://developers.google.com/search/docs/appearance/structured-data/intro-structured-data?hl=ko)를 위해 schema.org 구조화된 데이터도 사용합니다. Robots `meta` 태그 제한은 구조화된 데이터를 사용하는 데 영향을 미치지 않지만 다른 광고 소재 작업에서 지정된 구조화된 데이터의 `article.description` 및 `description` 값에는 예외적으로 영향을 미칩니다. `description` 값에 따라 미리보기의 최대 길이를 지정하려면 `max-snippet` 규칙을 사용하세요. 예를 들어 텍스트 미리보기가 제한되는 경우에도 페이지에 표시된 구조화된 데이터 `recipe`는 레시피 캐러셀에 포함될 수 있습니다. `max-snippet`을 사용하면 텍스트 미리보기의 길이를 제한할 수 있지만, 이 정보가 구조화된 데이터를 사용해 리치 결과용으로 제공되는 경우 이 robots `meta` 태그는 적용되지 않습니다.

웹페이지의 구조화된 데이터 사용 방식을 관리하려면 구조화된 데이터 유형과 값 자체를 수정하면 됩니다. 정보를 추가 또는 삭제하면 원하는 데이터만 제공할 수 있습니다. 또한 `data-nosnippet` 요소 내에서 선언될 경우 구조화된 데이터는 검색 결과에 사용 가능한 상태로 남아 있습니다.

## `X-Robots-Tag`의 실제 구현

사이트의 웹 서버 소프트웨어의 구성 파일을 통해 `X-Robots-Tag`를 사이트의 HTTP 응답에 추가할 수 있습니다. 예를 들어 Apache 기반 웹 서버에서는 .htaccess 파일과 httpd.conf 파일을 사용할 수 있습니다. `X-Robots-Tag`를 HTTP 응답과 함께 사용할 때 좋은 점은 사이트에 전체적으로 적용되는 크롤링 규칙을 지정할 수 있다는 것입니다. 정규 표현식이 지원되어 매우 유연하게 지시어를 지정할 수 있습니다.

예를 들어 전체 사이트에서 모든 `.PDF` 파일의 HTTP 응답에 `noindex, nofollow` `X-Robots-Tag`를 추가하려면 다음 스니펫을 Apache에서는 사이트의 루트 `.htaccess` 파일이나 `httpd.conf` 파일에 추가하고, NGINX에서는 사이트의 `.conf` 파일에 추가하세요.

[Apache](https://developers.google.com/search/docs/crawling-indexing/robots-meta-tag?hl=ko/#apache)[NGINX](https://developers.google.com/search/docs/crawling-indexing/robots-meta-tag?hl=ko/#nginx) 더보기

```bash
<Files ~ "\.pdf$">
Header set X-Robots-Tag "noindex, nofollow"
</Files>
```

```ruby
location ~* \.pdf$ {
add_header X-Robots-Tag "noindex, nofollow";
}
```

HTML에 robots `meta` 태그를 사용할 수 없는 이미지 파일처럼 HTML이 아닌 파일에는 `X-Robots-Tag`를 사용할 수 있습니다. 다음은 전체 사이트에서 이미지 파일(`.png`, `.jpeg`, `.jpg`, `.gif`)에 `noindex` `X-Robots-Tag` 규칙을 추가하는 예입니다.

[Apache](https://developers.google.com/search/docs/crawling-indexing/robots-meta-tag?hl=ko/#apache)[NGINX](https://developers.google.com/search/docs/crawling-indexing/robots-meta-tag?hl=ko/#nginx) 더보기

```bash
<Files ~ "\.(png|jpe?g|gif)$">
Header set X-Robots-Tag "noindex"
</Files>
```

```ruby
location ~* \.(png|jpe?g|gif)$ {
add_header X-Robots-Tag "noindex";
}
```

개별 정적 파일의 `X-Robots-Tag` 헤더를 설정할 수도 있습니다.

[Apache](https://developers.google.com/search/docs/crawling-indexing/robots-meta-tag?hl=ko/#apache)[NGINX](https://developers.google.com/search/docs/crawling-indexing/robots-meta-tag?hl=ko/#nginx) 더보기

```makefile
# the htaccess file must be placed in the directory of the matched file.
<Files "unicorn.pdf">
Header set X-Robots-Tag "noindex, nofollow"
</Files>
```

```bash
location = /secrets/unicorn.pdf {
add_header X-Robots-Tag "noindex, nofollow";
}
```

## robots.txt 규칙과 색인 생성 및 게재 규칙 결합

robots `meta` 태그와 `X-Robots-Tag` HTTP 헤더는 URL을 크롤링할 때 발견됩니다. robots.txt 파일을 통해 페이지 크롤링이 금지된 경우 색인 생성 또는 게재 규칙에 관한 정보는 찾을 수 없으므로 무시됩니다. 색인 생성 또는 게재 규칙을 따라야 한다면 해당 규칙이 포함된 URL의 크롤링을 금지하면 안 됩니다.