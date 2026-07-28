"""One-way digests for the identifiers VEO refuses to store in the clear.

Email addresses, IP addresses and user agents are personal data. VEO needs them only to
answer questions of the form "is this the same one as before?", which a digest answers
just as well as the value itself. So the value never lands in a row.

These digests are deliberately plain SHA-256, not a password hash: they key lookups on
every request and must stay cheap. That means they are not resistant to a dictionary
attack over a known address space — a determined attacker holding the database can test
whether a *specific* address appears. That is the accepted trade-off, and it is why these
helpers are never used for passwords.
"""

from __future__ import annotations

import hashlib
import re

#: Length of every digest this module produces, in hex characters. Matches the
#: ``String(64)`` columns on ``UserSession`` and ``LoginAttempt``.
DIGEST_LENGTH = 64


def sha256_hex(value: str) -> str:
    """SHA-256 of ``value``, hex-encoded."""
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


#: Deliberately not RFC 5322, and deliberately not ``pydantic.EmailStr``.
#:
#: The full grammar accepts addresses no mail system in Korea will deliver to, and
#: ``EmailStr`` would pull in a new runtime dependency to reject the same three mistakes
#: this catches: a bare username, a stray space, a missing dot in the domain. Delivery is
#: proven by an invitation link arriving, not by a regular expression — so the job here is
#: only to stop an obvious typo becoming an account nobody can reach.
EMAIL_SHAPE_PATTERN = r"[^@\s]+@[^@\s]+\.[^@\s]+"

_EMAIL_SHAPE = re.compile(rf"\A{EMAIL_SHAPE_PATTERN}\Z")


def looks_like_email(value: str) -> bool:
    """Whether ``value`` is shaped like a deliverable address."""
    return _EMAIL_SHAPE.fullmatch(value.strip()) is not None


def normalize_email(email: str) -> str:
    """Fold an address to the single form VEO stores and compares.

    Case folding only. VEO does not strip dots or ``+`` tags: those are provider-specific
    conventions, and treating ``a.b@x`` and ``ab@x`` as one account would silently merge
    two identities on providers that consider them distinct.
    """
    return email.strip().casefold()


def identifier_hash(value: str) -> str:
    """Throttle and audit key for an email address or an IP address.

    Normalises first, so ``Analyst@Example.Test`` and ``analyst@example.test`` share one
    lockout counter and cannot be used to double an attacker's attempt budget.
    """
    return sha256_hex(normalize_email(value))


def optional_identifier_hash(value: str | None) -> str | None:
    """``identifier_hash`` that tolerates a missing value."""
    if value is None or not value.strip():
        return None
    return identifier_hash(value)
