Feedfetcher는 Google에서 [Google 뉴스](https://play.google.com/store/apps/details?id=com.google.android.apps.magazines&hl=ko) 및 [WebSub](https://en.wikipedia.org/wiki/WebSub)의 RSS 또는 Atom 피드를 크롤링하는 방식입니다. Feedfetcher는 앱 또는 서비스의 사용자가 요청한 피드를 저장하고 정기적으로 새로고침합니다. Google 검색에서는 팟캐스트 피드만 색인이 생성됩니다. 하지만 피드가 [Atom](https://www.rfc-editor.org/rfc/rfc4287.txt) 또는 [RSS](https://cyber.harvard.edu/rss/rss.html) 사양을 준수하지 않아도 색인이 생성될 수 있습니다. 다음은 사용자가 제어하는 이 피드 수집기의 작동 방식에 관해 자주 묻는 질문에 대한 답변입니다.

## Google에서 내 사이트 피드의 일부나 전체를 검색하지 못하도록 요청하려면 어떻게 해야 하나요?

사용자가 Feedfetcher 데이터를 사용하는 서비스나 앱을 추가하면 Google의 Feedfetcher가 피드의 콘텐츠를 가져와서 표시합니다. Feedfetcher 요청은 자동화된 크롤러가 아닌 실제 사용자의 명시적 작업으로 실행되기 때문에 Feedfetcher는 robots.txt 규칙을 무시합니다.

공개적으로 사용할 수 있는 피드인 경우 Google에서는 사용자가 이 피드에 액세스하는 것을 제한할 수 없습니다. 이를 해결하는 한 가지 방법은 `Feedfetcher-Google` 사용자 에이전트를 대상으로 `404`, `410` 또는 기타 오류 상태 메시지를 게재하도록 사이트를 구성하는 것입니다.

블로그나 사이트 호스팅 서비스로 피드를 제공한다면 해당 서비스에 직접 문의하여 피드 액세스 권한을 제한하세요.

## Feedfetcher는 얼마나 자주 내 피드를 검색하나요?

Feedfetcher는 대부분의 사이트에서 평균 1시간에 두 번 이상 피드를 검색하지 않습니다. 자주 업데이트되는 일부 사이트의 경우 더 자주 새로고침되기도 합니다. 하지만 네트워크 지연으로 인해 잠시 Feedfetcher가 피드를 더 자주 검색하는 것으로 보일 수도 있습니다.

## Feedfetcher가 내 서버 또는 존재하지 않는 도메인에서 잘못된 링크를 다운로드하는 이유는 무엇인가요?

Feedfetcher는 사용자가 설치한 서비스나 앱의 요청이 있을 때 피드를 검색합니다. 사용자가 존재하지 않는 피드 URL을 요청했을 수 있습니다.

## Feedfetcher가 내 '비밀' 웹 서버에서 정보를 다운로드하는 이유는 무엇인가요?

Feedfetcher는 사용자가 설치한 서비스나 앱의 요청이 있을 때 피드를 검색합니다. '비밀' 서버에 관해 알고 있는 사용자가 요청했거나 실수로 잘못 입력했을 수 있습니다.

## 왜 Feedfetcher가 내 robots.txt 파일을 따르지 않나요?

Feedfetcher는 사용자가 피드에서 데이터를 요청하는 서비스나 앱을 명시적으로 시작한 후에만 피드를 검색합니다. Feedfetcher는 로봇이 아니라 실제 사용자의 직접 에이전트로서 작동하므로 robots.txt 항목을 무시합니다. Feedfetcher는 여러 사용자의 에이전트 역할을 하므로 앱이나 서비스를 통해 피드를 요청한 모든 사용자의 공통 피드를 한 번만 요청함으로써 대역폭을 절약합니다. 공통 피드는 [RSS](https://en.wikipedia.org/wiki/RSS) 및 [Atom](https://en.wikipedia.org/wiki/Atom_(Web_standard))입니다.

`404`, `410` 또는 다른 오류 상태 메시지를 `Feedfetcher-Google` 사용자 에이전트에 게재하도록 서버를 구성하여 Feedfetcher가 사이트를 크롤링하지 못하게 할 수 있습니다.

## 모두 사용자 에이전트 Feedfetcher가 있는 Google.com의 여러 컴퓨터에서 사이트를 방문하는 이유는 무엇인가요?

Feedfetcher는 웹이 확대됨에 따라 성능과 규모를 개선하기 위해 여러 컴퓨터에 분산되도록 설계되었습니다. 대역폭 사용량을 줄이기 위해 사용된 컴퓨터가 네트워크에서 검색 중인 사이트의 근처에 위치하는 경우가 많습니다.

## 내 로그를 필터링할 수 있도록 Feedfetcher가 요청을 실행하는 IP 주소를 알려 줄 수 있나요?

Feedfetcher에서 사용하는 IP 주소는 [user-triggered-fetchers-google.json](https://developers.google.com/static/crawling/ipranges/user-triggered-fetchers-google.json?hl=ko) 객체에 포함됩니다.

## Feedfetcher가 내 사이트에서 같은 페이지를 여러 번 다운로드하는 이유는 무엇인가요?

일반적으로 Feedfetcher는 지정된 피드를 검색하는 동안 사이트에서 각 파일의 복사본을 하나만 다운로드합니다. 하지만 아주 드물게 컴퓨터가 중단되었다가 다시 시작되는 경우 최근에 방문한 페이지를 다시 검색할 수 있습니다.

## Feedfetcher가 크롤링하는 링크 종류는 무엇인가요?

일반 웹 크롤러와는 달리 Feedfetcher는 크롤링할 링크를 전혀 검색하지 않습니다. 대신 Feedfetcher를 사용하는 서비스나 앱의 사용자가 제공한 단일 URL을 크롤링합니다.

## 내 Feedfetcher 질문에 대한 대답이 여기에 없습니다. 어디에서 도움을 받을 수 있나요?

여전히 문제가 해결되지 않는다면 Google 검색 센터 [포럼](https://support.google.com/webmasters/community?hl=ko)에 질문을 올려 보세요.