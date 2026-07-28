"""PageSpeed Insights: a lab simulation, and — sometimes — a field block beside it.

The rule this suite defends is the one the SEO specification already encodes by giving
``seo.perf.*_lab`` and ``seo.perf.inp_field`` separate check ids: **a Lighthouse number
and a CrUX number answer different questions and may never end up in the same field.**
That is asserted by type here, not by naming convention, because a convention survives
exactly until someone writes ``metrics.update(other_metrics)``.
"""

from __future__ import annotations

from datetime import UTC, datetime

import httpx
import pytest
from google_fixtures import SITE_URL, runpagespeed_response
from pydantic import SecretStr

from veo.contracts.enums import DataSource, ProviderState, ValueQuality
from veo.providers.google.credentials import PageSpeedCredentials
from veo.providers.google.crux import FieldDataState, FieldMeasurement, FieldMetric
from veo.providers.google.errors import UNKNOWN
from veo.providers.google.pagespeed import (
    RUNPAGESPEED_PATH,
    LabAudit,
    LabMeasurement,
    PageSpeedClient,
    PageSpeedResult,
    Strategy,
    lab_payload,
    normalize_runpagespeed,
)

COLLECTED_AT = datetime(2026, 7, 28, 3, 5, tzinfo=UTC)
CREDENTIALS = PageSpeedCredentials(api_key=SecretStr("synthetic-pagespeed-key"))


def normalized(**kwargs: object) -> PageSpeedResult:
    payload = runpagespeed_response(**kwargs)  # type: ignore[arg-type]
    return normalize_runpagespeed(
        payload,
        url=SITE_URL,
        strategy=Strategy.MOBILE,
        collected_at=COLLECTED_AT,
        raw_bytes=b"{}",
    )


def build_client(handler: object, **kwargs: object) -> PageSpeedClient:
    return PageSpeedClient(
        credentials=CREDENTIALS,
        transport=httpx.MockTransport(handler),  # type: ignore[arg-type]
        clock=lambda: COLLECTED_AT,
        **kwargs,  # type: ignore[arg-type]
    )


# --------------------------------------------------------------------------- #
# Lab and field never merge
# --------------------------------------------------------------------------- #


def test_lab_and_field_are_different_types_not_a_naming_convention() -> None:
    result = normalized()
    assert isinstance(result.lab, LabMeasurement)
    assert isinstance(result.field, FieldMeasurement)

    for audit in result.lab.audits.values():
        assert isinstance(audit, LabAudit)
        assert not isinstance(audit, FieldMetric)
    for metric in result.field.metrics.values():
        assert isinstance(metric, FieldMetric)
        assert not isinstance(metric, LabAudit)


def test_lab_values_carry_the_pagespeed_source_and_field_values_carry_crux() -> None:
    result = normalized()
    for audit in result.lab.audits.values():
        assert audit.source is DataSource.GOOGLE_PAGESPEED
    for metric in result.field.metrics.values():
        assert metric.source is DataSource.GOOGLE_CRUX


def test_a_lab_audit_cannot_be_built_with_a_field_source() -> None:
    """The separation is enforced at construction, not left to the caller's care."""
    with pytest.raises(ValueError, match="source"):
        LabAudit(
            audit_id="largest-contentful-paint",
            score=0.9,
            display_value="1.6 s",
            numeric_value=1600.0,
            numeric_unit="millisecond",
            quality=ValueQuality.EXACT,
            source=DataSource.GOOGLE_CRUX,
        )


def test_a_field_metric_cannot_be_built_with_a_lab_source() -> None:
    with pytest.raises(ValueError, match="source"):
        FieldMetric(
            metric_id="INTERACTION_TO_NEXT_PAINT",
            category="FAST",
            category_quality=ValueQuality.EXACT,
            percentile=120.0,
            percentile_quality=ValueQuality.EXACT,
            source=DataSource.GOOGLE_PAGESPEED,
        )


def test_the_two_payloads_share_no_keys_of_the_other_kind() -> None:
    result = normalized()
    lab_entry = lab_payload([result.lab])[SITE_URL]
    assert "lighthouse" in lab_entry
    assert "metrics" not in lab_entry


# --------------------------------------------------------------------------- #
# Lab mapping
# --------------------------------------------------------------------------- #


def test_every_documented_lab_audit_is_mapped() -> None:
    audits = normalized().lab.audits
    for audit_id in (
        "largest-contentful-paint",
        "cumulative-layout-shift",
        "total-blocking-time",
        "first-contentful-paint",
    ):
        assert audits[audit_id].score is not None


def test_the_strategy_is_part_of_the_measurement() -> None:
    """Mobile and desktop are different measurements of the same URL, not one number."""
    result = normalized()
    assert result.lab.strategy is Strategy.MOBILE
    entry = lab_payload([result.lab])[SITE_URL]["lighthouse"]
    assert entry["largest-contentful-paint"]["strategy"] == "MOBILE"


def test_every_value_carries_source_and_collection_time() -> None:
    result = normalized()
    entry = lab_payload([result.lab])[SITE_URL]
    assert entry["source"] == DataSource.GOOGLE_PAGESPEED.value
    assert entry["collected_at"] == COLLECTED_AT.isoformat()
    for audit in entry["lighthouse"].values():
        assert audit["source"] == DataSource.GOOGLE_PAGESPEED.value
        assert audit["collected_at"] == COLLECTED_AT.isoformat()
        assert audit["quality"] in {q.value for q in ValueQuality}


def test_an_audit_google_could_not_run_is_missing_not_zero() -> None:
    payload = runpagespeed_response()
    payload["lighthouseResult"]["audits"]["total-blocking-time"] = {
        "id": "total-blocking-time",
        "score": None,
        "scoreDisplayMode": "notApplicable",
    }
    result = normalize_runpagespeed(
        payload, url=SITE_URL, strategy=Strategy.MOBILE, collected_at=COLLECTED_AT, raw_bytes=b"{}"
    )
    audit = result.lab.audits["total-blocking-time"]
    assert audit.score is None
    assert audit.score != 0
    assert audit.quality is ValueQuality.MISSING


# --------------------------------------------------------------------------- #
# Field block
# --------------------------------------------------------------------------- #


def test_a_url_without_a_crux_sample_is_not_applicable_and_not_zero() -> None:
    result = normalized(with_field_data=False)
    field = result.field
    assert field.state is FieldDataState.NOT_APPLICABLE
    assert field.metrics == {}
    assert field.reason_ko
    for value in (0, 0.0, False):
        assert field.state != value


def test_a_present_field_block_reports_the_providers_own_category() -> None:
    field = normalized().field
    assert field.state is FieldDataState.AVAILABLE
    inp = field.metrics["INTERACTION_TO_NEXT_PAINT"]
    assert inp.category == "FAST"
    assert inp.percentile == 120


def test_a_slow_field_category_is_carried_through_verbatim() -> None:
    field = normalized(inp_category="SLOW").field
    assert field.metrics["INTERACTION_TO_NEXT_PAINT"].category == "SLOW"


# --------------------------------------------------------------------------- #
# The client
# --------------------------------------------------------------------------- #


def test_the_client_calls_the_documented_endpoint_with_the_strategy() -> None:
    seen: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["path"] = request.url.path
        seen["params"] = dict(request.url.params)
        return httpx.Response(200, json=runpagespeed_response())

    outcome = build_client(handler).measure(SITE_URL, strategy=Strategy.DESKTOP)
    assert outcome.value is not UNKNOWN
    assert seen["path"] == RUNPAGESPEED_PATH
    params = seen["params"]
    assert isinstance(params, dict)
    assert params["url"] == SITE_URL
    assert params["strategy"] == "DESKTOP"
    assert params["key"] == "synthetic-pagespeed-key"


def test_without_a_credential_no_connection_is_opened() -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(200, json=runpagespeed_response())

    client = PageSpeedClient(
        credentials=None,
        transport=httpx.MockTransport(handler),
        clock=lambda: COLLECTED_AT,
    )
    assert client.state is ProviderState.DISABLED_NO_CREDENTIAL

    outcome = client.measure(SITE_URL)
    assert calls == 0
    assert outcome.value is UNKNOWN
    assert outcome.failure is not None
    assert outcome.failure.provider_state is ProviderState.DISABLED_NO_CREDENTIAL
    assert outcome.failure.reason_ko


def test_a_placeholder_credential_is_disabled_invalid_and_never_dials() -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(200, json=runpagespeed_response())

    client = PageSpeedClient(
        credentials=None,
        unavailable_state=ProviderState.DISABLED_INVALID_CREDENTIAL,
        transport=httpx.MockTransport(handler),
        clock=lambda: COLLECTED_AT,
    )
    assert client.state is ProviderState.DISABLED_INVALID_CREDENTIAL

    outcome = client.measure(SITE_URL)
    assert calls == 0
    assert outcome.failure is not None
    assert outcome.failure.provider_state is ProviderState.DISABLED_INVALID_CREDENTIAL


@pytest.mark.parametrize("status", [401, 403, 429, 500, 503])
def test_each_failing_status_maps_to_a_typed_error_with_a_fixed_korean_message(
    status: int,
) -> None:
    leak = "quota exceeded for key AIzaSyD-synthetic-leaked-key"

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status, json={"error": {"message": leak}})

    outcome = build_client(handler, sleep=lambda seconds: None).measure(SITE_URL)
    assert outcome.value is UNKNOWN
    assert outcome.failure is not None
    assert outcome.failure.reason_ko
    assert leak not in outcome.failure.reason_ko
    assert "AIzaSy" not in outcome.failure.reason_ko


def test_the_korean_message_differs_per_error_class() -> None:
    messages = set()
    for status in (401, 403, 429, 500):

        def handler(request: httpx.Request, code: int = status) -> httpx.Response:
            return httpx.Response(code, json={"error": {"message": "x"}})

        outcome = build_client(handler, sleep=lambda seconds: None).measure(SITE_URL)
        assert outcome.failure is not None
        messages.add(outcome.failure.reason_ko)
    assert len(messages) == 4


def test_a_timeout_is_unknown_rather_than_an_exception() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("slow", request=request)

    outcome = build_client(handler, sleep=lambda seconds: None).measure(SITE_URL)
    assert outcome.value is UNKNOWN
    assert outcome.failure is not None
    assert outcome.failure.retryable is True


def test_a_response_that_is_not_the_documented_shape_is_a_schema_failure() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"kind": "pagespeedonline#result"})

    outcome = build_client(handler, sleep=lambda seconds: None).measure(SITE_URL)
    assert outcome.value is UNKNOWN
    assert outcome.failure is not None


def test_an_oversized_response_is_refused() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=b"x" * 8192)

    outcome = build_client(
        handler, sleep=lambda seconds: None, max_response_bytes=1024
    ).measure(SITE_URL)
    assert outcome.value is UNKNOWN


def test_the_api_key_never_appears_in_a_repr_or_a_failure() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"error": {"message": "bad key"}})

    client = build_client(handler, sleep=lambda seconds: None)
    outcome = client.measure(SITE_URL)
    assert "synthetic-pagespeed-key" not in repr(client)
    assert outcome.failure is not None
    assert "synthetic-pagespeed-key" not in outcome.failure.reason_ko
