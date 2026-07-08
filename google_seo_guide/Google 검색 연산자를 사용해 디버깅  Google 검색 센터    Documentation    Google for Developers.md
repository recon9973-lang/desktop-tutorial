-   [홈](https://developers.google.com/?hl=ko)
-   [Search Central](https://developers.google.com/search?hl=ko)
-   [Documentation](https://developers.google.com/search/docs?hl=ko)

도움이 되었나요?

의견 보내기

-   이 페이지의 내용
-   [filetype:](https://developers.google.com/search/docs/monitor-debug/search-operators?hl=ko/#filetype:)
-   [imagesize:](https://developers.google.com/search/docs/monitor-debug/search-operators?hl=ko/#imagesize:)
-   [site:](https://developers.google.com/search/docs/monitor-debug/search-operators?hl=ko/#site:)
-   [src:](https://developers.google.com/search/docs/monitor-debug/search-operators?hl=ko/#src:)

# Google 검색 연산자 개요

Google 검색은 검색 범위를 좁히거나 타겟팅하는 데 사용할 수 있는 [여러 검색 연산자](https://support.google.com/websearch/answer/2466433?hl=ko)를 지원합니다. 다음 검색 연산자는 웹사이트 디버깅에도 유용할 수 있습니다.

예를 들어 `site:` 검색 연산자는 웹사이트에서 댓글 스팸을 모니터링하는 데 유용할 수 있고 이미지 검색 `imagesize:` 연산자는 사이트에서 작은 이미지를 찾는 데 도움이 될 수 있습니다.

검색 연산자는 색인 생성 및 검색 제한을 따르므로 Search Console의 [URL 검사](https://support.google.com/webmasters/answer/9012289?hl=ko) 도구는 디버깅 용도에 더 안정적입니다.

다음 표에는 Google 검색에서 페이지의 다양한 측면을 검사하는 데 사용할 수 있는 검색 연산자가 포함되어 있습니다.

| 검색 연산자 | 검색 연산자 |
|---------------|---------------------------------------------------------------------------------------------------------------------------------------------------|
| ## `filetype:` | `content-type` HTTP 헤더 또는 파일 확장자로 정의된 [특정 파일 형식](https://developers.google.com/search/docs/crawling-indexing/indexable-file-types?hl=ko)의 검색 결과를 찾습니다. 예를 들어 콘텐츠에 'galway'라는 용어가 포함된 `.rtf`로 끝나는 RTF 파일 및 URL을 검색할 수 있습니다.

filetype:rtf galway |
| ## [`imagesize:`](https://developers.google.com/search/docs/monitor-debug/search-operators/image-search?hl=ko#imagesize) | 특정 크기의 이미지가 포함된 페이지를 찾습니다. 이 검색 연산자는 Google 이미지에서만 작동합니다. 예:

imagesize:1200x800 |
| ## [`site:`](https://developers.google.com/search/docs/monitor-debug/search-operators/all-search-site?hl=ko) | 특정 도메인, URL, URL 접두사에서 검색결과를 찾습니다. 예:

site:https://www.google.com/ |
| ## [`src:`](https://developers.google.com/search/docs/monitor-debug/search-operators/image-search?hl=ko#src) | `src` 속성에서 특정 이미지 URL을 참조하는 페이지를 찾습니다. 이 검색 연산자는 Google 이미지에서만 작동합니다. 예:

src:https://www.example.com/images/peanut-butter.png |

도움이 되었나요?

의견 보내기

달리 명시되지 않는 한 이 페이지의 콘텐츠에는 [Creative Commons Attribution 4.0 라이선스](https://creativecommons.org/licenses/by/4.0/)에 따라 라이선스가 부여되며, 코드 샘플에는 [Apache 2.0 라이선스](https://www.apache.org/licenses/LICENSE-2.0)에 따라 라이선스가 부여됩니다. 자세한 내용은 [Google Developers 사이트 정책](https://developers.google.com/site-policies?hl=ko)을 참조하세요. 자바는 Oracle 및/또는 Oracle 계열사의 등록 상표입니다.

최종 업데이트: 2025-12-18(UTC)