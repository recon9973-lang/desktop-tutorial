## 사이트 이동 방법

이 문서에서는 Google 검색 결과에 대한 부정적인 영향을 최소화하면서 사이트의 기존 페이지 URL을 변경하는 방법을 설명합니다. 이러한 사이트 이전의 예는 다음과 같습니다.

-   `HTTP`에서 `HTTPS`로 URL 변경
-   도메인 이름 변경(예: `example.com`에서 `example.net`으로) 또는 여러 도메인이나 호스트 이름 병합
-   URL 경로 변경(예: `example.com/page.php?id=1`에서 `example.com/widget`으로 또는 `example.com/page.html`에서 `example.com/page.htm`으로)

## 개요

1.  [**사이트 이동에 관한 일반적인 권장사항**](https://developers.google.com/search/docs/crawling-indexing/site-move-with-url-changes?hl=ko#general_recommendations_for_site_moves) 예상되는 결과라든지 사용자 및 순위에 미칠 수 있는 영향을 파악합니다. HTTP에서 HTTPS로 이동하는 경우 [HTTPS 권장사항](https://web.dev/articles/enable-https?hl=ko)을 검토합니다.
2.  [**새 사이트를 준비**](https://developers.google.com/search/docs/crawling-indexing/site-move-with-url-changes?hl=ko#prepare-new-site)하고 꼼꼼히 테스트합니다.
3.  현재 URL에서 이에 상응하는 새 형식으로 [**URL 매핑을 준비**](https://developers.google.com/search/docs/crawling-indexing/site-move-with-url-changes?hl=ko#prepare-url-mapping)합니다.
4.  이전 URL에서 새 URL로 리디렉션하도록 서버를 설정하여 [**사이트 이동을 시작**](https://developers.google.com/search/docs/crawling-indexing/site-move-with-url-changes?hl=ko#start-site-move)합니다.
5.  이전 URL과 새 URL 모두의 [**트래픽을 모니터링**](https://developers.google.com/search/docs/crawling-indexing/site-move-with-url-changes?hl=ko#monitor)합니다.

## 사이트 이동에 관한 일반적인 권장사항

-   **사이트에 적합한 경우 이동을 여러 단계로 나누어 진행합니다**  
    규모가 큰 사이트이며 기술적으로 가능한 경우, 처음에는 사이트의 일부만 이동하여 트래픽 및 검색 색인 생성에 미치는 영향을 테스트하는 것이 좋습니다. 그 후 나머지 사이트를 한꺼번에 또는 몇 개의 부분으로 나누어 이동하면 됩니다. 사이트에서 우선적으로 테스트할 섹션을 선택할 때는 변경 빈도가 낮으며 빈번하거나 예상치 못한 이벤트에 의해 큰 영향을 받지 않는 섹션을 선택하세요. 또한 한 섹션만 이동하는 것이 테스트하기에는 좋지만 테스트한 부분이 Google 검색과 관련하여 전체 사이트 이동을 대표적으로 보여주는 것은 아니라는 점에 유의하시기 바랍니다. 이동하는 페이지가 늘어나면서 해결해야 할 문제가 더 많이 발생하게 됩니다. 신중히 계획을 세워 문제를 최소화해야 합니다.
-   **한 번에 한 가지만 변경합니다**  
    사이트를 한 번에 모두 변경하지 말고 한 번에 하나씩 변경하는 것으로 계획하세요. 예를 들어 사이트를 새 도메인 이름으로 이동하고, 콘텐츠 관리 시스템(CMS)을 변경하고, 새로운 레이아웃을 사용하도록 업데이트하려면 한 번에 하나씩 처리하세요. 새로운 도메인으로 이전한 다음, 사이트의 레이아웃을 변경하는 것이 좋습니다.
-   **가능하면 트래픽이 적을 때 이동하도록 시기를 조정합니다**  
    트래픽이 계절에 따라 다르거나 특정 요일에는 적다면 트래픽이 반복적으로 감소하는 동안 사이트를 이동하는 것이 좋습니다. 이렇게 하면 사이트 이동 중에 발생할 수 있는 문제의 영향을 받는 사용자 수가 감소하며, 사이트를 크롤링하는 Googlebot에 사용할 수 있는 서버 리소스가 늘어날 수 있습니다.
-   **이동하는 동안 일시적으로 사이트 순위에 변화가 생길 수 있습니다**  
    사이트에 중요한 변화가 있는 경우 Google에서 사이트를 다시 크롤링하고 색인을 다시 생성하는 동안 순위 변화가 발생하기도 합니다. 대개 중간 규모의 웹사이트의 경우 Google의 색인에서 대부분의 페이지가 이동하는 데 몇 주가 걸릴 수 있으며 더 큰 사이트는 더 오래 소요됩니다. Googlebot과 Google 시스템에서 이동한 URL을 발견하고 처리하는 속도는 URL 수와 서버 속도에 따라 크게 달라집니다. [사이트맵을 제출](https://developers.google.com/search/docs/crawling-indexing/sitemaps/build-sitemap?hl=ko)하면 발견 과정을 단축할 수 있으며 섹션별로 사이트를 이동해도 됩니다.
-   **링크 크레딧은 걱정하지 마세요**  
    `301` 및 [기타 영구 리디렉션](https://developers.google.com/search/docs/crawling-indexing/301-redirects?hl=ko#permanent-server-side-redirects)으로 인해 [PageRank](https://wikipedia.org/wiki/PageRank)가 손실되는 일은 없습니다.
-   **Search Console을 활용합니다**  
    Search Console은 사이트 이동에 특히 중요한 도구입니다. Search Console에서 각 속성의 데이터를 개별적으로 확인하세요. 전반적인 정보는 [색인 상태 보고서](https://support.google.com/webmasters/answer/7440203?hl=ko)를 참고하세요. [사이트맵 보고서](https://support.google.com/webmasters/answer/7451001?hl=ko)에서 사이트맵에 제출된 URL 중 색인이 생성된 URL 수를 확인할 수 있습니다.
-   **여유를 갖고 결과를 기다리세요**  
    사이트 이동이 완료된 것으로 간주하려면 Googlebot에서 이전 사이트와 새 사이트의 모든 URL을 한 번 이상 방문해야 합니다. 정해진 크롤링 빈도는 없습니다. Googlebot의 크롤링 속도는 사이트와 크기 및 가능한 크롤링 속도에 따라 다릅니다. 이동은 URL별로 이루어집니다.

## 새 사이트 준비

사이트 준비에 관한 자세한 내용은 사이트 이동마다 달라집니다. 하지만 대개 다음 중 하나 이상의 작업을 실행하게 됩니다.

-   **CMS를 설정**(이전 사이트에 사용한 것과 동일한 CMS를 사용하는 것이 좋음)하고 기존 사이트에서 콘텐츠를 가져옵니다.
-   호스팅하는 **이미지와 다운로드를 전송**합니다(예: PDF 문서).  
    이러한 이미지와 다운로드에 이미 Google 검색이나 링크를 통한 트래픽이 발생할 수 있으므로 Googlebot과 사용자에게 새 위치를 알리는 것이 좋습니다.
-   **HTTPS로 이전하는 경우** 서버에 필수 TLS 인증서를 받고 설정합니다.
-   **새 사이트에 robots.txt를 설정**하고 새 사이트의 robots.txt 파일에 있는 규칙에서 크롤링을 차단하려는 부분이 제대로 반영되어 있는지 확인합니다.
    
    일부 사이트 소유자는 개발 중 모든 크롤링을 차단하기도 합니다. 이렇게 하면 사이트 이동을 시작한 후 robots.txt 파일을 어떻게 변경할지 준비해야 합니다. 마찬가지로 개발 중에 `noindex` 규칙을 사용하는 경우 사이트 이전을 시작하면 `noindex` 규칙을 삭제할 URL 목록을 준비하세요.
    
-   **삭제되거나 병합된 콘텐츠의 오류를 제공**합니다. 기존 콘텐츠를 새 사이트로 모두 이전하지는 않는 경우 이러한 URL이 새 사이트에서 `404` 또는 `410` 오류 응답 코드를 올바르게 반환하는지 확인하세요.
    
-   사이트 이동에 도움이 되도록 **Search Console 설정이 올바른지** 확인합니다.
    
    아직 확인하지 않았다면 Search Console에서 이전 사이트와 새 사이트를 모두 [확인](https://support.google.com/webmasters/answer/9008080?hl=ko)하세요. 이전 사이트와 새 사이트의 변형을 모두 확인해야 합니다. 예를 들어 `www.example.com`과 `example.com`을 확인하고 HTTPS URL을 사용하는 경우 HTTPS 및 HTTP 사이트 변형을 모두 포함해야 합니다. 이전 사이트와 새 사이트 모두 해당됩니다.
    
    -   **Search Console 확인 검토**
        
        사이트를 이전한 후에도 Search Console 확인이 계속 작동하는지 확인하세요. 다른 확인 방법을 사용하는 경우 URL을 변경했을 때 확인 토큰이 다를 수 있습니다.
        
        [HTML 파일을 이용하는 방법](https://support.google.com/webmasters/answer/9008080?hl=ko#html_verification)을 사용하여 Search Console에서 사이트 소유권을 확인하는 경우 현재 확인 파일을 사이트의 새 사본에 포함해야 합니다.
        
        마찬가지로, [`meta` 태그](https://support.google.com/webmasters/answer/9008080?hl=ko#meta_tag_verification)를 참조하는 include 파일 또는 [Google 애널리틱스](https://support.google.com/webmasters/answer/9008080?hl=ko#google_analytics_verification)를 사용하여 소유권을 확인한다면 새 CMS 사본에도 이를 포함해야 합니다.
        
    -   이전 사이트에 적용했을 수 있는 **Search Console의 모든 설정을 검토**하고 새 사이트의 설정도 이러한 변경사항을 반영하도록 업데이트해야 합니다. 예:
        
        -   [크롤링 속도](https://support.google.com/webmasters/webmasters/answer/48620?hl=ko): 이전 사이트와 새 사이트 모두의 크롤링 속도를 'Googlebot이 결정'으로 설정합니다.
        -   [거부된 백링크](https://support.google.com/webmasters/webmasters/answer/2648487?hl=ko): 이전 사이트의 링크를 거부하는 파일을 업로드했다면 새 사이트의 Search Console 계정을 사용하여 이 파일을 다시 업로드하는 것이 좋습니다.
    -   **최근 구매한 도메인을 정리**하여 이전 소유자와 관련해 해결되지 않은 문제가 없는지 확인하는 것이 좋습니다. 다음 설정을 확인하세요.
        
        -   이전 스팸에 관한 [직접 조치](https://support.google.com/webmasters/answer/9044175?hl=ko): 새 사이트에 적용된 직접 조치가 있다면 표시되어 있는 문제를 전부 해결한 다음 [재검토 요청](https://support.google.com/webmasters/answer/35843?hl=ko)을 제출하세요.
        -   [삭제된 URL](https://support.google.com/webmasters/answer/9689846?hl=ko): 이전 소유자에게 삭제해야 하는 URL, 특히 사이트 전체 URL이 남아 있지 않은지 확인합니다.
-   **웹 분석을 사용**하여 이전 사이트와 새 사이트 모두의 사용량을 분석합니다. 웹로그 분석 소프트웨어를 사용하면 손쉽게 분석할 수 있습니다. 일반적으로 웹로그 분석 설정은 페이지에 삽입된 JavaScript 조각으로 구성됩니다. 다양한 사이트의 추적 세부정보는 분석 소프트웨어 및 로깅, 처리, 필터링 설정에 따라 다릅니다. 도움이 필요하면 분석 소프트웨어 제공업체에 문의하시기 바랍니다. 또한 분석 소프트웨어 설정을 변경할 계획이 있다면 지금 변경하세요. Google 애널리틱스를 사용하는 경우 콘텐츠 보고서에서 새 사이트를 확실히 구분할 수 있도록 새 프로필을 만드는 것이 좋습니다.
    
-   **서버에 충분한 컴퓨팅 리소스가 있는지 확인**하세요. 이전이 완료된 후 Google에서는 평소보다 더 많이 새 사이트를 일시적으로 크롤링합니다. 이는 이전 사이트에서 새 사이트로 트래픽을 리디렉션하기 때문이며 이전 사이트의 모든 크롤링은 다른 크롤링과 함께 새 사이트로 리디렉션됩니다. 새 사이트에 Google로 인해 증가한 트래픽을 처리할 정도로 충분한 용량이 있는지 확인하세요. 사이트의 크기가 특별히 큰 경우 호스팅 업체에 문의하여 사이트 이동을 계획하고 있다고 알립니다.

## URL 매핑 준비

이전 사이트의 URL을 새 사이트의 URL로 매핑하는 것이 중요합니다. 이 섹션에서는 두 사이트의 URL을 알맞게 평가하고 매핑을 촉진하기 위해 할 수 있는 여러 일반적인 방법을 설명합니다. 매핑을 생성하는 방법에 관한 정확한 세부정보는 현재 웹사이트 인프라와 사이트 이동 세부정보에 따라 다릅니다.

### 이전 URL 확인

가장 간단한 사이트 이동의 경우 이전 URL의 목록을 생성할 필요가 없을 수도 있습니다. 예를 들어 사이트의 도메인을 변경한다면(예: `example.com`에서 `example.net`으로 변경) 와일드 카드 서버 측 리디렉션을 사용해도 됩니다.

좀 더 복잡한 사이트 이동의 경우 이전 URL 목록을 생성한 다음 새 도착 URL에 매핑해야 합니다. 이전 URL 목록을 생성하는 방법은 현재 웹사이트의 설정에 따라 다릅니다. 다음은 몇 가지 간단한 도움말입니다.

-   **중요한 URL로 시작합니다**. 중요한 URL을 찾으려면 다음을 따르세요.
    -   가장 중요한 URL은 Search Console에 사이트맵으로 제출되었을 가능성이 높으므로 [사이트맵](https://developers.google.com/search/docs/crawling-indexing/sitemaps/overview?hl=ko)을 살펴봅니다.
    -   서버 로그나 분석 소프트웨어에서 트래픽이 가장 많이 발생하는 URL을 확인합니다.
    -   Search Console의 [사이트로 연결되는 링크 기능](https://support.google.com/webmasters/answer/9049606?hl=ko)에서 내부 링크와 외부 링크가 있는 페이지를 확인합니다.
-   일반적으로 콘텐츠를 호스팅하는 모든 URL의 목록을 간편하게 생성하는 **콘텐츠 관리 시스템을 사용**합니다.
-   **서버 로그**에서 최근에 한 번 이상 방문된 URL을 확인합니다. 계절에 따른 트래픽 변화를 염두에 두고 사이트에 적합한 기간을 선택합니다.
-   **이미지와 동영상을 포함합니다**. 삽입된 콘텐츠(동영상, 이미지, JavaScript, CSS 파일)의 URL을 사이트 이동 계획에 포함해야 합니다. 이러한 URL은 웹사이트의 다른 모든 콘텐츠와 동일한 방법으로 이동해야 합니다.

### 이전 URL에서 새 URL로 매핑 생성

이전 URL 목록을 만들면 각 URL을 리디렉션할 위치를 결정합니다. 이러한 매핑을 저장하는 방법은 서버 및 사이트 이동에 따라 다릅니다. 데이터베이스를 사용하거나 시스템에 일반 리디렉션 패턴에 관한 URL 재작성 규칙 일부를 설정할 수 있습니다.

### 새 사이트에 있는 모든 URL의 세부정보 업데이트

URL 매핑을 정의한 후에는 다음 3가지 작업을 진행하여 페이지에서 트래픽을 수신할 준비를 합니다.

1.  각 페이지의 HTML 또는 사이트맵 항목에서 새로운 URL을 가리키도록 **주석을 업데이트**합니다.
    1.  새로운 URL마다 자체 참조 [`rel="canonical" <link>`](https://developers.google.com/search/docs/crawling-indexing/consolidate-duplicate-urls?hl=ko) 태그가 있어야 합니다.
    2.  이동한 사이트에 [`rel-alternate-hreflang` 주석](https://developers.google.com/search/docs/specialty/international/localized-versions?hl=ko)을 사용하여 주석기 달린 다국어 또는 다국적 페이지가 있다면 새 URL을 사용하도록 주석을 업데이트해야 합니다.
2.  **내부 링크를 업데이트합니다**.  
    새 사이트의 내부 링크를 이전 URL에서 새 URL로 변경합니다. 이전에 생성한 매핑을 사용하여 필요에 따라 링크를 찾고 업데이트할 수 있습니다.
3.  **최종 이동을 위해 다음 목록을 저장합니다**.  
    -   매핑에 새 URL을 포함하는 사이트맵 파일. [사이트맵 작성](https://developers.google.com/search/docs/crawling-indexing/sitemaps/build-sitemap?hl=ko) 문서를 참고하세요.
    -   이전 URL로 연결되는 사이트 목록. Search Console에서 [사이트로 연결되는 링크](https://support.google.com/webmasters/answer/9049606?hl=ko)를 확인할 수 있습니다.

### 리디렉션 전략 계획하기

매핑을 생성하고 새 사이트가 준비되면 다음으로 리디렉션 전략을 계획합니다. 매핑에 표시한 대로 이전 URL에서 새 URL로의 서버 측 [영구 리디렉션](https://developers.google.com/search/docs/crawling-indexing/301-redirects?hl=ko)을 사용하는 것이 좋습니다. 서버 관리자나 호스팅 업체에 기술적으로 어떤 종류의 서버 측 리디렉션을 사용할 수 있는지 문의하세요. 서버에서 [Apache HTTP 서버](https://httpd.apache.org/)를 사용하거나 CMS의 리디렉션 함수를 사용하는 경우 `.htaccess` 파일의 리디렉션 규칙을 사용해야 할 수도 있습니다.

서버 측 리디렉션 설정을 사용할 수 없는 경우 최후의 수단으로 클라이언트 측 리디렉션을 사용할 수 있습니다.

**사이트 이동 방식을 결정합니다.** 모두 한 번에 이동할지 또는 섹션별로 이동할지 결정합니다.

-   **중소형 사이트:** 한 번에 한 섹션씩 이동하지 않고 사이트의 모든 URL을 동시에 이동하는 것이 좋습니다. 이렇게 하면 사용자들이 새로운 형식에서 사이트와 상호작용하고 Google 알고리즘이 사이트 이동을 감지하고 색인을 신속하게 업데이트하는 데 도움이 됩니다.
-   **대형 사이트:** 규모가 더 큰 사이트는 한 번에 한 섹션씩 이동할 수 있습니다. 이렇게 하면 신속하면서도 간편하게 문제를 모니터링하고 감지하고 해결하기에 좋습니다.

다음 사항에 유의하세요.

-   기술적으로 가능하다면 **서버 측 영구 리디렉션을 사용**합니다. Googlebot에서는 [여러 종류의 리디렉션](https://developers.google.com/search/docs/crawling-indexing/301-redirects?hl=ko)을 지원하지만 가능하면 `301`, `308` 등의 HTTP 영구 리디렉션을 사용하는 것이 좋습니다.
-   **체인 리디렉션을 사용하지 않습니다.** Googlebot은 여러 리디렉션 '체인'(예: 1페이지 \> 2페이지 \> 3페이지)에서 [최대 10개의 홉](https://developers.google.com/crawling/docs/troubleshooting/http-status-codes?hl=ko#3xx-redirection)을 지원할 수 있으나, 최종 도착 페이지로 리디렉션하는 것이 좋습니다. 한 번에 리디렉션할 수 없는 경우 체인의 리디렉션 수를 적게 유지합니다. 3개 이하가 적당하며 최대 5개까지입니다. 체인 리디렉션을 사용하면 사용자의 지연 시간이 늘어나며 일부 사용자 에이전트와 브라우저에서는 긴 리디렉션 체인을 지원하지 않습니다.

## 사이트 이전 시작

URL 매핑이 정확하며 무엇을 리디렉션할지 확정했다면 사이트를 이전할 준비가 된 것입니다.

1.  **리디렉션을 구현하거나 사용 설정합니다**. 리디렉션 전략에 따라 서버 구성 파일 업데이트를 푸시하거나 CMS를 맞춤 코드로 업데이트해야 할 수 있습니다.
2.  **`rel="canonical"` `link` 주석 및 `robots` `meta` 규칙 확인하기:** 리디렉션이 활성화되면 새 사이트의 `rel="canonical"` `link` 주석이 새 URL을 사용하는지 확인합니다. 마찬가지로 새 URL의 조기 색인 생성을 방지하기 위해 `noindex` `robots` `meta` 규칙을 새 사이트에 추가한 경우 규칙을 업데이트해야 합니다.
3.  **리디렉션을 테스트합니다**. [URL 검사 도구](https://support.google.com/webmasters/answer/9012289?hl=ko)를 사용하여 URL을 하나씩 테스트하거나 명령줄 도구 또는 스크립트를 사용하여 다수의 URL을 테스트합니다.
4.  **Search Console에서 이전 사이트에 대한 [주소 변경 알림](https://support.google.com/webmasters/answer/9370220?hl=ko)을 제출합니다.**
5.  **리디렉션을 최대한 오랫동안 유지**합니다. 일반적으로 최소 1년입니다. 이 기간이 확보되어야 Google은 이전 URL로 연결되는 다른 사이트의 링크를 다시 크롤링하고 재할당하는 등 모든 신호를 새 URL에 전송할 수 있습니다.
    
    사용자 측면에서는 리디렉션을 무기한 유지하는 것이 좋습니다. 그러나 사용자에게는 리디렉션이 느리기 때문에 자체 링크 및 다른 웹사이트로 연결되는 대용량 링크가 새로운 URL에 연결되도록 업데이트해 보세요.
    
6.  **Search Console에서 새 사이트맵을 제출합니다**. Google에서 새 URL을 학습하는 데 도움이 됩니다. 이후 Google에서 새 사이트맵을 사용하므로 이 시점에서 이전 사이트맵을 삭제할 수 있습니다.

Googlebot과 Google 시스템에서 사이트 이동에 포함된 모든 URL을 찾아서 처리하는 데 걸리는 시간은 서버 속도 및 포함된 URL 수에 따라 다릅니다. 중소형 웹사이트의 경우 대부분의 페이지를 이동하는 데 대개 몇 주 정도 걸릴 수 있으며 대형 사이트 이동은 더 오래 걸립니다. Googlebot과 Google 시스템에서 이동한 URL을 발견하고 처리하는 속도는 URL 수와 서버 속도에 따라 다릅니다.

### 링크 업데이트

사이트 이동이 시작된 직후에는 가능한 한 많은 수신 링크를 업데이트하여 사용자 환경을 개선하고 서버 로드를 줄이는 것이 좋습니다. 여기에는 다음이 포함됩니다.

-   내부 링크: 이전에 만든 URL 매핑을 기반으로 해당 페이지를 가리키는 모든 URL을 바꿉니다.
-   외부 링크: 현재 콘텐츠로 연결되는 사이트의 저장된 목록에 있는 사이트에 연락하여 링크를 새 사이트로 업데이트해 달라고 요청합니다. 각 링크의 인바운드 방문수를 기준으로 작업 우선순위를 정하는 것이 좋습니다.
-   Facebook, Twitter, LinkedIn 등의 프로필 링크
-   새로운 방문 페이지를 가리키는 광고 캠페인

## 트래픽 모니터링

사이트 이동을 시작했다면 사용자와 크롤러의 트래픽이 새 사이트 및 이전 사이트에서 어떻게 변하는지 모니터링합니다. 새 사이트의 트래픽은 증가하는 한편, 이전 사이트의 트래픽은 감소하는 것이 이상적입니다. [Search Console](https://search.google.com/search-console/?hl=ko) 및 다른 도구를 사용하여 사이트에서 사용자와 크롤러의 활동을 모니터링할 수 있습니다.

### Search Console을 사용하여 트래픽 모니터링

다양한 Search Console 기능은 다음과 같이 사이트 이동의 모니터링을 돕습니다.

-   [사이트맵](https://search.google.com/search-console/sitemaps?hl=ko): 매핑에서 이전에 저장한 두 사이트맵을 제출합니다. 처음에는 새 URL이 포함된 사이트맵에 페이지의 색인이 생성되지 않고 이전 URL의 사이트맵에는 여러 페이지의 색인이 생성됩니다. 시간이 지나면서 이전 URL 사이트맵에서 색인이 생성된 페이지 수가 0까지 줄어들고 이에 상응하여 새 URL의 색인이 증가합니다. Search Console에서 URL 리디렉션에 관한 이전 URL이 포함된 사이트맵에 경고가 표시될 수 있습니다. 이는 정상적인 상황이며 이 경고를 무시해도 괜찮습니다. 결국 새로운 URL로 이전하고 있기 때문입니다.
-   [색인 생성 범위 보고서](https://search.google.com/search-console/index?hl=ko): 그래프에 사이트 이동이 반영되면서 이전 사이트의 색인 생성된 URL 수는 줄어들고 새 사이트의 색인 생성이 증가합니다. 예상치 않은 크롤링 오류가 있는지 정기적으로 확인합니다.
-   [검색어](https://search.google.com/search-console/performance/search-analytics?hl=ko): 새 사이트 페이지의 색인이 더 많이 생성되고 순위가 집계됨에 따라 검색어 보고서에 새 사이트에서 검색 노출수와 클릭수를 받는 URL이 표시되기 시작합니다.

### 다른 도구를 사용하여 트래픽 모니터링

서버 액세스와 오류 로그를 주시하여 특히 Googlebot의 크롤링, 예기치 않게 HTTP 오류 상태 코드를 반환하는 URL, 일반 사용자 트래픽을 확인합니다.

사이트에 웹로그 분석 소프트웨어를 설치했거나 CMS에서 분석을 제공하는 경우 이전 사이트에서 새 사이트로의 트래픽 진행 상황을 확인할 수 있도록 이 방법으로 트래픽을 검토하는 것이 좋습니다. 특히 Google 애널리틱스에서 제공하는 실시간 보고서는 사이트 이동 초기 단계에서 사용하기에 유용한 기능입니다. 이전 사이트의 트래픽은 줄어들고 새 사이트의 트래픽은 증가해야 합니다.

## 추가 리소스

사이트 이전은 부담스럽고 복잡한 작업이므로 이를 진행하는 방법에 관한 여러 가지 의견이 있습니다. [Aleyda Solis의 사이트 이전 체크리스트](https://www.aleydasolis.com/en/search-engine-optimization/seo-for-web-migrations/)는 특히 유용하며, 사이트 이전을 위한 [Screaming Frog 도구 가이드](https://www.screamingfrog.co.uk/how-to-use-the-seo-spider-in-a-site-migration/)도 큰 도움이 됩니다.

**문제가 발생하면 Google 검색 센터에서 도움말을 찾아보세요.**  
[도움말 페이지](https://developers.google.com/search/help?hl=ko)에서 다양한 도움말을 확인하고 [사용자 포럼](https://support.google.com/webmasters/community?hl=ko)에서 특정 사례에 달린 답변을 확인할 수 있습니다. 답변을 찾을 수 없다면 [검색엔진 최적화 센터 오피스 아워](https://developers.google.com/search/help/office-hours?hl=ko)에 Google 검색 전문가에게 질문해 보세요.

## 사이트 이동 관련 문제 해결

다음은 사이트를 이전하면서 URL을 변경(HTTP에서 HTTPS로 변경하는 경우 포함)할 때 놓치기 쉬운 몇 가지 일반적인 실수입니다. 이러한 실수로 인해 새 사이트의 색인이 완전히 생성되지 않을 수 있습니다.

| 흔히 발생하는 실수 | 흔히 발생하는 실수 |
|------------------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| ### `noindex` 또는 robots.txt 블록 | 이전용으로만 필요한 `noindex` 또는 robots.txt 블록을 삭제하는 것을 잊지 마세요.

사이트에 robots.txt 파일이 없어도 괜찮습니다. 하지만 robots.txt 파일이 없는 경우에는 적절한 `404` HTTP 상태 코드를 반환해야 합니다.

**테스트 방법:**

-   HTTPS 사이트에서 robots.txt 파일을 살펴보고 변경해야 할 사항이 있는지 확인합니다.
-   새 사이트의 페이지 중 Google에서 누락된 것으로 보이는 페이지에 [URL 검사 도구](https://support.google.com/webmasters/answer/9012289?hl=ko)를 사용합니다. |
| ### 잘못된 리디렉션 | 오래된 사이트에서 새 사이트로 연결되는 리디렉션을 확인합니다. 새 사이트에서 방문자가 잘못된(존재하지 않는) URL로 리디렉션되는 경우가 자주 있습니다.

Search Console을 사용하여 보고된 '찾을 수 없음' 오류 수가 비정상적으로 많은지 확인하거나 [Screaming Frog](https://www.screamingfrog.co.uk/seo-spider/)와 같은 다른 도구를 사용하여 내 사이트를 크롤링하고 리디렉션이 예상대로 작동하는지 확인할 수 있습니다. |
| ### 기타 크롤링 오류 | [색인 생성 범위 보고서](https://search.google.com/search-console/index?hl=ko)를 살펴보고 이전 이벤트 동안 새 사이트에서 다른 오류가 급증했는지 확인합니다. |
| ### 서버 용량 부족 | 이전 후 Google에서는 평소보다 훨씬 많이 새 사이트를 크롤링합니다. 이는 이전 사이트에서 새 사이트로 트래픽을 리디렉션하기 때문이며 이전 사이트의 모든 크롤링은 다른 크롤링과 함께 새 사이트로 리디렉션됩니다. 새 사이트에 Google로 인해 증가한 트래픽을 처리할 정도로 충분한 용량이 있는지 확인하세요. |
| ### 사이트맵을 업데이트하지 않음 | 사이트맵을 새 URL로 모두 업데이트했는지 확인합니다. |