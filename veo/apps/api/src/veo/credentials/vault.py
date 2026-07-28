"""The credential vault: the only code in VEO that touches a provider secret.

The whole design follows from one rule: **a provider secret goes in and is used; it never
comes back out.**

* :meth:`CredentialVault.store` is the only way in.
* :meth:`CredentialVault.describe` is the only thing a router may show, and it returns
  state — configured or not, a fingerprint, a four-character hint, some timestamps.
* :meth:`CredentialVault.resolve_for_use` is the only way a plaintext is ever produced,
  and it exists for outbound provider calls made by a worker. No HTTP handler calls it.
  There is no permission that would make calling it legitimate, and a test asserts that
  the name does not appear in ``router.py``.

Tenancy is not left to reviewer discipline. Every query is built with ``tenant_select``
and checked with ``assert_tenant_scoped`` before it executes, and a row belonging to
another organization is reported as *not found* — never as forbidden, which would confirm
it exists.
"""

from __future__ import annotations

import logging
import uuid
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Protocol

from pydantic import SecretStr
from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from veo.authz import Principal, assert_tenant_scoped, tenant_select
from veo.contracts.enums import ProviderState
from veo.credentials.cipher import (
    AES_GCM_ALGORITHM,
    CipherBackend,
    CredentialCryptoError,
    MasterKey,
    build_associated_data,
    build_fingerprint_context,
    select_cipher_backend,
)
from veo.credentials.providers import (
    CREDENTIAL_PROVIDERS,
    CredentialField,
    CredentialProvider,
    VerificationErrorCode,
    fields_for,
)
from veo.credentials.redaction import redact_exception
from veo.db.models import ProviderCredential

__all__ = [
    "MAX_SECRET_BYTES",
    "CredentialFieldState",
    "CredentialNotFoundError",
    "CredentialShape",
    "CredentialValidationError",
    "CredentialVault",
    "CredentialVaultError",
    "CredentialVerifier",
    "LocalIntegrityVerifier",
    "ProviderCredentialState",
    "RotationReport",
    "VerificationResult",
]

_log = logging.getLogger("veo.credentials")

#: Generous enough for a Google service-account JSON, small enough that a mistaken
#: file upload is rejected rather than encrypted and stored forever.
MAX_SECRET_BYTES = 16_384

#: Below this length, the last four characters give away too much of the secret.
_MIN_LENGTH_FOR_HINT = 12
_HINT_LENGTH = 4


class CredentialVaultError(Exception):
    """Base class for vault failures."""


class CredentialNotFoundError(CredentialVaultError):
    """No usable credential exists for this organization, provider and field.

    Raised identically for "there is no such row", "the row belongs to someone else" and
    "the row is deactivated". A caller cannot tell those apart, which is the point:
    distinguishing them would confirm another tenant's configuration.
    """


class CredentialValidationError(CredentialVaultError):
    """The request itself is not acceptable — wrong field, empty or oversized secret."""


# --------------------------------------------------------------------------- #
# State — everything a caller outside this module is allowed to see
# --------------------------------------------------------------------------- #


@dataclass(frozen=True, slots=True)
class CredentialFieldState:
    """One field's state. There is no attribute here that could hold a secret."""

    field: CredentialField
    is_configured: bool
    fingerprint: str | None = None
    display_hint: str | None = None
    algorithm: str | None = None
    key_version: int | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    rotated_at: datetime | None = None
    last_verified_at: datetime | None = None
    last_verification_error_code: VerificationErrorCode | None = None


@dataclass(frozen=True, slots=True)
class ProviderCredentialState:
    """One provider's state, following the same vocabulary as ``GET /api/providers``."""

    provider: CredentialProvider
    state: ProviderState
    fields: tuple[CredentialFieldState, ...]


@dataclass(frozen=True, slots=True)
class RotationReport:
    """The outcome of a key rotation. Counts only — never a row's contents."""

    key_version: int
    rotated_count: int
    skipped_count: int


@dataclass(frozen=True, slots=True)
class VerificationResult:
    """The outcome of a verification. ``error_code`` is a closed machine vocabulary."""

    provider: ProviderCredentialState
    verified: bool
    error_code: VerificationErrorCode | None
    checked_at: datetime


# --------------------------------------------------------------------------- #
# Verification
# --------------------------------------------------------------------------- #

#: What a verifier receives: the provider's complete credential set, still wrapped.
type CredentialShape = Mapping[CredentialField, SecretStr]


class CredentialVerifier(Protocol):
    """Checks a credential set against the provider.

    An implementation may raise anything at all; the vault collapses whatever comes back
    into a :class:`VerificationErrorCode` and redacts the detail before it is logged. It
    must never return the provider's error text, because that text frequently contains
    the credential.
    """

    def verify(
        self, provider: CredentialProvider, credentials: CredentialShape
    ) -> VerificationErrorCode | None: ...


class LocalIntegrityVerifier:
    """The default verifier: checks what VEO can check without calling anyone.

    Reaching this class already proves the useful part — every required field is present,
    active, and decrypts under the current master key. It deliberately does **not** claim
    the provider would accept the credential; a live verifier is registered by whoever
    owns that provider's client, through :class:`CredentialVerifier`.
    """

    def verify(
        self, provider: CredentialProvider, credentials: CredentialShape
    ) -> VerificationErrorCode | None:
        missing = [
            field for field in fields_for(provider)
            if not credentials.get(field, SecretStr("")).get_secret_value()
        ]
        return VerificationErrorCode.MISSING_FIELDS if missing else None


# --------------------------------------------------------------------------- #
# The vault
# --------------------------------------------------------------------------- #


class CredentialVault:
    """Stores, describes, rotates and deactivates provider credentials."""

    def __init__(
        self,
        session: Session,
        *,
        master_key: MasterKey,
        previous_keys: Sequence[MasterKey] = (),
        backend: CipherBackend | None = None,
    ) -> None:
        self._session = session
        self._backend = backend if backend is not None else select_cipher_backend()
        self._current = master_key
        # Rows written before a rotation still carry the older version. Keeping the
        # retired keys here is what lets rotate_key() read them; nothing else uses them.
        self._keys: dict[int, MasterKey] = {key.version: key for key in previous_keys}
        self._keys[master_key.version] = master_key

    def __repr__(self) -> str:
        return (
            f"<CredentialVault key_version={self._current.version} "
            f"backend={self._backend.name} REDACTED>"
        )

    # ----------------------------------------------------------------- write

    def store(
        self,
        *,
        principal: Principal,
        provider: CredentialProvider,
        field: CredentialField,
        secret: SecretStr,
    ) -> CredentialFieldState:
        """Encrypt a secret into the caller's organization. The only way in.

        Storing over an existing value replaces it: there is no history table of former
        credentials, because a retired secret that is still readable is still a secret
        someone can steal.
        """
        self._assert_field_belongs_to_provider(provider, field)
        plaintext = self._normalise(secret)

        row = self._session.execute(
            self._scoped(principal.organization_id, provider, field),
        ).scalar_one_or_none()

        key = self._current
        nonce = self._backend.random_nonce()
        ciphertext = self._backend.encrypt(
            key=key.aes_key,
            nonce=nonce,
            plaintext=plaintext,
            associated_data=build_associated_data(
                principal.organization_id, provider.value, field.value, key.version
            ),
        )
        fingerprint = key.fingerprint(
            plaintext,
            context=build_fingerprint_context(
                principal.organization_id, provider.value, field.value
            ),
        )
        hint = self._display_hint(plaintext)
        del plaintext

        now = datetime.now(UTC)
        if row is None:
            row = ProviderCredential(
                organization_id=principal.organization_id,
                provider=provider.value,
                field=field.value,
                metadata_json={},
                created_by=principal.user_id,
            )
            self._session.add(row)
        else:
            row.rotated_at = now

        row.ciphertext = ciphertext
        row.nonce = nonce
        row.algorithm = AES_GCM_ALGORITHM
        row.key_version = key.version
        row.fingerprint = fingerprint
        row.display_hint = hint
        row.is_active = True
        # A replaced credential has not been verified yet; leaving the previous result
        # in place would show a green tick for a value nobody has checked.
        row.last_verified_at = None
        row.last_verification_error_code = None

        self._session.commit()
        self._session.refresh(row)
        return self._field_state(field, row)

    def deactivate(
        self,
        *,
        principal: Principal,
        provider: CredentialProvider,
        field: CredentialField,
    ) -> CredentialFieldState:
        """Retire a credential and destroy its key material.

        The row survives so an operator can still see that something *was* configured,
        and the fingerprint survives with it, but the ciphertext and nonce are cleared.
        A deactivated credential is not recoverable — which is the correct behaviour for
        a delete, and the reason this is not a reversible flag flip.
        """
        self._assert_field_belongs_to_provider(provider, field)
        row = self._session.execute(
            self._scoped(principal.organization_id, provider, field)
        ).scalar_one_or_none()
        if row is None or not row.is_active:
            raise CredentialNotFoundError("credential not found")

        row.ciphertext = b""
        row.nonce = b""
        row.is_active = False
        row.rotated_at = datetime.now(UTC)
        row.last_verified_at = None
        row.last_verification_error_code = None

        self._session.commit()
        self._session.refresh(row)
        return self._field_state(field, row)

    def rotate_key(
        self, *, principal: Principal, new_key: MasterKey
    ) -> RotationReport:
        """Re-encrypt this organization's active credentials under a new master key.

        Each row is decrypted with whichever key version wrote it and re-encrypted under
        ``new_key`` with a fresh nonce, in place. The plaintext exists only as a local
        name inside the loop and is dropped immediately; it is never written to a column,
        a log line, or a temporary row.

        Fingerprints are recomputed under the new key's derived fingerprint key, so they
        change too. That is the point: if the old master key leaked, its fingerprint key
        leaked with it, and keeping the old fingerprints would keep the door open to an
        offline guess against a short credential. The cost is that a rotation looks like
        a change — which is distinguishable, because a rotation moves *every* fingerprint
        in the organization at once and stamps ``rotated_at`` on the same rows, while a
        replaced credential moves exactly one.

        CPython cannot guarantee that the freed plaintext is erased from process memory.
        That is a limitation of the runtime, not something this method papers over.
        """
        if new_key.version <= self._current.version:
            raise CredentialValidationError(
                "a rotation must move to a strictly higher key_version"
            )

        statement = tenant_select(ProviderCredential, principal)
        assert_tenant_scoped(statement, principal.organization_id)
        rows = list(self._session.execute(statement).scalars().all())

        rotated = 0
        skipped = 0
        for row in rows:
            if not row.is_active or not row.ciphertext:
                skipped += 1
                continue
            source_key = self._keys.get(row.key_version)
            if source_key is None:
                skipped += 1
                _log.error(
                    "credential.rotate.unknown_key_version",
                    extra={"key_version": row.key_version},
                )
                continue

            plaintext = self._decrypt_row(row, source_key)
            try:
                nonce = self._backend.random_nonce()
                row.ciphertext = self._backend.encrypt(
                    key=new_key.aes_key,
                    nonce=nonce,
                    plaintext=plaintext,
                    associated_data=build_associated_data(
                        row.organization_id, row.provider, row.field, new_key.version
                    ),
                )
                row.nonce = nonce
                row.key_version = new_key.version
                row.algorithm = AES_GCM_ALGORITHM
                row.fingerprint = new_key.fingerprint(
                    plaintext,
                    context=build_fingerprint_context(
                        row.organization_id, row.provider, row.field
                    ),
                )
                row.rotated_at = datetime.now(UTC)
            finally:
                del plaintext
            rotated += 1

        self._session.commit()
        self._keys[new_key.version] = new_key
        self._current = new_key
        return RotationReport(
            key_version=new_key.version, rotated_count=rotated, skipped_count=skipped
        )

    # ------------------------------------------------------------------ read

    def describe(self, *, principal: Principal) -> tuple[ProviderCredentialState, ...]:
        """State for every provider that takes credentials. Never a secret.

        Providers with nothing stored are listed too, so the console shows the whole
        matrix rather than only what happens to exist — the same honesty principle as
        ``GET /api/providers``, which reports a disabled provider instead of hiding it.
        """
        rows = self._all_rows(principal)
        return tuple(
            self._provider_state(provider, rows)
            for provider in sorted(CREDENTIAL_PROVIDERS, key=lambda item: item.value)
        )

    def describe_provider(
        self, *, principal: Principal, provider: CredentialProvider
    ) -> ProviderCredentialState:
        self._assert_is_credential_provider(provider)
        return self._provider_state(provider, self._all_rows(principal))

    def verify(
        self,
        *,
        principal: Principal,
        provider: CredentialProvider,
        verifier: CredentialVerifier | None = None,
    ) -> VerificationResult:
        """Check a provider's stored credential set and record the outcome.

        Only the machine code is persisted. Whatever the verifier raised is redacted and
        logged, never stored and never returned — provider errors quote the credential.
        """
        self._assert_is_credential_provider(provider)
        rows = {
            row.field: row
            for row in self._all_rows(principal)
            if row.provider == provider.value
        }

        credentials: dict[CredentialField, SecretStr] = {}
        error_code: VerificationErrorCode | None = None
        plaintexts: list[str] = []

        for field in fields_for(provider):
            row = rows.get(field.value)
            if row is None or not row.is_active or not row.ciphertext:
                error_code = VerificationErrorCode.MISSING_FIELDS
                continue
            key = self._keys.get(row.key_version)
            if key is None:
                error_code = error_code or VerificationErrorCode.DECRYPT_FAILED
                continue
            try:
                value = self._decrypt_row(row, key).decode("utf-8")
            except (CredentialCryptoError, UnicodeDecodeError):
                error_code = error_code or VerificationErrorCode.DECRYPT_FAILED
                continue
            plaintexts.append(value)
            credentials[field] = SecretStr(value)

        if error_code is None:
            try:
                error_code = (verifier or LocalIntegrityVerifier()).verify(
                    provider, credentials
                )
            except Exception as exc:  # a verifier may raise anything at all
                error_code = VerificationErrorCode.UNKNOWN
                _log.warning(
                    "credential.verify.failed provider=%s detail=%s",
                    provider.value,
                    redact_exception(exc, known_values=plaintexts),
                )

        credentials.clear()
        plaintexts.clear()

        checked_at = datetime.now(UTC)
        for row in rows.values():
            if not row.is_active:
                continue
            row.last_verified_at = checked_at
            row.last_verification_error_code = error_code.value if error_code else None
        self._session.commit()

        return VerificationResult(
            provider=self._provider_state(provider, self._all_rows(principal)),
            verified=error_code is None,
            error_code=error_code,
            checked_at=checked_at,
        )

    # -------------------------------------------------------------- internal

    def resolve_for_use(
        self,
        *,
        organization_id: uuid.UUID,
        provider: CredentialProvider,
        field: CredentialField,
    ) -> SecretStr:
        """INTERNAL — decrypt a credential for one outbound call to ``provider``.

        **No HTTP router may call this method, now or later.** It is not a read endpoint
        with a permission attached; it is the seam between the vault and a provider
        client, and it exists solely so that an adapter can put the secret into an
        outbound request. There is no permission in the matrix that would authorise
        returning this value to a caller, and a test asserts that the string
        ``resolve_for_use`` does not appear in ``router.py``.

        The return type is :class:`~pydantic.SecretStr` so that the value cannot be
        logged, formatted into a message, or serialised into a response by accident —
        every one of those renders as ``**********``. Unwrap it as late as possible,
        directly into the outbound request, and never assign the unwrapped value to
        anything that outlives the call.
        """
        row = self._session.execute(
            self._scoped(organization_id, provider, field)
        ).scalar_one_or_none()
        if row is None or not row.is_active or not row.ciphertext:
            raise CredentialNotFoundError("credential not found")

        key = self._keys.get(row.key_version)
        if key is None:
            _log.error(
                "credential.resolve.unknown_key_version",
                extra={"key_version": row.key_version},
            )
            raise CredentialNotFoundError("credential not found")

        try:
            return SecretStr(self._decrypt_row(row, key).decode("utf-8"))
        except (CredentialCryptoError, UnicodeDecodeError) as exc:
            # Indistinguishable from "no such credential" on purpose: a caller learning
            # that a row exists but will not decrypt learns something about another
            # organization's data if the guard above ever regresses.
            raise CredentialNotFoundError("credential not found") from exc

    # --------------------------------------------------------------- helpers

    @staticmethod
    def _scoped(
        organization_id: uuid.UUID, provider: CredentialProvider, field: CredentialField
    ) -> Select[tuple[ProviderCredential]]:
        """One row, filtered to one organization and checked before it can execute.

        ``resolve_for_use`` runs in a worker that has an organization but no HTTP
        principal, so this path cannot use ``tenant_select``. Fabricating a Principal
        would invent roles nobody granted; instead the filter is written explicitly and
        ``assert_tenant_scoped`` — the actual structural guard — still refuses to let an
        unfiltered statement through.
        """
        statement = (
            select(ProviderCredential)
            .where(ProviderCredential.organization_id == organization_id)
            .where(ProviderCredential.provider == provider.value)
            .where(ProviderCredential.field == field.value)
        )
        assert_tenant_scoped(statement, organization_id)
        return statement

    def _all_rows(self, principal: Principal) -> list[ProviderCredential]:
        statement = tenant_select(ProviderCredential, principal)
        assert_tenant_scoped(statement, principal.organization_id)
        return list(self._session.execute(statement).scalars().all())

    def _decrypt_row(self, row: ProviderCredential, key: MasterKey) -> bytes:
        return self._backend.decrypt(
            key=key.aes_key,
            nonce=row.nonce,
            ciphertext=row.ciphertext,
            associated_data=build_associated_data(
                row.organization_id, row.provider, row.field, row.key_version
            ),
        )

    def _normalise(self, secret: SecretStr) -> bytes:
        """Validate the incoming value and encode it.

        Surrounding whitespace is stripped: a key pasted out of a console or a file
        arrives with a trailing newline far more often than a provider issues one that
        depends on it, and the alternative is an authentication failure nobody can see
        the cause of — because the value can never be read back to compare.
        """
        value = secret.get_secret_value().strip()
        if not value:
            raise CredentialValidationError("credential value must not be empty")
        plaintext = value.encode("utf-8")
        if len(plaintext) > MAX_SECRET_BYTES:
            raise CredentialValidationError(
                f"credential value must be at most {MAX_SECRET_BYTES} bytes"
            )
        return plaintext

    @staticmethod
    def _display_hint(plaintext: bytes) -> str | None:
        """The last four characters, and only when the secret is long enough.

        For anything short, four characters is a large fraction of the value, so no hint
        is better than a helpful one.
        """
        try:
            value = plaintext.decode("utf-8")
        except UnicodeDecodeError:
            return None
        if len(value) < _MIN_LENGTH_FOR_HINT:
            return None
        return value[-_HINT_LENGTH:]

    @staticmethod
    def _assert_is_credential_provider(provider: CredentialProvider) -> None:
        if provider not in CREDENTIAL_PROVIDERS:
            raise CredentialValidationError(
                f"{provider.value} does not take stored credentials"
            )

    @classmethod
    def _assert_field_belongs_to_provider(
        cls, provider: CredentialProvider, field: CredentialField
    ) -> None:
        cls._assert_is_credential_provider(provider)
        if field not in fields_for(provider):
            raise CredentialValidationError(
                f"{provider.value} does not use the field {field.value}"
            )

    @staticmethod
    def _field_state(
        field: CredentialField, row: ProviderCredential | None
    ) -> CredentialFieldState:
        if row is None:
            return CredentialFieldState(field=field, is_configured=False)
        configured = bool(row.is_active and row.ciphertext)
        return CredentialFieldState(
            field=field,
            is_configured=configured,
            fingerprint=row.fingerprint,
            display_hint=row.display_hint,
            algorithm=row.algorithm,
            key_version=row.key_version,
            created_at=row.created_at,
            updated_at=row.updated_at,
            rotated_at=row.rotated_at,
            last_verified_at=row.last_verified_at,
            last_verification_error_code=(
                VerificationErrorCode(row.last_verification_error_code)
                if row.last_verification_error_code
                else None
            ),
        )

    @classmethod
    def _provider_state(
        cls, provider: CredentialProvider, rows: Sequence[ProviderCredential]
    ) -> ProviderCredentialState:
        by_field = {row.field: row for row in rows if row.provider == provider.value}
        states = tuple(
            cls._field_state(field, by_field.get(field.value))
            for field in fields_for(provider)
        )
        complete = bool(states) and all(state.is_configured for state in states)
        return ProviderCredentialState(
            provider=provider,
            state=(
                ProviderState.ENABLED
                if complete
                else ProviderState.DISABLED_NO_CREDENTIAL
            ),
            fields=states,
        )
