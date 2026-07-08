-   [홈](https://developers.google.com/?hl=ko)
-   [Search Central](https://developers.google.com/search?hl=ko)
-   [Documentation](https://developers.google.com/search/docs?hl=ko)

도움이 되었나요?

의견 보내기

-   이 페이지의 내용
-   [콘텐츠 차단 방법](https://developers.google.com/search/docs/crawling-indexing/control-what-you-share?hl=ko/#how-to-block-content)
    -   [사이트에서 콘텐츠 삭제](https://developers.google.com/search/docs/crawling-indexing/control-what-you-share?hl=ko/#remove-the-content-from-your-site)
    -   [파일을 비밀번호로 보호](https://developers.google.com/search/docs/crawling-indexing/control-what-you-share?hl=ko/#password-protect-your-files)
    -   [robots.txt을 사용한 크롤링 금지](https://developers.google.com/search/docs/crawling-indexing/control-what-you-share?hl=ko/#disallow-crawling-with-robots.txt)
-   [Google에서 기존 콘텐츠 삭제](https://developers.google.com/search/docs/crawling-indexing/control-what-you-share?hl=ko/#remove-existing-content-from-google)

# Google과 공유하는 정보 관리하기

Google은 사이트 소유자가 Google 검색결과에 표시되는 콘텐츠를 관리할 수 있는 다양한 방법을 지원합니다. 대부분의 사용자는 페이지의 색인을 생성하는 데 집중하지만 그와 반대로 콘텐츠가 Google 검색에 표시되지 않도록 하는 것이 중요할 때도 있습니다. Google로부터 콘텐츠를 숨기고자 하는 데에는 다음과 같은 몇 가지 이유가 있습니다.

-   **데이터 제한**: 이미 사이트를 사용하고 있는 사용자에게만 표시하려는 데이터가 사이트에 호스팅되어 있을 수 있습니다. Google이 이러한 데이터를 크롤링하지 못하도록 하여 검색결과에 표시되지 않게 할 수 있습니다.  
    또한 사이트에 게시된 특정 파일에 Google 검색에 표시될 수 있는 메타데이터가 포함될 수 있습니다. [Google 검색에서 수정된 정보 제외하는 방법 자세히 알아보기](https://developers.google.com/search/docs/crawling-indexing/keep-redacted-information-out?hl=ko)
-   **방문자에게 중요하지 않은 콘텐츠 숨기기**: 검색에 표시되어서는 안 되는 저품질 콘텐츠가 웹사이트에 있을 수 있습니다. 예를 들어 웹사이트에서 사용자가 콘텐츠를 제작하도록 허용하는 경우에 일부 콘텐츠가 [저품질이거나 스팸일 수도 있습니다](https://developers.google.com/search/docs/essentials/spam-policies?hl=ko#user-generated-spam). 이러한 콘텐츠의 색인 생성을 허용하면 Google 검색결과에서의 사이트 순위에 부정적인 영향을 미칠 수 있습니다.
-   **Google에서 중요한 콘텐츠에 집중하도록 하기**: 사이트가 매우 크고(수십만 개 이상의 URL 보유) 페이지에 중요도가 낮은 콘텐츠가 있거나 중복 콘텐츠가 많다면 Google에서 더 중요한 콘텐츠에 집중할 수 있도록 중복되거나 중요도가 낮은 페이지를 크롤링하지 못하게 할 수 있습니다.

## 콘텐츠 차단 방법

Google에 콘텐츠가 표시되지 않도록 차단하는 주된 방법은 다음과 같습니다.

| 메서드 | 메서드 |
|----------------------------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| ### 사이트에서 콘텐츠 삭제 | **대상: 모든 콘텐츠 유형**

사이트에서 콘텐츠를 삭제하면 가장 확실하게 콘텐츠가 Google 검색 또는 인터넷의 다른 곳에 표시되지 않게 할 수 있습니다. |
| ### 파일을 비밀번호로 보호 | **대상: 모든 콘텐츠 유형**

사이트에 기밀 또는 비공개 콘텐츠가 있는 경우에는 승인된 사용자만 콘텐츠에 액세스할 수 있도록 비밀번호로 보호해야 합니다. 이렇게 하면 Google 검색에 콘텐츠가 표시되지 않거나 콘텐츠가 이미 표시되는 경우에는 해당 콘텐츠를 Google 검색결과에서 삭제됩니다. |
| [`noindex` 규칙](https://developers.google.com/search/docs/crawling-indexing/block-indexing?hl=ko) | **대상: 모든 콘텐츠 유형**

`noindex` robots `meta` 태그는 Google에서 콘텐츠의 색인을 생성하지 않거나 Google 검색결과에 표시하지 않도록 지시하는 규칙입니다. 이렇게 차단된 콘텐츠는 다른 웹페이지에 연결되거나 다른 웹페이지를 통해 방문할 수 있으며 사용자가 링크를 이용해 직접 방문할 수도 있지만, Google 검색결과에는 표시되지 않습니다. |
| ### [robots.txt](https://developers.google.com/search/docs/crawling-indexing/prevent-images-on-your-page?hl=ko#for-non-emergency-image-removal)을 사용한 크롤링 금지 | **대상: 이미지 및 동영상**

Google은 Googlebot이 크롤링할 수 있는 이미지와 동영상만 색인을 생성합니다. Googlebot이 미디어 파일에 액세스하지 못하도록 하려면 [robots.txt 규칙을 사용하여 파일을 차단](https://developers.google.com/search/docs/crawling-indexing/prevent-images-on-your-page?hl=ko#for-non-emergency-image-removal)하세요. |
| [특정 Google 서비스 사용 중지](https://support.google.com/webmasters/answer/3035947?hl=ko) | **대상: 웹페이지**

[Google 쇼핑](https://www.google.com/shopping?hl=ko), [Google 호텔](https://www.google.com/travel/hotels?hl=ko) 및 공유숙박과 같은 특정 Google 서비스에 사이트의 콘텐츠를 포함하지 말아 달라고 Google에 요청할 수 있습니다. |

## Google에서 기존 콘텐츠 삭제

사이트에서 호스팅되는 콘텐츠가 이미 Google에 표시되는 경우에는 해당 검색결과 삭제를 요청할 수 있습니다. [사이트에서 호스팅된 페이지를 Google에서 삭제](https://developers.google.com/search/docs/crawling-indexing/remove-information?hl=ko)하는 방법을 알아보세요.

도움이 되었나요?

의견 보내기

달리 명시되지 않는 한 이 페이지의 콘텐츠에는 [Creative Commons Attribution 4.0 라이선스](https://creativecommons.org/licenses/by/4.0/)에 따라 라이선스가 부여되며, 코드 샘플에는 [Apache 2.0 라이선스](https://www.apache.org/licenses/LICENSE-2.0)에 따라 라이선스가 부여됩니다. 자세한 내용은 [Google Developers 사이트 정책](https://developers.google.com/site-policies?hl=ko)을 참조하세요. 자바는 Oracle 및/또는 Oracle 계열사의 등록 상표입니다.

최종 업데이트: 2025-12-31(UTC)