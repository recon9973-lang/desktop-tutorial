"""Fixtures shared by the GEO readiness tests."""

from __future__ import annotations

import pytest
from tests.geo.support import GeoCase, case_names, iter_cases, load_case

from veo.scoring import ScoringSpec, latest_published


@pytest.fixture(scope="session")
def spec() -> ScoringSpec:
    return latest_published("veo.geo.readiness")


@pytest.fixture(scope="session")
def all_cases() -> dict[str, GeoCase]:
    return {case.name: case for case in iter_cases()}


@pytest.fixture
def case() -> object:
    def _load(name: str) -> GeoCase:
        return load_case(name)

    return _load


def pytest_generate_tests(metafunc: pytest.Metafunc) -> None:
    if "case_name" in metafunc.fixturenames:
        metafunc.parametrize("case_name", case_names())
