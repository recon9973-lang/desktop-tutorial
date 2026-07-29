"""The rules that hold for the SEO collectors as a set, whatever any one of them checks.

Three failures are being guarded against.

1. A check id in the published specification that nobody implements. The suite fails the
   moment VEO-LAB adds one, so an unimplemented check cannot be scored as a silent pass.
2. Two collectors claiming the same check, which would give one observation two owners.
3. A weight, a severity or a score creeping into checker code. The specification is the
   only place a number may live, and the strongest way to prove it is to change every
   number in the specification and watch the observations stay identical.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest
from tests.seo.support import SPEC, build_context

from veo.collect.contract import CollectionResult, Collector, run_collectors, verify_complete
from veo.scoring import CheckStatus
from veo.seo import seo_collectors
from veo.seo.collectors import CATEGORY_COLLECTORS

SEO_PACKAGE = Path(__file__).resolve().parents[2] / "src" / "veo" / "seo"

FIXTURES = (
    "healthy",
    "sitewide_noindex",
    "cross_domain_canonical",
    "redirect_loop",
    "broken_jsonld",
    "duplicate_metadata",
    "orphan_page",
    "conflicting_hreflang",
    "render_gap",
    "brochure_na",
)


# --------------------------------------------------------------------------- #
# Coverage of the specification
# --------------------------------------------------------------------------- #


def test_the_collectors_between_them_cover_every_check_in_the_specification() -> None:
    covered: set[str] = set()
    for collector in seo_collectors():
        covered |= set(collector.check_ids)

    missing = set(SPEC.check_ids) - covered
    assert not missing, (
        "the published specification declares checks nobody collects: " + ", ".join(sorted(missing))
    )


def test_no_collector_reports_a_check_outside_the_specification() -> None:
    extra: set[str] = set()
    for collector in seo_collectors():
        extra |= set(collector.check_ids) - set(SPEC.check_ids)
    assert not extra, "collectors claim checks the specification does not define: " + ", ".join(
        sorted(extra)
    )


def test_no_check_id_is_claimed_twice() -> None:
    seen: dict[str, str] = {}
    for collector in seo_collectors():
        for check_id in collector.check_ids:
            owner = type(collector).__name__
            assert check_id not in seen, (
                f"{check_id} is claimed by both {seen[check_id]} and {owner}"
            )
            seen[check_id] = owner


def test_there_are_forty_seven_checks_and_all_of_them_are_owned() -> None:
    assert len(SPEC.check_ids) == 47
    owned = {check_id for collector in seo_collectors() for check_id in collector.check_ids}
    assert owned == set(SPEC.check_ids)


def test_each_collector_owns_exactly_one_specification_category() -> None:
    """A collector maps to a category so an issue can be traced back to a section."""
    for category_id, factory in CATEGORY_COLLECTORS.items():
        declared = set(factory().check_ids)
        spec_ids = {
            check.id
            for category in SPEC.categories
            if category.id == category_id
            for check in category.checks
        }
        assert declared == spec_ids, f"{category_id} collector does not match its category"


def test_every_specification_category_has_a_collector() -> None:
    assert {category.id for category in SPEC.categories} == set(CATEGORY_COLLECTORS)


# --------------------------------------------------------------------------- #
# Silence is refused, on every fixture
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("fixture", FIXTURES)
def test_verify_complete_passes_for_every_collector_on_every_fixture(fixture: str) -> None:
    context = build_context(fixture)
    for collector in seo_collectors():
        result = collector.collect(context)
        verify_complete(result, collector.check_ids, collector_name=type(collector).__name__)


@pytest.mark.parametrize("fixture", FIXTURES)
def test_running_all_collectors_yields_exactly_one_outcome_per_check(fixture: str) -> None:
    combined = run_collectors(list(seo_collectors()), build_context(fixture))
    assert len(combined.outcomes) == len(SPEC.check_ids)
    assert combined.outcome_ids() == frozenset(SPEC.check_ids)


def test_every_collector_satisfies_the_collector_protocol() -> None:
    for collector in seo_collectors():
        assert isinstance(collector, Collector)


@pytest.mark.parametrize("fixture", FIXTURES)
def test_a_collector_run_never_raises_on_a_fixture(fixture: str) -> None:
    """A malformed page is a finding, not a crash."""
    context = build_context(fixture)
    for collector in seo_collectors():
        assert isinstance(collector.collect(context), CollectionResult)


# --------------------------------------------------------------------------- #
# Collectors observe; they do not score
# --------------------------------------------------------------------------- #

#: Names that would mean a checker had started deciding points for itself.
FORBIDDEN_NAMES = frozenset(
    {
        "severity",
        "severity_coefficient",
        "penalty",
        "penalty_total",
        "score",
        "overall_score",
        "points",
        "deduct",
        "budget",
        "band",
        "cap",
        "max_overall_score",
    }
)

#: Contract fields that legitimately contain the word "weight".
ALLOWED_WEIGHT_NAMES = frozenset({"affected_weight", "evaluated_weight"})


#: The plumbing that carries a finished score back to a caller. It is allowed to say
#: "score" because that is what it is transporting; nothing in it computes one.
# 채점을 **하지 않고** 이미 정해진 점수를 나르기만 하는 모듈들. 규칙이 막으려는 것은
# 검사기가 스스로 배점·심각도·임계값을 갖는 것이지, 결과를 응답이나 행으로 옮기는 일이
# 아니다. `history.py` 는 채점 결과를 DB 로 옮기며, 심각도조차 발행된 명세에서만 읽는다.
SCORE_PLUMBING = frozenset({"service.py", "router.py", "schemas.py", "history.py"})


def _python_sources(package: Path) -> list[Path]:
    return sorted(p for p in package.rglob("*.py") if "__pycache__" not in p.parts)


def _checker_sources() -> list[Path]:
    """Every module that observes — the whole package bar the response plumbing."""
    return [p for p in _python_sources(SEO_PACKAGE) if p.name not in SCORE_PLUMBING]


def test_no_checker_module_names_a_scoring_concept() -> None:
    offenders: list[str] = []
    for path in _checker_sources():
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            name: str | None = None
            if isinstance(node, ast.Name):
                name = node.id
            elif isinstance(node, ast.Attribute):
                name = node.attr
            elif isinstance(node, ast.arg):
                name = node.arg
            if name is None:
                continue
            lowered = name.lower()
            if lowered in ALLOWED_WEIGHT_NAMES:
                continue
            if lowered in FORBIDDEN_NAMES or (
                "weight" in lowered and lowered not in ALLOWED_WEIGHT_NAMES
            ):
                offenders.append(f"{path.name}:{name}")
    assert not offenders, "scoring vocabulary found in checker code: " + ", ".join(offenders)


def test_no_checker_module_imports_the_evaluator() -> None:
    """Only the service hands outcomes to :func:`veo.scoring.evaluate`."""
    for path in _checker_sources():
        tree = ast.parse(path.read_text(encoding="utf-8"))
        imported = {
            alias.name for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)
            for alias in node.names
        } | {
            alias.name for node in ast.walk(tree) if isinstance(node, ast.Import)
            for alias in node.names
        }
        assert "evaluate" not in imported, f"{path.name} imports the evaluator"
        called = {
            node.func.id
            for node in ast.walk(tree)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
        }
        assert "evaluate" not in called, f"{path.name} calls the evaluator"


def test_no_todo_markers_remain_in_the_package() -> None:
    for path in _python_sources(SEO_PACKAGE):
        source = path.read_text(encoding="utf-8")
        for marker in ("TODO", "FIXME", "XXX", "placeholder"):
            assert marker not in source, f"{path.name} still carries a {marker}"


@pytest.mark.parametrize("fixture", FIXTURES)
def test_rewriting_every_number_in_the_specification_changes_no_observation(
    fixture: str,
) -> None:
    """The proof that no weight lives in a checker.

    The severity coefficients, the category weights and the caps are all replaced with
    different values. If any collector consulted one of them, an outcome would move.
    """
    from veo.scoring import build_spec, load_spec

    original = load_spec("veo.seo.readiness", "1.0.0")
    document = original.model_dump(mode="json", exclude={"checksum"})
    document["severity_coefficients"] = {
        "BLOCKER": 0.11,
        "CRITICAL": 0.22,
        "MAJOR": 0.33,
        "MINOR": 0.44,
        "INFO": 0.55,
    }
    for category in document["categories"]:
        category["weight"] = 7.0
    for cap in document["caps"]:
        cap["max_overall_score"] = 99.0
    mutated = build_spec(document, validate_schema=False)

    before = run_collectors(list(seo_collectors()), build_context(fixture))
    after = run_collectors(list(seo_collectors()), build_context(fixture, spec=mutated))

    def shape(result: CollectionResult) -> dict[str, tuple[CheckStatus, float, float, float]]:
        return {
            o.check_id: (
                o.status,
                o.confidence if o.confidence is not None else -1.0,
                o.affected_weight,
                o.evaluated_weight,
            )
            for o in result.outcomes
        }

    assert shape(before) == shape(after)
