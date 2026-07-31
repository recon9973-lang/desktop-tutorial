"""CrUX: field data, and the one thing the standalone API does not publish.

Two surfaces expose the Chrome UX Report, and they are not interchangeable:

* PageSpeed's ``loadingExperience`` block carries Google's own ``FAST``/``AVERAGE``/
  ``SLOW`` label.
* The CrUX record API carries percentiles and histograms and **no label at all**.

VEO reports the label only where the provider supplies one. Deriving FAST from a p75 and
a threshold of VEO's choosing would put VEO's judgement into a field that reads, to a
customer, as Google's. That refusal is what most of this suite checks.
"""

from __future__ import annotations

from datetime import UTC, datetime

import httpx
import pytest
from google_fixtures import SITE_URL, crux_not_found_response, crux_query_record_response
from pydantic import SecretStr

from veo.contracts.enums import DataSource, ProviderState, ValueQuality
from veo.providers.google.credentials import PageSpeedCredentials
from veo.providers.google.crux import (
    CATEGORY_ACCESS_KO,
    INP_METRIC,
    QUERY_RECORD_PATH,
    CruxClient,
    FieldDataState,
    FieldScope,
    field_payload,
    normalize_loading_experience,
    normalize_query_record,
)
from veo.providers.google.errors import UNKNOWN
from veo.providers.google.http import API_KEY_HEADER

COLLECTED_AT = datetime(2026, 7, 28, 3, 5, tzinfo=UTC)
CREDENTIALS = PageSpeedCredentials(api_key=SecretStr("synthetic-pagespeed-key"))


def build_client(handler: object, **kwargs: object) -> CruxClient:
    return CruxClient(
        credentials=CREDENTIALS,
        transport=httpx.MockTransport(handler),  # type: ignore[arg-type]
        clock=lambda: COLLECTED_AT,
        **kwargs,  # type: ignore[arg-type]
    )


# --------------------------------------------------------------------------- #
# The record API is reachable, and it is honest about what it does not carry
# --------------------------------------------------------------------------- #


def test_a_record_maps_the_percentile_the_api_actually_publishes() -> None:
    measurement = normalize_query_record(
        crux_query_record_response(),
        url=SITE_URL,
        scope=FieldScope.URL,
        collected_at=COLLECTED_AT,
        raw_bytes=b"{}",
    )
    assert measurement.state is FieldDataState.AVAILABLE
    inp = measurement.metrics[INP_METRIC]
    assert inp.percentile == 120
    assert inp.percentile_quality is ValueQuality.EXACT
    assert inp.source is DataSource.GOOGLE_CRUX


def test_the_record_api_supplies_no_category_and_veo_does_not_invent_one() -> None:
    measurement = normalize_query_record(
        crux_query_record_response(),
        url=SITE_URL,
        scope=FieldScope.URL,
        collected_at=COLLECTED_AT,
        raw_bytes=b"{}",
    )
    inp = measurement.metrics[INP_METRIC]
    assert inp.category is None
    assert inp.category_quality is ValueQuality.MISSING


def test_every_field_value_in_the_payload_carries_source_and_collection_time() -> None:
    measurement = normalize_loading_experience(
        {"metrics": {INP_METRIC: {"category": "FAST", "percentile": 120}}},
        url=SITE_URL,
        scope=FieldScope.URL,
        collected_at=COLLECTED_AT,
    )
    entry = field_payload([measurement])[SITE_URL]
    assert entry["source"] == DataSource.GOOGLE_CRUX.value
    assert entry["collected_at"] == COLLECTED_AT.isoformat()
    for value in entry["metrics"].values():
        assert value["source"] == DataSource.GOOGLE_CRUX.value
        assert value["collected_at"] == COLLECTED_AT.isoformat()
        assert value["quality"] == ValueQuality.EXACT.value


def test_a_not_applicable_url_still_reaches_the_collector_so_it_can_say_so() -> None:
    """An omitted entry would read as "no integration"; an empty one reads as "no sample"."""
    measurement = normalize_loading_experience(
        {}, url=SITE_URL, scope=FieldScope.URL, collected_at=COLLECTED_AT
    )
    entry = field_payload([measurement])[SITE_URL]
    assert entry["metrics"] == {}
    assert entry["state"] == FieldDataState.NOT_APPLICABLE.value


def test_where_the_category_comes_from_is_documented_in_exactly_one_place() -> None:
    assert CATEGORY_ACCESS_KO
    assert "PageSpeed" in CATEGORY_ACCESS_KO


def test_a_measurement_without_a_provider_category_is_kept_out_of_the_collector_payload() -> None:
    """The collector reads a category. Feeding it a metric that has none would make a
    real sample look like a missing one, so the payload omits it and the reason travels
    with the measurement instead."""
    measurement = normalize_query_record(
        crux_query_record_response(),
        url=SITE_URL,
        scope=FieldScope.URL,
        collected_at=COLLECTED_AT,
        raw_bytes=b"{}",
    )
    assert field_payload([measurement]) == {}


# --------------------------------------------------------------------------- #
# No sample is not a zero
# --------------------------------------------------------------------------- #


def test_a_url_with_no_sample_is_not_applicable_rather_than_an_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, json=crux_not_found_response())

    outcome = build_client(handler, sleep=lambda seconds: None).query_record(SITE_URL)
    assert outcome.value is not UNKNOWN
    assert outcome.failure is None
    measurement = outcome.value
    assert measurement.state is FieldDataState.NOT_APPLICABLE
    assert measurement.metrics == {}
    assert measurement.reason_ko


def test_a_not_applicable_measurement_holds_no_numbers_at_all() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, json=crux_not_found_response())

    outcome = build_client(handler, sleep=lambda seconds: None).query_record(SITE_URL)
    measurement = outcome.value
    payload = measurement.as_payload_entry()
    for value in payload.get("metrics", {}).values():
        raise AssertionError(f"a URL with no sample produced a value: {value}")


# --------------------------------------------------------------------------- #
# The client
# --------------------------------------------------------------------------- #


def test_the_client_posts_to_the_documented_endpoint() -> None:
    seen: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["method"] = request.method
        seen["path"] = request.url.path
        seen["params"] = dict(request.url.params)
        seen["body"] = request.content.decode()
        return httpx.Response(200, json=crux_query_record_response())

    build_client(handler).query_record(SITE_URL)
    assert seen["method"] == "POST"
    assert seen["path"] == QUERY_RECORD_PATH
    assert SITE_URL in str(seen["body"])


def test_the_api_key_travels_in_a_header_and_never_in_the_url() -> None:
    """Same rule as PageSpeed: the key stays out of anything that gets logged by default.

    CrUX is the easier one to forget — its request already carries a JSON body, so a key
    in the query string looks like it is out of the way. It is not: the URL is still what
    a proxy writes down.
    """
    seen: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["header"] = request.headers.get(API_KEY_HEADER)
        seen["url"] = str(request.url)
        return httpx.Response(200, json=crux_query_record_response())

    build_client(handler).query_record(SITE_URL)
    assert seen["header"] == "synthetic-pagespeed-key"
    assert "synthetic-pagespeed-key" not in str(seen["url"])


def test_an_origin_query_is_a_different_scope_not_a_different_url() -> None:
    seen: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["body"] = request.content.decode()
        return httpx.Response(200, json=crux_query_record_response())

    outcome = build_client(handler).query_record(SITE_URL, scope=FieldScope.ORIGIN)
    assert '"origin"' in str(seen["body"])
    assert outcome.value.scope is FieldScope.ORIGIN


def test_without_a_credential_no_connection_is_opened() -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(200, json=crux_query_record_response())

    client = CruxClient(
        credentials=None, transport=httpx.MockTransport(handler), clock=lambda: COLLECTED_AT
    )
    assert client.state is ProviderState.DISABLED_NO_CREDENTIAL
    outcome = client.query_record(SITE_URL)
    assert calls == 0
    assert outcome.value is UNKNOWN
    assert outcome.failure is not None


def test_a_placeholder_credential_never_dials_either() -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(200, json=crux_query_record_response())

    client = CruxClient(
        credentials=None,
        unavailable_state=ProviderState.DISABLED_INVALID_CREDENTIAL,
        transport=httpx.MockTransport(handler),
        clock=lambda: COLLECTED_AT,
    )
    outcome = client.query_record(SITE_URL)
    assert calls == 0
    assert outcome.failure is not None
    assert outcome.failure.provider_state is ProviderState.DISABLED_INVALID_CREDENTIAL


@pytest.mark.parametrize("status", [401, 403, 429, 500])
def test_failures_are_typed_and_never_echo_the_provider(status: int) -> None:
    leak = "API key not valid: AIzaSyD-synthetic-leaked-key"

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status, json={"error": {"message": leak}})

    outcome = build_client(handler, sleep=lambda seconds: None).query_record(SITE_URL)
    assert outcome.value is UNKNOWN
    assert outcome.failure is not None
    assert leak not in outcome.failure.reason_ko
    assert "AIzaSy" not in outcome.failure.reason_ko


def test_a_timeout_degrades_to_unknown() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectTimeout("slow", request=request)

    outcome = build_client(handler, sleep=lambda seconds: None).query_record(SITE_URL)
    assert outcome.value is UNKNOWN
