"""Provider-credential vault.

One rule shapes every file in this package: **a provider secret goes in and is used; it
never comes back out.** There is no read-the-secret endpoint, no decrypt-and-return
service method exposed to a router, and no permission in the matrix that would allow
one. The most anyone can ever learn is which provider, which field, whether it is
configured, when it was set, a non-reversible fingerprint, and a short display hint.

Layout:

* ``cipher`` — AES-256-GCM, master-key loading and the startup guard.
* ``vault`` — store, describe, rotate, deactivate, verify, and the single internal
  decrypt path used by outbound provider clients.
* ``providers`` — which sources take credentials and what their fields are called.
* ``schemas`` / ``router`` — the HTTP surface. The router is not mounted here; see
  ``INTEGRATION_REQUEST.md``.
* ``redaction`` — scrubbing secrets out of anything bound for a log or an error.

``resolve_for_use`` is intentionally absent from these exports. It is a method on the
vault, reached deliberately by a provider client, not a package-level utility.
"""

from veo.credentials.cipher import (
    AES_GCM_ALGORITHM,
    CipherBackend,
    CipherConfigurationError,
    CredentialCryptoError,
    DecryptionError,
    MasterKey,
    assert_cipher_backend_allowed,
    assert_vault_startup_ready,
    load_master_key,
    select_cipher_backend,
)
from veo.credentials.providers import (
    CREDENTIAL_PROVIDERS,
    PROVIDER_FIELDS,
    CredentialField,
    CredentialProvider,
    VerificationErrorCode,
    fields_for,
    is_credential_provider,
)
from veo.credentials.redaction import redact, redact_exception, redact_mapping
from veo.credentials.vault import (
    CredentialFieldState,
    CredentialNotFoundError,
    CredentialValidationError,
    CredentialVault,
    CredentialVaultError,
    CredentialVerifier,
    LocalIntegrityVerifier,
    ProviderCredentialState,
    RotationReport,
    VerificationResult,
)

__all__ = [
    "AES_GCM_ALGORITHM",
    "CREDENTIAL_PROVIDERS",
    "PROVIDER_FIELDS",
    "CipherBackend",
    "CipherConfigurationError",
    "CredentialCryptoError",
    "CredentialField",
    "CredentialFieldState",
    "CredentialNotFoundError",
    "CredentialProvider",
    "CredentialValidationError",
    "CredentialVault",
    "CredentialVaultError",
    "CredentialVerifier",
    "DecryptionError",
    "LocalIntegrityVerifier",
    "MasterKey",
    "ProviderCredentialState",
    "RotationReport",
    "VerificationErrorCode",
    "VerificationResult",
    "assert_cipher_backend_allowed",
    "assert_vault_startup_ready",
    "fields_for",
    "is_credential_provider",
    "load_master_key",
    "redact",
    "redact_exception",
    "redact_mapping",
    "select_cipher_backend",
]
