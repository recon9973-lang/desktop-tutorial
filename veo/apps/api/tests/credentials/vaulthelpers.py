"""Shared helpers for the credential-vault suite.

Kept out of ``conftest.py`` so the test modules can import them by name without
depending on how pytest happens to have named the conftest module.
"""

from __future__ import annotations

import base64
import os
import uuid

import pytest

from veo.authz import Principal
from veo.contracts.enums import Role
from veo.db.models import Organization, User

DATABASE_URL = os.environ.get("VEO_TEST_DATABASE_URL")

requires_database = pytest.mark.skipif(
    not DATABASE_URL,
    reason="set VEO_TEST_DATABASE_URL to run credential vault tests against PostgreSQL",
)

#: Obviously synthetic key material. Never a plausible-looking real key.
MASTER_KEY_V1_B64 = base64.b64encode(bytes(range(32))).decode("ascii")
MASTER_KEY_V2_B64 = base64.b64encode(bytes(range(32, 64))).decode("ascii")

#: Obviously synthetic secrets. Never a plausible-looking real credential.
SECRET = "test-secret-not-a-real-key"
OTHER_SECRET = "test-secret-not-a-real-key-two"


def make_principal(organization: Organization, user: User, *roles: Role) -> Principal:
    """A principal built by hand. Authentication is another worker's job."""
    return Principal(
        user_id=user.id,
        organization_id=organization.id,
        roles=frozenset(roles or (Role.SUPER_ADMIN,)),
        session_id=uuid.uuid4().hex,
    )
