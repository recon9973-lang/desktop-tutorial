"""The official Naver Search Ad API — absolute search counts, clicks, CTR, competition.

This module is the only place in VEO that produces a :class:`SearchCount`. A count from
here is an *absolute monthly number of searches*, which is a different kind of quantity
from the relative interest index in :mod:`veo.providers.naver.datalab`. The two modules do
not import each other, so no refactor can quietly route one into the other.

Three things this adapter refuses to do:

* **Invent.** A value the provider did not supply comes back as ``None`` with a
  :class:`~veo.contracts.enums.ValueQuality` saying which kind of absence it is.
* **Flatten.** ``0``, an explicit ``null``, an absent key, and the ``"< 10"`` low-volume
  marker are four different facts, and they stay four different facts all the way to the
  database column and the export file.
* **Guess at a new schema.** If the response is not the shape VEO knows, the call fails
  as :class:`~veo.providers.naver.errors.NaverSchemaError` rather than mapping whatever
  looks close. A wrong number is worse than no number.

The provider's own values are kept in ``provider_raw`` beside the mapping, so a mapping
bug can be diagnosed later without another call — and so a customer disputing a figure
can be shown exactly what Naver said.

**Unverified.** VEO has no Search Ad credential, so none of the field names or value
conventions below have been checked against a live response. They follow the documented
response shape. ``keywords/INTEGRATION_REQUEST.md`` lists precisely what was inferred.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Final, final

import httpx
from pydantic import SecretStr

from veo.contracts.enums import DataSource, ProviderState, ValueQuality
from veo.providers.naver.errors import (
    UNKNOWN,
    CallOutcome,
    CircuitBreaker,
    NaverCredentialMissingError,
    NaverResponseTooLargeError,
    NaverSchemaError,
    ProviderFailure,
    ResilientCaller,
    RetryPolicy,
    classify_status,
    classify_transport_exception,
)

__all__ = [
    "API_VERSION",
    "BELOW_THRESHOLD_MARKER",
    "BELOW_THRESHOLD_UPPER_BOUND_EXCLUSIVE",
    "KEYWORDSTOOL_PATH",
    "SEARCHAD_BASE_URL",
    "AverageMetric",
    "NaverSearchAdClient",
    "SearchAdCredentials",
    "SearchAdKeywordMetrics",
    "SearchAdKeywordResponse",
    "SearchCount",
    "build_headers",
    "normalize_keywordstool",
    "sign",
]

SEARCHAD_BASE_URL: Final = "https://api.searchad.naver.com"
KEYWORDSTOOL_PATH: Final = "/keywordstool"

#: VEO's label for *this mapping*, not a version string Naver publishes. It changes when
#: the field mapping below changes, so a stored metric can always be read back with the
#: rules that produced it. Kept short: ``keyword_metrics.api_version`` is ``VARCHAR(32)``.
API_VERSION: Final = "searchad.keywordstool.map.v1"

#: Naver reports very low volumes as a marker rather than a number, to avoid disclosing
#: near-unique queries. It is a *bound*, not the number zero.
BELOW_THRESHOLD_MARKER: Final = "< 10"
BELOW_THRESHOLD_UPPER_BOUND_EXCLUSIVE: Final = 10

DEFAULT_TIMEOUT_SECONDS: Final = 10.0
DEFAULT_MAX_RESPONSE_BYTES: Final = 4 * 1024 * 1024
MAX_KEYWORDS_PER_CALL: Final = 5

#: Response keys this adapter understands. Anything else in a row is reported through
#: ``unmapped_fields`` rather than dropped — a silent drop is how a schema change becomes
#: a column of zeroes.
_MAPPED_KEYS: Final = frozenset(
    {
        "relKeyword",
        "monthlyPcQcCnt",
        "monthlyMobileQcCnt",
        "monthlyAvePcClkCnt",
        "monthlyAveMobileClkCnt",
        "monthlyAvePcCtr",
        "monthlyAveMobileCtr",
        "plAvgDepth",
        "compIdx",
    }
)

_MISSING = object()

#: A quality either asserts a number or explains its absence. Nothing sits in between.
_QUALITIES_WITH_A_VALUE: Final = frozenset({ValueQuality.EXACT, ValueQuality.ROUNDED})
_QUALITIES_WITHOUT_A_VALUE: Final = frozenset(
    {
        ValueQuality.MISSING,
        ValueQuality.SUPPRESSED_BY_PROVIDER,
        ValueQuality.BELOW_PROVIDER_THRESHOLD,
        ValueQuality.RANGE,
    }
)


# --------------------------------------------------------------------------- #
# Signing
# --------------------------------------------------------------------------- #


@final
@dataclass(frozen=True, slots=True)
class SearchAdCredentials:
    """One organization's Search Ad credential set.

    The secret is wrapped in :class:`~pydantic.SecretStr` so it renders as ``**********``
    in a repr, a log line, or an accidental response body. It is unwrapped in exactly one
    place — :func:`sign` — and the result of that unwrapping never leaves the process.
    """

    api_key: SecretStr
    secret_key: SecretStr
    customer_id: str


def sign(*, timestamp_ms: int, method: str, path: str, secret_key: SecretStr) -> str:
    """``base64(HMAC-SHA256(secret, "{timestamp}.{METHOD}.{path}"))``.

    Signatures are generated server-side only. There is no code path that hands the
    secret, or a signing function bound to it, to anything outside this process.

    A path carrying a query string is rejected rather than signed: the server signs the
    path alone, so signing ``"/keywordstool?hintKeywords=x"`` produces a signature that
    can never verify, and the resulting 401 is indistinguishable from a bad key.
    """
    if not path.startswith("/"):
        raise ValueError("path must be absolute and begin with '/'")
    if "?" in path:
        raise ValueError("path must not contain a query string; the signature covers the path")

    message = f"{timestamp_ms}.{method.upper()}.{path}"
    digest = hmac.new(
        secret_key.get_secret_value().encode("utf-8"),
        message.encode("utf-8"),
        hashlib.sha256,
    ).digest()
    return base64.b64encode(digest).decode("ascii")


def build_headers(
    *, credentials: SearchAdCredentials, timestamp_ms: int, method: str, path: str
) -> dict[str, str]:
    """The four headers the API requires. The secret key is not among them."""
    return {
        "X-Timestamp": str(timestamp_ms),
        "X-API-KEY": credentials.api_key.get_secret_value(),
        "X-Customer": credentials.customer_id,
        "X-Signature": sign(
            timestamp_ms=timestamp_ms,
            method=method,
            path=path,
            secret_key=credentials.secret_key,
        ),
    }


# --------------------------------------------------------------------------- #
# Values
# --------------------------------------------------------------------------- #


@final
@dataclass(frozen=True, slots=True)
class SearchCount:
    """An absolute number of searches, or a stated reason there is no number.

    ``value`` and ``quality`` are validated against each other on construction, so it is
    not possible to build a count that claims to be exact while holding nothing, or that
    holds a number while claiming to be missing. That check exists because the mistake it
    prevents is invisible downstream: a suppressed value written as ``0`` reads to a
    customer as "nobody searches for this".
    """

    value: int | None
    quality: ValueQuality
    upper_bound_exclusive: int | None = None
    source: DataSource = DataSource.NAVER_SEARCH_AD

    def __post_init__(self) -> None:
        if self.value is None and self.quality in _QUALITIES_WITH_A_VALUE:
            raise ValueError(
                f"quality {self.quality} claims a value, but none was supplied"
            )
        if self.value is not None and self.quality in _QUALITIES_WITHOUT_A_VALUE:
            raise ValueError(
                f"quality {self.quality} says there is no value, but one was supplied"
            )
        if self.value is not None and self.value < 0:
            raise ValueError("a search count must not be negative")

    @property
    def is_measured(self) -> bool:
        return self.value is not None

    @classmethod
    def exact(cls, value: int, *, source: DataSource = DataSource.NAVER_SEARCH_AD) -> SearchCount:
        return cls(value=value, quality=ValueQuality.EXACT, source=source)

    @classmethod
    def missing(cls, *, source: DataSource = DataSource.NAVER_SEARCH_AD) -> SearchCount:
        return cls(value=None, quality=ValueQuality.MISSING, source=source)

    @classmethod
    def suppressed(cls, *, source: DataSource = DataSource.NAVER_SEARCH_AD) -> SearchCount:
        return cls(value=None, quality=ValueQuality.SUPPRESSED_BY_PROVIDER, source=source)

    @classmethod
    def below_threshold(
        cls, *, upper_bound_exclusive: int, source: DataSource = DataSource.NAVER_SEARCH_AD
    ) -> SearchCount:
        return cls(
            value=None,
            quality=ValueQuality.BELOW_PROVIDER_THRESHOLD,
            upper_bound_exclusive=upper_bound_exclusive,
            source=source,
        )

    @classmethod
    def ranged(
        cls, *, upper_bound_exclusive: int, source: DataSource = DataSource.CALCULATED
    ) -> SearchCount:
        return cls(
            value=None,
            quality=ValueQuality.RANGE,
            upper_bound_exclusive=upper_bound_exclusive,
            source=source,
        )

    def note_ko(self) -> str:
        """A one-line explanation a customer can read beside the value."""
        if self.quality is ValueQuality.EXACT:
            return "제공자가 보고한 값입니다."
        if self.quality is ValueQuality.ROUNDED:
            return "제공자가 반올림해 보고한 값입니다."
        if self.quality is ValueQuality.BELOW_PROVIDER_THRESHOLD:
            bound = self.upper_bound_exclusive
            return (
                f"제공자가 보고 하한 미만으로 표시한 구간입니다({bound} 미만). "
                "0이 아니라 '정확한 수치를 제공하지 않음'입니다."
            )
        if self.quality is ValueQuality.RANGE:
            bound = self.upper_bound_exclusive
            return f"정확한 값 대신 구간만 알 수 있습니다({bound} 미만)."
        if self.quality is ValueQuality.SUPPRESSED_BY_PROVIDER:
            return "제공자가 값을 제공하지 않았습니다. 0이 아니라 '측정 불가'입니다."
        return "응답에 해당 항목이 없었습니다. 0이 아니라 '측정 불가'입니다."


#: Naver's CTR fields are already percentages, not ratios. Settled on 2026-07-28 against
#: a live response: 임플란트 reported 4,370 PC searches, 24.1 average clicks and a CTR of
#: 0.59 — and 24.1/4370 is 0.55%, so 0.59 means 0.59 percent. Read as a ratio it would
#: claim 59%, a hundredfold overstatement. Nothing downstream may multiply by 100.
CTR_UNIT = "PERCENT"

#: Click counts are monthly averages of absolute clicks, not rates.
CLICK_UNIT = "MONTHLY_AVERAGE_COUNT"


@final
@dataclass(frozen=True, slots=True)
class AverageMetric:
    """An average click count or click-through rate, with the same honesty rules.

    The value is stored exactly as Naver sent it. For CTR that means a **percentage**
    (see :data:`CTR_UNIT`) — 0.59 is 0.59%, not 59%. Rescaling here would make the stored
    figure disagree with the provider's own raw response, which is kept alongside it.

    ``keyword_metrics`` has no ``*_quality`` column for these two families, so the quality
    recorded here travels in the API response and in ``provider_raw`` rather than in a
    column of its own. See ``INTEGRATION_REQUEST.md``.
    """

    value: float | None
    quality: ValueQuality
    source: DataSource = DataSource.NAVER_SEARCH_AD

    def __post_init__(self) -> None:
        if self.value is None and self.quality in {ValueQuality.EXACT, ValueQuality.ROUNDED}:
            raise ValueError(f"quality {self.quality} claims a value, but none was supplied")
        if self.value is not None and self.quality in {
            ValueQuality.MISSING,
            ValueQuality.SUPPRESSED_BY_PROVIDER,
        }:
            raise ValueError(f"quality {self.quality} says there is no value, but one exists")

    def note_ko(self) -> str:
        if self.quality is ValueQuality.EXACT:
            return "제공자가 보고한 값입니다."
        if self.quality is ValueQuality.SUPPRESSED_BY_PROVIDER:
            return "제공자가 값을 제공하지 않았습니다. 0이 아니라 '측정 불가'입니다."
        return "응답에 해당 항목이 없었습니다. 0이 아니라 '측정 불가'입니다."


# --------------------------------------------------------------------------- #
# Normalisation
# --------------------------------------------------------------------------- #


@final
@dataclass(frozen=True, slots=True)
class SearchAdKeywordMetrics:
    """One keyword's official figures, with the provider's raw row beside them."""

    keyword: str
    monthly_pc_searches: SearchCount
    monthly_mobile_searches: SearchCount
    monthly_total_searches: SearchCount
    avg_pc_clicks: AverageMetric
    avg_mobile_clicks: AverageMetric
    avg_pc_ctr: AverageMetric
    avg_mobile_ctr: AverageMetric
    competition_label: str | None
    ad_depth: int | None
    source_rank: int | None
    provider_raw: Mapping[str, Any] = field(default_factory=dict)

    #: Naver publishes an advertising competition *label* (``compIdx``), not a 0-100
    #: index. Deriving a number from the label and storing it in ``competition_index``
    #: would look like a provider figure while being VEO's invention, so the column stays
    #: empty and the label is what is reported.
    competition_index: float | None = None


@final
@dataclass(frozen=True, slots=True)
class SearchAdKeywordResponse:
    """A normalised ``/keywordstool`` response, plus what VEO could not map."""

    metrics: tuple[SearchAdKeywordMetrics, ...]
    api_version: str
    collected_at: datetime
    raw_response_hash: str
    unmapped_fields: tuple[str, ...] = ()


def _count_from_raw(row: Mapping[str, Any], key: str) -> SearchCount:
    """Map one raw count, keeping the four kinds of absence apart."""
    raw = row.get(key, _MISSING)
    if raw is _MISSING:
        return SearchCount.missing()
    if raw is None:
        return SearchCount.suppressed()
    if isinstance(raw, bool):
        # ``True`` is an ``int`` in Python. Reading it as 1 would be a fabrication.
        return SearchCount.missing()
    if isinstance(raw, int):
        return SearchCount.exact(raw)
    if isinstance(raw, str):
        text = raw.strip()
        if text.replace(" ", "") == BELOW_THRESHOLD_MARKER.replace(" ", ""):
            return SearchCount.below_threshold(
                upper_bound_exclusive=BELOW_THRESHOLD_UPPER_BOUND_EXCLUSIVE
            )
        try:
            return SearchCount.exact(int(text))
        except ValueError:
            # Some marker VEO has not seen. Recording it as MISSING keeps it out of the
            # numbers while ``provider_raw`` preserves what was actually said.
            return SearchCount.missing()
    return SearchCount.missing()


def _average_from_raw(row: Mapping[str, Any], key: str) -> AverageMetric:
    raw = row.get(key, _MISSING)
    if raw is _MISSING:
        return AverageMetric(value=None, quality=ValueQuality.MISSING)
    if raw is None:
        return AverageMetric(value=None, quality=ValueQuality.SUPPRESSED_BY_PROVIDER)
    if isinstance(raw, bool):
        return AverageMetric(value=None, quality=ValueQuality.MISSING)
    if isinstance(raw, int | float):
        return AverageMetric(value=float(raw), quality=ValueQuality.EXACT)
    if isinstance(raw, str):
        try:
            return AverageMetric(value=float(raw.strip()), quality=ValueQuality.EXACT)
        except ValueError:
            return AverageMetric(value=None, quality=ValueQuality.MISSING)
    return AverageMetric(value=None, quality=ValueQuality.MISSING)


def _total(pc: SearchCount, mobile: SearchCount) -> SearchCount:
    """PC + mobile, and an honest answer when that addition cannot be performed.

    Naver does not publish a total; this is VEO's arithmetic, so the result is labelled
    ``CALCULATED``. Two below-threshold figures still bound the total, which is more
    useful than "unknown" and — crucially — is not the same claim as a number.
    """
    if pc.is_measured and mobile.is_measured:
        assert pc.value is not None and mobile.value is not None
        return SearchCount.exact(pc.value + mobile.value, source=DataSource.CALCULATED)

    both_below = (
        pc.quality is ValueQuality.BELOW_PROVIDER_THRESHOLD
        and mobile.quality is ValueQuality.BELOW_PROVIDER_THRESHOLD
        and pc.upper_bound_exclusive is not None
        and mobile.upper_bound_exclusive is not None
    )
    if both_below:
        assert pc.upper_bound_exclusive is not None and mobile.upper_bound_exclusive is not None
        return SearchCount.ranged(
            upper_bound_exclusive=pc.upper_bound_exclusive + mobile.upper_bound_exclusive
        )

    if ValueQuality.SUPPRESSED_BY_PROVIDER in {pc.quality, mobile.quality}:
        return SearchCount.suppressed(source=DataSource.CALCULATED)
    return SearchCount.missing(source=DataSource.CALCULATED)


def _ad_depth(row: Mapping[str, Any]) -> int | None:
    raw = row.get("plAvgDepth")
    if isinstance(raw, bool) or raw is None:
        return None
    if isinstance(raw, int):
        return raw
    if isinstance(raw, str):
        try:
            return int(raw.strip())
        except ValueError:
            return None
    return None


def normalize_keywordstool(
    payload: Mapping[str, Any], *, collected_at: datetime, raw_bytes: bytes
) -> SearchAdKeywordResponse:
    """Map a ``/keywordstool`` payload into VEO's vocabulary.

    Raises :class:`~veo.providers.naver.errors.NaverSchemaError` when the payload is not
    the documented shape. The alternative — mapping what looks close and defaulting the
    rest — produces a response full of zeroes that nobody can tell from measurements.
    """
    rows = payload.get("keywordList")
    if not isinstance(rows, list):
        raise NaverSchemaError("response has no keywordList array")

    metrics: list[SearchAdKeywordMetrics] = []
    unmapped: set[str] = set()

    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            raise NaverSchemaError(f"keywordList[{index}] is not an object")
        keyword = row.get("relKeyword")
        if not isinstance(keyword, str) or not keyword.strip():
            raise NaverSchemaError(f"keywordList[{index}] has no relKeyword")

        unmapped.update(key for key in row if key not in _MAPPED_KEYS)

        pc = _count_from_raw(row, "monthlyPcQcCnt")
        mobile = _count_from_raw(row, "monthlyMobileQcCnt")
        competition = row.get("compIdx")

        metrics.append(
            SearchAdKeywordMetrics(
                keyword=keyword,
                monthly_pc_searches=pc,
                monthly_mobile_searches=mobile,
                monthly_total_searches=_total(pc, mobile),
                avg_pc_clicks=_average_from_raw(row, "monthlyAvePcClkCnt"),
                avg_mobile_clicks=_average_from_raw(row, "monthlyAveMobileClkCnt"),
                avg_pc_ctr=_average_from_raw(row, "monthlyAvePcCtr"),
                avg_mobile_ctr=_average_from_raw(row, "monthlyAveMobileCtr"),
                competition_label=competition if isinstance(competition, str) else None,
                ad_depth=_ad_depth(row),
                source_rank=index + 1,
                provider_raw=dict(row),
            )
        )

    return SearchAdKeywordResponse(
        metrics=tuple(metrics),
        api_version=API_VERSION,
        collected_at=collected_at,
        raw_response_hash=hashlib.sha256(raw_bytes).hexdigest(),
        unmapped_fields=tuple(sorted(unmapped)),
    )


# --------------------------------------------------------------------------- #
# The client
# --------------------------------------------------------------------------- #


class NaverSearchAdClient:
    """Calls ``/keywordstool``, or explains why it did not.

    With no credential the client is ``DISABLED_NO_CREDENTIAL`` and **never opens a
    connection** — the check happens before the request is built, so a misconfigured
    deployment cannot produce a stream of 401s against Naver.
    """

    def __init__(
        self,
        *,
        credentials: SearchAdCredentials | None,
        transport: httpx.BaseTransport | None = None,
        base_url: str = SEARCHAD_BASE_URL,
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
        self._clock = clock
        self._timeout = timeout_seconds
        self._max_response_bytes = max_response_bytes
        self._caller = ResilientCaller(
            policy=policy or RetryPolicy(),
            breaker=breaker or CircuitBreaker(),
            sleep=sleep,
            now=clock,
        )

    def __repr__(self) -> str:
        return f"<NaverSearchAdClient state={self.state.value}>"

    @property
    def state(self) -> ProviderState:
        if self._credentials is None:
            return ProviderState.DISABLED_NO_CREDENTIAL
        return self._caller.breaker.provider_state()

    def lookup(self, keywords: Sequence[str]) -> CallOutcome[SearchAdKeywordResponse]:
        """Look up up to :data:`MAX_KEYWORDS_PER_CALL` keywords.

        Never raises for a provider problem. The outcome either carries a response or
        carries ``UNKNOWN`` with a stated reason.
        """
        credentials = self._credentials
        if credentials is None:
            return self._disabled()

        hints = [keyword.strip() for keyword in keywords if keyword.strip()]
        if not hints:
            raise ValueError("at least one keyword is required")
        if len(hints) > MAX_KEYWORDS_PER_CALL:
            raise ValueError(
                f"the API accepts at most {MAX_KEYWORDS_PER_CALL} hint keywords per call"
            )

        def operation() -> SearchAdKeywordResponse:
            collected_at = self._clock()
            body = self._request(credentials, hints)
            payload = _parse_json(body)
            return normalize_keywordstool(payload, collected_at=collected_at, raw_bytes=body)

        return self._caller.call(operation)

    # ------------------------------------------------------------- internals

    def _disabled(self) -> CallOutcome[SearchAdKeywordResponse]:
        return CallOutcome(
            value=UNKNOWN,
            failure=ProviderFailure.from_error(
                NaverCredentialMissingError("no Search Ad credential"),
                occurred_at=self._clock(),
            ),
            attempts=0,
        )

    def _request(self, credentials: SearchAdCredentials, hints: Sequence[str]) -> bytes:
        timestamp_ms = int(self._clock().timestamp() * 1000)
        headers = build_headers(
            credentials=credentials,
            timestamp_ms=timestamp_ms,
            method="GET",
            path=KEYWORDSTOOL_PATH,
        )

        with httpx.Client(
            transport=self._transport,
            timeout=httpx.Timeout(self._timeout),
            follow_redirects=False,
            cookies=None,
        ) as client:
            request = client.build_request(
                "GET",
                f"{self._base_url}{KEYWORDSTOOL_PATH}",
                params={"hintKeywords": ",".join(hints), "showDetail": "1"},
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
                return _read_capped(response, self._max_response_bytes)
            except httpx.HTTPError as exc:
                raise classify_transport_exception(exc) from None
            finally:
                response.close()


def _read_capped(response: httpx.Response, max_bytes: int) -> bytes:
    """Read a response body under a byte ceiling.

    The ceiling is enforced while the body arrives, not after, so an oversized answer is
    refused rather than buffered. A test double built from a bytes literal is already
    materialised; that path still charges the whole body against the same ceiling.
    """
    chunks: list[bytes] = []
    total = 0
    try:
        for chunk in response.iter_bytes():
            total += len(chunk)
            if total > max_bytes:
                raise NaverResponseTooLargeError(f"over {max_bytes} bytes")
            chunks.append(chunk)
    except httpx.StreamConsumed:
        body = response.content
        if len(body) > max_bytes:
            raise NaverResponseTooLargeError(f"over {max_bytes} bytes") from None
        return body
    return b"".join(chunks)


def _parse_json(body: bytes) -> Mapping[str, Any]:
    try:
        payload = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, ValueError) as exc:
        raise NaverSchemaError(f"body is not JSON: {type(exc).__name__}") from None
    if not isinstance(payload, dict):
        raise NaverSchemaError("body is not a JSON object")
    return payload
