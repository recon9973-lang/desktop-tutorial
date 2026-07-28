"""The HTTP surface.

The single assertion that matters most is repeated on every endpoint: the secret string
must not appear anywhere in the serialized response. Everything else — permissions,
tenant isolation, error shape — protects that property.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import SecretStr
from vaulthelpers import SECRET, make_principal, requires_database

from veo.authz import Principal
from veo.authz.deps import get_principal
from veo.contracts.enums import ErrorCode, ProviderState, Role
from veo.credentials.providers import CredentialField, CredentialProvider
from veo.credentials.vault import CredentialVault
from veo.db.models import Organization, User

pytestmark = [pytest.mark.requires_postgres, requires_database]

OPENAI_KEY_PATH = "/api/credentials/OPENAI/api_key"


def assert_no_secret(response: Any) -> None:
    """The secret must be absent from the raw body and from the parsed JSON alike."""
    assert SECRET not in response.text
    assert SECRET not in json.dumps(response.json(), ensure_ascii=False)


def _store(client: TestClient, secret: str = SECRET) -> Any:
    return client.put(OPENAI_KEY_PATH, json={"secret": secret})


# --------------------------------------------------------------------------- #
# PUT — store
# --------------------------------------------------------------------------- #


def test_store_returns_state_only(client: TestClient) -> None:
    response = _store(client)
    assert response.status_code == 200
    assert_no_secret(response)

    payload = response.json()["data"]
    assert payload["provider"] == CredentialProvider.OPENAI.value
    assert payload["state"] == ProviderState.ENABLED.value
    field = payload["fields"][0]
    assert field["field"] == CredentialField.API_KEY.value
    assert field["is_configured"] is True
    assert field["display_hint"] == SECRET[-4:]
    assert len(field["fingerprint"]) == 64
    assert field["algorithm"] == "AES-256-GCM"


def test_store_response_has_no_field_wide_enough_to_hold_a_secret(
    client: TestClient,
) -> None:
    _store(client)
    field = client.get("/api/credentials").json()["data"]["providers"][0]["fields"][0]
    for key, value in field.items():
        if isinstance(value, str) and key not in {"field", "last_verification_error_code"}:
            assert len(value) <= 64


def test_store_rejects_an_empty_secret(client: TestClient) -> None:
    response = client.put(OPENAI_KEY_PATH, json={"secret": "   "})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == ErrorCode.VALIDATION_FAILED.value


def test_store_rejects_an_unknown_provider(client: TestClient) -> None:
    assert client.put("/api/credentials/NOT_A_PROVIDER/api_key",
                      json={"secret": SECRET}).status_code == 422


def test_store_rejects_a_data_source_that_is_not_a_credential_provider(
    client: TestClient,
) -> None:
    """VEO_CRAWLER is a real DataSource, but nobody stores a secret for it."""
    response = client.put("/api/credentials/VEO_CRAWLER/api_key", json={"secret": SECRET})
    assert response.status_code == 422
    assert_no_secret(response)


def test_store_rejects_a_field_the_provider_does_not_use(client: TestClient) -> None:
    response = client.put("/api/credentials/OPENAI/customer_id", json={"secret": SECRET})
    assert response.status_code == 422
    assert_no_secret(response)


def test_store_rejects_an_unknown_field(client: TestClient) -> None:
    assert client.put("/api/credentials/OPENAI/nope",
                      json={"secret": SECRET}).status_code == 422


def test_a_validation_error_does_not_echo_the_secret(client: TestClient) -> None:
    response = client.put("/api/credentials/OPENAI/customer_id", json={"secret": SECRET})
    assert SECRET not in response.text


def test_a_missing_body_does_not_echo_anything(client: TestClient) -> None:
    assert client.put(OPENAI_KEY_PATH, json={}).status_code == 422


# --------------------------------------------------------------------------- #
# GET — state list
# --------------------------------------------------------------------------- #


def test_list_reports_state_for_every_provider(client: TestClient) -> None:
    response = client.get("/api/credentials")
    assert response.status_code == 200
    assert_no_secret(response)

    providers = response.json()["data"]["providers"]
    assert len(providers) >= 5
    assert all(block["reason_ko"] for block in providers)
    assert all(
        block["state"] == ProviderState.DISABLED_NO_CREDENTIAL.value for block in providers
    )


def test_list_after_store_contains_no_secret(client: TestClient) -> None:
    _store(client)
    response = client.get("/api/credentials")
    assert response.status_code == 200
    assert_no_secret(response)

    openai = next(
        block
        for block in response.json()["data"]["providers"]
        if block["provider"] == CredentialProvider.OPENAI.value
    )
    assert openai["state"] == ProviderState.ENABLED.value


def test_list_is_readable_without_the_manage_permission(
    app: FastAPI,
    client: TestClient,
    organization_a: Organization,
    user: User,
) -> None:
    _store(client)
    app.dependency_overrides[get_principal] = lambda: make_principal(
        organization_a, user, Role.ANALYST
    )
    response = client.get("/api/credentials")
    assert response.status_code == 200
    assert_no_secret(response)


def test_list_is_refused_without_any_credential_permission(
    app: FastAPI, client: TestClient, organization_a: Organization, user: User
) -> None:
    app.dependency_overrides[get_principal] = lambda: make_principal(
        organization_a, user, Role.SALES_VIEWER
    )
    response = client.get("/api/credentials")
    assert response.status_code == 403
    assert response.json()["error"]["code"] == ErrorCode.PERMISSION_DENIED.value


# --------------------------------------------------------------------------- #
# DELETE — deactivate
# --------------------------------------------------------------------------- #


def test_delete_deactivates(client: TestClient) -> None:
    _store(client)
    response = client.delete(OPENAI_KEY_PATH)
    assert response.status_code == 200
    assert_no_secret(response)
    assert response.json()["data"]["fields"][0]["is_configured"] is False

    listed = client.get("/api/credentials").json()["data"]["providers"]
    openai = next(b for b in listed if b["provider"] == CredentialProvider.OPENAI.value)
    assert openai["state"] == ProviderState.DISABLED_NO_CREDENTIAL.value


def test_delete_of_a_missing_credential_is_404(client: TestClient) -> None:
    response = client.delete(OPENAI_KEY_PATH)
    assert response.status_code == 404
    assert response.json()["error"]["code"] == ErrorCode.NOT_FOUND.value


# --------------------------------------------------------------------------- #
# POST — verify
# --------------------------------------------------------------------------- #


def test_verify_reports_a_machine_code_only(client: TestClient) -> None:
    _store(client)
    response = client.post("/api/credentials/OPENAI/verify")
    assert response.status_code == 200
    assert_no_secret(response)

    payload = response.json()["data"]
    assert payload["verified"] is True
    assert payload["error_code"] is None
    assert payload["provider"]["fields"][0]["last_verified_at"] is not None


def test_verify_without_a_stored_credential_is_404(client: TestClient) -> None:
    response = client.post("/api/credentials/OPENAI/verify")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == ErrorCode.NOT_FOUND.value


def test_verify_reports_incomplete_credentials_without_prose(client: TestClient) -> None:
    client.put("/api/credentials/NAVER_SEARCH_AD/api_key", json={"secret": SECRET})
    response = client.post("/api/credentials/NAVER_SEARCH_AD/verify")
    assert response.status_code == 200
    assert_no_secret(response)

    payload = response.json()["data"]
    assert payload["verified"] is False
    assert payload["error_code"] == "MISSING_FIELDS"


# --------------------------------------------------------------------------- #
# Permissions: writing is SUPER_ADMIN only
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    "role", [Role.ANALYST, Role.DEVELOPER, Role.LAB_ADMIN, Role.SALES_VIEWER,
             Role.CLIENT_VIEWER]
)
def test_a_non_super_admin_cannot_store(
    app: FastAPI, client: TestClient, organization_a: Organization, user: User, role: Role
) -> None:
    app.dependency_overrides[get_principal] = lambda: make_principal(
        organization_a, user, role
    )
    response = _store(client)
    assert response.status_code == 403
    assert response.json()["error"]["code"] == ErrorCode.PERMISSION_DENIED.value
    assert_no_secret(response)


@pytest.mark.parametrize(
    "role", [Role.ANALYST, Role.DEVELOPER, Role.LAB_ADMIN, Role.SALES_VIEWER,
             Role.CLIENT_VIEWER]
)
def test_a_non_super_admin_cannot_delete(
    app: FastAPI, client: TestClient, organization_a: Organization, user: User, role: Role
) -> None:
    _store(client)
    app.dependency_overrides[get_principal] = lambda: make_principal(
        organization_a, user, role
    )
    response = client.delete(OPENAI_KEY_PATH)
    assert response.status_code == 403


@pytest.mark.parametrize("role", [Role.ANALYST, Role.DEVELOPER, Role.LAB_ADMIN])
def test_a_non_super_admin_cannot_verify(
    app: FastAPI, client: TestClient, organization_a: Organization, user: User, role: Role
) -> None:
    _store(client)
    app.dependency_overrides[get_principal] = lambda: make_principal(
        organization_a, user, role
    )
    assert client.post("/api/credentials/OPENAI/verify").status_code == 403


def test_a_principal_with_no_roles_is_refused(
    app: FastAPI, client: TestClient, organization_a: Organization, user: User
) -> None:
    app.dependency_overrides[get_principal] = lambda: make_principal(organization_a, user)
    app.dependency_overrides[get_principal] = lambda: Principal(
        user_id=user.id,
        organization_id=organization_a.id,
        roles=frozenset(),
        session_id="none",
    )
    assert client.get("/api/credentials").status_code == 403
    assert _store(client).status_code == 403


# --------------------------------------------------------------------------- #
# Tenant isolation: another organization's row is not found, not forbidden
# --------------------------------------------------------------------------- #


def test_another_organizations_credential_is_404_on_delete(
    app: FastAPI,
    client: TestClient,
    vault: CredentialVault,
    organization_b: Organization,
    user: User,
) -> None:
    vault.store(
        principal=make_principal(organization_b, user, Role.SUPER_ADMIN),
        provider=CredentialProvider.OPENAI,
        field=CredentialField.API_KEY,
        secret=SecretStr(SECRET),
    )
    response = client.delete(OPENAI_KEY_PATH)
    assert response.status_code == 404
    assert response.json()["error"]["code"] == ErrorCode.NOT_FOUND.value


def test_another_organizations_credential_is_404_on_verify(
    client: TestClient,
    vault: CredentialVault,
    organization_b: Organization,
    user: User,
) -> None:
    vault.store(
        principal=make_principal(organization_b, user, Role.SUPER_ADMIN),
        provider=CredentialProvider.OPENAI,
        field=CredentialField.API_KEY,
        secret=SecretStr(SECRET),
    )
    assert client.post("/api/credentials/OPENAI/verify").status_code == 404


def test_another_organizations_credential_is_invisible_in_the_list(
    client: TestClient,
    vault: CredentialVault,
    organization_b: Organization,
    user: User,
) -> None:
    other = make_principal(organization_b, user, Role.SUPER_ADMIN)
    stored = vault.store(
        principal=other,
        provider=CredentialProvider.OPENAI,
        field=CredentialField.API_KEY,
        secret=SecretStr(SECRET),
    )
    response = client.get("/api/credentials")
    assert response.status_code == 200
    assert stored.fingerprint not in response.text
    assert_no_secret(response)


def test_each_organization_sees_only_its_own_credential(
    app: FastAPI,
    client: TestClient,
    vault: CredentialVault,
    organization_a: Organization,
    organization_b: Organization,
    user: User,
) -> None:
    _store(client)
    mine = client.get("/api/credentials").text

    app.dependency_overrides[get_principal] = lambda: make_principal(
        organization_b, user, Role.SUPER_ADMIN
    )
    theirs = client.get("/api/credentials").text
    assert mine != theirs
    assert SECRET not in mine + theirs


# --------------------------------------------------------------------------- #
# Structural guarantees
# --------------------------------------------------------------------------- #


def test_the_router_defines_no_read_the_secret_endpoint() -> None:
    source = (
        Path(__file__).resolve().parents[2] / "src" / "veo" / "credentials" / "router.py"
    ).read_text(encoding="utf-8")
    for forbidden in ("get_secret_value", "resolve_for_use", "decrypt"):
        assert forbidden not in source


def test_the_router_is_mounted_and_still_exposes_no_secret_route() -> None:
    """The integrator has mounted this router; it must stay write-only there too.

    This assertion was inverted at integration: while the vault was being written it
    checked the router was *not* mounted, because mounting was the integrator's call.
    Now that it is mounted, the invariant worth holding is that the assembled
    application exposes the state and management routes and nothing that reads a
    secret back.
    """
    from veo.api.app import create_app

    paths = create_app().openapi()["paths"]
    credential_paths = [p for p in paths if p.startswith("/api/credentials")]
    assert credential_paths, "the credential vault is unreachable"

    for path in credential_paths:
        assert "secret" not in path
        for method, operation in paths[path].items():
            if method != "get":
                continue
            responses = operation.get("responses", {})
            assert "secret" not in str(responses).lower().replace("secret_key", ""), (
                f"GET {path} looks like it could return a secret"
            )


def test_no_endpoint_accepts_a_response_shape_that_could_carry_a_secret(
    app: FastAPI,
) -> None:
    schema = app.openapi()
    definitions = schema["components"]["schemas"]
    for name in ("CredentialFieldState", "ProviderCredentialState"):
        properties = definitions[name]["properties"]
        assert "secret" not in properties
        assert definitions[name].get("additionalProperties") is False
