## 호스팅 변경

이 가이드에서 사이트의 호스팅 인프라 변경이 Google 검색에서 사이트 실적에 미치는 영향을 최소화하는 방법을 알아보세요. 호스팅 인프라를 변경하면 호스팅 업체를 바꾸거나 콘텐츠 전송 네트워크(CDN)로 이전해야 합니다. 이 가이드는 사용자에게 표시되는 URL에 영향을 미치지 않는 이전에만 적용됩니다.

## 개요

1.  **[새 호스팅 인프라를 준비합니다](https://developers.google.com/search/docs/crawling-indexing/site-move-no-url-changes?hl=ko#hosting-infrastructure)**. 콘텐츠를 새로운 서버에 업로드하거나 CDN과 원본 서버를 구성한 후 테스트합니다.
2.  **[사이트 이전을 시작합니다](https://developers.google.com/search/docs/crawling-indexing/site-move-no-url-changes?hl=ko#start-site-move)**. 새 호스팅 인프라를 가리키도록 도메인 이름의 DNS 설정을 변경합니다. 이 단계는 트래픽을 새 인프라로 보내는 프로세스의 첫걸음을 떼는 실제 사이트 이전 단계입니다.
3.  **[트래픽을 모니터링합니다](https://developers.google.com/search/docs/crawling-indexing/site-move-no-url-changes?hl=ko#monitor)**. 이전 호스팅과 새 호스팅에서 제공하는 트래픽을 계속 주시합니다.
4.  **[종료합니다](https://developers.google.com/search/docs/crawling-indexing/site-move-no-url-changes?hl=ko#shut-down-old-hosting)**. 모든 사용자가 Googlebot을 포함한 새 인프라에서 콘텐츠를 제대로 수신하고 있으며 이전 인프라를 사용하는 사용자가 없다고 확인되면 이전 호스팅 인프라를 종료합니다.

## 새 호스팅 인프라 준비

이 섹션에서는 실제 인프라 이전을 시작하기 전에 따라야 하는 단계를 다룹니다.

### 새 사이트 복사 및 테스트

먼저 사이트 사본을 새 호스팅 업체에 업로드합니다. '웹사이트 사본'의 의미는 이전 콘텐츠 관리 플랫폼에 따라 완전히 다릅니다. 새 호스팅 플랫폼에 복제하는 실제 HTML 파일이거나 새 위치에서 가져와야 하는 데이터베이스 내보내기일 수 있습니다. 업로드가 완료되면 사용자가 사이트와 상호작용하는 방식의 모든 측면을 철저히 테스트하여 알맞게 작동하는지 확인합니다. 다음은 몇 가지 제안사항입니다.

-   **테스트 환경을 구성합니다**(IP 제한 액세스가 포함될 수 있음). 이를 통해 웹사이트를 게시하기 전에 모든 기능을 테스트합니다.
-   **웹브라우저에서 새 사이트를 열고** 페이지, 이미지, 양식, 다운로드(예: PDF 파일) 등 사이트의 요소를 모두 검토합니다.
-   새 인프라의 임시 호스트 이름(예: `beta.example.com`)으로 **공개 테스트를 허용**하여 브라우저의 접근성을 테스트합니다. 임시 호스트 이름을 사용하면 Googlebot의 사이트 도달 가능 여부를 테스트할 수 있습니다. 실수로 테스트 사이트의 색인이 생성되지 않도록 하려면 페이지의 HTML 또는 HTTP 헤더에 [`noindex` `robots` 규칙](https://developers.google.com/search/docs/crawling-indexing/block-indexing?hl=ko)을 추가하세요.

### Googlebot이 새 호스팅 인프라에 액세스할 수 있는지 확인

Search Console 계정이 아직 없다면 사이트의 [새 계정을 만들어](https://support.google.com/webmasters/answer/34592?hl=ko) Google 액세스 및 트래픽을 모니터링할 수 있습니다. 새 사이트의 임시 호스트 이름을 만든 경우 해당 속성도 확인하세요. Search Console에서 [URL 검사 도구](https://support.google.com/webmasters/answer/9012289?hl=ko)를 사용하여 Googlebot이 새 인프라에 액세스할 수 있는지를 확인합니다.

### DNS 레코드의 TTL 값 낮추기

사이트 DNS 레코드의 TTL 값을 낮추면 새 설정이 ISP에 더 빠르게 전파되므로 사이트 이전 속도를 높일 수 있습니다. 일반적으로 DNS 설정은 지정된 [TTL(수명) 설정](https://wikipedia.org/wiki/Time_to_live#DNS_records)에 따라 ISP에서 캐시합니다. DNS 캐시의 새로고침 속도를 더 빠르게 하기 위해 적어도 이전 일주일 전에 TTL을 보수적으로 낮은 값(예: 몇 시간)으로 낮추는 것이 좋습니다.

### Search Console 확인 검토

호스팅을 이전한 후에도 Search Console 확인이 계속 작동하는지 확인하세요.

[HTML 파일을 이용하는 방법](https://support.google.com/webmasters/answer/9008080?hl=ko#html_verification)을 사용하여 Search Console에서 사이트 소유권을 확인하는 경우 현재 확인 파일을 사이트의 새 사본에 포함해야 합니다.

마찬가지로 콘텐츠 관리 시스템(CMS)의 템플릿에 [`meta` 태그](https://support.google.com/webmasters/answer/9008080?hl=ko#meta_tag_verification) 또는 [Google 애널리틱스](https://support.google.com/webmasters/answer/9008080?hl=ko#google_analytics_verification)를 포함하여 소유권을 확인하려면 새 CMS 사본에도 이를 포함해야 합니다.

## 이전 시작

이전 절차는 다음과 같습니다.

1.  **크롤링 임시 차단 기능을 모두 삭제합니다**. 사이트의 새 사본을 만드는 동안 일부 사이트 소유자는 robots.txt 파일을 사용하여 Googlebot 및 다른 크롤러의 크롤링을 모두 금지하거나 `noindex` `meta` 태그 또는 HTTP 헤더를 사용하여 콘텐츠의 색인 생성을 차단합니다. 이전을 시작할 준비가 되면 사이트의 새 사본에서 이러한 차단 기능을 모두 삭제해야 합니다.
2.  **DNS 설정을 업데이트합니다**. 새 호스팅 업체를 가리키도록 DNS 레코드를 업데이트하여 이전을 시작합니다. 업데이트 방법은 DNS 제공업체에 문의하세요.

## 트래픽 모니터링

인프라 변경이 원활하게 진행되는지 모니터링하려면 다음 단계를 따르세요.

-   **새 서버와 이전 서버의 서버 로그를 모두 확인합니다.**  
    DNS 설정이 전파되고 사이트 트래픽이 이동함에 따라 이전 서버에 로그되는 트래픽이 줄어들고 새 서버의 트래픽이 그만큼 증가함을 확인하게 됩니다.
-   **다른 공개 DNS 확인 도구를 사용합니다.**  
    전 세계의 서로 다른 ISP에서 새 DNS 설정으로 적절하게 업데이트하고 있는지 확인합니다.
-   **크롤링을 모니터링합니다.**  
    Search Console에서 [색인 생성 범위](https://support.google.com/webmasters/answer/7440203?hl=ko) 그래프를 모니터링합니다.

### Googlebot의 크롤링 속도 관련 참고사항

호스팅 인프라를 변경하면 일반적으로 사이트 게시 직후에는 Googlebot의 크롤링 속도가 일시적으로 떨어졌다가 이후 며칠 동안 점차 증가하여 이전하기 전보다 높아질 수 있습니다.

속도 변동이 발생하는 이유는 사이트의 크롤링 속도가 여러 신호를 토대로 결정되며 호스팅을 변경하면 이러한 신호도 변경되기 때문입니다. 새 인프라에 액세스할 때 Googlebot에 심각한 문제나 속도 저하가 발생하지 않는 한 Googlebot은 필요한 경우 가능한 한 빨리 사이트를 크롤링하려고 합니다.

## 이전 호스팅 종료

이전 업체의 서버 로그를 확인하여 트래픽이 0에 도달하면 이전 호스팅 인프라를 종료하세요. 이로써 호스팅 변경이 완료됩니다.