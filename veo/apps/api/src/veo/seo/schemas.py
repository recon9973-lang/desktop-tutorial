"""Request and response shapes for ``/seo``.

The scan endpoint takes a crawl that has already happened. This package deliberately
does not fetch: the SSRF guard, the redirect policy and the size budgets live in
``veo.common.security`` and belong to one crawler, not to eight collectors. So the
worker crawls once through :class:`~veo.common.security.fetcher.SafeFetcher` and posts
the material here, which also means the endpoint can be exercised end to end from a
fixture with no network at all.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

_FROZEN = ConfigDict(frozen=True, extra="forbid")

ImportanceLiteral = Literal[
    "CONVERSION_OR_HOME",
    "CATEGORY_OR_HUB",
    "CONTENT_OR_PRODUCT",
    "TAG_OR_FILTER",
    "INTENTIONAL_NOINDEX",
]


class HopPayload(BaseModel):
    model_config = _FROZEN

    url: str
    status: int = Field(ge=100, le=599)
    location: str | None = None


class PagePayload(BaseModel):
    model_config = _FROZEN

    url: str = Field(min_length=1, description="리다이렉트를 모두 따른 최종 URL입니다.")
    status: int = Field(default=200, ge=100, le=599)
    importance: ImportanceLiteral = "CONTENT_OR_PRODUCT"
    html: str = Field(default="", description="크롤러가 받은 원본 HTML입니다.")
    rendered_dom: str | None = Field(
        default=None,
        description=(
            "자바스크립트 실행 후의 DOM입니다. 렌더러가 돌지 않았다면 비워 두십시오. "
            "비어 있으면 렌더링 비교 항목은 UNKNOWN이 되며, 일치한다고 가정하지 않습니다."
        ),
    )
    headers: dict[str, str] = Field(default_factory=dict)
    hops: list[HopPayload] = Field(default_factory=list)


class ScanRequest(BaseModel):
    model_config = _FROZEN

    target_url: str = Field(min_length=1)
    pages: list[PagePayload] = Field(min_length=1)
    locale: str = "ko-KR"
    primary_url: str | None = None
    robots_txt: str | None = Field(
        default=None,
        description=(
            "수집하지 못했다면 null로 두십시오. 빈 문자열은 '내용이 없는 파일'이라는 뜻입니다."
        ),
    )
    sitemaps: dict[str, str] = Field(default_factory=dict)
    provider_states: dict[str, str] = Field(default_factory=dict)
    provider_payloads: dict[str, Any] = Field(default_factory=dict)


class SiteScanRequest(BaseModel):
    """콘솔 진단 요청 — 주소만 주면 VEO 가 직접 가져와 채점한다.

    `ScanRequest` 와 나란히 두는 이유: 저쪽은 **이미 수집된 자료**를 채점하는 계약이라
    수집기를 따로 돌리는 파이프라인이 쓰고, 이쪽은 사람이 콘솔에서 주소 하나를 넣는
    경우를 위한 것이다. 둘은 같은 엔진과 같은 명세로 채점하며, 결과 형식도 같다.
    """

    model_config = _FROZEN

    target_url: str = Field(min_length=1, description="진단할 사이트의 대표 주소입니다.")
    site_id: uuid.UUID | None = Field(
        default=None,
        description=(
            "등록된 사이트에 결과를 남기려면 지정합니다. 비워 두면 채점은 동일하게 "
            "수행하지만 **아무것도 저장하지 않습니다** — 영업 단계의 간편 진단이 그 경우입니다."
        ),
    )
    urls: list[str] = Field(
        default_factory=list,
        description=(
            "함께 볼 페이지 주소입니다. 비워 두면 대표 주소 한 장만 봅니다. "
            "내부 링크·중복 메타데이터처럼 사이트를 봐야 판정되는 항목은 "
            "페이지가 한 장뿐이면 측정 불가로 남습니다."
        ),
    )
    locale: str = "ko-KR"


class ImprovementSummary(BaseModel):
    """고치면 얼마나 오르는가 — 위에서부터 처리하면 점수가 가장 빨리 오른다.

    `gain_points` 는 채점기가 실제 산식으로 계산한 값이다. 화면이 따로 어림하지 않는다 —
    어림하면 고친 뒤의 실제 점수와 어긋나고, 그러면 우선순위 자체를 믿을 수 없게 된다.
    """

    model_config = _FROZEN

    check_id: str
    category_id: str
    title_ko: str
    #: 이 항목을 통과로 바꿨을 때 전체 점수가 오르는 폭.
    gain_points: float
    #: 상한에 걸려 지금은 고쳐도 점수가 오르지 않는 상태. 이때 `gain_points` 는 0이다.
    blocked_by_cap: bool
    severity: str
    remediation_owner: str


class ScanHistoryEntry(BaseModel):
    """이력 한 줄. 추이 그래프의 점 하나가 된다."""

    model_config = _FROZEN

    scan_run_id: uuid.UUID
    started_at: datetime
    finished_at: datetime | None
    status: str
    urls_collected: int
    score: float | None
    band_id: str | None
    coverage: float
    confidence: float
    #: 그때 적용된 명세. 버전이 다른 두 점수를 나란히 비교하면 안 된다는 표시이기도 하다.
    spec_version: str
    spec_checksum: str
    #: 실행한 사람. 계정이 지워졌거나 예약 실행이면 비어 있다 — 기록 자체는 남는다.
    requested_by_name: str | None


class ScanHistoryPayload(BaseModel):
    model_config = _FROZEN

    site_id: uuid.UUID
    entries: list[ScanHistoryEntry]


# --------------------------------------------------------------------------- #
# Responses
# --------------------------------------------------------------------------- #


class CheckCatalogueEntry(BaseModel):
    model_config = _FROZEN

    id: str
    title_ko: str
    title_en: str
    category_id: str
    category_name_ko: str
    severity: str
    scope: str
    remediation_owner: str
    applicability_ko: str | None
    evidence_required: list[str]
    engine_scope: list[str]
    collector: str
    requires_provider: bool


class CheckCataloguePayload(BaseModel):
    model_config = _FROZEN

    spec_id: str
    spec_version: str
    spec_checksum: str
    checks: list[CheckCatalogueEntry]


class CategorySummary(BaseModel):
    model_config = _FROZEN

    category_id: str
    name_ko: str
    weight: float
    status: str
    score: float | None
    coverage: float
    confidence: float
    not_applicable_check_ids: list[str]
    unknown_check_ids: list[str]
    failing_check_ids: list[str]


class CapSummary(BaseModel):
    model_config = _FROZEN

    cap_id: str
    max_overall_score: float
    reason_ko: str
    release_condition_ko: str
    triggered_by: list[str]


class ScoreSummary(BaseModel):
    model_config = _FROZEN

    spec_id: str
    spec_version: str
    spec_checksum: str
    status: str
    score: float | None
    score_before_caps: float | None
    band_id: str | None
    coverage: float
    confidence: float
    is_rank_prediction: Literal[False]
    categories: list[CategorySummary]
    applied_caps: list[CapSummary]
    calculation_trace: dict[str, Any]


class OutcomeSummary(BaseModel):
    """한 항목의 판정과, **왜 그렇게 판정했는지**.

    식별자와 상태만 내보내면 화면은 `seo.onpage.heading_hierarchy` 라고 쓸 수밖에 없고,
    그 줄을 본 직원이 할 수 있는 일이 없다. 제목·영역·심각도는 발행 명세에서 가져오고,
    관측값은 수집기가 이미 담아 둔 것을 그대로 흘려보낸다.
    """

    model_config = _FROZEN

    check_id: str
    #: 명세가 정한 이름. 수집기가 정하게 두면 같은 항목의 이름이 수집기마다 달라진다.
    title_ko: str
    category_id: str
    category_name_ko: str
    severity: str
    remediation_owner: str
    #: 이 항목을 재려면 누가 움직여야 하는가 — SELF_SERVICE / CUSTOMER_GRANTED /
    #: PAID_PROVIDER. 뒤의 둘은 배점에서 빠지므로, 화면이 그 사실을 함께 알려야 한다.
    availability: str
    #: 왜 이 항목을 보는지. 명세의 근거 문장을 그대로 옮긴다.
    reference_ko: str | None
    status: str
    confidence: float | None
    confidence_level: str | None
    affected_weight: float
    evaluated_weight: float
    evidence_ids: list[str]
    note: str | None
    #: 수집기가 실제로 본 값. 페이지별 제목 길이, 어긋난 제목 단계, 막힌 크롤러 이름 —
    #: 화면의 "원인 상세" 가 여기서 나온다. 판정을 내리지 못했으면 ``None``.
    observed: Any = None


class UnknownCheckSummary(BaseModel):
    model_config = _FROZEN

    check_id: str
    category_id: str
    title_ko: str
    reason_ko: str


class IssueSummary(BaseModel):
    model_config = _FROZEN

    check_id: str
    title_ko: str
    summary_ko: str
    affected_urls: list[str]
    evidence_ids: list[str]
    remediation_ko: str
    remediation_owner: str
    business_impact_ko: str
    fix_example: str | None
    reverification_note_ko: str


class EvidenceSummary(BaseModel):
    model_config = _FROZEN

    evidence_id: str
    kind: str
    url: str | None
    collected_at: str
    content_hash: str
    excerpt: str


class ScanPayload(BaseModel):
    model_config = _FROZEN

    summary_ko: str
    score: ScoreSummary
    outcomes: list[OutcomeSummary]
    unknown_checks: list[UnknownCheckSummary]
    issues: list[IssueSummary]
    #: 조치 우선순위. 이득이 큰 것부터.
    improvements: list[ImprovementSummary] = Field(default_factory=list)
    evidence: list[EvidenceSummary]
    notes_ko: list[str]


__all__ = [
    "CapSummary",
    "CategorySummary",
    "CheckCatalogueEntry",
    "CheckCataloguePayload",
    "EvidenceSummary",
    "HopPayload",
    "IssueSummary",
    "OutcomeSummary",
    "PagePayload",
    "ScanPayload",
    "ScanRequest",
    "ScoreSummary",
    "UnknownCheckSummary",
]
