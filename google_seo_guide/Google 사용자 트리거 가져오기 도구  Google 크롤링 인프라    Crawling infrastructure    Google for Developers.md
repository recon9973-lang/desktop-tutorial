# Google 사용자 트리거 가져오기 도구 목록

사용자 트리거 가져오기 도구는 사용자가 Google 제품 내에서 가져오기 기능을 수행하기 위해 사용자에 의해 시작됩니다. 예를 들어 [Google 사이트 인증 도구](https://support.google.com/webmasters/answer/9008080?hl=ko)는 사용자의 요청에 따라 작동하거나 Google Cloud(GCP)에서 호스팅되는 사이트에는 사이트 사용자가 외부 RSS 피드를 가져오도록 허용하는 기능이 있습니다. 사용자가 가져오기를 요청했기 때문에 이러한 가져오기 도구에서는 보통 robots.txt 규칙을 무시합니다. Google 크롤러의 일반 [기술 속성](https://developers.google.com/crawling/docs/crawlers-fetchers/overview-google-crawlers?hl=ko#crawl-technical-props)은 사용자 트리거 가져오기 도구에도 적용됩니다.

사용자 트리거 가져오기 도구에서 사용하는 IP 범위는 [user-triggered-fetchers.json](https://developers.google.com/static/crawling/ipranges/user-triggered-fetchers.json?hl=ko), [user-triggered-fetchers-google.json](https://developers.google.com/static/crawling/ipranges/user-triggered-fetchers-google.json?hl=ko), [user-triggered-agents.json](https://developers.google.com/static/crawling/ipranges/user-triggered-agents.json?hl=ko) 객체에 게시됩니다. 사용자 트리거 가져오기 도구의 역방향 DNS 마스크는 가져오기 도구가 Google 소유인지 사용자 소유인지에 따라 각각 `***-***-***-***.gae.googleusercontent.com` 또는 `google-proxy-***-***-***-***.google.com`과 일치합니다.

다음 목록은 사용자 트리거 가져오기 도구, HTTP 요청에 표시되는 사용자 에이전트 문자열, 연결된 제품을 보여줍니다. 이 목록은 일부일 뿐 전부 포함하지는 않습니다. 로그 파일에 나타날 가능성이 더 높으며 Google에 관련 문의가 접수되는 요청자만 다룹니다.

## Chrome 웹 스토어

| **HTTP 요청의 사용자 에이전트** | Mozilla/5.0 (compatible; Google-CWS) |
|-------------------|-------------------------------------------------------------------------|
| **연결된 제품** | Chrome 웹 스토어 가져오기 도구는 개발자가 Chrome 확장 프로그램 및 테마의 메타데이터에 제공하는 URL을 요청합니다. |

## [Feedfetcher](https://developers.google.com/crawling/docs/crawlers-fetchers/feedfetcher?hl=ko)

| **HTTP 요청의 사용자 에이전트** | FeedFetcher-Google; (+http://www.google.com/feedfetcher.html) |
|-------------------|----------------------------------------------------------------|
| **연결된 제품** | Feedfetcher는 Google 뉴스, WebSub에 RSS 또는 Atom 피드를 크롤링하는 데 사용됩니다. |

## Google-Agent

| **HTTP 요청의 사용자 에이전트** | 모바일 에이전트

Mozilla/5.0 (Linux; Android 6.0.1; Nexus 5X Build/MMB29P) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/W.X.Y.Z Mobile Safari/537.36 (compatible; Google-Agent; +https://developers.google.com/crawling/docs/crawlers-fetchers/google-agent)

데스크톱 에이전트

Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko; compatible; Google-Agent; +https://developers.google.com/crawling/docs/crawlers-fetchers/google-agent) Chrome/W.X.Y.Z Safari/537.36 |
|-------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **연결된 제품** | Google-Agent는 Google 인프라에서 호스팅되는 에이전트가 웹을 탐색하고 사용자 요청에 따라 작업을 실행하는 데 사용됩니다(예: [Project Mariner](https://deepmind.google/models/project-mariner/?hl=ko)). [user-triggered-agents.json](https://developers.google.com/static/crawling/ipranges/user-triggered-agents.json?hl=ko)의 IP 범위를 사용합니다. |

## Google 메시지

| **HTTP 요청의 사용자 에이전트** | GoogleMessages |
|-------------------|--------------------------------------------------------------|
| **연결된 제품** | Google 메시지 가져오기 도구는 채팅 메시지에서 전송된 URL의 링크 미리보기를 생성하는 데 사용됩니다. |

## Google NotebookLM

| **HTTP 요청의 사용자 에이전트** | Google-NotebookLM |
|-------------------|-------------------------------------------------------------------------|
| **연결된 제품** | `Google-NotebookLM` 가져오기 도구는 [NotebookLM](https://notebooklm.google/?hl=ko) 사용자가 프로젝트의 소스로 제공한 개별 URL을 요청합니다. |

## Google Pinpoint

| **HTTP 요청의 사용자 에이전트** | Google-Pinpoint |
|-------------------|--------------------------------------------------------------------------|
| **연결된 제품** | `Google-Pinpoint` 가져오기 도구는 [Pinpoint](https://support.google.com/pinpoint/answer/11948320?hl=ko) 사용자가 개인 문서 컬렉션의 소스로 지정한 개별 URL을 요청합니다. |

## Google 게시자 센터

| **HTTP 요청의 사용자 에이전트** | GoogleProducer; (+https://developers.google.com/search/docs/crawling-indexing/google-producer) |
|-------------------|------------------------------------------------------------------------------------------------|
| **연결된 제품** | Google 게시자 센터에서는 Google 뉴스 방문 페이지에서 사용하기 위해 [게시자가 명시적으로 제공한 피드](https://support.google.com/news/publisher-center/answer/9545414?hl=ko)를 가져와 처리합니다. |

## [Google Read Aloud](https://developers.google.com/crawling/docs/crawlers-fetchers/read-aloud-user-agent?hl=ko)

| **HTTP 요청의 사용자 에이전트** | 모바일 에이전트

Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Mobile Safari/537.36 (compatible; Google-Read-Aloud; +https://support.google.com/webmasters/answer/1061943)

데스크톱 에이전트

Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36 (compatible; Google-Read-Aloud; +https://support.google.com/webmasters/answer/1061943)

이전 에이전트(지원 중단됨)

`google-speakr` |
|-------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **연결된 제품** | 사용자 요청에 따라 Google Read Aloud에서는 [텍스트 음성 변환(TTS)을 통해 웹페이지를 가져와 읽습니다](https://developers.google.com/crawling/docs/crawlers-fetchers/read-aloud-user-agent?hl=ko). |

## [Google 사이트 인증 도구](https://support.google.com/webmasters/answer/9008080?hl=ko)

| **HTTP 요청의 사용자 에이전트** | Mozilla/5.0 (compatible; Google-Site-Verification/1.0) |
|-------------------|--------------------------------------------------------|
| **연결된 제품** | Google 사이트 인증 도구는 Search Console 확인 토큰을 가져옵니다. |