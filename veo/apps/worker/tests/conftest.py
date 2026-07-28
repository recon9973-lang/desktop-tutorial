"""Shared fixtures.

Every test in this suite runs without a broker. Redis is not reachable in the Phase 0
environment, so anything that would genuinely need one is marked ``requires_redis`` and
skipped unless ``VEO_TEST_REDIS_URL`` is set. Nothing here fakes a passing broker test.
"""

from __future__ import annotations

import os
from collections.abc import Iterator

import pytest

_BROKER_ENV_VARS = (
    "VEO_BROKER_URL",
    "VEO_RESULT_BACKEND_URL",
    "VEO_WORKER_TASK_TIME_LIMIT",
    "VEO_WORKER_TASK_SOFT_TIME_LIMIT",
    "VEO_WORKER_MAX_ATTEMPTS",
)


@pytest.fixture(autouse=True)
def _clean_worker_env(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """Stop a developer's ambient broker settings from changing test outcomes."""
    for name in _BROKER_ENV_VARS:
        monkeypatch.delenv(name, raising=False)
    yield


@pytest.fixture(scope="session")
def live_redis_url() -> str:
    url = os.environ.get("VEO_TEST_REDIS_URL")
    if not url:
        pytest.skip("VEO_TEST_REDIS_URL is unset; no live broker available.")
    return url
