URL 리디렉션은 기존 URL을 다른 URL과 연결 지어 방문자와 Google 검색에 페이지의 위치가 새로 지정되었음을 효과적으로 알리는 방법입니다. 리디렉션은 다음 상황에서 특히 유용합니다.

-   사이트를 새로운 도메인으로 옮기고 사이트 이전을 최대한 원활하게 진행하고자 하는 경우
-   사용자가 여러 다른 URL을 통해 사이트에 액세스하는 경우: 예를 들어, `https://example.com/home`, `http://home.example.com` 또는 `https://www.example.com`과 같이 여러 방법으로 홈페이지에 액세스할 수 있다면 이러한 URL 중 하나를 선호([표준](https://developers.google.com/search/docs/crawling-indexing/consolidate-duplicate-urls?hl=ko#definition))하는 목적지로 선택하고 리디렉션을 사용하여 다른 URL에서 선호하는 URL로 트래픽을 전송하는 것이 좋습니다.
-   두 웹사이트를 통합하면서 이전 URL 링크가 정확한 페이지로 리디렉션되게 하려는 경우
-   페이지를 삭제하여 사용자를 새 페이지로 유도하려는 경우

## 리디렉션 유형 개요

일반적으로 사용자는 서로 다른 유형의 리디렉션 차이를 분별할 수 없지만, Google 검색에서는 특정 유형의 리디렉션을 리디렉션 대상이 표준이어야 한다는 신호로 삼습니다. 어떤 리디렉션을 선택할지는 리디렉션의 예상 시간과 Google 검색의 검색 결과에 표시하려는 페이지에 따라 다릅니다.

-   **영구 리디렉션**: 검색결과에 새 리디렉션 대상을 표시합니다.
-   **임시 리디렉션**: 검색결과에 소스 페이지를 표시합니다.

다음 표에는 영구 리디렉션과 임시 리디렉션을 설정하는 다양한 방법이 설명되어 있습니다. 순서는 Google에서 올바르게 해석할 가능성이 높은 순으로 되어 있습니다(예: 서버 측 리디렉션이 올바르게 해석될 가능성이 가장 높음). 상황과 사이트에 맞는 리디렉션 유형을 선택합니다.

| 리디렉션 유형 | 리디렉션 유형 |
|---------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| 영구 | Googlebot이 리디렉션을 따르고, 색인 생성 파이프라인은 리디렉션 대상이 [표준](https://developers.google.com/search/docs/crawling-indexing/consolidate-duplicate-urls?hl=ko#definition)이어야 한다는 신호로 리디렉션을 사용합니다.

`HTTP 301 (moved permanently)`

[서버 측 리디렉션](https://developers.google.com/search/docs/crawling-indexing/301-redirects?hl=ko#serverside)을 설정합니다.

`HTTP 308 (moved permanently)`

`meta refresh`(0초)

[`meta refresh` 리디렉션](https://developers.google.com/search/docs/crawling-indexing/301-redirects?hl=ko#metarefresh)을 설정합니다.

HTTP 새로고침(0초)

JavaScript `location`

[자바스크립트 리디렉션](https://developers.google.com/search/docs/crawling-indexing/301-redirects?hl=ko#jslocation)을 설정합니다.

Crypto 리디렉션

[crypto 리디렉션](https://developers.google.com/search/docs/crawling-indexing/301-redirects?hl=ko#cryptoredirects)에 관해 자세히 알아보세요. |
| 임시 | Googlebot은 리디렉션을 따르지만 색인 생성 파이프라인은 리디렉션을 리디렉션 대상이 표준이어야 한다는 신호로 사용하지 않습니다. 다른 표준화 신호가 있는 경우 대상 페이지의 색인이 계속 생성될 수 있습니다.

`HTTP 302 (found)`

[서버 측 리디렉션](https://developers.google.com/search/docs/crawling-indexing/301-redirects?hl=ko#serverside)을 설정합니다.

`HTTP 303 (see other)`

`HTTP 307 (temporary redirect)`

`meta refresh`(0초 이상)

[`meta refresh` 리디렉션](https://developers.google.com/search/docs/crawling-indexing/301-redirects?hl=ko#metarefresh)을 설정합니다.

`HTTP refresh`(0초 이상) |

## 서버 측 리디렉션

서버 측 리디렉션을 설정하려면 서버 구성 파일(예: Apache의 `.htaccess` 파일)에 액세스하거나 서버 측 스크립트(예: PHP)를 사용하여 리디렉션 헤더를 설정해야 합니다. 서버 측에는 영구 리디렉션과 임시 리디렉션을 모두 만들 수 있습니다.

### 영구 서버 측 리디렉션

<iframe frameborder="0" allowfullscreen="" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share" referrerpolicy="strict-origin-when-cross-origin" width="640" height="360" src="https://www.youtube.com/embed/OJEXnCKxV88?origin=https%3A%2F%2Fdevelopers.google.com&amp;autoplay&amp;controls&amp;embed_domain&amp;enablejsapi=1&amp;end&amp;hl&amp;showinfo&amp;start&amp;video-id=OJEXnCKxV88&amp;widgetid=17&amp;forigin=https%3A%2F%2Fdevelopers.google.com%2Fsearch%2Fdocs%2Fcrawling-indexing%2F301-redirects%3Fhl%3Dko&amp;aoriginsup=1&amp;gporigin=https%3A%2F%2Fdevelopers.google.com%2Fsearch%2Fdocs%2Fcrawling-indexing%2Famp%2Fabout-amp%3Fhl%3Dko&amp;vf=1" id="widget18" data-title="YouTube video player" title="Processing 301 redirects"></iframe>

검색엔진 결과에 표시되는 대로 페이지의 URL을 변경해야 하는 경우 가능하면 영구 서버 측 리디렉션을 사용하는 것이 좋습니다. 이는 Google 검색과 사용자를 정확한 페이지로 이동하도록 하는 최상의 방법입니다. `301` 및 `308` 상태 코드는 페이지가 새 위치로 영구 이전했다는 의미입니다.

### 임시 서버 측 리디렉션

사용자를 임시로 다른 페이지로 보내려고 할 때 임시 리디렉션을 사용합니다. 이렇게 하면 Google이 리디렉션의 영향을 받지 않으므로 이전 URL이 Google 검색 결과에 유지될 수 있습니다. 예를 들어 사이트에서 제공하는 서비스가 일시적으로 사용할 수 없게 된 경우, 임시 리디렉션을 설정하여 현재 상황을 설명하는 페이지로 사용자를 리디렉션할 수 있습니다. 이 경우 검색 결과에 표시되는 원래 URL이 손상되지도 않습니다.

### 서버 측 리디렉션 구현

서버 측 리디렉션의 구현은 호스팅 환경과 서버 환경 또는 사이트 백엔드의 스크립트 언어에 따라 다릅니다.

PHP로 영구 리디렉션을 설정하려면 `header()` 함수를 사용합니다. 화면에 항목을 전송하기 전에 헤더를 먼저 설정해야 합니다.

```less
header('HTTP/1.1 301 Moved Permanently');
header('Location: https://www.example.com/newurl');
exit();
```

마찬가지로 다음은 PHP를 사용하여 임시 리디렉션을 설정하는 방법의 예입니다.

```less
header('HTTP/1.1 302 Found');
header('Location: https://www.example.com/newurl');
exit();
```

웹 서버 구성 파일에 액세스 권한이 있으면 직접 리디렉션 규칙을 작성할 수 있습니다. 웹 서버의 가이드를 따르세요.

-   **Apache:** [Apache `.htaccess` 튜토리얼](https://httpd.apache.org/docs/2.0/howto/htaccess.html), [Apache URL 재작성 가이드](https://httpd.apache.org/docs/2.0/misc/rewriteguide.html) 및 [Apache `mod_alias` 문서](https://httpd.apache.org/docs/current/mod/mod_alias.html)를 참고하세요. 예를 들어 `mod_alias`를 사용하여 가장 간단한 형태의 리디렉션을 설정할 수 있습니다.
    
    ```bash
    # Permanent redirect:
    Redirect permanent "/old" "https://example.com/new"
    
    # Temporary redirect:
    Redirect temp "/two-old" "https://example.com/two-new"
    ```
    
    더 복잡한 리디렉션의 경우 `mod_rewrite`를 사용합니다. 예를 들면 다음과 같습니다.
    
    ```graphql
    RewriteEngine on
    # redirect the service page to a new page with a permanent redirect
    RewriteRule   "^/service$"  "/about/service"  [R=301]
    
    # redirect the service page to a new page with a temporary redirect
    RewriteRule   "^/service$"  "/about/service"  [R]
    ```
    
-   **NGINX:** NGINX 블로그에서 [NGINX 재작성 규칙 만들기](https://www.nginx.com/blog/creating-nginx-rewrite-rules/)를 읽어보세요. Apache를 사용할 때와 마찬가지로 여러 가지 방법 중에서 선택하여 리디렉션을 만들 수 있습니다. 예를 들면 다음과 같습니다.
    
    ```php
    location = /service {
    # for a permanent redirect
    return 301 $scheme://example.com/about/service
    
    # for a temporary redirect
    return 302 $scheme://example.com/about/service
    }
    ```
    
    더 복잡한 리디렉션에는 `rewrite` 규칙을 사용합니다.
    
    ```bash
    location = /service {
    # for a permanent redirect
    rewrite service?name=$1 ^service/offline/([a-z]+)/?$ permanent;
    
    # for a temporary redirect
    rewrite service?name=$1 ^service/offline/([a-z]+)/?$ redirect;
    }
    ```
    
-   다른 모든 웹 서버의 경우에는 서버 관리자나 호스팅 업체에 문의하거나 선호하는 검색엔진에서 가이드를 검색하세요(예: 'LiteSpeed 리디렉션').

[서버 측 리디렉션](https://developers.google.com/search/docs/crawling-indexing/301-redirects?hl=ko#serverside)을 플랫폼에서 구현할 수 없는 경우 `meta refresh` 리디렉션이 실행 가능한 대안이 될 수 있습니다. Google에서는 두 가지 유형의 `meta refresh` 리디렉션을 구별합니다.

-   **즉시 `meta refresh` 리디렉션**: 페이지가 브라우저에 로드되는 즉시 트리거됩니다. Google 검색은 즉시 `meta refresh` 리디렉션을 영구 리디렉션으로 해석합니다.
-   **지연 `meta refresh` 리디렉션**: 사이트 소유자가 설정한 임의의 시간(초)이 지난 뒤에만 트리거됩니다. Google 검색은 지연 `meta refresh` 리디렉션을 임시 리디렉션으로 해석합니다.

`meta refresh` 리디렉션을 서버 측 코드가 있는 HTTP 헤더 또는 HTML의 `<head>` 요소에 배치합니다. 예를 들어 다음은 HTML의 `<head>` 요소에 배치된 즉시 `meta refresh` 리디렉션입니다.

```php-template
<!doctype html>
<html>
<head>
<meta http-equiv="refresh" content="0; url=https://example.com/newlocation">
<title>Example title</title>
<!--...-->
```

다음은 이에 상응하는 HTTP 헤더의 예입니다. HTTP 헤더는 서버 측 스크립트로 삽입할 수 있습니다.

```python-repl
HTTP/1.1 200 OK
Refresh: 0; url=https://www.example.com/newlocation
...
```

Google에서 임시 리디렉션으로 간주하는 지연 리디렉션을 만들려면 `content` 속성을 리디렉션이 지연되어야 하는 시간(초)으로 설정합니다.

```php-template
<!doctype html>
<html>
<head>
<meta http-equiv="refresh" content="5; url=https://example.com/newlocation">
<title>Example title</title>
<!--...-->
```

## 자바스크립트 `location` 리디렉션

Google 검색은 URL 크롤링이 완료되면 웹 렌더링 서비스를 사용하여 JavaScript를 해석하고 실행합니다.

JavaScript 리디렉션을 설정하려면 HTML 헤드의 스크립트 블록에서 `location` 속성을 리디렉션 대상 URL로 설정합니다. 예를 들면 다음과 같습니다.

```php-template
<!doctype html>
<html>
<head>
<script>
  window.location.href = "https://www.example.com/newlocation";
</script>
<title>Example title</title>
<!--...-->
```

## Crypto 리디렉션

다른 리디렉션 방법을 구현할 수 없는 경우에도 사용자에게 페이지나 콘텐츠가 이동되었음을 알리도록 계속 노력해야 합니다. 가장 간단한 방법은 간단한 설명과 함께 새 페이지를 가리키는 링크를 추가하는 것입니다. 예를 들면 다음과 같습니다.

> <a href="https://newsite.example.com/newpage.html">이전 완료! 새로운 사이트에서 콘텐츠를 찾아보세요!</a>

이렇게 하면 사용자가 새 사이트를 찾을 수 있고 Google에서 이를 crypto 리디렉션으로 이해할 수 있습니다. 스코틀랜드 네스호 괴물과 마찬가지로 리디렉션이 존재하는지 의심스러울 수 있으며 모든 검색엔진이 이 유사 리디렉션을 정식 리디렉션으로 인식하지는 않습니다.

## 대체 URL 버전

URL이 리디렉션되는 경우 Google에서는 리디렉션 소스(이전 URL)와 리디렉션 대상(새 URL)을 모두 추적합니다. 이 URL 중 하나가 [표준](https://developers.google.com/search/docs/crawling-indexing/consolidate-duplicate-urls?hl=ko) URL이 됩니다. 어떤 URL이 될지는 리디렉션이 임시적인지 아니면 영구적인지 등을 나타내는 신호에 따라 다릅니다. 남은 URL이 표준 URL의 _대체 이름_이 됩니다. 대체 이름은 사용자가 인식하고 더 신뢰할 수 있는 다른 버전의 표준 URL입니다. 사용자 검색어에 이전 URL이 더 많이 신뢰될 수 있다는 암시가 있으면 대체 이름이 검색 결과에 표시될 수 있습니다.

예를 들어 [새 도메인 이름으로 이동](https://developers.google.com/search/docs/crawling-indexing/site-move-with-url-changes?hl=ko)한 경우 새 URL의 색인이 이미 생성되었더라도 경우에 따라 Google 결과에 이전 URL이 계속 표시될 수 있습니다. 이는 정상적인 현상이며, 사용자가 새 도메인 이름에 익숙해지면 개발자의 별도 작업 없이 대체 이름은 사라집니다.