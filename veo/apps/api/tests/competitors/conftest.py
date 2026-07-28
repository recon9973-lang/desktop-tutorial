"""PostgreSQL fixtures for the one test module that needs a real database.

Everything else in this suite runs against in-memory fakes on purpose: the comparison
engine has no business knowing what a session is, and a test that needs a database to
prove an arithmetic property is a test that will eventually be skipped and rot.

The migrations are re-run before the first database test because ``tests/db`` downgrades
to base in its own teardown; creating the tables behind Alembic's back instead would
leave ``alembic_version`` disagreeing with the schema.
"""

from __future__ import annotations

import os
from collections.abc import Iterator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

DATABASE_URL = os.environ.get("VEO_TEST_DATABASE_URL")

API_ROOT = Path(__file__).resolve().parents[2]


def _migrate_to_head() -> None:
    assert DATABASE_URL is not None
    config = Config(str(API_ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(API_ROOT / "alembic"))
    previous = os.environ.get("VEO_DATABASE_URL")
    os.environ["VEO_DATABASE_URL"] = DATABASE_URL
    try:
        command.upgrade(config, "head")
    finally:
        if previous is None:
            os.environ.pop("VEO_DATABASE_URL", None)
        else:
            os.environ["VEO_DATABASE_URL"] = previous


@pytest.fixture(scope="session")
def engine() -> Iterator[Engine]:
    if DATABASE_URL is None:
        pytest.skip("set VEO_TEST_DATABASE_URL to run the database-backed competitor tests")
    _migrate_to_head()
    created = create_engine(DATABASE_URL, future=True)
    try:
        yield created
    finally:
        created.dispose()


@pytest.fixture
def db(engine: Engine) -> Iterator[Session]:
    factory = sessionmaker(bind=engine, expire_on_commit=False, class_=Session)
    session = factory()
    try:
        yield session
    finally:
        session.rollback()
        session.close()
