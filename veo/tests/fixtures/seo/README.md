# SEO 수집기 픽스처

각 하위 디렉터리는 크롤링이 끝난 사이트 하나를 그대로 재현한 자료입니다. 테스트는
네트워크를 쓰지 않고 이 파일들만 읽어 `CollectionContext`를 만듭니다.

## 디렉터리 규약

- `site.json` — 매니페스트. 어떤 URL이 어떤 파일로 응답했는지, 상태 코드·헤더·리다이렉트
  체인·URL 중요도를 적습니다. HTML 자체에는 담을 수 없는 사실만 여기에 둡니다.
- `pages/*.html` — 크롤러가 받은 **원본 HTML**.
- `rendered/*.html` — 자바스크립트 실행 뒤의 **렌더링된 DOM**. 렌더러가 돌지 않은 URL은
  아예 없습니다. 없는 것과 같은 것은 다른 사실이므로 비워 두지 않습니다.
- `robots.txt`, `sitemap.xml` — 있으면 그대로 읽습니다.

## `site.json` 필드

| 필드 | 뜻 |
| --- | --- |
| `target_url` | 진단 대상 진입 URL |
| `locale` | 기본 `ko-KR`. 네이버 대상 여부 판단에 쓰입니다. |
| `pages[].url` | 최종 URL (리다이렉트 후) |
| `pages[].file` | `pages/` 아래 원본 HTML 파일명. 없으면 본문이 빈 응답입니다. |
| `pages[].status` | HTTP 상태 코드 |
| `pages[].headers` | 응답 헤더 (소문자 키) |
| `pages[].importance` | `UrlImportance` 값 |
| `pages[].hops` | 리다이렉트 체인. `{url, status, location}` 목록 |
| `pages[].rendered` | `rendered/` 아래 렌더링 DOM 파일명 (선택) |
| `primary_url` | 대표 문서 URL. 없으면 `target_url` |
| `sitemaps` | `{사이트맵 URL: 파일명}` |

## 픽스처 목록

| 디렉터리 | 재현하는 상황 |
| --- | --- |
| `healthy/` | 기술적 결함이 없는 사이트 |
| `sitewide_noindex/` | 사이트 전체가 `noindex` |
| `cross_domain_canonical/` | canonical이 외부 도메인을 가리킴 |
| `redirect_loop/` | 리다이렉트 루프 |
| `broken_jsonld/` | JSON-LD 문법 오류·필수 속성 누락 |
| `duplicate_metadata/` | title·description이 페이지 간 중복 |
| `orphan_page/` | 내부 링크로 도달할 수 없는 주요 페이지 |
| `conflicting_hreflang/` | hreflang과 canonical 신호가 서로 어긋남 |
| `render_gap/` | 원본 HTML과 렌더링 DOM이 크게 다름 |
| `brochure_na/` | 해당 없음 항목이 많은 소개용 사이트 |
