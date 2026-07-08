Google은 [30년 이상](https://groups.google.com/g/comp.lang.java/c/aSPAJO05LIU/m/ushhUIQQ-ogJ?hl=ko) 공개 웹을 크롤링해 왔으며 Google의 웹 크롤러가 작동하는 방식에 관한 질문을 정기적으로 받습니다. 이러한 질문에 답변하기 위해 Google 크롤러와 크롤러가 전 세계의 정보를 정리하고 사용자를 웹 전반의 콘텐츠에 연결하는 방법을 설명하는 몇 가지 사실을 소개합니다.

## 크롤링이란 무엇인가요? 간단히 말해 크롤링은 Google이 웹을 '보는' 방식입니다.

크롤링은 자동화된 소프트웨어를 사용하여 새 웹페이지를 발견하고 이를 이해하는 프로세스입니다. 이렇게 하면 Google에서 웹페이지를 찾을 때 해당 페이지가 존재한다는 것을 알 수 있으며 검색 결과에 포함할 수 있습니다. 모든 검색엔진은 크롤링을 통해 어떤 페이지와 정보가 있는지 파악합니다. [Google 검색에서 페이지를 크롤링하는 방법](https://www.youtube.com/watch?v=JuK7NnfyEuc&t=49s&hl=ko)에 관한 동영상을 시청하여 자세히 알아보세요.

## Google에는 많은 크롤러가 있으며 각 크롤러는 중요한 작업을 수행합니다.

Googlebot은 가장 잘 알려진 크롤러로, Google 검색의 결과를 최신 상태로 유지하는 데 사용됩니다. Google 이미지 및 Google 쇼핑과 같은 다른 플랫폼에 특화된 크롤러도 있습니다. Google은 가장 흔히 사용되는 크롤러와 그 용도에 관한 [전체 문서](https://developers.google.com/crawling?hl=ko)를 제공합니다. Google 크롤러는 쉽게 식별할 수 있는 사용자 에이전트 이름과 알려진 인터넷 주소를 사용합니다. 이렇게 하면 사이트 소유자는 표시되는 Google 크롤러가 합법적이라고 확신할 수 있습니다.

## Google은 최신 업데이트를 확인하고 최신 검색 결과를 제공하기 위해 반복 크롤링을 실행합니다.

속보 기사를 포착하기 위해 Google은 몇 분마다 뉴스 홈페이지를 다시 크롤링할 수 있습니다. 다른 경우에는 수년 동안 변경된 사항이 없었을 수 있으므로 한 달 동안 기다렸다가 다시 크롤링할 수 있습니다. 사이트 소유자는 새 페이지와 업데이트된 페이지에 관한 정보를 제공하는 [사이트맵](https://developers.google.com/search/docs/crawling-indexing/sitemaps/build-sitemap?hl=ko) 파일을 사용하여 재크롤링 빈도에 영향을 줄 수 있습니다.

## 크롤링이 자주 이루어지는 것은 좋은 신호입니다.

Google에서 사이트를 자주 크롤링하는 것은 페이지에 사람들이 찾고 싶어 하는 최신 또는 관련성이 높은 콘텐츠가 있으며 Google 시스템에서 이러한 수요를 인식하고 있다는 것을 나타냅니다. 온라인 쇼핑이 좋은 예입니다. Google은 검색 결과에 소매업체의 최신 가격, 프로모션, 재고 상태가 표시되도록 전자상거래 사이트를 자주 크롤링합니다.

## 페이지가 점점 복잡해짐에 따라 Google의 크롤링도 시간이 지날수록 증가했습니다.

Google이 자주 재크롤링하는 또 다른 이유는 웹페이지의 풍부함과 웹페이지에서 제공하는 내용을 완전히 파악하기 위해서입니다. Google 크롤러는 렌더링이라는 기법을 사용하여 실제 사용자가 보는 것처럼 페이지를 '보기' 위해 사이트를 완전히 로드합니다. 수년에 걸쳐 웹페이지가 더욱 정교해졌습니다. [모바일 페이지의 중앙값](https://almanac.httparchive.org/en/2024/page-weight#requests-volume) 크기가 816KB에서 [2.3MB](https://almanac.httparchive.org/en/2024/page-weight#request-bytes)로 커졌으며, 이제 이미지부터 대화형 구성요소까지 [60개가 넘는 다양한 파일](https://almanac.httparchive.org/en/2024/page-weight#requests-volume)을 로드해야 합니다. 따라서 웹페이지의 전체 모습을 대표하는 스냅샷을 얻으려면 동일한 페이지를 여러 번 크롤링해야 할 수도 있습니다. 새 요소가 계속 추가되므로 그 이상으로 크롤링해야 할 수도 있습니다.

## 크롤링은 자동으로 최적화됩니다.

Google 크롤러는 효율성을 위해 설계되었으며 사이트 소유자에게 미치는 영향을 최소화하도록 조정됩니다. 예를 들어 사이트 속도가 느려지거나 오류가 반환되면 사이트 서버의 오버로드를 방지하기 위해 [크롤링 속도가 자동으로 변경](https://developers.google.com/search/docs/crawling-indexing/large-site-managing-crawl-budget?hl=ko)됩니다. 크롤링된 콘텐츠를 캐싱하여 불필요한 크롤링을 제한합니다. 또한 Google 크롤러가 웹사이트를 더 많이 발견할수록 크롤링을 덜 해도 되는 섹션을 인식할 수 있습니다. 예를 들어 9999년까지 표시되는 캘린더는 전체를 크롤링하지 않아도 됩니다. 사이트 소유자는 크롤링할 필요가 없는 콘텐츠를 [식별하여 도움을 줄 수 있습니다](https://developers.google.com/search/docs/crawling-indexing/robots/intro?hl=ko). 이렇게 하면 인프라 비용이 절감되어 웹사이트 비용이 절약되고 인터넷 전체의 효율성이 높아집니다.

## Google 크롤러는 허가 없이 페이월 또는 구독 콘텐츠로 이동하지 않습니다.

기본적으로 페이지가 공개 웹에서 액세스할 수 없는 경우(예: 콘텐츠가 로그인 페이지 뒤에 있는 경우) Google 크롤러도 액세스할 수 없습니다. Google이 구독 페이지에 액세스할 수 있는 명시적 권한을 부여하려는 경우 (예: Google이 사용자를 해당 콘텐츠로 안내할 수 있도록) [사이트 소유자를 위한 구체적인 안내](https://developers.google.com/search/docs/appearance/flexible-sampling?hl=ko)가 있습니다. 크롤러에 구독 액세스를 제공하는 경우 [구조화된 데이터](https://developers.google.com/search/docs/appearance/flexible-sampling?hl=ko#how-to-indicate-paywalled-content)를 사용하여 [스팸 관련 규칙](https://developers.google.com/search/docs/essentials/spam-policies?hl=ko)을 트리거하지 않고 실제 방문자에게 로그인 화면을 계속 표시할 수 있습니다. [미리보기 컨트롤](https://developers.google.com/search/docs/appearance/snippet?hl=ko#nosnippet)을 활용하여 구독 콘텐츠가 페이지 미리보기에 표시되지 않도록 할 수도 있습니다.

## 사이트 소유자는 크롤링되는 콘텐츠와 크롤링 방식을 제어할 수 있습니다.

Google은 사이트 소유자가 Google과 같은 크롤러가 페이지와 상호작용하는 방식을 선언할 수 있는 간단한 텍스트 파일인 [robots.txt](https://developers.google.com/search/docs/crawling-indexing/robots/intro?hl=ko)와 같은 개방형 웹 표준을 준수합니다. robots.txt는 [robots 메타 태그](https://developers.google.com/search/docs/crawling-indexing/robots-meta-tag?hl=ko)와 함께 웹사이트가 콘텐츠에 액세스하는 방법을 Google 및 기타 서비스에 쉽게 전달할 수 있도록 지원합니다. Google 검색에 페이지가 표시되지 않도록 차단할 수 있습니다. [사이트맵](https://developers.google.com/search/docs/crawling-indexing/sitemaps/build-sitemap?hl=ko)을 사용하여 크롤링할 새 콘텐츠를 Google에 알릴 수 있습니다. 또한 [크롤링 예산](https://developers.google.com/crawling/docs/crawl-budget?hl=ko)을 통해 Google에서 사이트를 크롤링하는 빈도를 관리할 수 있습니다.

## Google의 [표준 크롤러](https://developers.google.com/crawling/docs/crawlers-fetchers/google-common-crawlers?hl=ko)는 콘텐츠에 액세스하고 사용하는 방법에 관한 웹사이트의 선택을 항상 존중합니다.

크롤링 후 Google은 크롤링된 데이터를 여러 번 사용하여 사이트에서 불필요한 반복 요청을 줄일 수 있습니다. 이 데이터를 재사용하는 경우에도 Google은 robots.txt를 통해 사이트에서 선택한 사항과 이 개방형 웹 프로토콜을 통해 제공되는 컨트롤을 계속 존중합니다. 예를 들어 사이트에서는 robots.txt에서 [Google-Extended](https://developers.google.com/crawling/docs/crawlers-fetchers/google-common-crawlers?hl=ko#google-extended)를 사용하여 콘텐츠가 Gemini 모델의 향후 버전을 학습하는 데 도움이 되는지 등을 관리할 수 있습니다. Google-Extended를 활용해도 Google 검색에 사이트가 포함되는 데 영향을 미치지 않으며 Google-Extended는 Google 검색에서 순위 결정 신호로 사용되지도 않습니다.

Google에서는 사이트 소유자가 Google 크롤링 환경을 관리할 수 있도록 다양한 도구를 제공합니다. 그중 하나가 사이트 소유자에게 무료로 제공되는 [Google Search Console](https://search.google.com/search-console/about?hl=ko)입니다. [크롤링한 양과 이유](https://support.google.com/webmasters/answer/9679690?hl=ko)에 관한 정보를 제공합니다. 또한 사이트에서 서버 다운타임이나 속도 문제와 같은 문제를 진단하는 데도 도움이 됩니다. 또한 Search Console에서는 사이트 페이지가 Google 검색에 표시되는 방식과 사용자가 페이지와 상호작용하는 방식에 관한 포괄적인 정보를 제공합니다.

Google 크롤러는 사용자를 최고의 웹으로 연결해 주며, Google은 항상 크롤러의 성능과 효율성을 높이기 위한 방법을 모색하고 있습니다.