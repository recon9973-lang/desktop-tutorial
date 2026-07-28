"""Golden tests: published VEO-LAB specifications against hand-computed expectations.

Each fixture in ``packages/scoring-specs/golden`` states the outcomes and the numbers a
human worked out from the methodology. If the evaluator or a spec changes, these fail —
which is the point. A published specification must never drift silently.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from veo.scoring import (
    CheckOutcome,
    CheckStatus,
    ScoringSpec,
    evaluate,
    find_specs_root,
    load_spec,
)

GOLDEN_DIR = find_specs_root() / "golden"
GOLDEN_FILES = sorted(GOLDEN_DIR.glob("*.json"))

TOLERANCE = 1e-6


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _build_outcomes(spec: ScoringSpec, fixture: dict[str, Any]) -> list[CheckOutcome]:
    overrides = {item["check_id"]: item for item in fixture.get("overrides", [])}

    unknown_ids = set(overrides) - set(spec.check_ids)
    assert not unknown_ids, f"fixture references checks absent from the spec: {sorted(unknown_ids)}"

    default = fixture["default"]
    outcomes = []
    for check_id in spec.check_ids:
        item = overrides.get(check_id, default)
        outcomes.append(
            CheckOutcome(
                check_id=check_id,
                status=CheckStatus(item["status"]),
                confidence=item.get("confidence", default.get("confidence")),
                affected_weight=item.get("affected_weight", 1.0),
                evaluated_weight=item.get("evaluated_weight", 1.0),
                evidence_ids=[f"golden::{fixture['name']}::{check_id}"],
            )
        )
    return outcomes


def test_golden_directory_is_not_empty() -> None:
    assert GOLDEN_FILES, f"no golden fixtures found under {GOLDEN_DIR}"


@pytest.mark.parametrize("path", GOLDEN_FILES, ids=lambda p: p.stem)
def test_golden_fixture(path: Path) -> None:
    fixture = _load(path)
    spec = load_spec(fixture["spec_id"], fixture["spec_version"])
    result = evaluate(spec, _build_outcomes(spec, fixture))
    expected = fixture["expected"]

    assert result.status == expected["status"]

    for field in ("overall_score", "overall_score_before_caps"):
        want = expected[field]
        got = getattr(result, field)
        if want is None:
            assert got is None, f"{field}: expected None, got {got}"
        else:
            assert got == pytest.approx(want, abs=TOLERANCE), f"{field}"

    assert result.band_id == expected["band_id"]
    assert result.coverage == pytest.approx(expected["coverage"], abs=TOLERANCE)
    assert result.confidence == pytest.approx(expected["confidence"], abs=TOLERANCE)
    assert result.effective_weight_total == pytest.approx(
        expected["effective_weight_total"], abs=TOLERANCE
    )

    assert [c.cap_id for c in result.applied_caps] == expected["applied_cap_ids"]
    assert sorted({g.status_code for g in result.gates}) == sorted(
        set(expected["gate_status_codes"])
    )

    for category_id, want_category in expected.get("categories", {}).items():
        got_category = result.category(category_id)
        for field, want in want_category.items():
            got = getattr(got_category, field)
            if want is None:
                assert got is None, f"{category_id}.{field}: expected None, got {got}"
            elif isinstance(want, (int, float)):
                assert got == pytest.approx(want, abs=TOLERANCE), f"{category_id}.{field}"
            else:
                assert got == want, f"{category_id}.{field}"


@pytest.mark.parametrize("path", GOLDEN_FILES, ids=lambda p: p.stem)
def test_golden_fixture_score_is_reproducible_from_its_own_trace(path: Path) -> None:
    """The published trace must be enough to recompute the score by hand."""
    fixture = _load(path)
    spec = load_spec(fixture["spec_id"], fixture["spec_version"])
    result = evaluate(spec, _build_outcomes(spec, fixture))

    for row in result.trace["categories"]:
        if row["status"] != "SCORED":
            continue
        penalties = sum(
            check["penalty"]
            for check in result.trace["checks"]
            if check["category_id"] == row["category_id"]
        )
        assert penalties == pytest.approx(row["penalty_total"], abs=TOLERANCE)
        if row["budget"] > 0:
            recomputed = 100.0 * max(0.0, 1.0 - row["penalty_total"] / row["budget"])
            assert recomputed == pytest.approx(row["score"], abs=TOLERANCE)

    overall = result.trace["overall"]
    if overall["score_before_caps"] is not None:
        weighted = sum(
            row["score"] * row["weight"]
            for row in result.trace["categories"]
            if row["status"] == "SCORED"
        )
        assert weighted / overall["effective_weight_total"] == pytest.approx(
            overall["score_before_caps"], abs=TOLERANCE
        )
