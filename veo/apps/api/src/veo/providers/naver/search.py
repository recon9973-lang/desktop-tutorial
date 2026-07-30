"""네이버 검색 API — 바깥에서 이 사업자를 뭐라고 하는가.

## 왜 DataLab 옆에 있나

같은 호스트(`openapi.naver.com`), 같은 헤더(`X-Naver-Client-Id/Secret`), 같은 자격증명을
쓴다. **DataLab 을 쓸 수 있으면 이것도 쓸 수 있다.** 그래서 재시도·회로차단기·응답 크기
상한도 그쪽과 같은 것을 쓴다 — 옆에 있는 것을 가져다 쓰지 않고 새로 쓰면 두 벌이 되고,
두 벌은 반드시 갈라진다(지침서 0-D).

## 여기서 나온 값은 점수에 들어가지 않는다

두 가지 한계 때문이다.

* **네이버 한 곳만 본다.** 구글·다음은 보지 않는다. 이것을 "웹 전체에서의 평판" 이라고
  부르면 재지 않은 것을 잰 것처럼 말하는 것이다(0-A).
* **이름이 비슷한 다른 업체가 섞인다.** 실측에서 "온담한의원" 을 찾으면 검색 1위가
  "백세온담한의원" 이었다. 그대로 세면 **없는 평판을 만들어 낸다.**

그래서 명세는 이 항목들을 `REFERENCE_ONLY` 로 두고, 화면은 "참고 · 별도 확인 필요" 로
표시한다. 조회는 하되 숫자로 확정하지 않는다.
"""

from __future__ import annotations

import json
import time
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Final, Literal, final

import httpx

from veo.common.http import read_capped
from veo.contracts.enums import ProviderState

# 같은 자격증명이다 — DataLab 과 검색 API 는 같은 네이버 오픈API 앱을 쓴다.
from veo.providers.naver.datalab import DataLabCredentials as NaverOpenApiCredentials
from veo.providers.naver.errors import (
    CircuitBreaker,
    NaverResponseTooLargeError,
    NaverSchemaError,
    ProviderFailure,
    ResilientCaller,
    RetryPolicy,
    classify_status,
    classify_transport_exception,
)

SEARCH_BASE_URL: Final = "https://openapi.naver.com"

#: 조회하는 말뭉치. `webkr`(웹문서)은 일부러 빼 두었다 — 계약이 정한 출처 유형
#: (디렉터리·등록부·언론·리뷰·소셜·학술) 중 어디에도 정직하게 넣을 수 없다. 억지로
#: 한 칸에 몰아넣으면 "출처가 다양하다" 는 판정이 근거 없이 좋아진다.
Corpus = Literal["local", "blog", "news", "cafearticle"]

#: 말뭉치 → 계약이 정한 출처 유형.
#: 블로그와 카페를 같은 `SOCIAL` 로 두는 것은 의도한 것이다. 둘 다 개인 게시물이고,
#: 다른 유형으로 세면 다양성 판정이 부풀어 오른다.
SOURCE_TYPES: Final[Mapping[str, str]] = {
    "local": "DIRECTORY",
    "news": "NEWS",
    "blog": "SOCIAL",
    "cafearticle": "SOCIAL",
}

DEFAULT_TIMEOUT_SECONDS: Final = 10.0
DEFAULT_MAX_RESPONSE_BYTES: Final = 512 * 1024
#: 한 말뭉치당 가져오는 항목 수. 참고용이라 표본이면 충분하다.
DEFAULT_DISPLAY: Final = 10


@final
@dataclass(frozen=True, slots=True)
class SearchItem:
    """검색 결과 한 건. 마크업(`<b>`)은 제거된 상태다."""

    corpus: str
    source_type: str
    title: str
    description: str
    url: str
    #: 지역 검색만 채운다. 나머지는 빈 문자열.
    address: str = ""
    telephone: str = ""

    @property
    def text(self) -> str:
        """이름 대조에 쓰는 본문."""
        return f"{self.title} {self.description}".strip()


@final
@dataclass(frozen=True, slots=True)
class SearchOutcome:
    """조회 결과, 또는 왜 못 했는지.

    실패해도 예외를 던지지 않는다. 참고 항목 하나 때문에 진단 전체가 멈추면 안 된다 —
    못 가져온 것은 못 가져온 것으로 남기고 나머지는 그대로 진행한다.
    """

    items: tuple[SearchItem, ...] = ()
    #: 말뭉치별로 네이버가 보고한 전체 건수. 가져온 항목 수와 다르다.
    totals: Mapping[str, int] = field(default_factory=dict)
    failure: ProviderFailure | None = None
    #: 아예 부르지 못한 말뭉치와 그 이유.
    unavailable: Mapping[str, str] = field(default_factory=dict)


@final
class NaverSearchClient:
    """네이버 검색을 부르거나, 왜 못 불렀는지 설명한다."""

    def __init__(
        self,
        *,
        credentials: NaverOpenApiCredentials | None,
        transport: httpx.BaseTransport | None = None,
        base_url: str = SEARCH_BASE_URL,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
        sleep: Callable[[float], None] = time.sleep,
        policy: RetryPolicy | None = None,
        breaker: CircuitBreaker | None = None,
        timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
        max_response_bytes: int = DEFAULT_MAX_RESPONSE_BYTES,
    ) -> None:
        self._credentials = credentials
        self._transport = transport
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout_seconds
        self._max_response_bytes = max_response_bytes
        self._caller = ResilientCaller(
            policy=policy or RetryPolicy(),
            breaker=breaker or CircuitBreaker(),
            sleep=sleep,
            now=clock,
        )

    def __repr__(self) -> str:
        return f"<NaverSearchClient state={self.state.value}>"

    @property
    def state(self) -> ProviderState:
        if self._credentials is None:
            return ProviderState.DISABLED_NO_CREDENTIAL
        return self._caller.breaker.provider_state()

    def look_up(
        self,
        query: str,
        *,
        corpora: Sequence[Corpus] = ("local", "blog", "news", "cafearticle"),
        display: int = DEFAULT_DISPLAY,
    ) -> SearchOutcome:
        """한 이름을 여러 말뭉치에서 찾는다.

        말뭉치 하나가 실패해도 나머지는 계속한다. 하나 때문에 전부를 버리면 "아무 데서도
        언급되지 않는다" 처럼 보이는데, 그것은 사실이 아니다.
        """
        cleaned = query.strip()
        if not cleaned:
            return SearchOutcome(unavailable={"*": "조회할 이름이 비어 있습니다."})
        if self._credentials is None:
            return SearchOutcome(
                unavailable={"*": "네이버 오픈API 자격증명이 없어 조회하지 않았습니다."}
            )

        items: list[SearchItem] = []
        totals: dict[str, int] = {}
        unavailable: dict[str, str] = {}
        failure: ProviderFailure | None = None

        for corpus in corpora:
            # `ResilientCaller` 는 예외를 던지지 않고 결과에 담아 돌려준다. 말뭉치 하나가
            # 실패해도 나머지는 계속한다 — 하나 때문에 전부를 버리면 "아무 데서도 언급되지
            # 않는다" 처럼 보이는데, 그것은 사실이 아니다.
            outcome = self._caller.call(
                lambda corpus=corpus: self._request(cleaned, corpus, display)  # type: ignore[misc]
            )
            if not outcome.succeeded:
                failure = failure or outcome.failure
                unavailable[corpus] = (
                    outcome.failure.reason_ko
                    if outcome.failure is not None
                    else "조회하지 못했습니다."
                )
                continue

            body = outcome.value
            assert isinstance(body, bytes)
            try:
                parsed = _parse(body)
            except NaverSchemaError as exc:
                unavailable[corpus] = str(exc)
                continue

            totals[corpus] = int(parsed.get("total") or 0)
            for raw in parsed.get("items") or ():
                if isinstance(raw, dict):
                    items.append(_item(corpus, raw))

        return SearchOutcome(
            items=tuple(items),
            totals=totals,
            failure=failure,
            unavailable=unavailable,
        )

    def _request(self, query: str, corpus: str, display: int) -> bytes:
        assert self._credentials is not None
        headers = {
            "X-Naver-Client-Id": self._credentials.client_id.get_secret_value(),
            "X-Naver-Client-Secret": self._credentials.client_secret.get_secret_value(),
        }
        with httpx.Client(
            transport=self._transport,
            timeout=httpx.Timeout(self._timeout),
            follow_redirects=False,
            cookies=None,
        ) as client:
            request = client.build_request(
                "GET",
                f"{self._base_url}/v1/search/{corpus}.json",
                params={"query": query, "display": display},
                headers=headers,
            )
            try:
                response = client.send(request, stream=True)
            except httpx.HTTPError as exc:
                raise classify_transport_exception(exc) from None
            try:
                if response.status_code != 200:
                    raise classify_status(
                        response.status_code, retry_after=response.headers.get("retry-after")
                    )
                return read_capped(response, self._max_response_bytes, NaverResponseTooLargeError)
            except httpx.HTTPError as exc:
                raise classify_transport_exception(exc) from None
            finally:
                response.close()


def strip_markup(value: str) -> str:
    """네이버는 검색어를 `<b>` 로 감싸서 돌려준다. 이름 대조 전에 걷어낸다."""
    out: list[str] = []
    depth = 0
    for char in value:
        if char == "<":
            depth += 1
        elif char == ">":
            depth = max(0, depth - 1)
        elif depth == 0:
            out.append(char)
    return (
        "".join(out)
        .replace("&amp;", "&")
        .replace("&lt;", "<")
        .replace("&gt;", ">")
        .replace("&quot;", '"')
        .replace("&#39;", "'")
        .strip()
    )


def _item(corpus: str, raw: Mapping[str, Any]) -> SearchItem:
    return SearchItem(
        corpus=corpus,
        source_type=SOURCE_TYPES.get(corpus, "SOCIAL"),
        title=strip_markup(str(raw.get("title") or "")),
        description=strip_markup(str(raw.get("description") or "")),
        url=str(raw.get("link") or ""),
        address=strip_markup(str(raw.get("roadAddress") or raw.get("address") or "")),
        telephone=strip_markup(str(raw.get("telephone") or "")),
    )


def _parse(body: bytes) -> Mapping[str, Any]:
    try:
        payload = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, ValueError) as exc:
        raise NaverSchemaError(f"body is not JSON: {type(exc).__name__}") from None
    if not isinstance(payload, dict):
        raise NaverSchemaError("body is not a JSON object")
    return payload


__all__ = [
    "DEFAULT_DISPLAY",
    "SEARCH_BASE_URL",
    "SOURCE_TYPES",
    "Corpus",
    "NaverSearchClient",
    "SearchItem",
    "SearchOutcome",
    "strip_markup",
]
