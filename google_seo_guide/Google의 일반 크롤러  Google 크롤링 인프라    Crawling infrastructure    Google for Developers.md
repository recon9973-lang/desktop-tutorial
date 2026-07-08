Google의 일반 크롤러는 Google의 검색 색인을 만들기 위한 정보를 찾고, 다른 제품과 관련된 크롤링을 수행하며, 분석하는 데 사용됩니다. 일반 크롤러는 자동으로 크롤링할 때 항상 [robots.txt 규칙](https://developers.google.com/crawling/docs/robots-txt/robots-txt-spec?hl=ko)을 준수합니다. Google 크롤러의 일반 [기술 속성](https://developers.google.com/crawling/docs/crawlers-fetchers/overview-google-crawlers?hl=ko#crawl-technical-props)은 일반 크롤러에도 적용됩니다.

일반 크롤러는 일반적으로 [common-crawlers.json](https://developers.google.com/static/crawling/ipranges/common-crawlers.json?hl=ko) 객체, 호스트 이름이 `crawl-***-***-***-***.googlebot.com` 또는 `geo-crawl-***-***-***-***.geo.googlebot.com`인 역방향 DNS 마스크에 게시된 IP 범위에서 크롤링합니다.

다음 목록은 일반 크롤러, HTTP 요청에 표시되는 사용자 에이전트 문자열, robots.txt의 `User-agent:` 줄에 사용되는 사용자 에이전트 토큰, 크롤러용 크롤링 환경설정의 영향을 받는 제품을 보여줍니다. 일부 크롤러에는 사용자 에이전트 토큰이 두 개 이상 있습니다. 규칙을 적용하려면 크롤러 토큰 하나만 일치시켜야 합니다. 이 목록은 일부일 뿐 전부 포함하지는 않습니다. 로그 파일에 나타날 가능성이 더 높으며 Google에 관련 문의가 접수되는 요청자만 다룹니다.

## [Googlebot](https://developers.google.com/search/docs/crawling-indexing/googlebot?hl=ko)

| **HTTP 요청의 `User-Agent`** | Googlebot 스마트폰

Mozilla/5.0 (Linux; Android 6.0.1; Nexus 5X Build/MMB29P) AppleWebKit/537.36 (KHTML, like Gecko) [Chrome/_W.X.Y.Z_](https://developers.google.com/crawling/docs/crawlers-fetchers/google-common-crawlers?hl=ko#user_agent_version) Mobile Safari/537.36 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)

Googlebot 데스크톱

Mozilla/5.0 AppleWebKit/537.36 (KHTML, like Gecko; compatible; Googlebot/2.1; +http://www.google.com/bot.html) [Chrome/_W.X.Y.Z_](https://developers.google.com/crawling/docs/crawlers-fetchers/google-common-crawlers?hl=ko#user_agent_version) Safari/537.36

드물게:

-   `Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)`
-   `Googlebot/2.1 (+http://www.google.com/bot.html)` |
|---------------------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **robots.txt** | robots.txt의 사용자 에이전트 토큰

`Googlebot`

robots.txt 그룹의 예

user-agent: **Googlebot**
allow: /archive/1Q84
disallow: /archive |
| **영향을 받는 제품** | `Googlebot` 사용자 에이전트로 주소가 지정된 크롤링 환경설정은 Google 검색(디스커버 및 모든 Google 검색 기능 포함) 및 기타 제품(예: Google 이미지, Google 비디오, Google 뉴스, 디스커버)에 영향을 미칩니다. |

## Googlebot 이미지

| **HTTP 요청의 사용자 에이전트** | Googlebot-Image/1.0 |
|-------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------|
| **robots.txt** | robots.txt의 사용자 에이전트 토큰

`Googlebot-Image`

___

`Googlebot`

robots.txt 그룹의 예

user-agent: **Googlebot-Image**
allow: /archive/1Q84
disallow: /archive/moons.jpg |
| **영향을 받는 제품** | `Googlebot-Image` 사용자 에이전트로 주소가 지정된 크롤링 환경설정은 Google 이미지, 디스커버, Google 비디오뿐 아니라 이미지, 로고, favicon이 표시되는 Google 검색의 모든 기능에 영향을 미칩니다. |

## Googlebot 동영상

| **HTTP 요청의 사용자 에이전트** | Googlebot-Video/1.0 |
|-------------------|-----------------------------------------------------------------------------------------------------------------------------------------------|
| **robots.txt** | robots.txt의 사용자 에이전트 토큰

`Googlebot-Video`

___

`Googlebot`

robots.txt 그룹의 예

user-agent: **Googlebot-Video**
allow: /archive/1Q84
disallow: /archive/ |
| **영향을 받는 제품** | `Googlebot-Video` 사용자 에이전트로 주소가 지정된 크롤링 환경설정은 동영상 관련 Google 검색 기능 및 동영상에 종속된 기타 제품에 영향을 미칩니다. |

## Googlebot 뉴스

| **HTTP 요청의 사용자 에이전트** | Googlebot 뉴스에는 별도의 HTTP 요청 사용자 에이전트 문자열이 없습니다. 크롤링은 [다양한 Googlebot 사용자 에이전트 문자열](https://developers.google.com/crawling/docs/crawlers-fetchers/google-common-crawlers?hl=ko#googlebot)을 사용하여 실행됩니다. |
|-------------------|---------------------------------------------------------------------------------------------------------------------------------------------|
| **robots.txt** | robots.txt의 사용자 에이전트 토큰

`Googlebot-News`

___

`Googlebot`

robots.txt 그룹의 예

user-agent: **Googlebot-News**
allow: /archive/1Q84
disallow: /archive/ |
| **영향을 받는 제품** | `Googlebot-News` 사용자 에이전트로 주소가 지정된 크롤링 환경설정은 [news.google.com](https://news.google.com/?hl=ko) 및 Google 뉴스 앱을 비롯한 Google 뉴스 제품에 영향을 미칩니다. |

## [Google StoreBot](https://support.google.com/merchants/answer/13294660?hl=ko)

| **HTTP 요청의 사용자 에이전트** | 데스크톱 에이전트

Mozilla/5.0 (X11; Linux x86_64; Storebot-Google/1.0) AppleWebKit/537.36 (KHTML, like Gecko) [Chrome/_W.X.Y.Z_](https://developers.google.com/crawling/docs/crawlers-fetchers/google-common-crawlers?hl=ko#user_agent_version) Safari/537.36

모바일 에이전트

Mozilla/5.0 (Linux; Android 8.0; Pixel 2 Build/OPD3.170816.012; Storebot-Google/1.0) AppleWebKit/537.36 (KHTML, like Gecko) [Chrome/_W.X.Y.Z_](https://developers.google.com/crawling/docs/crawlers-fetchers/google-common-crawlers?hl=ko#user_agent_version) Mobile Safari/537.36 |
|-------------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **robots.txt** | robots.txt의 사용자 에이전트 토큰

`Storebot-Google`

robots.txt 그룹의 예

user-agent: **Storebot-Google**
allow: /archive/1Q84
disallow: /archive/konbini |
| **영향을 받는 제품** | `Storebot-Google` 사용자 에이전트로 주소가 지정된 크롤링 환경설정은 Google 쇼핑의 모든 표시 경로(예: Google 검색 쇼핑 탭 및 [Google 쇼핑](https://shopping.google.com/?hl=ko))에 영향을 미칩니다. |

## Google-InspectionTool

| **HTTP 요청의 사용자 에이전트** | 데스크톱 에이전트

Mozilla/5.0 (compatible; Google-InspectionTool/1.0;)

모바일 에이전트

Mozilla/5.0 (Linux; Android 6.0.1; Nexus 5X Build/MMB29P) AppleWebKit/537.36 (KHTML, like Gecko) [Chrome/_W.X.Y.Z_](https://developers.google.com/crawling/docs/crawlers-fetchers/google-common-crawlers?hl=ko#user_agent_version) Mobile Safari/537.36 (compatible; Google-InspectionTool/1.0;) |
|-------------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **robots.txt** | robots.txt의 사용자 에이전트 토큰

`Google-InspectionTool`

___

`Googlebot`

robots.txt 그룹의 예

user-agent: **Google-InspectionTool**
allow: /archive/1Q84
disallow: /archive/ |
| **영향을 받는 제품** | `Google-InspectionTool` 사용자 에이전트로 주소가 지정된 크롤링 환경설정은 검색 테스트 도구(예: [리치 결과 테스트](https://search.google.com/test/rich-results?hl=ko) 및 Search Console의 [URL 검사](https://support.google.com/webmasters/answer/9012289?hl=ko))에 영향을 미칩니다. Google 검색 또는 기타 제품에는 영향을 미치지 않습니다. |

## GoogleOther

| **HTTP 요청의 사용자 에이전트** | Mozilla/5.0 (Linux; Android 6.0.1; Nexus 5X Build/MMB29P) AppleWebKit/537.36 (KHTML, like Gecko) [Chrome/_W.X.Y.Z_](https://developers.google.com/crawling/docs/crawlers-fetchers/google-common-crawlers?hl=ko#user_agent_version) Mobile Safari/537.36 (compatible; GoogleOther)

___

Mozilla/5.0 AppleWebKit/537.36 (KHTML, like Gecko; compatible; GoogleOther) [Chrome/_W.X.Y.Z_](https://developers.google.com/crawling/docs/crawlers-fetchers/google-common-crawlers?hl=ko#user_agent_version) Safari/537.36 |
|-------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **robots.txt** | robots.txt의 사용자 에이전트 토큰

`GoogleOther`

robots.txt 그룹의 예

user-agent: **GoogleOther**
allow: /archive/1Q84
disallow: /archive/ |
| **영향을 받는 제품** | `GoogleOther` 사용자 에이전트로 주소가 지정된 크롤링 환경설정은 특정 제품에 영향을 미치지 않습니다. GoogleOther는 사이트에서 사용자가 공개적으로 액세스할 수 있는 콘텐츠를 가져오기 위해 여러 제품팀에서 사용할 수 있는 일반적인 크롤러입니다. 예를 들어 내부 연구 및 개발을 위한 일회성 크롤링에 사용할 수 있습니다. |

## GoogleOther-Image

| **HTTP 요청의 사용자 에이전트** | GoogleOther-Image/1.0 |
|-------------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **robots.txt** | robots.txt의 사용자 에이전트 토큰

`GoogleOther-Image`

___

`GoogleOther`

robots.txt 그룹의 예

user-agent: **GoogleOther-Image**
allow: /archive/1Q84
disallow: /archive/moon.jpg |
| **영향을 받는 제품** | `GoogleOther-Image` 사용자 에이전트로 주소가 지정된 크롤링 환경설정은 GoogleOther와 유사한 특정 제품에 영향을 미치지 않습니다. GoogleOther-Image는 공개적으로 액세스할 수 있는 이미지 URL을 가져오는 데 최적화된 GoogleOther 버전입니다. |

## GoogleOther-Video

| **HTTP 요청의 사용자 에이전트** | GoogleOther-Video/1.0 |
|-------------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **robots.txt** | robots.txt의 사용자 에이전트 토큰

`GoogleOther-Video`

___

`GoogleOther`

robots.txt 그룹의 예

user-agent: **GoogleOther-Video**
allow: /archive/1Q84
disallow: /archive |
| **영향을 받는 제품** | `GoogleOther-Video` 사용자 에이전트로 주소가 지정된 크롤링 환경설정은 GoogleOther와 유사한 특정 제품에 영향을 미치지 않습니다. GoogleOther-Video는 공개적으로 액세스할 수 있는 동영상 URL을 가져오는 데 최적화된 GoogleOther 버전입니다. |

## Google-CloudVertexBot

| **HTTP 요청의 사용자 에이전트 하위 문자열** | Google-CloudVertexBot |
|--------------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------|
| **robots.txt** | robots.txt의 사용자 에이전트 토큰

`Google-CloudVertexBot`

___

`Googlebot`

robots.txt 그룹의 예

user-agent: **Google-CloudVertexBot**
allow: /archive/1Q84
disallow: /archive/ |
| **영향을 받는 제품** | `Google-CloudVertexBot` 사용자 에이전트로 주소가 지정된 크롤링 환경설정은 사이트 소유자가 [Vertex AI 에이전트](https://cloud.google.com/generative-ai-app-builder/docs/prepare-data?hl=ko#website) 빌드를 위해 요청한 크롤링에 영향을 미칩니다. Google 검색 또는 기타 제품에는 영향을 미치지 않습니다. |

## Google-Extended

| **HTTP 요청의 사용자 에이전트** | Google-Extended에는 별도의 HTTP 요청 사용자 에이전트 문자열이 없습니다. 크롤링은 기존 Google 사용자 에이전트 문자열을 사용하여 실행됩니다. robots.txt 사용자 에이전트 토큰은 제어 기능으로 사용됩니다. |
|-------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **robots.txt** | robots.txt의 사용자 에이전트 토큰

`Google-Extended`

robots.txt 그룹의 예

user-agent: **Google-Extended**
allow: /archive/1Q84
disallow: /archive/ |
| **영향을 받는 제품** | `Google-Extended`는 독립형 제품 토큰으로서, 웹 게시자는 이를 사용해 Google이 사이트에서 크롤링하는 콘텐츠를 [Gemini 앱](https://support.google.com/gemini/answer/13594961?hl=ko#gemini_apps&zippy=,what-are-gemini-apps) 및 [Gemini용 Vertex AI API](https://cloud.google.com/vertex-ai/generative-ai/docs/model-reference/inference?hl=ko)를 지원하는 차세대 Gemini 모델을 학습시키는 데 사용하거나, [Gemini 앱](https://support.google.com/gemini/answer/13594961?hl=ko#gemini_apps&zippy=,what-are-gemini-apps) 및 [Vertex AI에서 Google 검색을 사용한 그라운딩](https://cloud.google.com/vertex-ai/generative-ai/docs/grounding/overview?hl=ko#ground-public)에서 그라운딩(프롬프트 시 사실성 및 관련성 개선을 위해 Google 검색 색인의 콘텐츠를 모델에 제공하는 것)에 사용할 수 있는지 여부를 관리할 수 있습니다.

Google-Extended는 Google 검색에 사이트가 포함될지 여부에 영향을 미치지 않으며 Google 검색에서 순위 결정 신호로 사용되지도 않습니다. |

## 사용자 에이전트의 Chrome/_W.X.Y.Z_ 관련 참고사항

목록에 있는 사용자 에이전트 문자열의 **Chrome/_W.X.Y.Z_** 문자열은 사용자 에이전트가 사용하는 Chrome 브라우저의 버전(예: `41.0.2272.96`)을 나타내는 플레이스홀더입니다. 이 버전 번호는 [Googlebot에 사용되는 최신 Chromium 출시 버전에 맞춰](https://developers.google.com/search/blog/2019/05/the-new-evergreen-googlebot?hl=ko) 시간이 지남에 따라 증가합니다.

이 패턴이 있는 사용자 에이전트를 대상으로 로그를 검색하거나 서버를 필터링하는 경우 정확한 버전 번호를 지정하기보다는 버전 번호에 와일드 카드를 사용하세요.