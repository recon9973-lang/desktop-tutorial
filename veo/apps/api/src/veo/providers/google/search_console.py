"""Search Console — ownership, sitemaps, index coverage, and the performance series.

Four things this module is careful about, in the order they can hurt.

**1. The CTR unit.** Search Console's ``ctr`` is a **ratio in [0, 1]**. Naver Search Ad's
``monthlyAvePcCtr`` is a **percentage**. Both adapters live in this repository, one import
apart, and a figure moved between them is wrong by exactly 100x with no visible symptom —
a 3.4% click-through rate renders as 340% or as 0.034%, and both look like a formatting
bug rather than a data bug. :data:`CTR_UNIT` names the unit, and the arithmetic that
settles it is checkable offline in a way the Naver one was not: Google's own rows satisfy
``ctr == clicks / impressions`` exactly, and the test suite asserts that row by row. What
is *assumed* rather than verified: that a live response keeps that identity for aggregated
(non-``date``) dimensions, where rounding could make it approximate.

**2. Search performance is not technical readiness.** Impressions, clicks, CTR and average
position are **outcomes**. They are reported beside the readiness score and never folded
into it — a site can be technically flawless and unvisited, or badly built and ranking on
brand terms alone. Nothing this module returns is shaped like a score.

**3. Index coverage is VEO's count, not Google's.** Search Console publishes **no**
aggregate coverage API. The number here is produced by inspecting URLs one at a time
through the URL Inspection API, under a documented daily quota, and it is labelled
:attr:`~veo.contracts.enums.DataSource.CALCULATED` and carries how many URLs it looked at.
It must never be presented as "Google says you have N indexed pages".

**4. ``previous_indexed`` comes from VEO's own history.** This module does not invent it
and does not guess it; it leaves the field ``None`` for the caller to fill from a prior
scan. See ``INTEGRATION_REQUEST.md`` §6.

**Unverified.** VEO holds no Search Console credential. Every field name follows the
published API reference and none has been checked against a live response.
"""

from __future__ import annotations

import hashlib
import time
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from datetime import time as clock_time
from typing import Any, Final, final
from urllib.parse import quote

import httpx
import jwt

from veo.contracts.enums import DataSource, ProviderState
from veo.providers.google.credentials import (
    SEARCH_CONSOLE_SCOPE,
    AuthorizedUserCredentials,
    SearchConsoleCredentials,
    ServiceAccountCredentials,
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
    DEFAULT_MAX_RESPONSE_BYTES,
    DEFAULT_TIMEOUT_SECONDS,
    GoogleHttpCaller,
    as_number,
)

__all__ = [
    "API_VERSION",
    "CTR_UNIT",
    "MAX_URLS_PER_COVERAGE_RUN",
    "POSITION_UNIT",
    "SEARCH_CONSOLE_BASE_URL",
    "UNVERIFIED_PERMISSION_LEVEL",
    "URL_INSPECTION_BASE_URL",
    "IndexCoverage",
    "PerformanceRow",
    "PerformanceSeries",
    "SearchConsoleClient",
    "SiteOwnership",
    "SitemapSubmission",
    "UrlIndexStatus",
    "search_console_payload",
]

SEARCH_CONSOLE_BASE_URL: Final = "https://www.googleapis.com"
URL_INSPECTION_BASE_URL: Final = "https://searchconsole.googleapis.com"
_SITES_PATH: Final = "/webmasters/v3/sites"
_INSPECT_PATH: Final = "/v1/urlInspection/index:inspect"

#: VEO's label for *this mapping*, not a version Google publishes.
API_VERSION: Final = "google.searchconsole.v3.map.v1"

#: **Verified by arithmetic, not by documentation alone.** Search Console reports ``ctr``
#: as ``clicks / impressions`` — a ratio between 0 and 1. Every synthetic row in the test
#: suite is built from that identity and asserted against it, so a change that starts
#: multiplying by 100 fails immediately. Nothing downstream may rescale this value.
#:
#: Deliberately *not* the same as ``veo.providers.naver.searchad.CTR_UNIT``, which is
#: ``PERCENT``. The two providers disagree, and the constants say so out loud.
CTR_UNIT: Final = "RATIO_0_TO_1"

#: Average position, where 1 is the top result. Larger is worse — the one metric in VEO
#: where a rising number is bad news, which is exactly why it is named.
POSITION_UNIT: Final = "AVERAGE_RANK_1_IS_BEST"

#: The permission level Search Console reports for a property whose ownership has not been
#: verified. Any other level implies verification.
UNVERIFIED_PERMISSION_LEVEL: Final = "siteUnverifiedUser"

#: URL Inspection is quota-limited (documented at 2,000 queries per property per day, 600
#: per minute). A coverage run therefore inspects a bounded sample and says how many.
MAX_URLS_PER_COVERAGE_RUN: Final = 50

#: A verdict of ``PASS`` is the only one that means "indexed". ``NEUTRAL``, ``PARTIAL``
#: and ``FAIL`` all mean some form of not-indexed, and collapsing them into "indexed" is
#: how a coverage number ends up flattering a broken site.
_INDEXED_VERDICT: Final = "PASS"

#: Seconds of slack subtracted from a token's lifetime, so a token is never used in the
#: instant it expires.
_TOKEN_EXPIRY_MARGIN_SECONDS: Final = 60

_JWT_LIFETIME_SECONDS: Final = 3600


# --------------------------------------------------------------------------- #
# Values
# --------------------------------------------------------------------------- #


@final
@dataclass(frozen=True, slots=True)
class SiteOwnership:
    """Whether Search Console considers this property verified, and at what level."""

    site_url: str
    verified: bool
    permission_level: str | None
    collected_at: datetime
    source: DataSource = DataSource.GOOGLE_SEARCH_CONSOLE
    api_version: str = API_VERSION


@final
@dataclass(frozen=True, slots=True)
class SitemapSubmission:
    """One submitted sitemap as Search Console reports it.

    ``errors`` and ``warnings`` arrive as JSON *strings* (protobuf int64 convention). A
    value VEO cannot read stays ``None`` rather than becoming ``0``: "no errors" and "we
    could not tell how many errors" are different facts, and one of them is reassuring.
    """

    path: str
    is_pending: bool
    is_sitemaps_index: bool
    errors: int | None
    warnings: int | None
    last_submitted: str | None
    last_downloaded: str | None
    collected_at: datetime
    source: DataSource = DataSource.GOOGLE_SEARCH_CONSOLE


@final
@dataclass(frozen=True, slots=True)
class PerformanceRow:
    """One row of the search performance series, in the provider's own units."""

    key: str | None
    row_date: date | None
    clicks: int
    impressions: int
    ctr: float
    position: float
    ctr_unit: str = CTR_UNIT
    position_unit: str = POSITION_UNIT
    source: DataSource = DataSource.GOOGLE_SEARCH_CONSOLE


@final
@dataclass(frozen=True, slots=True)
class PerformanceSeries:
    """The performance series, plus the totals VEO computed from it.

    ``source`` is the provider; ``totals_source`` is ``CALCULATED``, because Google did not
    send a total and VEO added the rows up. A reader must be able to tell those apart.
    """

    rows: tuple[PerformanceRow, ...]
    date_range_start: date
    date_range_end: date
    collected_at: datetime
    total_clicks: int
    total_impressions: int
    average_ctr: float | None
    average_position: float | None
    source: DataSource = DataSource.GOOGLE_SEARCH_CONSOLE
    totals_source: DataSource = DataSource.CALCULATED
    ctr_unit: str = CTR_UNIT
    position_unit: str = POSITION_UNIT
    api_version: str = API_VERSION
    raw_response_hash: str | None = None


@final
@dataclass(frozen=True, slots=True)
class UrlIndexStatus:
    """What the URL Inspection API said about one URL."""

    url: str
    verdict: str | None
    coverage_state: str | None
    indexing_state: str | None
    robots_txt_state: str | None
    last_crawl_time: str | None
    is_indexed: bool
    source: DataSource = DataSource.GOOGLE_SEARCH_CONSOLE


@final
@dataclass(frozen=True, slots=True)
class IndexCoverage:
    """A count VEO produced by inspecting URLs one at a time.

    Not a Search Console figure. Google exposes no aggregate coverage endpoint, so this is
    arithmetic over however many URLs the run was allowed to inspect — which is why
    ``inspected`` and ``requested`` travel with the counts, and why ``source`` is
    ``CALCULATED``.
    """

    indexed: int
    not_indexed: int
    inspected: int
    requested: int
    collected_at: datetime
    statuses: tuple[UrlIndexStatus, ...] = ()
    previous_indexed: int | None = None
    source: DataSource = DataSource.CALCULATED
    api_version: str = API_VERSION

    @property
    def is_complete(self) -> bool:
        """Whether every requested URL was actually inspected."""
        return self.inspected == self.requested


# --------------------------------------------------------------------------- #
# Normalisation
# --------------------------------------------------------------------------- #


def _normalize_site(
    payload: Mapping[str, Any], *, site_url: str, collected_at: datetime
) -> SiteOwnership:
    permission = payload.get("permissionLevel")
    if not isinstance(permission, str) or not permission.strip():
        raise GoogleSchemaError("site response has no permissionLevel")
    return SiteOwnership(
        site_url=str(payload.get("siteUrl") or site_url),
        verified=permission != UNVERIFIED_PERMISSION_LEVEL,
        permission_level=permission,
        collected_at=collected_at,
    )


def _normalize_sitemaps(
    payload: Mapping[str, Any], *, collected_at: datetime
) -> tuple[SitemapSubmission, ...]:
    raw = payload.get("sitemap", [])
    if not isinstance(raw, list):
        raise GoogleSchemaError("sitemaps response has no sitemap array")

    submissions: list[SitemapSubmission] = []
    for entry in raw:
        if not isinstance(entry, Mapping):
            raise GoogleSchemaError("a sitemap entry is not an object")
        path = entry.get("path")
        if not isinstance(path, str) or not path.strip():
            raise GoogleSchemaError("a sitemap entry has no path")
        submissions.append(
            SitemapSubmission(
                path=path,
                is_pending=bool(entry.get("isPending")),
                is_sitemaps_index=bool(entry.get("isSitemapsIndex")),
                errors=_int(entry.get("errors")),
                warnings=_int(entry.get("warnings")),
                last_submitted=_text(entry.get("lastSubmitted")),
                last_downloaded=_text(entry.get("lastDownloaded")),
                collected_at=collected_at,
            )
        )
    return tuple(submissions)


def _normalize_performance(
    payload: Mapping[str, Any],
    *,
    start_date: date,
    end_date: date,
    collected_at: datetime,
    raw_bytes: bytes,
) -> PerformanceSeries:
    raw_rows = payload.get("rows", [])
    if not isinstance(raw_rows, list):
        raise GoogleSchemaError("search analytics response has no rows array")

    rows: list[PerformanceRow] = []
    for entry in raw_rows:
        if not isinstance(entry, Mapping):
            raise GoogleSchemaError("a search analytics row is not an object")
        keys = entry.get("keys")
        key = str(keys[0]) if isinstance(keys, list) and keys else None
        rows.append(
            PerformanceRow(
                key=key,
                row_date=_date(key),
                clicks=int(_required_number(entry, "clicks")),
                impressions=int(_required_number(entry, "impressions")),
                # Verbatim. See CTR_UNIT: this is already a ratio.
                ctr=_required_number(entry, "ctr"),
                position=_required_number(entry, "position"),
            )
        )

    total_clicks = sum(row.clicks for row in rows)
    total_impressions = sum(row.impressions for row in rows)
    return PerformanceSeries(
        rows=tuple(rows),
        date_range_start=start_date,
        date_range_end=end_date,
        collected_at=collected_at,
        total_clicks=total_clicks,
        total_impressions=total_impressions,
        # No impressions means no rate. Reporting 0.0 would say "nobody clicks", when what
        # happened is that nobody saw it.
        average_ctr=(total_clicks / total_impressions) if total_impressions else None,
        # Impression-weighted, because that is how an average position over a period is
        # defined; an unweighted mean of daily positions would over-count quiet days.
        average_position=_weighted_position(rows),
        raw_response_hash=hashlib.sha256(raw_bytes).hexdigest(),
    )


def _required_number(entry: Mapping[str, Any], key: str) -> float:
    """A performance figure that must be present, or a schema error.

    Defaulting an absent ``impressions`` to ``0`` would turn a response VEO failed to
    understand into a report saying nobody saw the site — the exact substitution this
    product exists to refuse. A row that is not the documented shape stops the call.
    """
    value = as_number(entry.get(key))
    if value is None:
        raise GoogleSchemaError(f"search analytics row has no readable {key}")
    return value


def _weighted_position(rows: Sequence[PerformanceRow]) -> float | None:
    impressions = sum(row.impressions for row in rows)
    if not impressions:
        return None
    return sum(row.position * row.impressions for row in rows) / impressions


def _normalize_inspection(payload: Mapping[str, Any], *, url: str) -> UrlIndexStatus:
    result = payload.get("inspectionResult")
    if not isinstance(result, Mapping):
        raise GoogleSchemaError("inspection response has no inspectionResult")
    status = result.get("indexStatusResult")
    if not isinstance(status, Mapping):
        raise GoogleSchemaError("inspection result has no indexStatusResult")
    verdict = _text(status.get("verdict"))
    return UrlIndexStatus(
        url=url,
        verdict=verdict,
        coverage_state=_text(status.get("coverageState")),
        indexing_state=_text(status.get("indexingState")),
        robots_txt_state=_text(status.get("robotsTxtState")),
        last_crawl_time=_text(status.get("lastCrawlTime")),
        is_indexed=verdict == _INDEXED_VERDICT,
    )


def _int(value: Any) -> int | None:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        try:
            return int(value.strip())
        except ValueError:
            # A marker VEO has not seen. None keeps it out of the arithmetic while the
            # fact that something was there is preserved by not being a zero.
            return None
    return None




def _text(value: Any) -> str | None:
    return value if isinstance(value, str) and value.strip() else None


def _date(value: str | None) -> date | None:
    if value is None:
        return None
    try:
        return date.fromisoformat(value.strip())
    except ValueError:
        return None


# --------------------------------------------------------------------------- #
# The collector payload
# --------------------------------------------------------------------------- #


def search_console_payload(
    *,
    site: SiteOwnership | None = None,
    sitemaps: Sequence[SitemapSubmission] | None = None,
    performance: PerformanceSeries | None = None,
    coverage: IndexCoverage | None = None,
) -> dict[str, Any]:
    """Build the ``GOOGLE_SEARCH_CONSOLE`` payload the SEO collectors consume.

    Only the sections that were actually measured appear. A section VEO could not collect
    is absent, which the collectors read as UNKNOWN — rather than present with zeroes,
    which they would read as a measurement.
    """
    payload: dict[str, Any] = {}

    if site is not None:
        payload["site"] = {
            "verified": site.verified,
            "permission_level": site.permission_level,
            "source": site.source.value,
            "collected_at": site.collected_at.isoformat(),
        }

    if sitemaps is not None:
        payload["sitemaps"] = [
            {
                "path": submission.path,
                "is_pending": submission.is_pending,
                "errors": submission.errors,
                "warnings": submission.warnings,
                "last_submitted": submission.last_submitted,
                "last_downloaded": submission.last_downloaded,
                "source": submission.source.value,
                "collected_at": submission.collected_at.isoformat(),
            }
            for submission in sitemaps
        ]

    if performance is not None:
        payload["performance"] = {
            "rows": len(performance.rows),
            "impressions": performance.total_impressions,
            "clicks": performance.total_clicks,
            "ctr": performance.average_ctr,
            "ctr_unit": performance.ctr_unit,
            "average_position": performance.average_position,
            "position_unit": performance.position_unit,
            "date_range_start": _as_utc_iso(performance.date_range_start),
            "date_range_end": _as_utc_iso(performance.date_range_end),
            "source": performance.source.value,
            "totals_source": performance.totals_source.value,
            "collected_at": performance.collected_at.isoformat(),
        }

    if coverage is not None:
        payload["index_coverage"] = {
            "indexed": coverage.indexed,
            "not_indexed": coverage.not_indexed,
            "inspected": coverage.inspected,
            "requested": coverage.requested,
            "previous_indexed": coverage.previous_indexed,
            "source": coverage.source.value,
            "collected_at": coverage.collected_at.isoformat(),
        }

    return payload


def _as_utc_iso(value: date) -> str:
    """A date rendered as an explicit UTC instant.

    A bare ``2026-07-26`` is read as local time by half the tools that touch it, and a
    freshness check that silently shifts by nine hours in Korea is a check that reports
    stale data as fresh.
    """
    return datetime.combine(value, clock_time.min, tzinfo=UTC).isoformat()


# --------------------------------------------------------------------------- #
# The client
# --------------------------------------------------------------------------- #


class SearchConsoleClient:
    """Calls Search Console, or explains why it did not.

    Authentication is done here, against the documented OAuth 2.0 endpoints, with
    :mod:`httpx` and :mod:`jwt` — ``google-api-python-client`` is not a dependency of this
    project and adding one to sign a JWT would be a large amount of transitive surface for
    twenty lines of code.

    With no credential the client **never opens a connection**, including to the token
    endpoint.
    """

    def __init__(
        self,
        *,
        credentials: SearchConsoleCredentials | None,
        unavailable_state: ProviderState = ProviderState.DISABLED_NO_CREDENTIAL,
        transport: httpx.BaseTransport | None = None,
        base_url: str = SEARCH_CONSOLE_BASE_URL,
        inspection_base_url: str = URL_INSPECTION_BASE_URL,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
        sleep: Callable[[float], None] = time.sleep,
        policy: RetryPolicy | None = None,
        breaker: GoogleCircuitBreaker | None = None,
        timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
        max_response_bytes: int = DEFAULT_MAX_RESPONSE_BYTES,
        max_urls_per_coverage_run: int = MAX_URLS_PER_COVERAGE_RUN,
    ) -> None:
        if credentials is not None and (
            unavailable_state is not ProviderState.DISABLED_NO_CREDENTIAL
        ):
            raise ValueError("unavailable_state describes the absence of a credential")
        self._credentials = credentials
        self._unavailable_state = unavailable_state
        self._base_url = base_url.rstrip("/")
        self._inspection_base_url = inspection_base_url.rstrip("/")
        self._clock = clock
        self._max_urls = max_urls_per_coverage_run
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
        self._access_token: str | None = None
        self._token_expires_at: datetime | None = None

    def __repr__(self) -> str:
        return f"<SearchConsoleClient state={self.state.value}>"

    @property
    def state(self) -> ProviderState:
        if self._credentials is None:
            return self._unavailable_state
        return self._caller.breaker.provider_state()

    # ------------------------------------------------------------- the calls

    def site(self, site_url: str) -> CallOutcome[SiteOwnership]:
        """Ownership state of one property."""
        if self._credentials is None:
            return self._disabled()

        def operation() -> SiteOwnership:
            collected_at = self._clock()
            answer = self._http.request(
                "GET",
                f"{self._base_url}{_SITES_PATH}/{quote(site_url, safe='')}",
                headers=self._authorization(),
            )
            return _normalize_site(
                answer.json_object(), site_url=site_url, collected_at=collected_at
            )

        return self._caller.call(operation)

    def sitemaps(self, site_url: str) -> CallOutcome[tuple[SitemapSubmission, ...]]:
        """Sitemaps submitted for one property, and how each was processed."""
        if self._credentials is None:
            return self._disabled()

        def operation() -> tuple[SitemapSubmission, ...]:
            collected_at = self._clock()
            answer = self._http.request(
                "GET",
                f"{self._base_url}{_SITES_PATH}/{quote(site_url, safe='')}/sitemaps",
                headers=self._authorization(),
            )
            return _normalize_sitemaps(answer.json_object(), collected_at=collected_at)

        return self._caller.call(operation)

    def performance(
        self,
        site_url: str,
        *,
        start_date: date,
        end_date: date,
        dimensions: Sequence[str] = ("date",),
        row_limit: int = 1000,
    ) -> CallOutcome[PerformanceSeries]:
        """The search performance series — an outcome, never an input to a score."""
        if self._credentials is None:
            return self._disabled()

        def operation() -> PerformanceSeries:
            collected_at = self._clock()
            answer = self._http.request(
                "POST",
                f"{self._base_url}{_SITES_PATH}/{quote(site_url, safe='')}"
                "/searchAnalytics/query",
                headers=self._authorization(),
                json_body={
                    "startDate": start_date.isoformat(),
                    "endDate": end_date.isoformat(),
                    "dimensions": list(dimensions),
                    "rowLimit": row_limit,
                },
            )
            return _normalize_performance(
                answer.json_object(),
                start_date=start_date,
                end_date=end_date,
                collected_at=collected_at,
                raw_bytes=answer.body,
            )

        return self._caller.call(operation)

    def index_coverage(
        self, site_url: str, *, urls: Sequence[str]
    ) -> CallOutcome[IndexCoverage]:
        """Count how many of ``urls`` Google reports as indexed.

        One request per URL — that is the only shape the URL Inspection API offers — under
        :data:`MAX_URLS_PER_COVERAGE_RUN`. The result records both how many URLs were
        asked about and how many were inspected, so a truncated run can never be read as a
        site-wide figure.
        """
        if self._credentials is None:
            return self._disabled()

        requested = list(urls)
        sample = requested[: self._max_urls]

        def operation() -> IndexCoverage:
            collected_at = self._clock()
            statuses = tuple(
                _normalize_inspection(
                    self._http.request(
                        "POST",
                        f"{self._inspection_base_url}{_INSPECT_PATH}",
                        headers=self._authorization(),
                        json_body={"inspectionUrl": url, "siteUrl": site_url},
                    ).json_object(),
                    url=url,
                )
                for url in sample
            )
            indexed = sum(1 for status in statuses if status.is_indexed)
            return IndexCoverage(
                indexed=indexed,
                not_indexed=len(statuses) - indexed,
                inspected=len(statuses),
                requested=len(requested),
                collected_at=collected_at,
                statuses=statuses,
                # Deliberately absent: a comparison needs history, and history lives in
                # VEO's database. See INTEGRATION_REQUEST.md §6.
                previous_indexed=None,
            )

        return self._caller.call(operation)

    # ------------------------------------------------------------- internals

    def _disabled[T](self) -> CallOutcome[T]:
        error = (
            GoogleCredentialInvalidError("Search Console credential is a placeholder")
            if self._unavailable_state is ProviderState.DISABLED_INVALID_CREDENTIAL
            else GoogleCredentialMissingError("no Search Console credential")
        )
        return CallOutcome(
            value=UNKNOWN,
            failure=ProviderFailure.from_error(error, occurred_at=self._clock()),
            attempts=0,
        )

    def _authorization(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self._token()}"}

    def _token(self) -> str:
        """A cached bearer token, minted on first use and reused until it nears expiry."""
        now = self._clock()
        if (
            self._access_token is not None
            and self._token_expires_at is not None
            and now < self._token_expires_at
        ):
            return self._access_token

        credentials = self._credentials
        if credentials is None:  # pragma: no cover - guarded by every public method
            raise GoogleCredentialMissingError("no Search Console credential")

        answer = self._http.request(
            "POST", credentials.token_uri, form_body=self._token_request(credentials, now=now)
        )
        payload = answer.json_object()
        token = payload.get("access_token")
        if not isinstance(token, str) or not token.strip():
            raise GoogleSchemaError("token response has no access_token")

        lifetime = as_number(payload.get("expires_in")) or float(_JWT_LIFETIME_SECONDS)
        self._access_token = token
        self._token_expires_at = now + timedelta(
            seconds=max(lifetime - _TOKEN_EXPIRY_MARGIN_SECONDS, 0.0)
        )
        return token

    def _token_request(
        self, credentials: SearchConsoleCredentials, *, now: datetime
    ) -> dict[str, str]:
        if isinstance(credentials, ServiceAccountCredentials):
            return {
                "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
                "assertion": _assertion(credentials, now=now),
            }
        if isinstance(credentials, AuthorizedUserCredentials):
            return {
                "grant_type": "refresh_token",
                "client_id": credentials.client_id,
                "client_secret": credentials.client_secret.get_secret_value(),
                "refresh_token": credentials.refresh_token.get_secret_value(),
            }
        raise GoogleCredentialInvalidError(  # pragma: no cover - the union is closed
            f"unsupported credential type: {type(credentials).__name__}"
        )


def _assertion(credentials: ServiceAccountCredentials, *, now: datetime) -> str:
    """Sign the JWT bearer assertion.

    The private key is unwrapped in this function and nowhere else, and the result — a
    signature, not the key — is what leaves the process.
    """
    issued_at = int(now.timestamp())
    try:
        return jwt.encode(
            {
                "iss": credentials.client_email,
                "scope": SEARCH_CONSOLE_SCOPE,
                "aud": credentials.token_uri,
                "iat": issued_at,
                "exp": issued_at + _JWT_LIFETIME_SECONDS,
            },
            credentials.private_key.get_secret_value(),
            algorithm="RS256",
        )
    except Exception as exc:
        # A malformed private key raises from deep inside the crypto library, and its text
        # can quote key material. Only the exception's type name is kept.
        raise GoogleCredentialInvalidError(
            f"could not sign the assertion: {type(exc).__name__}"
        ) from None
