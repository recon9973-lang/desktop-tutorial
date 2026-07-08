서버에 대한 요청이 실제로 [Google에서 전송된 것인지](https://developers.google.com/crawling/docs/crawlers-fetchers/overview-google-crawlers?hl=ko) 확인할 수 있습니다. Googlebot과 같은 크롤러는 물론 다른 요청도 확인할 수 있습니다. 이 방법은 스팸 발송자나 악의적 사용자가 Google을 가장하여 사이트에 액세스하지 못하게 하는 데 도움이 됩니다.

Google 크롤러 및 가져오기 도구는 세 가지 카테고리로 분류됩니다.

| 유형 | 설명 | 역방향 DNS 마스크 | IP 범위 |
|--------------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|---------------------------------------------------------------|-----------------------------------------------------------------------------------------------|
| [일반 크롤러](https://developers.google.com/crawling/docs/crawlers-fetchers/google-common-crawlers?hl=ko) | Google 제품에 사용되는 일반 크롤러(예: Googlebot)입니다. 자동 크롤링에 대한 robots.txt 규칙을 항상 준수합니다. | `crawl-***-***-***-***.googlebot.com` 또는 `geo-crawl-***-***-***-***.geo.googlebot.com` | [common-crawlers.json](https://developers.google.com/static/crawling/ipranges/common-crawlers.json?hl=ko) |
| [예외 상황 크롤러](https://developers.google.com/crawling/docs/crawlers-fetchers/google-special-case-crawlers?hl=ko) | 크롤링된 사이트와 액세스 또는 악용 사례별 크롤링이나 가져오기에 관한 제품 간에 합의가 이루어진 경우 Google 제품의 특정 기능 (예: AdsBot)을 수행하는 크롤러 또는 가져오기 도구입니다. 이러한 크롤러 또는 가져오기 도구는 robots.txt 규칙을 준수할 수도 있고 준수하지 않을 수도 있습니다. | `rate-limited-proxy-***-***-***-***.google.com` | [special-crawlers.json](https://developers.google.com/static/crawling/ipranges/special-crawlers.json?hl=ko) |
| [사용자 트리거 가져오기](https://developers.google.com/crawling/docs/crawlers-fetchers/google-user-triggered-fetchers?hl=ko) | 최종 사용자가 가져오기를 트리거하는 도구 및 제품 기능입니다. 예를 들어 [Google 사이트 인증 도구](https://support.google.com/webmasters/answer/9008080?hl=ko)는 사용자의 요청에 따라 작동합니다. 사용자가 가져오기를 요청했으므로 해당 가져오기는 robots.txt 규칙을 무시합니다.<br>Google에서 제어하는 가져오기 도구는 `user-triggered-fetchers-google.json` 객체의 IP에서 시작되며 `google.com` 호스트 이름으로 확인됩니다. `user-triggered-fetchers.json` 객체의 IP는 `gae.googleusercontent.com` 호스트 이름으로 확인됩니다. 이 IP는 예를 들어 Google Cloud(GCP)에서 실행되는 사이트에 해당 사이트 사용자의 요청에 따라 외부 RSS 피드를 가져와야 하는 기능이 있는 경우에 사용됩니다. | `***-***-***-***.gae.googleusercontent.com` 또는 `google-proxy-***-***-***-***.google.com` | [user-triggered-fetchers.json](https://developers.google.com/static/crawling/ipranges/user-triggered-fetchers.json?hl=ko), [user-triggered-fetchers-google.json](https://developers.google.com/static/crawling/ipranges/user-triggered-fetchers-google.json?hl=ko), [user-triggered-agents.json](https://developers.google.com/static/crawling/ipranges/user-triggered-agents.json?hl=ko) |

Google의 요청을 확인하는 방법에는 두 가지가 있습니다.

-   [수동](https://developers.google.com/crawling/docs/crawlers-fetchers/verify-google-requests?hl=ko#manual): 일회성 조회의 경우 명령줄 도구를 사용합니다. 이 방법만 사용해도 대부분의 사용 사례에 충분합니다.
-   [자동](https://developers.google.com/crawling/docs/crawlers-fetchers/verify-google-requests?hl=ko#automatic): 대규모 조회의 경우 자동 솔루션을 사용하여 크롤러의 IP 주소를 게시된 Google IP 주소 목록과 대조합니다.

## 명령줄 도구 사용

1.  `host` 명령어를 사용해 로그의 액세스 IP 주소에 역방향 DNS 조회를 실행합니다.
2.  도메인 이름이 `googlebot.com`, `google.com`, 또는 `googleusercontent.com`인지 확인합니다.
3.  검색된 도메인 이름에서 `host` 명령어를 사용해 1단계에서 검색된 도메인 이름에 순방향 DNS 조회를 실행합니다.
4.  로그의 원래 액세스 IP 주소와 동일한지 확인합니다.

**예 1:**

```
host 66.249.66.1
```

**예 2:**

```
host 35.247.243.240
```

**예 3:**

```
host 66.249.90.77
```

## 자동 솔루션 사용

또는 크롤러의 IP 주소를 Googlebot 크롤러 및 가져오기의 IP 범위 목록과 대조해 IP 주소로 Googlebot을 식별할 수도 있습니다.

-   [Googlebot과 같은 일반 크롤러](https://developers.google.com/static/crawling/ipranges/common-crawlers.json?hl=ko)
-   [AdsBot과 같은 특수 크롤러](https://developers.google.com/static/crawling/ipranges/special-crawlers.json?hl=ko)
-   [사용자 트리거 가져오기 도구(사용자)](https://developers.google.com/static/crawling/ipranges/user-triggered-fetchers.json?hl=ko)
-   [사용자 트리거 가져오기 도구(Google)](https://developers.google.com/static/crawling/ipranges/user-triggered-fetchers-google.json?hl=ko)
-   [사용자 트리거 에이전트](https://developers.google.com/static/crawling/ipranges/user-triggered-agents.json?hl=ko)

사이트에 액세스할 수 있는 다른 Google IP 주소(예: [Apps Script](https://developers.google.com/apps-script?hl=ko))는 액세스 IP 주소를 [Google IP 주소 목록](https://www.gstatic.com/ipranges/goog.json)과 대조합니다. JSON 파일의 IP 주소는 [CIDR 형식](https://wikipedia.org/wiki/Classless_Inter-Domain_Routing)으로 표시됩니다.