# 구조화된 Speakable(`Article`, `WebPage`) 데이터(베타)

이 기능은 베타 단계이므로 변경될 수 있습니다. 이 기능은 현재 개발 중이며 요구사항 또는 가이드라인이 변경될 수 있습니다.

`speakable` [schema.org](https://schema.org/) 속성은 TTS(텍스트 음성 변환)를 사용한 오디오 재생에 적합한 기사 또는 웹페이지의 섹션을 식별합니다. 마크업을 추가하면 검색엔진 및 기타 애플리케이션이 TTS를 사용하여 Google 어시스턴트 지원 기기에서 소리내어 읽을 수 있는 콘텐츠를 식별합니다. 구조화된 `speakable` 데이터가 있는 웹페이지는 Google 어시스턴트를 사용하여 새로운 채널을 통해 콘텐츠를 배포하고 더 넓은 사용자층에 도달할 수 있습니다.

Google 어시스턴트는 구조화된 `speakable` 데이터를 사용하여 스마트 스피커 기기에서 주제별 뉴스 쿼리에 응답합니다. 사용자가 특정 주제에 관한 뉴스를 요청하면 Google 어시스턴트가 웹에서 최대 3개의 기사를 표시하고 구조화된 `speakable` 데이터가 있는 기사의 섹션에 TTS를 사용하여 오디오 재생을 지원합니다. Google 어시스턴트가 `speakable` 섹션을 소리내어 읽으면 출처를 확인하고 Google 어시스턴트 앱을 통해 사용자의 휴대기기에 전체 기사 URL을 전송합니다.

## 예

다음은 JSON-LD 코드를 사용하는 구조화된 `speakable` 데이터와 xPath `content-locator` 값의 예입니다.

```php-template
<html>
  <head>
    <title>Speakable markup example</title>
    <meta name="description" content="This page is all about the quick brown fox" />
    <script type="application/ld+json">
    {
     "@context": "https://schema.org/",
     "@type": "WebPage",
     "name": "Quick Brown Fox",
     "speakable":
     {
      "@type": "SpeakableSpecification",
      "xPath": [
        "/html/head/title",
        "/html/head/meta[@name='description']/@content"
        ]
      },
     "url": "https://www.example.com/quick-brown-fox"
     }
    </script>
  </head>
  <body>
  </body>
</html>
```

## 사용 가능한 국가 및 언어

`speakable` 속성은 영어로 설정된 Google Home 기기가 있는 미국 사용자와 영어로 콘텐츠를 게시하는 게시자가 사용할 수 있습니다. 충분한 수의 게시자가 `speakable`을 구현하는 대로 다른 국가와 언어로도 출시할 계획입니다.

## 시작하기

주제별 뉴스 쿼리에 내 뉴스 콘텐츠가 표시되려면 다음 단계를 따르세요.

1.  [Google 가이드라인](https://developers.google.com/search/docs/appearance/structured-data/speakable?hl=ko/#guidelines) 준수 여부를 확인합니다.
2.  웹페이지에 [구조화된 `speakable` 데이터](https://developers.google.com/search/docs/appearance/structured-data/speakable?hl=ko/#structured-data-type-definitions)를 추가합니다.

## 가이드라인

`speakable` 콘텐츠를 뉴스 결과에 표시하려면 다음 가이드라인을 따라야 합니다.

-   [기술 가이드라인](https://developers.google.com/search/docs/appearance/structured-data/speakable?hl=ko/#technical-guidelines)
-   [콘텐츠 가이드라인](https://developers.google.com/search/docs/appearance/structured-data/speakable?hl=ko/#content-guidelines)
-   [검색 Essentials](https://developers.google.com/search/docs/essentials?hl=ko)
-   [구조화된 데이터 일반 가이드라인](https://developers.google.com/search/docs/appearance/structured-data/sd-policies?hl=ko)

### 기술 가이드라인

Google 어시스턴트를 위한 `speakable` 마크업을 구현할 때 다음 가이드라인을 따르세요.

-   날짜 기입선(기사가 보고된 위치), 사진 자막, 출처 속성과 같이 음성 전용과 음성 전달 상황에서 혼동될 수 있는 콘텐츠에는 구조화된 `speakable` 데이터를 추가하지 마세요.
-   전체 기사를 구조화된 `speakable` 데이터로 강조하기보다는 요점에만 집중하세요. 이렇게 하면 듣는 사람이 기사 내용을 파악할 수 있고 TTS에서 읽을 때 중요한 세부정보를 잘라내지 않을 수 있습니다.

### 콘텐츠 가이드라인

구조화된 `speakable` 데이터로 마크업하려는 콘텐츠를 작성할 때는 다음 가이드라인을 따르세요.

-   구조화된 `speakable` 데이터로 표시되는 콘텐츠에는 사용자에게 이해할 수 있고 유용한 정보를 제공하는 간결한 제목 또는 요약이 반드시 포함되어 있어야 합니다.
-   구조화된 `speakable` 데이터에 뉴스 상단을 포함하는 경우 TTS가 더욱 명확하게 읽을 수 있는 개별 문장으로 정보를 분리해 뉴스 상단을 다시 작성하는 것이 좋습니다.
-   최적의 오디오 사용자 환경을 위해 구조화된 `speakable` 데이터의 섹션당 콘텐츠 길이는 약 20~30초 또는 약 2~3문장으로 구성하는 것이 좋습니다.

## 구조화된 데이터 유형 정의

[Speakable](https://pending.schema.org/speakable)은 [`Article`](https://pending.schema.org/Article) 또는 [`Webpage`](https://pending.schema.org/WebPage) 객체에서 사용합니다. `speakable`의 전체 정의는 [schema.org/speakable](https://schema.org/speakable)에서 확인할 수 있습니다. 콘텐츠가 이 기능을 사용하려면 필수 속성이 있어야 합니다.

`speakable` 속성은 CSS 선택기 및 xPath의 두 가지 가능한 `content-locator` 값으로 임의의 횟수를 반복할 수 있습니다. 다음 속성 중 하나를 사용하세요.

| 필수 속성 | 필수 속성 |
|-------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `cssSelector` | `[Text](https://schema.org/Text)`

주석이 첨부된 페이지에서 콘텐츠를 처리합니다(예: 클래스 속성). 두 속성을 모두 사용하지 않고 `cssSelector` 또는 `xPath` 중 하나만 사용합니다. 예:

"speakable":
  {
  "@type": "SpeakableSpecification",
  "cssSelector": [
    ".headline",
    ".summary"
  ]
} |
| `xPath` | `[Text](https://schema.org/Text)`

xPath를 사용하는 콘텐츠를 처리합니다(콘텐츠의 XML 보기라고 가정). 두 속성을 모두 사용하지 않고 `cssSelector` 또는 `xPath` 중 하나만 사용합니다. 예:

"speakable":
  {
  "@type": "SpeakableSpecification",
  "xPath": [
    "/html/head/title",
    "/html/head/meta[@name='description']/@content"
  ]
} |

## 문제 해결

구조화된 데이터를 구현하거나 디버깅하는 데 문제가 있다면 다음 리소스를 참고하세요.

-   콘텐츠 관리 시스템(CMS)을 사용하거나 다른 사람이 내 사이트를 관리한다면 도움을 요청하세요. 문제를 자세히 설명하는 모든 Search Console 메시지를 CMS나 관리자에게 전달해야 합니다.
-   Google은 구조화된 데이터를 사용하는 기능이라고 해서 검색결과에 표시된다고 보장하지 않습니다. Google에서 콘텐츠를 리치 결과로 표시할 수 없는 일반적인 이유 목록은 [구조화된 데이터 일반 가이드라인](https://developers.google.com/search/docs/appearance/structured-data/sd-policies?hl=ko)을 참고하세요.
-   구조화된 데이터에 오류가 있을 수 있습니다. [구조화된 데이터 오류 목록](https://support.google.com/webmasters/answer/13300873?hl=ko) 및 [파싱할 수 없는 구조화된 데이터 보고서](https://support.google.com/webmasters/answer/9166415?hl=ko)를 확인하세요.
-   페이지에 구조화된 데이터 직접 조치를 취하는 경우 페이지에 있는 구조화된 데이터는 무시됩니다. 하지만 페이지는 계속 Google 검색결과에 표시될 수 있습니다. [구조화된 데이터 문제](https://support.google.com/webmasters/answer/9044175?hl=ko#zippy=,structured-data-issue)를 해결하려면 [직접 조치 보고서](https://support.google.com/webmasters/answer/9044175?hl=ko)를 사용하세요.
-   [가이드라인](https://developers.google.com/search/docs/appearance/structured-data/speakable?hl=ko/#guidelines)을 다시 검토하여 콘텐츠가 가이드라인을 준수하지 않는지 확인합니다. 스팸성 콘텐츠 또는 스팸성 마크업의 사용으로 인해 문제가 발생할 수 있습니다. 하지만 해당 문제가 구문 문제가 아닐 수도 있고, 이 경우 리치 결과 테스트에서는 이 문제를 식별할 수 없습니다.
-   [누락된 리치 결과/전체 리치 결과 수 감소 문제 해결](https://support.google.com/webmasters/answer/13300208?hl=ko)
-   다시 크롤링이 이루어지고 색인이 생성될 때까지 기다리세요. 페이지가 게시된 후 Google에서 페이지를 찾고 크롤링하기까지 며칠 정도 걸릴 수 있습니다. 크롤링 및 색인 생성에 관한 일반적인 질문은 [Google 검색 크롤링 및 색인 생성 FAQ](https://developers.google.com/search/help/crawling-index-faq?hl=ko)를 참고하세요.
-   [Google 검색 센터 포럼](https://support.google.com/webmasters/community?hl=ko)에 질문을 올려보세요.

### 콘텐츠를 트리거할 수 없음

_error_ **문제**: Google 어시스턴트에서 TTS 오디오를 사용하여 콘텐츠를 실행할 수 없습니다.

_done_ **문제 해결**

1.  다음 음성 명령을 사용해 보세요.
    -   "$topic에 관한 최신 뉴스는?"
    -   "$topic에 관한 최신 소식은?"
    -   "$topic에 관한 뉴스 재생해 줘."
2.  여전히 문제가 발생하는 경우 순위가 알고리즘 방식으로 결정되었기 때문일 수 있습니다. Google 어시스턴트는 TTS 오디오 재생을 통해 다른 뉴스 게시자로부터 최대 3개의 기사를 제공합니다. Google의 기사 순위 작성 방식에 관해 자세히 알아보려면 [검색 원리](https://www.google.com/search/howsearchworks/?hl=ko)를 참고하세요.

## 추가 오디오 솔루션

구조화된 `speakable` 데이터 외에 맞춤 애플리케이션용 고급 Google 어시스턴트 통합과 같은 기타 Google 어시스턴트 오디오 솔루션을 뉴스 콘텐츠에 사용할 수 있습니다. 예를 들어 사용자가 Google 어시스턴트를 통해 앱과 소통할 수 있도록 할 수 있습니다. 자세히 알아보려면 [Actions on Google 개발자 가이드](https://developers.google.com/actions?hl=ko)를 참조하세요.