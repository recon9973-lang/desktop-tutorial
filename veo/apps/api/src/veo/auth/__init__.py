"""Authentication: proving who is calling.

The division of labour with :mod:`veo.authz` is strict. This package establishes
*identity* — passwords, tokens, sessions, throttling — and hands ``veo.authz`` a
:class:`~veo.authz.Principal`. It never decides what that principal may do; the permission
matrix lives in ``veo.authz`` and is not restated here.

The load-bearing decisions, in one place:

* An access token is a short-lived signed JWT, and it is **not** the authority on
  permissions. Roles are read from ``role_assignments`` on every request, so revoking a
  role takes effect on the next call rather than whenever the token happens to expire.
* A refresh token is opaque random material. Only its SHA-256 is stored, it is single-use,
  and replaying a spent one revokes the entire sign-in lineage.
* Every authentication failure — unknown address, wrong password, revoked session,
  expired or forged token — produces the same status, the same body and roughly the same
  latency. Distinguishing them is how an attacker maps the customer list.
* A principal belongs to exactly one organization, fixed at sign-in.

Wiring: call :func:`veo.auth.resolver.install_auth` on the application, and include
:data:`veo.auth.router.router`. This package deliberately mounts nothing itself.
"""

from veo.auth.audit import AuthAuditAction, LoginFailureCode, record_auth_event
from veo.auth.hashing import identifier_hash, normalize_email, optional_identifier_hash, sha256_hex
from veo.auth.passwords import (
    PasswordPolicyError,
    dummy_verify,
    hash_password,
    needs_rehash,
    verify_password,
)
from veo.auth.resolver import BearerPrincipalResolver, bearer_token_from, install_auth, load_roles

# ``veo.auth.router`` is deliberately **not** re-exported here, and this is load-bearing
# rather than tidiness. The router imports the application's request helpers, which import
# the application, which includes the router — so re-exporting it made
# ``import veo.auth.passwords`` (or anything else in this package) fail with a circular
# import on a cold start, in a way that looked like an unrelated bug wherever it surfaced.
# The docstring above already says this package mounts nothing; whoever needs the router
# imports ``veo.auth.router`` directly, as ``veo.api.app`` does.
from veo.auth.sessions import (
    IssuedSession,
    RevocationReason,
    create_session,
    is_usable,
    load_active_session,
    load_by_refresh_token,
    revoke_all_for_user,
    revoke_family,
    revoke_session,
    rotate_session,
    successor_of,
    sweep_expired,
)
from veo.auth.throttle import (
    AccountLockedError,
    LockoutState,
    assert_not_locked,
    clear_failures,
    lockout_state,
    register_failure,
)
from veo.auth.tokens import (
    GENERIC_AUTH_MESSAGE_KO,
    AccessTokenClaims,
    TokenError,
    TokenRejection,
    decode_access_token,
    encode_access_token,
    hash_refresh_token,
    mint_refresh_token,
)

__all__ = [
    "GENERIC_AUTH_MESSAGE_KO",
    "AccessTokenClaims",
    "AccountLockedError",
    "AuthAuditAction",
    "BearerPrincipalResolver",
    "IssuedSession",
    "LockoutState",
    "LoginFailureCode",
    "PasswordPolicyError",
    "RevocationReason",
    "TokenError",
    "TokenRejection",
    "assert_not_locked",
    "bearer_token_from",
    "clear_failures",
    "create_session",
    "decode_access_token",
    "dummy_verify",
    "encode_access_token",
    "hash_password",
    "hash_refresh_token",
    "identifier_hash",
    "install_auth",
    "is_usable",
    "load_active_session",
    "load_by_refresh_token",
    "load_roles",
    "lockout_state",
    "mint_refresh_token",
    "needs_rehash",
    "normalize_email",
    "optional_identifier_hash",
    "record_auth_event",
    "register_failure",
    "revoke_all_for_user",
    "revoke_family",
    "revoke_session",
    "rotate_session",
    "sha256_hex",
    "successor_of",
    "sweep_expired",
    "verify_password",
]
