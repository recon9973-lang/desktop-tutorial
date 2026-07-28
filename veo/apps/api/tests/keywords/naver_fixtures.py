"""Loader for the synthetic Naver fixtures.

Every file under ``tests/fixtures/naver`` must carry a ``_veo_fixture`` marker declaring
itself synthetic. This loader refuses anything without one, which is the mechanical
version of the rule in ADR 0004: a plausible-looking fake response must not be able to
enter the test suite unlabelled, because the next person to read it cannot tell.

The marker is stripped before the payload reaches a normaliser, so production code never
sees a field that only exists in a fixture.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[4]
FIXTURE_DIR = REPO_ROOT / "tests" / "fixtures" / "naver"

MARKER_KEY = "_veo_fixture"


class UnlabelledFixtureError(AssertionError):
    """A fixture file did not declare itself synthetic."""


def fixture_paths() -> tuple[Path, ...]:
    return tuple(sorted(FIXTURE_DIR.glob("*.json")))


def read_marker(path: Path) -> dict[str, Any]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    marker = raw.get(MARKER_KEY)
    if not isinstance(marker, dict):
        raise UnlabelledFixtureError(
            f"{path.name} has no {MARKER_KEY} block; every Naver fixture must declare "
            "itself synthetic"
        )
    for flag in ("synthetic", "not_a_real_observation"):
        if marker.get(flag) is not True:
            raise UnlabelledFixtureError(f"{path.name} must set {MARKER_KEY}.{flag} to true")
    if not marker.get("note_ko"):
        raise UnlabelledFixtureError(f"{path.name} must explain itself in {MARKER_KEY}.note_ko")
    return marker


def load(name: str) -> dict[str, Any]:
    """Return one fixture payload with the synthetic marker verified and removed."""
    path = FIXTURE_DIR / name
    read_marker(path)
    payload: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    payload.pop(MARKER_KEY, None)
    return payload


def load_bytes(name: str) -> bytes:
    """The marker-stripped payload as bytes, for hashing exactly what was normalised."""
    return json.dumps(load(name), ensure_ascii=False, sort_keys=True).encode("utf-8")
