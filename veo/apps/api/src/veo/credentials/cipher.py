"""AES-256-GCM for the provider-credential vault.

Everything the vault needs in order to turn a secret into an opaque blob lives here:
the backend protocol, the cipher itself, master-key loading, and the startup guard.

Three decisions are load-bearing and are not negotiable in review:

* **AES-256-GCM with a fresh random 96-bit nonce per write.** GCM is authenticated, so a
  tampered ciphertext fails loudly instead of decrypting to plausible garbage.
* **The associated data binds the ciphertext to its row.** It carries the organization,
  provider, field and key version. A blob copied from one tenant's row into another's —
  by a database compromise, a bad restore, or a bug — no longer decrypts.
* **The fingerprint is an HMAC, not a bare SHA-256.** A customer id or a short API key is
  guessable; an unkeyed digest of one is an offline dictionary attack waiting to happen.

``cryptography`` is not currently a dependency of ``veo-api``. Rather than ship something
that merely looks encrypted, this module implements AES-256-GCM on the standard library
and pins it against the published GCM test vectors in
``tests/credentials/test_cipher.py``. If ``cryptography`` is installed the hardened
backend is preferred automatically and produces byte-identical output. See
``INTEGRATION_REQUEST.md`` for the request to add it.
"""

from __future__ import annotations

import base64
import binascii
import hashlib
import hmac
import re
import secrets
import uuid
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, ClassVar, Protocol, runtime_checkable

if TYPE_CHECKING:  # pragma: no cover - typing only
    from veo.core.settings import Settings

__all__ = [
    "AES_GCM_ALGORITHM",
    "MASTER_KEY_BYTES",
    "NONCE_BYTES",
    "TAG_BYTES",
    "CipherBackend",
    "CipherConfigurationError",
    "CredentialCryptoError",
    "DecryptionError",
    "MasterKey",
    "PurePythonAesGcmBackend",
    "assert_cipher_backend_allowed",
    "build_associated_data",
    "build_fingerprint_context",
    "load_master_key",
    "select_cipher_backend",
]

AES_GCM_ALGORITHM = "AES-256-GCM"
MASTER_KEY_BYTES = 32
NONCE_BYTES = 12
TAG_BYTES = 16

#: Environments where a backend that is not authenticated AES may still be used.
LOCAL_ENVIRONMENTS = frozenset({"local", "test"})

_AAD_DOMAIN = b"veo.credential.aead.v1"
_FINGERPRINT_DOMAIN = b"veo.credential.fingerprint.v1"
_HKDF_SALT = b"veo.credential.vault.v1"
_SEPARATOR = b"|"

# Provider and field names are embedded in the associated data. Constraining them to
# characters that cannot contain the separator is what makes that encoding unambiguous —
# without it, ("AB", "C") and ("A", "BC") would produce the same associated data.
_PROVIDER_PATTERN = re.compile(r"\A[A-Z][A-Z0-9_]{0,47}\Z")
_FIELD_PATTERN = re.compile(r"\A[a-z][a-z0-9_]{0,63}\Z")


class CredentialCryptoError(Exception):
    """Base class for every failure raised by this module."""


class CipherConfigurationError(CredentialCryptoError):
    """The vault is misconfigured: a bad key, a bad nonce size, a refused backend.

    Raised at load or startup rather than at first use, so a deployment with an unusable
    key fails before it has accepted a single credential.
    """


class DecryptionError(CredentialCryptoError):
    """Authentication failed.

    Deliberately carries no detail. Whether the tag was wrong, the associated data did
    not match, or the blob was truncated is not something a caller may distinguish —
    and it is certainly not something to put in a response.
    """

    def __init__(self) -> None:
        super().__init__("credential could not be decrypted")


# --------------------------------------------------------------------------- #
# Associated data
# --------------------------------------------------------------------------- #


def _validate_names(provider: str, field_name: str) -> None:
    if not _PROVIDER_PATTERN.match(provider):
        raise CipherConfigurationError("provider name is not a legal credential provider")
    if not _FIELD_PATTERN.match(field_name):
        raise CipherConfigurationError("field name is not a legal credential field")


def build_associated_data(
    organization_id: uuid.UUID, provider: str, field_name: str, key_version: int
) -> bytes:
    """Bind a ciphertext to exactly one tenant, provider, field and key version.

    GCM authenticates this value without encrypting it. Changing any component makes
    decryption fail, which is what stops a stolen blob from being replayed into another
    organization's row or another field of the same row.
    """
    _validate_names(provider, field_name)
    if key_version < 1:
        raise CipherConfigurationError("key_version must be a positive integer")
    return _SEPARATOR.join(
        (
            _AAD_DOMAIN,
            str(organization_id).encode("ascii"),
            provider.encode("ascii"),
            field_name.encode("ascii"),
            str(key_version).encode("ascii"),
        )
    )


def build_fingerprint_context(
    organization_id: uuid.UUID, provider: str, field_name: str
) -> bytes:
    """Domain separation for a fingerprint.

    The key version is deliberately absent: this value says *which credential* a
    fingerprint is for, and which key version currently holds the ciphertext has nothing
    to do with that. (The fingerprint still changes when the master key rotates, because
    the HMAC key is derived from the master key — see ``CredentialVault.rotate_key``.)

    The organization is present so that two tenants who happen to use the same
    third-party key do not produce the same fingerprint. A database reader must not be
    able to correlate customers that way.
    """
    _validate_names(provider, field_name)
    return _SEPARATOR.join(
        (
            _FINGERPRINT_DOMAIN,
            str(organization_id).encode("ascii"),
            provider.encode("ascii"),
            field_name.encode("ascii"),
        )
    )


# --------------------------------------------------------------------------- #
# Backend protocol
# --------------------------------------------------------------------------- #


@runtime_checkable
class CipherBackend(Protocol):
    """An authenticated cipher. The vault talks to nothing else.

    ``is_authenticated_aes`` exists so :func:`assert_cipher_backend_allowed` can refuse,
    at startup, anything that is not real AES. A backend that lies about this is a
    deliberate act, not an accident.
    """

    @property
    def name(self) -> str: ...

    @property
    def algorithm(self) -> str: ...

    @property
    def is_authenticated_aes(self) -> bool: ...

    def random_nonce(self) -> bytes: ...

    def encrypt(
        self, *, key: bytes, nonce: bytes, plaintext: bytes, associated_data: bytes
    ) -> bytes: ...

    def decrypt(
        self, *, key: bytes, nonce: bytes, ciphertext: bytes, associated_data: bytes
    ) -> bytes: ...


def _check_key_and_nonce(key: bytes, nonce: bytes) -> None:
    if len(key) != MASTER_KEY_BYTES:
        raise CipherConfigurationError("AES-256-GCM requires a 32-byte key")
    if len(nonce) != NONCE_BYTES:
        raise CipherConfigurationError("AES-256-GCM here requires a 96-bit nonce")


# --------------------------------------------------------------------------- #
# AES-256 block cipher (FIPS-197), encryption direction only
# --------------------------------------------------------------------------- #

# GCM never runs the block cipher backwards, so there is no inverse S-box and no
# InvSubBytes/InvMixColumns here. Less code is less to get wrong.
_SBOX = bytes.fromhex(
    "637c777bf26b6fc53001672bfed7ab76"
    "ca82c97dfa5947f0add4a2af9ca472c0"
    "b7fd9326363ff7cc34a5e5f171d83115"
    "04c723c31896059a071280e2eb27b275"
    "09832c1a1b6e5aa0523bd6b329e32f84"
    "53d100ed20fcb15b6acbbe394a4c58cf"
    "d0efaafb434d338545f9027f503c9fa8"
    "51a3408f929d38f5bcb6da2110fff3d2"
    "cd0c13ec5f974417c4a77e3d645d1973"
    "60814fdc222a908846eeb814de5e0bdb"
    "e0323a0a4906245cc2d3ac629195e479"
    "e7c8376d8dd54ea96c56f4ea657aae08"
    "ba78252e1ca6b4c6e8dd741f4bbd8b8a"
    "703eb5664803f60e613557b986c11d9e"
    "e1f8981169d98e949b1e87e9ce5528df"
    "8ca1890dbfe6426841992d0fb054bb16"
)
_RCON = (0x00, 0x01, 0x02, 0x04, 0x08, 0x10, 0x20, 0x40, 0x80, 0x1B, 0x36)

_AES_256_ROUNDS = 14
_AES_256_KEY_WORDS = 8

# xtime(a) = a * x in GF(2^8) with the AES reduction polynomial.
_XTIME = bytes(((b << 1) ^ 0x1B) & 0xFF if b & 0x80 else (b << 1) & 0xFF for b in range(256))


def _rot_word(word: int) -> int:
    return ((word << 8) & 0xFFFFFFFF) | (word >> 24)


def _sub_word(word: int) -> int:
    return (
        (_SBOX[(word >> 24) & 0xFF] << 24)
        | (_SBOX[(word >> 16) & 0xFF] << 16)
        | (_SBOX[(word >> 8) & 0xFF] << 8)
        | _SBOX[word & 0xFF]
    )


def _expand_key(key: bytes) -> list[int]:
    """FIPS-197 key expansion for AES-256: 60 words of round key material."""
    words = [int.from_bytes(key[i * 4 : i * 4 + 4], "big") for i in range(_AES_256_KEY_WORDS)]
    for i in range(_AES_256_KEY_WORDS, 4 * (_AES_256_ROUNDS + 1)):
        temp = words[i - 1]
        if i % _AES_256_KEY_WORDS == 0:
            temp = _sub_word(_rot_word(temp)) ^ (_RCON[i // _AES_256_KEY_WORDS] << 24)
        elif i % _AES_256_KEY_WORDS == 4:
            temp = _sub_word(temp)
        words.append(words[i - _AES_256_KEY_WORDS] ^ temp)
    return words


def _add_round_key(state: bytearray, words: list[int], round_index: int) -> None:
    for column in range(4):
        word = words[4 * round_index + column]
        offset = 4 * column
        state[offset] ^= (word >> 24) & 0xFF
        state[offset + 1] ^= (word >> 16) & 0xFF
        state[offset + 2] ^= (word >> 8) & 0xFF
        state[offset + 3] ^= word & 0xFF


def _sub_bytes(state: bytearray) -> None:
    for i in range(16):
        state[i] = _SBOX[state[i]]


def _shift_rows(state: bytearray) -> None:
    for row in range(1, 4):
        original = (state[row], state[row + 4], state[row + 8], state[row + 12])
        rotated = original[row:] + original[:row]
        state[row], state[row + 4], state[row + 8], state[row + 12] = rotated


def _mix_columns(state: bytearray) -> None:
    for column in range(4):
        i = 4 * column
        a0, a1, a2, a3 = state[i], state[i + 1], state[i + 2], state[i + 3]
        total = a0 ^ a1 ^ a2 ^ a3
        state[i] = a0 ^ total ^ _XTIME[a0 ^ a1]
        state[i + 1] = a1 ^ total ^ _XTIME[a1 ^ a2]
        state[i + 2] = a2 ^ total ^ _XTIME[a2 ^ a3]
        state[i + 3] = a3 ^ total ^ _XTIME[a3 ^ a0]


def _encrypt_block(words: list[int], block: bytes) -> bytes:
    state = bytearray(block)
    _add_round_key(state, words, 0)
    for round_index in range(1, _AES_256_ROUNDS):
        _sub_bytes(state)
        _shift_rows(state)
        _mix_columns(state)
        _add_round_key(state, words, round_index)
    _sub_bytes(state)
    _shift_rows(state)
    _add_round_key(state, words, _AES_256_ROUNDS)
    return bytes(state)


# --------------------------------------------------------------------------- #
# GCM mode (NIST SP 800-38D)
# --------------------------------------------------------------------------- #

_GHASH_R = 0xE1 << 120
_MASK_128 = (1 << 128) - 1


def _gf_multiply(x: int, y: int) -> int:
    """Multiply in GF(2^128) using GCM's bit-reflected convention."""
    product = 0
    value = y
    for bit in range(128):
        if (x >> (127 - bit)) & 1:
            product ^= value
        if value & 1:
            value = (value >> 1) ^ _GHASH_R
        else:
            value >>= 1
    return product


def _ghash(subkey: int, data: bytes) -> int:
    """GHASH over data that is already a whole number of 16-byte blocks."""
    accumulator = 0
    for offset in range(0, len(data), 16):
        block = int.from_bytes(data[offset : offset + 16], "big")
        accumulator = _gf_multiply(accumulator ^ block, subkey)
    return accumulator


def _pad_to_block(data: bytes) -> bytes:
    remainder = len(data) % 16
    return data if remainder == 0 else data + bytes(16 - remainder)


def _increment_counter(counter: int) -> int:
    """inc32: only the low 32 bits wrap, exactly as GCM specifies."""
    return (counter & ~0xFFFFFFFF) | ((counter + 1) & 0xFFFFFFFF)


def _gctr(words: list[int], initial_counter: int, data: bytes) -> bytes:
    if not data:
        return b""
    output = bytearray()
    counter = initial_counter
    for offset in range(0, len(data), 16):
        chunk = data[offset : offset + 16]
        keystream = _encrypt_block(words, (counter & _MASK_128).to_bytes(16, "big"))
        output.extend(byte ^ keystream[i] for i, byte in enumerate(chunk))
        counter = _increment_counter(counter)
    return bytes(output)


def _gcm_tag(
    words: list[int], subkey: int, j0: int, associated_data: bytes, ciphertext: bytes
) -> bytes:
    lengths = ((len(associated_data) * 8).to_bytes(8, "big") +
               (len(ciphertext) * 8).to_bytes(8, "big"))
    digest = _ghash(
        subkey,
        _pad_to_block(associated_data) + _pad_to_block(ciphertext) + lengths,
    )
    mask = _encrypt_block(words, j0.to_bytes(16, "big"))
    return bytes(a ^ b for a, b in zip(digest.to_bytes(16, "big"), mask, strict=True))


class PurePythonAesGcmBackend:
    """AES-256-GCM on the standard library.

    This is real AES-GCM — it is checked against the published GCM test vectors, and
    when ``cryptography`` is present the two backends produce identical bytes.

    What it is *not* is constant-time: the S-box is a table lookup, so an attacker able
    to observe this process's cache timings could in principle recover the master key.
    That attack needs local co-residency and a great many samples, and credential writes
    are rare, so it is an accepted risk for now — but it is the reason
    ``INTEGRATION_REQUEST.md`` asks for ``cryptography`` to be added to the dependency
    set, after which this backend stops being selected.
    """

    name: ClassVar[str] = "pure-python"
    algorithm: ClassVar[str] = AES_GCM_ALGORITHM
    is_authenticated_aes: ClassVar[bool] = True

    def random_nonce(self) -> bytes:
        return secrets.token_bytes(NONCE_BYTES)

    def encrypt(
        self, *, key: bytes, nonce: bytes, plaintext: bytes, associated_data: bytes
    ) -> bytes:
        _check_key_and_nonce(key, nonce)
        words = _expand_key(key)
        subkey = int.from_bytes(_encrypt_block(words, bytes(16)), "big")
        j0 = int.from_bytes(nonce + b"\x00\x00\x00\x01", "big")
        ciphertext = _gctr(words, _increment_counter(j0), plaintext)
        return ciphertext + _gcm_tag(words, subkey, j0, associated_data, ciphertext)

    def decrypt(
        self, *, key: bytes, nonce: bytes, ciphertext: bytes, associated_data: bytes
    ) -> bytes:
        _check_key_and_nonce(key, nonce)
        if len(ciphertext) < TAG_BYTES:
            raise DecryptionError
        body, tag = ciphertext[:-TAG_BYTES], ciphertext[-TAG_BYTES:]

        words = _expand_key(key)
        subkey = int.from_bytes(_encrypt_block(words, bytes(16)), "big")
        j0 = int.from_bytes(nonce + b"\x00\x00\x00\x01", "big")

        expected = _gcm_tag(words, subkey, j0, associated_data, body)
        if not hmac.compare_digest(expected, tag):
            raise DecryptionError
        return _gctr(words, _increment_counter(j0), body)


class LibraryAesGcmBackend:
    """AES-256-GCM from ``cryptography``. Preferred whenever it is importable."""

    name: ClassVar[str] = "cryptography"
    algorithm: ClassVar[str] = AES_GCM_ALGORITHM
    is_authenticated_aes: ClassVar[bool] = True

    def __init__(self) -> None:
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM

        self._aesgcm = AESGCM

    def random_nonce(self) -> bytes:
        return secrets.token_bytes(NONCE_BYTES)

    def encrypt(
        self, *, key: bytes, nonce: bytes, plaintext: bytes, associated_data: bytes
    ) -> bytes:
        _check_key_and_nonce(key, nonce)
        result: bytes = self._aesgcm(key).encrypt(nonce, plaintext, associated_data)
        return result

    def decrypt(
        self, *, key: bytes, nonce: bytes, ciphertext: bytes, associated_data: bytes
    ) -> bytes:
        _check_key_and_nonce(key, nonce)
        if len(ciphertext) < TAG_BYTES:
            raise DecryptionError
        try:
            result: bytes = self._aesgcm(key).decrypt(nonce, ciphertext, associated_data)
        except Exception as exc:
            # The library's message is generic, but collapsing it anyway keeps every
            # decryption failure indistinguishable to the caller.
            raise DecryptionError from exc
        return result


def select_cipher_backend() -> CipherBackend:
    """Prefer the hardened implementation; fall back to the standard-library one."""
    try:
        return LibraryAesGcmBackend()
    except ImportError:
        return PurePythonAesGcmBackend()


def assert_cipher_backend_allowed(backend: CipherBackend, *, environment: str) -> None:
    """Startup guard. Anything that is not authenticated AES is refused off-box.

    Local and test may run with a stand-in so that a developer without the dependency
    can still run the suite. Staging and production may not: a vault that is not really
    encrypting is worse than no vault, because it looks like one.
    """
    if backend.is_authenticated_aes and backend.algorithm == AES_GCM_ALGORITHM:
        return
    if environment in LOCAL_ENVIRONMENTS:
        return
    raise CipherConfigurationError(
        f"cipher backend {backend.name!r} is not authenticated AES-256-GCM and is "
        f"refused in environment {environment!r}"
    )


# --------------------------------------------------------------------------- #
# Master key
# --------------------------------------------------------------------------- #


def _hkdf_sha256(secret: bytes, *, info: bytes, length: int = 32) -> bytes:
    """HKDF (RFC 5869) on SHA-256, so one master key yields several unrelated keys."""
    prk = hmac.new(_HKDF_SALT, secret, hashlib.sha256).digest()
    output = bytearray()
    block = b""
    counter = 1
    while len(output) < length:
        block = hmac.new(prk, block + info + bytes([counter]), hashlib.sha256).digest()
        output.extend(block)
        counter += 1
    return bytes(output[:length])


@dataclass(frozen=True)
class MasterKey:
    """One version of the vault's master key, already split into purpose-specific keys.

    The raw configured value is not retained. Encryption and fingerprinting use
    independently derived keys, so recovering one would not hand over the other.
    """

    version: int
    aes_key: bytes = field(repr=False)
    fingerprint_key: bytes = field(repr=False)

    @classmethod
    def from_base64(cls, encoded: str | None, *, version: int) -> MasterKey:
        """Decode and validate a configured key, or fail loudly.

        Anything other than exactly 32 bytes of valid base64 is a configuration error.
        A 16-byte key would silently give AES-128 in a module that promises AES-256.
        """
        if version < 1:
            raise CipherConfigurationError("credential_key_version must be >= 1")
        if encoded is None or not encoded.strip():
            raise CipherConfigurationError(
                "credential encryption key is not configured; the credential vault "
                "cannot start without it"
            )
        try:
            raw = base64.b64decode(encoded.strip(), validate=True)
        except (binascii.Error, ValueError) as exc:
            raise CipherConfigurationError(
                "credential encryption key is not valid base64"
            ) from exc
        if len(raw) != MASTER_KEY_BYTES:
            raise CipherConfigurationError(
                f"credential encryption key must decode to exactly {MASTER_KEY_BYTES} "
                f"bytes, got {len(raw)}"
            )
        return cls(
            version=version,
            aes_key=_hkdf_sha256(raw, info=b"aes-256-gcm"),
            fingerprint_key=_hkdf_sha256(raw, info=b"fingerprint-hmac"),
        )

    def fingerprint(self, plaintext: bytes, *, context: bytes) -> str:
        """A non-reversible identifier for a secret, keyed by the master key.

        HMAC rather than a bare digest: a customer id or a short key has far too little
        entropy to survive an unkeyed hash in a stolen database.
        """
        return hmac.new(
            self.fingerprint_key, context + _SEPARATOR + plaintext, hashlib.sha256
        ).hexdigest()

    def __repr__(self) -> str:
        return f"<MasterKey version={self.version} REDACTED>"

    __str__ = __repr__


def load_master_key(settings: Settings) -> MasterKey:
    """Build the current master key from configuration, or refuse to start."""
    configured = settings.credential_encryption_key
    return MasterKey.from_base64(
        configured.get_secret_value() if configured is not None else None,
        version=settings.credential_key_version,
    )


def vault_is_configured(settings: Settings) -> bool:
    """Whether a master key is present at all."""
    return settings.credential_encryption_key is not None


def assert_vault_startup_ready(settings: Settings) -> None:
    """Call once during application startup.

    Outside local and test, a missing or malformed master key is fatal: a credential
    vault that quietly degrades is worse than one that will not boot.

    In local and test an absent key means the vault is simply **not configured**, which
    is the same first-class state VEO uses for a provider with no credential. Startup
    proceeds, the vault endpoints refuse writes, and nothing pretends to be encrypted.
    Making a key mandatory here would mean the API could not boot for anyone who is not
    working on credentials — and the usual response to that is a committed dummy key,
    which is how a real one eventually gets committed too.

    A key that is *present but malformed* is always fatal, in every environment.
    """
    if vault_is_configured(settings) or settings.environment not in {"local", "test"}:
        load_master_key(settings)

    assert_cipher_backend_allowed(
        select_cipher_backend(), environment=settings.environment
    )
