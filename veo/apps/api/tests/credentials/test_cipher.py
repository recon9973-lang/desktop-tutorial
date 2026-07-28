"""Cryptographic core of the credential vault.

These tests are fully offline. They pin three things that must never regress:

* the implementation really is AES-256-GCM (checked against the published GCM test
  vectors, not against itself),
* a ciphertext is bound to the tenant, provider, field and key version it was written
  for, so it cannot be moved anywhere and still decrypt,
* a bad master key fails at load time rather than at first use.
"""

from __future__ import annotations

import base64
import uuid

import pytest
from pydantic import SecretStr

from veo.core.settings import Settings
from veo.credentials.cipher import (
    AES_GCM_ALGORITHM,
    NONCE_BYTES,
    CipherConfigurationError,
    DecryptionError,
    MasterKey,
    PurePythonAesGcmBackend,
    assert_cipher_backend_allowed,
    build_associated_data,
    build_fingerprint_context,
    load_master_key,
    select_cipher_backend,
)

SYNTHETIC_KEY_B64 = base64.b64encode(bytes(range(32))).decode("ascii")
SYNTHETIC_KEY_B64_V2 = base64.b64encode(bytes(range(32, 64))).decode("ascii")
PLAINTEXT = b"test-secret-not-a-real-key"


@pytest.fixture
def backend() -> PurePythonAesGcmBackend:
    return PurePythonAesGcmBackend()


@pytest.fixture
def key() -> MasterKey:
    return MasterKey.from_base64(SYNTHETIC_KEY_B64, version=1)


# --------------------------------------------------------------------------- #
# The implementation is really AES-256-GCM
# --------------------------------------------------------------------------- #

# McGrew & Viega GCM test cases 13-16 (AES-256). Verifying against these is the only
# way to know we implemented AES-GCM rather than something that merely round-trips.
_GCM_VECTORS = [
    pytest.param("00" * 32, "0" * 24, "", "", "", "530f8afbc74536b9a963b4f1c4cb738b",
                 id="tc13-empty"),
    pytest.param("00" * 32, "0" * 24, "00" * 16, "",
                 "cea7403d4d606b6e074ec5d3baf39d18",
                 "d0d1c8a799996bf0265b98b5d48ab919", id="tc14-one-block"),
    pytest.param(
        "feffe9928665731c6d6a8f9467308308feffe9928665731c6d6a8f9467308308",
        "cafebabefacedbaddecaf888",
        "d9313225f88406e5a55909c5aff5269a86a7a9531534f7da2e4c303d8a318a72"
        "1c3c0c95956809532fcf0e2449a6b525b16aedf5aa0de657ba637b391aafd255",
        "",
        "522dc1f099567d07f47f37a32a84427d643a8cdcbfe5c0c97598a2bd2555d1aa"
        "8cb08e48590dbb3da7b08b1056828838c5f61e6393ba7a0abcc9f662898015ad",
        "b094dac5d93471bdec1a502270e3cc6c",
        id="tc15-no-aad",
    ),
    pytest.param(
        "feffe9928665731c6d6a8f9467308308feffe9928665731c6d6a8f9467308308",
        "cafebabefacedbaddecaf888",
        "d9313225f88406e5a55909c5aff5269a86a7a9531534f7da2e4c303d8a318a72"
        "1c3c0c95956809532fcf0e2449a6b525b16aedf5aa0de657ba637b39",
        "feedfacedeadbeeffeedfacedeadbeefabaddad2",
        "522dc1f099567d07f47f37a32a84427d643a8cdcbfe5c0c97598a2bd2555d1aa"
        "8cb08e48590dbb3da7b08b1056828838c5f61e6393ba7a0abcc9f662",
        "76fc6ece0f4e1768cddf8853bb2d551b",
        id="tc16-with-aad",
    ),
]


@pytest.mark.parametrize(("key_hex", "iv_hex", "pt_hex", "aad_hex", "ct_hex", "tag_hex"),
                         _GCM_VECTORS)
def test_matches_published_gcm_test_vectors(
    backend: PurePythonAesGcmBackend,
    key_hex: str,
    iv_hex: str,
    pt_hex: str,
    aad_hex: str,
    ct_hex: str,
    tag_hex: str,
) -> None:
    produced = backend.encrypt(
        key=bytes.fromhex(key_hex),
        nonce=bytes.fromhex(iv_hex),
        plaintext=bytes.fromhex(pt_hex),
        associated_data=bytes.fromhex(aad_hex),
    )
    assert produced.hex() == ct_hex + tag_hex

    recovered = backend.decrypt(
        key=bytes.fromhex(key_hex),
        nonce=bytes.fromhex(iv_hex),
        ciphertext=produced,
        associated_data=bytes.fromhex(aad_hex),
    )
    assert recovered.hex() == pt_hex


def test_every_available_backend_agrees_with_the_vectors() -> None:
    """If ``cryptography`` is installed we must produce byte-identical output."""
    chosen = select_cipher_backend()
    assert chosen.algorithm == AES_GCM_ALGORITHM
    produced = chosen.encrypt(
        key=bytes(32),
        nonce=bytes(12),
        plaintext=bytes(16),
        associated_data=b"",
    )
    assert produced.hex() == (
        "cea7403d4d606b6e074ec5d3baf39d18d0d1c8a799996bf0265b98b5d48ab919"
    )


# --------------------------------------------------------------------------- #
# Round trip, nonce freshness, binding, tampering
# --------------------------------------------------------------------------- #


def test_round_trip(backend: PurePythonAesGcmBackend, key: MasterKey) -> None:
    aad = build_associated_data(uuid.uuid4(), "OPENAI", "api_key", 1)
    nonce = backend.random_nonce()
    assert len(nonce) == NONCE_BYTES

    ciphertext = backend.encrypt(
        key=key.aes_key, nonce=nonce, plaintext=PLAINTEXT, associated_data=aad
    )
    assert PLAINTEXT not in ciphertext

    assert (
        backend.decrypt(
            key=key.aes_key, nonce=nonce, ciphertext=ciphertext, associated_data=aad
        )
        == PLAINTEXT
    )


def test_identical_plaintext_produces_different_ciphertext(
    backend: PurePythonAesGcmBackend, key: MasterKey
) -> None:
    aad = build_associated_data(uuid.uuid4(), "OPENAI", "api_key", 1)
    writes = [
        backend.encrypt(
            key=key.aes_key,
            nonce=backend.random_nonce(),
            plaintext=PLAINTEXT,
            associated_data=aad,
        )
        for _ in range(8)
    ]
    assert len(set(writes)) == len(writes)


def test_ciphertext_from_one_organization_does_not_decrypt_under_another(
    backend: PurePythonAesGcmBackend, key: MasterKey
) -> None:
    org_a, org_b = uuid.uuid4(), uuid.uuid4()
    nonce = backend.random_nonce()
    ciphertext = backend.encrypt(
        key=key.aes_key,
        nonce=nonce,
        plaintext=PLAINTEXT,
        associated_data=build_associated_data(org_a, "OPENAI", "api_key", 1),
    )

    with pytest.raises(DecryptionError):
        backend.decrypt(
            key=key.aes_key,
            nonce=nonce,
            ciphertext=ciphertext,
            associated_data=build_associated_data(org_b, "OPENAI", "api_key", 1),
        )


@pytest.mark.parametrize(
    "moved_to",
    [
        ("OPENAI", "secret_key", 1),
        ("NAVER_DATALAB", "api_key", 1),
        ("OPENAI", "api_key", 2),
    ],
    ids=["other-field", "other-provider", "other-key-version"],
)
def test_ciphertext_is_bound_to_field_provider_and_key_version(
    backend: PurePythonAesGcmBackend, key: MasterKey, moved_to: tuple[str, str, int]
) -> None:
    org = uuid.uuid4()
    nonce = backend.random_nonce()
    ciphertext = backend.encrypt(
        key=key.aes_key,
        nonce=nonce,
        plaintext=PLAINTEXT,
        associated_data=build_associated_data(org, "OPENAI", "api_key", 1),
    )

    with pytest.raises(DecryptionError):
        backend.decrypt(
            key=key.aes_key,
            nonce=nonce,
            ciphertext=ciphertext,
            associated_data=build_associated_data(org, *moved_to),
        )


def test_flipping_one_byte_of_ciphertext_raises_instead_of_returning_garbage(
    backend: PurePythonAesGcmBackend, key: MasterKey
) -> None:
    aad = build_associated_data(uuid.uuid4(), "OPENAI", "api_key", 1)
    nonce = backend.random_nonce()
    ciphertext = backend.encrypt(
        key=key.aes_key, nonce=nonce, plaintext=PLAINTEXT, associated_data=aad
    )

    for index in range(len(ciphertext)):
        tampered = bytearray(ciphertext)
        tampered[index] ^= 0x01
        with pytest.raises(DecryptionError):
            backend.decrypt(
                key=key.aes_key,
                nonce=nonce,
                ciphertext=bytes(tampered),
                associated_data=aad,
            )


def test_a_wrong_nonce_raises(backend: PurePythonAesGcmBackend, key: MasterKey) -> None:
    aad = build_associated_data(uuid.uuid4(), "OPENAI", "api_key", 1)
    ciphertext = backend.encrypt(
        key=key.aes_key,
        nonce=backend.random_nonce(),
        plaintext=PLAINTEXT,
        associated_data=aad,
    )
    with pytest.raises(DecryptionError):
        backend.decrypt(
            key=key.aes_key,
            nonce=backend.random_nonce(),
            ciphertext=ciphertext,
            associated_data=aad,
        )


def test_truncated_ciphertext_raises(
    backend: PurePythonAesGcmBackend, key: MasterKey
) -> None:
    aad = build_associated_data(uuid.uuid4(), "OPENAI", "api_key", 1)
    with pytest.raises(DecryptionError):
        backend.decrypt(key=key.aes_key, nonce=bytes(12), ciphertext=b"short",
                        associated_data=aad)


def test_nonce_must_be_96_bits(backend: PurePythonAesGcmBackend, key: MasterKey) -> None:
    with pytest.raises(CipherConfigurationError):
        backend.encrypt(
            key=key.aes_key,
            nonce=bytes(16),
            plaintext=PLAINTEXT,
            associated_data=b"",
        )


def test_key_must_be_256_bits(backend: PurePythonAesGcmBackend) -> None:
    with pytest.raises(CipherConfigurationError):
        backend.encrypt(
            key=bytes(16), nonce=bytes(12), plaintext=PLAINTEXT, associated_data=b""
        )


# --------------------------------------------------------------------------- #
# Associated data construction
# --------------------------------------------------------------------------- #


def test_associated_data_is_unambiguous() -> None:
    org = uuid.uuid4()
    assert build_associated_data(org, "OPENAI", "api_key", 1) != build_associated_data(
        org, "OPENAI", "api", 1
    )


@pytest.mark.parametrize(
    ("provider", "field"),
    [("OPEN|AI", "api_key"), ("OPENAI", "api|key"), ("", "api_key"), ("OPENAI", "")],
)
def test_associated_data_rejects_separator_smuggling(provider: str, field: str) -> None:
    with pytest.raises(CipherConfigurationError):
        build_associated_data(uuid.uuid4(), provider, field, 1)


def test_fingerprint_context_excludes_key_version() -> None:
    """The context identifies the row, not the encryption epoch.

    Which key version happens to hold the ciphertext is irrelevant to *which credential
    this is*; mixing it in would make the context mean two different things at once.
    """
    org = uuid.uuid4()
    assert build_fingerprint_context(org, "OPENAI", "api_key") == (
        build_fingerprint_context(org, "OPENAI", "api_key")
    )
    assert build_fingerprint_context(org, "OPENAI", "api_key") != (
        build_fingerprint_context(uuid.uuid4(), "OPENAI", "api_key")
    )


# --------------------------------------------------------------------------- #
# Master key loading
# --------------------------------------------------------------------------- #


def test_master_key_loads_from_settings() -> None:
    settings = Settings(
        credential_encryption_key=SecretStr(SYNTHETIC_KEY_B64),
        credential_key_version=7,
    )
    loaded = load_master_key(settings)
    assert loaded.version == 7
    assert len(loaded.aes_key) == 32


@pytest.mark.parametrize(
    "bad",
    [
        base64.b64encode(bytes(16)).decode("ascii"),
        base64.b64encode(bytes(31)).decode("ascii"),
        base64.b64encode(bytes(64)).decode("ascii"),
        "not base64 at all !!!",
        "",
        "   ",
    ],
    ids=["16-bytes", "31-bytes", "64-bytes", "not-base64", "empty", "blank"],
)
def test_a_rejected_master_key_fails_loudly(bad: str) -> None:
    with pytest.raises(CipherConfigurationError):
        MasterKey.from_base64(bad, version=1)


def test_a_missing_master_key_fails_loudly() -> None:
    settings = Settings(credential_encryption_key=None)
    with pytest.raises(CipherConfigurationError):
        load_master_key(settings)


def test_key_version_must_be_positive() -> None:
    with pytest.raises(CipherConfigurationError):
        MasterKey.from_base64(SYNTHETIC_KEY_B64, version=0)


def test_master_key_repr_does_not_leak() -> None:
    loaded = MasterKey.from_base64(SYNTHETIC_KEY_B64, version=1)
    rendered = f"{loaded!r} {loaded!s}"
    assert loaded.aes_key.hex() not in rendered
    assert base64.b64encode(loaded.aes_key).decode("ascii") not in rendered
    assert "REDACTED" in rendered


def test_derived_keys_are_independent() -> None:
    loaded = MasterKey.from_base64(SYNTHETIC_KEY_B64, version=1)
    raw = base64.b64decode(SYNTHETIC_KEY_B64)
    assert loaded.aes_key != raw
    assert loaded.aes_key != loaded.fingerprint_key


def test_fingerprint_is_keyed_not_a_bare_digest() -> None:
    import hashlib

    key_one = MasterKey.from_base64(SYNTHETIC_KEY_B64, version=1)
    key_two = MasterKey.from_base64(SYNTHETIC_KEY_B64_V2, version=2)
    context = build_fingerprint_context(uuid.uuid4(), "OPENAI", "api_key")

    first = key_one.fingerprint(PLAINTEXT, context=context)
    assert len(first) == 64
    assert int(first, 16) >= 0
    assert first != hashlib.sha256(PLAINTEXT).hexdigest()
    assert first != hashlib.sha256(context + PLAINTEXT).hexdigest()
    assert first != key_two.fingerprint(PLAINTEXT, context=context)


def test_fingerprint_changes_with_the_plaintext() -> None:
    loaded = MasterKey.from_base64(SYNTHETIC_KEY_B64, version=1)
    context = build_fingerprint_context(uuid.uuid4(), "OPENAI", "api_key")
    assert loaded.fingerprint(PLAINTEXT, context=context) != loaded.fingerprint(
        b"test-secret-not-a-real-key-either", context=context
    )


# --------------------------------------------------------------------------- #
# Startup guard
# --------------------------------------------------------------------------- #


class _NotRealEncryption:
    """Stands in for any backend that is not authenticated AES. Never shipped."""

    algorithm = "NOT-ENCRYPTION"
    name = "stub"
    is_authenticated_aes = False

    def random_nonce(self) -> bytes:
        return bytes(NONCE_BYTES)

    def encrypt(
        self, *, key: bytes, nonce: bytes, plaintext: bytes, associated_data: bytes
    ) -> bytes:
        raise NotImplementedError

    def decrypt(
        self, *, key: bytes, nonce: bytes, ciphertext: bytes, associated_data: bytes
    ) -> bytes:
        raise NotImplementedError


@pytest.mark.parametrize("environment", ["staging", "production"])
def test_a_non_aes_backend_is_refused_outside_local(environment: str) -> None:
    with pytest.raises(CipherConfigurationError):
        assert_cipher_backend_allowed(_NotRealEncryption(), environment=environment)


@pytest.mark.parametrize("environment", ["local", "test"])
def test_a_non_aes_backend_is_tolerated_locally(environment: str) -> None:
    assert_cipher_backend_allowed(_NotRealEncryption(), environment=environment)


@pytest.mark.parametrize("environment", ["local", "test", "staging", "production"])
def test_the_shipped_backend_is_allowed_everywhere(environment: str) -> None:
    assert_cipher_backend_allowed(select_cipher_backend(), environment=environment)
