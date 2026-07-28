"""Running the golden fixtures against a candidate specification.

The fixtures in ``packages/scoring-specs/golden`` state numbers a human worked out from
the methodology. A candidate that produces different numbers has changed the methodology,
and the difference has to be acknowledged by updating the fixtures — not waved through.
"""

from __future__ import annotations

import pytest
from tests.lab.support import (
    BASELINE_VERSION,
    CANDIDATE_VERSION,
    LAB_SPEC_ID,
    baseline_document,
    candidate_document,
)

from veo.lab import golden
from veo.lab.errors import GoldenFixtureError
from veo.scoring import build_spec, load_spec


def _has_hangul(text: str) -> bool:
    return any("가" <= character <= "힣" for character in text)


def test_the_candidate_passes_the_fixtures_written_for_it() -> None:
    run = golden.run_golden_fixtures(build_spec(candidate_document()))
    assert run.total == 2
    assert run.passed_count == 2
    assert run.failed_count == 0
    assert run.all_passed
    assert run.spec_version == CANDIDATE_VERSION
    assert _has_hangul(run.summary_ko())


def test_the_previous_version_fails_the_fixtures_written_for_the_new_one() -> None:
    run = golden.run_golden_fixtures(build_spec(baseline_document()))
    assert run.spec_version == BASELINE_VERSION
    assert not run.all_passed
    assert run.failed_count == 1

    failed = [fixture for fixture in run.fixtures if not fixture.passed]
    assert [f.name for f in failed] == ["labtest-02-alpha-major-fail"]
    reasons = "\n".join(failed[0].failures_ko)
    assert _has_hangul(reasons)
    # The reviewer must be able to see both numbers without opening a debugger.
    assert "83.846154" in reasons and "86.153846" in reasons, reasons


def test_the_real_published_seo_specification_passes_its_own_fixtures() -> None:
    """Cross-check: this runner must agree with ``tests/scoring/test_golden.py``."""
    run = golden.run_golden_fixtures(load_spec("veo.seo.readiness", "1.0.0"))
    assert run.total >= 4
    assert run.all_passed, run.summary_ko()


def test_the_real_published_geo_specification_passes_its_own_fixtures() -> None:
    run = golden.run_golden_fixtures(load_spec("veo.geo.readiness", "1.0.0"))
    assert run.total >= 3
    assert run.all_passed, run.summary_ko()


def test_a_specification_family_with_no_fixtures_does_not_count_as_validated() -> None:
    document = candidate_document()
    document["spec_id"] = "veo.lab_test.unfixtured"
    run = golden.run_golden_fixtures(build_spec(document))
    assert run.total == 0
    assert not run.all_passed
    assert _has_hangul(run.summary_ko())


def test_a_fixture_referencing_a_removed_check_fails_loudly() -> None:
    document = candidate_document()
    document["categories"][0]["checks"] = document["categories"][0]["checks"][:1]
    run = golden.run_golden_fixtures(build_spec(document))

    assert not run.all_passed
    failed = [fixture for fixture in run.fixtures if not fixture.passed]
    joined = "\n".join(line for fixture in failed for line in fixture.failures_ko)
    assert "lab.alpha.two" in joined, joined


# --------------------------------------------------------------------------- #
# The publish gate reads a recorded run, not a live one
# --------------------------------------------------------------------------- #


def test_a_recorded_run_round_trips() -> None:
    spec = build_spec(candidate_document())
    record = golden.run_golden_fixtures(spec).to_record()

    assert record["spec_id"] == LAB_SPEC_ID
    assert record["spec_checksum"] == spec.checksum
    assert record["all_passed"] is True
    assert record["total"] == 2
    assert _has_hangul(record["summary_ko"])
    golden.assert_golden_ready(record, spec_checksum=spec.checksum)


def test_publishing_without_any_recorded_run_is_refused() -> None:
    spec = build_spec(candidate_document())
    for absent in (None, {}):
        with pytest.raises(GoldenFixtureError) as caught:
            golden.assert_golden_ready(absent, spec_checksum=spec.checksum)
        assert _has_hangul(caught.value.message_ko)


def test_publishing_with_a_failing_recorded_run_is_refused() -> None:
    spec = build_spec(baseline_document())
    record = golden.run_golden_fixtures(spec).to_record()
    assert record["all_passed"] is False

    with pytest.raises(GoldenFixtureError) as caught:
        golden.assert_golden_ready(record, spec_checksum=spec.checksum)
    assert _has_hangul(caught.value.message_ko)
    assert "labtest-02-alpha-major-fail" in caught.value.message_ko


def test_a_run_recorded_against_a_different_checksum_does_not_count() -> None:
    """Validate, then edit, then publish must not slip through."""
    record = golden.run_golden_fixtures(build_spec(candidate_document())).to_record()

    edited = candidate_document()
    edited["categories"][0]["weight"] = 75.0
    edited["categories"][1]["weight"] = 25.0
    edited_spec = build_spec(edited)
    assert edited_spec.checksum != record["spec_checksum"]

    with pytest.raises(GoldenFixtureError) as caught:
        golden.assert_golden_ready(record, spec_checksum=edited_spec.checksum)
    assert _has_hangul(caught.value.message_ko)
