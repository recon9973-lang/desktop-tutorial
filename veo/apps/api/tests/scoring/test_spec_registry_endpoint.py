"""The registry the console reads is the registry that scores.

The console used to carry its own copy of "which specifications are published" — two
entries, both pinned at 1.0.0, written by hand. By the time anyone looked, SEO was at
1.6.0 and GEO at 1.2.0, and the screen had been quietly reporting the wrong version for
eight releases. Nothing failed, because nothing compared the two lists.

These tests are that comparison. They assert against the loader the scoring path itself
uses, never against a literal version number — pinning a version here would just move the
hand-written list into the test suite, where it would be mechanically bumped whenever it
went red.
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from veo.api.app import create_app
from veo.scoring import SEVERITY_VOCABULARY, Severity, available_specs, latest_published


@pytest.fixture
def client() -> Iterator[TestClient]:
    with TestClient(create_app()) as test_client:
        yield test_client


def _specs(client: TestClient) -> list[dict]:
    response = client.get("/api/scoring/specs")
    assert response.status_code == 200
    return response.json()["data"]["specs"]


def test_every_version_on_disk_is_listed(client: TestClient) -> None:
    """No version disappears from the list, so history stays readable."""
    listed = {(spec["spec_id"], spec["version"]) for spec in _specs(client)}
    on_disk = {
        (spec_id, version)
        for spec_id, versions in available_specs().items()
        for version in versions
    }
    assert listed == on_disk


def test_current_version_is_the_one_the_engine_would_score_with(client: TestClient) -> None:
    """The exact drift that went unnoticed: the screen naming a version that is no longer used."""
    current = {
        spec["spec_id"]: spec["version"] for spec in _specs(client) if spec["is_current"]
    }
    expected = {
        spec_id: latest_published(spec_id).version for spec_id in available_specs()
    }
    assert current == expected


def test_at_most_one_current_version_per_spec_id(client: TestClient) -> None:
    seen: dict[str, int] = {}
    for spec in _specs(client):
        if spec["is_current"]:
            seen[spec["spec_id"]] = seen.get(spec["spec_id"], 0) + 1
    assert all(count == 1 for count in seen.values()), seen


def test_superseded_versions_are_marked_not_current(client: TestClient) -> None:
    """A published-but-superseded version must not read as the one in force."""
    for spec in _specs(client):
        if spec["is_current"]:
            continue
        assert spec["version"] != latest_published(spec["spec_id"]).version


def test_checksum_travels_with_every_summary(client: TestClient) -> None:
    for spec in _specs(client):
        assert spec["checksum"] != ""


def test_spec_detail_agrees_with_the_list_about_what_is_current(client: TestClient) -> None:
    for spec in _specs(client):
        response = client.get(f"/api/scoring/specs/{spec['spec_id']}/{spec['version']}")
        assert response.status_code == 200
        assert response.json()["data"]["is_current"] == spec["is_current"]


# --------------------------------------------------------------------------- #
# Severity vocabulary
# --------------------------------------------------------------------------- #


def _severities(client: TestClient) -> list[dict]:
    response = client.get("/api/scoring/severities")
    assert response.status_code == 200
    return response.json()["data"]["severities"]


def test_vocabulary_covers_every_severity_the_engine_can_emit(client: TestClient) -> None:
    """Adding a severity without giving it a name must fail here, not silently on screen."""
    served = [term["id"] for term in _severities(client)]
    assert served == [str(term.severity) for term in SEVERITY_VOCABULARY]
    assert set(served) == {str(member) for member in Severity}


def test_every_severity_is_named_and_explained(client: TestClient) -> None:
    for term in _severities(client):
        assert term["label_ko"] != ""
        assert term["meaning_ko"] != ""


def test_no_coefficient_leaves_the_engine_with_the_vocabulary(client: TestClient) -> None:
    """Severity coefficients are numbers, and numbers belong to the versioned spec.

    A screen holding them could produce a score of its own, and two scores that disagree
    is worse than one score nobody can explain.
    """
    for term in _severities(client):
        assert set(term) == {"id", "label_ko", "meaning_ko"}


def test_severity_vocabulary_is_public_like_the_rest_of_the_transparency_surface(
    client: TestClient,
) -> None:
    assert client.get("/api/scoring/severities").status_code == 200
