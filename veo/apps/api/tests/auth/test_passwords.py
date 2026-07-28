"""Password hashing: argon2id, and the timing floor that hides account existence."""

from __future__ import annotations

import statistics
import time

import pytest

from veo.auth.passwords import (
    MAX_PASSWORD_LENGTH,
    PasswordPolicyError,
    hash_password,
    needs_rehash,
    verify_password,
)

PASSWORD = "correct-horse-battery-staple-9f3"


def test_hash_is_argon2id_and_not_the_plaintext() -> None:
    stored = hash_password(PASSWORD)

    assert stored.startswith("$argon2id$")
    assert PASSWORD not in stored


def test_same_password_hashes_differently_each_time() -> None:
    assert hash_password(PASSWORD) != hash_password(PASSWORD)


def test_correct_password_verifies() -> None:
    assert verify_password(hash_password(PASSWORD), PASSWORD) is True


def test_wrong_password_fails() -> None:
    assert verify_password(hash_password(PASSWORD), PASSWORD + "!") is False


def test_missing_hash_fails_without_raising() -> None:
    assert verify_password(None, PASSWORD) is False
    assert verify_password("", PASSWORD) is False


def test_garbage_hash_fails_without_raising() -> None:
    assert verify_password("not-a-hash", PASSWORD) is False


def test_needs_rehash_is_false_for_a_fresh_hash() -> None:
    assert needs_rehash(hash_password(PASSWORD)) is False


def test_needs_rehash_is_true_for_a_weaker_legacy_hash() -> None:
    from argon2 import PasswordHasher
    from argon2.low_level import Type

    weak = PasswordHasher(
        time_cost=1, memory_cost=8, parallelism=1, hash_len=16, salt_len=8, type=Type.ID
    ).hash(PASSWORD)

    assert verify_password(weak, PASSWORD) is True
    assert needs_rehash(weak) is True


def test_needs_rehash_is_true_for_an_unreadable_hash() -> None:
    assert needs_rehash("not-a-hash") is True


def test_empty_password_is_rejected_at_hash_time() -> None:
    with pytest.raises(PasswordPolicyError):
        hash_password("")


def test_absurdly_long_password_is_rejected_rather_than_hashed() -> None:
    with pytest.raises(PasswordPolicyError):
        hash_password("a" * (MAX_PASSWORD_LENGTH + 1))


def test_absurdly_long_password_fails_verification_without_burning_cpu() -> None:
    stored = hash_password(PASSWORD)
    assert verify_password(stored, "a" * (MAX_PASSWORD_LENGTH + 1)) is False


def _median_seconds(call: object, rounds: int) -> float:
    samples: list[float] = []
    for _ in range(rounds):
        start = time.perf_counter()
        call()  # type: ignore[operator]
        samples.append(time.perf_counter() - start)
    return statistics.median(samples)


def test_missing_hash_burns_comparable_time_to_a_real_verify() -> None:
    """A non-existent account must not answer faster than a wrong password."""
    stored = hash_password(PASSWORD)

    real = _median_seconds(lambda: verify_password(stored, "wrong-password"), rounds=5)
    absent = _median_seconds(lambda: verify_password(None, "wrong-password"), rounds=5)

    assert absent > real * 0.5, (
        f"absent-user verify is far faster than a real one ({absent:.4f}s vs {real:.4f}s)"
    )
    assert absent < real * 2.0
