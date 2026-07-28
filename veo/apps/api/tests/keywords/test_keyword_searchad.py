"""SearchAd response normalisation and the client's behaviour.

The rule under test throughout: **0, missing, provider-suppressed and range-bounded are
four different facts.** Collapsing any of them into another is the failure this suite
exists to catch, because a suppressed value written as ``0`` is indistinguishable from a
keyword nobody searches for — and a customer would act on that.
"""

from __future__ import annotations

from datetime import UTC, datetime

import httpx
import pytest
from pydantic import SecretStr
from tests.keywords.naver_fixtures import load, load_bytes

from veo.contracts.enums import DataSource, ProviderState, ValueQuality
from veo.providers.naver.errors import UNKNOWN, NaverSchemaError
from veo.providers.naver.searchad import (
    BELOW_THRESHOLD_UPPER_BOUND_EXCLUSIVE,
    KEYWORDSTOOL_PATH,
    AverageMetric,
    NaverSearchAdClient,
    SearchAdCredentials,
    SearchCount,
    normalize_keywordstool,
)

COLLECTED_AT = datetime(2026, 7, 28, 3, 0, tzinfo=UTC)

CREDENTIALS = SearchAdCredentials(
    api_key=SecretStr("synthetic-access-license"),
    secret_key=SecretStr("synthetic-secret"),
    customer_id="9999999",
)


def normalized() -> dict[str, object]:
    payload = load("searchad_keywordstool_synthetic.json")
    response = normalize_keywordstool(
        payload,
        collected_at=COLLECTED_AT,
        raw_bytes=load_bytes("searchad_keywordstool_synthetic.json"),
    )
    return {metric.keyword: metric for metric in response.metrics}


# --------------------------------------------------------------------------- #
# Field mapping
# --------------------------------------------------------------------------- #


def test_ordinary_row_maps_every_documented_field() -> None:
    metric = normalized()["합성키워드-A"]
    assert metric.monthly_pc_searches == SearchCount(value=1111, quality=ValueQuality.EXACT)
    assert metric.monthly_mobile_searches == SearchCount(value=2222, quality=ValueQuality.EXACT)
    assert metric.avg_pc_clicks == AverageMetric(value=11.1, quality=ValueQuality.EXACT)
    assert metric.avg_mobile_clicks == AverageMetric(value=22.2, quality=ValueQuality.EXACT)
    assert metric.avg_pc_ctr == AverageMetric(value=1.11, quality=ValueQuality.EXACT)
    assert metric.avg_mobile_ctr == AverageMetric(value=2.22, quality=ValueQuality.EXACT)
    assert metric.ad_depth == 11
    assert metric.competition_label == "높음"


def test_competition_index_is_absent_because_naver_publishes_a_label() -> None:
    """The documented response carries ``compIdx`` as a label, not a 0-100 index.

    Inventing a number for the ``competition_index`` column would be exactly the kind of
    plausible fabrication this product must not produce, so the column stays NULL and the
    label is what is reported.
    """
    for metric in normalized().values():
        assert metric.competition_index is None


def test_raw_provider_values_are_preserved_alongside_the_mapping() -> None:
    metric = normalized()["합성키워드-A"]
    assert metric.provider_raw["monthlyPcQcCnt"] == 1111
    assert metric.provider_raw["compIdx"] == "높음"


def test_response_records_when_and_what_it_normalised() -> None:
    response = normalize_keywordstool(
        load("searchad_keywordstool_synthetic.json"),
        collected_at=COLLECTED_AT,
        raw_bytes=load_bytes("searchad_keywordstool_synthetic.json"),
    )
    assert response.collected_at == COLLECTED_AT
    assert len(response.raw_response_hash) == 64
    assert response.api_version


# --------------------------------------------------------------------------- #
# Zero / missing / suppressed / range-bounded stay four different facts
# --------------------------------------------------------------------------- #


def test_zero_is_an_exact_zero() -> None:
    metric = normalized()["합성키워드-B"]
    assert metric.monthly_pc_searches.value == 0
    assert metric.monthly_pc_searches.quality is ValueQuality.EXACT


def test_below_threshold_marker_is_not_zero() -> None:
    metric = normalized()["합성키워드-C"]
    count = metric.monthly_pc_searches
    assert count.value is None
    assert count.quality is ValueQuality.BELOW_PROVIDER_THRESHOLD
    assert count.upper_bound_exclusive == BELOW_THRESHOLD_UPPER_BOUND_EXCLUSIVE
    assert count.value != 0


def test_explicit_null_is_suppressed_not_zero() -> None:
    metric = normalized()["합성키워드-D"]
    count = metric.monthly_pc_searches
    assert count.value is None
    assert count.quality is ValueQuality.SUPPRESSED_BY_PROVIDER


def test_absent_key_is_missing_not_zero() -> None:
    metric = normalized()["합성키워드-D"]
    assert metric.avg_pc_clicks.value is None
    assert metric.avg_pc_clicks.quality is ValueQuality.MISSING
    assert metric.ad_depth is None
    assert metric.competition_label is None


def test_the_four_qualities_are_all_distinct_in_one_response() -> None:
    rows = normalized()
    qualities = {
        rows["합성키워드-B"].monthly_pc_searches.quality,
        rows["합성키워드-C"].monthly_pc_searches.quality,
        rows["합성키워드-D"].monthly_pc_searches.quality,
        rows["합성키워드-D"].avg_pc_clicks.quality,
    }
    assert qualities == {
        ValueQuality.EXACT,
        ValueQuality.BELOW_PROVIDER_THRESHOLD,
        ValueQuality.SUPPRESSED_BY_PROVIDER,
        ValueQuality.MISSING,
    }


# --------------------------------------------------------------------------- #
# The total is VEO's arithmetic, and it refuses to add what it cannot add
# --------------------------------------------------------------------------- #


def test_total_is_calculated_and_labelled_as_such() -> None:
    metric = normalized()["합성키워드-A"]
    assert metric.monthly_total_searches.value == 3333
    assert metric.monthly_total_searches.quality is ValueQuality.EXACT
    assert metric.monthly_total_searches.source is DataSource.CALCULATED


def test_total_of_two_zeroes_is_zero() -> None:
    metric = normalized()["합성키워드-B"]
    assert metric.monthly_total_searches.value == 0
    assert metric.monthly_total_searches.quality is ValueQuality.EXACT


def test_total_of_two_below_threshold_values_is_a_range_not_a_number() -> None:
    metric = normalized()["합성키워드-C"]
    total = metric.monthly_total_searches
    assert total.value is None
    assert total.quality is ValueQuality.RANGE
    assert total.upper_bound_exclusive == 2 * BELOW_THRESHOLD_UPPER_BOUND_EXCLUSIVE


def test_total_is_not_computed_when_a_device_figure_is_suppressed() -> None:
    metric = normalized()["합성키워드-D"]
    total = metric.monthly_total_searches
    assert total.value is None
    assert total.quality is not ValueQuality.EXACT
    # 4444 alone must not be presented as the total.
    assert total.value != 4444


# --------------------------------------------------------------------------- #
# Schema drift
# --------------------------------------------------------------------------- #


def test_renamed_fields_are_reported_missing_rather_than_defaulted_to_zero() -> None:
    payload = load("searchad_schema_drift_synthetic.json")
    response = normalize_keywordstool(
        payload,
        collected_at=COLLECTED_AT,
        raw_bytes=load_bytes("searchad_schema_drift_synthetic.json"),
    )
    metric = response.metrics[0]
    assert metric.monthly_pc_searches.value is None
    assert metric.monthly_pc_searches.quality is ValueQuality.MISSING


def test_unmapped_fields_are_recorded_so_a_schema_change_is_visible() -> None:
    response = normalize_keywordstool(
        load("searchad_schema_drift_synthetic.json"),
        collected_at=COLLECTED_AT,
        raw_bytes=load_bytes("searchad_schema_drift_synthetic.json"),
    )
    assert "someBrandNewFieldVeoHasNeverSeen" in response.unmapped_fields
    assert "monthlyPcSearchVolume" in response.unmapped_fields


def test_a_response_without_the_keyword_list_is_a_schema_error() -> None:
    with pytest.raises(NaverSchemaError):
        normalize_keywordstool({"somethingElse": []}, collected_at=COLLECTED_AT, raw_bytes=b"{}")


def test_a_row_without_a_keyword_is_a_schema_error() -> None:
    with pytest.raises(NaverSchemaError):
        normalize_keywordstool(
            {"keywordList": [{"monthlyPcQcCnt": 1}]},
            collected_at=COLLECTED_AT,
            raw_bytes=b"{}",
        )


def test_an_unparseable_count_is_missing_not_zero() -> None:
    response = normalize_keywordstool(
        {"keywordList": [{"relKeyword": "합성키워드-Z", "monthlyPcQcCnt": "알 수 없음"}]},
        collected_at=COLLECTED_AT,
        raw_bytes=b"{}",
    )
    count = response.metrics[0].monthly_pc_searches
    assert count.value is None
    assert count.quality is ValueQuality.MISSING


# --------------------------------------------------------------------------- #
# SearchCount refuses to be constructed dishonestly
# --------------------------------------------------------------------------- #


def test_search_count_cannot_hold_a_value_and_claim_it_is_missing() -> None:
    with pytest.raises(ValueError, match="quality"):
        SearchCount(value=5, quality=ValueQuality.MISSING)


def test_search_count_cannot_claim_an_exact_value_it_does_not_have() -> None:
    with pytest.raises(ValueError, match="quality"):
        SearchCount(value=None, quality=ValueQuality.EXACT)


def test_search_count_rejects_a_negative_count() -> None:
    with pytest.raises(ValueError, match="negative"):
        SearchCount(value=-1, quality=ValueQuality.EXACT)


# --------------------------------------------------------------------------- #
# The client
# --------------------------------------------------------------------------- #


def build_client(handler: object, **kwargs: object) -> NaverSearchAdClient:
    transport = httpx.MockTransport(handler)  # type: ignore[arg-type]
    return NaverSearchAdClient(
        credentials=CREDENTIALS,
        transport=transport,
        clock=lambda: COLLECTED_AT,
        **kwargs,  # type: ignore[arg-type]
    )


def test_client_signs_the_request_it_actually_sends() -> None:
    seen: dict[str, str] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen.update(dict(request.headers))
        return httpx.Response(200, json=load("searchad_keywordstool_synthetic.json"))

    client = build_client(handler)
    outcome = client.lookup(["합성키워드-A"])

    assert outcome.value is not UNKNOWN
    assert seen["x-api-key"] == "synthetic-access-license"
    assert seen["x-customer"] == "9999999"
    assert seen["x-signature"]
    assert seen["x-timestamp"]
    assert "synthetic-secret" not in " ".join(seen.values())


def test_client_requests_the_documented_path_and_parameters() -> None:
    seen: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["path"] = request.url.path
        seen["params"] = dict(request.url.params)
        return httpx.Response(200, json=load("searchad_keywordstool_synthetic.json"))

    build_client(handler).lookup(["합성키워드-A", "합성키워드-B"])
    assert seen["path"] == KEYWORDSTOOL_PATH
    params = seen["params"]
    assert isinstance(params, dict)
    assert params["hintKeywords"] == "합성키워드-A,합성키워드-B"
    assert params["showDetail"] == "1"


@pytest.mark.parametrize("status", [401, 403, 429, 500, 503])
def test_a_failing_call_returns_unknown_and_never_a_number(status: int) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status, json={"title": "error"})

    client = build_client(handler, sleep=lambda seconds: None)
    outcome = client.lookup(["합성키워드-A"])
    assert outcome.value is UNKNOWN
    assert outcome.failure is not None
    assert outcome.failure.reason_ko


def test_a_timeout_returns_unknown() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("slow", request=request)

    client = build_client(handler, sleep=lambda seconds: None)
    outcome = client.lookup(["합성키워드-A"])
    assert outcome.value is UNKNOWN


def test_a_body_that_is_not_json_is_a_schema_failure_not_an_empty_result() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=b"<html>maintenance</html>")

    client = build_client(handler, sleep=lambda seconds: None)
    outcome = client.lookup(["합성키워드-A"])
    assert outcome.value is UNKNOWN
    assert outcome.failure is not None


def test_client_without_a_credential_is_disabled_and_never_dials() -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(200, json={"keywordList": []})

    client = NaverSearchAdClient(
        credentials=None, transport=httpx.MockTransport(handler), clock=lambda: COLLECTED_AT
    )
    assert client.state is ProviderState.DISABLED_NO_CREDENTIAL

    outcome = client.lookup(["합성키워드-A"])
    assert calls == 0
    assert outcome.value is UNKNOWN
    assert outcome.failure is not None
    assert outcome.failure.provider_state is ProviderState.DISABLED_NO_CREDENTIAL


def test_client_refuses_an_oversized_response() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=b"x" * 4096)

    client = build_client(handler, max_response_bytes=1024, sleep=lambda seconds: None)
    outcome = client.lookup(["합성키워드-A"])
    assert outcome.value is UNKNOWN
