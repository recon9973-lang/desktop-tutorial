"""The authentication audit trail, and the scrubber that keeps it safe to keep.

An audit log is only worth having if it can be read — by an operator during an incident,
by an auditor, sometimes by a customer. That makes it exactly the wrong place for a
password, a token, an address or an IP. It is also append-only, so anything written here
is written for as long as the table lives.

The defence is not "remember not to log secrets". It is an allowlist: only keys this
module names may appear in ``detail``, every value is checked against the shapes that
personal data and credentials take, and anything matching is replaced with
:data:`REDACTED`. A future caller who passes something careless gets a redacted row, not
a leak.

What is recorded instead: hashed identifiers, machine-readable outcome codes, and ids of
rows that already exist elsewhere in the database.
"""

from __future__ import annotations

import re
import uuid
from enum import StrEnum
from typing import Any

from sqlalchemy.orm import Session

from veo.db.models.identity import AuditLog

#: What a scrubbed value is replaced with.
REDACTED = "[REDACTED]"

#: Longer than this and it is not an outcome code — it is content of some kind.
MAX_DETAIL_VALUE_LENGTH = 64


class AuthAuditAction(StrEnum):
    """Every authentication event VEO records. A closed set, so the trail is queryable."""

    LOGIN_SUCCEEDED = "auth.login.succeeded"
    LOGIN_FAILED = "auth.login.failed"
    LOGIN_LOCKED_OUT = "auth.login.locked_out"
    LOGOUT = "auth.logout"
    TOKEN_REFRESHED = "auth.token.refreshed"  # noqa: S105 - an event name, not a credential
    REFRESH_REUSE_DETECTED = "auth.refresh.reuse_detected"
    SESSION_REVOKED = "auth.session.revoked"


class LoginFailureCode(StrEnum):
    """Why a sign-in failed, for the trail only.

    None of these ever reaches the caller: the response to every one of them is the same
    generic 401, because "no such user" and "wrong password" are different answers only
    to someone probing for accounts.
    """

    NO_SUCH_USER = "NO_SUCH_USER"
    PASSWORD_MISMATCH = "PASSWORD_MISMATCH"  # noqa: S105 - an outcome code, not a credential
    USER_INACTIVE = "USER_INACTIVE"
    NO_ORGANIZATION = "NO_ORGANIZATION"
    ORGANIZATION_INACTIVE = "ORGANIZATION_INACTIVE"
    ORGANIZATION_AMBIGUOUS = "ORGANIZATION_AMBIGUOUS"
    LOCKED_OUT = "LOCKED_OUT"


#: Keys permitted in ``detail``. Anything else is dropped, not redacted — a key VEO does
#: not recognise is a key nobody has reviewed for what it might contain.
ALLOWED_DETAIL_KEYS = frozenset(
    {
        "outcome",
        "reason",
        "attempt",
        "failed_count",
        "locked",
        "retry_after_seconds",
        "rotation_count",
        "revoked_sessions",
        "roles",
        "session_generation",
        "identifier_hash",
        "family_id",
    }
)

_EMAIL = re.compile(r"[^\s@]+@[^\s@]+\.[^\s@]+")
_IPV4 = re.compile(r"\b\d{1,3}(?:\.\d{1,3}){3}\b")
_IPV6 = re.compile(r"(?:[0-9a-fA-F]{0,4}:){2,}[0-9a-fA-F]{0,4}")
_PASSWORD_HASH = re.compile(r"\$argon2|\$2[aby]\$|\$scrypt\$|\$pbkdf2")
_JWT = re.compile(r"^[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}$")


def _looks_sensitive(value: str) -> bool:
    """Shapes that must never be written to the trail, whatever key they arrive under."""
    if len(value) > MAX_DETAIL_VALUE_LENGTH:
        return True
    return bool(
        _EMAIL.search(value)
        or _IPV4.search(value)
        or _IPV6.search(value)
        or _PASSWORD_HASH.search(value)
        or _JWT.match(value)
    )


def sanitize_detail(detail: dict[str, Any] | None) -> dict[str, Any]:
    """Reduce ``detail`` to allowlisted keys holding demonstrably safe values.

    Unknown keys are dropped. Known keys holding something that looks like personal data
    or a credential keep the key — so the shape of the event survives — but lose the
    value.
    """
    if not detail:
        return {}

    cleaned: dict[str, Any] = {}
    for key, value in detail.items():
        if key not in ALLOWED_DETAIL_KEYS:
            continue
        cleaned[key] = _sanitize_value(value)
    return cleaned


def _sanitize_value(value: Any) -> Any:
    if value is None or isinstance(value, bool | int | float):
        return value
    if isinstance(value, list | tuple):
        return [_sanitize_value(item) for item in value]
    text = str(value)
    return REDACTED if _looks_sensitive(text) else text


def record_auth_event(
    db: Session,
    *,
    action: AuthAuditAction,
    organization_id: uuid.UUID | None = None,
    actor_user_id: uuid.UUID | None = None,
    target_type: str | None = None,
    target_id: str | None = None,
    request_id: str | None = None,
    source_ip_hash: str | None = None,
    detail: dict[str, Any] | None = None,
) -> AuditLog:
    """Append one authentication event.

    ``source_ip_hash`` must already be hashed — this function will not accept a raw
    address, because a helper that quietly hashes whatever it is handed is a helper that
    stops being checked. Use :func:`veo.auth.hashing.optional_identifier_hash`.
    """
    if not isinstance(action, AuthAuditAction):
        raise ValueError(f"unknown authentication audit action: {action!r}")
    if source_ip_hash is not None and _looks_sensitive(source_ip_hash):
        raise ValueError("source_ip_hash must be a hash, not an address")

    row = AuditLog(
        id=uuid.uuid4(),
        organization_id=organization_id,
        actor_user_id=actor_user_id,
        actor_kind="USER" if actor_user_id else "ANONYMOUS",
        action=action.value,
        target_type=target_type,
        target_id=target_id,
        request_id=request_id,
        source_ip_hash=source_ip_hash,
        detail=sanitize_detail(detail),
    )
    db.add(row)
    db.flush()
    return row
