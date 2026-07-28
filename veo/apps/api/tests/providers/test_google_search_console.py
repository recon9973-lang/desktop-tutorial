"""Search Console: ownership, sitemaps, the performance series, and index coverage.

Two things this suite pins down and one it refuses to let happen.

**Pinned — the CTR unit.** Search Console's ``ctr`` is a ratio in ``[0, 1]``; Naver Search
Ad's is a percentage. The two live one import away from each other in this codebase, and a
figure copied between them is wrong by exactly 100x with no visible symptom. The unit is a
named constant and the arithmetic that settles it — ``clicks / impressions`` — is asserted
row by row.

**Pinned — where a number came from.** ``index_coverage.indexed`` is a count VEO computed
by inspecting URLs one at a time, because Search Console publishes no aggregate coverage
API. It is labelled ``CALCULATED`` and it must never be presented as Google's own figure.

**Refused — search performance leaking into readiness.** Impressions and clicks are
outcomes reported beside the score. Nothing in this module returns anything a scorer
could add up.
"""

from __future__ import annotations

from datetime import UTC, date, datetime

import httpx
import pytest
from google_fixtures import (
    GSC_PERFORMANCE_ROWS,
    SITE_URL,
    gsc_search_analytics_response,
    gsc_site_response,
    gsc_sitemaps_response,
    gsc_url_inspection_response,
    oauth_token_response,
    service_account_json,
)
from pydantic import SecretStr

from veo.contracts.enums import DataSource, ProviderState
from veo.providers.google.credentials import parse_search_console_credentials
from veo.providers.google.errors import UNKNOWN
from veo.providers.google.search_console import (
    CTR_UNIT,
    POSITION_UNIT,
    UNVERIFIED_PERMISSION_LEVEL,
    SearchConsoleClient,
    search_console_payload,
)

COLLECTED_AT = datetime(2026, 7, 28, 3, 5, tzinfo=UTC)
CREDENTIALS = parse_search_console_credentials(SecretStr(service_account_json()))

START = date(2026, 7, 24)
END = date(2026, 7, 26)


def route(request: httpx.Request) -> httpx.Response:
    """One handler for every endpoint the client may touch."""
    path = request.url.path
    if path.endswith("/token"):
        return httpx.Response(200, json=oauth_token_response())
    if path.endswith("/sitemaps"):
        return httpx.Response(200, json=gsc_sitemaps_response())
    if path.endswith("/searchAnalytics/query"):
        return httpx.Response(200, json=gsc_search_analytics_response())
    if "urlInspection" in path:
        return httpx.Response(200, json=gsc_url_inspection_response())
    return httpx.Response(200, json=gsc_site_response())


def build_client(handler: object = route, **kwargs: object) -> SearchConsoleClient:
    return SearchConsoleClient(
        credentials=CREDENTIALS,
        transport=httpx.MockTransport(handler),  # type: ignore[arg-type]
        clock=lambda: COLLECTED_AT,
        **kwargs,  # type: ignore[arg-type]
    )


# --------------------------------------------------------------------------- #
# The CTR unit
# --------------------------------------------------------------------------- #


def test_the_ctr_unit_is_declared_as_a_ratio() -> None:
    assert CTR_UNIT == "RATIO_0_TO_1"


def test_the_ctr_unit_is_not_the_naver_one() -> None:
    """Both adapters live in this repository. Their CTR units disagree, deliberately."""
    from veo.providers.naver.searchad import CTR_UNIT as NAVER_CTR_UNIT

    assert CTR_UNIT != NAVER_CTR_UNIT


def test_every_row_ctr_equals_clicks_over_impressions() -> None:
    """The arithmetic that settles the unit, kept as a regression check.

    If anything starts multiplying by 100, a stored ctr stops matching the click rate.
    """
    outcome = build_client().performance(SITE_URL, start_date=START, end_date=END)
    series = outcome.value
    for row in series.rows:
        assert row.ctr == pytest.approx(row.clicks / row.impressions, rel=1e-6)
        assert 0.0 <= row.ctr <= 1.0


def test_a_ctr_is_never_stored_as_a_percentage() -> None:
    outcome = build_client().performance(SITE_URL, start_date=START, end_date=END)
    for row in outcome.value.rows:
        assert row.ctr < 1.0, "a ctr at or above 1.0 means the ratio was rescaled"
        assert row.ctr_unit == CTR_UNIT


def test_position_carries_its_own_named_unit() -> None:
    assert POSITION_UNIT
    outcome = build_client().performance(SITE_URL, start_date=START, end_date=END)
    for row in outcome.value.rows:
        assert row.position_unit == POSITION_UNIT
        assert row.position >= 1.0


# --------------------------------------------------------------------------- #
# Performance series
# --------------------------------------------------------------------------- #


def test_the_series_totals_are_sums_of_the_rows_and_are_marked_calculated() -> None:
    outcome = build_client().performance(SITE_URL, start_date=START, end_date=END)
    series = outcome.value
    assert series.total_clicks == sum(row[1] for row in GSC_PERFORMANCE_ROWS)
    assert series.total_impressions == sum(row[2] for row in GSC_PERFORMANCE_ROWS)
    assert series.totals_source is DataSource.CALCULATED
    assert series.source is DataSource.GOOGLE_SEARCH_CONSOLE


def test_the_series_records_when_it_was_collected_and_what_window_it_covers() -> None:
    outcome = build_client().performance(SITE_URL, start_date=START, end_date=END)
    series = outcome.value
    assert series.collected_at == COLLECTED_AT
    assert series.date_range_start == START
    assert series.date_range_end == END


def test_a_row_missing_impressions_is_a_schema_error_and_never_a_zero() -> None:
    """Defaulting an unreadable figure to 0 would report "nobody saw the site"."""

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/token"):
            return httpx.Response(200, json=oauth_token_response())
        return httpx.Response(
            200,
            json={"rows": [{"keys": ["2026-07-26"], "clicks": 3, "ctr": 0.1, "position": 4.0}]},
        )

    outcome = build_client(handler, sleep=lambda seconds: None).performance(
        SITE_URL, start_date=START, end_date=END
    )
    assert outcome.value is UNKNOWN
    assert outcome.failure is not None


def test_an_empty_series_is_zero_rows_and_never_an_invented_number() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/token"):
            return httpx.Response(200, json=oauth_token_response())
        return httpx.Response(200, json={"responseAggregationType": "byPage"})

    outcome = build_client(handler).performance(SITE_URL, start_date=START, end_date=END)
    series = outcome.value
    assert series.rows == ()
    assert series.total_impressions == 0
    assert series.total_clicks == 0
    assert series.average_ctr is None
    assert series.average_position is None


# --------------------------------------------------------------------------- #
# Ownership
# --------------------------------------------------------------------------- #


def test_a_site_owner_is_verified() -> None:
    outcome = build_client().site(SITE_URL)
    ownership = outcome.value
    assert ownership.verified is True
    assert ownership.permission_level == "siteOwner"
    assert ownership.source is DataSource.GOOGLE_SEARCH_CONSOLE
    assert ownership.collected_at == COLLECTED_AT


def test_an_unverified_user_is_not_verified() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/token"):
            return httpx.Response(200, json=oauth_token_response())
        return httpx.Response(200, json=gsc_site_response(permission_level="siteUnverifiedUser"))

    outcome = build_client(handler).site(SITE_URL)
    assert outcome.value.verified is False
    assert UNVERIFIED_PERMISSION_LEVEL == "siteUnverifiedUser"


# --------------------------------------------------------------------------- #
# Sitemaps
# --------------------------------------------------------------------------- #


def test_int64_fields_that_arrive_as_strings_are_read_as_numbers() -> None:
    outcome = build_client().sitemaps(SITE_URL)
    submission = outcome.value[0]
    assert submission.errors == 0
    assert submission.warnings == 0
    assert submission.is_pending is False


def test_a_sitemap_with_errors_keeps_the_count() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/token"):
            return httpx.Response(200, json=oauth_token_response())
        return httpx.Response(200, json=gsc_sitemaps_response(errors="4"))

    outcome = build_client(handler).sitemaps(SITE_URL)
    assert outcome.value[0].errors == 4


def test_an_unreadable_count_is_none_rather_than_zero() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/token"):
            return httpx.Response(200, json=oauth_token_response())
        return httpx.Response(200, json=gsc_sitemaps_response(errors="unknown"))

    outcome = build_client(handler).sitemaps(SITE_URL)
    submission = outcome.value[0]
    assert submission.errors is None
    assert submission.errors != 0


# --------------------------------------------------------------------------- #
# Index coverage — VEO's count, labelled as VEO's count
# --------------------------------------------------------------------------- #


def test_index_coverage_is_labelled_calculated_because_google_publishes_no_total() -> None:
    outcome = build_client().index_coverage(SITE_URL, urls=[SITE_URL])
    coverage = outcome.value
    assert coverage.source is DataSource.CALCULATED
    assert coverage.indexed == 1
    assert coverage.inspected == 1


def test_a_url_google_has_not_indexed_is_counted_as_not_indexed() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/token"):
            return httpx.Response(200, json=oauth_token_response())
        return httpx.Response(200, json=gsc_url_inspection_response(verdict="NEUTRAL"))

    outcome = build_client(handler).index_coverage(SITE_URL, urls=[SITE_URL])
    coverage = outcome.value
    assert coverage.indexed == 0
    assert coverage.not_indexed == 1


def test_previous_indexed_is_not_invented_by_this_module() -> None:
    """A comparison needs history, and history lives in VEO's database, not in Google."""
    outcome = build_client().index_coverage(SITE_URL, urls=[SITE_URL])
    assert outcome.value.previous_indexed is None


# --------------------------------------------------------------------------- #
# Authentication
# --------------------------------------------------------------------------- #


def test_a_bearer_token_is_obtained_once_and_reused() -> None:
    token_calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal token_calls
        if request.url.path.endswith("/token"):
            token_calls += 1
            return httpx.Response(200, json=oauth_token_response())
        assert request.headers["authorization"] == "Bearer synthetic-access-token"
        return httpx.Response(200, json=gsc_site_response())

    client = build_client(handler)
    client.site(SITE_URL)
    client.site(SITE_URL)
    assert token_calls == 1


def test_the_private_key_never_leaves_the_process() -> None:
    bodies: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        bodies.append(request.content.decode())
        if request.url.path.endswith("/token"):
            return httpx.Response(200, json=oauth_token_response())
        return httpx.Response(200, json=gsc_site_response())

    client = build_client(handler)
    client.site(SITE_URL)
    assert "BEGIN PRIVATE KEY" not in " ".join(bodies)
    assert "BEGIN PRIVATE KEY" not in repr(client)


def test_a_rejected_token_request_is_unknown_with_a_korean_reason() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"error": "invalid_grant", "error_description": "leak"})

    outcome = build_client(handler, sleep=lambda seconds: None).site(SITE_URL)
    assert outcome.value is UNKNOWN
    assert outcome.failure is not None
    assert "leak" not in outcome.failure.reason_ko
    assert outcome.failure.reason_ko


# --------------------------------------------------------------------------- #
# No credential, and failures
# --------------------------------------------------------------------------- #


def test_without_a_credential_no_connection_is_opened() -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(200, json=gsc_site_response())

    client = SearchConsoleClient(
        credentials=None, transport=httpx.MockTransport(handler), clock=lambda: COLLECTED_AT
    )
    assert client.state is ProviderState.DISABLED_NO_CREDENTIAL
    for outcome in (
        client.site(SITE_URL),
        client.sitemaps(SITE_URL),
        client.performance(SITE_URL, start_date=START, end_date=END),
        client.index_coverage(SITE_URL, urls=[SITE_URL]),
    ):
        assert outcome.value is UNKNOWN
        assert outcome.failure is not None
        assert outcome.failure.provider_state is ProviderState.DISABLED_NO_CREDENTIAL
    assert calls == 0


def test_a_placeholder_credential_never_dials() -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(200, json=gsc_site_response())

    client = SearchConsoleClient(
        credentials=None,
        unavailable_state=ProviderState.DISABLED_INVALID_CREDENTIAL,
        transport=httpx.MockTransport(handler),
        clock=lambda: COLLECTED_AT,
    )
    assert client.state is ProviderState.DISABLED_INVALID_CREDENTIAL
    assert client.site(SITE_URL).value is UNKNOWN
    assert calls == 0


@pytest.mark.parametrize("status", [401, 403, 429, 500, 503])
def test_each_status_maps_to_a_typed_error_with_a_fixed_korean_message(status: int) -> None:
    leak = "User does not have sufficient permission for site https://real-customer.example"

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/token"):
            return httpx.Response(200, json=oauth_token_response())
        return httpx.Response(status, json={"error": {"message": leak}})

    outcome = build_client(handler, sleep=lambda seconds: None).site(SITE_URL)
    assert outcome.value is UNKNOWN
    assert outcome.failure is not None
    assert leak not in outcome.failure.reason_ko
    assert "real-customer" not in outcome.failure.reason_ko


def test_a_timeout_maps_to_a_retryable_failure() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/token"):
            return httpx.Response(200, json=oauth_token_response())
        raise httpx.ReadTimeout("slow", request=request)

    outcome = build_client(handler, sleep=lambda seconds: None).site(SITE_URL)
    assert outcome.value is UNKNOWN
    assert outcome.failure is not None
    assert outcome.failure.retryable is True


def test_a_response_in_an_unknown_shape_is_a_schema_failure_not_a_default() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/token"):
            return httpx.Response(200, json=oauth_token_response())
        return httpx.Response(200, content=b"<html>maintenance</html>")

    outcome = build_client(handler, sleep=lambda seconds: None).site(SITE_URL)
    assert outcome.value is UNKNOWN


# --------------------------------------------------------------------------- #
# The collector payload
# --------------------------------------------------------------------------- #


def test_the_payload_carries_outcomes_beside_readiness_never_inside_it() -> None:
    client = build_client()
    payload = search_console_payload(
        site=client.site(SITE_URL).value,
        sitemaps=client.sitemaps(SITE_URL).value,
        performance=client.performance(SITE_URL, start_date=START, end_date=END).value,
        coverage=client.index_coverage(SITE_URL, urls=[SITE_URL]).value,
    )
    assert payload["performance"]["impressions"] == sum(row[2] for row in GSC_PERFORMANCE_ROWS)
    assert payload["site"]["verified"] is True
    # Nothing in the payload offers a score, a grade or a weight for a scorer to pick up.
    assert not {"score", "points", "weight", "grade"} & set(payload)


def test_every_section_of_the_payload_says_where_it_came_from_and_when() -> None:
    client = build_client()
    payload = search_console_payload(
        site=client.site(SITE_URL).value,
        sitemaps=client.sitemaps(SITE_URL).value,
        performance=client.performance(SITE_URL, start_date=START, end_date=END).value,
        coverage=client.index_coverage(SITE_URL, urls=[SITE_URL]).value,
    )
    sections = [payload["site"], payload["performance"], payload["index_coverage"]]
    sections.extend(payload["sitemaps"])
    for section in sections:
        assert section["source"]
        assert section["collected_at"] == COLLECTED_AT.isoformat()

    # A Search Console figure and a VEO-calculated one must never look alike.
    assert payload["performance"]["source"] == DataSource.GOOGLE_SEARCH_CONSOLE.value
    assert payload["performance"]["totals_source"] == DataSource.CALCULATED.value
    assert payload["index_coverage"]["source"] == DataSource.CALCULATED.value


def test_a_section_veo_could_not_collect_is_absent_rather_than_zeroed() -> None:
    payload = search_console_payload(site=build_client().site(SITE_URL).value)
    assert "site" in payload
    assert "performance" not in payload
    assert "index_coverage" not in payload
