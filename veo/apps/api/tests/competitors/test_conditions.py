"""The conditions block must be *read*, never assumed.

Every field here has a way of going wrong quietly. A hardcoded locale makes a Korean and
an English measurement look alike; a defaulted device makes a mobile crawl comparable to
a desktop one; counting requested pages instead of collected ones hides a failed crawl.
So each field is asserted against a source of truth in the scan itself.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from veo.collect.contract import CollectionContext
from veo.common.security.fetcher import FetchedDocument, FetchHop
from veo.competitors.conditions import (
    MissingConditionError,
    conditions_from_geo_report,
    conditions_from_score,
    conditions_from_seo_scan,
    enabled_providers,
)
from veo.contracts.enums import ProviderState
from veo.geo.service import GeoReadinessReport
from veo.scoring import (
    CheckOutcome,
    CheckStatus,
    ScoreResult,
    ScoringDomain,
    latest_published,
)
from veo.seo.service import SeoScanResult

COLLECTED_AT = datetime(2026, 7, 1, 9, 0, tzinfo=UTC)


def document(url: str) -> FetchedDocument:
    body = b"<html><body>hi</body></html>"
    return FetchedDocument(
        requested_url=url,
        final_url=url,
        status=200,
        headers={"content-type": "text/html"},
        body=body,
        content_hash="0" * 64,
        content_type="text/html",
        charset="utf-8",
        hops=(FetchHop(url=url, status=200, resolved_ip="", location=None, elapsed_ms=0),),
        resolved_ips=(),
        fetched_at=COLLECTED_AT,
        elapsed_ms=1,
    )


def context(
    *,
    urls: tuple[str, ...] = ("https://a.example/", "https://a.example/b"),
    locale: str = "ko-KR",
    provider_states: dict[str, ProviderState] | None = None,
) -> CollectionContext:
    spec = latest_published("veo.seo.readiness")
    return CollectionContext(
        target_url=urls[0] if urls else "https://a.example/",
        spec=spec,
        documents={url: document(url) for url in urls},
        provider_states=provider_states or {},
        locale=locale,
        collected_at=COLLECTED_AT,
    )


def score(
    *,
    spec_id: str = "veo.seo.readiness",
    spec_version: str = "1.0.0",
    spec_checksum: str = "b" * 64,
) -> ScoreResult:
    return ScoreResult(
        spec_id=spec_id,
        spec_version=spec_version,
        spec_checksum=spec_checksum,
        domain=ScoringDomain.SEO_READINESS,
        status="SCORED",
        overall_score=71.0,
        overall_score_before_caps=71.0,
        band_id="at_risk",
        coverage=0.8,
        confidence=0.75,
        effective_weight_total=100.0,
        categories=[],
        applied_caps=[],
        gates=[],
        outcomes=[
            CheckOutcome(
                check_id="seo.http.status_ok", status=CheckStatus.PASS, confidence=1.0
            )
        ],
        trace={},
    )


# --------------------------------------------------------------------------- #
# What is read, and from where
# --------------------------------------------------------------------------- #


def test_the_methodology_fields_come_from_the_score_not_from_the_caller() -> None:
    built = conditions_from_score(
        score(spec_version="1.0.0", spec_checksum="b" * 64),
        context(),
        collector_version="veo-collector/1.4.0",
        device="MOBILE",
        renderer="HEADLESS_CHROME",
    )

    assert built.spec_id == "veo.seo.readiness"
    assert built.spec_version == "1.0.0"
    assert built.spec_checksum == "b" * 64


def test_pages_examined_counts_the_documents_that_were_actually_collected() -> None:
    built = conditions_from_score(
        score(),
        context(urls=("https://a.example/", "https://a.example/b", "https://a.example/c")),
        collector_version="veo-collector/1.4.0",
        device="MOBILE",
        renderer="HEADLESS_CHROME",
    )
    assert built.pages_examined == 3


def test_a_crawl_that_collected_nothing_reports_zero_rather_than_pretending() -> None:
    built = conditions_from_score(
        score(),
        context(urls=()),
        collector_version="veo-collector/1.4.0",
        device="MOBILE",
        renderer="HEADLESS_CHROME",
    )
    assert built.pages_examined == 0


def test_locale_and_measurement_time_come_from_the_collection_context() -> None:
    built = conditions_from_score(
        score(),
        context(locale="en-US"),
        collector_version="veo-collector/1.4.0",
        device="DESKTOP",
        renderer="NONE",
    )
    assert built.locale == "en-US"
    assert built.measured_at == COLLECTED_AT


def test_only_providers_that_were_actually_enabled_are_listed() -> None:
    states = {
        "google_psi": ProviderState.ENABLED,
        "naver_searchad": ProviderState.DISABLED_NO_CREDENTIAL,
        "google_crux": ProviderState.CIRCUIT_OPEN,
        "gsc": ProviderState.ENABLED,
    }
    assert enabled_providers(states) == ("google_psi", "gsc")

    built = conditions_from_score(
        score(),
        context(provider_states=states),
        collector_version="veo-collector/1.4.0",
        device="MOBILE",
        renderer="HEADLESS_CHROME",
    )
    assert built.enabled_providers == ("google_psi", "gsc")


# --------------------------------------------------------------------------- #
# What may not be guessed
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    "missing", ["collector_version", "device", "renderer"]
)
def test_a_field_veo_cannot_derive_must_be_stated_and_may_not_be_blank(missing: str) -> None:
    values = {
        "collector_version": "veo-collector/1.4.0",
        "device": "MOBILE",
        "renderer": "HEADLESS_CHROME",
    }
    values[missing] = "   "

    with pytest.raises(MissingConditionError) as caught:
        conditions_from_score(score(), context(), **values)  # type: ignore[arg-type]

    assert missing in str(caught.value)


def test_two_scans_run_the_same_way_share_a_fingerprint() -> None:
    kwargs = {
        "collector_version": "veo-collector/1.4.0",
        "device": "MOBILE",
        "renderer": "HEADLESS_CHROME",
    }
    left = conditions_from_score(score(), context(), **kwargs)  # type: ignore[arg-type]
    right = conditions_from_score(
        score(),
        context(urls=("https://b.example/",)),
        **kwargs,  # type: ignore[arg-type]
    )
    # Different page counts, same setup: the fingerprint deliberately ignores scope.
    assert left.fingerprint == right.fingerprint
    assert left.pages_examined != right.pages_examined


def test_a_different_renderer_changes_the_fingerprint() -> None:
    left = conditions_from_score(
        score(),
        context(),
        collector_version="veo-collector/1.4.0",
        device="MOBILE",
        renderer="HEADLESS_CHROME",
    )
    right = conditions_from_score(
        score(),
        context(),
        collector_version="veo-collector/1.4.0",
        device="MOBILE",
        renderer="NONE",
    )
    assert left.fingerprint != right.fingerprint


# --------------------------------------------------------------------------- #
# The two engines both feed the same conditions block
# --------------------------------------------------------------------------- #


def test_an_seo_scan_result_produces_the_same_conditions_as_its_score() -> None:
    scan = SeoScanResult(
        score=score(),
        issues=(),
        evidence=(),
        notes_ko=(),
        summary_ko="테스트 요약",
        unknown_checks=(),
    )
    ctx = context()
    kwargs = {
        "collector_version": "veo-collector/1.4.0",
        "device": "MOBILE",
        "renderer": "HEADLESS_CHROME",
    }
    assert conditions_from_seo_scan(scan, ctx, **kwargs) == conditions_from_score(  # type: ignore[arg-type]
        scan.score, ctx, **kwargs  # type: ignore[arg-type]
    )


def test_a_geo_report_produces_conditions_carrying_the_geo_specification() -> None:
    spec = latest_published("veo.geo.readiness")
    report = GeoReadinessReport(
        spec=spec,
        score=score(spec_id=spec.spec_id, spec_version=spec.version, spec_checksum=spec.checksum),
        evidence=(),
        issues=(),
        notes_ko=(),
    )
    built = conditions_from_geo_report(
        report,
        context(),
        collector_version="veo-collector/1.4.0",
        device="MOBILE",
        renderer="HEADLESS_CHROME",
    )
    assert built.spec_id == "veo.geo.readiness"
    assert built.spec_checksum == spec.checksum
