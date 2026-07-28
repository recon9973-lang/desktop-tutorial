"""Anonymous means anonymous — asserted by inspection, not by assurance.

A public route that could read one customer's row would be the worst bug VEO could ship,
and it would not announce itself in a response body. So this suite reads the package's
own imports and the router's own dependency graph: no database session, no ORM model, no
tenant repository, no authenticated principal anywhere in the public surface.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest
from fastapi.routing import APIRoute

from veo.authz.deps import get_optional_principal, get_principal
from veo.db.session import get_db
from veo.public.router import router as public_router

PACKAGE_ROOT = Path(__file__).resolve().parents[2] / "src" / "veo" / "public"

#: Modules that only exist to reach a customer's data. None of them belongs here.
FORBIDDEN_IMPORT_ROOTS = (
    "sqlalchemy",
    "veo.db",
    "veo.organizations",
    "veo.customers",
    "veo.projects",
    "veo.sites",
    "veo.credentials",
    "veo.competitors",
    "veo.issues",
    "veo.reports",
    "veo.observations",
    "veo.compare",
    "veo.lab",
    "veo.auth",
    "veo.authz",
    "veo.keywords.repository",
)

#: Names that mean "a tenant row", wherever they were imported from.
FORBIDDEN_NAMES = (
    "SqlKeywordRepository",
    "get_db",
    "Session",
    "sessionmaker",
)


def public_modules() -> list[Path]:
    return sorted(PACKAGE_ROOT.glob("*.py"))


def test_the_package_actually_has_modules() -> None:
    """Guard against this whole suite passing because it found nothing to check."""
    names = {path.name for path in public_modules()}
    assert {"limits.py", "tokens.py", "schemas.py", "service.py", "router.py", "leads.py"} <= names


def imported_modules(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    found: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            found.add(node.module)
    return found


@pytest.mark.parametrize("path", public_modules(), ids=lambda path: path.name)
def test_no_public_module_imports_a_tenant_scoped_package(path: Path) -> None:
    for module in imported_modules(path):
        for forbidden in FORBIDDEN_IMPORT_ROOTS:
            assert module != forbidden and not module.startswith(f"{forbidden}."), (
                f"{path.name} imports {module}, which reaches customer data"
            )


@pytest.mark.parametrize("path", public_modules(), ids=lambda path: path.name)
def test_no_public_module_names_a_tenant_row(path: Path) -> None:
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    used = {node.id for node in ast.walk(tree) if isinstance(node, ast.Name)}
    used |= {node.attr for node in ast.walk(tree) if isinstance(node, ast.Attribute)}
    for name in FORBIDDEN_NAMES:
        assert name not in used, f"{path.name} refers to {name}"


def flat_dependencies(route: APIRoute) -> set[object]:
    """Every callable FastAPI would invoke to serve this route."""
    collected: set[object] = set()
    pending = list(route.dependant.dependencies)
    while pending:
        dependant = pending.pop()
        if dependant.call is not None:
            collected.add(dependant.call)
        pending.extend(dependant.dependencies)
    if route.dependant.call is not None:
        collected.add(route.dependant.call)
    return collected


def test_no_public_route_depends_on_a_database_session_or_a_principal() -> None:
    routes = [route for route in public_router.routes if isinstance(route, APIRoute)]
    assert routes
    for route in routes:
        calls = flat_dependencies(route)
        assert get_db not in calls, f"{route.path} opens a database session"
        assert get_principal not in calls, f"{route.path} demands a principal"
        assert get_optional_principal not in calls, f"{route.path} reads a principal"


def test_no_public_route_pulls_in_the_authorization_machinery() -> None:
    """Not because permissions are bad — because a public route must not have a tenant.

    Checked by the module every dependency was defined in, which survives a FastAPI
    upgrade renaming its internals.
    """
    forbidden = ("veo.authz", "veo.auth", "veo.organizations", "veo.db")
    for route in public_router.routes:
        if not isinstance(route, APIRoute):
            continue
        for call in flat_dependencies(route):
            module = str(getattr(call, "__module__", ""))
            for prefix in forbidden:
                assert module != prefix and not module.startswith(f"{prefix}."), (
                    f"{route.path} depends on {module}"
                )


def test_the_public_package_writes_nothing_durable() -> None:
    """The only state the public surface keeps is the expiring result and the lead."""
    for path in public_modules():
        source = path.read_text(encoding="utf-8")
        assert "commit()" not in source
        assert "flush()" not in source
