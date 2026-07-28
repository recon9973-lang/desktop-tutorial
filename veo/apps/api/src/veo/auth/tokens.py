"""Access tokens (signed, short-lived) and refresh tokens (opaque, stored hashed).

The two credentials do different jobs and are built differently on purpose.

An **access token** is a signed JWT that any request handler can verify without a
database round trip. It is short-lived precisely because it cannot be revoked on its own;
the session row behind it is what gets revoked, and :mod:`veo.auth.resolver` re-checks
that row on every request. Fifteen minutes is therefore an upper bound on how long a
*claim* survives, not on how long access survives.

A **refresh token** is opaque random bytes. There is nothing to verify offline and
nothing to forge: the server looks up SHA-256 of what it was given. Only the digest is
stored, so a stolen database dump contains no usable session.

Decoding reports a typed reason internally — an operator debugging a client needs to know
whether tokens are expiring or being signed with the wrong key. The caller only ever sees
:data:`GENERIC_AUTH_MESSAGE_KO`, because "expired" versus "bad signature" tells an
attacker which half of their guess was right.
"""

from __future__ import annotations

import secrets
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import StrEnum

import jwt

from veo.auth.hashing import sha256_hex
from veo.authz import AuthenticationError
from veo.contracts.enums import Role
from veo.core.settings import get_settings

ACCESS_TOKEN_ALGORITHM = "HS256"  # noqa: S105 - public JWT metadata, not a credential
ACCESS_TOKEN_ISSUER = "veo"  # noqa: S105 - public JWT metadata, not a credential
ACCESS_TOKEN_AUDIENCE = "veo-console"  # noqa: S105 - public JWT metadata, not a credential

#: 48 bytes = 384 bits of entropy, comfortably above the 256-bit floor.
REFRESH_TOKEN_ENTROPY_BYTES = 48

#: The single sentence every authentication failure shows a caller.
GENERIC_AUTH_MESSAGE_KO = "인증 정보가 유효하지 않습니다. 다시 로그인해 주세요."


class TokenRejection(StrEnum):
    """Why a token was refused. Internal diagnostics — never serialised to a caller."""

    EXPIRED = "EXPIRED"
    BAD_SIGNATURE = "BAD_SIGNATURE"
    WRONG_AUDIENCE = "WRONG_AUDIENCE"
    WRONG_ISSUER = "WRONG_ISSUER"
    MALFORMED = "MALFORMED"


class TokenError(AuthenticationError):
    """A token could not be turned into claims.

    ``str(exc)`` is the typed reason, for logs. ``public_message`` is what a caller sees,
    and it is the same sentence for every reason.
    """

    def __init__(self, rejection: TokenRejection) -> None:
        self.rejection = rejection
        self.public_message = GENERIC_AUTH_MESSAGE_KO
        super().__init__(rejection.value)


class SigningKeyMissingError(RuntimeError):
    """No JWT secret is configured.

    A configuration fault, not an authentication failure: signing with a default or
    empty key would let anyone mint tokens, so VEO refuses to start issuing them.
    """


@dataclass(frozen=True)
class AccessTokenClaims:
    """The verified contents of an access token.

    ``roles`` is carried for observability and cross-checking only. Authorization reads
    roles from the database on every request — see :mod:`veo.auth.resolver` — because a
    role revoked five minutes ago must not keep working for the rest of the token's life.
    """

    user_id: uuid.UUID
    organization_id: uuid.UUID
    roles: frozenset[Role]
    session_id: uuid.UUID
    jti: str
    issued_at: datetime
    expires_at: datetime


def signing_secret() -> str:
    """The HS256 key, or a loud failure."""
    secret = get_settings().jwt_secret
    if secret is None:
        raise SigningKeyMissingError(
            "VEO_JWT_SECRET is not configured; VEO will not sign tokens with a default key"
        )
    value = secret.get_secret_value()
    if not value:
        raise SigningKeyMissingError("VEO_JWT_SECRET is empty")
    return value


def encode_access_token(
    *,
    user_id: uuid.UUID,
    organization_id: uuid.UUID,
    roles: frozenset[Role],
    session_id: uuid.UUID,
    issued_at: datetime | None = None,
    ttl_seconds: int | None = None,
) -> str:
    """Sign one access token for one session inside one organization."""
    issued = issued_at or datetime.now(UTC)
    ttl = ttl_seconds if ttl_seconds is not None else get_settings().access_token_ttl_seconds
    expires = issued + timedelta(seconds=ttl)

    payload = {
        "sub": str(user_id),
        "org": str(organization_id),
        "roles": sorted(role.value for role in roles),
        "sid": str(session_id),
        "jti": uuid.uuid4().hex,
        "iat": int(issued.timestamp()),
        "exp": int(expires.timestamp()),
        "iss": ACCESS_TOKEN_ISSUER,
        "aud": ACCESS_TOKEN_AUDIENCE,
    }
    return jwt.encode(payload, signing_secret(), algorithm=ACCESS_TOKEN_ALGORITHM)


def decode_access_token(token: str) -> AccessTokenClaims:
    """Verify signature, issuer, audience and expiry, then return the claims.

    ``algorithms`` is pinned to a single symmetric algorithm, so a token whose header
    asks for ``none`` — or for an asymmetric algorithm that would let the public key be
    used as an HMAC secret — is rejected before its signature is even considered.
    """
    if not token or token.count(".") != 2:
        raise TokenError(TokenRejection.MALFORMED)

    try:
        payload = jwt.decode(
            token,
            signing_secret(),
            algorithms=[ACCESS_TOKEN_ALGORITHM],
            audience=ACCESS_TOKEN_AUDIENCE,
            issuer=ACCESS_TOKEN_ISSUER,
            options={"require": ["sub", "org", "sid", "jti", "iat", "exp", "iss", "aud"]},
        )
    except jwt.ExpiredSignatureError as exc:
        raise TokenError(TokenRejection.EXPIRED) from exc
    except jwt.InvalidAudienceError as exc:
        raise TokenError(TokenRejection.WRONG_AUDIENCE) from exc
    except jwt.InvalidIssuerError as exc:
        raise TokenError(TokenRejection.WRONG_ISSUER) from exc
    except jwt.InvalidSignatureError as exc:
        raise TokenError(TokenRejection.BAD_SIGNATURE) from exc
    except jwt.DecodeError as exc:
        # Covers an unreadable payload and a header asking for an algorithm we do not
        # accept — both are "this is not one of our tokens".
        raise TokenError(_decode_rejection(exc)) from exc
    except jwt.InvalidTokenError as exc:
        raise TokenError(TokenRejection.MALFORMED) from exc

    return _claims_from(payload)


def _decode_rejection(exc: jwt.DecodeError) -> TokenRejection:
    """Separate "wrong key" from "not a token at all" for the operator's benefit."""
    text = str(exc).lower()
    if "signature" in text or "algorithm" in text:
        return TokenRejection.BAD_SIGNATURE
    return TokenRejection.MALFORMED


def _claims_from(payload: dict[str, object]) -> AccessTokenClaims:
    try:
        user_id = uuid.UUID(str(payload["sub"]))
        organization_id = uuid.UUID(str(payload["org"]))
        session_id = uuid.UUID(str(payload["sid"]))
        issued_at = datetime.fromtimestamp(int(str(payload["iat"])), tz=UTC)
        expires_at = datetime.fromtimestamp(int(str(payload["exp"])), tz=UTC)
        jti = str(payload["jti"])
    except (KeyError, TypeError, ValueError) as exc:
        raise TokenError(TokenRejection.MALFORMED) from exc

    return AccessTokenClaims(
        user_id=user_id,
        organization_id=organization_id,
        roles=_roles_from(payload.get("roles")),
        session_id=session_id,
        jti=jti,
        issued_at=issued_at,
        expires_at=expires_at,
    )


def _roles_from(claim: object) -> frozenset[Role]:
    """Parse the roles hint leniently.

    An unrecognised role name is dropped rather than fatal: the claim is not the
    authority, and refusing the whole token because the vocabulary grew would break every
    session outstanding at deploy time.
    """
    if not isinstance(claim, list):
        return frozenset()
    parsed: set[Role] = set()
    for item in claim:
        try:
            parsed.add(Role(str(item)))
        except ValueError:
            continue
    return frozenset(parsed)


def mint_refresh_token() -> str:
    """A fresh opaque refresh token. URL-safe, so it survives any transport."""
    return secrets.token_urlsafe(REFRESH_TOKEN_ENTROPY_BYTES)


def hash_refresh_token(token: str) -> str:
    """The only form of a refresh token that VEO ever stores.

    Plain SHA-256, not argon2: the token is 384 bits of uniform randomness, so there is
    no dictionary to attack and no reason to make every refresh request pay for a
    memory-hard function.
    """
    return sha256_hex(token)
