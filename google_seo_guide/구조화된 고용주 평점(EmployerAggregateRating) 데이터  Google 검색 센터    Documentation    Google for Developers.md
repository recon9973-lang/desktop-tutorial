사이트에서 채용 조직에 관한 사용자 생성 평점을 게시한다면 구조화된 `EmployerAggregateRating` 데이터를 사이트에 추가합니다. `EmployerAggregateRating`은 여러 사용자로부터 수집한 채용 조직 평가입니다. `EmployerAggregateRating`을 추가하면 채용 조직 평점을 제공하여 구직자가 일자리를 선택하는 데 도움을 줄 수 있습니다. 또한 Google의 채용정보 인리치드 검색 환경에서 눈에 띄는 브랜드 게재위치를 확보할 수 있습니다.

![검색결과에 표시된 고용주 평점의 예](https://developers.google.com/static/search/docs/images/employer-aggregate-rating01.png?hl=ko)

## 예

다음은 JSON-LD 코드를 사용하는 `EmployerAggregateRating`의 예입니다.

```php-template
<html>
  <head>
    <title>World's Best Coffee Shop</title>
    <script type="application/ld+json">
    {
      "@context" : "https://schema.org/",
      "@type": "EmployerAggregateRating",
      "itemReviewed": {
        "@type": "Organization",
        "name" : "World's Best Coffee Shop",
        "sameAs" : "https://example.com"
      },
      "ratingValue": 91,
      "bestRating": 100,
      "worstRating": 1,
      "ratingCount" : "10561"
    }
    </script>
  </head>
  <body>
  </body>
</html>
```

## 구조화된 데이터를 추가하는 방법

구조화된 데이터는 페이지 정보를 제공하고 페이지 콘텐츠를 분류하기 위한 표준화된 형식입니다. 구조화된 데이터를 처음 사용한다면 [구조화된 데이터의 작동 방식](https://developers.google.com/search/docs/appearance/structured-data/intro-structured-data?hl=ko)을 자세히 알아보세요.

다음은 구조화된 데이터를 빌드, 테스트 및 출시하는 방법의 개요입니다.

1.  [필수 속성](https://developers.google.com/search/docs/appearance/structured-data/employer-rating?hl=ko#structured-data-type-definitions)을 추가합니다. 사용 중인 형식에 따라 [페이지에 구조화된 데이터를 삽입](https://developers.google.com/search/docs/appearance/structured-data/intro-structured-data?hl=ko#format-placement)하는 위치를 알아보세요.
2.  [가이드라인](https://developers.google.com/search/docs/appearance/structured-data/employer-rating?hl=ko#guidelines)을 따릅니다.
3.  [리치 결과 테스트](https://search.google.com/test/rich-results?hl=ko)를 사용하여 코드의 유효성을 검사하고 심각한 오류를 해결하세요. 또한 도구에서 신고될 수 있는 심각하지 않은 문제는 구조화된 데이터의 품질을 개선하는 데 도움이 될 수 있으므로 해결하는 것이 좋습니다. 그러나 리치 결과를 사용하기 위한 필수사항은 아닙니다.
4.  구조화된 데이터를 포함하는 일부 페이지를 배포하고 [URL 검사 도구](https://support.google.com/webmasters/answer/9012289?hl=ko)를 사용하여 Google에서 페이지를 표시하는 방법을 테스트합니다. Google이 페이지에 액세스할 수 있으며 robots.txt 파일, `noindex` 태그 또는 로그인 요구사항에 의해 차단되지 않는지 확인합니다. 페이지가 정상적으로 표시되면 [Google에 URL을 재크롤링하도록 요청](https://developers.google.com/search/docs/crawling-indexing/ask-google-to-recrawl?hl=ko)할 수 있습니다.
5.  Google에 향후 변경사항을 계속 알리려면 [사이트맵을 제출](https://developers.google.com/search/docs/crawling-indexing/sitemaps/build-sitemap?hl=ko)하는 것이 좋습니다. 이는 [Search Console Sitemap API](https://developers.google.com/webmaster-tools/v1/sitemaps?hl=ko)를 사용하여 자동화할 수 있습니다.

## 가이드라인

Google 채용정보 검색 환경에 표시되려면 다음 가이드라인을 준수해야 합니다.

-   [기술 가이드라인](https://developers.google.com/search/docs/appearance/structured-data/employer-rating?hl=ko#technical-guidelines)
-   [콘텐츠 가이드라인](https://developers.google.com/search/docs/appearance/structured-data/employer-rating?hl=ko#content-guidelines)
-   [인리치드 검색 품질 가이드라인](https://developers.google.com/search/docs/appearance/enriched-search-results?hl=ko)
-   [검색 Essentials](https://developers.google.com/search/docs/essentials?hl=ko)
-   [구조화된 데이터 일반 가이드라인](https://developers.google.com/search/docs/appearance/structured-data/sd-policies?hl=ko)

### 기술 가이드라인

-   구조화된 `EmployerAggregateRating` 데이터를 추가한 페이지에서 사용자가 평점을 확인할 수 있어야 합니다. 페이지에 평점 콘텐츠가 있다는 것을 사용자가 바로 알 수 있어야 합니다.
-   카테고리나 항목 목록이 아닌 특정 채용 조직의 평점 정보를 제공합니다. 예를 들어 '일하기 좋은 직장 10위'나 '기술 기업'은 특정 채용 조직을 나타내지 않습니다.
-   Google은 기본적으로 사이트에서 5점 척도(5점이 최고, 1점이 최저)를 사용한다고 가정하지만, 다른 척도도 얼마든지 사용할 수 있습니다. 다른 척도를 사용하는 경우 최고 및 최저 평점을 지정할 수 있으며 Google에서 이 점수를 별 5개를 사용하는 체계로 변환합니다.

### 콘텐츠 가이드라인

-   사용자는 사이트에서 자신의 평점을 게시할 수 있어야 하고, 사이트는 이러한 사용자 평점을 호스팅해야 합니다.
-   평점 수는 사용자가 제공하는 실제 평점을 반영해야 합니다.
-   집계 점수는 제공된 평점을 바탕으로 정확히 계산되어야 합니다.

## 구조화된 데이터 유형 정의

이 섹션에서는 고용주 누계 평점과 관련된 구조화된 데이터 유형을 알아봅니다. 개선된 검색결과에 콘텐츠를 표시하려면 필수 속성이 있어야 합니다.

### `EmployerAggregateRating`

`EmployerAggregateRating`의 전체 정의는 [schema.org/EmployerAggregateRating](https://schema.org/EmployerAggregateRating)에서 확인하세요.

Google에서 지원하는 속성은 다음과 같습니다.

| 필수 속성 | 필수 속성 |
|--------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `itemReviewed` | `[Organization](https://schema.org/Organization)`

평가되는 조직입니다. `itemReviewed` 속성이 평가 대상 회사를 나타내는 [schema.org/Organization](https://schema.org/Organization)으로 연결되어야 합니다. 예:

{
  "@context" : "https://schema.org/",
  "@type": "EmployerAggregateRating",
  "itemReviewed": {
    "@type": "Organization",
    "name" : "World's Best Coffee Shop",
    "sameAs" : "https://www.worlds-best-coffee-shop.example.com"
  }
} |
| `ratingCount` | `[Number](https://schema.org/Number)`

사이트에 등록된 조직의 총 평점 수입니다. `ratingCount` 또는 `reviewCount` 중 하나가 필요합니다. |
| `ratingValue` | `[Number](https://schema.org/Number)` 또는 `[Text](https://schema.org/Text)`

항목의 품질 평점을 숫자, 백분율, 분수로 나타낸 숫자 값입니다(예: '4', '60%' 또는 '6/10'). 분수 자체나 백분율에 척도가 내포되어 있기에 Google에서는 분수와 백분율의 척도를 파악하고 있습니다. 숫자 값의 기본 척도는 5점이며, 1이 가장 낮은 값이고 5가 가장 높은 값입니다. 다른 척도를 사용하려면 `bestRating`과 `worstRating`을 사용하세요. |
| `reviewCount` | `[Number](https://schema.org/Number)`

평점과 함께 또는 평점 없이 리뷰를 남긴 사용자 수를 지정합니다. `ratingCount` 또는 `reviewCount` 중 하나가 필요합니다. |

| 권장 속성 | 권장 속성 |
|-------------|---------------------------------------------------------------------|
| `bestRating` | `[Number](https://schema.org/Number)`

이 평가 시스템에서 허용되는 가장 높은 값입니다. `bestRating`이 생략된 경우 5점으로 간주됩니다. |
| `worstRating` | `[Number](https://schema.org/Number)`

이 평가 시스템에서 허용되는 가장 낮은 값입니다. `worstRating`이 생략된 경우 1점으로 간주됩니다. |

## 문제 해결

구조화된 데이터를 구현하거나 디버깅하는 데 문제가 있다면 다음 리소스를 참고하세요.

-   콘텐츠 관리 시스템(CMS)을 사용하거나 다른 사람이 내 사이트를 관리한다면 도움을 요청하세요. 문제를 자세히 설명하는 모든 Search Console 메시지를 CMS나 관리자에게 전달해야 합니다.
-   Google은 구조화된 데이터를 사용하는 기능이라고 해서 검색결과에 표시된다고 보장하지 않습니다. Google에서 콘텐츠를 리치 결과로 표시할 수 없는 일반적인 이유 목록은 [구조화된 데이터 일반 가이드라인](https://developers.google.com/search/docs/appearance/structured-data/sd-policies?hl=ko)을 참고하세요.
-   구조화된 데이터에 오류가 있을 수 있습니다. [구조화된 데이터 오류 목록](https://support.google.com/webmasters/answer/13300873?hl=ko) 및 [파싱할 수 없는 구조화된 데이터 보고서](https://support.google.com/webmasters/answer/9166415?hl=ko)를 확인하세요.
-   페이지에 구조화된 데이터 직접 조치를 취하는 경우 페이지에 있는 구조화된 데이터는 무시됩니다. 하지만 페이지는 계속 Google 검색결과에 표시될 수 있습니다. [구조화된 데이터 문제](https://support.google.com/webmasters/answer/9044175?hl=ko#zippy=,structured-data-issue)를 해결하려면 [직접 조치 보고서](https://support.google.com/webmasters/answer/9044175?hl=ko)를 사용하세요.
-   [가이드라인](https://developers.google.com/search/docs/appearance/structured-data/employer-rating?hl=ko#guidelines)을 다시 검토하여 콘텐츠가 가이드라인을 준수하지 않는지 확인합니다. 스팸성 콘텐츠 또는 스팸성 마크업의 사용으로 인해 문제가 발생할 수 있습니다. 하지만 해당 문제가 구문 문제가 아닐 수도 있고, 이 경우 리치 결과 테스트에서는 이 문제를 식별할 수 없습니다.
-   [누락된 리치 결과/전체 리치 결과 수 감소 문제 해결](https://support.google.com/webmasters/answer/13300208?hl=ko)
-   다시 크롤링이 이루어지고 색인이 생성될 때까지 기다리세요. 페이지가 게시된 후 Google에서 페이지를 찾고 크롤링하기까지 며칠 정도 걸릴 수 있습니다. 크롤링 및 색인 생성에 관한 일반적인 질문은 [Google 검색 크롤링 및 색인 생성 FAQ](https://developers.google.com/search/help/crawling-index-faq?hl=ko)를 참고하세요.
-   [Google 검색 센터 포럼](https://support.google.com/webmasters/community?hl=ko)에 질문을 올려보세요.