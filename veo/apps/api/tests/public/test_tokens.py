"""Result tokens: unguessable, stored hashed, and mortal.

A public result URL is handed around in messages and browser history. Three properties
keep that from becoming a leak: enough randomness that nobody enumerates one, a stored
form that a database dump cannot be replayed from, and an expiry that ends the exposure.
"""

from __future__ import annotations

import inspect
import math
import re
from datetime import UTC, datetime, timedelta

import pytest

from veo.public import tokens


def test_a_token_carries_at_least_128_bits_of_randomness() -> None:
    assert tokens.TOKEN_ENTROPY_BITS >= tokens.MIN_TOKEN_ENTROPY_BITS >= 128
    assert tokens.TOKEN_ENTROPY_BYTES * 8 == tokens.TOKEN_ENTROPY_BITS

    token = tokens.mint_token()
    # url-safe base64 carries 6 bits per character; the encoded length has to be able
    # to hold the declared entropy, or the constant is a claim the code does not meet.
    assert len(token) * 6 >= tokens.TOKEN_ENTROPY_BITS


def test_tokens_are_url_safe() -> None:
    assert re.fullmatch(r"[A-Za-z0-9_-]+", tokens.mint_token())


def test_minted_tokens_do_not_repeat_or_share_structure() -> None:
    minted = [tokens.mint_token() for _ in range(500)]
    assert len(set(minted)) == 500

    # Guessing one from another would show up as a shared prefix. With 256 bits of
    # randomness the longest shared prefix across 500 samples should be tiny.
    longest = 0
    for index in range(1, len(minted)):
        previous, current = minted[index - 1], minted[index]
        shared = 0
        for a, b in zip(previous, current, strict=False):
            if a != b:
                break
            shared += 1
        longest = max(longest, shared)
    assert longest <= 4

    # And the sample should look like it came from a uniform alphabet, not a counter.
    alphabet = {ch for token in minted for ch in token}
    assert len(alphabet) >= 40
    assert _shannon_bits_per_char(minted) > 5.0


def test_the_stored_form_is_a_hash_and_not_the_token() -> None:
    token = tokens.mint_token()
    stored = tokens.fingerprint(token)

    assert stored != token
    assert token not in stored
    assert re.fullmatch(r"[0-9a-f]{64}", stored)
    assert tokens.fingerprint(token) == stored


def test_matching_accepts_the_token_and_rejects_every_other() -> None:
    token = tokens.mint_token()
    stored = tokens.fingerprint(token)

    assert tokens.token_matches(token, stored) is True
    assert tokens.token_matches(tokens.mint_token(), stored) is False
    assert tokens.token_matches(token[:-1], stored) is False
    assert tokens.token_matches("", stored) is False


def test_comparison_is_constant_time() -> None:
    """Byte-by-byte comparison of a fingerprint leaks it one character at a time."""
    source = inspect.getsource(tokens)
    assert "compare_digest" in source


def test_an_issued_token_expires() -> None:
    now = datetime(2026, 7, 1, 9, 0, tzinfo=UTC)
    issued = tokens.issue_token(ttl_seconds=3600, now=now)

    assert issued.expires_at == now + timedelta(seconds=3600)
    assert issued.is_expired(now=now) is False
    assert issued.is_expired(now=now + timedelta(seconds=3599)) is False
    assert issued.is_expired(now=now + timedelta(seconds=3601)) is True


def test_expiry_is_inclusive_at_the_boundary() -> None:
    now = datetime(2026, 7, 1, 9, 0, tzinfo=UTC)
    issued = tokens.issue_token(ttl_seconds=60, now=now)
    assert issued.is_expired(now=issued.expires_at) is True


def test_a_non_positive_ttl_is_refused() -> None:
    with pytest.raises(ValueError, match="ttl_seconds"):
        tokens.issue_token(ttl_seconds=0)


def test_the_shape_check_rejects_junk_before_hashing() -> None:
    assert tokens.looks_like_token(tokens.mint_token()) is True
    assert tokens.looks_like_token("../../etc/passwd") is False
    assert tokens.looks_like_token("short") is False
    assert tokens.looks_like_token("x" * 500) is False


def _shannon_bits_per_char(samples: list[str]) -> float:
    counts: dict[str, int] = {}
    total = 0
    for sample in samples:
        for ch in sample:
            counts[ch] = counts.get(ch, 0) + 1
            total += 1
    return -sum((n / total) * math.log2(n / total) for n in counts.values())
