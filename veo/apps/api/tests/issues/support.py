"""Shared constants and small helpers for the issue-tracking tests.

Kept out of ``conftest.py`` so a test module can import them by name: pytest loads
``conftest`` under its own module name, and importing from it directly would hand the
test a second copy of every class defined there.
"""

from __future__ import annotations

import os
import uuid
from dataclasses import dataclass
from typing import Any

import pytest

from veo.authz.principal import Principal
from veo.core.settings import get_settings

DATABASE_URL = os.environ.get("VEO_TEST_DATABASE_URL")

#: Applied by the modules that need rows rather than pure functions. It lives here, not in
#: ``conftest.py``, because importlib collection would hand an importing test module a
#: second copy of everything ``conftest`` defines.
requires_database = pytest.mark.skipif(
    DATABASE_URL is None,
    reason="set VEO_TEST_DATABASE_URL to run the issue tests against PostgreSQL",
)

API_PREFIX = get_settings().api_prefix
ISSUES = f"{API_PREFIX}/issues"

SEO_SPEC_ID = "veo.seo.readiness"

#: Three real check ids from the published SEO specification, chosen for their differing
#: severities so the severity filter is exercised against the spec rather than a literal.
BLOCKER_CHECK = "seo.robots.meta_indexable"
CRITICAL_CHECK = "seo.canonical.declared_and_consistent"
MAJOR_CHECK = "seo.http.redirect_chain_sane"


@dataclass(frozen=True)
class Tenant:
    """One organization with a writer, a read-only caller and a project to hang issues off."""

    organization_id: uuid.UUID
    project_id: uuid.UUID
    site_id: uuid.UUID
    analyst: Principal
    viewer: Principal


@dataclass
class PrincipalBox:
    """The caller of the next request. Swapped by the ``act_as`` fixture."""

    current: Principal | None = None


def payload(response: Any) -> dict[str, Any]:
    """The ``data`` object of a successful envelope, with the envelope checked."""
    body = response.json()
    assert body["error"] is None, body["error"]
    assert body["meta"]["request_id"]
    data: dict[str, Any] = body["data"]
    return data


def items(response: Any) -> list[dict[str, Any]]:
    """The ``data`` list of a paged envelope."""
    body = response.json()
    assert body["error"] is None, body["error"]
    rows: list[dict[str, Any]] = body["data"]
    return rows


def error_code(response: Any) -> str:
    body = response.json()
    assert body["data"] is None
    code: str = body["error"]["code"]
    return code


def error_message(response: Any) -> str:
    message: str = response.json()["error"]["message"]
    return message
