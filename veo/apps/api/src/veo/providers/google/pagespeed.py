"""PageSpeed Insights — a lab simulation, and the field block that rides along with it.

One call to ``runPagespeed`` returns two things that look similar and mean entirely
different things:

* ``lighthouseResult`` — a **lab** run. Chrome, throttled to a network profile Google
  chose, on the form factor VEO asked for. Reproducible, comparable between runs, and a
  simulation. It answers *"what would a visitor on this kind of connection experience?"*
* ``loadingExperience`` — a **field** block from the Chrome UX Report. Real visitors, 28
  days, published only when there are enough of them. It answers *"what did visitors
  actually experience?"*

VEO keeps them in two different types, from two different modules, carrying two different
:class:`~veo.contracts.enums.DataSource` values, and :func:`lab_payload` and
:func:`~veo.providers.google.crux.field_payload` build two different provider payloads for
two different checks. The SEO specification already made this distinction by giving
``seo.perf.*_lab`` and ``seo.perf.inp_field`` separate check ids; this module is where the
distinction is made impossible to erase by accident.

**The strategy is part of the measurement.** A mobile LCP and a desktop LCP of the same
URL are two measurements, not two readings of one. The strategy is recorded on the
measurement and on every audit inside it, so a stored figure can never be compared against
one taken on the other form factor without that being visible.

**Verified against live responses** on 2026-08-01 (Lighthouse 13.4.1, mobile). Every field
name below was read from a real ``runPagespeed`` payload: ``lighthouseResult.audits``
carried all four lab audits with the expected ``numericValue``/``numericUnit``/
``displayValue`` shape, and ``loadingExperience`` carried five CrUX metrics with
``unmapped_metrics`` empty — nothing in the response was left unexplained. The names had
been inferred from documentation until then; ``INTEGRATION_REQUEST`` §A records what was
inferred and is now confirmed.

The mapping was also checked against Google's own web UI for the same URL, which is the
check that matters: VEO reported a performance score of 60 and "no field sample" for
``chamsarang1075.com``, and the PageSpeed Insights page reported 60 and 데이터 없음.

Three things the live calls showed that the documentation does not:

* **A cold measurement takes far longer than any other Google call here** — see
  :data:`PAGESPEED_TIMEOUT_SECONDS`, which exists because of it.
* **Repeat calls to the same URL are served from Google's cache**, in ~0.3s, with an
  identical score. Two *cold* runs of one URL, by contrast, returned 0.64 and 0.83. The
  lab run is a simulation on shared infrastructure and it moves; a single reading is one
  draw, not the site's speed. Anything built on these numbers — a score, a trend line, a
  regression alarm — has to survive that spread, and must not mistake a cached repeat for
  a confirming second opinion.
* **A rejected key arrives as 400, not 401**, with ``details[].reason ==
  "API_KEY_INVALID"``. So does a target site Lighthouse could not load
  (``FAILED_DOCUMENT_REQUEST``). Two unrelated causes, one status, and
  :func:`~veo.providers.google.errors.classify_status` currently calls both a schema
  surprise — see the open item in the task list.
"""

from __future__ import annotations

import hashlib
import time
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, Final, final

import httpx

from veo.contracts.enums import DataSource, ProviderState, ValueQuality
from veo.providers.google.credentials import PageSpeedCredentials
from veo.providers.google.crux import (
    FieldMeasurement,
    FieldScope,
    normalize_loading_experience,
    not_applicable,
)
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
    GoogleHttpCaller,
)

__all__ = [
    "API_VERSION",
    "LAB_AUDIT_IDS",
    "PAGESPEED_BASE_URL",
    "PAGESPEED_TIMEOUT_SECONDS",
    "RUNPAGESPEED_PATH",
    "LabAudit",
    "LabMeasurement",
    "PageSpeedClient",
    "PageSpeedResult",
    "Strategy",
    "lab_payload",
    "normalize_runpagespeed",
]

PAGESPEED_BASE_URL: Final = "https://pagespeedonline.googleapis.com"
RUNPAGESPEED_PATH: Final = "/pagespeedonline/v5/runPagespeed"

#: VEO's label for *this mapping*, not a version Google publishes.
API_VERSION: Final = "google.pagespeed.v5.map.v1"

#: PageSpeed does not answer a question — it *runs Lighthouse* and answers when it is done.
#:
#: That makes it unlike every other call in this package, and the shared
#: :data:`~veo.providers.google.http.DEFAULT_TIMEOUT_SECONDS` (15s) is far too short for
#: it. Four cold measurements on 2026-08-01 took **16.0s, 24.1s, 28.3s and 59.8s** — every
#: one of them over the shared default.
#:
#: The failure this prevents is the worst kind, because it hides. Google serves a repeat
#: measurement of the same URL from cache in ~0.3s, so a URL measured once during
#: development answers instantly forever after. The timeout is only ever hit by a URL
#: nobody has measured yet — which is precisely every customer's site, on their first scan.
PAGESPEED_TIMEOUT_SECONDS: Final = 120.0

#: The four Lighthouse audits VEO reads. LCP, CLS and TBT back the three ``*_lab`` checks;
#: FCP is collected because it is the first thing an operator asks about when LCP is bad,
#: and asking for it costs nothing once the response has arrived.
LAB_AUDIT_IDS: Final = (
    "largest-contentful-paint",
    "cumulative-layout-shift",
    "total-blocking-time",
    "first-contentful-paint",
)

#: Only the performance category is requested. The others (accessibility, SEO, best
#: practices) would multiply the response size for audits VEO scores itself, from its own
#: published specification, against its own evidence.
_CATEGORY: Final = "PERFORMANCE"


class Strategy(StrEnum):
    """The form factor a lab run simulates. Part of the measurement, never a default."""

    MOBILE = "MOBILE"
    DESKTOP = "DESKTOP"


@final
@dataclass(frozen=True, slots=True)
class LabAudit:
    """One Lighthouse audit result.

    ``score`` is Lighthouse's own normalised 0-to-1 figure, kept exactly as sent; the
    pass/average bands belong to Lighthouse and VEO reports its verdict rather than
    re-deriving one from milliseconds against a threshold of VEO's invention.

    ``source`` is fixed to ``GOOGLE_PAGESPEED`` and rejected otherwise, which is what
    makes "lab and field never merge" a property of the type rather than of the reviewer's
    attention span.
    """

    audit_id: str
    score: float | None
    display_value: str | None
    numeric_value: float | None
    numeric_unit: str | None
    quality: ValueQuality
    source: DataSource = DataSource.GOOGLE_PAGESPEED

    def __post_init__(self) -> None:
        if self.source is not DataSource.GOOGLE_PAGESPEED:
            raise ValueError(
                f"a lab audit's source must be GOOGLE_PAGESPEED, not {self.source}: a lab "
                "simulation and a field measurement are not interchangeable"
            )
        if self.score is None and self.quality is ValueQuality.EXACT:
            raise ValueError("a quality of EXACT claims a score that is not there")
        if self.score is not None and self.quality is ValueQuality.MISSING:
            raise ValueError("a quality of MISSING denies a score that is there")

    @property
    def is_measured(self) -> bool:
        return self.score is not None


@final
@dataclass(frozen=True, slots=True)
class LabMeasurement:
    """One Lighthouse run of one URL on one form factor."""

    url: str
    strategy: Strategy
    audits: Mapping[str, LabAudit]
    collected_at: datetime
    lighthouse_version: str | None = None
    performance_score: float | None = None
    analysis_timestamp: str | None = None
    source: DataSource = DataSource.GOOGLE_PAGESPEED
    api_version: str = API_VERSION
    raw_response_hash: str | None = None

    def as_payload_entry(self) -> dict[str, Any]:
        """The per-URL entry the three ``seo.perf.*_lab`` checks read.

        Each audit carries its own source, collection time, quality and strategy — not
        just the entry as a whole. The checks copy an audit dict into their evidence
        record, and an audit that travels without its provenance arrives somewhere it can
        be mistaken for a VEO-derived number.
        """
        return {
            "lighthouse": {
                audit_id: {
                    "score": audit.score,
                    "display_value": audit.display_value,
                    "numeric_value": audit.numeric_value,
                    "numeric_unit": audit.numeric_unit,
                    "quality": audit.quality.value,
                    "strategy": self.strategy.value,
                    "source": audit.source.value,
                    "collected_at": self.collected_at.isoformat(),
                }
                for audit_id, audit in self.audits.items()
            },
            "strategy": self.strategy.value,
            "lighthouse_version": self.lighthouse_version,
            "performance_score": self.performance_score,
            "source": self.source.value,
            "collected_at": self.collected_at.isoformat(),
            "api_version": self.api_version,
        }


@final
@dataclass(frozen=True, slots=True)
class PageSpeedResult:
    """One ``runPagespeed`` response, split into the two things it actually contains.

    Two attributes of two different types from two different modules. There is no combined
    accessor and no ``metrics`` property that returns both, because the first convenience
    method that merged them would be the last day the distinction survived.
    """

    lab: LabMeasurement
    field: FieldMeasurement


def lab_payload(measurements: Iterable[LabMeasurement]) -> dict[str, Any]:
    """Build the ``GOOGLE_PAGESPEED`` provider payload the SEO collectors consume."""
    payload: dict[str, Any] = {}
    for measurement in measurements:
        if measurement.url in payload:
            raise ValueError(
                f"two lab measurements for {measurement.url}: mobile and desktop are "
                "different measurements and one may not overwrite the other"
            )
        payload[measurement.url] = measurement.as_payload_entry()
    return payload


def normalize_runpagespeed(
    payload: Mapping[str, Any],
    *,
    url: str,
    strategy: Strategy,
    collected_at: datetime,
    raw_bytes: bytes,
) -> PageSpeedResult:
    """Map a ``runPagespeed`` payload into VEO's vocabulary.

    Raises :class:`~veo.providers.google.errors.GoogleSchemaError` when the payload is not
    the documented shape. Mapping what looks close and defaulting the rest produces a
    response full of zeroes that nobody can tell from measurements.
    """
    lighthouse = payload.get("lighthouseResult")
    if not isinstance(lighthouse, Mapping):
        raise GoogleSchemaError("response has no lighthouseResult object")
    raw_audits = lighthouse.get("audits")
    if not isinstance(raw_audits, Mapping):
        raise GoogleSchemaError("lighthouseResult has no audits object")

    audits = {audit_id: _audit(raw_audits, audit_id) for audit_id in LAB_AUDIT_IDS}

    lab = LabMeasurement(
        url=url,
        strategy=strategy,
        audits=audits,
        collected_at=collected_at,
        lighthouse_version=_text(lighthouse.get("lighthouseVersion")),
        performance_score=_performance_score(lighthouse),
        analysis_timestamp=_text(payload.get("analysisUTCTimestamp")),
        raw_response_hash=hashlib.sha256(raw_bytes).hexdigest(),
    )

    experience = payload.get("loadingExperience")
    if isinstance(experience, Mapping):
        measurement = normalize_loading_experience(
            experience, url=url, scope=FieldScope.URL, collected_at=collected_at
        )
    else:
        # No block at all is the ordinary case for a page with modest traffic. It is a
        # statement about visitor numbers, not about the page.
        measurement = not_applicable(url=url, scope=FieldScope.URL, collected_at=collected_at)

    return PageSpeedResult(lab=lab, field=measurement)


def _audit(raw_audits: Mapping[str, Any], audit_id: str) -> LabAudit:
    raw = raw_audits.get(audit_id)
    if not isinstance(raw, Mapping):
        # Absent because the run did not produce it. Not a zero — a zero score in
        # Lighthouse means "as bad as this metric gets".
        return _missing_audit(audit_id)

    score = _number(raw.get("score"))
    if score is None:
        # ``scoreDisplayMode`` of ``notApplicable``/``informative``/``error`` all land
        # here. Lighthouse declined to score it; VEO does not score it either.
        return _missing_audit(audit_id, display_value=_text(raw.get("displayValue")))

    return LabAudit(
        audit_id=audit_id,
        score=score,
        display_value=_text(raw.get("displayValue")),
        numeric_value=_number(raw.get("numericValue")),
        numeric_unit=_text(raw.get("numericUnit")),
        quality=ValueQuality.EXACT,
    )


def _missing_audit(audit_id: str, *, display_value: str | None = None) -> LabAudit:
    return LabAudit(
        audit_id=audit_id,
        score=None,
        display_value=display_value,
        numeric_value=None,
        numeric_unit=None,
        quality=ValueQuality.MISSING,
    )


def _performance_score(lighthouse: Mapping[str, Any]) -> float | None:
    categories = lighthouse.get("categories")
    if not isinstance(categories, Mapping):
        return None
    performance = categories.get("performance")
    if not isinstance(performance, Mapping):
        return None
    return _number(performance.get("score"))


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


def _text(value: Any) -> str | None:
    return value if isinstance(value, str) and value.strip() else None


# --------------------------------------------------------------------------- #
# The client
# --------------------------------------------------------------------------- #


class PageSpeedClient:
    """Runs one PageSpeed measurement, or explains why it did not.

    With no credential the client **never opens a connection**: the state check happens
    before the request is built, so a deployment that was never configured cannot produce
    a stream of failures against Google — or a bill.
    """

    def __init__(
        self,
        *,
        credentials: PageSpeedCredentials | None,
        unavailable_state: ProviderState = ProviderState.DISABLED_NO_CREDENTIAL,
        transport: httpx.BaseTransport | None = None,
        base_url: str = PAGESPEED_BASE_URL,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
        sleep: Callable[[float], None] = time.sleep,
        policy: RetryPolicy | None = None,
        breaker: GoogleCircuitBreaker | None = None,
        timeout_seconds: float = PAGESPEED_TIMEOUT_SECONDS,
        max_response_bytes: int = DEFAULT_MAX_RESPONSE_BYTES,
        locale: str = "ko",
    ) -> None:
        if credentials is not None and (
            unavailable_state is not ProviderState.DISABLED_NO_CREDENTIAL
        ):
            raise ValueError("unavailable_state describes the absence of a credential")
        self._credentials = credentials
        self._unavailable_state = unavailable_state
        self._base_url = base_url.rstrip("/")
        self._clock = clock
        self._locale = locale
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
        return f"<PageSpeedClient state={self.state.value}>"

    @property
    def state(self) -> ProviderState:
        if self._credentials is None:
            return self._unavailable_state
        return self._caller.breaker.provider_state()

    def measure(
        self, url: str, *, strategy: Strategy = Strategy.MOBILE
    ) -> CallOutcome[PageSpeedResult]:
        """Measure one URL on one form factor.

        Never raises for a provider problem: the outcome either carries a result or
        carries ``UNKNOWN`` with a stated reason.
        """
        credentials = self._credentials
        if credentials is None:
            return self._disabled()

        def operation() -> PageSpeedResult:
            collected_at = self._clock()
            answer = self._http.request(
                "GET",
                f"{self._base_url}{RUNPAGESPEED_PATH}",
                params={
                    "url": url,
                    "strategy": strategy.value,
                    "category": _CATEGORY,
                    "locale": self._locale,
                },
                # The key travels in a header, never in the query string. Google documents
                # `?key=`, and it works — but a URL is the one part of a request that gets
                # written down by everything it passes through: access logs, proxy
                # histories, error reports, browser history if a URL is ever pasted. A
                # header is not immune to logging, but nothing logs it by default.
                #
                # Header authentication was an unverified guess until 2026-08-01, when a
                # live call returned 200 for both forms (INTEGRATION_REQUEST.md §5, §A-1).
                headers={API_KEY_HEADER: credentials.api_key.get_secret_value()},
            )
            return normalize_runpagespeed(
                answer.json_object(),
                url=url,
                strategy=strategy,
                collected_at=collected_at,
                raw_bytes=answer.body,
            )

        return self._caller.call(operation)

    def _disabled(self) -> CallOutcome[PageSpeedResult]:
        error = (
            GoogleCredentialInvalidError("PageSpeed credential is a placeholder")
            if self._unavailable_state is ProviderState.DISABLED_INVALID_CREDENTIAL
            else GoogleCredentialMissingError("no PageSpeed API key")
        )
        return CallOutcome(
            value=UNKNOWN,
            failure=ProviderFailure.from_error(error, occurred_at=self._clock()),
            attempts=0,
        )
