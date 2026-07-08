# Google 예외 상황 크롤러 목록

예외 상황 크롤러는 크롤링된 사이트와 크롤링 프로세스 관련 제품 간에 합의가 이루어진 특정 Google 제품에서 사용됩니다. 예를 들어 `AdsBot`은 광고 게시자의 권한이 있는 전역 robots.txt 사용자 에이전트(`*`)를 무시합니다. Google 크롤러의 일반 [기술 속성](https://developers.google.com/crawling/docs/crawlers-fetchers/overview-google-crawlers?hl=ko#crawl-technical-props)은 예외 상황 크롤러에도 적용됩니다.

예외 상황 크롤러는 robots.txt 규칙을 무시할 수 있으므로 일반 크롤러와 다른 IP 범위에서 작동합니다. IP 범위는 [special-crawlers.json](https://developers.google.com/static/crawling/ipranges/special-crawlers.json?hl=ko) 개체에 게시됩니다. 예외 상황 크롤러의 역방향 DNS 마스크는 `rate-limited-proxy-***-***-***-***.google.com`과 일치합니다.

다음 목록은 예외 상황 크롤러, HTTP 요청에 표시되는 사용자 에이전트 문자열, robots.txt의 `User-agent:` 줄에 사용되는 사용자 에이전트 토큰, 크롤러용 크롤링 환경설정의 영향을 받는 제품을 보여줍니다. 이 목록은 일부일 뿐 전부 포함하지는 않습니다. 로그 파일에 나타날 가능성이 더 높으며 Google에 관련 문의가 접수되는 요청자만 다룹니다.

## [APIs-Google](https://developers.google.com/crawling/docs/crawlers-fetchers/apis-user-agent?hl=ko)

| **HTTP 요청의 사용자 에이전트** | APIs-Google (+https://developers.google.com/webmasters/APIs-Google.html) |
|-------------------|---------------------------------------------------------------------------------------------------------------------------------------------------|
| **robots.txt** | robots.txt의 사용자 에이전트 토큰

`APIs-Google`

___

전역 사용자 에이전트(`*`)는 무시됩니다.

robots.txt 그룹의 예

user-agent: **APIs-Google**
allow: /archive/1Q84
disallow: /archive/ |
| **영향을 받는 제품** | `APIs-Google` 사용자 에이전트로 주소가 지정된 크롤링 환경설정은 Google API의 푸시 알림 메시지 전송에 영향을 미칩니다. |

## AdsBot 모바일 웹

| **HTTP 요청의 사용자 에이전트** | Mozilla/5.0 (Linux; Android 6.0.1; Nexus 5X Build/MMB29P) AppleWebKit/537.36 (KHTML, like Gecko) [Chrome/_W.X.Y.Z_](https://developers.google.com/crawling/docs/crawlers-fetchers/google-common-crawlers?hl=ko#user_agent_version) Mobile Safari/537.36 (compatible; AdsBot-Google-Mobile; +http://www.google.com/mobile/adsbot.html) |
|-------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **robots.txt** | robots.txt의 사용자 에이전트 토큰

`AdsBot-Google-Mobile`

___

전역 사용자 에이전트(`*`)는 무시됩니다.

robots.txt 그룹의 예

user-agent: **AdsBot-Google-Mobile**
allow: /archive/1Q84
disallow: /archive/ |
| **영향을 받는 제품** | `AdsBot-Google-Mobile` 사용자 에이전트로 주소가 지정된 크롤링 환경설정은 Google Ads에서 [웹페이지 광고 품질](https://support.google.com/google-ads/answer/2404197?hl=ko)을 확인하는 기능에 영향을 미칩니다. |

## AdsBot

| **HTTP 요청의 사용자 에이전트** | AdsBot-Google (+http://www.google.com/adsbot.html) |
|-------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------|
| **robots.txt** | robots.txt의 사용자 에이전트 토큰

`AdsBot-Google`

___

전역 사용자 에이전트(`*`)는 무시됩니다.

robots.txt 그룹의 예

user-agent: **AdsBot-Google**
allow: /archive/1Q84
disallow: /archive/ |
| **영향을 받는 제품** | `AdsBot-Google` 사용자 에이전트로 주소가 지정된 크롤링 환경설정은 Google Ads에서 [웹페이지 광고 품질](https://support.google.com/google-ads/answer/2404197?hl=ko)을 확인하는 기능에 영향을 미칩니다. |

## [AdSense](https://support.google.com/adsense/answer/99376?hl=ko)

| **HTTP 요청의 사용자 에이전트** | 데스크톱 에이전트

Mediapartners-Google

모바일 에이전트

_(Various mobile device types)_ (compatible; Mediapartners-Google/2.1; +http://www.google.com/bot.html) |
|-------------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **robots.txt** | robots.txt의 사용자 에이전트 토큰

`Mediapartners-Google`

___

전역 사용자 에이전트(`*`)는 무시됩니다.

robots.txt 그룹의 예

user-agent: **Mediapartners-Google**
allow: /archive/1Q84
disallow: /archive/ |
| **영향을 받는 제품** | `Mediapartners-Google` 사용자 에이전트로 주소가 지정된 크롤링 환경설정은 Google 애드센스에 영향을 미칩니다. 애드센스 크롤러는 참여 사이트를 방문하여 관련성 있는 광고를 게재합니다. |

## Google 안전 센터

| **HTTP 요청의 사용자 에이전트** | Google-Safety |
|-------------------|----------------------------------------------------------------------------------------------------------|
| **robots.txt** | Google 안전 센터 사용자 에이전트는 robots.txt 규칙을 무시합니다. |
| **영향을 받는 제품** | Google 안전 센터 사용자 에이전트는 Google 서비스에 공개적으로 게시된 링크의 멀웨어 감지와 같은 악용 관련 크롤링을 처리합니다. 따라서 크롤링 환경설정의 영향을 받지 않습니다. |

## 중단된 예외 상황 크롤러

다음 예외 상황 크롤러는 더 이상 사용되지 않으며 여기에 기록 참고용으로만 표시됩니다.

### AdsBot 모바일 웹

## 중단된 예외 상황 크롤러

| **HTTP 요청의 사용자 에이전트** | Mozilla/5.0 (iPhone; CPU iPhone OS 14_7_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.2 Mobile/15E148 Safari/604.1 (compatible; AdsBot-Google-Mobile; +http://www.google.com/mobile/adsbot.html) |
|-------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **robots.txt** |  |
| **영향을 받는 제품** | `AdsBot-Google-Mobile` 사용자 에이전트로 주소가 지정된 크롤링 환경설정은 Google Ads에서 iPhone [웹페이지 광고 품질](https://support.google.com/google-ads/answer/2404197?hl=ko)을 확인하는 기능에 영향을 미칩니다. |

### Duplex on the web

## 중단된 예외 상황 크롤러

| **HTTP 요청의 사용자 에이전트** | Mozilla/5.0 (Linux; Android 11; Pixel 2; DuplexWeb-Google/1.0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/86.0.4240.193 Mobile Safari/537.36 |
|-------------------|-------------------------------------------------------------------------------------------------------------------------------------------------|
| **robots.txt** |  |
| **영향을 받는 제품** | Duplex on the web 서비스를 지원합니다. |

### [Google 파비콘](https://developers.google.com/search/docs/appearance/favicon-in-search?hl=ko#crawler)

## 중단된 예외 상황 크롤러

| **HTTP 요청의 사용자 에이전트** | Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/49.0.2623.75 Safari/537.36 Google Favicon |
|-------------------|-------------------------------------------------------------------------------------------------------------------------|
| **robots.txt** | robots.txt의 사용자 에이전트 토큰

`Googlebot-Image`

___

`Googlebot` |

### 모바일 앱 Android

## 중단된 예외 상황 크롤러

| **HTTP 요청의 사용자 에이전트** | AdsBot-Google-Mobile-Apps |
|-------------------|------------------------------------------------------------------------------------------------------------|
| **robots.txt** |  |
| **영향을 받는 제품** | `AdsBot-Google-Mobile-Apps` 사용자 에이전트로 주소가 지정된 크롤링 환경설정은 Google Ads에서 Android 앱 페이지 [광고 품질](https://support.google.com/google-ads/answer/2404197?hl=ko)을 확인하는 기능에 영향을 미칩니다. |

### Web Light

## 중단된 예외 상황 크롤러

| **HTTP 요청의 사용자 에이전트** | Mozilla/5.0 (Linux; Android 4.2.1; en-us; Nexus 5 Build/JOP40D) AppleWebKit/535.19 (KHTML, like Gecko; googleweblight) Chrome/38.0.1025.166 Mobile Safari/535.19 |
|-------------------|------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **robots.txt** |  |
| **영향을 받는 제품** | Web Light 사용자 에이전트는 사용자가 적절한 조건하에 Google 검색에서 페이지를 클릭할 때마다 `no-transform` 헤더의 존재 여부를 확인했습니다. |