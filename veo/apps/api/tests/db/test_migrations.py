"""Migration tests against a real PostgreSQL instance.

These tests downgrade the schema to base, which destroys every table. They therefore run
against their **own** database, never the shared ``veo_test`` one: any other suite running
concurrently — another developer, another CI job, a parallel agent — would otherwise see
its tables vanish mid-transaction and fail with ``UndefinedTable`` or a deadlock.

The dedicated database is created on demand and dropped afterwards. Override its name with
``VEO_MIGRATION_TEST_DATABASE_URL`` if the default derivation does not suit your setup.

Skipped when ``VEO_TEST_DATABASE_URL`` is unset, so the suite still runs offline — but a
skipped migration test is a gap, not a pass. CI must set the variable.
"""

from __future__ import annotations

import os
from collections.abc import Iterator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import make_url

from veo.db.models import Base

API_ROOT = Path(__file__).resolve().parents[2]

SHARED_DATABASE_URL = os.environ.get("VEO_TEST_DATABASE_URL")


def _migration_database_url() -> str | None:
    """A database this module may safely destroy."""
    explicit = os.environ.get("VEO_MIGRATION_TEST_DATABASE_URL")
    if explicit:
        return explicit
    if not SHARED_DATABASE_URL:
        return None
    url = make_url(SHARED_DATABASE_URL)
    # `str(url)` 은 비밀번호를 `***` 로 가린다. 그 문자열로 접속하면 인증에 실패한다.
    return url.set(database=f"{url.database}_migrations").render_as_string(hide_password=False)


DATABASE_URL = _migration_database_url()

pytestmark = [
    pytest.mark.requires_postgres,
    pytest.mark.skipif(
        not DATABASE_URL,
        reason="set VEO_TEST_DATABASE_URL to run migration tests against PostgreSQL",
    ),
]


@pytest.fixture(scope="module", autouse=True)
def migration_database() -> Iterator[None]:
    """Create the throwaway database for this module, and drop it afterwards."""
    assert DATABASE_URL is not None
    url = make_url(DATABASE_URL)
    admin = create_engine(
        url.set(database="postgres").render_as_string(hide_password=False),
        isolation_level="AUTOCOMMIT",
    )
    name = url.database
    try:
        with admin.connect() as connection:
            connection.execute(text(f'DROP DATABASE IF EXISTS "{name}" WITH (FORCE)'))
            connection.execute(text(f'CREATE DATABASE "{name}"'))
        yield
        with admin.connect() as connection:
            connection.execute(text(f'DROP DATABASE IF EXISTS "{name}" WITH (FORCE)'))
    finally:
        admin.dispose()


@pytest.fixture
def alembic_config() -> Iterator[Config]:
    config = Config(str(API_ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(API_ROOT / "alembic"))
    assert DATABASE_URL is not None
    # Point Alembic at the throwaway database, and restore the caller's value afterwards
    # so a later test does not inherit it.
    previous = os.environ.get("VEO_DATABASE_URL")
    os.environ["VEO_DATABASE_URL"] = DATABASE_URL
    try:
        yield config
    finally:
        if previous is None:
            os.environ.pop("VEO_DATABASE_URL", None)
        else:
            os.environ["VEO_DATABASE_URL"] = previous


@pytest.fixture
def clean_database(alembic_config: Config) -> Iterator[Config]:
    command.downgrade(alembic_config, "base")
    yield alembic_config
    command.downgrade(alembic_config, "base")


def test_upgrade_creates_every_mapped_table(clean_database: Config) -> None:
    command.upgrade(clean_database, "head")

    assert DATABASE_URL is not None
    engine = create_engine(DATABASE_URL)
    try:
        present = set(inspect(engine).get_table_names())
    finally:
        engine.dispose()

    missing = set(Base.metadata.tables) - present
    assert not missing, f"migration did not create: {sorted(missing)}"


def test_downgrade_removes_every_table(clean_database: Config) -> None:
    command.upgrade(clean_database, "head")
    command.downgrade(clean_database, "base")

    assert DATABASE_URL is not None
    engine = create_engine(DATABASE_URL)
    try:
        remaining = set(inspect(engine).get_table_names()) - {"alembic_version"}
    finally:
        engine.dispose()

    assert not remaining, f"downgrade left tables behind: {sorted(remaining)}"


def test_upgrade_is_repeatable_after_a_full_cycle(clean_database: Config) -> None:
    command.upgrade(clean_database, "head")
    command.downgrade(clean_database, "base")
    command.upgrade(clean_database, "head")

    assert DATABASE_URL is not None
    engine = create_engine(DATABASE_URL)
    try:
        present = set(inspect(engine).get_table_names())
    finally:
        engine.dispose()
    assert set(Base.metadata.tables) <= present


def test_models_and_migrations_have_not_drifted(clean_database: Config) -> None:
    """Autogenerate against the migrated database must find nothing left to do."""
    from alembic.autogenerate import compare_metadata
    from alembic.migration import MigrationContext

    command.upgrade(clean_database, "head")

    assert DATABASE_URL is not None
    engine = create_engine(DATABASE_URL)
    try:
        with engine.connect() as connection:
            context = MigrationContext.configure(
                connection,
                opts={"compare_type": True, "compare_server_default": True},
            )
            diff = compare_metadata(context, Base.metadata)
    finally:
        engine.dispose()

    assert not diff, (
        "models and migrations have drifted; regenerate the migration:\n"
        + "\n".join(str(entry) for entry in diff)
    )
