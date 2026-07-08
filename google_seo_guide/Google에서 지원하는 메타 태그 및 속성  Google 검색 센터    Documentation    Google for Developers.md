이 페이지에서는 `meta` 태그의 정의, Google에서 색인 생성을 제어하기 위해 지원하는 `meta` 태그 및 HTML 속성, `meta` 태그를 구현할 때 유의해야 할 기타 중요한 사항을 설명합니다.

<iframe frameborder="0" allowfullscreen="" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share" referrerpolicy="strict-origin-when-cross-origin" width="640" height="360" src="https://www.youtube.com/embed/RBTBEfd7z_Y?origin=https%3A%2F%2Fdevelopers.google.com&amp;autoplay&amp;controls&amp;embed_domain&amp;enablejsapi=1&amp;end&amp;hl&amp;showinfo&amp;start&amp;video-id=RBTBEfd7z_Y&amp;widgetid=13&amp;forigin=https%3A%2F%2Fdevelopers.google.com%2Fsearch%2Fdocs%2Fcrawling-indexing%2Fspecial-tags%3Fhl%3Dko&amp;aoriginsup=1&amp;gporigin=https%3A%2F%2Fdevelopers.google.com%2Fsearch%2Fdocs%2Fcrawling-indexing%2Famp%2Fabout-amp%3Fhl%3Dko&amp;vf=1" id="widget14" data-title="YouTube video player" title="How much time should I spend on meta tags, and which ones matter?"></iframe>

`meta` 태그는 검색엔진과 기타 클라이언트에 페이지에 대한 추가 정보를 제공하는 데 사용되는 HTML 태그입니다. 클라이언트는 `meta` 태그를 처리하고 지원하지 않는 태그는 무시합니다. `meta` 태그는 HTML 페이지의 `<head>` 섹션에 추가되며 형식은 일반적으로 다음과 같습니다.

```php-template
<!DOCTYPE html>
  <html>
  <head>
    <meta charset="utf-8">
    <meta name="description" content="Author: A.N. Author, Illustrator: P. Picture, Category: Books, Price:  £9.24, Length: 784 pages">
    <meta name="google-site-verification" content="+nxGUDJ4QpAZ5l9Bsjdi102tLVC21AIh5d1Nl23908vVuFHs34=">
    <title>Example Books - high-quality used books for children</title>
    <meta name="robots" content="noindex,nofollow">
  </head>
</html>
```

Google에서는 다음 `meta` 태그를 지원합니다.

| Google에서 지원하는 `meta` 태그 목록 | Google에서 지원하는 `meta` 태그 목록 |
|------------------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| ### 설명 | <meta name="description" content="A description of the page">

이 태그를 사용하여 간단한 페이지 설명을 제공하세요. 페이지 설명은 [검색 결과에 표시되는 스니펫](https://developers.google.com/search/docs/appearance/snippet?hl=ko)에 사용되기도 합니다. |
| ### robots and googlebot | <meta name="robots" content="..., ...">

<meta name="googlebot" content="..., ...">

이 `meta` 태그는 검색엔진의 크롤링 및 색인 생성 동작을 제어합니다.

`<meta name="robots" ...` 태그는 모든 검색엔진에 적용되지만 `<meta name="googlebot ...` 태그는 Google에만 적용됩니다.

`robots`(또는 `googlebot`) `meta` 태그가 충돌하는 경우 더 제한적인 태그가 적용됩니다. 예를 들어 페이지에 `max-snippet:50` 태그와 `nosnippet` 태그가 둘 다 있는 경우 `nosnippet` 태그가 적용됩니다.

기본값은 `index, follow`이며 별도로 지정하지 않아도 됩니다. Google에서 지원하는 값의 전체 목록은 [유효한 규칙 목록](https://developers.google.com/search/docs/crawling-indexing/robots-meta-tag?hl=ko#directives)을 참고하세요.

`X-Robots-Tag` HTTP 헤더 규칙을 사용하여 페이지 헤더에 이 정보를 지정할 수도 있습니다. 이 방법은 그래픽 또는 다른 종류의 문서와 같이 HTML이 아닌 파일의 색인 생성을 제한하고 싶을 때 특히 유용합니다. [robots `meta` 태그에 관해 자세히 알아보기](https://developers.google.com/search/docs/crawling-indexing/robots-meta-tag?hl=ko) |
| ### notranslate | <meta name="googlebot" content="notranslate">

Google에서 페이지 콘텐츠가 사용자의 선호 언어로 작성되지 않았다고 판단하는 경우 검색 결과에 [번역된 제목 링크와 스니펫](https://developers.google.com/search/docs/appearance/translated-results?hl=ko)을 제공할 수도 있습니다. 사용자가 번역된 제목 링크를 클릭하면 이후 사용자와 페이지 간의 모든 상호작용은 Google 번역을 통해 이루어지고, 이후 이동하는 모든 링크가 자동으로 번역됩니다. 번역 링크를 통해 보다 많은 사용자에게 독특하고 매력적인 콘텐츠를 제공할 수 있습니다. 그러나 번역 링크를 원하지 않을 경우에는 이 `meta` 태그를 사용하여 Google에서 페이지 번역을 제공하지 않도록 할 수 있습니다. |
| ### nopagereadaloud | <meta name="google" content="nopagereadaloud">

다양한 [Google TTS(텍스트 음성 변환) 서비스](https://developers.google.com/search/docs/crawling-indexing/read-aloud-user-agent?hl=ko)에서 TTS(텍스트 음성 변환)를 사용하여 웹페이지를 소리 내어 읽는 것을 방지합니다. |
| ### google-site-verification | <meta name="google-site-verification" content="...">

사이트의 최상위 페이지에서 이 태그를 사용하여 [Search Console에 필요한 사이트 소유권을 확인](https://support.google.com/webmasters/answer/9008080?hl=ko)할 수 있습니다. `name` 및 `content` 속성의 값이 사용자에게 제공된 값과 정확하게 일치해야 하지만(대소문자 포함), XHTML에서 HTML로 태그를 변경하거나 태그의 형식이 페이지 형식과 일치하는지 여부는 상관없습니다. |
| ### Content-Type and charset | <meta http-equiv="Content-Type" content="...; charset=...">

<meta charset="...">

이 태그는 페이지의 콘텐츠 유형과 문자 집합을 각각 정의합니다. [`http-equiv`](https://developer.mozilla.org/en-US/docs/Web/HTML/Element/meta#attr-http-equiv) `meta` 태그의 `content` 속성 값의 양쪽을 따옴표로 묶어야 합니다. 그렇지 않으면 [`charset`](https://developer.mozilla.org/en-US/docs/Web/HTML/Element/meta#charset) 속성이 잘못 해석될 수도 있습니다. 가능한 경우 Unicode/UTF-8을 사용하는 것이 좋습니다. |
| ### 새로고침 | <meta http-equiv="refresh" content="...;url=...">

보통 메타 새로고침이라고 하는 이 태그는 일정 시간 후에 사용자를 새 URL로 보내는 태그로, 간단한 리디렉션 방법으로 사용되기도 합니다. 그러나 [모든 브라우저에서 지원되는 것은 아니므로 사용자에게 혼란을 초래할 수 있습니다](https://www.w3.org/TR/WCAG10-HTML-TECHS/#meta-element). Google에서는 대신 서버 측 [`301` 리디렉션](https://developers.google.com/search/docs/crawling-indexing/301-redirects?hl=ko)을 사용할 것을 권장합니다. |
| ### viewport | <meta name="viewport" content="...">

휴대기기에서 페이지를 렌더링하는 방법을 브라우저에 알리는 태그입니다. 이 태그를 사용하면 페이지가 모바일 친화적이라는 사실을 Google에 알릴 수 있습니다. [`viewport` `meta` 태그를 구성하는 방법 자세히 알아보기](https://web.dev/articles/responsive-web-design-basics?hl=ko#size-content) |
| ### rating | <meta name="rating" content="adult">

<meta name="rating" content="RTA-5042-1996-1400-1577-RTA">

선정적인 성인용 콘텐츠가 포함된 페이지라는 라벨을 지정하여 세이프서치 검색 결과에서 필터링되도록 합니다. [세이프서치 페이지 라벨 지정에 관해 자세히 알아보기](https://developers.google.com/search/docs/crawling-indexing/safesearch?hl=ko) |

## HTML 태그 속성

[HTML 태그 속성](https://developer.mozilla.org/docs/Web/HTML/Attributes)은 상위 태그를 구성하는 HTML 태그의 추가 값입니다. 예를 들어 `<a>` 태그의 `href` 속성은 앵커 태그가 가리키는 `<a **href="https://example.com/"**...>`과 같은 리소스를 구성합니다.

Google 검색은 색인 생성을 위해 HTML 속성의 수를 제한합니다. `src` 및 `href`와 같은 속성은 이미지 및 URL 등의 리소스를 검색하는 데 사용됩니다. Google에서는 사이트 소유자가 외부 연결 링크의 관계를 알릴 수 있도록 다양한 [`rel` 속성](https://developers.google.com/search/docs/crawling-indexing/qualify-outbound-links?hl=ko)도 지원합니다.

`div`, `span`, `section` 태그의 [`data-nosnippet` 속성](https://developers.google.com/search/docs/crawling-indexing/robots-meta-tag?hl=ko#data-nosnippet-attr)을 사용하면 HTML 페이지의 일부를 스니펫에서 제외할 수 있습니다.

## 기타 주의사항

-   Google은 페이지에 사용된 코드와 관계없이 HTML 및 XHTML 형식 `meta` 태그를 모두 읽을 수 있습니다.
-   자동 인식 정확도를 높이려면 `head` 섹션이 [유효한 HTML](https://developers.google.com/search/docs/crawling-indexing/valid-page-metadata?hl=ko)이어야 하며 속성의 경우 모든 상위 태그가 제대로 닫혀 있어야 합니다.
-   `google-site-verification`의 경우를 제외하면 `meta` 태그에서 대소문자는 보통 중요하지 않습니다.
-   사이트에 중요한 경우 다른 `meta` 태그를 사용할 수 있지만 Google에서 지원하지 않는 `meta` 태그는 무시됩니다.
-   자바스크립트를 사용하여 `meta` 태그를 삽입하거나 변경하는 것을 고려하는 경우 주의해야 합니다. 가능한 경우 자바스크립트를 사용하여 `meta` 태그를 삽입하거나 변경하지 않는 것이 좋습니다. 자바스크립트를 사용해야 하는 경우 [구현을 철저히 테스트](https://developers.google.com/search/docs/crawling-indexing/javascript/fix-search-javascript?hl=ko)하세요.
-   페이지의 `meta` 태그와 속성을 확인하려면 [URL 검사 도구](https://support.google.com/webmasters/answer/9012289?hl=ko)를 사용하세요.

다음 태그 및 속성은 Google 검색에서 지원되지 않으며 무시됩니다. 그러나 여기에서는 HTML에서 흔히 사용되거나 과거 Google에서 지원한 태그 및 속성을 포함합니다.

| 지원하지 않는 태그 및 속성 | 지원하지 않는 태그 및 속성 |
|--------------------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| 메타 키워드 태그 | `<meta name="keywords" content="...">` 메타 키워드 태그는 Google 검색에서 사용되지 않으며 색인 생성 및 순위 지정에 전혀 영향을 미치지 않습니다. |
| HTML 태그 `lang` 속성 | Google 검색은 페이지의 텍스트 콘텐츠를 토대로 페이지의 언어를 감지합니다. `lang`와 같은 코드 주석을 사용하지 않습니다. |
| `next` 및 `prev` `rel` 속성 값 | <link rel="next" href="...">

<link rel="prev" href="...">

Google에서는 이러한 HTML `<link>` 태그를 더 이상 사용하지 않으며 색인 생성에 영향을 미치지 않습니다. |
| ### nositelinkssearchbox | <meta name="google" content="nositelinkssearchbox">

해당 기능이 더 이상 존재하지 않으므로 Google 검색에서 특정 페이지에 대한 사이트링크 검색창 표시 여부를 제어하는 데 이 `nositelinkssearchbox` 규칙을 더 이상 사용하지 않습니다. |