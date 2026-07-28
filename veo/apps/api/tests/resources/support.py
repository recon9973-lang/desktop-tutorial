"""Shared values and small types for the resource tests.

These live outside ``conftest.py`` so that a test module can import them by name.
``conftest`` is loaded by pytest under its own module name; importing from it directly
would give the test a second copy of every class defined there.
"""

from __future__ import annotations

import os
import uuid
from dataclasses import dataclass
from typing import Any

from veo.authz.principal import Principal
from veo.core.settings import get_settings

DATABASE_URL = os.environ.get("VEO_TEST_DATABASE_URL")

API_PREFIX = get_settings().api_prefix

ORGANIZATIONS = f"{API_PREFIX}/organizations"
CUSTOMERS = f"{API_PREFIX}/customers"
PROJECTS = f"{API_PREFIX}/projects"
SITES = f"{API_PREFIX}/sites"


@dataclass(frozen=True)
class Tenant:
    """One organization plus a writer and a read-only caller inside it."""

    organization_id: uuid.UUID
    slug: str
    name: str
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


def error_code(response: Any) -> str:
    body = response.json()
    assert body["data"] is None
    code: str = body["error"]["code"]
    return code
