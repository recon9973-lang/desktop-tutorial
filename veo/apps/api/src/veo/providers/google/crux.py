"""The Chrome UX Report — field data, and the one label the record API does not publish.

This module owns VEO's entire vocabulary for **field** measurements: values aggregated
from real Chrome users over a 28-day window. :mod:`veo.providers.google.pagespeed` imports
these types to describe the field block it receives; nothing here imports lab types back.
That one-way edge is what makes it structurally impossible for a Lighthouse simulation to
be stored in a field-shaped structure.

Two facts drive every design decision below.

**A URL with no sample is ``NOT_APPLICABLE``, never zero.** CrUX only publishes an origin
or URL that has enough real visitors to anonymise. Most pages on most Korean clinic sites
do not, and reporting that as a score of zero would tell a customer their site is slow
when what actually happened is that too few people visited it to measure. The record API
answers ``404`` for exactly this case, and VEO reads that ``404`` as data.

**CrUX is reachable independently, but only PageSpeed publishes the category.** See
:data:`CATEGORY_ACCESS_KO`. The record API returns percentiles and histogram densities;
the ``FAST``/``AVERAGE``/``SLOW`` label VEO reports comes from PageSpeed's
``loadingExperience`` block. VEO does not derive the label from a percentile and a
threshold of its own choosing: the resulting word would read, to a customer, as Google's
verdict while being VEO's.
"""

from __future__ import annotations

import hashlib
import time
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, Final, final
from urllib.parse import urlsplit

import httpx

from veo.contracts.enums import DataSource, ProviderState, ValueQuality
from veo.providers.google.credentials import PageSpeedCredentials
from veo.providers.google.errors import (
    UNKNOWN,
    CallOutcome,
    GoogleCircuitBreaker,
    GoogleCredentialInvalidError,
    GoogleCredentialMissingError,
    GoogleSchemaError,
    ProviderFailure,
    ResilientCaller,
    RetryPolicy,
)
from veo.providers.google.http import (
    API_KEY_HEADER,
    DEFAULT_MAX_RESPONSE_BYTES,
    DEFAULT_TIMEOUT_SECONDS,
    GoogleHttpCaller,
)

__all__ = [
    "API_VERSION",
    "CATEGORY_ACCESS_KO",
    "CRUX_BASE_URL",
    "FIELD_CATEGORIES",
    "INP_METRIC",
    "NO_SAMPLE_KO",
    "QUERY_RECORD_PATH",
    "CruxClient",
    "FieldDataState",
    "FieldMeasurement",
    "FieldMetric",
    "FieldScope",
    "field_payload",
    "normalize_loading_experience",
    "normalize_query_record",
    "not_applicable",
]

CRUX_BASE_URL: Final = "https://chromeuxreport.googleapis.com"
QUERY_RECORD_PATH: Final = "/v1/records:queryRecord"

#: VEO's label for *this mapping*, not a version Google publishes. It changes when the
#: field mapping below changes, so a stored measurement can be read back with the rules
#: that produced it.
API_VERSION: Final = "google.crux.v1.map.v1"

#: The metric ``seo.perf.inp_field`` reads. Named in PageSpeed's spelling, which is the
#: vocabulary the SEO collector already uses.
INP_METRIC: Final = "INTERACTION_TO_NEXT_PAINT"

#: Google's own published buckets. VEO reports these words; it does not compute them.
FIELD_CATEGORIES: Final = frozenset({"FAST", "AVERAGE", "SLOW"})

#: **The one place this is written down.** Referenced from the module docstring, from
#: ``pagespeed.py`` and from ``INTEGRATION_REQUEST.md`` §4 rather than paraphrased.
CATEGORY_ACCESS_KO: Final = (
    "CrUX(실제 사용자 데이터)는 두 경로로 제공되며 두 경로가 주는 값이 다릅니다. "
    "PageSpeed Insights 응답의 loadingExperience 블록은 Google이 직접 판정한 "
    "FAST/AVERAGE/SLOW 구간을 함께 내려주지만, 단독 CrUX 기록 API(records:queryRecord)는 "
    "백분위수와 히스토그램만 내려주고 구간 라벨은 내려주지 않습니다. "
    "VEO가 보고하는 구간은 전자에서 온 값이며, 후자의 백분위수를 VEO가 정한 기준선에 대어 "
    "구간을 만들어 내지 않습니다. 그렇게 만든 단어는 고객에게 Google의 판정처럼 읽히지만 "
    "실제로는 VEO의 판단이기 때문입니다."
)

NO_SAMPLE_KO: Final = (
    "이 URL에는 CrUX 표본이 없습니다. 실제 방문자 수가 공개 기준에 미치지 않아 field 값이 "
    "존재하지 않는 것이며, 사이트가 느리다는 뜻이 아닙니다. 방문자 표본이 쌓이면 자동으로 "
    "평가 대상이 됩니다."
)

NO_CATEGORY_KO: Final = (
    "기록 API 응답에는 Google이 판정한 구간(FAST/AVERAGE/SLOW)이 들어 있지 않아 구간은 "
    "'측정 불가'로 둡니다. 백분위수는 그대로 보존합니다."
)

#: The record API answers in snake_case; PageSpeed answers in SCREAMING_CASE with a unit
#: suffix. VEO speaks PageSpeed's dialect because that is what the SEO collectors read.
_RECORD_METRIC_NAMES: Final = {
    "interaction_to_next_paint": INP_METRIC,
    "largest_contentful_paint": "LARGEST_CONTENTFUL_PAINT_MS",
    "cumulative_layout_shift": "CUMULATIVE_LAYOUT_SHIFT_SCORE",
    "first_contentful_paint": "FIRST_CONTENTFUL_PAINT_MS",
    "first_input_delay": "FIRST_INPUT_DELAY_MS",
    "experimental_time_to_first_byte": "EXPERIMENTAL_TIME_TO_FIRST_BYTE",
}


class FieldScope(StrEnum):
    """Whether a measurement describes one URL or a whole origin.

    Not interchangeable. An origin's numbers are dominated by its most-visited pages, so
    reporting an origin figure against a specific URL flatters or damns that URL with
    traffic it never had.
    """

    URL = "URL"
    ORIGIN = "ORIGIN"


class FieldDataState(StrEnum):
    """Whether field data exists at all for the requested key."""

    AVAILABLE = "AVAILABLE"
    NOT_APPLICABLE = "NOT_APPLICABLE"


@final
@dataclass(frozen=True, slots=True)
class FieldMetric:
    """One field metric: a category, a percentile, and what is known about each.

    ``source`` is fixed to :attr:`~veo.contracts.enums.DataSource.GOOGLE_CRUX` and
    rejected otherwise, so a lab value cannot be dressed as a field one by construction
    rather than by convention.
    """

    metric_id: str
    category: str | None
    category_quality: ValueQuality
    percentile: float | None
    percentile_quality: ValueQuality
    source: DataSource = DataSource.GOOGLE_CRUX
    histogram: tuple[Mapping[str, float], ...] = ()

    def __post_init__(self) -> None:
        if self.source is not DataSource.GOOGLE_CRUX:
            raise ValueError(
                f"a field metric's source must be GOOGLE_CRUX, not {self.source}: field data "
                "and lab data answer different questions and never share a field"
            )
        if self.category is not None and self.category_quality is not ValueQuality.EXACT:
            raise ValueError("a category that exists is EXACT; a quality cannot deny it")
        if self.category is None and self.category_quality is ValueQuality.EXACT:
            raise ValueError("a quality of EXACT claims a category that is not there")
        if self.percentile is not None and self.percentile_quality is not ValueQuality.EXACT:
            raise ValueError("a percentile that exists is EXACT; a quality cannot deny it")

    @property
    def has_provider_category(self) -> bool:
        return self.category is not None


@final
@dataclass(frozen=True, slots=True)
class FieldMeasurement:
    """Everything CrUX said about one key, including that it said nothing."""

    url: str
    scope: FieldScope
    state: FieldDataState
    metrics: Mapping[str, FieldMetric]
    collected_at: datetime
    overall_category: str | None = None
    reason_ko: str | None = None
    source: DataSource = DataSource.GOOGLE_CRUX
    api_version: str = API_VERSION
    raw_response_hash: str | None = None
    unmapped_metrics: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.state is FieldDataState.NOT_APPLICABLE and self.metrics:
            raise ValueError("a NOT_APPLICABLE measurement cannot carry metrics")

    @property
    def categorised_metrics(self) -> dict[str, FieldMetric]:
        return {
            metric_id: metric
            for metric_id, metric in self.metrics.items()
            if metric.has_provider_category
        }

    def as_payload_entry(self) -> dict[str, Any]:
        """The per-URL entry ``seo.perf.inp_field`` reads.

        Only metrics carrying the provider's own category appear under ``metrics``. A
        percentile without a label is preserved on the measurement but withheld from the
        payload — see :data:`CATEGORY_ACCESS_KO`.
        """
        return {
            "metrics": {
                metric_id: {
                    "category": metric.category,
                    "percentile": metric.percentile,
                    "quality": metric.category_quality.value,
                    "source": metric.source.value,
                    "collected_at": self.collected_at.isoformat(),
                }
                for metric_id, metric in self.categorised_metrics.items()
            },
            "state": self.state.value,
            "scope": self.scope.value,
            "overall_category": self.overall_category,
            "reason_ko": self.reason_ko,
            "source": self.source.value,
            "collected_at": self.collected_at.isoformat(),
            "api_version": self.api_version,
        }


def not_applicable(
    *,
    url: str,
    scope: FieldScope,
    collected_at: datetime,
    reason_ko: str = NO_SAMPLE_KO,
) -> FieldMeasurement:
    """A key CrUX has no data for. A fact about traffic, not a fault in the site."""
    return FieldMeasurement(
        url=url,
        scope=scope,
        state=FieldDataState.NOT_APPLICABLE,
        metrics={},
        collected_at=collected_at,
        reason_ko=reason_ko,
    )


def field_payload(measurements: Iterable[FieldMeasurement]) -> dict[str, Any]:
    """Build the ``GOOGLE_CRUX`` provider payload the SEO collector consumes.

    Three cases, and the middle one is the interesting one:

    * ``NOT_APPLICABLE`` — an entry with no metrics, so the check reports NOT_APPLICABLE
      with its "no real-user sample" wording, which is exactly what happened.
    * ``AVAILABLE`` but with no provider category — **omitted entirely**. Presenting it as
      an empty entry would make the check announce "no sample" about a URL that has one.
      The gap is filed as ``INTEGRATION_REQUEST.md`` §4 instead of being papered over.
    * ``AVAILABLE`` with categories — the entry the check was written for.
    """
    payload: dict[str, Any] = {}
    for measurement in measurements:
        if measurement.state is FieldDataState.AVAILABLE and not measurement.categorised_metrics:
            continue
        if measurement.url in payload:
            raise ValueError(
                f"two field measurements for {measurement.url}: merging them would hide "
                "which sample produced which value"
            )
        payload[measurement.url] = measurement.as_payload_entry()
    return payload


# --------------------------------------------------------------------------- #
# Normalisation — PageSpeed's loadingExperience block
# --------------------------------------------------------------------------- #


def normalize_loading_experience(
    block: Mapping[str, Any],
    *,
    url: str,
    scope: FieldScope,
    collected_at: datetime,
) -> FieldMeasurement:
    """Map PageSpeed's ``loadingExperience`` — the surface that carries the category."""
    raw_metrics = block.get("metrics")
    if not isinstance(raw_metrics, Mapping) or not raw_metrics:
        return not_applicable(url=url, scope=scope, collected_at=collected_at)

    metrics: dict[str, FieldMetric] = {}
    for metric_id, raw in raw_metrics.items():
        if not isinstance(raw, Mapping):
            continue
        category = _category(raw.get("category"))
        percentile = _number(raw.get("percentile"))
        metrics[str(metric_id)] = FieldMetric(
            metric_id=str(metric_id),
            category=category,
            category_quality=_quality_of(category),
            percentile=percentile,
            percentile_quality=_quality_of(percentile),
        )

    if not metrics:
        return not_applicable(url=url, scope=scope, collected_at=collected_at)

    return FieldMeasurement(
        url=url,
        scope=scope,
        state=FieldDataState.AVAILABLE,
        metrics=metrics,
        collected_at=collected_at,
        overall_category=_category(block.get("overall_category")),
    )


# --------------------------------------------------------------------------- #
# Normalisation — the standalone record API
# --------------------------------------------------------------------------- #


def normalize_query_record(
    payload: Mapping[str, Any],
    *,
    url: str,
    scope: FieldScope,
    collected_at: datetime,
    raw_bytes: bytes,
) -> FieldMeasurement:
    """Map a ``records:queryRecord`` response.

    Percentiles are carried through; the category is left ``MISSING`` because the record
    API does not publish one and VEO does not manufacture one. :data:`CATEGORY_ACCESS_KO`
    is the reason, written once.
    """
    record = payload.get("record")
    if not isinstance(record, Mapping):
        raise GoogleSchemaError("response has no record object")
    raw_metrics = record.get("metrics")
    if not isinstance(raw_metrics, Mapping):
        raise GoogleSchemaError("record has no metrics object")
    if not raw_metrics:
        return not_applicable(url=url, scope=scope, collected_at=collected_at)

    metrics: dict[str, FieldMetric] = {}
    unmapped: list[str] = []
    for raw_name, raw in raw_metrics.items():
        metric_id = _RECORD_METRIC_NAMES.get(str(raw_name))
        if metric_id is None:
            # A metric VEO has no vocabulary for. Recorded, not silently dropped, and not
            # guessed into an existing name.
            unmapped.append(str(raw_name))
            continue
        if not isinstance(raw, Mapping):
            continue
        percentiles = raw.get("percentiles")
        p75 = _number(percentiles.get("p75")) if isinstance(percentiles, Mapping) else None
        metrics[metric_id] = FieldMetric(
            metric_id=metric_id,
            category=None,
            category_quality=ValueQuality.MISSING,
            percentile=p75,
            percentile_quality=_quality_of(p75),
            histogram=_histogram(raw.get("histogram")),
        )

    if not metrics:
        return not_applicable(url=url, scope=scope, collected_at=collected_at)

    return FieldMeasurement(
        url=url,
        scope=scope,
        state=FieldDataState.AVAILABLE,
        metrics=metrics,
        collected_at=collected_at,
        reason_ko=NO_CATEGORY_KO,
        raw_response_hash=hashlib.sha256(raw_bytes).hexdigest(),
        unmapped_metrics=tuple(sorted(unmapped)),
    )


def _quality_of(value: object | None) -> ValueQuality:
    """``EXACT`` when the provider supplied something, ``MISSING`` when it did not.

    There is no third answer here. A field value either came from CrUX or it is absent —
    nothing in this module rounds, estimates or interpolates.
    """
    return ValueQuality.EXACT if value is not None else ValueQuality.MISSING


def _category(value: Any) -> str | None:
    """Google's own label, or nothing. Never a label VEO chose."""
    if not isinstance(value, str):
        return None
    candidate = value.strip().upper()
    return candidate if candidate in FIELD_CATEGORIES else None


def _number(value: Any) -> float | None:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, int | float):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value.strip())
        except ValueError:
            return None
    return None


def _histogram(value: Any) -> tuple[Mapping[str, float], ...]:
    if not isinstance(value, list):
        return ()
    bins: list[Mapping[str, float]] = []
    for entry in value:
        if not isinstance(entry, Mapping):
            continue
        # The last bin has no ``end`` — it is the open-ended "poor" bucket — so a missing
        # key is expected here and simply does not appear.
        bounds = {key: _number(entry.get(key)) for key in ("start", "end", "density")}
        bins.append({key: bound for key, bound in bounds.items() if bound is not None})
    return tuple(bins)


# --------------------------------------------------------------------------- #
# The client
# --------------------------------------------------------------------------- #


class CruxClient:
    """Queries the CrUX record API, or explains why it did not.

    With no credential the client **never opens a connection** — the state check happens
    before the request is built, so a misconfigured deployment cannot produce a stream of
    401s against Google.
    """

    def __init__(
        self,
        *,
        credentials: PageSpeedCredentials | None,
        unavailable_state: ProviderState = ProviderState.DISABLED_NO_CREDENTIAL,
        transport: httpx.BaseTransport | None = None,
        base_url: str = CRUX_BASE_URL,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
        sleep: Callable[[float], None] = time.sleep,
        policy: RetryPolicy | None = None,
        breaker: GoogleCircuitBreaker | None = None,
        timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
        max_response_bytes: int = DEFAULT_MAX_RESPONSE_BYTES,
    ) -> None:
        if credentials is not None and (
            unavailable_state is not ProviderState.DISABLED_NO_CREDENTIAL
        ):
            raise ValueError("unavailable_state describes the absence of a credential")
        self._credentials = credentials
        self._unavailable_state = unavailable_state
        self._base_url = base_url.rstrip("/")
        self._clock = clock
        self._http = GoogleHttpCaller(
            transport=transport,
            timeout_seconds=timeout_seconds,
            max_response_bytes=max_response_bytes,
        )
        self._caller = ResilientCaller(
            policy=policy or RetryPolicy(),
            breaker=breaker or GoogleCircuitBreaker(),
            sleep=sleep,
            now=clock,
        )

    def __repr__(self) -> str:
        return f"<CruxClient state={self.state.value}>"

    @property
    def state(self) -> ProviderState:
        if self._credentials is None:
            return self._unavailable_state
        return self._caller.breaker.provider_state()

    def query_record(
        self, url: str, *, scope: FieldScope = FieldScope.URL
    ) -> CallOutcome[FieldMeasurement]:
        """Ask CrUX about one URL or one origin.

        A ``404`` is not a failure here: it is CrUX saying the key has too few real-user
        samples to publish, which is a measurement outcome of its own.
        """
        credentials = self._credentials
        if credentials is None:
            return self._disabled()

        def operation() -> FieldMeasurement:
            collected_at = self._clock()
            key = _origin_of(url) if scope is FieldScope.ORIGIN else url
            answer = self._http.request(
                "POST",
                f"{self._base_url}{QUERY_RECORD_PATH}",
                headers={API_KEY_HEADER: credentials.api_key.get_secret_value()},
                json_body={"origin" if scope is FieldScope.ORIGIN else "url": key},
                accept_statuses=(200, 404),
            )
            if answer.status_code == 404:
                return not_applicable(url=url, scope=scope, collected_at=collected_at)
            return normalize_query_record(
                answer.json_object(),
                url=url,
                scope=scope,
                collected_at=collected_at,
                raw_bytes=answer.body,
            )

        return self._caller.call(operation)

    def _disabled(self) -> CallOutcome[FieldMeasurement]:
        error = (
            GoogleCredentialInvalidError("CrUX credential is a placeholder")
            if self._unavailable_state is ProviderState.DISABLED_INVALID_CREDENTIAL
            else GoogleCredentialMissingError("no Google API key for CrUX")
        )
        return CallOutcome(
            value=UNKNOWN,
            failure=ProviderFailure.from_error(error, occurred_at=self._clock()),
            attempts=0,
        )


def _origin_of(url: str) -> str:
    parts = urlsplit(url)
    if not parts.scheme or not parts.netloc:
        raise ValueError(f"cannot derive an origin from {url!r}")
    return f"{parts.scheme}://{parts.netloc}"
