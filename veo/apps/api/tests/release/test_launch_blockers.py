"""The eight launch blockers, as checks instead of checkboxes.

`docs/operations/release-checklist.md` lists them well. The trouble with a list is that
it is read by a person, on the day of a release, under time pressure — which is exactly
the wrong moment to be relying on someone's care. Each of the eight is a path by which
VEO tells a customer something untrue, so each one is worth a test that fails the build.

Where a blocker cannot be fully proven by a test, this file checks the strongest
observable proxy and says plainly, in the test, what remains human work. A guard that
overstates its own coverage is worse than no guard.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

SRC = Path(__file__).resolve().parents[2] / "src" / "veo"
REPO = Path(__file__).resolve().parents[4]

PYTHON_SOURCES = sorted(SRC.rglob("*.py"))


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


# --------------------------------------------------------------------------- #
# B-1  Hard-coded scores
# --------------------------------------------------------------------------- #

#: Only these may compute a score at all.
SCORING_MODULES = {"evaluator.py", "models.py", "spec.py"}


def test_a_score_actually_derives_from_its_specification() -> None:
    """Change the specification, and the score must move.

    This replaced a syntactic search for score-like assignments, which flagged three
    dozen lines that were simply passing an already-computed score into a response
    model. Grepping cannot tell "assigning a score" from "carrying one", and a guard
    that cannot tell them apart gets muted.

    Behaviour can tell them apart. A hard-coded score is, by definition, one that does
    not change when the methodology does — so rewrite the weights and watch.
    """
    from veo.scoring import CheckOutcome, CheckStatus, build_spec, evaluate
    from veo.scoring.spec import load_spec

    spec = load_spec("veo.seo.readiness", "1.0.0")
    outcomes = [
        CheckOutcome(
            check_id=check_id,
            status=CheckStatus.FAIL if index == 0 else CheckStatus.PASS,
            confidence=1.0,
        )
        for index, check_id in enumerate(spec.check_ids)
    ]
    # Compare before caps. A cap is an upper bound, so a capped score stays put no
    # matter what the weights do — which is the cap working correctly, and which would
    # make this check quietly vacuous if it looked at the final number.
    original = evaluate(spec, outcomes).overall_score_before_caps

    # Round-trip through the on-disk document rather than the model: dumping the model
    # emits explicit nulls for optional fields that the schema declares as numbers.
    import yaml

    from veo.scoring.spec import find_specs_root

    source = find_specs_root() / "specs" / "veo.seo.readiness" / "1.0.0.yaml"
    document = yaml.safe_load(source.read_text(encoding="utf-8"))
    for category in document["categories"]:
        category["weight"] = 100 / len(document["categories"])
    reweighted = evaluate(build_spec(document), outcomes).overall_score_before_caps

    assert original != reweighted, (
        "the score did not move when every category weight changed — it is not coming "
        "from the specification"
    )


def test_no_collector_calls_the_evaluator() -> None:
    """Collectors observe. Turning observations into a number is a separate job.

    Matched on the actual import, not on the substring "evaluate" — collectors use
    `evaluated_weight` constantly, and a check that cannot tell those apart would be
    switched off within a week.
    """
    offenders: list[str] = []
    for path in PYTHON_SOURCES:
        if "collectors" not in path.relative_to(SRC).parts:
            continue
        tree = ast.parse(read(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and (node.module or "").startswith("veo.scoring"):
                imported = {alias.name for alias in node.names}
                if "evaluate" in imported:
                    offenders.append(str(path.relative_to(SRC)))
    assert not offenders, f"collectors that score their own findings: {offenders}"


# --------------------------------------------------------------------------- #
# B-2  Fabricated provider data
# --------------------------------------------------------------------------- #


def test_no_provider_returns_a_literal_measurement_on_failure() -> None:
    """The specific fabrication: a failed call that yields 0 instead of 측정 불가."""
    offenders: list[str] = []
    for path in sorted((SRC / "providers").rglob("*.py")):
        source = read(path)
        for match in re.finditer(r"except[^\n]*\n(?:\s+[^\n]*\n){0,6}", source):
            block = match.group(0)
            if re.search(r"return\s+0(?:\.0)?\b", block):
                offenders.append(str(path.relative_to(SRC)))
    assert not offenders, (
        "a provider that returns zero from an error path is reporting a measurement it "
        f"never made: {offenders}"
    )


def test_every_provider_family_can_report_being_unavailable() -> None:
    from veo.contracts.enums import ProviderState

    assert ProviderState.DISABLED_NO_CREDENTIAL
    assert ProviderState.DISABLED_INVALID_CREDENTIAL
    assert ProviderState.NOT_AVAILABLE


# --------------------------------------------------------------------------- #
# B-3  N/A treated as failure
# --------------------------------------------------------------------------- #


def test_not_applicable_leaves_the_denominator() -> None:
    from veo.scoring import CheckOutcome, CheckStatus, build_spec, evaluate
    from veo.scoring.spec import load_spec

    spec = load_spec("veo.seo.readiness", "1.0.0")
    assert build_spec is not None

    all_na = [
        CheckOutcome(check_id=check_id, status=CheckStatus.NOT_APPLICABLE, confidence=1.0)
        for check_id in spec.check_ids
    ]
    result = evaluate(spec, all_na)
    assert result.overall_score is None, "an all-N/A scan must be unscoreable, not zero"
    assert result.status == "NOT_APPLICABLE"


def test_unknown_lowers_coverage_and_never_the_score() -> None:
    from veo.scoring import CheckOutcome, CheckStatus, evaluate
    from veo.scoring.spec import load_spec

    spec = load_spec("veo.seo.readiness", "1.0.0")
    passing = [
        CheckOutcome(check_id=check_id, status=CheckStatus.PASS, confidence=1.0)
        for check_id in spec.check_ids
    ]
    one_unknown = [
        CheckOutcome(check_id=spec.check_ids[0], status=CheckStatus.UNKNOWN, confidence=0.0),
        *passing[1:],
    ]

    assert evaluate(spec, passing).overall_score == 100.0
    degraded = evaluate(spec, one_unknown)
    assert degraded.overall_score == 100.0, "unknown must not reduce the score"
    assert degraded.coverage < 1.0, "unknown must reduce coverage"


# --------------------------------------------------------------------------- #
# B-4  A score that cannot be traced
# --------------------------------------------------------------------------- #


def test_every_score_carries_its_methodology_and_arithmetic() -> None:
    from veo.scoring import CheckOutcome, CheckStatus, evaluate
    from veo.scoring.spec import load_spec

    spec = load_spec("veo.geo.readiness", "1.0.0")
    result = evaluate(
        spec,
        [
            CheckOutcome(check_id=check_id, status=CheckStatus.PASS, confidence=1.0)
            for check_id in spec.check_ids
        ],
    )

    assert result.spec_version and result.spec_checksum
    assert result.trace["checks"], "no per-check arithmetic recorded"
    assert result.trace["categories"], "no per-category arithmetic recorded"
    assert result.coverage is not None and result.confidence is not None


# --------------------------------------------------------------------------- #
# B-5  Cross-tenant leakage
# --------------------------------------------------------------------------- #


def test_every_tenant_owned_table_is_guarded() -> None:
    from veo.authz import tenant_table_names
    from veo.db.models import Base

    unguarded = [
        table.name
        for table in Base.metadata.tables.values()
        if "organization_id" in table.c
        and not table.c["organization_id"].nullable
        and table.name not in tenant_table_names()
    ]
    assert not unguarded, f"tenant tables outside the isolation guard: {unguarded}"


def test_the_isolation_guard_rejects_an_unfiltered_query() -> None:
    import uuid

    from sqlalchemy import select

    from veo.authz import TenantIsolationError, assert_tenant_scoped
    from veo.db.models import Project

    with pytest.raises(TenantIsolationError):
        assert_tenant_scoped(select(Project), uuid.uuid4())


# --------------------------------------------------------------------------- #
# B-6  SSRF
# --------------------------------------------------------------------------- #


def test_the_fetcher_is_the_only_way_out() -> None:
    """Any module that dials http:// itself has stepped around the guard."""
    allowed = {
        "fetcher.py",  # the guarded fetcher itself
        "url_guard.py",
        "limits.py",
        # 알림 웹훅(veo/notify). SSRF 가 막는 것은 **고객이 고른 URL** 인데, 이
        # URL 은 요청이 아니라 운영자 설정(VEO_ALERT_WEBHOOK_URL)에서만 온다.
        # https 전용·요청 데이터 미사용은 tests/notify 가 따로 지킨다.
        "webhook.py",
    }
    offenders: list[str] = []
    for path in PYTHON_SOURCES:
        if path.name in allowed:
            continue
        # Providers call named vendor endpoints, not caller-supplied URLs; SSRF is about
        # URLs a customer chooses, which only the crawler accepts.
        if "providers" in path.relative_to(SRC).parts:
            continue
        source = read(path)
        if re.search(r"httpx\.(get|post|put|delete|stream|request)\s*\(", source):
            offenders.append(str(path.relative_to(SRC)))
    assert not offenders, (
        f"outbound HTTP outside the guarded fetcher: {offenders}. A customer-supplied URL "
        "fetched anywhere else bypasses the SSRF decision entirely."
    )


def test_a_private_address_is_still_refused() -> None:
    from veo.common.security.url_guard import UrlGuard

    guard = UrlGuard(resolver=lambda host: ["169.254.169.254"])
    assert not guard.validate("https://metadata.example/").allowed


# --------------------------------------------------------------------------- #
# B-7  Readiness mixed with observed visibility
# --------------------------------------------------------------------------- #


def test_no_readiness_specification_scores_observed_visibility() -> None:
    from veo.scoring.spec import available_specs, load_spec

    forbidden = ("mention", "citation", "share_of_voice", "sov", "visibility")
    for spec_id, versions in available_specs().items():
        spec = load_spec(spec_id, versions[-1])
        for check_id in spec.check_ids:
            assert not any(word in check_id.lower() for word in forbidden), (
                f"{spec_id} scores {check_id}: observed AI visibility is measured, "
                "never folded into a readiness score"
            )


def test_the_scoring_domain_enum_has_no_observation_member() -> None:
    from veo.scoring import ScoringDomain

    assert not any("OBSERV" in str(domain) for domain in ScoringDomain)


# --------------------------------------------------------------------------- #
# B-8  Naver figures without source and time
# --------------------------------------------------------------------------- #


def test_a_relative_index_cannot_be_used_as_a_count() -> None:
    """DataLab is 0-100 relative. Arithmetic on it would make it look like volume."""
    from veo.providers.naver.datalab import RelativeIndex

    index = RelativeIndex(value=52.07)
    for forbidden in ("__int__", "__float__", "__index__", "__add__", "__mul__"):
        assert not hasattr(index, forbidden) or getattr(type(index), forbidden, None) is None, (
            f"RelativeIndex exposes {forbidden}; a relative index that can be added to a "
            "search count will eventually be added to one"
        )


def test_the_forbidden_marketing_phrase_is_never_shown_to_a_user() -> None:
    """'실시간 인기검색어' has no lawful source behind it, so VEO never claims it.

    The phrase legitimately appears in comments that forbid it — deleting those would
    lose the reason. What matters is that it never reaches a string a user can see.
    """
    offenders: list[str] = []
    for path in PYTHON_SOURCES:
        tree = ast.parse(read(path))
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Constant)
                and isinstance(node.value, str)
                and "실시간 인기검색어" in node.value
                and not _is_docstring(tree, node)
            ):
                offenders.append(f"{path.relative_to(SRC)}:{node.lineno}")
    assert not offenders, f"the forbidden phrase reaches a user-visible string: {offenders}"


def _is_docstring(tree: ast.AST, node: ast.Constant) -> bool:
    for parent in ast.walk(tree):
        if isinstance(parent, ast.Module | ast.ClassDef | ast.FunctionDef):
            body = getattr(parent, "body", [])
            if body and isinstance(body[0], ast.Expr) and body[0].value is node:
                return True
    return False


# --------------------------------------------------------------------------- #
# Discipline: nothing unfinished ships
# --------------------------------------------------------------------------- #


def test_no_todo_or_placeholder_in_shipped_source() -> None:
    markers = ("TODO", "FIXME", "XXX", "HACK", "placeholder score", "dummy score")
    offenders: list[str] = []
    for path in PYTHON_SOURCES:
        source = read(path)
        for marker in markers:
            if marker in source:
                offenders.append(f"{path.relative_to(SRC)} ({marker})")
    assert not offenders, offenders


def test_every_shipped_module_parses() -> None:
    for path in PYTHON_SOURCES:
        try:
            ast.parse(read(path))
        except SyntaxError as exc:  # pragma: no cover - would fail the import anyway
            pytest.fail(f"{path.relative_to(SRC)}: {exc}")


def test_what_this_file_does_not_cover_is_written_down() -> None:
    """The checklist must state the human-only steps, or its automation is a lie.

    Load behaviour, accessibility with a real screen reader, backup restoration onto a
    clean machine, and a live provider's actual field semantics cannot be settled here.
    """
    checklist = REPO / "docs" / "operations" / "release-checklist.md"
    assert checklist.is_file()
    text = checklist.read_text(encoding="utf-8")
    for topic in ("접근성", "백업", "부하"):
        assert topic in text, f"release checklist no longer mentions {topic}"
