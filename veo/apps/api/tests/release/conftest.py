"""A database session for the release checks, rolled back after every test.

The bootstrap tests are the only ones in VEO that assert on an *empty* database — the
whole point is what happens when nothing exists yet. So the session runs inside a
transaction that is discarded at the end, and each test first clears the identity tables
so a row left by a neighbouring suite cannot make "no organization exists" false and turn
a real failure into a passing refusal.
"""

from __future__ import annotations

import os
from collections.abc import Iterator

import pytest
from sqlalchemy import Engine, create_engine, inspect, text
from sqlalchemy.orm import Session

DATABASE_URL = os.environ.get("VEO_TEST_DATABASE_URL")

#: Child tables first: role_assignments references both of the others.
_IDENTITY_TABLES = ("role_assignments", "users", "organizations")


@pytest.fixture(scope="session")
def engine() -> Iterator[Engine]:
    if DATABASE_URL is None:
        pytest.skip("VEO_TEST_DATABASE_URL is not set")
    created = create_engine(DATABASE_URL, future=True)
    present = set(inspect(created).get_table_names())
    missing = set(_IDENTITY_TABLES) - present
    if missing:
        created.dispose()
        pytest.skip(f"veo_test is not migrated; missing {sorted(missing)}")
    try:
        yield created
    finally:
        created.dispose()


@pytest.fixture
def db(engine: Engine) -> Iterator[Session]:
    connection = engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection, join_transaction_mode="create_savepoint")
    # Inside the outer transaction, so this is undone with everything else.
    for table in _IDENTITY_TABLES:
        session.execute(text(f"DELETE FROM {table}"))  # noqa: S608 — fixed identifiers
    session.flush()
    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()
