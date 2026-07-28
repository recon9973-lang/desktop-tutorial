"""Load a brand-detection fixture from ``tests/fixtures/observations``.

Nothing here touches the network and nothing here calls a model. A case is a JSON file
holding one synthetic Korean answer plus the brand and competitor declarations the
detector would have been given in production.
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from veo.observations.detection import BrandProfile

FIXTURE_ROOT = Path(__file__).resolve().parents[5] / "tests" / "fixtures" / "observations"


@dataclass(frozen=True, slots=True)
class DetectionCase:
    name: str
    purpose_ko: str
    answer_text: str
    citations: tuple[str, ...]
    brand: BrandProfile
    competitors: tuple[BrandProfile, ...]
    expected: dict[str, Any]


def case_names() -> tuple[str, ...]:
    return tuple(sorted(path.stem for path in FIXTURE_ROOT.glob("*.json")))


def _profile(payload: dict[str, Any], *, is_own_brand: bool) -> BrandProfile:
    return BrandProfile(
        entity_key=payload["entity_key"],
        display_name=payload["display_name"],
        aliases=tuple(payload.get("aliases", ())),
        own_domains=tuple(payload.get("own_domains", ())),
        address_terms=tuple(payload.get("address_terms", ())),
        phone_numbers=tuple(payload.get("phone_numbers", ())),
        distinguishing_terms=tuple(payload.get("distinguishing_terms", ())),
        is_own_brand=is_own_brand,
        competitor_id=payload.get("competitor_id"),
    )


def load_case(name: str) -> DetectionCase:
    payload = json.loads((FIXTURE_ROOT / f"{name}.json").read_text(encoding="utf-8"))
    return DetectionCase(
        name=payload["name"],
        purpose_ko=payload["purpose_ko"],
        answer_text=payload["answer_text"],
        citations=tuple(payload.get("citations", ())),
        brand=_profile(payload["brand"], is_own_brand=True),
        competitors=tuple(
            _profile(item, is_own_brand=False) for item in payload.get("competitors", ())
        ),
        expected=payload["expected"],
    )


def iter_cases() -> Iterator[DetectionCase]:
    for name in case_names():
        yield load_case(name)
