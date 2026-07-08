선정적인 콘텐츠(예: 성적으로 노골적이거나 노골적인 폭력 콘텐츠)가 검색 결과에 표시되는 것을 원하지 않는 사용자가 많으며, Google의 [세이프서치 설정](https://support.google.com/websearch/answer/510?hl=ko)을 사용하면 선정적인 콘텐츠를 필터링할 수 있습니다. 하지만 Google 시스템에서 다른 콘텐츠를 선정적인 콘텐츠로 표시할 수도 있습니다(예: 란제리 웹사이트, 성교육 사이트, 마사지 사이트, 선정적인 콘텐츠 등 미묘하거나 은근히 암시하는 성격의 콘텐츠). 즉, 이러한 콘텐츠가 세이프서치에 의해 잘못 필터링될 수 있습니다. 이 가이드에서는 사이트가 Google 검색 결과에서 선정적인 것으로 잘못 신고되었는지 확인하는 방법과 일반적인 실수를 해결하는 방법을 설명합니다.

## 세이프서치에서 콘텐츠를 필터링 중인지 확인하기

먼저 세이프서치에서 몇 개의 페이지를 필터링하는지 아니면 전체 웹사이트를 필터링하는지 확인하여 문제가 어떻게 표시되고 앞으로 어떻게 해결할지 더 잘 이해할 수 있습니다.

1.  **특정 페이지를 확인합니다**. 사이트의 특정 페이지가 선정적인 것으로 식별되고 있는지 확인하려면 다음 단계를 따르세요.
    1.  [세이프서치가 사용 안 함으로 설정되어 있는지 확인](https://support.google.com/websearch/answer/510?hl=ko)합니다.
    2.  검색 결과에서 해당 페이지를 찾을 수 있는 검색어를 검색합니다.
    3.  [세이프서치를 필터링으로 설정](https://support.google.com/websearch/answer/510?hl=ko)합니다. 검색 결과에 페이지가 표시되지 않는다면 이 검색어가 세이프서치로 인해 필터링되고 있을 가능성이 높습니다.
2.  **사이트 전체 확인**: 전체 사이트가 선정적인 것으로 식별되고 있는지 확인하려면 [`site:` 검색 연산자](https://developers.google.com/search/docs/monitor-debug/search-operators/all-search-site?hl=ko)를 사용하여 검색 결과에서 사이트를 찾은 다음 세이프서치를 필터링으로 설정하세요. 더 이상 사이트가 표시되지 않으면 세이프서치가 사용 설정되어 있을 때 Google에서 사이트를 필터링하고 있는 것입니다.
3.  **해당하는 경우 사이트 변경**: 문제가 어떻게 표시되는지 파악한 후 [일반적인 실수](https://developers.google.com/search/docs/specialty/explicit/troubleshooting?hl=ko#common-mistakes) 목록을 확인하고 해당하는 문제를 해결합니다.
4.  **검토 요청**: 수정사항을 적용한 경우 Google 분류기에서 콘텐츠를 다시 처리하는 데 최대 2~3개월이 걸릴 수 있으므로 [검토를 요청](https://support.google.com/webmasters/contact/safesearch_review?hl=ko)하기 전에 최소 2~3개월을 기다려야 합니다. 사이트가 항상 [사이트 최적화 안내](https://developers.google.com/search/docs/specialty/explicit/guidelines?hl=ko)를 따랐다면 즉시 검토를 요청할 수 있습니다.

## 일반적인 실수 해결하기

다음은 사이트가 노골적인 콘텐츠로 잘못 신고되게 하는 가장 일반적인 실수입니다.

| 흔히 발생하는 실수 | 흔히 발생하는 실수 |
|------------------------------------------------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| ### 선정적이지 않은 콘텐츠에 성인 등급 `meta` 태그 추가 | 사이트 소유자가 선정적이지 않은 페이지에 성인용 평점 `meta` 태그를 적용하는 경우가 있습니다. 세이프서치는 콘텐츠와 관계없이 성인용 등급 `meta` 태그를 사용하는 모든 페이지를 필터링합니다.

문제를 해결하려면 성적으로 노골적이지 않은 페이지에서 [성인용 등급 `meta` 태그](https://developers.google.com/search/docs/crawling-indexing/special-tags?hl=ko#rating)를 삭제합니다. [성인용 등급 `meta` 태그](https://developers.google.com/search/docs/crawling-indexing/special-tags?hl=ko#meta-tags)는 성적으로 노골적인 _페이지_에만 사용해야 합니다. |
| ### 동영상 사이트맵에서 선정적이지 않은 동영상을 `family_friendly`가 아닌 것으로 라벨 지정 | 사이트 소유자가 [`<video:family_friendly>` 태그](https://developers.google.com/search/docs/crawling-indexing/sitemaps/video-sitemaps?hl=ko#family-friendly)를 너무 광범위하게 적용하여 세이프서치에서 콘텐츠와 관계없이 `family_friendly`가 아닌 모든 페이지를 필터링하는 경우가 있습니다.

문제를 해결하려면 콘텐츠가 성적으로 노골적이거나 노골적인 폭력이 포함된 경우에만 값이 `no`인 가족 친화적 태그를 적용하세요. |
| ### 콘텐츠 검토 없이 모든 UGC 댓글 허용 | 콘텐츠 검토가 충분하지 않은 상태에서 사용자가 선정적인 콘텐츠를 작성하거나 업로드하도록 허용하는 경우 사이트가 선정적인 것으로 간주될 수 있습니다.

문제를 해결하려면 [스팸성 UGC 댓글을 방지](https://developers.google.com/search/docs/monitor-debug/prevent-abuse?hl=ko)하기 위한 조치와 기타 콘텐츠 검토 권장사항을 구현하는 것이 좋습니다. |
| ### 연령 제한으로 Googlebot 제한 | 연령 제한이 있고 Googlebot이 연령 제한을 트리거하지 않고 크롤링하도록 허용하지 않으면 일부 페이지는 선정적이지 않더라도 Google 시스템에서 전체 사이트가 본질적으로 선정적이라고 판단하여 검색 결과에서 전체 사이트를 필터링할 수 있습니다.

이 문제를 해결하려면 [Googlebot이 연령 제한 없이 크롤링할 수 있도록 허용](https://developers.google.com/search/docs/specialty/explicit/guidelines?hl=ko#allow-googlebot-to-crawl)하고 [필수 전면 광고에 대한 Google 가이드라인](https://developers.google.com/search/docs/appearance/avoid-intrusive-interstitials?hl=ko#mandatory-interstitials)을 따르세요. 그런 다음 Search Console의 [라이브 URL 테스트](https://support.google.com/webmasters/answer/9012289?hl=ko#test_live_page)를 사용하여 Googlebot이 연령 제한을 트리거하지 않고 크롤링할 수 있는지 확인합니다. |
| ### 선정적인 페이지를 선정적이지 않은 페이지와 구분하지 않음 | 성적으로 노골적인 콘텐츠가 많고 이러한 페이지를 별도의 도메인이나 하위 도메인에 그룹화하지 않으면 Google 시스템에서 전체 사이트가 선정적인 것으로 판단할 수 있습니다.

이 문제를 해결하려면 [선정적인 페이지를 별도의 도메인이나 하위 도메인에 그룹화](https://developers.google.com/search/docs/specialty/explicit/guidelines?hl=ko#group-explicit-pages)하는 것이 좋습니다. |

## 문제 해결

변경사항을 적용한 후에도 여전히 웹페이지가 선정적인 웹페이지로 잘못 신고되어 있다면 다음 사항을 고려해 보세요.

-   최근에 변경사항을 적용한 경우에는 분류기에서 처리 시간이 더 필요할 수 있습니다. 최대 2~3개월이 걸릴 수 있습니다.
-   웹사이트에 노출이 심하거나 선정적인 콘텐츠 (컴퓨터 생성 콘텐츠 포함)와 노골적인 폭력이 다량 포함되어 있으면 전체 사이트가 선정적인 것으로 분류되어 세이프서치 필터 적용 시 표시되지 않을 수 있습니다.
-   페이지의 선정적인 이미지를 흐리게 처리하는 경우에도 이미지를 선명하게 할 수 있거나 선명한 이미지로 연결된다면 페이지는 여전히 선정적인 것으로 간주될 수 있습니다.
-   선정적인 페이지에서는 세이프서치 필터 사용 여부와 관계없이 리치 결과, 추천 스니펫, 동영상 미리보기와 같은 일부 검색 결과 기능을 사용할 수 없습니다. [검색 결과 기능 정책](https://support.google.com/websearch/answer/10622781?hl=ko#features_policies) 자세히 알아보기