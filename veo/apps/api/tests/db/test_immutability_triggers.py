"""Immutability holds against raw SQL, not just against the ORM.

Both guarantees were enforced by SQLAlchemy event listeners, which fire only for code
that goes through the ORM with the right module imported. These tests deliberately
bypass the ORM entirely — if the guarantee only survives when everyone is polite, it is
not a guarantee.
"""

from __future__ import annotations

import os
import uuid
from collections.abc import Iterator

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.exc import DBAPIError

DATABASE_URL = os.environ.get("VEO_TEST_DATABASE_URL")

pytestmark = [
    pytest.mark.requires_postgres,
    pytest.mark.skipif(not DATABASE_URL, reason="needs VEO_TEST_DATABASE_URL"),
]


@pytest.fixture
def connection() -> Iterator:  # type: ignore[type-arg]
    assert DATABASE_URL is not None
    engine = create_engine(DATABASE_URL)
    with engine.begin() as conn:
        yield conn
        conn.rollback()
    engine.dispose()


def _organization(conn) -> uuid.UUID:  # type: ignore[no-untyped-def]
    org_id = uuid.uuid4()
    conn.execute(
        text(
            "INSERT INTO organizations (id, slug, name, is_active, settings, created_at, "
            "updated_at) VALUES (:id, :slug, :name, true, '{}'::jsonb, now(), now())"
        ),
        {"id": org_id, "slug": f"trig-{org_id.hex[:10]}", "name": "트리거 테스트"},
    )
    return org_id


# --------------------------------------------------------------------------- #
# report_versions — append only
# --------------------------------------------------------------------------- #


def test_a_report_version_cannot_be_updated_by_raw_sql(connection) -> None:  # type: ignore[no-untyped-def]
    org_id = _organization(connection)
    report_id, version_id = uuid.uuid4(), uuid.uuid4()

    _report_version(connection, org_id, report_id, version_id)

    with pytest.raises(DBAPIError) as exc:
        connection.execute(
            text("UPDATE report_versions SET content = '{\"score\": 100}'::jsonb WHERE id = :id"),
            {"id": version_id},
        )
    assert "append-only" in str(exc.value)


def test_a_report_version_cannot_be_touched_even_trivially(connection) -> None:  # type: ignore[no-untyped-def]
    """No 'harmless' update either — the table is closed, not selectively closed."""
    org_id = _organization(connection)
    report_id, version_id = uuid.uuid4(), uuid.uuid4()
    _report_version(connection, org_id, report_id, version_id)

    with pytest.raises(DBAPIError):
        connection.execute(
            text("UPDATE report_versions SET version_number = 2 WHERE id = :id"),
            {"id": version_id},
        )


# --------------------------------------------------------------------------- #
# scoring_versions — frozen once published
# --------------------------------------------------------------------------- #


def _report_version(conn, org_id, report_id, version_id) -> None:  # type: ignore[no-untyped-def]
    # reports.project_id is NOT NULL, so the whole ownership chain has to exist.
    customer_id, project_id = uuid.uuid4(), uuid.uuid4()
    conn.execute(
        text(
            "INSERT INTO customers (id, organization_id, name, is_active, created_at, "
            "updated_at) VALUES (:id, :org, '테스트 고객', true, now(), now())"
        ),
        {"id": customer_id, "org": org_id},
    )
    conn.execute(
        text(
            "INSERT INTO projects (id, organization_id, customer_id, slug, name, locale, "
            "settings, created_at, updated_at) VALUES (:id, :org, :customer, :slug, "
            "'테스트 프로젝트', 'ko-KR', '{}'::jsonb, now(), now())"
        ),
        {
            "id": project_id,
            "org": org_id,
            "customer": customer_id,
            "slug": f"trig-{project_id.hex[:10]}",
        },
    )
    conn.execute(
        text(
            "INSERT INTO reports (id, organization_id, project_id, title, audience, "
            "created_at, updated_at) VALUES (:id, :org, :project, '테스트 보고서', "
            "'EXECUTIVE', now(), now())"
        ),
        {"id": report_id, "org": org_id, "project": project_id},
    )
    conn.execute(
        text(
            "INSERT INTO report_versions (id, organization_id, report_id, version_number, "
            "included_run_ids, scoring_versions, content, disclosures_ko, export_formats, "
            "created_at) VALUES (:id, :org, :report, 1, '[]'::jsonb, '{}'::jsonb, "
            "'{\"score\": 85}'::jsonb, '[]'::jsonb, '[]'::jsonb, now())"
        ),
        {"id": version_id, "org": org_id, "report": report_id},
    )


def _scoring_version(conn, status: str) -> uuid.UUID:  # type: ignore[no-untyped-def]
    version_id = uuid.uuid4()
    conn.execute(
        text(
            "INSERT INTO scoring_versions (id, spec_id, domain, semantic_version, status, "
            "specification, checksum, compatible_collector_versions, golden_fixture_results, "
            "created_at) VALUES (:id, :spec, 'SEO_READINESS', '9.9.9', :status, "
            "'{\"weight\": 25}'::jsonb, :checksum, '[]'::jsonb, '{}'::jsonb, now())"
        ),
        {
            "id": version_id,
            "spec": f"veo.test.{version_id.hex[:8]}",
            "status": status,
            "checksum": "d" * 64,
        },
    )
    return version_id


def test_a_published_specification_cannot_be_rewritten(connection) -> None:  # type: ignore[no-untyped-def]
    version_id = _scoring_version(connection, "PUBLISHED")

    with pytest.raises(DBAPIError) as exc:
        connection.execute(
            text("UPDATE scoring_versions SET specification = '{\"weight\": 1}'::jsonb "
                 "WHERE id = :id"),
            {"id": version_id},
        )
    assert "frozen" in str(exc.value)


def test_rewriting_the_checksum_to_match_a_tampered_spec_also_fails(connection) -> None:  # type: ignore[no-untyped-def]
    """The gap a worker named: changing the document *and* its checksum together.

    Checksum verification alone cannot catch that, because the row stays self-consistent.
    The trigger can, because it sees the old row.
    """
    version_id = _scoring_version(connection, "PUBLISHED")

    with pytest.raises(DBAPIError):
        connection.execute(
            text(
                "UPDATE scoring_versions SET specification = '{\"weight\": 1}'::jsonb, "
                "checksum = :new WHERE id = :id"
            ),
            {"new": "e" * 64, "id": version_id},
        )


def test_golden_results_are_frozen_once_published(connection) -> None:  # type: ignore[no-untyped-def]
    version_id = _scoring_version(connection, "PUBLISHED")
    with pytest.raises(DBAPIError):
        connection.execute(
            text("UPDATE scoring_versions SET golden_fixture_results = "
                 "'{\"faked\": true}'::jsonb WHERE id = :id"),
            {"id": version_id},
        )


def test_a_published_version_may_still_be_retired(connection) -> None:  # type: ignore[no-untyped-def]
    """Freezing the content must not freeze the lifecycle."""
    version_id = _scoring_version(connection, "PUBLISHED")
    connection.execute(
        text("UPDATE scoring_versions SET status = 'RETIRED' WHERE id = :id"),
        {"id": version_id},
    )
    status = connection.execute(
        text("SELECT status FROM scoring_versions WHERE id = :id"), {"id": version_id}
    ).scalar_one()
    assert status == "RETIRED"


def test_a_draft_specification_is_still_editable(connection) -> None:  # type: ignore[no-untyped-def]
    """The freeze applies to published methodology, not to work in progress."""
    version_id = _scoring_version(connection, "DRAFT")
    connection.execute(
        text("UPDATE scoring_versions SET specification = '{\"weight\": 30}'::jsonb "
             "WHERE id = :id"),
        {"id": version_id},
    )
    spec = connection.execute(
        text("SELECT specification FROM scoring_versions WHERE id = :id"), {"id": version_id}
    ).scalar_one()
    assert spec == {"weight": 30}
