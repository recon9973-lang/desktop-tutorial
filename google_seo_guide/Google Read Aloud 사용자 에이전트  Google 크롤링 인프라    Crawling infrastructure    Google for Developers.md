[`Google-Read-Aloud`](https://developers.google.com/crawling/docs/crawlers-fetchers/google-user-triggered-fetchers?hl=ko#google-read-aloud)는 Google Read Aloud 서비스의 사용자 에이전트입니다. 이 서비스를 사용하면 텍스트 음성 변환(TTS)으로 웹페이지를 읽을 수 있습니다. 최종 사용자가 TTS 기능을 사용 설정한 후 페이지에 방문하면 서비스가 활성화됩니다. Read Aloud 서비스는 [Google Go](https://www.blog.google/technology/next-billion-users/make-google-read-it/?hl=ko), [Google Read it](https://developers.google.com/assistant/app/read-it?hl=ko), [Google 앱의 Read Aloud](https://support.google.com/websearch/answer/10078840?hl=ko) 및 기타 Google TTS 서비스에 사용됩니다.

## 크롤링 빈도 및 동작

Google Read Aloud는 사용자 요청에 따라 실행됩니다. Google Read Aloud는 페이지 결과를 캐싱하여 대역폭을 절약하지만 특정 페이지와 관련해 여러 요청이 발생할 수도 있습니다.

Google Read Aloud는 웹 크롤러가 아니며, 사용자 요청 시 활성화되고 링크를 따라가지 않습니다. Google Read Aloud는 스테이트리스(Stateless) 렌더링을 사용하여 사용자와 같은 방식으로 페이지를 확인합니다. 특히 사용자의 쿠키를 사용하지 않습니다. 사용자가 웹페이지 듣기를 요청하면 페이지를 최근에 가져왔는지에 따라 페이지에 접속하거나 접속하지 않을 수 있습니다.

## Google Read Aloud 요청 줄이기

Google Read Aloud는 자동 웹 크롤링의 결과가 아닌 사용자가 시작하므로 robots.txt 파일을 사용하여 선택 해제할 수 없습니다. Google Read Aloud 기능을 선택 해제하려면 `nopagereadaloud` `meta` 태그를 사용합니다.

```php-template
<meta name="google" content="nopagereadaloud">
```

페이지의 메타 태그를 인식하기 위해 Google Read Aloud는 삽입된 리소스를 사용하여 페이지에 사전 대응적으로 액세스하고 페이지를 렌더링할 수 있습니다. 페이지에서 메타 태그가 인식되면 향후 요청 수가 자동으로 줄어듭니다.

페이월 콘텐츠를 소리 내어 읽지 않도록 차단하려면 [구독 및 페이월 콘텐츠에 구조화된 데이터](https://developers.google.com/search/docs/appearance/structured-data/paywalled-content?hl=ko)를 사용합니다. `isAccessibleForFree` 속성이 `False`로 설정되어 있는지 확인합니다.

## `google-speakr` 에이전트란 무엇인가요?

`google-speakr` 에이전트는 지원 중단된 사용자 에이전트의 이전 버전입니다. 사용자 에이전트의 현재 이름은 `Google-Read-Aloud`입니다.