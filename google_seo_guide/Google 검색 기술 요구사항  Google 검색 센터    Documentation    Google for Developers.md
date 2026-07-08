누가 뭐라고 하든 검색결과에 페이지가 표시되게 하는 데에는 비용이 들지 않습니다. 페이지가 최소 기술 요구사항을 충족하기만 하면 Google 검색의 색인 생성 대상이 됩니다.

1.  Googlebot이 차단되지 않음
2.  페이지가 작동함, Google에서 HTTP `200 (success)` 상태 코드를 수신함
3.  페이지에 색인 생성 가능한 콘텐츠가 있습니다.

## Googlebot이 차단되지 않음(페이지 검색 및 액세스가 가능함)

Google은 일반 사용자가 액세스할 수 있으며 크롤러 [Googlebot](https://developers.google.com/search/docs/crawling-indexing/googlebot?hl=ko)이 페이지를 크롤링하지 못하도록 차단하지 않는 웹상의 페이지만 색인을 생성합니다. 페이지를 비공개로 만드는 경우(예: 로그인해야 볼 수 있는 경우) Googlebot은 페이지를 크롤링하지 않습니다. 마찬가지로 [여러 메커니즘](https://developers.google.com/search/docs/crawling-indexing/control-what-you-share?hl=ko) 중 하나를 사용하여 Google의 색인 생성을 차단할 경우 페이지의 색인이 생성되지 않습니다.

### Googlebot이 페이지를 찾고 액세스할 수 있는지 확인

[robots.txt](https://developers.google.com/search/docs/crawling-indexing/robots/intro?hl=ko)에 의해 차단된 페이지는 Google 검색결과에 표시될 가능성이 작습니다. Google에서 액세스할 수 없지만 검색결과에 표시하고 싶은 페이지 목록을 보려면 Search Console의 [페이지 색인 생성 보고서](https://support.google.com/webmasters/answer/7440203?hl=ko) 및 [크롤링 통계 보고서](https://support.google.com/webmasters/answer/9679690?hl=ko)를 모두 사용하세요. 보고서마다 URL에 관한 정보가 다를 수 있으므로 두 보고서를 모두 살펴보는 것이 좋습니다.

특정 페이지를 테스트하려면 [URL 검사 도구](https://support.google.com/webmasters/answer/9012289?hl=ko)를 사용하세요.

## 페이지가 작동함(오류 메시지가 표시되지 않음)

Google은 [HTTP `200 (success)` 상태 코드](https://developers.google.com/crawling/docs/troubleshooting/http-status-codes?hl=ko#2xx-success)로 게재되는 페이지만 색인을 생성합니다. 클라이언트 및 서버 오류 페이지의 색인은 생성되지 않았습니다. [URL 검사 도구](https://support.google.com/webmasters/answer/9012289?hl=ko)를 사용하여 특정 페이지의 HTTP 상태 코드를 확인할 수 있습니다.

## 페이지에 색인 생성 가능한 콘텐츠가 있음

Googlebot이 작동하는 페이지를 찾아서 액세스할 수 있게 되면 Google은 페이지에 색인 생성 가능한 콘텐츠가 있는지 확인합니다. 색인 생성 가능 콘텐츠란 다음을 의미합니다.

-   텍스트 콘텐츠가 [Google 검색에서 지원하는 파일 형식](https://developers.google.com/search/docs/crawling-indexing/indexable-file-types?hl=ko)으로 되어 있습니다.
-   콘텐츠가 Google의 [스팸 정책](https://developers.google.com/search/docs/essentials/spam-policies?hl=ko)을 위반하지 않습니다.