"""Integrity of the published VEO-LAB specifications themselves."""

from __future__ import annotations

import pytest

from veo.scoring import available_specs, latest_published, load_spec

PUBLISHED = [
    ("veo.seo.readiness", "1.0.0", 100.0),
    ("veo.geo.readiness", "1.0.0", 100.0),
]


def test_expected_specs_are_on_disk() -> None:
    found = available_specs()
    assert "veo.seo.readiness" in found
    assert "veo.geo.readiness" in found


@pytest.mark.parametrize(("spec_id", "version", "weight_total"), PUBLISHED)
def test_category_weights_sum_to_declared_total(
    spec_id: str, version: str, weight_total: float
) -> None:
    spec = load_spec(spec_id, version)
    assert sum(c.weight for c in spec.categories) == pytest.approx(weight_total)


@pytest.mark.parametrize(("spec_id", "version", "_weight"), PUBLISHED)
def test_published_spec_loads_and_is_marked_published(
    spec_id: str, version: str, _weight: float
) -> None:
    spec = load_spec(spec_id, version)
    assert spec.status == "PUBLISHED"
    assert spec.methodology_owner == "VEO-LAB"
    assert spec.implementation_owner == "VENOM"
    assert spec.score_meaning.is_rank_prediction is False


@pytest.mark.parametrize(("spec_id", "version", "_weight"), PUBLISHED)
def test_checksum_is_stable_across_loads(spec_id: str, version: str, _weight: float) -> None:
    assert load_spec(spec_id, version).checksum == load_spec(spec_id, version).checksum


@pytest.mark.parametrize(("spec_id", "version", "_weight"), PUBLISHED)
def test_bands_cover_zero_to_one_hundred_without_gaps(
    spec_id: str, version: str, _weight: float
) -> None:
    spec = load_spec(spec_id, version)
    for score in (0.0, 12.5, 25.0, 49.9, 50.0, 74.9, 85.0, 99.9, 100.0):
        assert spec.band_for(score) is not None, f"no band covers {score}"


@pytest.mark.parametrize(("spec_id", "version", "_weight"), PUBLISHED)
def test_every_check_declares_required_evidence(
    spec_id: str, version: str, _weight: float
) -> None:
    spec = load_spec(spec_id, version)
    for category in spec.categories:
        for check in category.checks:
            assert check.evidence_required, (
                f"{check.id} declares no evidence — every VEO result must be traceable "
                "to raw material"
            )


def test_latest_published_resolves() -> None:
    assert latest_published("veo.seo.readiness").version == "1.0.0"
    assert latest_published("veo.geo.readiness").version == "1.0.0"


def test_geo_readiness_never_carries_observation_metrics() -> None:
    """Readiness and observed AI visibility must stay separate engines and scores."""
    spec = load_spec("veo.geo.readiness", "1.0.0")
    forbidden = ("mention", "citation_rate", "share_of_voice", "sov", "visibility")
    for category in spec.categories:
        for check in category.checks:
            lowered = check.id.lower()
            assert not any(token in lowered for token in forbidden), (
                f"{check.id} looks like an observation metric; observed AI visibility "
                "belongs to the observation engine, not the readiness score"
            )


def test_seo_caps_match_the_methodology_ceilings() -> None:
    spec = load_spec("veo.seo.readiness", "1.0.0")
    ceilings = {cap.id: cap.max_overall_score for cap in spec.caps}
    assert ceilings == {
        "sitewide_index_block": 25,
        "key_template_server_error": 35,
        "mass_cross_domain_canonical": 40,
        "sitemap_majority_invalid": 55,
        "https_or_mobile_failure": 60,
    }


def test_every_cap_states_a_release_condition() -> None:
    for spec_id, version, _ in PUBLISHED:
        spec = load_spec(spec_id, version)
        for cap in spec.caps:
            assert cap.reason_ko and cap.release_condition_ko
