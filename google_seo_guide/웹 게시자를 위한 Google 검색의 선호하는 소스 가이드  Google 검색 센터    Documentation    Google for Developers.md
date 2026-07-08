웹사이트 소유자는 사용자가 Google 검색에서 내 간행물을 선호하는 소스로 찾을 수 있도록 도울 수 있습니다. 사용자가 내 사이트를 선호하는 출처로 선택하면 '[주요 뉴스](https://support.google.com/websearch/answer/16379181?hl=ko)'에 내 콘텐츠가 표시될 가능성이 높아지며 '선호' 배지가 강조 표시됩니다. AI 모드 및 AI 개요에서 내 사이트를 선호하는 출처로 선택한 사용자에게는 내 콘텐츠가 '선호' 배지와 함께 강조 표시될 수 있습니다.

![AI 모드의 선호하는 출처 기능](https://developers.google.com/static/search/docs/images/preferred-sources-ai-mode.png?hl=ko&dcb_=0.5656501292815393) ![주요 뉴스의 선호하는 출처 기능](https://developers.google.com/static/search/docs/images/preferred-sources-site.png?hl=ko)

## 기능 제공 여부

선호하는 출처 기능은 Google 검색을 사용할 수 있는 모든 언어로 '주요 뉴스' 기능에 대해 전 세계에서 제공됩니다. 선호하는 출처는 AI 모드 및 AI 개요가 제공되는 모든 언어와 지역에서 해당 기능에 표시될 수도 있습니다.

도메인 수준 및 하위 도메인 수준 사이트만 [출처 환경설정 도구](https://www.google.com/preferences/source?hl=ko)에 표시될 수 있습니다. 예를 들어 `https://www.example.com/` 및 `https://code.example.com/`은 선호하는 소스에 적합하지만 하위 디렉터리 `https://www.example.com/blog`는 적합하지 않습니다.

## 사용자가 내 사이트를 선호하는 소스로 찾을 수 있도록 지원하는 방법

사이트가 [출처 환경설정 도구](https://www.google.com/preferences/source?hl=ko)에 표시되는 경우(확인하려면 도구의 검색창에 사이트를 입력하세요) 다음 방법을 사용하여 독자가 사이트를 선호하는 출처로 선택하도록 안내할 수 있습니다.

-   **소셜 게시물 또는 프로모션에 딥 링크를 추가합니다.** 사용자를 [출처 환경설정 도구](https://www.google.com/preferences/source?hl=ko)의 사이트로 바로 연결하는 다음 URL 형식을 사용합니다.
    
    ```
    https://google.com/preferences/source?q=Your_Website's_URL
    ```
    
    예를 들어 사이트가 `https://example.com`인 경우 다음 URL을 사용하세요.
    
    ```
    https://google.com/preferences/source?q=example.com
    ```
    
-   **다른 소셜 CTA와 함께 사이트에 버튼을 추가**합니다. 자체 디자인을 사용하거나 Google에서 일부 언어에 제공하는 버튼 애셋을 다운로드할 수 있습니다.
    
    | 언어별 버튼 애셋 | 언어별 버튼 애셋 |
    |------------|---------------------------|
    | 나열된 모든 언어 | [(all_listed_languages) 다운로드](https://services.google.com/fh/files/helpcenter/google_preferred_source_badge_all_languages.zip?hl=ko) |
    | 덴마크어 | [(da) 다운로드](https://services.google.com/fh/files/helpcenter/google_preferred_source_badge_da.zip?hl=ko) |
    | 영어 | [(en) 다운로드](https://services.google.com/fh/files/helpcenter/google_preferred_source_badge_en.zip?hl=ko) |
    | 에스토니아어 | [(et) 다운로드](https://services.google.com/fh/files/helpcenter/google_preferred_source_badge_et.zip?hl=ko) |
    | 핀란드어 | [(fi) 다운로드](https://services.google.com/fh/files/helpcenter/google_preferred_source_badge_fi.zip?hl=ko) |
    | 프랑스어 | [(fr) 다운로드](https://services.google.com/fh/files/helpcenter/google_preferred_source_badge_fr.zip?hl=ko) |
    | 독일어 | [(de) 다운로드](https://services.google.com/fh/files/helpcenter/google_preferred_source_badge_de.zip?hl=ko) |
    | 히브리어 | [(iw) 다운로드](https://services.google.com/fh/files/helpcenter/google_preferred_source_badge_iw.zip?hl=ko) |
    | 힌디어 | [(hi) 다운로드](https://services.google.com/fh/files/helpcenter/google_preferred_source_badge_hi.zip?hl=ko) |
    | 일본어 | [(ja) 다운로드](https://services.google.com/fh/files/helpcenter/google_preferred_source_badge_ja.zip?hl=ko) |
    | 한국어 | [(ko) 다운로드](https://services.google.com/fh/files/helpcenter/google_preferred_source_badge_ko.zip?hl=ko) |
    | 포르투갈어(브라질) | [(pt-br) 다운로드](https://services.google.com/fh/files/helpcenter/google_preferred_source_badge_pt-br.zip?hl=ko) |
    | 러시아어 | [(ru) 다운로드](https://services.google.com/fh/files/helpcenter/google_preferred_source_badge_ru.zip?hl=ko) |
    | 스페인어 | [(es) 다운로드](https://services.google.com/fh/files/helpcenter/google_preferred_source_badge_es.zip?hl=ko) |
    | 스웨덴어 | [(sv) 다운로드](https://services.google.com/fh/files/helpcenter/google_preferred_source_badge_sv.zip?hl=ko) |
    | 터키어 | [(tr) 다운로드](https://services.google.com/fh/files/helpcenter/google_preferred_source_badge_tr.zip?hl=ko) |
    | 우크라이나어 | [(uk) 다운로드](https://services.google.com/fh/files/helpcenter/google_preferred_source_badge_uk.zip?hl=ko) |