"""Fixtures shared by the public-surface suite."""

from __future__ import annotations

import pytest
from public_support import ServiceClock


@pytest.fixture
def clock() -> ServiceClock:
    """A movable clock, so result expiry can be crossed inside a test."""
    return ServiceClock()
