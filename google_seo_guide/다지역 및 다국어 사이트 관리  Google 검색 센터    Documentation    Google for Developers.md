## 다지역 및 다국어 사이트 관리

사이트에서 여러 언어, 국가, 지역의 사용자에게 다양한 콘텐츠를 제공하는 경우 사이트의 Google 검색 결과를 최적화할 수 있습니다.

## 다국어와 다지역의 차이점은 무엇인가요?

-   _다국어_ 웹사이트는 두 개 이상의 언어로 콘텐츠를 제공하는 웹사이트입니다. 예를 들어 캐나다의 비즈니스가 영어와 프랑스어 버전의 사이트를 제공할 수 있습니다. Google 검색에서는 검색 사용자의 언어와 일치하는 페이지를 찾아줍니다.
-   _다지역_ 웹사이트는 명시적으로 여러 국가의 사용자를 대상으로 하는 사이트를 말합니다. 예를 들어 캐나다와 미국으로 제품을 배송하는 제조업체가 있을 수 있습니다. Google 검색에서는 검색 사용자의 언어로 된 페이지를 찾아줍니다.

다지역인 동시에 다국어인 사이트도 있습니다. 예를 들어 미국 및 캐나다 버전이 따로 있으며, 캐나다인을 위한 콘텐츠를 프랑스어 및 영어 버전으로 제공하는 사이트가 있을 수 있습니다.

## 사이트의 다국어 버전 관리

<iframe frameborder="0" allowfullscreen="" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share" referrerpolicy="strict-origin-when-cross-origin" width="640" height="360" src="https://www.youtube.com/embed/n-6NmhCbEaI?origin=https%3A%2F%2Fdevelopers.google.com&amp;autoplay&amp;controls&amp;embed_domain&amp;enablejsapi=1&amp;end&amp;hl&amp;showinfo&amp;start&amp;video-id=n-6NmhCbEaI&amp;widgetid=127&amp;forigin=https%3A%2F%2Fdevelopers.google.com%2Fsearch%2Fdocs%2Fspecialty%2Finternational%2Fmanaging-multi-regional-sites%3Fhl%3Dko&amp;aoriginsup=1&amp;gporigin=https%3A%2F%2Fdevelopers.google.com%2Fsearch%2Fdocs%2Fcrawling-indexing%2Famp%2Fabout-amp%3Fhl%3Dko&amp;vf=1" id="widget128" data-title="YouTube video player" title="3 Tips for International Websites"></iframe>

사이트에서 동일한 콘텐츠를 여러 언어로 제공하는 경우 사용자(및 Google 검색)가 올바른 페이지를 찾을 수 있게 하는 방법을 알아보세요.

### 언어 버전별로 다른 URL 사용

Google에서는 쿠키나 브라우저 설정을 사용하여 페이지의 콘텐츠 언어를 조정하는 방법보다는 페이지의 URL을 언어별로 달리 할 것을 권장합니다.

언어별로 서로 다른 URL을 사용하는 경우 [`hreflang` 주석](https://developers.google.com/search/docs/specialty/international/localized-versions?hl=ko)을 사용하여 Google 검색 결과가 페이지의 올바른 언어 버전으로 연결될 수 있도록 하세요.

언어 설정에 따라 콘텐츠를 적극적으로 변경하거나 사용자를 다시 라우팅하려는 경우 **Google에서 모든 버전을 찾고 크롤링하지 못할 수도 있다는 점을 유의하세요**. 이는 Googlebot 크롤러가 일반적으로 미국에 기반을 두고 있기 때문입니다. 또한 크롤러는 요청 헤더에 `Accept-Language`를 설정하지 않은 상태로 HTTP 요청을 보냅니다.

### Google에 사이트의 언어별 버전 알리기

Google에서는 `hreflang` 주석 및 사이트맵을 포함하여 [페이지의 언어 또는 지역 버전에 라벨을 지정할 수 있도록 여러 가지 방법을 지원](https://developers.google.com/search/docs/specialty/international/localized-versions?hl=ko)합니다. 이러한 방법을 통해 페이지를 적절히 표시하세요.

### 페이지 언어가 명확한지 확인

Google에서는 페이지에 표시된 콘텐츠를 통해 언어를 결정합니다. `lang` 속성과 같은 코드 수준 언어 정보나 URL은 사용하지 않습니다. 각 페이지의 콘텐츠 및 탐색에 단일 언어를 사용하고 나란히 번역되지 않도록 하면 Google이 언어를 정확하게 판단하는 데 도움이 됩니다.

콘텐츠의 대부분은 단일 언어로 표시하면서 페이지에 고정적으로 사용되는 특정 텍스트만 번역하면(사용자 제작 콘텐츠를 표시하는 페이지에서 종종 사용하는 방식) 검색 결과에 동일한 콘텐츠가 다른 언어로 여러 번 표시되어 사용자가 불편을 겪을 수 있습니다.

### 사용자가 페이지 언어를 전환하도록 허용

하나의 페이지에 여러 버전이 있는 경우 다음을 고려해 보세요.

-   사이트의 한 언어 버전에서 다른 언어 버전으로 사용자를 **자동으로 리디렉션하지 마세요**. 예를 들어 사용자의 언어를 추측하여 리디렉션하지 마세요. 이러한 리디렉션은 사용자 및 검색엔진이 사이트의 모든 버전을 보지 못하도록 만듭니다.
-   **페이지의 다른 언어 버전으로 연결되는 하이퍼링크를 추가해 보세요**. 이렇게 하면 사용자가 페이지의 다른 언어 버전을 클릭하여 선택할 수 있습니다.

### 언어별 URL 사용

URL에 현지화된 단어를 사용하거나 [IDN(국제 도메인 이름)](https://en.wikipedia.org/wiki/Internationalized_domain_name)을 사용해도 됩니다. 그러나 URL에는 UTF-8 인코딩을 사용하고(가능한 한 UTF-8 사용) URL에 연결할 때 URL을 올바르게 이스케이프해야 합니다.

## 특정 국가에 사이트 콘텐츠 타겟팅(지역 타겟팅)

특정 언어를 사용하는 특정 국가의 사용자에게 웹사이트 전체 또는 일부를 타겟팅할 수 있습니다. 이렇게 하면 대상 국가에서 페이지의 순위는 높아지지만 다른 지역/언어에서의 실적이 저조해질 수 있습니다.

Google에서 **사이트를 지역 타겟팅하는 방법**은 다음과 같습니다.

-   **페이지 또는 사이트 수준:** [사이트 또는 페이지에 지역별 URL](https://developers.google.com/search/docs/specialty/international/managing-multi-regional-sites?hl=ko#locale-specific-urls)을 사용하세요.
-   **페이지 수준:** [`hreflang` 또는 사이트맵을 사용](https://developers.google.com/search/docs/specialty/international/localized-versions?hl=ko)하여 위치나 언어별로 적용할 페이지를 Google에 알리세요.

지역 타겟팅이 항상 정확하지는 않으므로 의도하지 않게 사이트의 다른 버전을 방문하는 사용자가 있을 수 있다는 것을 고려해야 합니다. 지역 타겟팅의 한 가지 방법으로 사용자가 지역 또는 언어를 선택할 수 있도록 모든 페이지에 링크를 표시할 수 있습니다.

### 언어별 URL 사용

다른 지역에 손쉽게 사이트의 전체 또는 일부를 지역 타겟팅할 수 있는 URL 구조 사용을 고려해 보세요. 다음 표에 사용할 수 있는 방법이 설명되어 있습니다.

| URL 구조 옵션 | URL 구조 옵션 |
|-------------------------------------|----------------------------------------------------------------------------------------------------------------------------------------------------------|
| **국가별 도메인**

`example.de` | **장점:**

-   명확한 지역 타겟팅
-   서버 위치가 중요하지 않음
-   간편한 사이트 분리

**단점:**

-   많은 비용 발생(사용 가능성이 제한될 수 있음)
-   추가 인프라 필요
-   경우에 따라 ccTLD 요구사항이 엄격함
-   단일 국가만 타겟팅할 수 있음 |
| **gTLD를 포함하는 하위 도메인**

`de.example.com` | **장점:**

-   간편한 설정
-   다양한 서버 위치 허용
-   간편한 사이트 분리

**단점:**

-   사용자가 URL만으로 지역 타겟팅을 인식하지 못할 수 있음(예: 'de'가 언어인지 국가인지 확실하지 않음) |
| **gTLD를 포함하는 하위 디렉터리**

`example.com/de/` | **장점:**

-   간편한 설정
-   저렴한 유지 관리비(호스트가 동일함)

**단점:**

-   사용자가 URL만으로 지역 타겟팅을 인식하지 못할 수도 있음
-   단일 서버 위치
-   사이트의 분리가 어려움 |
| **URL 매개변수**

`site.com?loc=de` | 권장하지 않음

**단점:**

-   URL 기반 세분화가 어려움
-   사용자가 URL만으로 지역 타겟팅을 인식하지 못할 수도 있음 |

### Google에서는 어떻게 대상 지역을 판단하나요?

Google은 여러 가지 신호를 활용하여 페이지에 가장 적합한 타겟층을 판단합니다.

-   **국가 코드 최상위 도메인 이름**(ccTLDs). 이러한 이름은 특정 국가에 연결되므로(예: .de는 독일, .cn은 중국) 사용자와 검색엔진 모두에 사이트가 특정 국가를 대상으로 한다는 것을 명시적으로 알리는 강력한 신호가 됩니다. 일부 국가의 경우 누가 ccTLD를 사용할 수 있는지에 관한 제한이 있으므로 먼저 자세히 알아보세요. Google에서는 일부 가상 ccTLD(예: .tv, .me)도 gTLD로 처리합니다. 사용자와 웹사이트 소유자가 가상 ccTLD를 국가를 대상으로 한 도메인보다는 일반적인 도메인으로 보는 경우가 많기 때문입니다. [Google의 gTLD 목록](https://developers.google.com/search/docs/specialty/international/managing-multi-regional-sites?hl=ko#generic-domains)을 확인해 보세요.
-   태그, 헤더 또는 사이트맵의 [**`hreflang` 구문**](https://developers.google.com/search/docs/specialty/international/localized-versions?hl=ko)
-   **서버의 IP 주소를 통한 서버 위치.** 서버 위치는 실제로 사용자와 가까운 경우가 많으며 사이트의 타겟 사용자를 알 수 있는 힌트가 될 수 있습니다. 일부 웹사이트는 분산된 CDN(콘텐츠 전송 네트워크)을 사용하거나 더 나은 웹 서버 인프라가 구축된 국가에서 호스트되므로 서버 위치가 확실한 신호는 아닙니다.
-   **기타 신호.** 사이트의 타겟층을 식별하는 기타 신호에는 페이지의 현지 주소 및 전화번호나 현지 언어 및 통화 사용, 다른 현지 사이트의 링크, [비즈니스 프로필](https://www.google.com/business/?hl=ko)의 신호(사용 가능한 경우)가 포함될 수 있습니다.

**Google에서 사용하지 _않는_ 항목**

-   Google은 전 세계 여러 지역의 웹을 크롤링합니다. Google에서는 다른 버전의 페이지를 찾기 위해 하나의 사이트에 사용되는 크롤러 소스를 변경하지 **않습니다**. 따라서 여기에 나온 방법(예: `hreflang` 항목, ccTLD, 명시적 링크) 중 하나를 사용하여 사이트에서 노출하는 언어나 언어 변형을 Google에 명시적으로 알려야 합니다.
-   Google은 `geo.position` 또는 `distribution`과 같은 위치 `meta` 태그나 지역 타겟팅 HTML 속성을 **무시**합니다.

## 다국어/다지역 사이트의 중복 페이지 처리

다지역 사이트의 일부로서 다른 URL에서 동일한 언어로 유사하거나 중복되는 콘텐츠를 제공하는 경우(예: `example.de/`와 `example.com/de/`에서 유사한 독일어 콘텐츠를 표시) 기본 버전을 선택하고 [`rel="canonical"` 요소](https://developers.google.com/search/docs/crawling-indexing/consolidate-duplicate-urls?hl=ko) 및 [`hreflang`](https://developers.google.com/search/docs/specialty/international/localized-versions?hl=ko) 태그를 사용하여 올바른 언어 또는 지역 URL이 검색 사용자에게 제공합니다.

### 일반 최상위 도메인

일반 최상위 도메인(gTLD)은 특정 위치와 관련되지 않는 도메인입니다. 사이트에 .com 또는 .org와 같은 일반 최상위 도메인 또는 다음 도메인이 있고 특정 지리적 위치의 사용자를 타겟팅하고자 하는 경우, 앞서 설명한 방법 중 하나를 사용하여 국가 대상을 명시적으로 설정합니다.

Google은 다음 최상위 도메인을 gTLD로 처리합니다.

-   **일반 최상위 도메인**: ICANN에서 최상위 도메인을 [국가 코드 최상위 도메인](https://www.iana.org/domains/root/db)(ccTLD)으로 나열하지 않는 한 Google은 IANA DNS 루트 영역을 통해 확인되는 모든 TLD를 gTLD로 처리합니다. **예:**
    -   .com
    -   .org
    -   .edu
    -   .gov
    -   그 외 다수
-   **일반 지역 최상위 도메인**: 이 도메인은 지역과 관련되어 있지만 일반적으로 .com 또는 .org와 마찬가지로 일반 최상위 도메인으로 처리됩니다.
    -   .eu
    -   .asia
-   **일반 국가 코드 최상위 도메인(ccTLD)**: Google에서는 일부 ccTLD(예: .tv, .me)를 gTLD로 처리하는데, 이는 사용자 및 웹사이트 소유자가 이러한 ccTLD를 국가를 대상으로 한 도메인보다는 일반적인 도메인으로 보는 경우가 자주 있기 때문입니다. 다음은 이러한 ccTLD 목록이며 이 목록은 변경될 수 있습니다.
    -   .ad
    -   .ai
    -   .as
    -   .bz
    -   .cc
    -   .cd
    -   .co
    -   .dj
    -   .fm
    -   .io
    -   .la
    -   .me
    -   .ms
    -   .nu
    -   .sc
    -   .sr
    -   .su
    -   .tv
    -   .tk
    -   .ws