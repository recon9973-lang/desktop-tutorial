"""Request and response models for the credential endpoints.

The response types are the last line of defence. Even if every guard above them failed,
a secret still could not travel through :class:`CredentialFieldState`, because the model
has no attribute able to carry one:

* every field is an enum, a boolean, an integer, a timestamp, or a string constrained to
  a shape a credential cannot take — a 64-character lowercase hex fingerprint, a hint of
  at most four characters, an algorithm name from a fixed pattern;
* ``extra="forbid"`` means a stray ``model_dump`` key is rejected rather than serialised;
* the models are frozen, so a handler cannot decorate one with a secret on its way out.

Requests are the mirror image: :class:`StoreCredentialRequest` is the only model that
accepts a secret, it is typed :class:`~pydantic.SecretStr` so it cannot be echoed into a
validation error, and there is no response model that shares a field with it.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, SecretStr

from veo.contracts.enums import ProviderState
from veo.credentials.providers import (
    CredentialField,
    CredentialProvider,
    VerificationErrorCode,
)

__all__ = [
    "CredentialFieldState",
    "CredentialStateListPayload",
    "ProviderCredentialState",
    "StoreCredentialRequest",
    "VerificationPayload",
]

_STRICT = ConfigDict(extra="forbid", frozen=True)


class StoreCredentialRequest(BaseModel):
    """The one model that carries a secret, and only inbound.

    ``SecretStr`` renders as ``**********`` in every repr, log and serialisation, so a
    validation error or an unhandled exception on this request cannot echo the value
    back to the caller.
    """

    model_config = ConfigDict(extra="forbid")

    secret: SecretStr = Field(
        min_length=1,
        max_length=16_384,
        description=(
            "저장할 자격증명 값입니다. 저장 후에는 어떤 방법으로도 다시 조회할 수 없습니다."
        ),
    )


class CredentialFieldState(BaseModel):
    """State of one credential field. Structurally incapable of holding a secret."""

    model_config = _STRICT

    field: CredentialField = Field(description="자격증명 항목 이름.")
    is_configured: bool = Field(description="현재 사용 가능한 값이 저장되어 있는지 여부.")
    fingerprint: str | None = Field(
        default=None,
        min_length=64,
        max_length=64,
        pattern=r"^[0-9a-f]{64}$",
        description=(
            "값 자체를 드러내지 않고 '값이 바뀌었는지'만 확인할 수 있는 비가역 지문입니다."
        ),
    )
    display_hint: str | None = Field(
        default=None,
        max_length=4,
        description="화면 표시용 힌트(마지막 4자). 값이 짧으면 제공하지 않습니다.",
    )
    algorithm: str | None = Field(
        default=None,
        max_length=32,
        pattern=r"^[A-Z0-9-]{1,32}$",
        description="암호화 알고리즘.",
    )
    key_version: int | None = Field(default=None, ge=1, description="암호화에 사용된 키 버전.")
    created_at: datetime | None = None
    updated_at: datetime | None = None
    rotated_at: datetime | None = Field(
        default=None, description="값이 마지막으로 교체되거나 재암호화된 시각."
    )
    last_verified_at: datetime | None = None
    last_verification_error_code: VerificationErrorCode | None = Field(
        default=None,
        description=(
            "검증 실패 사유 코드입니다. 제공자가 돌려준 오류 문구는 자격증명을 그대로 "
            "포함하는 경우가 많아 저장하지도, 반환하지도 않습니다."
        ),
    )


class ProviderCredentialState(BaseModel):
    """One provider's connection state, in the same vocabulary as ``/api/providers``."""

    model_config = _STRICT

    provider: CredentialProvider
    state: ProviderState
    reason_ko: str = Field(description="상태에 대한 한국어 설명.")
    fields: tuple[CredentialFieldState, ...] = Field(
        default=(), description="이 제공자가 필요로 하는 항목별 상태."
    )


class CredentialStateListPayload(BaseModel):
    model_config = _STRICT

    providers: tuple[ProviderCredentialState, ...] = ()


class VerificationPayload(BaseModel):
    """The result of a verification: a machine code and the resulting state."""

    model_config = _STRICT

    provider: ProviderCredentialState
    verified: bool
    error_code: VerificationErrorCode | None = None
    reason_ko: str
    checked_at: datetime
