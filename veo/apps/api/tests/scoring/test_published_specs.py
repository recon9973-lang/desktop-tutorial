"""Integrity of the published VEO-LAB specifications themselves."""

from __future__ import annotations

import pytest

from veo.scoring import available_specs, latest_published, load_spec

#: 디스크에 있어야 하는 명세와 그 가중치 합. 버전은 개정되므로 **발행된 최신본**을
#: 기준으로 본다 — 여기에 버전을 고정해 두면 명세를 고칠 때마다 관련 없는 테스트가
#: 깨지고, 그러다 보면 기대값을 기계적으로 갱신하게 되어 검사의 의미가 사라진다.
PUBLISHED = [
    ("veo.seo.readiness", 100.0),
    ("veo.geo.readiness", 100.0),
]


def test_expected_specs_are_on_disk() -> None:
    found = available_specs()
    assert "veo.seo.readiness" in found
    assert "veo.geo.readiness" in found


@pytest.mark.parametrize(("spec_id", "weight_total"), PUBLISHED)
def test_category_weights_sum_to_declared_total(spec_id: str, weight_total: float) -> None:
    spec = latest_published(spec_id)
    assert sum(c.weight for c in spec.categories) == pytest.approx(weight_total)


@pytest.mark.parametrize(("spec_id", "_weight"), PUBLISHED)
def test_published_spec_loads_and_is_marked_published(spec_id: str, _weight: float) -> None:
    spec = latest_published(spec_id)
    assert spec.status == "PUBLISHED"
    assert spec.methodology_owner == "VEO-LAB"
    assert spec.implementation_owner == "VENOM"
    assert spec.score_meaning.is_rank_prediction is False


@pytest.mark.parametrize(("spec_id", "_weight"), PUBLISHED)
def test_checksum_is_stable_across_loads(spec_id: str, _weight: float) -> None:
    assert latest_published(spec_id).checksum == latest_published(spec_id).checksum


@pytest.mark.parametrize(("spec_id", "_weight"), PUBLISHED)
def test_bands_cover_zero_to_one_hundred_without_gaps(spec_id: str, _weight: float) -> None:
    spec = latest_published(spec_id)
    for score in (0.0, 12.5, 25.0, 49.9, 50.0, 74.9, 85.0, 99.9, 100.0):
        assert spec.band_for(score) is not None, f"no band covers {score}"


@pytest.mark.parametrize(("spec_id", "_weight"), PUBLISHED)
def test_every_check_declares_required_evidence(spec_id: str, _weight: float) -> None:
    spec = latest_published(spec_id)
    for category in spec.categories:
        for check in category.checks:
            assert check.evidence_required, (
                f"{check.id} declares no evidence — every VEO result must be traceable "
                "to raw material"
            )


def test_latest_published_resolves() -> None:
    """발행본이 하나는 있어야 하고, 그 상태가 PUBLISHED 여야 한다."""
    for spec_id, _ in PUBLISHED:
        spec = latest_published(spec_id)
        assert spec.status == "PUBLISHED"
        assert spec.version in available_specs()[spec_id]


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
    for spec_id, _ in PUBLISHED:
        spec = latest_published(spec_id)
        for cap in spec.caps:
            assert cap.reason_ko and cap.release_condition_ko
