# `veo.auth` → integration requests

Everything below is outside `apps/api/src/veo/auth/**` and therefore not mine to change.
Nothing here is required for the auth package to be correct on its own; items 1–3 are
required for it to be *reachable*.

---

## 1. Mount the router and install the resolver (required)

`veo/auth/router.py` deliberately mounts nothing. In `veo/api/app.py::create_app`:

```python
from veo.auth.resolver import install_auth
from veo.auth.router import router as auth_router

install_auth(app)                                   # resolver + auth error handlers
app.include_router(auth_router, prefix=api_prefix)  # /api/auth/{login,refresh,logout,me}
```

`install_auth` must run **before** the first request. It does two things:

* `set_principal_resolver(app, BearerPrincipalResolver())`;
* registers exception handlers for `AuthenticationError`, `PermissionDeniedError`,
  `OrganizationMismatch` and `AccountLockedError`.

The handlers are registered here rather than in `app.py` because `app.py` is not mine to
edit, and without them `AuthenticationError` — which `veo.authz.get_principal` raises on
every unauthenticated request — escapes as a 500. **If you would rather own that mapping
in `app.py`, please move it there and drop the `add_exception_handler` calls from
`install_auth`; do not leave both.** The mapping must stay:

| condition                                   | status | `ErrorCode`         |
| ------------------------------------------- | ------ | ------------------- |
| no/!invalid credential, revoked session      | 401    | `UNAUTHENTICATED`   |
| authenticated, permission missing            | 403    | `PERMISSION_DENIED` |
| resource in another organization             | 404    | `NOT_FOUND`         |
| sign-in throttled                            | 429    | `RATE_LIMITED`      |

Every 401 body carries the same generic Korean sentence
(`veo.auth.tokens.GENERIC_AUTH_MESSAGE_KO`). The 403 body does not name the missing
permission — `PermissionDeniedError` does, in `str(exc)`, for logs only.

## 2. Regenerate `openapi.json` (required)

`apps/api/openapi.json` and `packages/shared-types` are not mine. Mounting the router adds
four paths and the `LoginRequest` / `SessionPayload` / `MePayload` / `LogoutPayload`
schemas, so `tests/contract/test_openapi_contract.py` will fail until the document is
re-exported (`scripts/export_openapi.py`).

## 3. Require `VEO_JWT_SECRET` outside local/test (requested)

`Settings.jwt_secret` is `SecretStr | None`. `veo.auth.tokens.signing_secret()` raises
`SigningKeyMissingError` when it is absent, so nothing is ever signed with a default key —
but that failure surfaces at the first login rather than at boot. A startup check in
`core/settings.py` or `api/app.py` (`if settings.is_production and not settings.jwt_secret:
raise`) would turn a runtime outage into a deploy-time refusal.

---

## Notes — no change requested, but you should know

**No `rotated_to` column was added.** The design calls for `rotated_to`/`rotated_from`
linkage; `UserSession` ships only `rotated_from_id`, and I did not alter the table. The
forward direction is `veo.auth.sessions.successor_of()`, a query on
`rotated_from_id == session.id`. It needs no column and cannot drift out of sync with the
backward link. Family revocation walks `family_id`, not the chain, so nothing depends on
the forward link being indexed.

**Two database sessions per authenticated request.** The resolver opens its own session
via `veo.db.session.session_scope` because it runs before route dependencies. If you want
one session per request, pass a request-scoped factory:
`install_auth(app, session_factory=my_factory)`. The resolver performs three indexed reads
(session, user + organization, role assignments); it is not free, and it is the price of
revoking a role taking effect on the next request instead of at token expiry.

**The refresh token is returned in the response body**, not set as a cookie. That keeps the
API surface uniform and lets non-browser clients use it, but it means the console must
store it somewhere; an `HttpOnly; Secure; SameSite=Strict` cookie set by the web layer
would be stronger against XSS. That is a front-end/integrator decision — the endpoints
accept the token in the body either way.

**Expiry sweeping is a function, not a schedule.** `sessions.sweep_expired(db,
organization_id=...)` exists and is tested; wiring it to a periodic worker task lives in
`apps/worker/**`. Nothing depends on it — every read already rejects expired rows — it
only stops dead rows from looking live to an operator or a retention job.

**Throttling is per identifier, not per IP.** `login_attempts` is keyed by SHA-256 of the
lowercased email, so an attacker spraying one password across many addresses is not slowed
down by it, and a customer whose address is known can be locked out for the window. Both
are deliberate (see the module docstring). A per-IP or per-ASN limit at the edge would
close the spraying gap; it does not belong in this table.
