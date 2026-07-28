"""Candidate validation and the Korean diff a reviewer reads instead of the YAML."""

from __future__ import annotations

import pytest
from tests.lab.support import (
    BASELINE_WEIGHTS,
    CANDIDATE_WEIGHTS,
    baseline_document,
    candidate_document,
    lab_document,
)

from veo.lab import validation
from veo.lab.errors import SpecificationRejectedError
from veo.scoring import ScoringSpec, build_spec


def _has_hangul(text: str) -> bool:
    return any("가" <= character <= "힣" for character in text)


@pytest.fixture
def baseline() -> ScoringSpec:
    return build_spec(baseline_document())


# --------------------------------------------------------------------------- #
# Validation
# --------------------------------------------------------------------------- #


def test_a_well_formed_candidate_validates(baseline: ScoringSpec) -> None:
    report = validation.validate_candidate(candidate_document(), baseline=baseline)
    assert report.ok, report.errors_ko
    assert report.errors_ko == ()
    assert report.category_weight_total == pytest.approx(100.0)


def test_a_document_that_fails_the_json_schema_is_rejected(baseline: ScoringSpec) -> None:
    document = candidate_document()
    del document["bands"]
    report = validation.validate_candidate(document, baseline=baseline)
    assert not report.ok
    assert report.errors_ko
    assert all(_has_hangul(line) for line in report.errors_ko)


def test_category_weights_must_total_one_hundred(baseline: ScoringSpec) -> None:
    document = lab_document(
        version="1.2.0", status="DRAFT", weights={"alpha": 60.0, "beta": 30.0}
    )
    report = validation.validate_candidate(document, baseline=baseline)
    assert not report.ok
    assert report.category_weight_total == pytest.approx(90.0)
    assert any("90" in line and _has_hangul(line) for line in report.errors_ko), report.errors_ko


def test_a_cap_referencing_an_undefined_check_is_named(baseline: ScoringSpec) -> None:
    document = candidate_document()
    document["caps"][0]["trigger"]["any_of"][0]["check_id"] = "lab.alpha.ghost"
    report = validation.validate_candidate(document, baseline=baseline)
    assert not report.ok
    assert any("lab.alpha.ghost" in line for line in report.errors_ko), report.errors_ko


def test_a_gate_referencing_an_undefined_check_is_named(baseline: ScoringSpec) -> None:
    document = candidate_document()
    document["gates"][0]["trigger"]["any_of"][0]["check_id"] = "lab.beta.ghost"
    report = validation.validate_candidate(document, baseline=baseline)
    assert not report.ok
    assert any("lab.beta.ghost" in line for line in report.errors_ko), report.errors_ko


def test_build_candidate_raises_with_a_korean_reason() -> None:
    document = candidate_document()
    document["categories"][0]["checks"][0]["severity"] = "APOCALYPTIC"
    with pytest.raises(SpecificationRejectedError) as caught:
        validation.build_candidate(document)
    assert _has_hangul(caught.value.message_ko)


def test_a_duplicate_check_id_is_rejected(baseline: ScoringSpec) -> None:
    document = candidate_document()
    document["categories"][1]["checks"][0]["id"] = "lab.alpha.one"
    report = validation.validate_candidate(document, baseline=baseline)
    assert not report.ok
    assert any("lab.alpha.one" in line for line in report.errors_ko), report.errors_ko


# --------------------------------------------------------------------------- #
# The Korean diff
# --------------------------------------------------------------------------- #


def test_the_diff_names_the_weight_that_actually_moved(baseline: ScoringSpec) -> None:
    candidate = build_spec(candidate_document())
    diff = validation.diff_specs(baseline, candidate)

    assert diff.has_changes
    moved = {change.category_id: change for change in diff.weight_changes}
    assert set(moved) == {"alpha", "beta"}
    assert moved["alpha"].before == pytest.approx(BASELINE_WEIGHTS["alpha"])
    assert moved["alpha"].after == pytest.approx(CANDIDATE_WEIGHTS["alpha"])

    lines = diff.lines_ko()
    alpha_line = next(line for line in lines if "alpha" in line)
    assert _has_hangul(alpha_line)
    assert "60" in alpha_line and "70" in alpha_line, alpha_line
    assert "알파" in alpha_line


def test_the_diff_reports_an_added_and_a_removed_check(baseline: ScoringSpec) -> None:
    document = candidate_document()
    # The gate triggers on lab.beta.one, so it has to go with the check it names.
    document["gates"] = []
    document["categories"][1]["checks"] = [
        {
            "id": "lab.beta.three",
            "title_ko": "새 점검",
            "title_en": "new check",
            "severity": "MINOR",
            "scope": "URL",
            "remediation_owner": "MARKETER",
        }
    ]
    diff = validation.diff_specs(baseline, build_spec(document))

    assert [c.check_id for c in diff.checks_added] == ["lab.beta.three"]
    assert sorted(c.check_id for c in diff.checks_removed) == ["lab.beta.one", "lab.beta.two"]
    joined = "\n".join(diff.lines_ko())
    assert "lab.beta.three" in joined
    assert "lab.beta.one" in joined


def test_the_diff_reports_a_severity_change(baseline: ScoringSpec) -> None:
    document = candidate_document()
    document["categories"][0]["checks"][1]["severity"] = "CRITICAL"
    diff = validation.diff_specs(baseline, build_spec(document))

    changes = {c.check_id: c for c in diff.severity_changes}
    assert changes["lab.alpha.two"].before == "MAJOR"
    assert changes["lab.alpha.two"].after == "CRITICAL"
    assert any("MAJOR" in line and "CRITICAL" in line for line in diff.lines_ko())


def test_the_diff_reports_a_changed_cap_ceiling(baseline: ScoringSpec) -> None:
    document = candidate_document()
    document["caps"][0]["max_overall_score"] = 15
    diff = validation.diff_specs(baseline, build_spec(document))

    assert [c.cap_id for c in diff.cap_changes] == ["alpha_blocked"]
    assert diff.cap_changes[0].before_max == pytest.approx(30.0)
    assert diff.cap_changes[0].after_max == pytest.approx(15.0)
    assert any("alpha_blocked" in line and "15" in line for line in diff.lines_ko())


def test_a_removed_cap_and_gate_are_reported(baseline: ScoringSpec) -> None:
    document = candidate_document()
    document["caps"] = []
    document["gates"] = []
    diff = validation.diff_specs(baseline, build_spec(document))

    assert [c.cap_id for c in diff.caps_removed] == ["alpha_blocked"]
    assert list(diff.gates_removed) == ["beta_gate"]
    joined = "\n".join(diff.lines_ko())
    assert "alpha_blocked" in joined and "beta_gate" in joined


def test_an_identical_specification_reports_no_change(baseline: ScoringSpec) -> None:
    same = build_spec(baseline_document())
    diff = validation.diff_specs(baseline, same)
    assert not diff.has_changes
    assert _has_hangul(diff.summary_ko())


def test_a_first_version_says_so_rather_than_inventing_a_baseline() -> None:
    candidate = build_spec(candidate_document())
    diff = validation.diff_specs(None, candidate)
    assert diff.baseline_version is None
    assert _has_hangul(diff.summary_ko())
    assert diff.lines_ko()


def test_the_diff_survives_a_serialisation_round_trip(baseline: ScoringSpec) -> None:
    diff = validation.diff_specs(baseline, build_spec(candidate_document()))
    record = diff.to_record()
    assert record["baseline_version"] == "1.0.0"
    assert record["candidate_version"] == "1.1.0"
    assert any("alpha" in line for line in record["lines_ko"])
