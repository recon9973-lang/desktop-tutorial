## 자바스크립트로 구조화된 데이터 생성

오늘날의 웹사이트에서는 많은 동적 콘텐츠를 표시하는 데 자바스크립트를 사용합니다. JavaScript를 사용하여 웹사이트에서 구조화된 데이터를 생성할 때 주의해야 할 몇 가지 사항이 있습니다. 본 가이드에서는 권장사항과 구현 전략을 설명합니다. 구조화된 데이터를 처음 사용한다면 [구조화된 데이터의 작동 방식](https://developers.google.com/search/docs/appearance/structured-data/intro-structured-data?hl=ko)을 자세히 알아보세요.

자바스크립트로 구조화된 데이터를 생성하는 방법에는 여러 가지가 있지만 가장 일반적인 방법은 다음과 같습니다.

-   [Google 태그 관리자](https://developers.google.com/search/docs/appearance/structured-data/generate-structured-data-with-javascript?hl=ko#use-google-tag-manager)
-   [맞춤 자바스크립트](https://developers.google.com/search/docs/appearance/structured-data/generate-structured-data-with-javascript?hl=ko#custom-javascript)

## Google 태그 관리자를 사용하여 동적으로 JSON-LD 생성

[Google 태그 관리자](https://tagmanager.google.com/?hl=ko)는 코드를 수정하지 않고도 웹사이트에서 태그를 관리할 수 있는 플랫폼입니다. Google 태그 관리자로 구조화된 데이터를 생성하려면 다음 단계를 따르세요.

1.  사이트에 [Google 태그 관리자를 설정하고 설치](https://support.google.com/tagmanager/answer/6103696?hl=ko)합니다.
2.  컨테이너에 새 **맞춤 HTML** 태그를 추가합니다.
3.  [지원되는 구조화된 데이터](https://developers.google.com/search/docs/guides/search-gallery?hl=ko) 블록을 태그 콘텐츠에 붙여넣습니다.
4.  컨테이너 관리자 메뉴의 **Google 태그 관리자 설치** 섹션에 표시된 대로 컨테이너를 설치합니다.
5.  웹사이트에 태그를 추가하려면 Google 태그 관리자 인터페이스에 컨테이너를 게시합니다.
6.  [구현한 사항을 테스트](https://developers.google.com/search/docs/appearance/structured-data/generate-structured-data-with-javascript?hl=ko#testing)합니다.

### Google 태그 관리자에서 변수 사용

Google 태그 관리자(GTM)는 [변수](https://support.google.com/tagmanager/topic/7683268?ref_topic=3441647&hl=ko)를 지원해 페이지에 있는 정보를 구조화된 데이터의 일부로 사용하도록 합니다. GTM에서 정보를 복제하는 대신 변수를 사용하여 페이지에서 구조화된 데이터를 추출합니다. GTM에서 정보를 복제하면 페이지 콘텐츠와 GTM을 통해 삽입된 구조화된 데이터가 일치하지 않을 위험이 커집니다.

예를 들어 이름이 다음과 같은 맞춤 변수를 생성하여 레시피 이름이 페이지 제목인 [레시피](https://developers.google.com/search/docs/appearance/structured-data/recipe?hl=ko) JSON-LD 블록을 동적으로 생성할 수 있습니다. `recipe_name`:

```javascript
function() { return document.title; }
```

그런 다음 맞춤 태그 HTML에서 `{{recipe_name}}`을 사용할 수 있습니다.

변수를 사용하는 페이지에서 필요한 모든 정보를 수집하기 위해 변수를 만드는 것이 좋습니다.

다음은 맞춤 HTML 태그 콘텐츠의 예입니다.

```perl
<script type="application/ld+json">
  {
    "@context": "https://schema.org/",
    "@type": "Recipe",
    "name": "{{recipe_name}}",
    "image": [ "{{recipe_image}}" ],
    "author": {
      "@type": "Person",
      "name": "{{recipe_author}}"
    }
  }
</script>
```

## 맞춤 자바스크립트로 구조화된 데이터 생성

구조화된 데이터를 생성하는 또 다른 방법은 JavaScript를 사용하여 구조화된 데이터를 모두 생성하거나 서버 측에서 렌더링된 구조화된 데이터에 더 많은 정보를 추가하는 것입니다. 어떻게 하든 Google 검색에서는 페이지를 렌더링할 때 DOM에서 사용 가능한 구조화된 데이터를 이해하고 처리할 수 있습니다. Google 검색에서 JavaScript를 처리하는 방법을 자세히 알아보려면 [JavaScript 기본 가이드](https://developers.google.com/search/docs/crawling-indexing/javascript/javascript-seo-basics?hl=ko)를 참조하세요.

다음은 자바스크립트로 생성된 구조화된 데이터의 예입니다.

1.  관심 있는 [구조화된 데이터 유형을 찾습니다](https://developers.google.com/search/docs/appearance/structured-data/search-gallery?hl=ko).
2.  다음 예와 같은 JavaScript 스니펫을 포함하도록 웹사이트의 HTML을 수정합니다(CMS 또는 호스팅 업체의 문서 참고 또는 개발자에게 문의).  
    
    ```javascript
    fetch('https://api.example.com/recipes/123')
    .then(response => response.text())
    .then(structuredDataText => {
      const script = document.createElement('script');
      script.setAttribute('type', 'application/ld+json');
      script.textContent = structuredDataText;
      document.head.appendChild(script);
    });
    ```
    
3.  [리치 결과 테스트로 구현한 사항을 테스트합니다](https://developers.google.com/search/docs/appearance/structured-data/generate-structured-data-with-javascript?hl=ko#testing).

## 서버 측 렌더링 사용

[서버 측 렌더링](https://developers.google.com/web/updates/2019/02/rendering-on-the-web?hl=ko#server-rendering)을 사용하면 렌더링된 출력에 구조화된 데이터를 포함할 수도 있습니다. 관심 있는 [구조화된 데이터 유형](https://developers.google.com/search/docs/appearance/structured-data/search-gallery?hl=ko)에 맞게 JSON-LD를 생성하는 방법은 프레임워크 문서에서 확인하세요.

## 구현 테스트

Google 검색에서 구조화된 데이터를 크롤링하고 색인을 생성할 수 있도록 하려면 다음과 같이 구현한 사항을 테스트하세요.

1.  [리치 결과 테스트](https://goo.gle/richresults)를 엽니다.
2.  테스트할 URL을 입력합니다.
3.  **URL 테스트**를 클릭합니다.
    
    **성공**: 올바르게 작업했으며 [구조화된 데이터 유형이 도구에서 지원](https://support.google.com/webmasters/answer/7445569?hl=ko)되면 '페이지가 리치 결과 기능에 적합함'이라는 메시지가 표시됩니다.  
    리치 결과 테스트에서 지원하지 않는 구조화된 데이터 유형을 테스트하는 경우 렌더링된 HTML을 확인하세요. 렌더링된 HTML에 구조화된 데이터가 포함되어 있으면 Google 검색에서 처리할 수 있습니다.
    
    **다시 시도**: 오류 또는 경고가 표시되면 구문 오류이거나 속성이 누락됐을 가능성이 높습니다. [구조화된 데이터 유형에 관한 문서](https://developers.google.com/search/docs/appearance/structured-data/search-gallery?hl=ko)를 읽고 모든 속성을 추가했는지 확인하세요. 문제가 지속되면 [검색 관련 자바스크립트 문제 해결](https://developers.google.com/search/docs/crawling-indexing/javascript/fix-search-javascript?hl=ko) 가이드도 확인하세요.