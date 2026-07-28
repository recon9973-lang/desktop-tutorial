"""Fixtures for the ``veo.common`` suite.

Every test in this package is fully offline. The autouse ``_forbid_real_dns`` fixture
detonates if any code path reaches the real resolver, so a regression that quietly
re-introduces a live lookup fails loudly instead of silently making the suite
network-dependent and non-deterministic.
"""

from __future__ import annotations

import socket
from typing import Any

import pytest
from fakes import ZONE, FakeResolver

from veo.common.security.url_guard import UrlGuard, UrlGuardPolicy


@pytest.fixture(autouse=True)
def _forbid_real_dns(monkeypatch: pytest.MonkeyPatch) -> None:
    """Fail the test if anything attempts a real name lookup."""

    def _detonate(*args: Any, **kwargs: Any) -> Any:
        raise AssertionError("test attempted a real DNS lookup")

    monkeypatch.setattr(socket, "getaddrinfo", _detonate)
    monkeypatch.setattr(socket, "gethostbyname", _detonate)
    monkeypatch.setattr(socket, "gethostbyname_ex", _detonate)


@pytest.fixture
def resolver() -> FakeResolver:
    return FakeResolver(ZONE)


@pytest.fixture
def guard(resolver: FakeResolver) -> UrlGuard:
    return UrlGuard(resolver=resolver)


@pytest.fixture
def permissive_port_guard(resolver: FakeResolver) -> UrlGuard:
    return UrlGuard(
        resolver=resolver,
        policy=UrlGuardPolicy(allowed_ports=frozenset({80, 443, 8080})),
    )
