"""Naver DataLab — a relative interest index, and nothing that resembles a count.

A DataLab ``ratio`` is scaled so that the largest point in the requested window is 100.
Change the window and every number changes. It cannot be compared across two queries, it
cannot be summed, and it is not a quantity of searches — which is why it lives in
``keyword_trends`` rather than beside the counts in ``keyword_metrics``.

The separation is enforced by construction rather than by convention:

* :class:`RelativeIndex` is its own type with no ``__int__``, ``__float__``, ``__index__``
  or arithmetic, so it cannot be coerced into a number by accident.
* This module does not import :mod:`veo.providers.naver.searchad`, and that module does
  not import this one. A test asserts both directions.
* Nothing here carries a field name containing "searches", "volume" or "clicks", so a
  careless ``getattr`` cannot find one.

**Unverified.** VEO has no DataLab credential. The request and response shapes below
follow the documented API; none has been checked against a live response. See
``keywords/INTEGRATION_REQUEST.md``.
"""

from __future__ import annotations

import json
import time
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime
from typing import Any, Final, Literal, final

import httpx
from pydantic import SecretStr

from veo.common.http import read_capped
from veo.contracts.enums import DataSource, ProviderState
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
    parse_json_object,
)

__all__ = [
    "API_VERSION",
    "DATALAB_BASE_URL",
    "DATALAB_PATH",
    "INDEX_BASIS_NOTE_KO",
    "INDEX_MAXIMUM",
    "INDEX_MINIMUM",
    "RELATIVE_INDEX_UNIT",
    "DataLabCredentials",
    "KeywordTrendSeries",
    "NaverDataLabClient",
    "RelativeIndex",
    "TrendPoint",
    "normalize_datalab",
]

DATALAB_BASE_URL: Final = "https://openapi.naver.com"
DATALAB_PATH: Final = "/v1/datalab/search"

#: Kept within ``VARCHAR(32)``, matching the Search Ad adapter's convention.
API_VERSION: Final = "datalab.search.map.v1"

#: The unit string that travels with every series into the API response. It exists so a
#: front end cannot render the value without also having been told what it is.
RELATIVE_INDEX_UNIT: Final = "RELATIVE_INDEX_0_100"

INDEX_MINIMUM: Final = 0.0
INDEX_MAXIMUM: Final = 100.0

INDEX_BASIS_NOTE_KO: Final = (
    "요청한 기간 안에서 가장 큰 값을 100으로 놓고 환산한 상대 관심도 지수입니다. "
    "검색량(검색 횟수)이 아니며, 기간이 달라지면 같은 키워드라도 값이 달라집니다. "
    "다른 조회 결과의 지수와 직접 비교하거나 더할 수 없습니다."
)

DEFAULT_TIMEOUT_SECONDS: Final = 10.0
DEFAULT_MAX_RESPONSE_BYTES: Final = 4 * 1024 * 1024

type TimeUnit = Literal["date", "week", "month"]
type Device = Literal["ALL", "PC", "MOBILE"]

#: VEO's device vocabulary to the provider's. ``ALL`` is the empty string in the API.
_DEVICE_PARAMETER: Final[Mapping[str, str]] = {"ALL": "", "PC": "pc", "MOBILE": "mo"}


@final
@dataclass(frozen=True, slots=True)
class DataLabCredentials:
    """An Open API client id and secret. Both wrapped, both used once, per request."""

    client_id: SecretStr
    client_secret: SecretStr


@final
@dataclass(frozen=True, slots=True)
class RelativeIndex:
    """A relative interest value between 0 and 100. **Not** a number of searches.

    Deliberately not a subclass of ``float`` and deliberately without any numeric
    protocol. ``int(index)`` and ``index + 1`` both raise, which is the point: the way a
    0-100 index becomes a "monthly search volume" in a report is one careless coercion,
    and there is no warning when it happens.
    """

    value: float
    source: DataSource = DataSource.NAVER_DATALAB

    def __post_init__(self) -> None:
        if not INDEX_MINIMUM <= self.value <= INDEX_MAXIMUM:
            raise ValueError(
                f"a relative interest index must be between {INDEX_MINIMUM} and "
                f"{INDEX_MAXIMUM}; got {self.value}"
            )

    @property
    def unit(self) -> str:
        return RELATIVE_INDEX_UNIT


@final
@dataclass(frozen=True, slots=True)
class TrendPoint:
    """One period's relative interest."""

    period_start: date
    relative_index: RelativeIndex


@final
@dataclass(frozen=True, slots=True)
class KeywordTrendSeries:
    """One keyword group's relative interest over the requested window."""

    keyword: str
    group_title: str
    grouped_keywords: tuple[str, ...]
    time_unit: str
    device: str
    period_start: date
    period_end: date
    points: tuple[TrendPoint, ...]
    collected_at: datetime
    api_version: str = API_VERSION
    source: DataSource = DataSource.NAVER_DATALAB
    index_basis_note_ko: str = INDEX_BASIS_NOTE_KO
    unit: str = RELATIVE_INDEX_UNIT


def _parse_date(value: Any, *, where: str) -> date:
    if not isinstance(value, str):
        raise NaverSchemaError(f"{where} is not a date string")
    try:
        return date.fromisoformat(value.strip())
    except ValueError:
        raise NaverSchemaError(f"{where} is not an ISO date") from None


def normalize_datalab(
    payload: Mapping[str, Any], *, collected_at: datetime, device: str
) -> tuple[KeywordTrendSeries, ...]:
    """Map a ``/v1/datalab/search`` payload into trend series.

    Anything unexpected raises :class:`~veo.providers.naver.errors.NaverSchemaError`. In
    particular a ratio outside 0-100 is refused rather than clamped: a value outside the
    documented range means the response no longer means what VEO thinks it means, and
    clamping it would hide that behind a plausible number.
    """
    groups = payload.get("results")
    if not isinstance(groups, list) or not groups:
        raise NaverSchemaError("response has no results array")

    period_start = _parse_date(payload.get("startDate"), where="startDate")
    period_end = _parse_date(payload.get("endDate"), where="endDate")
    time_unit = payload.get("timeUnit")
    if not isinstance(time_unit, str) or not time_unit:
        raise NaverSchemaError("response has no timeUnit")

    series: list[KeywordTrendSeries] = []
    for index, group in enumerate(groups):
        if not isinstance(group, dict):
            raise NaverSchemaError(f"results[{index}] is not an object")

        keywords = group.get("keywords")
        if not isinstance(keywords, list) or not keywords:
            raise NaverSchemaError(f"results[{index}] has no keywords")
        grouped = tuple(str(keyword) for keyword in keywords)

        rows = group.get("data")
        if not isinstance(rows, list):
            raise NaverSchemaError(f"results[{index}] has no data array")

        points: list[TrendPoint] = []
        for row_index, row in enumerate(rows):
            if not isinstance(row, dict):
                raise NaverSchemaError(f"results[{index}].data[{row_index}] is not an object")
            ratio = row.get("ratio")
            if isinstance(ratio, bool) or not isinstance(ratio, int | float):
                raise NaverSchemaError(f"results[{index}].data[{row_index}] has no ratio")
            try:
                relative_index = RelativeIndex(float(ratio))
            except ValueError as exc:
                raise NaverSchemaError(str(exc)) from None
            points.append(
                TrendPoint(
                    period_start=_parse_date(
                        row.get("period"), where=f"results[{index}].data[{row_index}].period"
                    ),
                    relative_index=relative_index,
                )
            )

        title = group.get("title")
        series.append(
            KeywordTrendSeries(
                keyword=grouped[0],
                group_title=title if isinstance(title, str) else grouped[0],
                grouped_keywords=grouped,
                time_unit=time_unit,
                device=device,
                period_start=period_start,
                period_end=period_end,
                points=tuple(points),
                collected_at=collected_at,
            )
        )

    return tuple(series)


class NaverDataLabClient:
    """Calls the DataLab search trend endpoint, or explains why it did not."""

    def __init__(
        self,
        *,
        credentials: DataLabCredentials | None,
        transport: httpx.BaseTransport | None = None,
        base_url: str = DATALAB_BASE_URL,
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
        return f"<NaverDataLabClient state={self.state.value}>"

    @property
    def state(self) -> ProviderState:
        if self._credentials is None:
            return ProviderState.DISABLED_NO_CREDENTIAL
        return self._caller.breaker.provider_state()

    def lookup_trend(
        self,
        keywords: Sequence[str],
        *,
        start_date: date,
        end_date: date,
        time_unit: TimeUnit = "month",
        device: Device = "ALL",
    ) -> CallOutcome[tuple[KeywordTrendSeries, ...]]:
        credentials = self._credentials
        if credentials is None:
            return CallOutcome(
                value=UNKNOWN,
                failure=ProviderFailure.from_error(
                    NaverCredentialMissingError("no DataLab credential"),
                    occurred_at=self._clock(),
                ),
                attempts=0,
            )

        cleaned = [keyword.strip() for keyword in keywords if keyword.strip()]
        if not cleaned:
            raise ValueError("at least one keyword is required")
        if start_date > end_date:
            raise ValueError("start_date must not be after end_date")

        def operation() -> tuple[KeywordTrendSeries, ...]:
            collected_at = self._clock()
            body = self._request(credentials, cleaned, start_date, end_date, time_unit, device)
            payload = parse_json_object(body)
            return normalize_datalab(payload, collected_at=collected_at, device=device)

        return self._caller.call(operation)

    # ------------------------------------------------------------- internals

    def _request(
        self,
        credentials: DataLabCredentials,
        keywords: Sequence[str],
        start_date: date,
        end_date: date,
        time_unit: str,
        device: str,
    ) -> bytes:
        payload: dict[str, Any] = {
            "startDate": start_date.isoformat(),
            "endDate": end_date.isoformat(),
            "timeUnit": time_unit,
            "keywordGroups": [
                {"groupName": keyword, "keywords": [keyword]} for keyword in keywords
            ],
        }
        parameter = _DEVICE_PARAMETER.get(device, "")
        if parameter:
            payload["device"] = parameter

        headers = {
            "X-Naver-Client-Id": credentials.client_id.get_secret_value(),
            "X-Naver-Client-Secret": credentials.client_secret.get_secret_value(),
            "Content-Type": "application/json",
        }

        with httpx.Client(
            transport=self._transport,
            timeout=httpx.Timeout(self._timeout),
            follow_redirects=False,
            cookies=None,
        ) as client:
            request = client.build_request(
                "POST",
                f"{self._base_url}{DATALAB_PATH}",
                content=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
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



