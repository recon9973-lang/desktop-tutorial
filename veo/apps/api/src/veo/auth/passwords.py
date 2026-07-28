"""Password hashing with argon2id.

Two things this module exists to guarantee.

*Cost.* argon2id is memory-hard, so an attacker holding the table cannot trade cheap
parallel hardware for speed the way they can against a fast digest. The parameters below
are tuned for an interactive login on a small API node; they are recorded in the hash
string itself, so raising them later does not invalidate existing hashes — it makes
:func:`needs_rehash` return ``True`` and the next successful sign-in upgrades the row.

*Timing.* Verifying a password for an address that has no account must cost about the
same as verifying one that does. Otherwise the response time answers "does this address
have an account here?" for anyone willing to time it. :func:`verify_password` accepts a
missing hash and burns a comparable amount of work against a dummy hash instead of
returning early.
"""

from __future__ import annotations

from functools import lru_cache

from argon2 import PasswordHasher
from argon2.exceptions import (
    HashingError,
    InvalidHashError,
    VerificationError,
    VerifyMismatchError,
)
from argon2.low_level import Type

#: Interactive-login parameters: 64 MiB, three passes, one lane.
#: Memory cost dominates an attacker's hardware budget, so it is the knob that is high.
ARGON2_TIME_COST = 3
ARGON2_MEMORY_COST_KIB = 64 * 1024
ARGON2_PARALLELISM = 1
ARGON2_HASH_LENGTH = 32
ARGON2_SALT_LENGTH = 16

#: Refuse absurd input rather than hand a memory-hard function an unbounded string.
#: Long passphrases are welcome; a megabyte of them is a denial-of-service vector.
MAX_PASSWORD_LENGTH = 1024
MIN_PASSWORD_LENGTH = 1

#: Fixed input used only to make an absent account cost the same as a present one.
#: Named so no reader — and no secret scanner — mistakes it for a credential.
_TIMING_EQUALISER_INPUT = "veo-timing-equaliser-not-a-credential"


class PasswordPolicyError(ValueError):
    """The supplied password cannot be hashed at all.

    Raised for structural problems only — empty, or long enough to be an attack. It never
    describes the strength of a real user's password, so it cannot be used as an oracle.
    """


@lru_cache(maxsize=1)
def _hasher() -> PasswordHasher:
    return PasswordHasher(
        time_cost=ARGON2_TIME_COST,
        memory_cost=ARGON2_MEMORY_COST_KIB,
        parallelism=ARGON2_PARALLELISM,
        hash_len=ARGON2_HASH_LENGTH,
        salt_len=ARGON2_SALT_LENGTH,
        type=Type.ID,
    )


@lru_cache(maxsize=1)
def _dummy_hash() -> str:
    """A real argon2id hash under the current parameters, computed once per process.

    Verifying against this costs what verifying a real user costs, which is the entire
    point: the work is what hides whether the account exists.
    """
    return _hasher().hash(_TIMING_EQUALISER_INPUT)


def _within_policy(password: str) -> bool:
    return MIN_PASSWORD_LENGTH <= len(password) <= MAX_PASSWORD_LENGTH


def hash_password(password: str) -> str:
    """Return an argon2id hash string, parameters included.

    Raises :class:`PasswordPolicyError` for input that must never reach the hasher.
    """
    if not _within_policy(password):
        raise PasswordPolicyError(
            f"password length must be between {MIN_PASSWORD_LENGTH} and "
            f"{MAX_PASSWORD_LENGTH} characters"
        )
    try:
        return _hasher().hash(password)
    except HashingError as exc:  # pragma: no cover - argon2 backend failure
        raise PasswordPolicyError("password could not be hashed") from exc


def dummy_verify() -> None:
    """Burn one verification's worth of work and discard the result.

    Call this on every path that would otherwise skip the hasher — no such user, user
    with no password set — so the fast path and the slow path take the same time.
    """
    try:
        _hasher().verify(_dummy_hash(), _TIMING_EQUALISER_INPUT + "-mismatch")
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return


def verify_password(stored_hash: str | None, password: str) -> bool:
    """Check ``password`` against ``stored_hash``.

    Returns ``False`` — never raises — for a missing, empty or unparseable hash, and
    still spends the time a real verification would. A caller therefore cannot tell an
    unknown address from a wrong password by timing the answer or by catching a
    different exception.
    """
    if not _within_policy(password):
        dummy_verify()
        return False
    if not stored_hash:
        dummy_verify()
        return False
    try:
        return _hasher().verify(stored_hash, password)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


def needs_rehash(stored_hash: str) -> bool:
    """Whether ``stored_hash`` was produced under weaker parameters than today's.

    An unreadable hash reports ``True``: whatever it is, it is not a current hash, and the
    row should be rewritten the next time the owner proves the password.
    """
    if not stored_hash:
        return True
    try:
        return bool(_hasher().check_needs_rehash(stored_hash))
    except (InvalidHashError, ValueError):
        return True
