네트워크 오류와 DNS 오류는 Google이 URL을 성공적으로 크롤링할 수 있는지에 즉각적으로 부정적인 영향을 미칩니다. Google은 네트워크 시간 초과, 연결 재설정, DNS 오류를 `5xx` 서버 오류와 유사하게 처리합니다. 네트워크 오류는 서버가 실행 중인 로드를 처리하지 못할 수 있다는 신호이기 때문에 크롤링 속도가 즉시 저하되기 시작합니다. Google이 사이트를 호스팅하는 서버에 도달할 수 없었으므로 Google도 서버에서 아무런 콘텐츠도 받지 못했습니다.

Google 검색의 경우 콘텐츠 부족으로 인해 Google에서 크롤링된 URL의 색인을 생성할 수 없으며, 이미 색인이 생성되었으나 도달할 수 없는 URL은 며칠 내로 Google 색인에서 삭제됩니다. Search Console은 각각의 오류와 관련해 오류 메시지를 생성할 수 있습니다.

## 네트워크 오류 디버그

이러한 오류는 Google에서 URL 크롤링을 시작하기 전이나 크롤링하는 중에 발생합니다. 서버가 응답하기 전에 오류가 발생할 수 있고 이때 문제의 의미를 나타내는 상태 코드가 없기 때문에 오류를 진단하기가 더 어려울 수 있습니다. 시간 초과 및 연결 재설정 오류를 디버그하려면 다음과 같이 합니다.

-   **방화벽 설정 및 로그를 확인**합니다. 설정된 차단 규칙이 지나치게 광범위할 수 있습니다. [Google IP 주소](https://developers.google.com/crawling/docs/crawlers-fetchers/verify-google-requests?hl=ko#use-automatic-solutions)가 방화벽 규칙에 의해 차단되지 않는지 확인합니다.
-   **네트워크 트래픽을 확인**합니다. [tcpdump](https://www.tcpdump.org/manpages/tcpdump.1.html)나 [Wireshark](https://www.wireshark.org/) 같은 도구를 사용해 TCP 패킷을 캡처, 분석하고 특정 네트워크 구성요소나 서버 모듈을 가리키는 이상 징후를 찾습니다.
-   **의심스러운 항목을 찾지 못하면 호스팅 업체에 문의**합니다.

네트워크 트래픽을 처리하는 서버 구성요소에 오류가 있을 수 있습니다. 예를 들어 과부하된 네트워크 인터페이스가 시간 초과(연결을 설정할 수 없음) 및 연결 재설정(포트가 실수로 닫혀서 `RST` 패킷이 전송됨)을 초래한 패킷을 삭제할 수 있습니다.

## DNS 오류 디버그

DNS 오류는 주로 잘못된 구성으로 인해 발생하지만, Google DNS 쿼리를 차단하는 방화벽 규칙에 의해 발생할 수도 있습니다. DNS 오류를 디버그하려면 다음과 같이 합니다.

-   **방화벽 규칙을 검사합니다**. 방화벽 규칙에 의해 차단된 [Google IP가 없고](https://developers.google.com/crawling/docs/crawlers-fetchers/verify-google-requests?hl=ko#use-automatic-solutions) `UDP`와 `TCP` 요청이 모두 허용되는지 확인합니다.
-   **DNS 레코드를 확인**합니다. `A` 레코드와 `CNAME` 레코드가 각각 올바른 IP 주소와 호스트 이름을 가리키는지 다시 한번 확인합니다. 예를 들면 다음과 같습니다.
    
    ```
    dig +nocmd example.com a +noall +answer
    ```
    
    ```
    dig +nocmd www.example.com cname +noall +answer
    ```
    
-   **모든 네임서버가 사이트의 올바른 IP 주소를 가리키는지 확인**합니다. 예를 들면 다음과 같습니다.
    
    ```
    dig +nocmd example.com ns +noall +answer
    ```
    
-   **최근 72시간 이내에 DNS 구성을 변경한 경우** 변경사항이 전역 DNS 네트워크에 전파될 때까지 기다려야 할 수도 있습니다. 전파 속도를 높이려면 [Google의 공개 DNS 캐시를 플러시](https://developers.google.com/speed/public-dns/faq?hl=ko#update_cache)하면 됩니다.
-   **자체 DNS 서버를 실행 중인 경우** 서버가 정상 상태로 유지되고 과부하되지 않도록 합니다.