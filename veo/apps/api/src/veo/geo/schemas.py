"""Request and response shapes for the GEO readiness endpoints.

The response is deliberately two blocks, not one. ``readiness`` carries the number and
nothing else; ``exposure`` carries the gate statuses and nothing else. A console can then
render "준비도 95점" and "노출 차단" in the same view without either fact swallowing the
other — which is the whole reason gates never touch the score.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

_STRICT = ConfigDict(extra="forbid")


# --------------------------------------------------------------------------- #
# Request
# --------------------------------------------------------------------------- #


class GeoDocumentInput(BaseModel):
    """One already-fetched document. This endpoint never fetches anything itself."""

    model_config = _STRICT

    url: str = Field(description="문서의 최종 URL입니다.")
    html: str = Field(description="수집된 원본 HTML입니다.")
    status: int = Field(default=200, ge=100, le=599)
    headers: dict[str, str] = Field(default_factory=dict)
    primary: bool = Field(default=False, description="진단 대상 문서인지 여부입니다.")


class GeoAnalysisRequest(BaseModel):
    model_config = _STRICT

    target_url: str = Field(description="진단할 URL입니다.")
    documents: list[GeoDocumentInput] = Field(
        min_length=1, description="이미 수집된 문서 목록입니다. 최소 한 건이 필요합니다."
    )
    robots_txt: str | None = Field(
        default=None, description="수집된 robots.txt 본문입니다. 읽지 못했다면 생략합니다."
    )
    sitemap_documents: dict[str, str] = Field(default_factory=dict)
    rendered_dom: dict[str, str] = Field(
        default_factory=dict,
        description="JavaScript 실행 후 DOM입니다. 원본 HTML과 구분해 보관합니다.",
    )
    url_importance: dict[str, str] = Field(default_factory=dict)
    provider_states: dict[str, str] = Field(default_factory=dict)
    provider_payloads: dict[str, Any] = Field(default_factory=dict)
    collected_at: datetime | None = None


# --------------------------------------------------------------------------- #
# Response
# --------------------------------------------------------------------------- #


class GeoScanRequest(BaseModel):
    """주소만 주면 VEO 가 직접 가져와 GEO 준비도를 채점한다.

    `GeoAnalysisRequest` 와 나란히 둔다. 저쪽은 **이미 수집된 자료**를 받는 계약이라
    수집기를 따로 돌리는 파이프라인이 쓰고, 이쪽은 사람이 콘솔에서 주소 하나를 넣는
    경우를 위한 것이다. 같은 명세, 같은 수집기, 같은 결과 형식이다.

    SEO 진단과 **같은 수집 경로**를 쓴다. 한 번 가져온 것으로 둘 다 잴 수 있어야 대상
    사이트에 두 번 요청하지 않는다. 다만 재는 재료가 같다고 해서 두 점수를 합치지는
    않는다(ADR 0003).
    """

    model_config = _STRICT

    target_url: str = Field(min_length=1, description="진단할 사이트의 대표 주소입니다.")
    urls: list[str] = Field(
        default_factory=list,
        description="반드시 함께 볼 페이지 주소입니다.",
    )
    discover: bool = Field(
        default=True,
        description=(
            "사이트맵과 내부 링크를 따라 VEO 가 스스로 페이지를 찾을지 여부입니다. "
            "끄면 대표 주소와 `urls` 만 봅니다 — 사이트 전체를 봐야 판정되는 항목은 "
            "그때 측정 불가로 남고, 그 배점은 분모에 그대로 남습니다."
        ),
    )
    max_urls: int | None = Field(
        default=None,
        ge=1,
        le=500,
        description=(
            "이번 진단에서 가져올 최대 페이지 수입니다. 대상 사이트에 보내는 요청 수를 "
            "그대로 정하는 값이므로 함부로 올리지 않습니다."
        ),
    )
    locale: str = "ko-KR"


class GeoCategoryPayload(BaseModel):
    model_config = _STRICT

    category_id: str
    name_ko: str
    weight: float
    status: Literal["SCORED", "NOT_APPLICABLE", "UNKNOWN"]
    score: float | None
    coverage: float
    confidence: float
    failing_check_ids: list[str]
    unknown_check_ids: list[str]
    not_applicable_check_ids: list[str]


class GeoReadinessBlock(BaseModel):
    """The number, and only the number."""

    model_config = _STRICT

    spec_id: str
    spec_version: str
    spec_checksum: str
    status: Literal["SCORED", "NOT_APPLICABLE", "UNKNOWN"]
    score: float | None
    band_id: str | None
    band_label_ko: str | None
    coverage: float
    confidence: float
    categories: list[GeoCategoryPayload]


class GeoGatePayload(BaseModel):
    model_config = _STRICT

    gate_id: str
    status_code: str
    label_ko: str
    description_ko: str | None
    triggered_by: list[str]


class GeoExposureBlock(BaseModel):
    """The exposure status, and only the exposure status."""

    model_config = _STRICT

    blocked: bool
    status_codes: list[str]
    gates: list[GeoGatePayload]


class GeoIssuePayload(BaseModel):
    model_config = _STRICT

    check_id: str
    title_ko: str
    summary_ko: str
    remediation_ko: str
    remediation_owner: str
    business_impact_ko: str
    affected_urls: list[str]
    evidence_ids: list[str]
    fix_example: str | None = None
    reverification_note_ko: str = ""


class GeoEvidencePayload(BaseModel):
    model_config = _STRICT

    evidence_id: str
    kind: str
    url: str | None
    content_hash: str
    collected_at: datetime
    excerpt: str


class GeoCheckPayload(BaseModel):
    model_config = _STRICT

    check_id: str
    title_ko: str
    status: str
    confidence_level: str | None
    note_ko: str | None
    evidence_ids: list[str]


class GeoReadinessPayload(BaseModel):
    model_config = _STRICT

    target_url: str
    readiness: GeoReadinessBlock
    exposure: GeoExposureBlock
    summary_ko: str
    scope_notice_ko: str
    checks: list[GeoCheckPayload]
    issues: list[GeoIssuePayload]
    evidence: list[GeoEvidencePayload]
    notes_ko: list[str]


class GeoSpecCategoryPayload(BaseModel):
    model_config = _STRICT

    id: str
    name_ko: str
    weight: float
    check_ids: list[str]


class GeoSpecPayload(BaseModel):
    model_config = _STRICT

    spec_id: str
    version: str
    checksum: str
    status: str
    score_meaning_ko: str
    check_count: int
    categories: list[GeoSpecCategoryPayload]
    gate_status_codes: list[str]


__all__ = [
    "GeoAnalysisRequest",
    "GeoCategoryPayload",
    "GeoCheckPayload",
    "GeoDocumentInput",
    "GeoEvidencePayload",
    "GeoExposureBlock",
    "GeoGatePayload",
    "GeoIssuePayload",
    "GeoReadinessBlock",
    "GeoReadinessPayload",
    "GeoScanRequest",
    "GeoSpecCategoryPayload",
    "GeoSpecPayload",
]
