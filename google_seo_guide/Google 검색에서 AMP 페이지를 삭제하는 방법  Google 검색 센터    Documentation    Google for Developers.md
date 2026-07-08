이 페이지에서는 웹 개발자가 Google 검색에서 AMP 페이지를 삭제하는 방법을 설명합니다.

AMP 콘텐츠를 삭제하는 데는 다음과 같은 세 가지 옵션이 있습니다.

-   AMP 페이지 및 AMP가 아닌 표준 페이지를 포함해 [페이지의 모든 버전을 신속하게 삭제](https://developers.google.com/search/docs/crawling-indexing/amp/remove-amp?hl=ko#remove-all-content)합니다.
-   AMP가 아닌 표준 페이지는 그대로 유지하면서 AMP가 아닌 표준 페이지와 한 쌍을 이루는 [AMP 페이지만 삭제](https://developers.google.com/search/docs/crawling-indexing/amp/remove-amp?hl=ko#remove-only-amp)합니다.
-   [CMS로 AMP 콘텐츠를 삭제](https://developers.google.com/search/docs/crawling-indexing/amp/remove-amp?hl=ko#remove-amp-with-cms)합니다(모든 버전의 페이지를 삭제할 수도 있고 AMP 버전만 삭제할 수도 있음).

## AMP 페이지 및 AMP가 아닌 페이지를 포함하는 모든 버전의 AMP 콘텐츠 삭제

이 섹션에서는 AMP 페이지 및 AMP가 아닌 페이지를 포함해 모든 버전의 AMP 콘텐츠를 Google 검색에서 삭제하는 방법을 설명합니다.

Google 검색에서 AMP 페이지 및 AMP가 아닌 페이지를 삭제하려면 다음 단계를 따르세요.

1.  서버 또는 CMS에서 페이지의 AMP 버전 및 AMP가 아닌 버전을 삭제합니다.
2.  [오래된 콘텐츠 삭제](https://www.google.com/webmasters/tools/removals?hl=ko) 도구를 사용해 페이지 삭제를 요청합니다. 삭제할 페이지의 AMP 버전 및 AMP가 아닌 버전의 URL(웹 주소)을 입력 하세요.
3.  Google 검색에서 콘텐츠를 검색하여 AMP 페이지가 삭제되었는지 확인합니다. 많은 수의 AMP 페이지를 삭제한 후 이를 확인하려면 Search Console에 있는 [AMP 상태 보고서](https://search.google.com/search-console/amp?hl=ko)를 확인하세요. ['색인이 생성된 AMP 페이지' 그래프에서 추세선이 내려가는지 확인하세요.](https://support.google.com/webmasters/answer/7450883?hl=ko)

[오래된 콘텐츠 삭제](https://www.google.com/webmasters/tools/removals?hl=ko) 페이지에서 요청 상태를 확인할 수 있습니다.

## AMP가 아닌 표준 페이지는 유지하면서 AMP 페이지만 삭제

이 섹션에서는 AMP가 아닌 표준 페이지는 계속 유지하면서 Google 검색에서 AMP 페이지만 삭제하는 방법을 설명합니다.

Google 검색에서 AMP가 아닌 표준 페이지는 유지하면서 페이지의 AMP 버전을 삭제하려면 다음 단계를 따르세요.

1.  소스 코드에 있는 AMP가 아닌 표준 페이지에서 `rel="amphtml"` 링크를 삭제합니다.
2.  삭제된 AMP 페이지에 대해 `HTTP 301 Moved Permanently` 또는 `302 Found` 응답을 반환하도록 서버를 구성합니다.
3.  삭제된 AMP 페이지에서 AMP가 아닌 표준 페이지로 연결되는 리디렉션을 구성합니다.
4.  Google 검색에서 삭제하는 것 외에도 Google이 아닌 다른 플랫폼에서 AMP 페이지를 삭제하려면 다음 단계를 완료하세요.
    1.  AMP 페이지를 삭제하고, 서버가 삭제된 AMP 페이지에 `HTTP 404 Not Found`를 전송하도록 구성하여 AMP 페이지에 더 이상 액세스할 수 없도록 합니다.
    2.  Google 검색에서 콘텐츠를 검색하여 AMP 페이지가 삭제되었는지 확인합니다. 많은 수의 AMP 페이지를 삭제한 후 이를 확인하려면 Search Console에 있는 [AMP 상태 보고서](https://search.google.com/search-console/amp?hl=ko)를 사용하세요. ['색인이 생성된 AMP 페이지' 그래프에서 추세선이 내려가는지 확인하세요.](https://support.google.com/webmasters/answer/7450883?hl=ko)
    3.  퍼머링크를 활성 상태로 유지하려면 서버에서 삭제된 AMP 페이지의 `HTTP 301 Redirect`를 AMP가 아닌 표준 페이지로 보내도록 구성합니다.

## CMS로 AMP 페이지 및 AMP가 아닌 페이지 삭제

일반적으로 CMS 제공업체는 AMP 페이지와 AMP가 아닌 페이지를 동시에 게시합니다. 단일 페이지를 제거하려면 해당 페이지를 게시 취소하거나 삭제하세요. 그렇게 하면 해당 페이지의 AMP 버전 및 AMP가 아닌 버전이 모두 삭제됩니다.

### 단일 페이지 삭제

페이지를 삭제하고 AMP 및 AMP가 아닌 양식에서 모두 게시를 중지하려면 CMS 인터페이스를 사용하세요. AMP 게재를 중지하는 방법에 관한 자세한 내용은 CMS 제공업체의 도움말 페이지를 확인하세요.

-   [WordPress.com 도움말](https://en.support.wordpress.com/google-amp-accelerated-mobile-pages/)
-   [Drupal 도움말](https://cgit.drupalcode.org/amp/tree/README.md?h=8.x-1.x)
-   [SquareSpace 도움말](https://support.squarespace.com/hc/en-us/articles/223766868-Using-AMP-with-Squarespace)

### 모든 AMP 페이지 삭제

CMS에서 AMP를 사용 중지하는 것도 한 가지 방법입니다.

AMP를 사용 중지하려면 CMS 제공업체의 도움말 페이지를 확인하거나 CMS 제공업체에 문의하세요. 사이트가 CMS 도메인에 호스팅되어 있는 경우 AMP가 사용 중지된 후 CMS에서 사용자를 AMP가 아닌 표준 페이지로 리디렉션할 수 있습니다. 리디렉션되지 않으면 CMS 제공업체에 지원을 요청하세요.