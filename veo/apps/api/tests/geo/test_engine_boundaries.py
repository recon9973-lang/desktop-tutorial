"""The two rules that define this engine, asserted against the source itself.

1. Readiness and observed AI visibility never mix. This package may explain the boundary
   in prose — it must not name an observation metric in code.
2. A collector observes; it does not score. No weight, no severity, no arithmetic that
   turns an observation into points.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest
from tests.geo.support import load_case

import veo.geo
from veo.geo.service import run_geo_readiness

PACKAGE_ROOT = Path(veo.geo.__file__).resolve().parent
SOURCE_FILES = sorted(PACKAGE_ROOT.rglob("*.py"))

#: Metrics that belong to the observation engine and to no part of this one.
OBSERVATION_TOKENS = (
    "mention",
    "citation",
    "share_of_voice",
    "shareofvoice",
    "sov",
    "visibility",
    "impression",
    "prompt_sample",
)

#: Vocabulary that would mean this package had started deciding points for itself.
SCORING_TOKENS = (
    "severity",
    "penalty",
    "coefficient",
    "deduct",
    "max_overall_score",
    "score_multiplier",
)

SEVERITY_NAMES = ("BLOCKER", "CRITICAL", "MAJOR", "MINOR")

NUMERIC_CONFIDENCE = re.compile(r"confidence\s*=\s*[-+]?[0-9]")


def _identifiers(path: Path) -> set[str]:
    """Every name this module defines, reads, sets or uses as a dictionary key."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    found: set[str] = set()
    for node in ast.walk(tree):
        match node:
            case ast.Name(id=name):
                found.add(name)
            case ast.Attribute(attr=name):
                found.add(name)
            case ast.arg(arg=name):
                found.add(name)
            case ast.FunctionDef(name=name) | ast.ClassDef(name=name):
                found.add(name)
            case ast.keyword(arg=name) if name:
                found.add(name)
            case ast.alias(name=name, asname=asname):
                found.add(asname or name.rsplit(".", 1)[-1])
            case ast.Dict(keys=keys):
                found.update(
                    key.value
                    for key in keys
                    if isinstance(key, ast.Constant) and isinstance(key.value, str)
                )
            case ast.Constant(value=value) if isinstance(value, str) and value.isidentifier():
                found.add(value)
    return found


def test_the_package_has_source_to_inspect() -> None:
    assert SOURCE_FILES, f"no modules found under {PACKAGE_ROOT}"


@pytest.mark.parametrize("path", SOURCE_FILES, ids=lambda p: p.name)
def test_no_module_names_an_observation_metric(path: Path) -> None:
    offenders = {
        name
        for name in _identifiers(path)
        for token in OBSERVATION_TOKENS
        if token in name.lower()
    }
    assert not offenders, (
        f"{path.name} names {sorted(offenders)}; observed AI visibility is a separate "
        "engine, a separate score and a separate screen (ADR 0003)"
    )


@pytest.mark.parametrize("path", SOURCE_FILES, ids=lambda p: p.name)
def test_no_module_carries_scoring_vocabulary(path: Path) -> None:
    offenders = {
        name for name in _identifiers(path) for token in SCORING_TOKENS if token in name.lower()
    }
    assert not offenders, (
        f"{path.name} names {sorted(offenders)}; weights and severities live in "
        "packages/scoring-specs, never in a collector"
    )


@pytest.mark.parametrize("path", SOURCE_FILES, ids=lambda p: p.name)
def test_no_module_hard_codes_a_severity(path: Path) -> None:
    source = path.read_text(encoding="utf-8")
    for name in SEVERITY_NAMES:
        assert not re.search(rf"\b{name}\b", source), (
            f"{path.name} mentions severity {name}; the specification assigns severity"
        )
    assert "Severity" not in source, f"{path.name} imports or names Severity"


@pytest.mark.parametrize("path", SOURCE_FILES, ids=lambda p: p.name)
def test_no_module_assigns_a_number_to_a_scoring_name(path: Path) -> None:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    banned = ("severity", "penalty", "coefficient", "budget", "points", "score")
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign) or not isinstance(node.value, ast.Constant):
            continue
        if not isinstance(node.value.value, (int, float)) or isinstance(node.value.value, bool):
            continue
        for target in node.targets:
            if isinstance(target, ast.Name):
                lowered = target.id.lower()
                assert not any(token in lowered for token in banned), (
                    f"{path.name} assigns {node.value.value} to {target.id}"
                )


@pytest.mark.parametrize("path", SOURCE_FILES, ids=lambda p: p.name)
def test_confidence_is_named_not_numbered(path: Path) -> None:
    """A collector picks a confidence *level*; the spec decides what that is worth."""
    source = path.read_text(encoding="utf-8")
    assert not NUMERIC_CONFIDENCE.search(source), (
        f"{path.name} passes a numeric confidence; use the specification's "
        "confidence_level vocabulary instead"
    )


def test_a_completed_report_exposes_no_observation_field() -> None:
    report = run_geo_readiness(load_case("hospital_local").context)
    payload = report.score.model_dump(mode="json")

    def walk_keys(node: object) -> list[str]:
        if isinstance(node, dict):
            keys: list[str] = []
            for key, value in node.items():
                keys.append(str(key))
                keys.extend(walk_keys(value))
            return keys
        if isinstance(node, list):
            return [k for item in node for k in walk_keys(item)]
        return []

    for key in walk_keys(payload):
        assert not any(token in key.lower() for token in OBSERVATION_TOKENS), key
