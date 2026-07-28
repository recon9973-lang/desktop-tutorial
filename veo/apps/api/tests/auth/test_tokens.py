"""Access-token signing and the refusal reasons that never reach the caller."""

from __future__ import annotations

import base64
import uuid
from datetime import UTC, datetime, timedelta

import jwt
import pytest

from veo.auth.tokens import (
    ACCESS_TOKEN_ALGORITHM,
    ACCESS_TOKEN_AUDIENCE,
    ACCESS_TOKEN_ISSUER,
    GENERIC_AUTH_MESSAGE_KO,
    REFRESH_TOKEN_ENTROPY_BYTES,
    TokenError,
    TokenRejection,
    decode_access_token,
    encode_access_token,
    hash_refresh_token,
    mint_refresh_token,
    signing_secret,
)
from veo.contracts.enums import Role


@pytest.fixture
def subject() -> dict[str, object]:
    return {
        "user_id": uuid.uuid4(),
        "organization_id": uuid.uuid4(),
        "roles": frozenset({Role.ANALYST, Role.SALES_VIEWER}),
        "session_id": uuid.uuid4(),
    }


def _encode(subject: dict[str, object], **kwargs: object) -> str:
    return encode_access_token(**subject, **kwargs)  # type: ignore[arg-type]


def test_roundtrip_preserves_every_claim(subject: dict[str, object]) -> None:
    claims = decode_access_token(_encode(subject))

    assert claims.user_id == subject["user_id"]
    assert claims.organization_id == subject["organization_id"]
    assert claims.roles == subject["roles"]
    assert claims.session_id == subject["session_id"]
    assert claims.jti


def test_two_tokens_for_one_session_have_distinct_jti(subject: dict[str, object]) -> None:
    assert decode_access_token(_encode(subject)).jti != decode_access_token(_encode(subject)).jti


def test_raw_claims_carry_the_agreed_issuer_and_audience(subject: dict[str, object]) -> None:
    raw = jwt.decode(
        _encode(subject),
        signing_secret(),
        algorithms=[ACCESS_TOKEN_ALGORITHM],
        audience=ACCESS_TOKEN_AUDIENCE,
        issuer=ACCESS_TOKEN_ISSUER,
    )

    assert raw["iss"] == "veo"
    assert raw["aud"] == "veo-console"
    assert set(raw) >= {"sub", "org", "roles", "sid", "jti", "iat", "exp", "iss", "aud"}


def test_expired_token_is_rejected(subject: dict[str, object]) -> None:
    issued = datetime.now(UTC) - timedelta(hours=2)
    token = _encode(subject, issued_at=issued, ttl_seconds=60)

    with pytest.raises(TokenError) as caught:
        decode_access_token(token)

    assert caught.value.rejection is TokenRejection.EXPIRED


def test_tampered_signature_is_rejected(subject: dict[str, object]) -> None:
    header, payload, signature = _encode(subject).split(".")
    flipped = signature[:-2] + ("aa" if not signature.endswith("aa") else "bb")

    with pytest.raises(TokenError) as caught:
        decode_access_token(f"{header}.{payload}.{flipped}")

    assert caught.value.rejection is TokenRejection.BAD_SIGNATURE


def test_tampered_payload_is_rejected(subject: dict[str, object]) -> None:
    """Escalating the roles claim in place must not survive verification."""
    token = _encode(subject)
    header, _, signature = token.split(".")
    forged = (
        base64.urlsafe_b64encode(
            b'{"sub":"x","org":"y","roles":["SUPER_ADMIN"],"sid":"z","jti":"1",'
            b'"iat":0,"exp":9999999999,"iss":"veo","aud":"veo-console"}'
        )
        .rstrip(b"=")
        .decode()
    )

    with pytest.raises(TokenError) as caught:
        decode_access_token(f"{header}.{forged}.{signature}")

    assert caught.value.rejection is TokenRejection.BAD_SIGNATURE


def test_token_signed_with_another_secret_is_rejected(subject: dict[str, object]) -> None:
    foreign = jwt.encode(
        {
            "sub": str(subject["user_id"]),
            "org": str(subject["organization_id"]),
            "roles": ["SUPER_ADMIN"],
            "sid": str(subject["session_id"]),
            "jti": uuid.uuid4().hex,
            "iat": int(datetime.now(UTC).timestamp()),
            "exp": int(datetime.now(UTC).timestamp()) + 900,
            "iss": ACCESS_TOKEN_ISSUER,
            "aud": ACCESS_TOKEN_AUDIENCE,
        },
        "an-entirely-different-signing-key",
        algorithm=ACCESS_TOKEN_ALGORITHM,
    )

    with pytest.raises(TokenError) as caught:
        decode_access_token(foreign)

    assert caught.value.rejection is TokenRejection.BAD_SIGNATURE


def test_wrong_audience_is_rejected(subject: dict[str, object]) -> None:
    token = jwt.encode(
        {
            "sub": str(subject["user_id"]),
            "org": str(subject["organization_id"]),
            "roles": ["ANALYST"],
            "sid": str(subject["session_id"]),
            "jti": uuid.uuid4().hex,
            "iat": int(datetime.now(UTC).timestamp()),
            "exp": int(datetime.now(UTC).timestamp()) + 900,
            "iss": ACCESS_TOKEN_ISSUER,
            "aud": "some-other-app",
        },
        signing_secret(),
        algorithm=ACCESS_TOKEN_ALGORITHM,
    )

    with pytest.raises(TokenError) as caught:
        decode_access_token(token)

    assert caught.value.rejection is TokenRejection.WRONG_AUDIENCE


def test_wrong_issuer_is_rejected(subject: dict[str, object]) -> None:
    token = jwt.encode(
        {
            "sub": str(subject["user_id"]),
            "org": str(subject["organization_id"]),
            "roles": ["ANALYST"],
            "sid": str(subject["session_id"]),
            "jti": uuid.uuid4().hex,
            "iat": int(datetime.now(UTC).timestamp()),
            "exp": int(datetime.now(UTC).timestamp()) + 900,
            "iss": "not-veo",
            "aud": ACCESS_TOKEN_AUDIENCE,
        },
        signing_secret(),
        algorithm=ACCESS_TOKEN_ALGORITHM,
    )

    with pytest.raises(TokenError) as caught:
        decode_access_token(token)

    assert caught.value.rejection is TokenRejection.WRONG_ISSUER


def test_algorithm_confusion_none_is_rejected(subject: dict[str, object]) -> None:
    unsigned = jwt.encode(
        {
            "sub": str(subject["user_id"]),
            "org": str(subject["organization_id"]),
            "roles": ["SUPER_ADMIN"],
            "sid": str(subject["session_id"]),
            "jti": uuid.uuid4().hex,
            "iat": int(datetime.now(UTC).timestamp()),
            "exp": int(datetime.now(UTC).timestamp()) + 900,
            "iss": ACCESS_TOKEN_ISSUER,
            "aud": ACCESS_TOKEN_AUDIENCE,
        },
        key="",
        algorithm="none",
    )

    with pytest.raises(TokenError):
        decode_access_token(unsigned)


@pytest.mark.parametrize("garbage", ["", "abc", "a.b", "a.b.c.d", "....", "not.a.token"])
def test_malformed_tokens_are_rejected(garbage: str) -> None:
    with pytest.raises(TokenError) as caught:
        decode_access_token(garbage)

    assert caught.value.rejection is TokenRejection.MALFORMED


def test_every_rejection_reports_the_same_generic_korean_sentence(
    subject: dict[str, object],
) -> None:
    """The typed reason is for us. The caller always sees one sentence."""
    messages = set()
    for token in ("", "a.b.c", _encode(subject, issued_at=datetime(2020, 1, 1, tzinfo=UTC))):
        with pytest.raises(TokenError) as caught:
            decode_access_token(token)
        messages.add(caught.value.public_message)

    assert messages == {GENERIC_AUTH_MESSAGE_KO}


def test_refresh_token_carries_at_least_256_bits() -> None:
    assert REFRESH_TOKEN_ENTROPY_BYTES >= 32

    token = mint_refresh_token()

    assert len(token) >= 43
    assert token != mint_refresh_token()


def test_refresh_hash_is_sha256_hex_and_irreversible() -> None:
    token = mint_refresh_token()
    digest = hash_refresh_token(token)

    assert len(digest) == 64
    assert int(digest, 16) >= 0
    assert token not in digest
    assert digest == hash_refresh_token(token)
    assert digest != hash_refresh_token(mint_refresh_token())
