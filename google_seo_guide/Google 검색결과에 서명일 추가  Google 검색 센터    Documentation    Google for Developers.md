-   [홈](https://developers.google.com/?hl=ko)
-   [Search Central](https://developers.google.com/search?hl=ko)
-   [Documentation](https://developers.google.com/search/docs?hl=ko)

도움이 되었나요?

의견 보내기

-   이 페이지의 내용
-   [Google에 날짜 정보를 제공하는 방법](https://developers.google.com/search/docs/appearance/publication-dates?hl=ko/#how-to-provide-date-information-to-google)
-   [서명일에 영향을 주기 위한 권장사항](https://developers.google.com/search/docs/appearance/publication-dates?hl=ko/#guidelines)

# Google 검색에서 서명일에 영향 주기

_서명일_은 Google에서 웹페이지를 업데이트하거나 게시한 것으로 추정하는 날짜입니다. Google에서 페이지나 동영상의 서명일을 확인할 수 있고 이 정보가 사용자에게 유용한 것으로 간주되는 경우 검색결과에 이 정보를 노출할 수 있습니다. Google에서 서명일을 결정하는 데 도움이 되는 정보를 제공할 수 있습니다.

서명일 부분 주위에 강조표시된 상자가 있는 Google 검색 텍스트 검색 결과의 삽화

호기심 많은 판다

[나무늘보는 왜 느린가요?](https://wikipedia.org/wiki/Sloth)

2023년 8월 25일

어떤 요소든지 문제가 발생할 소지가 있기 때문에 Google에서는 한 가지 날짜 요소에 의존하지 않습니다. 따라서 Google 시스템은 페이지가 게시되었거나 중요한 업데이트가 이루어진 시기를 최선으로 예상하기 위해 여러 요소를 살펴봅니다.

## Google에 날짜 정보를 제공하는 방법

Google에 날짜 정보를 제공하려면 다음 단계를 따르세요.

1.  [서명일 데이터에 영향을 주는 권장사항](https://developers.google.com/search/docs/appearance/publication-dates?hl=ko/#guidelines)을 따릅니다.
2.  사용자가 볼 수 있는 날짜를 페이지에 추가하고 눈에 잘 띄게 표시합니다. 날짜에 '게시' 또는 '최종 업데이트' 같은 텍스트로 적절하게 라벨을 지정합니다. 다음은 웹페이지에 관한 날짜 정보를 강조표시하는 방법의 예입니다.
    
    -   **게시 날짜: 2019년 2월 4일**
    -   **2019년 2월 4일에 게시됨**
    -   **최종 업데이트: 2018년 2월 14일**
    -   **업데이트 날짜: 2019년 2월 14일 오후 8시(동부 표준시)**
    
    게시 날짜 및/또는 최종 업데이트 날짜를 제공할 수 있습니다.
    
    ```php-template
    <html>
      <head>
        <title>Analyzing Google Search traffic drops</title>
      </head>
      <body>
        <p>
          Posted Tuesday, July 20, 2021
        </p>
        <p>
          Suppose you open Search Console and find out that your Google Search traffic dropped. What should you do?
        </p>
      </body>
    </html>
    ```
    
3.  [구조화된 데이터](https://developers.google.com/search/docs/appearance/structured-data/intro-structured-data?hl=ko)로 날짜를 지정합니다. [`CreativeWork`](https://schema.org/CreativeWork)의 하위유형(예: [`Article`](https://developers.google.com/search/docs/appearance/structured-data/article?hl=ko), [`BlogPosting`](https://schema.org/BlogPosting) 또는 [`VideoObject`](https://developers.google.com/search/docs/appearance/structured-data/video?hl=ko))을 추가하고 `datePublished` 및/또는 `dateModified` 필드를 지정하는 것이 좋습니다. [Google의 구조화된 데이터 가이드라인에 따라](https://developers.google.com/search/docs/appearance/structured-data/sd-policies?hl=ko) 크롤러가 문서 날짜를 파악할 수 있도록 해야 합니다.
    
    ```php-template
    <html>
      <head>
        <title>Analyzing Google Search traffic drops</title>
        <script type="application/ld+json">
        {
          "@context": "https://schema.org",
          "@type": "NewsArticle",
          "headline": "Analyzing Google Search traffic drops",
          "datePublished": "2021-07-20T08:00:00+08:00",
          "dateModified": "2021-07-20T09:20:00+08:00"
        }
        </script>
      </head>
      <body>
        <p>
          Posted Tuesday, July 20, 2021
        </p>
        <p>
          Suppose you open Search Console and find out that your Google Search traffic dropped. What should you do?
        </p>
      </body>
    </html>
    ```
    

## 서명일에 영향을 주기 위한 권장사항

Google은 표시되는 데이터인지, 구조화된 데이터인지와 상관없이 서명일이 검색결과에 표시되도록 보장하지 않지만, 가이드라인을 따르면 Google 알고리즘에서 정보를 찾고 처리하는 데 도움이 됩니다.

-   **날짜는 필요하며 시간은 필요하지 않습니다.** 그러나 정밀도를 높이기 위해 마크업에 시간과 시간대를 제공하는 것이 좋습니다.
-   **시간대를 지정할 때** 해당하는 경우 [일광 절약 시간](https://en.wikipedia.org/wiki/Daylight_saving_time)을 고려하여 [정확한 시간대](https://en.wikipedia.org/wiki/ISO_8601#Time_zone_designators)를 제공해야 합니다.
-   **날짜와 시간을 일관되게 지정합니다.** 사용자에게 표시되는 값과 구조화된 값 사이의 날짜(및 선택적 시간 및 시간대)가 일치하는지 확인합니다. 시간 및 시간대는 구조화된 데이터에 제공되었더라도 사용자에게 표시되는 데이터에서는 선택사항입니다.
-   **향후 날짜 또는 페이지에 설명된 작업 날짜는 지정하지 않도록 합니다.** 날짜는 페이지의 게시 또는 업데이트 날짜를 설명하지만, 여기에 설명된 스토리나 이벤트는 설명하지 않아야 합니다. 원하는 경우 페이지에 [이벤트 마크업](https://developers.google.com/search/docs/appearance/structured-data/event?hl=ko)을 추가하여 페이지에 나열된 활동을 설명할 수 있습니다.
-   **페이지에서 다른 날짜 표시는 최소화합니다.** 권장사항을 따랐는데도 잘못된 날짜가 선택된다면 페이지에 표시되는 다른 날짜를 일부 또는 전부 삭제해 보세요.
-   **페이지가 Google 뉴스 검색에 표시**되게 하려면 [추가 가이드라인](https://support.google.com/news/publisher-center/answer/9607104?hl=ko)을 따릅니다.

도움이 되었나요?

의견 보내기

달리 명시되지 않는 한 이 페이지의 콘텐츠에는 [Creative Commons Attribution 4.0 라이선스](https://creativecommons.org/licenses/by/4.0/)에 따라 라이선스가 부여되며, 코드 샘플에는 [Apache 2.0 라이선스](https://www.apache.org/licenses/LICENSE-2.0)에 따라 라이선스가 부여됩니다. 자세한 내용은 [Google Developers 사이트 정책](https://developers.google.com/site-policies?hl=ko)을 참조하세요. 자바는 Oracle 및/또는 Oracle 계열사의 등록 상표입니다.

최종 업데이트: 2026-02-20(UTC)