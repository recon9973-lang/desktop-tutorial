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
    """한 영역의 판정.

    `contributes_to_score` 를 반드시 보십시오. 거짓이면 이 영역은 **애초에 점수의
    일부가 아닙니다.** 점수 안에 있는데 못 잰 영역과 화면에서 같게 그리면, 참고 항목이
    감점처럼 읽히거나 반대로 못 잰 것이 참고처럼 읽힙니다.
    """

    model_config = _STRICT

    category_id: str
    name_ko: str
    weight: float = Field(
        description=(
            "이 영역의 배점입니다. `contributes_to_score` 가 거짓이면 **이 배점은 "
            "분모에 들어가지 않습니다** — 참고용으로 원래 무게를 알려드리는 값입니다."
        )
    )
    contributes_to_score: bool = Field(
        default=True,
        description="점수에 반영되는 영역인가. 거짓이면 하단 참고 구역에 표시하십시오.",
    )
    outside_score_reason_ko: str | None = Field(
        default=None,
        description="점수 밖인 이유입니다. `contributes_to_score` 가 거짓일 때만 채워집니다.",
    )
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
    """한 항목의 판정과, **왜 그렇게 판정했는지**.

    필드 이름을 SEO 의 ``OutcomeSummary`` 와 맞춘다. 두 화면이 같은 부품을 쓰기 때문이다 —
    이름이 갈리면 화면도 두 벌이 되고, 두 벌이 되면 한쪽만 고쳐지는 날이 온다.

    영역·심각도·담당은 발행 명세에서 가져오고, 관측값은 수집기가 이미 담아 둔 것을 그대로
    흘려보낸다. 예전에는 상태와 제목만 실어서, 화면이 "그렇게 판정했다" 고만 말하고 근거를
    보여줄 수 없었다.
    """

    model_config = _STRICT

    check_id: str
    title_ko: str
    #: 명세가 정한 영역. 화면이 항목을 영역별로 묶는 근거다.
    category_id: str = ""
    category_name_ko: str = ""
    remediation_owner: str = "DEVELOPER"
    status: str
    confidence_level: str | None
    note_ko: str | None
    evidence_ids: list[str]
    #: 수집기가 실제로 본 값. 판정을 내리지 못했으면 ``None``.
    observed: Any = None


class GeoImprovementPayload(BaseModel):
    """고치면 얼마나 오르는가 — 위에서부터 처리하면 점수가 가장 빨리 오른다.

    ``gain_points`` 는 채점기가 실제 산식으로 계산한 값이다. 화면이 어림하지 않는다 —
    어림하면 고친 뒤의 실제 점수와 어긋나고, 그러면 우선순위 자체를 믿을 수 없게 된다.

    **무게 관련 값은 여기 없다.** 그것은 발행 명세가 정하고, 화면이 명세를 읽어 잇는다
    (`readCheckSeverities`). 이 패키지는 관측하고, 채점기가 낸 값을 그대로 옮길 뿐이다.
    """

    model_config = _STRICT

    check_id: str
    category_id: str
    title_ko: str
    gain_points: float
    #: 상한에 걸려 지금은 고쳐도 점수가 오르지 않는 상태. 이때 ``gain_points`` 는 0이다.
    blocked_by_cap: bool


class GeoLookupPayload(BaseModel):
    """참고 조회가 실제로 무엇을 보고 무엇을 버렸는가.

    **버린 건수를 함께 줍니다.** 조용히 빼면 "검색하면 많이 나오는데 보고서엔 몇 개
    없다" 가 설명되지 않고, 읽는 분은 저희가 못 찾았다고 이해하십니다.
    """

    model_config = _STRICT

    engine: str = Field(description="조회한 검색 서비스입니다. 지금은 네이버뿐입니다.")
    totals: dict[str, int] = Field(
        description="검색 종류별로 검색 서비스가 보고한 전체 건수입니다. 가져온 수와 다릅니다."
    )
    considered: int
    accepted: int = Field(description="이 사업자의 것으로 판단해 자료에 넣은 건수입니다.")
    rejected_as_another_business: int = Field(
        description=(
            "이름이 비슷한 **다른 업체**로 보여 제외한 건수입니다. 그대로 세면 없는 "
            "평판을 만들어 냅니다."
        )
    )
    unavailable: dict[str, str] = Field(
        description="조회하지 못한 검색 종류와 이유입니다. 비어 있어야 정상입니다."
    )


class GeoReadinessPayload(BaseModel):
    model_config = _STRICT

    target_url: str
    readiness: GeoReadinessBlock
    exposure: GeoExposureBlock
    summary_ko: str
    scope_notice_ko: str
    checks: list[GeoCheckPayload]
    #: 조치 우선순위 — 이득이 큰 것부터. 채점기가 낸 값을 그대로 싣는다.
    improvements: list[GeoImprovementPayload] = Field(default_factory=list)
    issues: list[GeoIssuePayload]
    evidence: list[GeoEvidencePayload]
    notes_ko: list[str]
    lookup: GeoLookupPayload | None = Field(
        default=None,
        description=(
            "참고 조회 결과입니다. 점수와는 무관하며, 하단 참고 구역에 표시합니다. "
            "조회하지 않았거나 못 했으면 `null` 입니다."
        ),
    )


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
    "GeoLookupPayload",
    "GeoReadinessBlock",
    "GeoReadinessPayload",
    "GeoScanRequest",
    "GeoSpecCategoryPayload",
    "GeoSpecPayload",
]
