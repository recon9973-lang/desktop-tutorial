# Integration requests — `veo.credentials`

Everything below is outside this worker's paths. The package is complete and tested
without any of it; each item is an improvement or a wiring step, and the first two are the
ones that actually matter.

---

## 1. Mount the router (required — nothing is reachable until this is done)

`apps/api/src/veo/api/app.py`, alongside the existing includes:

```python
from veo.credentials import router as credentials_routes

app.include_router(credentials_routes.router, prefix=api_prefix)
```

This adds:

| Method | Path | Permission |
| --- | --- | --- |
| `GET` | `/api/credentials` | `CREDENTIAL_READ_STATE` |
| `PUT` | `/api/credentials/{provider}/{field}` | `CREDENTIAL_MANAGE` |
| `DELETE` | `/api/credentials/{provider}/{field}` | `CREDENTIAL_MANAGE` |
| `POST` | `/api/credentials/{provider}/verify` | `CREDENTIAL_MANAGE` |

`apps/api/openapi.json` and `packages/shared-types` will need regenerating afterwards.

Also call the startup guard, so a deployment with a missing or malformed master key fails
before it accepts a single credential rather than on the first write:

```python
from veo.credentials import assert_vault_startup_ready

assert_vault_startup_ready(get_settings())
```

---

## 2. Add `cryptography` to `apps/api/pyproject.toml` (recommended)

```toml
"cryptography>=43.0,<47.0",
```

`cryptography` is not currently installed, so `cipher.py` implements AES-256-GCM on the
standard library. It is **real** AES-256-GCM, not a stand-in: `test_cipher.py` pins it
against the published GCM test vectors (McGrew & Viega cases 13–16), and the backends
produce byte-identical output, so adding the dependency changes nothing on disk and
requires no data migration — `select_cipher_backend()` simply starts preferring it.

The reason to add it anyway is that the pure-Python S-box is a table lookup and therefore
**not constant-time**. An attacker who can run code on the same host and observe cache
timing could, in principle, recover the master key. That needs local co-residency and a
great many samples, and credential writes are rare, so it is an accepted risk rather than
a blocker — but it is a real one, and it disappears entirely with this line.

Secondary benefit: the pure-Python GHASH runs 128 iterations per 16-byte block. Fine for
credentials (a few milliseconds), unsuitable if this module is ever reused for bulk data.

---

## 3. Settings for multi-key rotation (needed before the first real rotation)

`CredentialVault.rotate_key()` decrypts each row with whichever key version wrote it, so
it needs the retired keys. Today they can only be passed in code:

```python
CredentialVault(session, master_key=current, previous_keys=[retired_v1])
```

`core/settings.py` has `credential_encryption_key` and `credential_key_version` but no way
to express the previous ones. Suggested addition:

```python
# Retired master keys, "version:base64" per entry, kept only until every row has been
# re-encrypted. Rotation reads them; nothing else does.
credential_previous_encryption_keys: list[str] = Field(default_factory=list)
```

Until then a rotation has to be driven by a script that constructs the vault directly.
Rows whose `key_version` is not available are skipped and counted in `RotationReport`,
never silently dropped.

---

## 4. Global handlers for `veo.authz.AuthorizationError` (nice to have)

`app.py` handles `StarletteHTTPException` and `RequestValidationError`. A
`PermissionDeniedError` raised by `authz.require()` matches neither and would surface as a
500. `router.py` works around this with a `guard()` wrapper that catches it and re-raises
an `HTTPException` carrying the platform error envelope — correct, but every router will
need the same wrapper. Two handlers in `app.py` would remove the duplication:

```python
PermissionDeniedError -> 403 PERMISSION_DENIED
AuthenticationError   -> 401 UNAUTHENTICATED
```

`OrganizationMismatch` should stay a **404**, not a 401 — `require_same_organization`'s
own docstring says so, and this package follows the same rule.

---

## 5. Consider moving `CredentialProvider` into `contracts/enums.py` (nice to have)

`providers.py` defines `CredentialProvider` because `DataSource` is the wrong vocabulary:
`OPENAI` is not a data source (an AI answer is recorded as `AI_ENGINE_OBSERVATION`), and
`CALCULATED` / `VEO_CRAWLER` hold no secret. Its values are string-identical to the keys of
`ProviderCredentials.states()` in `core/settings.py`, so `/api/providers` (environment) and
`/api/credentials` (stored) report the same names.

That alignment is currently maintained by hand in two places. Promoting the enum to
`contracts` and having `states()` iterate it would make drift impossible. `CredentialField`
could move with it. This worker did not do it because `contracts/` is owned elsewhere.

---

## 6. Verification currently checks integrity, not acceptance

`POST /credentials/{provider}/verify` runs `LocalIntegrityVerifier`: every required field
is present, active, and decrypts under the current master key. It does **not** claim the
provider would accept the credential, because no provider client exists in the repository
yet and this worker will not invent outbound HTTP.

When a provider client lands, implement `vault.CredentialVerifier` next to it and pass it
to `vault.verify(..., verifier=...)`. The contract to honour: return a
`VerificationErrorCode`, never the provider's error text — that text routinely quotes the
credential back. Anything raised is caught, collapsed to `UNKNOWN`, and redacted before it
reaches the log.

---

## 7. Note for whoever writes the first provider client

`CredentialVault.resolve_for_use()` is the only decrypt path. It takes an
`organization_id` (not a `Principal`, since a worker has no HTTP principal) and returns a
`SecretStr`. Unwrap it directly into the outbound request and never assign the unwrapped
value to anything that outlives the call. It must not be reachable from an HTTP handler —
`tests/credentials/test_vault.py` asserts the name does not appear in `router.py`.
