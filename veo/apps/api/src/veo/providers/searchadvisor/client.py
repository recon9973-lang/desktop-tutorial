"""네이버 서치어드바이저 — IndexNow, and a stated gap where an API would be.

Read the package docstring first. In short: Naver publishes an IndexNow endpoint and
nothing else that VEO can call, so this module implements the one and names the others.

Every capability in :data:`NOT_AVAILABLE_CAPABILITIES` returns
:attr:`CapabilityState.NOT_AVAILABLE` **without opening a connection**. That is not a
degraded mode waiting for a credential — no credential would change it. It is the honest
answer, and it carries the manual alternative so the Korean text a customer sees tells them
what to actually do.

The error machinery comes from :mod:`veo.providers.naver.errors`: this *is* Naver, so the
customer-safe Korean messages there already name the right provider. Two IndexNow-specific
rejections get their own classes, because "키 파일을 못 찾았습니다" and "권한이 없습니다"
send an operator to two different places.
"""

from __future__ import annotations

import time
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, ClassVar, Final, final
from urllib.parse import urlsplit

import httpx
from pydantic import SecretStr

from veo.contracts.enums import DataSource
from veo.providers.naver.errors import (
    UNKNOWN,
    CallOutcome,
    CircuitBreaker,
    NaverCredentialMissingError,
    NaverProviderError,
    ProviderFailure,
    ResilientCaller,
    RetryPolicy,
    classify_status,
    classify_transport_exception,
)

__all__ = [
    "INDEXNOW_ENDPOINT",
    "NOT_AVAILABLE_CAPABILITIES",
    "SEARCH_ADVISOR_UNAVAILABLE_KO",
    "CapabilityGap",
    "CapabilityState",
    "IndexNowBadRequestError",
    "IndexNowKey",
    "IndexNowKeyRejectedError",
    "IndexNowSubmission",
    "IndexNowUrlRejectedError",
    "SearchAdvisorClient",
    "indexnow_payload",
    "search_advisor_capability",
]

#: Naver's own IndexNow endpoint. Naver is a participating IndexNow search engine, and a
#: submission to any participant is shared with the others; VEO submits to Naver's
#: endpoint directly because Naver is the engine VEO's customers care about.
INDEXNOW_ENDPOINT: Final = "https://searchadvisor.naver.com/indexnow"

DEFAULT_TIMEOUT_SECONDS: Final = 10.0

#: IndexNow's documented acceptances. ``202`` means the URLs were taken but the key file
#: has not been validated yet — accepted, and worth saying so rather than reporting a
#: success that may still be rejected minutes later.
_ACCEPTED_STATUSES: Final = frozenset({200, 202})

#: A submission may name at most this many URLs. The IndexNow specification puts the limit
#: at 10,000 per request.
MAX_URLS_PER_SUBMISSION: Final = 10_000


class CapabilityState(StrEnum):
    """Whether VEO can obtain something at all.

    ``NOT_AVAILABLE`` is not ``DISABLED_NO_CREDENTIAL``. One of them is fixed by adding a
    key; the other cannot be fixed by anyone, because the provider publishes no interface.
    Reporting the second as the first sends an operator hunting for a credential that does
    not exist.
    """

    AVAILABLE = "AVAILABLE"
    NOT_AVAILABLE = "NOT_AVAILABLE"


@final
@dataclass(frozen=True, slots=True)
class CapabilityGap:
    """One thing VEO cannot obtain, why, and what a person can do instead."""

    capability: str
    state: CapabilityState
    reason_ko: str
    manual_alternative_ko: str


SEARCH_ADVISOR_UNAVAILABLE_KO: Final = (
    "네이버 서치어드바이저는 사이트 등록·소유확인·수집 통계·사이트맵 처리 상태를 조회할 수 있는 "
    "공개 API를 제공하지 않습니다. 해당 정보는 웹 화면에서 사람이 확인하는 방식으로만 열려 있어 "
    "VEO는 이 항목들을 '조회 불가'로 표시하고 추정하지 않습니다. 자격증명을 등록해도 달라지지 "
    "않습니다."
)

_MANUAL_REGISTRATION_KO: Final = (
    "서치어드바이저에 로그인해 사이트를 추가하고, HTML 파일 업로드 또는 메타 태그로 소유를 확인한 "
    "뒤 사이트맵과 RSS를 제출하십시오. 확인 결과는 담당자가 VEO에 직접 입력해야 합니다."
)

_MANUAL_REPORT_KO: Final = (
    "서치어드바이저 웹 화면의 '요약'과 '수집/색인 현황'에서 직접 확인하십시오. VEO는 이 수치를 "
    "가져올 수 없으며, 크롤링으로 추정하지도 않습니다."
)

NOT_AVAILABLE_CAPABILITIES: Final[Mapping[str, CapabilityGap]] = {
    "site_registration": CapabilityGap(
        capability="site_registration",
        state=CapabilityState.NOT_AVAILABLE,
        reason_ko=SEARCH_ADVISOR_UNAVAILABLE_KO,
        manual_alternative_ko=_MANUAL_REGISTRATION_KO,
    ),
    "ownership_verification": CapabilityGap(
        capability="ownership_verification",
        state=CapabilityState.NOT_AVAILABLE,
        reason_ko=SEARCH_ADVISOR_UNAVAILABLE_KO,
        manual_alternative_ko=_MANUAL_REGISTRATION_KO,
    ),
    "crawl_stats": CapabilityGap(
        capability="crawl_stats",
        state=CapabilityState.NOT_AVAILABLE,
        reason_ko=SEARCH_ADVISOR_UNAVAILABLE_KO,
        manual_alternative_ko=_MANUAL_REPORT_KO,
    ),
    "sitemap_status": CapabilityGap(
        capability="sitemap_status",
        state=CapabilityState.NOT_AVAILABLE,
        reason_ko=SEARCH_ADVISOR_UNAVAILABLE_KO,
        manual_alternative_ko=_MANUAL_REPORT_KO,
    ),
    "index_status": CapabilityGap(
        capability="index_status",
        state=CapabilityState.NOT_AVAILABLE,
        reason_ko=SEARCH_ADVISOR_UNAVAILABLE_KO,
        manual_alternative_ko=_MANUAL_REPORT_KO,
    ),
}


def search_advisor_capability(capability: str) -> CapabilityGap:
    """What VEO can obtain for ``capability``.

    An unrecognised name is also ``NOT_AVAILABLE``: the set of things Naver exposes is
    closed and small, and defaulting an unknown request to "available" would be a
    guarantee VEO cannot keep.
    """
    known = NOT_AVAILABLE_CAPABILITIES.get(capability)
    if known is not None:
        return known
    return CapabilityGap(
        capability=capability,
        state=CapabilityState.NOT_AVAILABLE,
        reason_ko=SEARCH_ADVISOR_UNAVAILABLE_KO,
        manual_alternative_ko=_MANUAL_REPORT_KO,
    )


# --------------------------------------------------------------------------- #
# IndexNow
# --------------------------------------------------------------------------- #


class IndexNowBadRequestError(NaverProviderError):
    """400 — the submission itself was malformed."""

    message_ko: ClassVar[str] = (
        "IndexNow 제출 형식이 거부되었습니다(400). 이 제출은 반영되지 않았습니다."
    )


class IndexNowKeyRejectedError(NaverProviderError):
    """403 — the key file could not be validated at the location given."""

    message_ko: ClassVar[str] = (
        "IndexNow 키가 확인되지 않았습니다(403). 키 파일이 지정한 위치에 그대로 올라가 있는지, "
        "파일 내용이 키 값과 정확히 같은지 확인해 주세요."
    )


class IndexNowUrlRejectedError(NaverProviderError):
    """422 — the URLs do not belong to the host, or do not match the key."""

    message_ko: ClassVar[str] = (
        "제출한 URL이 해당 사이트에 속하지 않거나 키와 맞지 않아 거부되었습니다(422). "
        "이 제출은 반영되지 않았습니다."
    )


@final
@dataclass(frozen=True, slots=True)
class IndexNowKey:
    """A site's IndexNow key and where it is published.

    The key is public by design — it has to be readable at ``key_location`` for a search
    engine to validate it. It is still wrapped in :class:`~pydantic.SecretStr` so that it
    cannot drift into a log line or an error message by accident; ``key_location`` is the
    part VEO reports.
    """

    key: SecretStr
    key_location: str


@final
@dataclass(frozen=True, slots=True)
class IndexNowSubmission:
    """A record of what VEO submitted, and what the endpoint said about it.

    ``source`` is ``VEO_INTERNAL``: this is a record of an action VEO took, not a
    measurement of the site. Filing it as a provider measurement would let it be read as
    evidence about the customer's configuration.
    """

    endpoint: str
    host: str
    submitted_urls: tuple[str, ...]
    status_code: int
    accepted: bool
    submitted_at: datetime
    key_location: str
    source: DataSource = DataSource.VEO_INTERNAL


def indexnow_payload(*, key: IndexNowKey | None) -> dict[str, Any] | None:
    """Build the ``INDEXNOW`` provider payload, or ``None`` when VEO does not know.

    Returning ``{"configured": False}`` for a site VEO was simply never told about would
    be a claim about that site's configuration. VEO does not know that a site lacks
    IndexNow just because nobody handed VEO a key, so the payload is absent and the check
    stays UNKNOWN with its own "미구성으로 단정하지 않습니다" wording.
    """
    if key is None:
        return None
    return {"configured": True, "key_location": key.key_location}


class SearchAdvisorClient:
    """Submits to IndexNow; refuses, in writing, to pretend about anything else."""

    def __init__(
        self,
        *,
        transport: httpx.BaseTransport | None = None,
        endpoint: str = INDEXNOW_ENDPOINT,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
        sleep: Callable[[float], None] = time.sleep,
        policy: RetryPolicy | None = None,
        breaker: CircuitBreaker | None = None,
        timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
    ) -> None:
        self._transport = transport
        self._endpoint = endpoint
        self._clock = clock
        self._timeout = timeout_seconds
        self._caller = ResilientCaller(
            policy=policy or RetryPolicy(),
            breaker=breaker or CircuitBreaker(),
            sleep=sleep,
            now=clock,
        )

    def __repr__(self) -> str:
        return f"<SearchAdvisorClient endpoint={self._endpoint}>"

    def capability(self, capability: str) -> CapabilityGap:
        """What VEO can obtain. Answered from a table; opens no connection."""
        return search_advisor_capability(capability)

    def search_advisor_payload(self) -> None:
        """There is no payload to build, and that is the point.

        Always ``None``: the SEO collector reads a missing payload as UNKNOWN with a
        stated reason, which is the truthful outcome. Returning ``{"site_registered":
        False}`` would assert something about the customer's account that VEO has no way
        of knowing.
        """
        return None

    def submit_indexnow(
        self, *, host: str, urls: Sequence[str], key: IndexNowKey | None
    ) -> CallOutcome[IndexNowSubmission]:
        """Notify Naver that these URLs changed.

        With no key the client **never opens a connection** — the same rule the credential
        gate enforces everywhere else in VEO, applied to the one secret IndexNow has.
        """
        if key is None:
            return CallOutcome(
                value=UNKNOWN,
                failure=ProviderFailure.from_error(
                    NaverCredentialMissingError("no IndexNow key"),
                    occurred_at=self._clock(),
                ),
                attempts=0,
            )

        submitted = tuple(url.strip() for url in urls if url.strip())
        if not submitted:
            raise ValueError("at least one URL is required")
        if len(submitted) > MAX_URLS_PER_SUBMISSION:
            raise ValueError(
                f"IndexNow accepts at most {MAX_URLS_PER_SUBMISSION} URLs per submission"
            )
        # Checked before the call, not after a 422: a rejected batch tells us nothing about
        # which URL was wrong, and the answer is knowable here.
        _reject_foreign_urls(host=host, urls=submitted)

        def operation() -> IndexNowSubmission:
            submitted_at = self._clock()
            status = self._post(host=host, urls=submitted, key=key)
            return IndexNowSubmission(
                endpoint=self._endpoint,
                host=host,
                submitted_urls=submitted,
                status_code=status,
                accepted=status in _ACCEPTED_STATUSES,
                submitted_at=submitted_at,
                key_location=key.key_location,
            )

        return self._caller.call(operation)

    def _post(self, *, host: str, urls: Sequence[str], key: IndexNowKey) -> int:
        body = {
            "host": host,
            "key": key.key.get_secret_value(),
            "keyLocation": key.key_location,
            "urlList": list(urls),
        }
        with httpx.Client(
            transport=self._transport,
            timeout=httpx.Timeout(self._timeout),
            follow_redirects=False,
            cookies=None,
        ) as client:
            request = client.build_request(
                "POST",
                self._endpoint,
                json=body,
                headers={"Content-Type": "application/json; charset=utf-8"},
            )
            try:
                response = client.send(request)
            except httpx.HTTPError as exc:
                raise classify_transport_exception(exc) from None

            # The response body is never read. IndexNow answers with a status code, and
            # anything else it sends is prose that must not reach a customer.
            if response.status_code in _ACCEPTED_STATUSES:
                return response.status_code
            raise _classify_indexnow(
                response.status_code, retry_after=response.headers.get("retry-after")
            )


def _classify_indexnow(status_code: int, *, retry_after: str | None) -> NaverProviderError:
    """IndexNow's documented rejections, then the shared classifier for everything else."""
    if status_code == 400:
        return IndexNowBadRequestError(f"status={status_code}")
    if status_code == 403:
        return IndexNowKeyRejectedError(f"status={status_code}")
    if status_code == 422:
        return IndexNowUrlRejectedError(f"status={status_code}")
    return classify_status(status_code, retry_after=retry_after)


def _reject_foreign_urls(*, host: str, urls: Sequence[str]) -> None:
    expected = host.strip().lower()
    for url in urls:
        parsed = urlsplit(url)
        if (parsed.hostname or "").lower() != expected:
            raise ValueError(
                f"{url!r} does not belong to host {host!r}; IndexNow submissions are "
                "per-host and a foreign URL is rejected for the whole batch"
            )
