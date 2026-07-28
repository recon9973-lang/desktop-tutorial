"""Structural cross-tenant isolation.

Reviewer discipline does not scale: sooner or later a query is written without its
``organization_id`` filter, and that query silently returns another customer's rows.
So the rule is enforced by machinery instead.

Two pieces:

* :func:`tenant_select` builds a ``SELECT`` that already carries the filter.
* :func:`assert_tenant_scoped` inspects any statement and refuses one that touches a
  tenant-owned table without an equality predicate on that table's ``organization_id``.

``assert_tenant_scoped`` insists on a *conjunctive* predicate. ``WHERE org = :me OR
slug = 'x'`` is rejected, because an OR branch is exactly how a tenant filter stops
filtering.
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import BinaryExpression, Select, Table, select
from sqlalchemy.sql import operators
from sqlalchemy.sql.elements import BindParameter, BooleanClauseList, ColumnClause

from veo.authz.errors import TenantIsolationError
from veo.authz.principal import Principal
from veo.db.models import Base

TENANT_COLUMN = "organization_id"


def tenant_table_names() -> set[str]:
    """Every table whose rows belong to exactly one organization.

    A nullable ``organization_id`` means the row deliberately outlives its organization
    (audit trail, usage accounting), so those tables are not tenant-scoped for the
    purposes of this guard and are protected by permissions instead.
    """
    return {
        table.name
        for table in Base.metadata.tables.values()
        if TENANT_COLUMN in table.c and not table.c[TENANT_COLUMN].nullable
    }


def is_tenant_scoped_model(model: type[Any]) -> bool:
    table = getattr(model, "__table__", None)
    if table is None:
        return False
    return table.name in tenant_table_names()


def tenant_select[T](model: type[T], principal: Principal) -> Select[tuple[T]]:
    """``SELECT`` from ``model``, already restricted to the caller's organization."""
    if not is_tenant_scoped_model(model):
        raise TenantIsolationError(
            f"{model.__name__} is not tenant-scoped; use a plain select() and guard it "
            "with permissions instead"
        )
    column = model.__table__.c[TENANT_COLUMN]  # type: ignore[attr-defined]
    return select(model).where(column == principal.organization_id)


def assert_tenant_scoped(statement: Select[Any], organization_id: uuid.UUID) -> None:
    """Raise unless every tenant-owned table in ``statement`` is filtered to this org.

    Call this immediately before execution. It is cheap, and it converts a data-leak
    class of bug into a loud failure during development and testing.
    """
    touched = _tenant_tables_in(statement)
    if not touched:
        return

    scoped = _conjunctively_scoped_tables(statement, organization_id)

    unscoped = sorted(name for name in touched if name not in scoped)
    if unscoped:
        raise TenantIsolationError(
            "query touches tenant-owned table(s) without an organization filter: "
            + ", ".join(unscoped)
        )


# --------------------------------------------------------------------------- #
# Internals
# --------------------------------------------------------------------------- #


def _tenant_tables_in(statement: Select[Any]) -> set[str]:
    tenant_tables = tenant_table_names()
    found: set[str] = set()
    for element in statement.get_final_froms():
        for table in _tables_of(element):
            if table.name in tenant_tables:
                found.add(table.name)
    # A column selected from a table that is not in FROM (rare, but possible through
    # correlated constructs) still touches that table.
    for column in statement.selected_columns:
        owner: Any = getattr(column, "table", None)
        if isinstance(owner, Table) and owner.name in tenant_tables:
            found.add(owner.name)
    return found


def _tables_of(element: Any) -> list[Table]:
    if isinstance(element, Table):
        return [element]
    tables: list[Table] = []
    left = getattr(element, "left", None)
    right = getattr(element, "right", None)
    if left is not None:
        tables.extend(_tables_of(left))
    if right is not None:
        tables.extend(_tables_of(right))
    if not tables:
        inner = getattr(element, "element", None)
        if inner is not None:
            tables.extend(_tables_of(inner))
    return tables


def _conjunctively_scoped_tables(
    statement: Select[Any], organization_id: uuid.UUID
) -> set[str]:
    """Tables whose organization_id is pinned by a top-level AND-ed equality."""
    scoped: set[str] = set()
    for clause in _and_terms(statement.whereclause):
        table_name = _tenant_equality_target(clause, organization_id)
        if table_name:
            scoped.add(table_name)

    # ON clauses of a JOIN are also conjunctive with the WHERE clause.
    for element in statement.get_final_froms():
        for clause in _join_conditions(element):
            for term in _and_terms(clause):
                table_name = _tenant_equality_target(term, organization_id)
                if table_name:
                    scoped.add(table_name)
    return scoped


def _and_terms(clause: Any) -> list[Any]:
    """Flatten a top-level AND chain. An OR node yields nothing — by design."""
    if clause is None:
        return []
    if isinstance(clause, BooleanClauseList):
        if clause.operator is operators.and_:
            terms: list[Any] = []
            for child in clause.clauses:
                terms.extend(_and_terms(child))
            return terms
        # OR (or anything else) cannot guarantee the filter holds for every row.
        return []
    return [clause]


def _join_conditions(element: Any) -> list[Any]:
    conditions: list[Any] = []
    onclause = getattr(element, "onclause", None)
    if onclause is not None:
        conditions.append(onclause)
    for side in ("left", "right"):
        child = getattr(element, side, None)
        if child is not None:
            conditions.extend(_join_conditions(child))
    return conditions


def _tenant_equality_target(clause: Any, organization_id: uuid.UUID) -> str | None:
    """Return the table name if ``clause`` pins its organization_id to this org."""
    if not isinstance(clause, BinaryExpression):
        return None
    if clause.operator is not operators.eq:
        return None

    for column_side, value_side in ((clause.left, clause.right), (clause.right, clause.left)):
        if not isinstance(column_side, ColumnClause):
            continue
        if column_side.name != TENANT_COLUMN:
            continue
        owner: Any = getattr(column_side, "table", None)
        if not isinstance(owner, Table):
            continue
        if not _binds_to(value_side, organization_id):
            continue
        return str(owner.name)
    return None


def _binds_to(value: Any, organization_id: uuid.UUID) -> bool:
    if isinstance(value, BindParameter):
        return value.value == organization_id or str(value.value) == str(organization_id)
    return False
