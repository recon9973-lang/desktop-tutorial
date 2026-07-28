"""Result tokens: minted, hashed, compared in constant time, and expired.

A public result lives behind a URL that gets pasted into messages and left in browser
history. Three properties keep that from turning into a permanent leak.

**Unguessable.** 256 bits from :mod:`secrets`. The rule is 128; the cost of doubling it
is eleven characters of URL, so there is no reason to sit on the minimum.

**Stored hashed.** The server keeps SHA-256 of the token, never the token. Someone who
reads the store — a dump, a log, a backup — cannot reconstruct a working link from it.
A fast hash is the right choice *here*, unlike for a password: the input already carries
256 bits of uniform randomness, so there is no dictionary to run and stretching would
only slow down every legitimate read.

**Mortal.** Every token carries an expiry, checked on read. A short URL that never dies
is a permanent copy of whatever the scan found, addressable by anyone who ever saw it.

Comparison uses :func:`hmac.compare_digest`. Comparing hex digests with ``==`` returns
sooner on an early mismatch, and that timing difference is enough to walk a fingerprint
out one character at a time.
"""

from __future__ import annotations

import hashlib
import hmac
import re
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Final, final

__all__ = [
    "MIN_TOKEN_ENTROPY_BITS",
    "TOKEN_ENTROPY_BITS",
    "TOKEN_ENTROPY_BYTES",
    "IssuedToken",
    "fingerprint",
    "issue_token",
    "looks_like_token",
    "mint_token",
    "token_matches",
]

#: The floor the product promises. Anything below this is not a share link, it is a
#: guessable identifier with extra steps.
MIN_TOKEN_ENTROPY_BITS: Final = 128

TOKEN_ENTROPY_BYTES: Final = 32
TOKEN_ENTROPY_BITS: Final = TOKEN_ENTROPY_BYTES * 8

#: url-safe base64 of 32 bytes is 43 characters; the range leaves room for a future
#: token size without turning a shape check into a version check.
_TOKEN_SHAPE = re.compile(r"\A[A-Za-z0-9_-]{40,64}\Z")


def mint_token() -> str:
    """A fresh, url-safe result token."""
    return secrets.token_urlsafe(TOKEN_ENTROPY_BYTES)


def fingerprint(token: str) -> str:
    """The stored form of ``token``. One way, and stable across processes."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def token_matches(candidate: str, stored_fingerprint: str) -> bool:
    """Whether ``candidate`` is the token behind ``stored_fingerprint``."""
    return hmac.compare_digest(fingerprint(candidate), stored_fingerprint)


def looks_like_token(candidate: str) -> bool:
    """A cheap shape check, run before anything is hashed or looked up.

    It exists so that a path parameter carrying ``../../etc/passwd`` or a megabyte of
    text is discarded on sight rather than becoming a store lookup.
    """
    return bool(_TOKEN_SHAPE.fullmatch(candidate))


@final
@dataclass(frozen=True, slots=True)
class IssuedToken:
    """A minted token and the two facts the store needs about it."""

    token: str
    fingerprint: str
    issued_at: datetime
    expires_at: datetime

    def is_expired(self, *, now: datetime | None = None) -> bool:
        """Expiry is inclusive: at the stated instant the token is already gone."""
        moment = now or datetime.now(UTC)
        return moment >= self.expires_at


def issue_token(*, ttl_seconds: int, now: datetime | None = None) -> IssuedToken:
    """Mint a token that dies ``ttl_seconds`` from now."""
    if ttl_seconds <= 0:
        raise ValueError("ttl_seconds must be positive")
    issued_at = now or datetime.now(UTC)
    token = mint_token()
    return IssuedToken(
        token=token,
        fingerprint=fingerprint(token),
        issued_at=issued_at,
        expires_at=issued_at + timedelta(seconds=ttl_seconds),
    )
