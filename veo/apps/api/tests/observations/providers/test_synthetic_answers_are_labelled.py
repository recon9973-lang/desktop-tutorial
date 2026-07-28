"""Fixture discipline for invented AI answers.

An invented search volume is a number nobody can check. An invented *AI answer* is worse:
it is a paragraph of fluent Korean that reads exactly like a real observation and can be
pasted into a report. These tests keep the labelling mechanical rather than optional, and
keep the invented material out of anything a shipped code path can reach.
"""

from __future__ import annotations

from pathlib import Path

from tests.observations.providers import synthetic

SUITE_DIR = Path(__file__).resolve().parent
# .../apps/api/tests/observations/providers/ -> parents[3] is apps/api.
OBSERVATIONS_ROOT = Path(__file__).resolve().parents[3] / "src" / "veo" / "observations"

#: Only the modules this suite owns. Scanning the whole ``observations`` package would
#: make another engine's in-flight work fail these tests, which teaches everyone to
#: ignore them.
SOURCE_FILES = (
    *sorted((OBSERVATIONS_ROOT / "providers").rglob("*.py")),
    OBSERVATIONS_ROOT / "runner.py",
)


def test_the_files_this_suite_scans_actually_exist() -> None:
    """A wrong root would make every scan below pass by finding nothing."""
    assert len(SOURCE_FILES) >= 7, SOURCE_FILES
    assert all(path.is_file() for path in SOURCE_FILES)
    assert any(path.name == "gemini.py" for path in SOURCE_FILES)
    assert any(path.name == "runner.py" for path in SOURCE_FILES)


def test_every_invented_answer_body_carries_the_marker() -> None:
    for builder in (synthetic.mentioning_answer, synthetic.silent_answer):
        assert builder().startswith(synthetic.SYNTHETIC_MARKER)


def test_the_marker_says_it_is_not_a_real_answer() -> None:
    assert "합성" in synthetic.SYNTHETIC_MARKER
    assert "실제" in synthetic.SYNTHETIC_MARKER


def test_the_brand_and_its_domain_are_obviously_invented() -> None:
    assert synthetic.BRAND_NAME.startswith("합성")
    assert synthetic.BRAND_DOMAIN.endswith(".example")
    assert synthetic.RIVAL_DOMAIN.endswith(".example")


def test_no_answer_text_in_the_suite_escapes_the_marker() -> None:
    """Any long Korean string literal in a test must come from the synthetic builders."""
    for path in SUITE_DIR.glob("test_*.py"):
        text = path.read_text(encoding="utf-8")
        for line in text.splitlines():
            if "합성 답변" in line or "답변입니다" in line:
                assert "synthetic" in text or synthetic.SYNTHETIC_MARKER in line, path.name


def test_production_code_never_imports_the_synthetic_helpers() -> None:
    offenders = [
        path.name
        for path in SOURCE_FILES
        if "tests.observations.providers.synthetic" in path.read_text(encoding="utf-8")
    ]
    assert offenders == []


def test_no_production_module_ships_a_default_answer_or_price() -> None:
    """A "reasonable default" answer or price is the worst thing this module could ship."""
    suspicious = (
        "DEFAULT_ANSWER",
        "SAMPLE_ANSWER",
        "FALLBACK_ANSWER",
        "brand_mentioned = True",
        "cost_usd = 0.0",
    )
    for path in SOURCE_FILES:
        content = path.read_text(encoding="utf-8")
        for token in suspicious:
            assert token not in content, f"{path.name}: {token}"


def test_no_production_module_contains_a_todo() -> None:
    for path in SOURCE_FILES:
        content = path.read_text(encoding="utf-8")
        assert "TODO" not in content, path.name
        assert "FIXME" not in content, path.name
