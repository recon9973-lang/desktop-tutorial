"""URL 중요도 — 어느 페이지의 결함이 더 무겁게 세어지는가.

측정 범위는 페이지 수가 아니라 **중요도로 가중된** 페이지 비율이다.

    coverage = 영향받은 중요도 가중 URL / 검사 대상 중요도 가중 URL

그래서 중요도를 잘못 매기면 점수가 잘못 나온다. 지금까지 콘솔 진단은 수집한 **모든**
페이지에 `CONVERSION_OR_HOME`(3.0) 을 붙이고 있었다. 태그 페이지 한 장의 결함이
홈페이지 결함과 같은 무게였고, 가중치라는 개념이 사실상 없었다.

## 이 분류기가 하지 않는 것

**`CATEGORY_OR_HUB` 을 자동으로 붙이지 않는다.** 픽스처를 보면 그 이유가 분명하다 —
같은 1단계 경로인데 `/guide/` 는 허브이고 `/deep/` 은 일반 콘텐츠다. 사람이 **뜻으로**
라벨한 것이고 주소 모양에서는 나오지 않는다. 규칙을 지어내면 절반은 맞고 절반은 틀리는데,
틀린 절반은 조용히 점수를 흔든다. 확신이 없을 때의 정답은 중립값(`CONTENT_OR_PRODUCT`)
이고, 허브 판정은 사람이 콘솔에서 고르게 두는 것이 맞다.

**`INTENTIONAL_NOINDEX` 도 자동으로 붙이지 않는다.** 배점이 0 이라 분모에서 빠지는데,
`noindex` 태그만 보고 "의도된 것" 이라고 단정하면 **실수로 걸린 noindex 를 우리가 숨겨
주는** 셈이 된다. 그 실수는 사이트가 검색에서 통째로 사라지는 가장 큰 결함이고, 그것을
찾아내는 것이 이 제품이 하는 일이다. 의도는 사람이 선언하는 것이지 태그에서 추론하는
것이 아니다. `sitewide_noindex` 픽스처조차 이 값을 쓰지 않고, 대신 검사가 그것을 찾아
상한을 건다.

## 붙이는 것

주소가 **확실히** 말해 주는 것만 붙인다.

| 근거 | 분류 |
|---|---|
| 진입 주소, 또는 경로가 없는 대표 주소 | `CONVERSION_OR_HOME` |
| 전환 의도가 경로에 적힌 페이지 (문의·예약·상담·오시는길 등) | `CONVERSION_OR_HOME` |
| 목록을 자르거나 걸러 보여 주는 주소 (페이지네이션·태그·검색) | `TAG_OR_FILTER` |
| 그 밖 전부 | `CONTENT_OR_PRODUCT` |
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from urllib.parse import urlsplit

from veo.contracts.enums import UrlImportance
from veo.seo.parsing.urls import normalise_url

#: 경로에 전환 의도가 적혀 있는 페이지. 국내 병원·클리닉 사이트가 실제로 쓰는 표기를
#: 함께 넣는다 — 이 제품의 첫 시장이 거기이고, `contact` 만 보면 `문의` 를 놓친다.
#:
#: 한 조각(segment) 전체가 일치할 때만 인정한다. 부분 일치를 허용하면
#: `/contactless-treatment/` 같은 주소가 전환 페이지로 잡힌다.
CONVERSION_SEGMENTS = frozenset(
    {
        # 영문
        "contact", "contact-us", "contactus", "inquiry", "inquiries", "enquiry",
        "reservation", "reserve", "booking", "book", "appointment", "appointments",
        "consult", "consultation", "quote", "estimate", "apply", "signup", "sign-up",
        "register", "pricing", "price", "prices", "plans", "location", "locations",
        "directions", "map", "maps", "hours", "cart", "checkout",
        # 국문
        "문의", "문의하기", "상담", "상담신청", "온라인상담", "예약", "예약하기",
        "진료예약", "전화상담", "오시는길", "찾아오시는길", "위치", "약도",
        "진료시간", "가격", "비용", "요금", "견적", "신청", "회원가입", "장바구니",
    }
)

#: 목록을 자르거나 걸러 보여 주는 주소. 같은 본문을 다른 순서로 다시 내놓는 자리라
#: 대표 페이지와 같은 무게로 셀 수 없다.
FILTER_SEGMENTS = frozenset(
    {
        "page", "pages", "tag", "tags", "category", "categories", "cat",
        "archive", "archives", "author", "search", "filter", "sort",
        "label", "keyword", "topic",
        "태그", "분류", "검색", "목록", "보관함", "작성자",
    }
)

#: 목록을 걸러 보여 준다는 뜻의 질의 문자열 이름.
FILTER_QUERY_KEYS = frozenset(
    {
        "page", "paged", "p", "s", "q", "query", "search", "keyword", "tag",
        "category", "cat", "filter", "sort", "order", "orderby", "per_page",
        "offset", "start",
    }
)


def _segments(url: str) -> tuple[str, ...]:
    path = urlsplit(url).path
    return tuple(segment for segment in path.split("/") if segment)


def _query_keys(url: str) -> frozenset[str]:
    query = urlsplit(url).query
    if not query:
        return frozenset()
    keys: set[str] = set()
    for part in query.split("&"):
        name, _, _value = part.partition("=")
        if name:
            keys.add(name.strip().lower())
    return frozenset(keys)


def classify_url(url: str, *, entry_url: str) -> UrlImportance:
    """이 주소 하나의 중요도. 확신이 없으면 중립값을 돌려준다."""
    normalised = normalise_url(url)

    # 사람이 "이걸 진단해 달라" 고 지정한 주소는 그 진단의 대표 페이지다. 무엇이든
    # 이보다 앞설 수 없다.
    if normalised == normalise_url(entry_url):
        return UrlImportance.CONVERSION_OR_HOME

    segments = _segments(normalised)
    lowered = {segment.lower() for segment in segments}

    # 걸러 보여 주는 주소를 **먼저** 본다. `/pricing/page/2/` 는 가격 페이지가 아니라
    # 가격 목록의 두 번째 장이고, `/?s=레이저` 는 홈페이지가 아니라 검색 결과다 —
    # 경로가 비어 있다는 것만 보고 홈으로 접으면 그것을 놓친다.
    if _query_keys(normalised) & FILTER_QUERY_KEYS:
        return UrlImportance.TAG_OR_FILTER
    if lowered & FILTER_SEGMENTS:
        return UrlImportance.TAG_OR_FILTER

    # 경로가 없다는 것만으로 홈이라고 하지 않는다. `/?page_id=4` 는 워드프레스가
    # 페이지를 질의로 가리키는 형태이고 홈페이지가 아니다. 알아보지 못하는 질의가
    # 붙어 있으면 중립값으로 둔다 — 모르는 것을 대표 페이지로 올리면 그 페이지의 결함이
    # 홈페이지 무게로 세어진다.
    if not segments:
        if urlsplit(normalised).query:
            return UrlImportance.CONTENT_OR_PRODUCT
        return UrlImportance.CONVERSION_OR_HOME
    if lowered & CONVERSION_SEGMENTS:
        return UrlImportance.CONVERSION_OR_HOME

    return UrlImportance.CONTENT_OR_PRODUCT


def classify_urls(urls: Iterable[str], *, entry_url: str) -> Mapping[str, str]:
    """주소마다 중요도를 붙인다. 키는 넘겨받은 주소 그대로다.

    키를 정규화하지 않는 것은 의도한 것이다. 이 표는 `CollectionContext.url_importance`
    로 들어가고, 그쪽은 **수집한 문서의 최종 주소**로 조회한다. 여기서 키를 바꾸면
    조회가 빗나가고, 그때 모든 페이지가 조용히 기본값으로 떨어진다.
    """
    return {url: classify_url(url, entry_url=entry_url).value for url in urls}


__all__ = [
    "CONVERSION_SEGMENTS",
    "FILTER_QUERY_KEYS",
    "FILTER_SEGMENTS",
    "classify_url",
    "classify_urls",
]
