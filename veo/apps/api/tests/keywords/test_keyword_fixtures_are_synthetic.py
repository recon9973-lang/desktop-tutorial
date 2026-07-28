"""Fixture discipline.

VEO has no Naver credential, so every Naver fixture in this repository is invented. The
danger is not that they exist — tests need them — but that six months from now someone
reads ``monthlyPcQcCnt: 1111`` and treats it as an observation. These tests keep the
labelling mechanical rather than optional.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from tests.keywords.naver_fixtures import (
    FIXTURE_DIR,
    MARKER_KEY,
    UnlabelledFixtureError,
    fixture_paths,
    load,
    read_marker,
)

SOURCE_ROOT = Path(__file__).resolve().parents[2] / "src" / "veo"


def test_there_are_fixtures_to_check() -> None:
    assert fixture_paths()


@pytest.mark.parametrize("path", fixture_paths(), ids=lambda path: path.name)
def test_every_fixture_declares_itself_synthetic(path: Path) -> None:
    marker = read_marker(path)
    assert marker["synthetic"] is True
    assert marker["not_a_real_observation"] is True
    assert marker["note_ko"]


@pytest.mark.parametrize("path", fixture_paths(), ids=lambda path: path.name)
def test_every_fixture_keyword_is_obviously_invented(path: Path) -> None:
    """Keywords carry a ``합성`` prefix so no reader mistakes one for a real query."""
    text = path.read_text(encoding="utf-8")
    payload = json.loads(text)
    for row in payload.get("keywordList", []):
        keyword = row.get("relKeyword")
        if keyword is not None:
            assert keyword.startswith("합성"), keyword
    for group in payload.get("results", []):
        for keyword in group.get("keywords", []):
            assert keyword.startswith("합성"), keyword


def test_the_loader_refuses_an_unlabelled_fixture(tmp_path: Path) -> None:
    unlabelled = tmp_path / "sneaky.json"
    unlabelled.write_text(json.dumps({"keywordList": []}), encoding="utf-8")
    with pytest.raises(UnlabelledFixtureError):
        read_marker(unlabelled)


def test_the_loader_refuses_a_fixture_that_only_half_declares_itself(tmp_path: Path) -> None:
    half = tmp_path / "half.json"
    half.write_text(
        json.dumps({MARKER_KEY: {"synthetic": True}, "keywordList": []}), encoding="utf-8"
    )
    with pytest.raises(UnlabelledFixtureError):
        read_marker(half)


def test_the_marker_never_reaches_a_normaliser() -> None:
    payload = load("searchad_keywordstool_synthetic.json")
    assert MARKER_KEY not in payload


def test_production_code_never_reads_the_fixture_directory() -> None:
    """A fixture that a shipped code path can load is no longer a fixture."""
    offenders = [
        path
        for path in SOURCE_ROOT.rglob("*.py")
        if "fixtures/naver" in path.read_text(encoding="utf-8")
        or "fixtures\\naver" in path.read_text(encoding="utf-8")
    ]
    assert offenders == []


def test_no_production_module_hard_codes_a_search_volume() -> None:
    """No plausible-looking default anywhere in the keyword or provider code.

    Catching this by grep is crude, but the failure it prevents — a "reasonable default"
    monthly volume shipped as a fallback — is the single worst outcome this product can
    produce, and crude beats absent.
    """
    suspicious = ("monthly_pc_searches = 1", "or 0  # searches", "DEFAULT_MONTHLY_SEARCHES")
    for path in (SOURCE_ROOT / "keywords").rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        for token in suspicious:
            assert token not in text, f"{path.name}: {token}"
    for path in (SOURCE_ROOT / "providers").rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        for token in suspicious:
            assert token not in text, f"{path.name}: {token}"


def test_the_fixture_directory_explains_itself() -> None:
    readme = FIXTURE_DIR / "README.md"
    assert readme.exists()
    text = readme.read_text(encoding="utf-8")
    assert "합성" in text
    assert "실제" in text
