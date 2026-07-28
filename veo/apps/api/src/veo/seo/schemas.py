"""Request and response shapes for ``/seo``.

The scan endpoint takes a crawl that has already happened. This package deliberately
does not fetch: the SSRF guard, the redirect policy and the size budgets live in
``veo.common.security`` and belong to one crawler, not to eight collectors. So the
worker crawls once through :class:`~veo.common.security.fetcher.SafeFetcher` and posts
the material here, which also means the endpoint can be exercised end to end from a
fixture with no network at all.
"""

from __future__ import annotations

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
    model_config = _FROZEN

    check_id: str
    status: str
    confidence: float | None
    confidence_level: str | None
    affected_weight: float
    evaluated_weight: float
    evidence_ids: list[str]
    note: str | None


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
