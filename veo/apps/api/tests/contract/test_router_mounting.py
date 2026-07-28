"""Every engine is actually reachable in the assembled application.

This file exists because the obvious way to check mounting does not work. On this
FastAPI version ``app.include_router(...)`` appends a single ``_IncludedRouter`` object
whose ``path`` is ``None`` rather than flattening the child routes into ``app.routes``.
So any assertion of the form::

    any(route.path.startswith("/api/keywords") for route in app.routes)

is vacuously false no matter what is mounted. Three test suites had a guard of exactly
that shape; each one silently mounted its router a second time, which duplicated every
OpenAPI operation id and would have produced a broken TypeScript client.

The generated OpenAPI document is the honest source of truth, so that is what is checked
here.
"""

from __future__ import annotations

import collections

import pytest

from veo.api.app import create_app

#: Every router the product expects to serve, and one path that proves it is there.
EXPECTED_MOUNTS = {
    "meta": "/api/health",
    "providers": "/api/providers",
    "scoring": "/api/scoring/specs",
    "auth": "/api/auth/login",
    "organizations": "/api/organizations/current",
    "customers": "/api/customers",
    "projects": "/api/projects",
    "sites": "/api/sites",
    "credentials": "/api/credentials",
    "geo": "/api/geo/readiness/analyses",
    "keywords": "/api/keywords/lookups",
    "seo": "/api/seo/scan",
    "competitors": "/api/competitors/comparisons",
    "issues": "/api/issues",
    "lab": "/api/lab/scoring-versions",
    "reports": "/api/reports",
}


@pytest.fixture(scope="module")
def document() -> dict:
    return create_app().openapi()


@pytest.mark.parametrize(("name", "path"), sorted(EXPECTED_MOUNTS.items()))
def test_router_is_mounted(document: dict, name: str, path: str) -> None:
    assert path in document["paths"], f"the {name} router is not reachable"


def test_app_routes_cannot_be_used_to_detect_mounting(document: dict) -> None:
    """Pin the surprise, so nobody writes that guard again.

    If a future FastAPI flattens included routers back into ``app.routes``, this test
    fails and the comment above can be deleted along with it.
    """
    app = create_app()
    paths_from_routes = {str(getattr(route, "path", "")) for route in app.routes}
    assert "/api/keywords/lookups" not in paths_from_routes
    assert len(document["paths"]) > len(paths_from_routes)


def test_no_operation_id_is_duplicated(document: dict) -> None:
    """A duplicate operation id silently breaks generated-client method names."""
    operation_ids = [
        operation["operationId"]
        for path_item in document["paths"].values()
        for operation in path_item.values()
        if isinstance(operation, dict) and "operationId" in operation
    ]
    duplicates = sorted(
        name for name, count in collections.Counter(operation_ids).items() if count > 1
    )
    assert not duplicates, f"duplicate operation ids: {duplicates}"


def test_no_path_is_registered_twice(document: dict) -> None:
    app = create_app()
    seen = collections.Counter(
        str(getattr(route, "path", "")) for route in app.routes if getattr(route, "path", None)
    )
    assert not [p for p, c in seen.items() if c > 1]


def test_building_the_app_twice_produces_the_same_surface() -> None:
    """Router objects are module-level singletons; mounting must not accumulate."""
    first = set(create_app().openapi()["paths"])
    second = set(create_app().openapi()["paths"])
    assert first == second
