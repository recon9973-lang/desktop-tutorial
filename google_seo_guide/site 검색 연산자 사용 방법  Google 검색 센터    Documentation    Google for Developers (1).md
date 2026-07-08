`site:` 검색어는 연산자에 지정된 특정 도메인, URL, URL 접두사에서 검색결과를 요청할 수 있는 검색 연산자입니다. 예:

| `site:` 예 | `site:` 예 |
|---------------------------------------------|--------------------------------------------------------------------------------|
| `site:example.com` | `example.com` 도메인(`www.example.com`, `recipes.example.com`)의 결과만 표시합니다. |
| `site:https://www.example.com/ramen` tsukemen | `https://www.example.com/ramen`으로 시작하고 tsukemen 용어와 관련된 URL이 포함된 페이지의 결과를 표시합니다. |

`site:` 검색 연산자는 모든 Google 검색 속성에서 사용할 수 있습니다.

## 사이트 소유자를 위한 용도

`site:` 검색어는 여러 방식으로 사이트 디버깅에 도움이 될 수 있습니다. 몇 가지 예를 살펴보면 다음과 같습니다.

| `site:` 예 | `site:` 예 |
|------------------------------------------------------|----------------------------------------------|
| `site:example.com` | 색인이 생성된 URL과 게재 URL 목록을 반환합니다. |
| `site:https://example.com/recipes/tsukemen.html` | 특정 URL의 색인 생성 및 게재 여부를 파악하는 데 도움이 될 수 있습니다. |
| `site:example.com viagra casino` | 사이트의 스팸 문제를 식별하고 모니터링하는 데 도움이 됩니다. |
| `site:https://example.com/` lemon | 사이트에서 'lemon'이라는 용어에 관해 표시할 수 있는 URL을 표시합니다. |
| `site:https://example.com/recipes/tsukemen.html` lemon | 특정 URL이 'lemon'이라는 용어에 관해 색인이 생성되었는지를 표시합니다. |

## 제한사항

<iframe frameborder="0" allowfullscreen="" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share" referrerpolicy="strict-origin-when-cross-origin" width="640" height="360" src="https://www.youtube.com/embed/SgrDKE7xcEk?origin=https%3A%2F%2Fdevelopers.google.com&amp;autoplay&amp;controls&amp;embed_domain&amp;enablejsapi=1&amp;end&amp;hl&amp;showinfo&amp;start&amp;video-id=SgrDKE7xcEk&amp;widgetid=109&amp;forigin=https%3A%2F%2Fdevelopers.google.com%2Fsearch%2Fdocs%2Fmonitor-debug%2Fsearch-operators%2Fall-search-site%3Fhl%3Dko&amp;aoriginsup=1&amp;gporigin=https%3A%2F%2Fdevelopers.google.com%2Fsearch%2Fdocs%2Fcrawling-indexing%2Famp%2Fabout-amp%3Fhl%3Dko&amp;vf=1" id="widget110" data-title="Why does a site:query not show all my pages?"></iframe>

`site:` 연산자는 기본적으로 검색 사용자를 위해 설계되었으므로 사이트 소유자가 제한적이라고 생각할 수 있는 제한사항이 몇 가지 있습니다. 구체적으로는 다음과 같습니다.

-   `site:` 연산자는 검색어에 지정된 접두사로 색인이 생성된 URL을 모두 반환하지는 않습니다. 접두사로 색인이 생성되고 게재되는 URL 수를 식별하는 것과 같은 작업에 `site:` 연산자를 사용하려는 경우 이 점에 유의하세요.
-   검색어가 없는 `site:` 연산자(예: `site:example.com`)는 검색결과의 순위를 매기지 않습니다. 일반적으로 상단에 접두사에 관한 가장 짧은 URL이 표시되지만, 그 외에는 검색결과가 비교적 무작위로 표시됩니다.