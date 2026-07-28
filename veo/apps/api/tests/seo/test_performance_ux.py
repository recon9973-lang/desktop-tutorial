"""성능·사용자 경험.

The three lab metrics and the one field metric are only ever read from a provider. With
no credential they are UNKNOWN with a Korean reason — never a guess, never a FAIL. Lab
and field values are kept apart: a Lighthouse run and a CrUX record are different
measurements of different things and are never merged into one figure.
"""

from __future__ import annotations

import dataclasses

from tests.seo.support import (
    ALL_PROVIDERS_ENABLED,
    build_context,
    by_id,
    healthy_provider_payloads,
    issues_for,
    status_of,
)

from veo.contracts.enums import ProviderState
from veo.scoring import CheckStatus
from veo.seo.collectors import PerformanceUxCollector

COLLECTOR = PerformanceUxCollector()

LAB_CHECKS = ("seo.perf.lcp_lab", "seo.perf.cls_lab", "seo.perf.tbt_lab")


def run(fixture: str, **overrides: object):
    return COLLECTOR.collect(build_context(fixture, **overrides))  # type: ignore[arg-type]


def enabled(fixture: str = "healthy"):
    context = build_context(fixture)
    return COLLECTOR.collect(
        dataclasses.replace(
            context,
            provider_states=dict(ALL_PROVIDERS_ENABLED),
            provider_payloads=healthy_provider_payloads(tuple(context.documents)),
        )
    )


# --------------------------------------------------------------------------- #
# No credential means UNKNOWN. This is the single most important rule here.
# --------------------------------------------------------------------------- #


def test_every_lab_metric_is_unknown_without_a_pagespeed_credential() -> None:
    result = run("healthy")
    for check_id in LAB_CHECKS:
        outcome = by_id(result)[check_id]
        assert outcome.status is CheckStatus.UNKNOWN
        assert outcome.note
        assert outcome.observed_value is None


def test_an_unmeasured_metric_is_never_reported_as_a_failure() -> None:
    result = run("healthy")
    for check_id in (*LAB_CHECKS, "seo.perf.inp_field"):
        assert by_id(result)[check_id].status is not CheckStatus.FAIL


def test_a_degraded_provider_is_also_unknown() -> None:
    context = build_context("healthy")
    context = dataclasses.replace(
        context, provider_states={"GOOGLE_PAGESPEED": ProviderState.DEGRADED}
    )
    assert by_id(COLLECTOR.collect(context))["seo.perf.lcp_lab"].status is CheckStatus.UNKNOWN


def test_an_enabled_provider_that_returned_nothing_for_a_url_is_still_unknown() -> None:
    context = build_context("healthy")
    context = dataclasses.replace(
        context,
        provider_states={"GOOGLE_PAGESPEED": ProviderState.ENABLED},
        provider_payloads={"GOOGLE_PAGESPEED": {}},
    )
    assert by_id(COLLECTOR.collect(context))["seo.perf.lcp_lab"].status is CheckStatus.UNKNOWN


# --------------------------------------------------------------------------- #
# With a credential, the provider's own verdict is read
# --------------------------------------------------------------------------- #


def test_good_lab_values_pass() -> None:
    result = enabled()
    for check_id in LAB_CHECKS:
        assert by_id(result)[check_id].status is CheckStatus.PASS


def test_a_poor_lab_value_fails_and_records_what_the_provider_reported() -> None:
    context = build_context("healthy")
    payloads = healthy_provider_payloads(tuple(context.documents))
    pagespeed = dict(payloads["GOOGLE_PAGESPEED"])  # type: ignore[arg-type]
    for url in list(pagespeed):
        pagespeed[url] = {
            "lighthouse": {
                "largest-contentful-paint": {"score": 0.12, "display_value": "6.4초"},
                "cumulative-layout-shift": {"score": 1.0, "display_value": "0.01"},
                "total-blocking-time": {"score": 0.95, "display_value": "60밀리초"},
            }
        }
    payloads["GOOGLE_PAGESPEED"] = pagespeed
    context = dataclasses.replace(
        context,
        provider_states=dict(ALL_PROVIDERS_ENABLED),
        provider_payloads=payloads,
    )
    result = COLLECTOR.collect(context)
    outcome = by_id(result)["seo.perf.lcp_lab"]
    assert outcome.status is CheckStatus.FAIL
    assert outcome.observed_value is not None
    assert issues_for(result, "seo.perf.lcp_lab")


def test_the_field_metric_passes_from_a_crux_record() -> None:
    assert by_id(enabled())["seo.perf.inp_field"].status is CheckStatus.PASS


def test_a_url_with_no_crux_sample_is_not_applicable() -> None:
    context = build_context("healthy")
    context = dataclasses.replace(
        context,
        provider_states={"GOOGLE_CRUX": ProviderState.ENABLED},
        provider_payloads={"GOOGLE_CRUX": {url: {"metrics": {}} for url in context.documents}},
    )
    outcome = by_id(COLLECTOR.collect(context))["seo.perf.inp_field"]
    assert outcome.status is CheckStatus.NOT_APPLICABLE


def test_lab_and_field_are_never_read_from_the_same_provider() -> None:
    """A CrUX credential alone must not make the lab metrics measurable, or vice versa."""
    context = build_context("healthy")
    context = dataclasses.replace(
        context,
        provider_states={"GOOGLE_CRUX": ProviderState.ENABLED},
        provider_payloads={
            "GOOGLE_CRUX": {
                url: {"metrics": {"INTERACTION_TO_NEXT_PAINT": {"category": "FAST"}}}
                for url in context.documents
            }
        },
    )
    result = COLLECTOR.collect(context)
    assert by_id(result)["seo.perf.inp_field"].status is CheckStatus.PASS
    for check_id in LAB_CHECKS:
        assert by_id(result)[check_id].status is CheckStatus.UNKNOWN


# --------------------------------------------------------------------------- #
# The three checks that need no provider at all
# --------------------------------------------------------------------------- #


def test_a_declared_mobile_viewport_passes() -> None:
    assert status_of(run("healthy"), "seo.ux.mobile_viewport") is CheckStatus.PASS


def test_a_missing_viewport_fails() -> None:
    result = run("duplicate_metadata")
    assert status_of(result, "seo.ux.mobile_viewport") is CheckStatus.FAIL
    assert issues_for(result, "seo.ux.mobile_viewport")


def test_a_viewport_that_blocks_zooming_does_not_pass() -> None:
    context = build_context("healthy")
    blocked = {
        url: dataclasses.replace(
            document,
            body=document.body.replace(
                b'content="width=device-width, initial-scale=1"',
                b'content="width=device-width, initial-scale=1, user-scalable=no"',
            ),
        )
        for url, document in context.documents.items()
    }
    context = dataclasses.replace(context, documents=blocked, primary_document=None)
    outcome = by_id(COLLECTOR.collect(context))["seo.ux.mobile_viewport"]
    assert outcome.status is not CheckStatus.PASS


def test_https_passes_when_every_url_was_served_over_tls() -> None:
    assert status_of(run("healthy"), "seo.security.https_valid") is CheckStatus.PASS


def test_a_plain_http_url_fails_the_https_check() -> None:
    context = build_context("healthy")
    downgraded = {
        url.replace("https://", "http://"): dataclasses.replace(
            document, final_url=document.final_url.replace("https://", "http://")
        )
        for url, document in context.documents.items()
    }
    context = dataclasses.replace(
        context,
        target_url="http://healthy.example.kr/",
        documents=downgraded,
        primary_document=None,
        url_importance={
            url.replace("https://", "http://"): value
            for url, value in context.url_importance.items()
        },
    )
    assert by_id(COLLECTOR.collect(context))["seo.security.https_valid"].status is CheckStatus.FAIL


def test_no_mixed_content_passes() -> None:
    assert status_of(run("healthy"), "seo.security.no_mixed_content") is CheckStatus.PASS


def test_an_http_image_on_an_https_page_fails() -> None:
    result = run("duplicate_metadata")
    assert status_of(result, "seo.security.no_mixed_content") is CheckStatus.FAIL
    issue = issues_for(result, "seo.security.no_mixed_content")[0]
    assert issue.affected_urls


def test_mixed_content_prefers_the_rendered_dom_when_one_exists() -> None:
    """What the browser actually loaded beats what the source said it would."""
    context = build_context("healthy")
    injected = dict(context.rendered_dom)
    injected["https://healthy.example.kr/"] = (
        '<html><body><img src="http://tracker.example.com/pixel.gif" alt="x"></body></html>'
    )
    context = dataclasses.replace(context, rendered_dom=injected)
    assert (
        by_id(COLLECTOR.collect(context))["seo.security.no_mixed_content"].status
        is CheckStatus.FAIL
    )
