"""Risk findings may only reach a report through the publication gate.

Today there is no exposure path at all: nothing in `veo/reports` reads a claim
assessment. That is the safest possible state and also the most fragile one, because the
protection is an absence rather than a rule. The day someone adds a risk section to the
report — a reasonable, obviously-useful feature — the natural way to write it is to read
the assessments and render them, and unreviewed machine verdicts about a clinic's prices
go straight to that clinic's customer.

So the coupling is enforced structurally. `veo/reports` may reference risk material only
by going through `apply_publication_gate`, and this test fails the build if it ever does
otherwise. It is deliberately a source-level check: there is nothing to run yet, and by
the time there is, the guard has to already exist.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

REPORTS_ROOT = Path(__file__).resolve().parents[2] / "src" / "veo" / "reports"

#: Names that mean "this module is handling risk findings".
RISK_SYMBOLS = frozenset(
    {
        "ClaimAssessment",
        "ReviewedAssessment",
        "AutomatedJudgement",
        "RiskKind",
        "RiskBand",
    }
)

#: The only sanctioned door.
GATE_SYMBOL = "apply_publication_gate"


def _report_modules() -> list[Path]:
    return sorted(REPORTS_ROOT.rglob("*.py"))


def _imported_names(tree: ast.AST) -> set[str]:
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            for alias in node.names:
                names.add(alias.name)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                names.add(alias.name.split(".")[-1])
    return names


def test_the_reports_package_exists() -> None:
    assert REPORTS_ROOT.is_dir(), "reports package moved; this guard needs its new path"


@pytest.mark.parametrize("module", _report_modules(), ids=lambda p: p.name)
def test_a_report_module_touching_risk_must_use_the_gate(module: Path) -> None:
    tree = ast.parse(module.read_text(encoding="utf-8"))
    imported = _imported_names(tree)

    touches_risk = bool(imported & RISK_SYMBOLS)
    if not touches_risk:
        return

    assert GATE_SYMBOL in imported, (
        f"{module.name} imports risk material {sorted(imported & RISK_SYMBOLS)} without "
        f"importing {GATE_SYMBOL}. Every risk finding that reaches a customer-facing "
        "report must pass the publication gate — an unreviewed machine verdict about a "
        "clinic is a defamation risk, not a data-quality one."
    )


def test_the_gate_is_importable_and_named_as_the_guard_expects() -> None:
    """If the gate is renamed, this fails before the guard silently stops guarding."""
    from veo.observations.review import gating

    assert hasattr(gating, GATE_SYMBOL), (
        f"{GATE_SYMBOL} is gone from veo.observations.review.gating; "
        "update this guard together with it, or it will pass by never matching."
    )


def test_the_guard_would_actually_catch_a_violation(tmp_path: Path) -> None:
    """Prove the check bites, rather than trusting that it would.

    A guard nobody has seen fail is a guard nobody knows works.
    """
    offender = tmp_path / "risk_section.py"
    offender.write_text(
        "from veo.observations.risk.assessment import ClaimAssessment\n"
        "def render(items: list[ClaimAssessment]) -> str:\n"
        "    return str(items)\n",
        encoding="utf-8",
    )

    imported = _imported_names(ast.parse(offender.read_text(encoding="utf-8")))
    assert imported & RISK_SYMBOLS, "the sample should look like a risk-handling module"
    assert GATE_SYMBOL not in imported, "the sample should be a violation"
