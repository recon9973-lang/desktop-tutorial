"""The vault: store, describe, rotate, deactivate — and the one internal read path."""

from __future__ import annotations

import uuid
from pathlib import Path

import pytest
from pydantic import SecretStr
from sqlalchemy import select
from sqlalchemy.orm import Session
from vaulthelpers import OTHER_SECRET, SECRET, make_principal, requires_database

from veo.authz import Principal
from veo.contracts.enums import ProviderState, Role
from veo.credentials.cipher import AES_GCM_ALGORITHM, MasterKey
from veo.credentials.providers import (
    PROVIDER_FIELDS,
    CredentialField,
    CredentialProvider,
    VerificationErrorCode,
)
from veo.credentials.vault import (
    CredentialNotFoundError,
    CredentialValidationError,
    CredentialVault,
)
from veo.db.models import Organization, ProviderCredential, User

pytestmark = [pytest.mark.requires_postgres, requires_database]


def _row(session: Session, principal: Principal) -> ProviderCredential:
    return session.execute(
        select(ProviderCredential).where(
            ProviderCredential.organization_id == principal.organization_id
        )
    ).scalars().one()


# --------------------------------------------------------------------------- #
# store
# --------------------------------------------------------------------------- #


def test_store_writes_ciphertext_and_never_the_plaintext(
    vault: CredentialVault, session: Session, principal: Principal
) -> None:
    vault.store(
        principal=principal,
        provider=CredentialProvider.OPENAI,
        field=CredentialField.API_KEY,
        secret=SecretStr(SECRET),
    )

    row = _row(session, principal)
    assert SECRET.encode() not in row.ciphertext
    assert row.algorithm == AES_GCM_ALGORITHM
    assert len(row.nonce) == 12
    assert row.key_version == 1
    assert row.is_active is True
    assert len(row.fingerprint) == 64
    assert row.display_hint == SECRET[-4:]
    assert row.created_by == principal.user_id

    # No column anywhere in the row carries the secret.
    dumped = {c.name: getattr(row, c.name) for c in row.__table__.columns}
    assert SECRET not in str(dumped)


def test_store_is_idempotent_per_provider_and_field(
    vault: CredentialVault, session: Session, principal: Principal
) -> None:
    first = vault.store(
        principal=principal,
        provider=CredentialProvider.OPENAI,
        field=CredentialField.API_KEY,
        secret=SecretStr(SECRET),
    )
    second = vault.store(
        principal=principal,
        provider=CredentialProvider.OPENAI,
        field=CredentialField.API_KEY,
        secret=SecretStr(OTHER_SECRET),
    )

    rows = session.execute(
        select(ProviderCredential).where(
            ProviderCredential.organization_id == principal.organization_id
        )
    ).scalars().all()
    assert len(rows) == 1
    assert first.fingerprint != second.fingerprint
    assert rows[0].rotated_at is not None


def test_store_rejects_an_empty_secret(
    vault: CredentialVault, principal: Principal
) -> None:
    with pytest.raises(CredentialValidationError):
        vault.store(
            principal=principal,
            provider=CredentialProvider.OPENAI,
            field=CredentialField.API_KEY,
            secret=SecretStr("   "),
        )


def test_store_rejects_an_absurdly_large_secret(
    vault: CredentialVault, principal: Principal
) -> None:
    with pytest.raises(CredentialValidationError):
        vault.store(
            principal=principal,
            provider=CredentialProvider.OPENAI,
            field=CredentialField.API_KEY,
            secret=SecretStr("x" * 100_000),
        )


def test_every_provider_declares_at_least_one_field() -> None:
    """An empty field set would make a provider report ENABLED with nothing stored."""
    assert set(PROVIDER_FIELDS) == set(CredentialProvider)
    assert all(fields for fields in PROVIDER_FIELDS.values())


def test_store_rejects_a_field_the_provider_does_not_use(
    vault: CredentialVault, principal: Principal
) -> None:
    with pytest.raises(CredentialValidationError):
        vault.store(
            principal=principal,
            provider=CredentialProvider.OPENAI,
            field=CredentialField.CUSTOMER_ID,
            secret=SecretStr(SECRET),
        )


def test_a_short_secret_gets_no_display_hint(
    vault: CredentialVault, session: Session, principal: Principal
) -> None:
    vault.store(
        principal=principal,
        provider=CredentialProvider.OPENAI,
        field=CredentialField.API_KEY,
        secret=SecretStr("abc123"),
    )
    assert _row(session, principal).display_hint is None


# --------------------------------------------------------------------------- #
# describe
# --------------------------------------------------------------------------- #


def test_describe_reports_state_only(
    vault: CredentialVault, principal: Principal
) -> None:
    vault.store(
        principal=principal,
        provider=CredentialProvider.OPENAI,
        field=CredentialField.API_KEY,
        secret=SecretStr(SECRET),
    )
    described = vault.describe(principal=principal)

    openai = next(block for block in described if block.provider is CredentialProvider.OPENAI)
    assert openai.state is ProviderState.ENABLED
    assert openai.fields[0].is_configured is True
    assert SECRET not in repr(described)


def test_describe_lists_unconfigured_providers_as_disabled(
    vault: CredentialVault, principal: Principal
) -> None:
    described = vault.describe(principal=principal)
    assert described
    assert all(block.state is ProviderState.DISABLED_NO_CREDENTIAL for block in described)
    assert all(
        field.is_configured is False for block in described for field in block.fields
    )


def test_a_provider_needing_several_fields_stays_disabled_until_all_are_present(
    vault: CredentialVault, principal: Principal
) -> None:
    vault.store(
        principal=principal,
        provider=CredentialProvider.NAVER_SEARCH_AD,
        field=CredentialField.API_KEY,
        secret=SecretStr(SECRET),
    )
    block = vault.describe_provider(
        principal=principal, provider=CredentialProvider.NAVER_SEARCH_AD
    )
    assert block.state is ProviderState.DISABLED_NO_CREDENTIAL

    for field in (CredentialField.SECRET_KEY, CredentialField.CUSTOMER_ID):
        vault.store(
            principal=principal,
            provider=CredentialProvider.NAVER_SEARCH_AD,
            field=field,
            secret=SecretStr(SECRET),
        )
    block = vault.describe_provider(
        principal=principal, provider=CredentialProvider.NAVER_SEARCH_AD
    )
    assert block.state is ProviderState.ENABLED


def test_describe_never_crosses_the_tenant_boundary(
    vault: CredentialVault,
    principal: Principal,
    organization_b: Organization,
    user: User,
) -> None:
    other = make_principal(organization_b, user, Role.SUPER_ADMIN)
    vault.store(
        principal=other,
        provider=CredentialProvider.OPENAI,
        field=CredentialField.API_KEY,
        secret=SecretStr(SECRET),
    )

    mine = vault.describe_provider(principal=principal, provider=CredentialProvider.OPENAI)
    assert mine.state is ProviderState.DISABLED_NO_CREDENTIAL
    assert mine.fields[0].fingerprint is None


# --------------------------------------------------------------------------- #
# resolve_for_use — the only decrypt path
# --------------------------------------------------------------------------- #


def test_resolve_for_use_returns_the_plaintext_as_a_secret(
    vault: CredentialVault, principal: Principal
) -> None:
    vault.store(
        principal=principal,
        provider=CredentialProvider.OPENAI,
        field=CredentialField.API_KEY,
        secret=SecretStr(SECRET),
    )
    resolved = vault.resolve_for_use(
        organization_id=principal.organization_id,
        provider=CredentialProvider.OPENAI,
        field=CredentialField.API_KEY,
    )
    assert isinstance(resolved, SecretStr)
    assert resolved.get_secret_value() == SECRET
    assert SECRET not in repr(resolved)
    assert SECRET not in str(resolved)


def test_resolve_for_use_refuses_another_organization(
    vault: CredentialVault, principal: Principal, organization_b: Organization
) -> None:
    vault.store(
        principal=principal,
        provider=CredentialProvider.OPENAI,
        field=CredentialField.API_KEY,
        secret=SecretStr(SECRET),
    )
    with pytest.raises(CredentialNotFoundError):
        vault.resolve_for_use(
            organization_id=organization_b.id,
            provider=CredentialProvider.OPENAI,
            field=CredentialField.API_KEY,
        )


def test_resolve_for_use_refuses_a_deactivated_credential(
    vault: CredentialVault, principal: Principal
) -> None:
    vault.store(
        principal=principal,
        provider=CredentialProvider.OPENAI,
        field=CredentialField.API_KEY,
        secret=SecretStr(SECRET),
    )
    vault.deactivate(
        principal=principal,
        provider=CredentialProvider.OPENAI,
        field=CredentialField.API_KEY,
    )
    with pytest.raises(CredentialNotFoundError):
        vault.resolve_for_use(
            organization_id=principal.organization_id,
            provider=CredentialProvider.OPENAI,
            field=CredentialField.API_KEY,
        )


def test_no_router_may_call_resolve_for_use() -> None:
    router_source = (
        Path(__file__).resolve().parents[2]
        / "src"
        / "veo"
        / "credentials"
        / "router.py"
    ).read_text(encoding="utf-8")
    assert "resolve_for_use" not in router_source


# --------------------------------------------------------------------------- #
# deactivate
# --------------------------------------------------------------------------- #


def test_deactivate_destroys_the_key_material_but_keeps_the_audit_trail(
    vault: CredentialVault, session: Session, principal: Principal
) -> None:
    stored = vault.store(
        principal=principal,
        provider=CredentialProvider.OPENAI,
        field=CredentialField.API_KEY,
        secret=SecretStr(SECRET),
    )
    state = vault.deactivate(
        principal=principal,
        provider=CredentialProvider.OPENAI,
        field=CredentialField.API_KEY,
    )
    assert state.is_configured is False

    row = _row(session, principal)
    assert row.is_active is False
    assert row.ciphertext == b""
    assert row.nonce == b""
    assert row.fingerprint == stored.fingerprint


def test_deactivate_on_a_missing_credential_raises_not_found(
    vault: CredentialVault, principal: Principal
) -> None:
    with pytest.raises(CredentialNotFoundError):
        vault.deactivate(
            principal=principal,
            provider=CredentialProvider.OPENAI,
            field=CredentialField.API_KEY,
        )


def test_deactivate_cannot_reach_another_organization(
    vault: CredentialVault,
    principal: Principal,
    organization_b: Organization,
    user: User,
) -> None:
    other = make_principal(organization_b, user, Role.SUPER_ADMIN)
    vault.store(
        principal=other,
        provider=CredentialProvider.OPENAI,
        field=CredentialField.API_KEY,
        secret=SecretStr(SECRET),
    )
    with pytest.raises(CredentialNotFoundError):
        vault.deactivate(
            principal=principal,
            provider=CredentialProvider.OPENAI,
            field=CredentialField.API_KEY,
        )


def test_storing_again_after_deactivation_reactivates(
    vault: CredentialVault, principal: Principal
) -> None:
    vault.store(
        principal=principal,
        provider=CredentialProvider.OPENAI,
        field=CredentialField.API_KEY,
        secret=SecretStr(SECRET),
    )
    vault.deactivate(
        principal=principal,
        provider=CredentialProvider.OPENAI,
        field=CredentialField.API_KEY,
    )
    vault.store(
        principal=principal,
        provider=CredentialProvider.OPENAI,
        field=CredentialField.API_KEY,
        secret=SecretStr(OTHER_SECRET),
    )
    assert (
        vault.resolve_for_use(
            organization_id=principal.organization_id,
            provider=CredentialProvider.OPENAI,
            field=CredentialField.API_KEY,
        ).get_secret_value()
        == OTHER_SECRET
    )


# --------------------------------------------------------------------------- #
# rotation
# --------------------------------------------------------------------------- #


def test_rotation_preserves_the_plaintext_and_bumps_the_key_version(
    vault: CredentialVault,
    session: Session,
    principal: Principal,
    next_master_key: MasterKey,
) -> None:
    stored = vault.store(
        principal=principal,
        provider=CredentialProvider.OPENAI,
        field=CredentialField.API_KEY,
        secret=SecretStr(SECRET),
    )
    before = _row(session, principal)
    old_ciphertext, old_nonce = before.ciphertext, before.nonce

    report = vault.rotate_key(principal=principal, new_key=next_master_key)
    assert report.rotated_count == 1
    assert report.key_version == 2

    after = _row(session, principal)
    assert after.key_version == 2
    assert after.ciphertext != old_ciphertext
    assert after.nonce != old_nonce
    assert after.rotated_at is not None
    # The fingerprint key is derived from the master key, so it rotates too. A rotation
    # is recognisable because every fingerprint in the organization moves at once and
    # rotated_at moves with it; a single fingerprint changing on its own still means
    # somebody replaced that credential.
    assert after.fingerprint != stored.fingerprint

    assert (
        vault.resolve_for_use(
            organization_id=principal.organization_id,
            provider=CredentialProvider.OPENAI,
            field=CredentialField.API_KEY,
        ).get_secret_value()
        == SECRET
    )


def test_after_rotation_the_fingerprint_still_identifies_the_value(
    vault: CredentialVault,
    session: Session,
    principal: Principal,
    next_master_key: MasterKey,
) -> None:
    """Post-rotation, an unchanged credential must still fingerprint identically."""
    vault.store(
        principal=principal,
        provider=CredentialProvider.OPENAI,
        field=CredentialField.API_KEY,
        secret=SecretStr(SECRET),
    )
    vault.rotate_key(principal=principal, new_key=next_master_key)
    rotated = _row(session, principal).fingerprint

    same = vault.store(
        principal=principal,
        provider=CredentialProvider.OPENAI,
        field=CredentialField.API_KEY,
        secret=SecretStr(SECRET),
    )
    assert same.fingerprint == rotated

    changed = vault.store(
        principal=principal,
        provider=CredentialProvider.OPENAI,
        field=CredentialField.API_KEY,
        secret=SecretStr(OTHER_SECRET),
    )
    assert changed.fingerprint != rotated


def test_rotation_skips_deactivated_rows(
    vault: CredentialVault, principal: Principal, next_master_key: MasterKey
) -> None:
    vault.store(
        principal=principal,
        provider=CredentialProvider.OPENAI,
        field=CredentialField.API_KEY,
        secret=SecretStr(SECRET),
    )
    vault.deactivate(
        principal=principal,
        provider=CredentialProvider.OPENAI,
        field=CredentialField.API_KEY,
    )
    report = vault.rotate_key(principal=principal, new_key=next_master_key)
    assert report.rotated_count == 0
    assert report.skipped_count == 1


def test_rotation_refuses_to_go_backwards(
    vault: CredentialVault, principal: Principal, master_key: MasterKey
) -> None:
    with pytest.raises(CredentialValidationError):
        vault.rotate_key(principal=principal, new_key=master_key)


def test_rotation_does_not_touch_another_organization(
    vault: CredentialVault,
    session: Session,
    principal: Principal,
    organization_b: Organization,
    user: User,
    next_master_key: MasterKey,
) -> None:
    other = make_principal(organization_b, user, Role.SUPER_ADMIN)
    vault.store(
        principal=other,
        provider=CredentialProvider.OPENAI,
        field=CredentialField.API_KEY,
        secret=SecretStr(SECRET),
    )
    vault.store(
        principal=principal,
        provider=CredentialProvider.OPENAI,
        field=CredentialField.API_KEY,
        secret=SecretStr(SECRET),
    )

    report = vault.rotate_key(principal=principal, new_key=next_master_key)
    assert report.rotated_count == 1

    untouched = session.execute(
        select(ProviderCredential).where(
            ProviderCredential.organization_id == organization_b.id
        )
    ).scalars().one()
    assert untouched.key_version == 1


def test_a_row_written_under_an_unknown_key_version_cannot_be_read(
    vault: CredentialVault, session: Session, principal: Principal
) -> None:
    vault.store(
        principal=principal,
        provider=CredentialProvider.OPENAI,
        field=CredentialField.API_KEY,
        secret=SecretStr(SECRET),
    )
    row = _row(session, principal)
    row.key_version = 99
    session.commit()

    with pytest.raises(CredentialNotFoundError):
        vault.resolve_for_use(
            organization_id=principal.organization_id,
            provider=CredentialProvider.OPENAI,
            field=CredentialField.API_KEY,
        )


# --------------------------------------------------------------------------- #
# verification
# --------------------------------------------------------------------------- #


def test_verification_records_only_a_machine_code(
    vault: CredentialVault, session: Session, principal: Principal
) -> None:
    result = vault.verify(principal=principal, provider=CredentialProvider.OPENAI)
    assert result.error_code is VerificationErrorCode.MISSING_FIELDS

    vault.store(
        principal=principal,
        provider=CredentialProvider.OPENAI,
        field=CredentialField.API_KEY,
        secret=SecretStr(SECRET),
    )
    result = vault.verify(principal=principal, provider=CredentialProvider.OPENAI)
    assert result.error_code is None

    row = _row(session, principal)
    assert row.last_verified_at is not None
    assert row.last_verification_error_code is None


def test_verification_failure_never_stores_provider_text(
    vault: CredentialVault, session: Session, principal: Principal
) -> None:
    class _ChattyVerifier:
        def verify(self, provider: CredentialProvider, credentials: object) -> None:
            raise RuntimeError(f"401 Unauthorized: key {SECRET} is invalid")

    vault.store(
        principal=principal,
        provider=CredentialProvider.OPENAI,
        field=CredentialField.API_KEY,
        secret=SecretStr(SECRET),
    )
    result = vault.verify(
        principal=principal, provider=CredentialProvider.OPENAI, verifier=_ChattyVerifier()
    )
    assert result.error_code is VerificationErrorCode.UNKNOWN

    row = _row(session, principal)
    assert row.last_verification_error_code == VerificationErrorCode.UNKNOWN.value
    assert SECRET not in str(row.last_verification_error_code)
    assert len(row.last_verification_error_code or "") <= 48
    assert SECRET not in repr(result)


def test_verification_detects_a_row_that_no_longer_decrypts(
    vault: CredentialVault, session: Session, principal: Principal
) -> None:
    vault.store(
        principal=principal,
        provider=CredentialProvider.OPENAI,
        field=CredentialField.API_KEY,
        secret=SecretStr(SECRET),
    )
    row = _row(session, principal)
    row.ciphertext = bytes(len(row.ciphertext))
    session.commit()

    result = vault.verify(principal=principal, provider=CredentialProvider.OPENAI)
    assert result.error_code is VerificationErrorCode.DECRYPT_FAILED


def test_verification_is_tenant_scoped(
    vault: CredentialVault,
    principal: Principal,
    organization_b: Organization,
    user: User,
) -> None:
    other = make_principal(organization_b, user, Role.SUPER_ADMIN)
    vault.store(
        principal=other,
        provider=CredentialProvider.OPENAI,
        field=CredentialField.API_KEY,
        secret=SecretStr(SECRET),
    )
    result = vault.verify(principal=principal, provider=CredentialProvider.OPENAI)
    assert result.error_code is VerificationErrorCode.MISSING_FIELDS


# --------------------------------------------------------------------------- #
# repr safety
# --------------------------------------------------------------------------- #


def test_model_repr_does_not_leak(
    vault: CredentialVault, session: Session, principal: Principal
) -> None:
    vault.store(
        principal=principal,
        provider=CredentialProvider.OPENAI,
        field=CredentialField.API_KEY,
        secret=SecretStr(SECRET),
    )
    row = _row(session, principal)
    rendered = f"{row!r} {row!s}"
    assert SECRET not in rendered
    assert row.ciphertext.hex() not in rendered
    assert "REDACTED" in rendered


def test_vault_repr_does_not_leak(vault: CredentialVault, master_key: MasterKey) -> None:
    rendered = repr(vault)
    assert master_key.aes_key.hex() not in rendered
    assert master_key.fingerprint_key.hex() not in rendered


def test_the_model_has_no_plaintext_column() -> None:
    names = set(ProviderCredential.__table__.columns.keys())
    assert not names & {"plaintext", "secret", "value", "raw", "decrypted"}


def test_an_unknown_organization_is_simply_not_found(vault: CredentialVault) -> None:
    with pytest.raises(CredentialNotFoundError):
        vault.resolve_for_use(
            organization_id=uuid.uuid4(),
            provider=CredentialProvider.OPENAI,
            field=CredentialField.API_KEY,
        )
