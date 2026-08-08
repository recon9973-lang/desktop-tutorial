"""HTTP surface for stored provider credentials.

**This router is mounted** — ``veo.api.app`` includes it at the API prefix
(``api/app.py``). It said "deliberately not mounted" until 2026-08-08; that line was
written before the integrator wired it up and then outlived the fact. A comment that
outlives its fact is worse than no comment: the next reader trusts it.

Two things it is still fair to say about how far this reaches:

* **The vault is not yet the source of truth for outbound calls.** Every provider call
  still reads deployment-wide environment variables through
  ``core.settings.get_provider_credentials``. The per-organization resolvers exist
  (``providers/*/credentials.py``'s ``*_from_vault``) and nothing in ``src`` calls them.
  Switching changes boot conditions, so it is an open decision — see
  ``keywords/INTEGRATION_REQUEST.md`` request #5.
* **The AI answer engines are not in this vault.** ``CredentialProvider`` covers five
  providers; ``ProviderCredentials.states()`` knows eight. Gemini, Perplexity and
  Anthropic have settings fields but no vault slot.

Four endpoints, and a conspicuous absence: there is no way to read a credential back.
That is not an oversight to be filled in later — the permission matrix has no
``credential:read`` and the vault has no method a handler could call to produce one.
What a router may show is what ``GET /credentials`` returns: which provider, which field,
configured or not, a fingerprint, a four-character hint, and some timestamps.

Two conventions inherited from the rest of the API:

* A row belonging to another organization is **404, never 403**. A 403 would confirm the
  credential exists, which is exactly the fact being protected.
* Korean messages follow ``api/routes/meta.py``: a disabled provider is a normal,
  reportable state, not an error.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, status
from sqlalchemy.orm import Session

from veo.api.deps import RequestId, ok
from veo.authz import (
    CurrentPrincipal,
    Permission,
    Principal,
    require,
)
from veo.contracts.enums import ErrorCode, ProviderState
from veo.contracts.envelope import ApiError, ApiResponse
from veo.core.settings import get_settings
from veo.credentials.cipher import load_master_key
from veo.credentials.providers import (
    CredentialField,
    CredentialProvider,
    VerificationErrorCode,
)
from veo.credentials.schemas import (
    CredentialFieldState,
    CredentialStateListPayload,
    ProviderCredentialState,
    StoreCredentialRequest,
    VerificationPayload,
)
from veo.credentials.vault import (
    CredentialNotFoundError,
    CredentialValidationError,
    CredentialVault,
)
from veo.credentials.vault import ProviderCredentialState as ProviderStateRecord
from veo.db.session import get_db

__all__ = ["get_vault", "router"]

router = APIRouter(tags=["credentials"])

_STATE_REASONS_KO: dict[ProviderState, str] = {
    ProviderState.ENABLED: "필요한 자격증명이 모두 저장되어 있어 연동이 가능합니다.",
    ProviderState.DISABLED_NO_CREDENTIAL: (
        "필요한 자격증명이 없어 비활성 상태입니다. 해당 제공자에 의존하는 검사는 실패가 "
        "아니라 '측정 불가'로 표시되며, VEO는 추정값을 실제 데이터처럼 표시하지 않습니다."
    ),
    ProviderState.DISABLED_BY_CONFIG: "설정에 의해 비활성화되어 있습니다.",
    ProviderState.DEGRADED: "응답이 불안정해 일부 결과가 누락될 수 있습니다.",
    ProviderState.CIRCUIT_OPEN: "연속 실패로 호출을 일시 차단했습니다.",
}

_VERIFICATION_REASONS_KO: dict[VerificationErrorCode, str] = {
    VerificationErrorCode.MISSING_FIELDS: "필요한 항목이 모두 저장되지 않았습니다.",
    VerificationErrorCode.DECRYPT_FAILED: (
        "저장된 값을 현재 암호화 키로 복호화하지 못했습니다. 값을 다시 저장해 주세요."
    ),
    VerificationErrorCode.PROVIDER_UNAUTHORIZED: "제공자가 자격증명을 거부했습니다.",
    VerificationErrorCode.PROVIDER_FORBIDDEN: "제공자에서 권한이 거부되었습니다.",
    VerificationErrorCode.PROVIDER_RATE_LIMITED: "제공자 호출 한도를 초과했습니다.",
    VerificationErrorCode.PROVIDER_UNAVAILABLE: "제공자에 연결할 수 없습니다.",
    VerificationErrorCode.UNKNOWN: (
        "검증에 실패했습니다. 자세한 사유는 서버 로그에서 확인하세요. 제공자 오류 문구는 "
        "자격증명을 그대로 포함하는 경우가 많아 응답에 포함하지 않습니다."
    ),
}
_VERIFIED_REASON_KO = "저장된 자격증명이 모두 정상적으로 확인되었습니다."


def get_vault(session: Annotated[Session, Depends(get_db)]) -> CredentialVault:
    """Build a vault for this request from the configured master key.

    A missing or malformed key raises at this point rather than half-way through a
    write. Call ``cipher.assert_vault_startup_ready`` during startup so a deployment
    with an unusable key never reaches a request at all.
    """
    return CredentialVault(session, master_key=load_master_key(get_settings()))


VaultDep = Annotated[CredentialVault, Depends(get_vault)]

ProviderPath = Annotated[
    CredentialProvider, Path(description="자격증명을 저장할 외부 제공자입니다.")
]
FieldPath = Annotated[
    CredentialField, Path(description="제공자 자격증명의 항목 이름입니다.")
]


def _error(status_code: int, code: ErrorCode, message: str) -> HTTPException:
    """Build the platform error envelope the application's handler expects."""
    return HTTPException(
        status_code=status_code,
        detail=ApiError.of(code, message).model_dump(mode="json"),
    )


def _not_found() -> HTTPException:
    """The single response for "not yours" and "not there".

    Cross-tenant access is a 404 on purpose. Returning 403 would tell the caller their
    token is valid but for another organization, which confirms that organization's
    credential exists.
    """
    return _error(
        status.HTTP_404_NOT_FOUND,
        ErrorCode.NOT_FOUND,
        "해당 제공자 자격증명을 찾을 수 없습니다.",
    )


def guard(*permissions: Permission) -> Callable[[Principal], Principal]:
    """Pass-through to ``authz.require``.

    ``require`` is the single source of truth for the permission check, and
    ``veo.api.app`` is the single source of truth for how a refusal is rendered.
    """
    # `veo.api.app` now registers an application-wide PermissionDeniedError handler that
    # renders the standard 403 envelope, so the failure is no longer translated here.
    # One definition of a 403, in one place.
    return require(*permissions)


def _to_schema(record: ProviderStateRecord) -> ProviderCredentialState:
    return ProviderCredentialState(
        provider=record.provider,
        state=record.state,
        reason_ko=_STATE_REASONS_KO[record.state],
        fields=tuple(
            CredentialFieldState(
                field=state.field,
                is_configured=state.is_configured,
                fingerprint=state.fingerprint if state.is_configured else None,
                display_hint=state.display_hint if state.is_configured else None,
                algorithm=state.algorithm if state.is_configured else None,
                key_version=state.key_version if state.is_configured else None,
                created_at=state.created_at,
                updated_at=state.updated_at,
                rotated_at=state.rotated_at,
                last_verified_at=state.last_verified_at,
                last_verification_error_code=state.last_verification_error_code,
            )
            for state in record.fields
        ),
    )


@router.get(
    "/credentials",
    response_model=ApiResponse[CredentialStateListPayload],
    summary="저장된 제공자 자격증명 연동 상태 조회",
    description=(
        "조직에 저장된 제공자 자격증명의 **상태만** 반환합니다. 저장된 값 자체는 어떤 "
        "방법으로도 조회할 수 없으며, 이 응답에는 값을 담을 수 있는 필드 자체가 없습니다. "
        "확인할 수 있는 것은 제공자·항목·설정 여부·지문·마지막 4자 힌트·시각뿐입니다. "
        "자격증명이 없는 제공자도 함께 표시해, 무엇이 비어 있는지 감추지 않습니다."
    ),
    dependencies=[Depends(guard(Permission.CREDENTIAL_READ_STATE))],
)
def list_credential_state(
    vault: VaultDep, principal: CurrentPrincipal, request_id: RequestId
) -> ApiResponse[CredentialStateListPayload]:
    records = vault.describe(principal=principal)
    payload = CredentialStateListPayload(
        providers=tuple(_to_schema(record) for record in records)
    )
    return ok(payload, request_id)


@router.put(
    "/credentials/{provider}/{field}",
    response_model=ApiResponse[ProviderCredentialState],
    summary="제공자 자격증명 저장 (쓰기 전용)",
    description=(
        "자격증명을 AES-256-GCM으로 암호화해 저장합니다. **저장 후에는 다시 조회할 수 "
        "없습니다.** 응답에는 저장 결과 상태만 담기며, 기존 값이 있으면 교체되고 이전 "
        "값은 어디에도 남지 않습니다. 값이 바뀌면 검증 결과도 함께 초기화됩니다."
    ),
    dependencies=[Depends(guard(Permission.CREDENTIAL_MANAGE))],
)
def store_credential(
    provider: ProviderPath,
    field: FieldPath,
    payload: StoreCredentialRequest,
    vault: VaultDep,
    principal: CurrentPrincipal,
    request_id: RequestId,
) -> ApiResponse[ProviderCredentialState]:
    try:
        vault.store(
            principal=principal, provider=provider, field=field, secret=payload.secret
        )
    except CredentialValidationError as exc:
        # ``exc`` is raised by this package and is built from the provider and field
        # names only; it never contains the submitted value.
        raise _error(
            status.HTTP_422_UNPROCESSABLE_ENTITY, ErrorCode.VALIDATION_FAILED, str(exc)
        ) from exc
    return ok(
        _to_schema(vault.describe_provider(principal=principal, provider=provider)),
        request_id,
    )


@router.delete(
    "/credentials/{provider}/{field}",
    response_model=ApiResponse[ProviderCredentialState],
    summary="제공자 자격증명 비활성화",
    description=(
        "저장된 자격증명을 비활성화하고 암호문을 즉시 삭제합니다. 되돌릴 수 없으며, "
        "다시 사용하려면 값을 새로 저장해야 합니다. 감사 목적으로 '무엇이 설정되어 "
        "있었는지'를 알 수 있도록 지문과 시각 기록은 남습니다. 다른 조직의 자격증명은 "
        "존재 사실을 확인해 주지 않기 위해 403이 아니라 404로 응답합니다."
    ),
    dependencies=[Depends(guard(Permission.CREDENTIAL_MANAGE))],
)
def deactivate_credential(
    provider: ProviderPath,
    field: FieldPath,
    vault: VaultDep,
    principal: CurrentPrincipal,
    request_id: RequestId,
) -> ApiResponse[ProviderCredentialState]:
    try:
        vault.deactivate(principal=principal, provider=provider, field=field)
    except CredentialNotFoundError as exc:
        raise _not_found() from exc
    except CredentialValidationError as exc:
        raise _error(
            status.HTTP_422_UNPROCESSABLE_ENTITY, ErrorCode.VALIDATION_FAILED, str(exc)
        ) from exc
    return ok(
        _to_schema(vault.describe_provider(principal=principal, provider=provider)),
        request_id,
    )


@router.post(
    "/credentials/{provider}/verify",
    response_model=ApiResponse[VerificationPayload],
    summary="제공자 자격증명 검증",
    description=(
        "저장된 자격증명이 완전하고 현재 키로 복호화되는지 확인하고 결과를 기록합니다. "
        "실패 사유는 기계 판독용 코드로만 남깁니다. 제공자가 돌려주는 오류 문구에는 "
        "자격증명이 그대로 포함되는 경우가 많아, 저장하지도 반환하지도 않습니다."
    ),
    dependencies=[Depends(guard(Permission.CREDENTIAL_MANAGE))],
)
def verify_credential(
    provider: ProviderPath,
    vault: VaultDep,
    principal: CurrentPrincipal,
    request_id: RequestId,
) -> ApiResponse[VerificationPayload]:
    try:
        current = vault.describe_provider(principal=principal, provider=provider)
    except CredentialValidationError as exc:
        raise _error(
            status.HTTP_422_UNPROCESSABLE_ENTITY, ErrorCode.VALIDATION_FAILED, str(exc)
        ) from exc
    if not any(state.is_configured for state in current.fields):
        # Nothing of ours is stored for this provider — indistinguishable from another
        # organization having stored one, which is the point.
        raise _not_found()

    result = vault.verify(principal=principal, provider=provider)
    payload = VerificationPayload(
        provider=_to_schema(result.provider),
        verified=result.verified,
        error_code=result.error_code,
        reason_ko=(
            _VERIFIED_REASON_KO
            if result.error_code is None
            else _VERIFICATION_REASONS_KO[result.error_code]
        ),
        checked_at=result.checked_at,
    )
    return ok(payload, request_id)
