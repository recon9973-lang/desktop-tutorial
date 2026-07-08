## 웹 크롤러 인증으로 요청 인증(실험용)

Google에서는 웹사이트에서 크롤러가 진짜인지 확인할 수 있도록 지원하는 새로운 암호화 프로토콜인 [웹 크롤러 인증](https://datatracker.ietf.org/doc/draft-meunier-http-message-signatures-directory/) IETF 인터넷 초안의 사용을 테스트하고 있습니다. Google 인프라에서 호스팅되는 일부 AI 에이전트를 사용하여 프로토콜을 테스트하고 있습니다. 이 가이드에서는 웹 크롤러 인증이 무엇인지, 현재 상태는 어떤지, 실험 단계에서 인증은 어떻게 구현하는지 설명합니다.

## 웹 크롤러 인증이란 무엇인가요?

웹 크롤러 인증은 크롤러가 보낸 요청을 인증하는 데 사용되는 실험적인 암호화 프로토콜입니다. 자체 신고 헤더와 IP 주소에만 의존하는 대신 웹 크롤러 인증을 사용하면 에이전트가 요청에 암호화 방식으로 서명할 수 있습니다.

웹 크롤러 인증을 사용하면 웹사이트 소유자가 사이트에서 자동화된 트래픽을 식별하고 다른 행위자가 평판이 좋은 에이전트를 스푸핑하려고 시도하는 것을 방지할 수 있습니다. 웹 크롤러 인증은 다음과 같은 이점을 제공할 수 있습니다.

-   **암호화된 확실성:** 쉽게 스푸핑되는 헤더를 넘어 인증된 ID로 이동하고 에이전트 ID를 IP 주소에서 분리합니다.
-   **모니터링 가능성 개선:** 에이전트가 콘텐츠와 상호작용하는 방식을 더 명확하게 파악할 수 있습니다.
-   **미래 대비:** 에이전트 제공업체와 웹사이트가 상호 신뢰를 구축하고 정보에 입각한 액세스 결정을 내릴 수 있는 웹을 구축하도록 지원합니다.

## 웹 크롤러 인증의 현재 상태: 실험용

Google의 [웹 크롤러 인증](https://datatracker.ietf.org/doc/draft-meunier-web-bot-auth-architecture/) 구현은 다음과 같은 이유로 현재 _실험용_입니다.

-   웹 크롤러 인증은 현재 IETF [WBA 실무 그룹](https://datatracker.ietf.org/wg/webbotauth/about/)에서 개발한 초안 사양이며, 시간이 지남에 따라 변경될 수 있습니다. Google은 실무 그룹의 작업이 진행됨에 따라 계속해서 참여하고 있습니다.
-   사용자 에이전트 및 IP 기반 크롤러 인증은 현재 사실상 표준이며, 이를 중심으로 수십 년간 시스템, 정책, 권장사항이 구축되었습니다. 이를 변경하려면 시간과 신중한 접근 방식이 필요하며, 아직 초기 단계로 프로토콜의 기술적 특성과 잠재적인 생태계 영향을 평가하고 있습니다.

### 이러한 메시지는 무엇을 의미하나요?

실험적 상태는 다음을 의미합니다.

-   일부 Google 사용자 에이전트는 웹 크롤러 인증을 사용하지 않습니다.
-   Google은 아직 프로토콜을 사용하는 에이전트의 모든 요청에 서명하지 않습니다.
-   서명된 트래픽이 점진적으로 출시되므로 웹 크롤러 인증 외에도 [IP 주소, 역방향 DNS, 사용자 에이전트 문자열](https://developers.google.com/crawling/docs/crawlers-fetchers/verify-google-requests?hl=ko)을 계속 사용하는 것이 좋습니다.

실험 단계에 참여하고자 하는 분들을 위해 Google AI 에이전트를 인식하고 허용 목록에 추가하는 방법에 관한 안내를 제공합니다.

실험용 AI 에이전트를 허용 목록에 추가하려는 개발자 또는 시스템 관리자는 웹 크롤러 인증 프로토콜을 통해 인증을 구현할 수 있습니다.

-   [웹 크롤러 인증을 지원하는 제품 또는 서비스 사용](https://developers.google.com/crawling/docs/crawlers-fetchers/web-bot-auth?hl=ko#products-and-services)
-   [직접 요청 인증하기](https://developers.google.com/crawling/docs/crawlers-fetchers/web-bot-auth?hl=ko#verify-requests-yourself)

### 웹 크롤러 인증을 지원하는 제품 또는 서비스 사용

주요 크롤러 감지 서비스, CDN, WAF는 웹 크롤러 인증을 지원합니다. 일부 인프라 서비스는 `[Google-Agent](https://developers.google.com/crawling/docs/crawlers-fetchers/google-user-triggered-fetchers?hl=ko#google-agent)` 사용자 에이전트를 조회하고 허용 목록에 추가하는 방법을 제공합니다. 정확한 단계는 제공업체에 문의하세요. `Google-Agent`에서 수행한 요청의 **하위 집합**은 웹 크롤러 인증으로 서명됩니다. 이러한 경우 `https://agent.bot.goog`로 인증됩니다. 제공업체에서 프로토콜을 지원하는 경우 자동으로 이를 확인할 가능성이 높습니다.

### 직접 요청 인증

요청을 직접 인증하려면 [자동 트래픽 아키텍처 사양을 위한 HTTP 메시지 서명](https://datatracker.ietf.org/doc/draft-meunier-web-bot-auth-architecture/) 및 [GitHub의 예시 구현](https://github.com/cloudflare/web-bot-auth)을 참고하세요. 일반적으로 주요 프로토콜 단계는 다음과 같습니다.

1.  [https://agent.bot.goog/.well-known/http-message-signatures-directory](https://agent.bot.goog/.well-known/http-message-signatures-directory)에서 에이전트의 공개 키 세트를 가져오고 `[Cache-Control](https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Headers/Cache-Control)` 헤더에 따라 캐시합니다.
2.  서버로 전송되는 참여 요청에는 `Signature-Agent` HTTP 요청 헤더가 `g="https://agent.bot.goog"`로 설정됩니다 (`g=` 라벨 참고).
3.  HTTP 메시지 서명 표준 ([RFC 9421](https://datatracker.ietf.org/doc/html/rfc9421))에 따라 `Signature-Input`에 따라 `Signature` 헤더를 확인합니다. `g`로 라벨이 지정된 `Signature` 및 `Signature-Input` 헤더를 사용합니다.
4.  모든 요청이 서명되는 것은 아니므로 [IP 기반 인증](https://developers.google.com/crawling/docs/crawlers-fetchers/verify-google-requests?hl=ko)으로 대체해야 합니다.

![웹 크롤러 인증 단계](https://developers.google.com/static/crawling/images/verify-requests-web-bot-auth.png?hl=ko)

지연 시간에 민감한 요청의 경우 미리 응답을 반환하고 [만료 기간](https://datatracker.ietf.org/doc/html/rfc9421#section-2.3-4.4) 내에 서명을 검증할 수 있습니다. 이 경우 사후 제재가 적용되며 호출자의 향후 요청에 이를 적용할 수 있습니다.

## 다음 단계

-   호스팅 또는 보안 제공업체에 문의하여 웹 크롤러 인증을 지원하는지 확인하세요.
-   [웹 크롤러 인증 실무 그룹](https://datatracker.ietf.org/wg/webbotauth/about/)의 기술 사양에 관한 최신 정보를 확인하세요.
-   [IETF 메일링 리스트](https://mailman3.ietf.org/mailman3/lists/web-bot-auth@ietf.org/)에서 토론에 참여하세요.
-   [웹 크롤러 인증 의견 양식](https://forms.gle/HyxC6SdPaAJCDHfv7)을 통해 의견을 보내주세요.