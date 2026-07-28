"""Builders shared by the competitor-comparison tests.

Measurements are constructed by hand rather than produced by running a scan. That is
deliberate: these tests are about *comparability and arithmetic*, and a scan result would
drag the whole collector stack in and make the expected numbers a function of fixture HTML
rather than of something a person can check on paper.

Everything defaults to one fixed, internally consistent set of conditions, so a test that
wants to prove "this one difference blocks" changes exactly one field and nothing else.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from veo.compare import MeasurementConditions
from veo.competitors.comparison import CategoryMeasurement, Measurement
from veo.scoring import CheckStatus

FIXTURE_ROOT = Path(__file__).resolve().parents[4] / "tests" / "fixtures" / "competitors"

BASE_MEASURED_AT = datetime(2026, 7, 1, 9, 0, tzinfo=UTC)

CATEGORY_NAMES_KO = {
    "crawl_indexability": "크롤링·색인 가능성",
    "onpage_semantics": "온페이지 시맨틱",
    "structured_data": "구조화 데이터",
}


def load_fixture(name: str) -> dict[str, Any]:
    document: dict[str, Any] = json.loads(
        (FIXTURE_ROOT / name).read_text(encoding="utf-8")
    )
    return document


def conditions(**overrides: Any) -> MeasurementConditions:
    """The reference setup. Override one field to build a specific difference."""
    values: dict[str, Any] = {
        "spec_id": "veo.seo.readiness",
        "spec_version": "1.0.0",
        "spec_checksum": "a" * 64,
        "collector_version": "veo-collector/1.4.0",
        "pages_examined": 30,
        "locale": "ko-KR",
        "device": "MOBILE",
        "renderer": "HEADLESS_CHROME",
        "enabled_providers": ("google_psi",),
        "measured_at": BASE_MEASURED_AT,
    }
    values.update(overrides)
    return MeasurementConditions(**values)


def category(
    category_id: str,
    score: float | None,
    *,
    weight: float = 25.0,
    coverage: float = 1.0,
    scored: tuple[str, ...] = (),
) -> CategoryMeasurement:
    return CategoryMeasurement(
        category_id=category_id,
        name_ko=CATEGORY_NAMES_KO.get(category_id, category_id),
        weight=weight,
        score=score,
        coverage=coverage,
        scored_check_ids=scored,
    )


def measurement(
    key: str,
    label_ko: str,
    *,
    overall: float | None = 70.0,
    coverage: float = 0.9,
    confidence: float = 0.9,
    categories: tuple[CategoryMeasurement, ...] = (),
    checks: dict[str, CheckStatus] | None = None,
    measurement_conditions: MeasurementConditions | None = None,
) -> Measurement:
    return Measurement(
        key=key,
        label_ko=label_ko,
        conditions=measurement_conditions or conditions(),
        overall_score=overall,
        coverage=coverage,
        confidence=confidence,
        categories=categories,
        check_statuses=dict(checks or {}),
    )


def categories_from(block: dict[str, Any], weights: dict[str, float]) -> tuple[
    CategoryMeasurement, ...
]:
    """Turn a fixture's ``categories`` block into engine input, order preserved."""
    return tuple(
        category(
            category_id,
            values["score"],
            weight=weights[category_id],
            coverage=values["coverage"],
            scored=tuple(values.get("scored", ())),
        )
        for category_id, values in block.items()
    )
