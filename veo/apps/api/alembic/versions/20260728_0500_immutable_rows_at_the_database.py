"""Enforce immutability in the database, not only in the ORM

ADR 0012 says a published methodology cannot change, and the reports design says a
delivered report version cannot change. Both were enforced by SQLAlchemy event listeners
— which only fire for code that goes through the ORM, with the right module imported.
A migration, a psql session, an admin script or a future service in another language
walks straight past them.

An immutability rule that a raw UPDATE can bypass is documentation, not a guarantee.
These triggers make the claim true at the only layer that sees every writer.

Deliberately narrow:

* ``report_versions`` — no UPDATE at all. The table is an append-only snapshot log.
* ``scoring_versions`` — the specification, its checksum and its recorded golden results
  are frozen once the row reaches PUBLISHED or RETIRED. Status may still move (a
  published version can be retired) and operational columns stay writable.

Revision ID: 7f3c9a1d64e2
Revises: 9f0c1c619171
"""

from __future__ import annotations

from alembic import op

revision = "7f3c9a1d64e2"
down_revision = "9f0c1c619171"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE OR REPLACE FUNCTION veo_refuse_update() RETURNS trigger AS $$
        BEGIN
            RAISE EXCEPTION
                'VEO: % is append-only; row % cannot be updated',
                TG_TABLE_NAME, OLD.id
                USING ERRCODE = 'restrict_violation';
        END;
        $$ LANGUAGE plpgsql;
        """
    )
    op.execute(
        """
        CREATE TRIGGER report_versions_are_immutable
            BEFORE UPDATE ON report_versions
            FOR EACH ROW EXECUTE FUNCTION veo_refuse_update();
        """
    )

    op.execute(
        """
        CREATE OR REPLACE FUNCTION veo_freeze_published_scoring_version()
        RETURNS trigger AS $$
        BEGIN
            IF OLD.status IN ('PUBLISHED', 'RETIRED') THEN
                IF NEW.specification IS DISTINCT FROM OLD.specification
                   OR NEW.checksum IS DISTINCT FROM OLD.checksum
                   OR NEW.spec_id IS DISTINCT FROM OLD.spec_id
                   OR NEW.semantic_version IS DISTINCT FROM OLD.semantic_version
                   OR NEW.golden_fixture_results IS DISTINCT FROM OLD.golden_fixture_results
                THEN
                    RAISE EXCEPTION
                        'VEO: scoring version %@% is % and its specification is frozen; '
                        'publish a new version instead',
                        OLD.spec_id, OLD.semantic_version, OLD.status
                        USING ERRCODE = 'restrict_violation';
                END IF;
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        """
    )
    op.execute(
        """
        CREATE TRIGGER scoring_versions_freeze_when_published
            BEFORE UPDATE ON scoring_versions
            FOR EACH ROW EXECUTE FUNCTION veo_freeze_published_scoring_version();
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS scoring_versions_freeze_when_published ON scoring_versions")
    op.execute("DROP TRIGGER IF EXISTS report_versions_are_immutable ON report_versions")
    op.execute("DROP FUNCTION IF EXISTS veo_freeze_published_scoring_version()")
    op.execute("DROP FUNCTION IF EXISTS veo_refuse_update()")
