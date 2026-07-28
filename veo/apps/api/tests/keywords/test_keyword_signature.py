"""The SearchAd request signature.

The signature is the one part of this integration that cannot be verified against a live
response *or* inferred from a fixture: it either matches what the server computes or the
call fails. So it is pinned against a vector computed by hand from the documented rule —
``base64(HMAC-SHA256(secret, "{timestamp}.{METHOD}.{path}"))`` — rather than against
whatever the implementation happens to produce.
"""

from __future__ import annotations

import base64
import hashlib
import hmac

import pytest
from pydantic import SecretStr

from veo.providers.naver.searchad import (
    KEYWORDSTOOL_PATH,
    SearchAdCredentials,
    build_headers,
    sign,
)

# A throwaway secret that exists only in this file. Not a credential.
VECTOR_SECRET = "veo-test-secret-key-do-not-use"
VECTOR_TIMESTAMP_MS = 1767225600000
VECTOR_MESSAGE = "1767225600000.GET./keywordstool"
VECTOR_SIGNATURE = "5/SbM3HmrtD6gyR/sGdr8vKnztctHkrvraLHVkQ7U9M="
VECTOR_POST_SIGNATURE = "FjtIFz25RSVK31ko6YpJkxakDNDF69JVNMQkKECsPaQ="


def test_signature_matches_the_hand_computed_vector() -> None:
    assert (
        sign(
            timestamp_ms=VECTOR_TIMESTAMP_MS,
            method="GET",
            path=KEYWORDSTOOL_PATH,
            secret_key=SecretStr(VECTOR_SECRET),
        )
        == VECTOR_SIGNATURE
    )


def test_the_vector_is_what_the_documented_rule_produces() -> None:
    """Recompute the vector from the rule, independently of the implementation.

    If this ever disagrees with ``test_signature_matches_the_hand_computed_vector`` the
    constant above was mistyped, not the implementation.
    """
    expected = base64.b64encode(
        hmac.new(
            VECTOR_SECRET.encode("utf-8"), VECTOR_MESSAGE.encode("utf-8"), hashlib.sha256
        ).digest()
    ).decode("ascii")
    assert expected == VECTOR_SIGNATURE


def test_method_is_upper_cased_before_signing() -> None:
    lowered = sign(
        timestamp_ms=VECTOR_TIMESTAMP_MS,
        method="get",
        path=KEYWORDSTOOL_PATH,
        secret_key=SecretStr(VECTOR_SECRET),
    )
    assert lowered == VECTOR_SIGNATURE


def test_method_is_part_of_the_signed_message() -> None:
    posted = sign(
        timestamp_ms=VECTOR_TIMESTAMP_MS,
        method="POST",
        path="/ncc/keywords",
        secret_key=SecretStr(VECTOR_SECRET),
    )
    assert posted == VECTOR_POST_SIGNATURE
    assert posted != VECTOR_SIGNATURE


def test_query_string_is_rejected_rather_than_silently_signed() -> None:
    """A signature over a path that still carries a query string would never verify.

    Failing loudly here is the difference between a clear error and an hour spent
    wondering why the server keeps answering 401.
    """
    with pytest.raises(ValueError, match="query"):
        sign(
            timestamp_ms=VECTOR_TIMESTAMP_MS,
            method="GET",
            path="/keywordstool?hintKeywords=x",
            secret_key=SecretStr(VECTOR_SECRET),
        )


def test_path_must_be_absolute() -> None:
    with pytest.raises(ValueError, match="/"):
        sign(
            timestamp_ms=VECTOR_TIMESTAMP_MS,
            method="GET",
            path="keywordstool",
            secret_key=SecretStr(VECTOR_SECRET),
        )


def test_headers_carry_the_signature_and_never_the_secret() -> None:
    credentials = SearchAdCredentials(
        api_key=SecretStr("synthetic-access-license"),
        secret_key=SecretStr(VECTOR_SECRET),
        customer_id="9999999",
    )
    headers = build_headers(
        credentials=credentials,
        timestamp_ms=VECTOR_TIMESTAMP_MS,
        method="GET",
        path=KEYWORDSTOOL_PATH,
    )

    assert headers["X-Timestamp"] == str(VECTOR_TIMESTAMP_MS)
    assert headers["X-API-KEY"] == "synthetic-access-license"
    assert headers["X-Customer"] == "9999999"
    assert headers["X-Signature"] == VECTOR_SIGNATURE

    # The secret key signs the message and is never transmitted.
    assert VECTOR_SECRET not in "".join(headers.values())


def test_credentials_do_not_leak_through_repr() -> None:
    credentials = SearchAdCredentials(
        api_key=SecretStr("synthetic-access-license"),
        secret_key=SecretStr(VECTOR_SECRET),
        customer_id="9999999",
    )
    rendered = f"{credentials!r} {credentials!s}"
    assert VECTOR_SECRET not in rendered
    assert "synthetic-access-license" not in rendered
