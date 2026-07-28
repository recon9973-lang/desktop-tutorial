"""The risk taxonomy: which kinds exist, and where severity comes from.

Severity is read from a versioned specification table, never chosen at the call site.
The regulated bands — medical, legal, pricing, contractual — are the point of the whole
module: for a hospital, "the AI says you perform a procedure you do not" is a regulatory
problem, not a marketing nuisance.
"""

from __future__ import annotations

import pytest

from veo.observations.risk.taxonomy import (
    BAND_SEVERITY,
    RISK_TAXONOMY,
    ClaimDomain,
    RiskBand,
    RiskKind,
)
from veo.scoring.models import Severity

#: The exact vocabulary ``claim_assessments.assessment_type`` documents. Owned by the
#: integration maintainer; this module consumes it and may not widen it.
STORED_ASSESSMENT_TYPES = frozenset(
    {
        "CLAIM_ACCURACY",
        "CITATION_ENTAILMENT",
        "CITATION_COMPLETENESS",
        "ENTITY_DISAMBIGUATION",
        "RECOMMENDATION",
        "SENTIMENT",
        "STALENESS",
    }
)


def test_every_risk_kind_from_the_methodology_has_a_spec() -> None:
    expected = {
        RiskKind.CLAIM_ACCURACY,
        RiskKind.CITATION_ENTAILMENT,
        RiskKind.CITATION_COMPLETENESS,
        RiskKind.ENTITY_DISAMBIGUATION,
        RiskKind.RECOMMENDATION_INCLUSION,
        RiskKind.RECOMMENDATION_EXCLUSION,
        RiskKind.SENTIMENT_WITH_GROUNDS,
        RiskKind.STALENESS,
    }
    assert {spec.kind for spec in RISK_TAXONOMY.kinds} == expected


def test_every_kind_stores_as_a_value_the_schema_already_accepts() -> None:
    for kind in RiskKind:
        assert kind.storage_value in STORED_ASSESSMENT_TYPES


def test_the_ambiguous_stored_value_is_refused_rather_than_guessed() -> None:
    # RECOMMENDATION covers two different findings. Reading it back and picking one
    # would silently turn "the clinic was left out" into "the clinic was wrongly
    # recommended". The round trip refuses instead.
    assert RiskKind.from_storage("SENTIMENT") is RiskKind.SENTIMENT_WITH_GROUNDS
    with pytest.raises(ValueError, match="RECOMMENDATION"):
        RiskKind.from_storage("RECOMMENDATION")


def test_the_four_bands_carry_the_korean_names_from_the_methodology() -> None:
    assert [band.label_ko for band in RiskBand] == ["치명", "높음", "중간", "낮음"]


def test_bands_map_onto_the_platform_severity_vocabulary() -> None:
    assert BAND_SEVERITY[RiskBand.FATAL] is Severity.BLOCKER
    assert set(BAND_SEVERITY) == set(RiskBand)


@pytest.mark.parametrize(
    "domain",
    [ClaimDomain.MEDICAL, ClaimDomain.LEGAL, ClaimDomain.PRICING, ClaimDomain.CONTRACTUAL],
)
@pytest.mark.parametrize("kind", list(RiskKind))
def test_regulated_subject_matter_is_always_the_top_band(
    domain: ClaimDomain, kind: RiskKind
) -> None:
    # Even a stale-information finding is fatal when the stale information is a price
    # or a licensed procedure.
    assert RISK_TAXONOMY.band_for(kind=kind, domain=domain) is RiskBand.FATAL


def test_outside_the_regulated_domains_the_band_comes_from_the_spec_table() -> None:
    spec = RISK_TAXONOMY.spec_for(RiskKind.STALENESS)
    assert RISK_TAXONOMY.band_for(kind=RiskKind.STALENESS, domain=ClaimDomain.GENERAL) is (
        spec.base_band
    )
    assert spec.base_band is not RiskBand.FATAL


def test_severity_is_derived_from_the_spec_not_from_a_number_at_the_call_site() -> None:
    assert (
        RISK_TAXONOMY.severity_for(kind=RiskKind.CLAIM_ACCURACY, domain=ClaimDomain.MEDICAL)
        is Severity.BLOCKER
    )


def test_the_review_threshold_is_declared_by_the_taxonomy() -> None:
    assert RISK_TAXONOMY.requires_human_review(RiskBand.FATAL) is True
    assert RISK_TAXONOMY.requires_human_review(RiskBand.HIGH) is True
    assert RISK_TAXONOMY.requires_human_review(RiskBand.MEDIUM) is False
    assert RISK_TAXONOMY.requires_human_review(RiskBand.LOW) is False


def test_every_kind_states_what_a_rule_decides_and_what_needs_a_model() -> None:
    for spec in RISK_TAXONOMY.kinds:
        assert spec.definition_ko.strip()
        assert spec.deterministic_ko.strip()
        assert spec.needs_model_ko.strip()
        assert spec.examples, f"{spec.kind}: 실무 예시가 없습니다"


def test_every_worked_example_is_marked_fictional() -> None:
    from veo.observations.risk.taxonomy import FICTIONAL_EXAMPLE_MARKER

    for spec in RISK_TAXONOMY.kinds:
        for example in spec.examples:
            assert FICTIONAL_EXAMPLE_MARKER in example.situation_ko, (
                f"{spec.kind}: 예시가 가상 사례로 표기되지 않았습니다 — {example.situation_ko}"
            )


def test_the_taxonomy_is_versioned() -> None:
    assert RISK_TAXONOMY.version
    assert RISK_TAXONOMY.as_dict()["version"] == RISK_TAXONOMY.version
