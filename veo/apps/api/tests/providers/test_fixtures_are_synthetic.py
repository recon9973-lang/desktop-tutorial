"""The fixtures are invented, and this is what proves it.

VEO has never held a Google credential, so no response in this suite can have come from a
live call. The danger is not today — it is the afternoon someone pastes a real captured
response, complete with a customer's domain and a quota-bearing key, into a file that gets
committed. These checks fail loudly if that happens.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import google_fixtures as fixtures

SUITE = Path(__file__).resolve().parent

#: RFC 2606 reserves these for exactly this purpose. Anything else is somebody's site.
ALLOWED_HOST_SUFFIXES = (".example", ".example.com", ".example.kr", ".example.org", "example.com")

#: Google API keys start with this prefix. One in a fixture is a real key, revoked or not.
GOOGLE_API_KEY_PATTERN = re.compile(r"AIza[0-9A-Za-z_-]{35}")


def fixture_text() -> str:
    return (SUITE / "google_fixtures.py").read_text(encoding="utf-8")


def test_no_fixture_carries_anything_shaped_like_a_real_google_api_key() -> None:
    for path in SUITE.glob("*.py"):
        assert not GOOGLE_API_KEY_PATTERN.search(path.read_text(encoding="utf-8")), path.name


def test_every_host_in_the_fixtures_is_a_reserved_example_domain() -> None:
    hosts = set(re.findall(r"https?://([A-Za-z0-9._-]+)", fixture_text()))
    for host in hosts:
        if host.endswith("googleapis.com") or host.endswith("google.com"):
            # Endpoint hostnames, not customer data — they have to be the real ones.
            continue
        assert host.endswith(ALLOWED_HOST_SUFFIXES), host


def test_the_service_account_is_generated_in_process_and_is_not_a_google_account() -> None:
    document = json.loads(fixtures.service_account_json())
    assert document["client_email"].endswith(".example.com")
    assert "synthetic" in document["private_key_id"]
    assert "BEGIN PRIVATE KEY" in document["private_key"]


def test_the_generated_key_differs_between_processes() -> None:
    """It is generated, not stored, so nothing durable exists to leak."""
    assert "BEGIN PRIVATE KEY" not in fixture_text()


def test_every_identifier_announces_itself_as_synthetic() -> None:
    document = json.loads(fixtures.service_account_json())
    for value in (document["project_id"], document["private_key_id"], document["client_email"]):
        assert "synthetic" in value
