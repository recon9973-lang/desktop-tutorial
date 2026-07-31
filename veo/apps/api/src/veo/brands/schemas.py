"""브랜드 식별 요청·응답.

여기서 받는 값 하나하나가 **측정이 되느냐 마느냐**를 가른다. 그래서 설명 문구가
"이 필드는 무엇이다" 가 아니라 "이걸 안 넣으면 어떻게 되느냐" 로 적혀 있다 — 등록
화면에서 사람이 읽고 판단할 문장이기 때문이다.
"""

from __future__ import annotations

import uuid
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

_STRICT = ConfigDict(extra="forbid", frozen=True)
_FROZEN = ConfigDict(frozen=True)

NonBlank = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]


class BrandDeclareRequest(BaseModel):
    model_config = _STRICT

    display_name: NonBlank = Field(
        description="AI 답변에 나올 법한 **정식 상호**입니다. 간판에 적힌 그대로."
    )
    is_own_brand: bool = Field(
        default=False,
        description="자사 브랜드는 프로젝트당 하나입니다. 나머지는 비교 대상입니다.",
    )
    homepage_url: str | None = Field(
        default=None, description="비교 대상일 때의 홈페이지. 같은 주소는 두 번 등록되지 않습니다."
    )
    aliases: list[str] = Field(
        default_factory=list,
        description="줄임말·옛 상호·영문 표기처럼 답변이 쓸 수 있는 다른 이름입니다.",
    )
    own_domains: list[str] = Field(
        default_factory=list,
        description="자사 도메인입니다. **도메인은 동명 업체와 공유되지 않으므로**, 답변이 "
        "이 주소를 근거로 인용하면 그 언급은 그것만으로 확정됩니다.",
    )
    address_terms: list[str] = Field(
        default_factory=list,
        description="행정동·역명·랜드마크처럼 AI 답변이 실제로 말할 만한 소재지 표현입니다. "
        "**소재지만으로는 확정에 이르지 못합니다** — 흔한 상호라면 전화번호가 필요합니다.",
    )
    phone_numbers: list[str] = Field(
        default_factory=list,
        description="대표번호입니다. 흔한 상호를 확정선 위로 올리는 **가장 효과가 큰 한 "
        "가지**입니다. 저장할 때 숫자만 남겨 정규화하므로 02-1234-5678 로 넣어도 됩니다.",
    )
    distinguishing_terms: list[str] = Field(
        default_factory=list,
        description="이 업체만의 표현입니다 — 대표 시술, 남다른 진료시간, 원장 성함 등.",
    )
    name_is_ambiguous: bool | None = Field(
        default=None,
        description="비워 두면 VEO가 이름만 보고 판단합니다. 여러 업체가 함께 쓰는 이름인 "
        "것을 아는 경우에만 직접 지정하십시오.",
    )


class BrandUpdateRequest(BaseModel):
    """빠뜨린 값을 채우는 용도. **식별자(`entity_key`)는 바뀌지 않습니다.**

    지난 관측이 그 값으로 이 브랜드를 가리키고 있어서, 바꾸면 과거와 현재가 다른
    브랜드처럼 갈라지고 추이가 조용히 끊깁니다.
    """

    model_config = _STRICT

    display_name: NonBlank | None = None
    aliases: list[str] | None = None
    own_domains: list[str] | None = None
    address_terms: list[str] | None = None
    phone_numbers: list[str] | None = None
    distinguishing_terms: list[str] | None = None
    name_is_ambiguous: bool | None = None
    is_active: bool | None = None


class BrandPayload(BaseModel):
    model_config = _FROZEN

    id: uuid.UUID
    entity_key: str
    display_name: str
    is_own_brand: bool
    aliases: list[str]
    own_domains: list[str]
    address_terms: list[str]
    phone_numbers: list[str]
    distinguishing_terms: list[str]
    identity_strength: str = Field(
        description="SUFFICIENT | PARTIAL | INSUFFICIENT — **측정이 되느냐**입니다. "
        "`INSUFFICIENT` 면 이 브랜드의 언급은 전부 검수 대기로 넘어갑니다."
    )
    name_is_generic: bool = Field(
        description="여러 업체가 함께 쓰는 이름인지. 그렇다면 이름만으로는 확정되지 않습니다."
    )
    gaps_ko: list[str] = Field(
        description="무엇을 더 넣으면 측정이 되는지 — **효과가 큰 순서**로."
    )


class ProjectBrandsPayload(BaseModel):
    """한 프로젝트의 브랜드 전부와, 지금 상태로 측정이 되는지."""

    model_config = _FROZEN

    ours: BrandPayload | None = Field(
        default=None,
        description="자사 브랜드입니다. **없으면 GEO 관측이 실행되지 않습니다** — 무엇을 "
        "찾아야 하는지 모르는 채로 돌리면 모든 답변이 '언급 없음'으로 기록되고, 그것은 "
        "측정이 아닙니다.",
    )
    competitors: list[BrandPayload] = Field(default_factory=list)
    can_observe: bool
    asymmetry_ko: list[str] = Field(
        default_factory=list,
        description="우리 쪽만 잘 적혀 있을 때의 경고입니다. 그 상태로 점유율을 계산하면 "
        "**실제 노출 차이가 아니라 등록 정보 차이**가 숫자로 나타납니다. 경고가 떠도 "
        "저장은 됩니다 — 막으면 경쟁사를 아예 등록하지 않게 되고, 그러면 점유율 자체가 "
        "사라집니다.",
    )
