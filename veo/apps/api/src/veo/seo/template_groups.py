"""블로그형(자동 생성) 페이지의 템플릿 그룹 — URL 모양으로 묶는다.

## 왜 묶는가

칼럼·소식 같은 자동 생성 페이지는 수백~수천 장이 되지만 **페이지별로 SEO 작업을
하는 것이 아니다.** 한 템플릿이 전부를 그리므로 결함도 템플릿 단위로 생긴다 —
실측(chamsarang1075.com, 2026-08-02)에서 게시판 칼럼 103장의 title 이 전부 같았고,
무작위 3장의 뼈대(레이아웃·JSON-LD·canonical 선언)가 완전히 동일했다. 표본 3장이
103장의 결함을 잡는다.

그래서 크롤이 그룹당 표본 몇 장만 가져오고, 아낀 예산으로 **고정 페이지를 전부**
본다. 구글 Search Console 도 같은 방식으로 URL 을 템플릿 그룹으로 묶어 판정한다.

## 이 모듈이 하지 않는 것

표본의 판정을 그룹 전체 점수로 **일반화하지 않는다.** 그것은 점수의 의미를 바꾸는
일이라 명세 1.9.0 의 몫이다(SEO_SCORING_V3_PAGES.md §9). 여기서는 수집 범위만
정하고, 표본 밖이 존재한다는 사실을 결과에 정직하게 남긴다.

## 그룹 판정은 보수적으로

잘못 묶으면 표본의 결함이 무고한 페이지에 씌워지고, 무고한 표본이 결함 페이지를
가린다. 그래서 **문서 식별자가 값만 다른 게시판형 쿼리**와 **접두 경로 아래 깊은
문서**만 그룹으로 본다. 최상위 고정 페이지(/불면증/ 같은)는 절대 그룹이 되지 않는다.
"""

from __future__ import annotations

from typing import Final
from urllib.parse import parse_qsl, urlsplit

__all__ = ["group_key"]

#: 게시판·블로그 플러그인이 문서를 가리킬 때 쓰는 쿼리 키. 값이 문서마다 다르고
#: 키 집합은 같다 — 같은 물리 페이지가 값만 바꿔 문서를 갈아 끼운다.
_DOCUMENT_QUERY_KEYS: Final = frozenset(
    {"uid", "wr_id", "document_srl", "idx", "no", "num", "seq", "post", "p", "article_id"}
)

#: 그룹으로 보지 않는 첫 경로 조각. 목록·분류 페이지는 문서가 아니라 문서를 담는
#: 그릇이고, 수가 적어 표본화할 이유가 없다.
_NEVER_GROUPED_PREFIXES: Final = frozenset({"category", "tag", "author", "page"})


def group_key(url: str) -> str | None:
    """이 주소가 속한 템플릿 그룹의 키. 그룹이 아니면 ``None``.

    두 가지 모양만 그룹이다:

    * **게시판형 쿼리** — 경로가 같고 쿼리에 문서 식별자 키가 있다.
      ``/칼럼/?pageid=10&mod=document&uid=188`` → ``/칼럼/?mod,pageid,uid``
      (키 집합만 남긴다 — 값이 다른 것이 그룹의 정의다).
    * **접두 경로형** — ``/news/글제목/`` 처럼 접두 아래 한 단계 더 들어간 문서.
      → ``/news/*``

    최상위 문서(``/불면증/``)와 홈은 언제나 ``None`` 이다 — 고정 페이지는 사람이
    한 장씩 만들며, 표본으로 대신할 수 없다.
    """
    parts = urlsplit(url)
    path = parts.path or "/"
    segments = [s for s in path.split("/") if s]

    if parts.query:
        keys = {key.lower() for key, _ in parse_qsl(parts.query, keep_blank_values=True)}
        if keys & _DOCUMENT_QUERY_KEYS:
            return f"{path}?{','.join(sorted(keys))}"

    if len(segments) >= 2:
        head = segments[0].lower()
        if head in _NEVER_GROUPED_PREFIXES:
            return None
        return f"/{segments[0]}/*"

    return None
