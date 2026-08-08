"""브랜드 식별 API — 고객이 자기가 누구인지 말하는 경로.

이 경로가 없어서 `brand_identities` 는 **쓰는 코드가 0건**이었고, 등록이 없으면
`brand_target_for` 가 거부하므로 GEO 관측이 아예 돌지 않았다(0-E).

권한은 `competitor:*` 를 쓴다. 여기서 등록하는 것이 곧 비교 집합이고, 비교 집합이
바뀌면 점유율이 바뀌기 때문이다 — 같은 급의 행위다.
"""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from veo.api.deps import RequestId, ok
from veo.authz import Permission, Principal
from veo.brands import service
from veo.brands.schemas import (
    BrandDeclareRequest,
    BrandPayload,
    BrandUpdateRequest,
    IdentityCandidatePayload,
    ProjectBrandsPayload,
    SiteIdentityDraftPayload,
    SiteIdentityDraftRequest,
)
from veo.brands.service import SharedDomainError
from veo.brands.site_lookup import SiteIdentityReader
from veo.contracts.enums import ErrorCode
from veo.contracts.envelope import ApiResponse
from veo.db.session import get_db
from veo.organizations.errors import DuplicateResourceError, ReferenceNotFoundError
from veo.organizations.http import api_error, conflict, guard, not_found

router = APIRouter(prefix="/projects/{project_id}/brands", tags=["brands"])

Reader = Annotated[Principal, Depends(guard(Permission.COMPETITOR_READ))]
Writer = Annotated[Principal, Depends(guard(Permission.COMPETITOR_WRITE))]
DbSession = Annotated[Session, Depends(get_db)]


def _payload(view: service.BrandIdentityView) -> BrandPayload:
    record = view.record
    return BrandPayload(
        id=view.row.id,
        entity_key=record.entity_key,
        display_name=record.display_name,
        is_own_brand=record.is_own_brand,
        aliases=list(record.aliases),
        own_domains=list(record.own_domains),
        address_terms=list(record.address_terms),
        # 정규화된 형태를 돌려준다. 화면이 저장된 값을 그대로 보여줘야, 넣은 것과
        # 재는 데 쓰이는 것이 같다는 사실을 사람이 확인할 수 있다.
        phone_numbers=list(record.normalised_phones or record.phone_numbers),
        distinguishing_terms=list(record.distinguishing_terms),
        identity_strength=str(record.strength),
        name_is_generic=record.name_is_generic,
        gaps_ko=view.gaps_ko,
    )


def _brands_payload(brands: service.ProjectBrands) -> ProjectBrandsPayload:
    return ProjectBrandsPayload(
        ours=_payload(brands.ours) if brands.ours is not None else None,
        competitors=[_payload(view) for view in brands.competitors],
        can_observe=brands.can_observe,
        asymmetry_ko=brands.asymmetry_ko,
    )


@router.get(
    "",
    response_model=ApiResponse[ProjectBrandsPayload],
    summary="이 프로젝트가 선언한 브랜드 — 자사와 비교 대상",
    description=(
        "`identity_strength` 가 이 화면의 요점입니다. `INSUFFICIENT` 인 브랜드는 언급이 "
        "**전부 검수 대기로 넘어갑니다** — 흔한 상호를 이름만으로 이 업체라고 말할 수 "
        "없기 때문입니다.\n\n"
        "`asymmetry_ko` 는 우리 쪽만 잘 적혀 있을 때 뜹니다. 그 상태의 점유율은 실제 "
        "노출 차이가 아니라 등록 정보 차이를 보여줍니다."
    ),
)
def index(
    project_id: uuid.UUID,
    principal: Reader,
    request_id: RequestId,
    db: DbSession,
) -> ApiResponse[ProjectBrandsPayload]:
    try:
        brands = service.list_brands(db, principal, project_id)
    except ReferenceNotFoundError as exc:
        raise not_found(exc.message_ko) from exc
    return ok(_brands_payload(brands), request_id)


@router.post(
    "",
    response_model=ApiResponse[BrandPayload],
    status_code=status.HTTP_201_CREATED,
    summary="브랜드를 선언한다 (자사 또는 비교 대상)",
    description=(
        "**전화번호가 가장 효과가 큽니다.** 흔한 상호는 이름만으로 확정되지 않고, "
        "소재지만으로도 확정선에 이르지 못합니다.\n\n"
        "비교 대상도 같은 필드로 등록합니다. 우리 쪽만 채우면 경쟁사 언급이 더 자주 "
        "검수 대기로 떨어져 분자에서 빠지고, **산술을 한 글자도 안 고치고** 우리 점유율이 "
        "오릅니다."
    ),
)
def declare(
    project_id: uuid.UUID,
    payload: BrandDeclareRequest,
    principal: Writer,
    request_id: RequestId,
    db: DbSession,
) -> ApiResponse[BrandPayload]:
    try:
        view = service.declare_brand(
            db,
            principal,
            project_id,
            display_name=payload.display_name,
            is_own_brand=payload.is_own_brand,
            aliases=payload.aliases,
            own_domains=payload.own_domains,
            address_terms=payload.address_terms,
            phone_numbers=payload.phone_numbers,
            distinguishing_terms=payload.distinguishing_terms,
            name_is_ambiguous=payload.name_is_ambiguous,
            homepage_url=payload.homepage_url,
        )
    except ReferenceNotFoundError as exc:
        raise not_found(exc.message_ko) from exc
    except SharedDomainError as exc:
        # 중복(409)이 아니라 입력 오류(422)다. 화면이 어느 칸을 빨갛게 칠할지 알아야
        # 하므로 코드를 따로 둔다 — 설명은 화면이 아니라 모달이 한다.
        raise api_error(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            ErrorCode.VALIDATION_FAILED,
            exc.message_ko,
        ) from exc
    except DuplicateResourceError as exc:
        raise conflict(exc.message_ko) from exc
    db.commit()
    return ok(_payload(view), request_id)


@router.patch(
    "/{brand_id}",
    response_model=ApiResponse[BrandPayload],
    summary="빠뜨린 식별 정보를 채운다",
    description=(
        "**식별자는 바뀌지 않습니다.** 지난 관측이 그 값으로 이 브랜드를 가리키고 있어서, "
        "바꾸면 과거와 현재가 다른 브랜드처럼 갈라지고 추이가 조용히 끊깁니다."
    ),
)
def update(
    project_id: uuid.UUID,
    brand_id: uuid.UUID,
    payload: BrandUpdateRequest,
    principal: Writer,
    request_id: RequestId,
    db: DbSession,
) -> ApiResponse[BrandPayload]:
    del project_id  # 경로에만 있다. 소유 검사는 조직 범위로 한다.
    try:
        view = service.update_brand(
            db,
            principal,
            brand_id,
            display_name=payload.display_name,
            aliases=payload.aliases,
            own_domains=payload.own_domains,
            address_terms=payload.address_terms,
            phone_numbers=payload.phone_numbers,
            distinguishing_terms=payload.distinguishing_terms,
            name_is_ambiguous=payload.name_is_ambiguous,
            is_active=payload.is_active,
        )
    except SharedDomainError as exc:
        raise api_error(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            ErrorCode.VALIDATION_FAILED,
            exc.message_ko,
        ) from exc
    except ReferenceNotFoundError as exc:
        raise not_found(exc.message_ko) from exc
    db.commit()
    return ok(_payload(view), request_id)


@router.post(
    "/identity-draft",
    response_model=ApiResponse[SiteIdentityDraftPayload],
    summary="홈페이지에서 식별 정보를 읽어 후보로 돌려준다",
    description=(
        "**아무것도 저장하지 않습니다.** 사람이 고른 값을 등록·수정 요청으로 다시 보내야 "
        "저장됩니다.\n\n"
        "자동으로 채우지 않는 이유는 하나입니다 — 식별 값이 하나 더해지면 확신도가 "
        "올라가고, 확정선을 넘으면 **사람 검수를 건너뜁니다.** 틀린 값을 자동으로 넣는 "
        "것은 틀린 판정을 검수 없이 확정시키는 일입니다.\n\n"
        "`source` 가 `DECLARED` 인 것만 `preselected` 가 `true` 입니다. 본문에서 찾은 "
        "값은 실측에서 오검출이 나왔으므로 사람이 직접 골라야 합니다.\n\n"
        "홈페이지를 읽지 못해도 오류가 아닙니다. 후보가 비고 `notes_ko` 에 사유가 "
        "담깁니다 — 사이트가 안 열리는 것은 등록을 막을 일이 아닙니다."
    ),
)
def identity_draft(
    project_id: uuid.UUID,
    payload: SiteIdentityDraftRequest,
    principal: Writer,
    request_id: RequestId,
    db: DbSession,
) -> ApiResponse[SiteIdentityDraftPayload]:
    # 프로젝트가 이 조직 것인지 확인한다. 확인하지 않으면 남의 프로젝트 번호를 붙여
    # **아무 주소나 우리 서버로 받아 보는 창구**가 된다.
    try:
        service.list_brands(db, principal, project_id)
    except ReferenceNotFoundError as exc:
        raise not_found(exc.message_ko) from exc

    draft = SiteIdentityReader().read(payload.url)
    return ok(
        SiteIdentityDraftPayload(
            url=draft.url,
            candidates=[
                IdentityCandidatePayload(
                    field=str(one.field),
                    value=one.value,
                    source=str(one.source),
                    preselected=one.preselected,
                    note_ko=one.note_ko,
                )
                for one in draft.candidates
            ],
            notes_ko=list(draft.notes_ko),
        ),
        request_id,
    )


__all__ = ["router"]
