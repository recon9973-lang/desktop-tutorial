"""Request and response models for ``/keywords``.

Every measured value is an *object*, not a bare number:

.. code-block:: json

    "monthly_pc_searches": {
      "value": null,
      "quality": "BELOW_PROVIDER_THRESHOLD",
      "source": "NAVER_SEARCH_AD",
      "upper_bound_exclusive": 10,
      "note_ko": "제공자가 보고 하한 미만으로 표시한 구간입니다(10 미만) …"
    }

That shape costs a few bytes and buys the one thing this product cannot do without: a
client physically cannot render the number without also having been handed its source and
its quality. A bare ``0`` in JSON is indistinguishable from a suppressed value; this is
not.

The DataLab trend carries an explicit ``unit`` of ``RELATIVE_INDEX_0_100`` and a Korean
note saying it is not a search volume, and no field in it is named as though it held one.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from veo.contracts.enums import DataSource, ProviderState, ValueQuality
from veo.keywords.opportunity import OpportunityResult
from veo.keywords.repository import (
    StoredKeywordList,
    StoredMetric,
    StoredRelated,
    StoredTrend,
)
from veo.keywords.service import (
    KeywordLookupResult,
    KeywordSnapshot,
    RecentKeywordsReport,
)
from veo.providers.naver.searchad import AverageMetric, SearchCount

_STRICT = ConfigDict(extra="forbid")

__all__ = [
    "KeywordListPayload",
    "KeywordListRequest",
    "KeywordLookupPayload",
    "KeywordLookupRequest",
    "KeywordMetricsPayload",
    "MeasuredCount",
    "MeasuredRatio",
    "OpportunityPayload",
    "ProviderBadge",
    "RecentKeywordsPayload",
    "RelatedKeywordPayload",
    "TrendPayload",
    "lookup_payload",
    "provider_badges",
    "recent_payload",
    "related_payload",
    "state_reason_ko",
]

#: The same vocabulary ``GET /api/providers`` uses, so an operator comparing the two
#: screens never has to translate.
_STATE_REASONS_KO: dict[ProviderState, str] = {
    ProviderState.ENABLED: "자격증명이 설정되어 실제 데이터를 조회합니다.",
    ProviderState.DISABLED_NO_CREDENTIAL: (
        "자격증명이 없어 비활성 상태입니다. 관련 수치는 실패가 아니라 '측정 불가'로 "
        "표시되며, VEO는 추정값을 실제 데이터처럼 표시하지 않습니다."
    ),
    ProviderState.DISABLED_BY_CONFIG: "설정에 의해 비활성화되어 있습니다.",
    ProviderState.DEGRADED: "응답이 불안정해 일부 수치가 '측정 불가'로 표시됩니다.",
    ProviderState.CIRCUIT_OPEN: "연속 실패로 호출을 일시 차단했습니다.",
}


def state_reason_ko(state: ProviderState) -> str:
    return _STATE_REASONS_KO[state]


class ProviderBadge(BaseModel):
    """One provider's state, shown rather than hidden — including when it is disabled."""

    model_config = _STRICT

    provider: str
    state: ProviderState
    reason_ko: str


class MeasuredCount(BaseModel):
    """An absolute count, or a stated reason there is none. Never a bare number."""

    model_config = _STRICT

    value: int | None
    quality: ValueQuality
    source: DataSource
    note_ko: str
    upper_bound_exclusive: int | None = None


class MeasuredRatio(BaseModel):
    """An average click count or CTR, with the same rules."""

    model_config = _STRICT

    value: float | None
    quality: ValueQuality
    source: DataSource
    note_ko: str


class KeywordMetricsPayload(BaseModel):
    model_config = _STRICT

    source: DataSource
    api_version: str | None
    collected_at: datetime
    age_seconds: int
    source_period: str | None
    raw_response_hash: str | None
    cache_hit: bool

    monthly_pc_searches: MeasuredCount
    monthly_mobile_searches: MeasuredCount
    monthly_total_searches: MeasuredCount

    avg_pc_clicks: MeasuredRatio
    avg_mobile_clicks: MeasuredRatio
    avg_pc_ctr: MeasuredRatio
    avg_mobile_ctr: MeasuredRatio

    competition_label: str | None
    competition_index: float | None = Field(
        default=None,
        description=(
            "네이버는 경쟁 정도를 라벨(compIdx)로 제공하며 0-100 지수를 제공하지 않습니다. "
            "VEO가 임의로 숫자를 만들지 않기 때문에 이 값은 항상 비어 있습니다."
        ),
    )
    ad_depth: int | None
    partial_reason_ko: str | None = None


class TrendPointPayload(BaseModel):
    model_config = _STRICT

    period_start: date
    relative_index: float


class TrendPayload(BaseModel):
    """DataLab relative interest. Deliberately carries no count-shaped field name."""

    model_config = _STRICT

    source: DataSource
    unit: str
    note_ko: str
    time_unit: str
    device: str
    period_start: date
    period_end: date
    collected_at: datetime
    age_seconds: int
    points: list[TrendPointPayload]


class OpportunityComponentPayload(BaseModel):
    model_config = _STRICT

    name: str
    weight: float
    value: float | None
    contribution: float | None
    source: DataSource
    note_ko: str
    unavailable_reason_ko: str | None = None


class OpportunityPayload(BaseModel):
    model_config = _STRICT

    source: DataSource
    formula_version: str
    score: float | None
    weighted_sum: float
    coverage: float
    freshness: float
    confidence: float
    components: list[OpportunityComponentPayload]
    missing_components: list[str]
    calculation_trace: dict[str, Any]
    disclosure_ko: str
    unavailable_reason_ko: str | None = None


class RelatedKeywordPayload(BaseModel):
    model_config = _STRICT

    seed_keyword: str
    related_keyword: str
    source: DataSource
    source_rank: int | None
    monthly_total_searches: MeasuredCount


class KeywordSnapshotPayload(BaseModel):
    model_config = _STRICT

    original_keyword: str
    normalized_keyword: str
    metrics: KeywordMetricsPayload | None = None
    trend: TrendPayload | None = None
    opportunity: OpportunityPayload | None = None
    related: list[RelatedKeywordPayload] = Field(default_factory=list)


class KeywordLookupPayload(BaseModel):
    model_config = _STRICT

    query_id: uuid.UUID | None
    project_id: uuid.UUID | None
    requested_at: datetime
    locale: str
    providers: list[ProviderBadge]
    keywords: list[KeywordSnapshotPayload]
    notices_ko: list[str]


class RecentKeywordEntryPayload(BaseModel):
    model_config = _STRICT

    normalized_keyword: str
    lookup_count: int
    last_requested_at: datetime


class RecentKeywordsPayload(BaseModel):
    # This docstring reaches the OpenAPI document, so it states what the payload *is*
    # rather than quoting the forbidden name — a contract test scans the document for
    # that string, and an example of it would be indistinguishable from a use of it.
    """VEO 자체 관측치입니다. 네이버가 제공하는 인기검색어 순위가 아닙니다."""

    model_config = _STRICT

    title_ko: str
    source: DataSource
    window_hours: int
    period_start: datetime
    period_end: datetime
    refreshed_at: datetime
    min_lookups: int
    entries: list[RecentKeywordEntryPayload]
    suppressed_count: int
    methodology_ko: str
    scope_ko: str
    de_identification_ko: str


class KeywordLookupRequest(BaseModel):
    model_config = _STRICT

    keywords: list[str] = Field(min_length=1, max_length=20)
    locale: str = "ko-KR"
    project_id: uuid.UUID | None = None
    include_trend: bool = True
    intent_fit: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="사업·페이지 목적 적합도(0~1). VEO가 추정하지 않고 호출자가 지정합니다.",
    )
    content_gap: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="콘텐츠 격차(0~1). VEO가 추정하지 않고 호출자가 지정합니다.",
    )


class KeywordListRequest(BaseModel):
    model_config = _STRICT

    project_id: uuid.UUID
    name: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=2000)
    keywords: list[str] = Field(min_length=1, max_length=1000)


class KeywordListUpdateRequest(BaseModel):
    model_config = _STRICT

    name: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=2000)
    keywords: list[str] = Field(min_length=1, max_length=1000)


class KeywordListPayload(BaseModel):
    model_config = _STRICT

    id: uuid.UUID
    project_id: uuid.UUID
    name: str
    description: str | None
    keywords: list[str]
    created_at: datetime | None = None
    updated_at: datetime | None = None


# --------------------------------------------------------------------------- #
# Builders
# --------------------------------------------------------------------------- #


def _age_seconds(collected_at: datetime, now: datetime) -> int:
    return max(0, int((now - collected_at).total_seconds()))


def _count(
    value: int | None,
    quality: ValueQuality,
    *,
    source: DataSource,
    upper_bound_exclusive: int | None = None,
) -> MeasuredCount:
    # Building the provider's own value object first is what keeps the customer-facing
    # note and the value/quality consistency rule in one place instead of two.
    reference = SearchCount(
        value=value,
        quality=quality,
        upper_bound_exclusive=upper_bound_exclusive,
        source=source,
    )
    return MeasuredCount(
        value=value,
        quality=quality,
        source=source,
        note_ko=reference.note_ko(),
        upper_bound_exclusive=upper_bound_exclusive,
    )


def _ratio(value: float | None, quality: ValueQuality) -> MeasuredRatio:
    reference = AverageMetric(value=value, quality=quality)
    return MeasuredRatio(
        value=value,
        quality=quality,
        source=DataSource.NAVER_SEARCH_AD,
        note_ko=reference.note_ko(),
    )


def metrics_payload(metric: StoredMetric, *, now: datetime) -> KeywordMetricsPayload:
    return KeywordMetricsPayload(
        source=metric.source,
        api_version=metric.api_version,
        collected_at=metric.collected_at,
        age_seconds=_age_seconds(metric.collected_at, now),
        source_period=metric.source_period,
        raw_response_hash=metric.raw_response_hash,
        cache_hit=metric.was_cache_hit,
        monthly_pc_searches=_count(
            metric.monthly_pc_searches,
            metric.monthly_pc_searches_quality,
            source=DataSource.NAVER_SEARCH_AD,
            upper_bound_exclusive=metric.monthly_pc_upper_bound_exclusive,
        ),
        monthly_mobile_searches=_count(
            metric.monthly_mobile_searches,
            metric.monthly_mobile_searches_quality,
            source=DataSource.NAVER_SEARCH_AD,
            upper_bound_exclusive=metric.monthly_mobile_upper_bound_exclusive,
        ),
        monthly_total_searches=_count(
            metric.monthly_total_searches,
            metric.monthly_total_searches_quality,
            source=DataSource.CALCULATED,
            upper_bound_exclusive=metric.monthly_total_upper_bound_exclusive,
        ),
        avg_pc_clicks=_ratio(metric.avg_pc_clicks, metric.avg_pc_clicks_quality),
        avg_mobile_clicks=_ratio(metric.avg_mobile_clicks, metric.avg_mobile_clicks_quality),
        avg_pc_ctr=_ratio(metric.avg_pc_ctr, metric.avg_pc_ctr_quality),
        avg_mobile_ctr=_ratio(metric.avg_mobile_ctr, metric.avg_mobile_ctr_quality),
        competition_label=metric.competition_label,
        competition_index=metric.competition_index,
        ad_depth=metric.ad_depth,
        partial_reason_ko=metric.partial_reason,
    )


def trend_payload(trend: StoredTrend, *, now: datetime) -> TrendPayload:
    return TrendPayload(
        source=trend.source,
        unit=trend.unit,
        note_ko=trend.index_basis_note_ko,
        time_unit=trend.time_unit,
        device=trend.device,
        period_start=trend.period_start,
        period_end=trend.period_end,
        collected_at=trend.collected_at,
        age_seconds=_age_seconds(trend.collected_at, now),
        points=[
            TrendPointPayload(
                period_start=point.period_start, relative_index=point.relative_index
            )
            for point in trend.points
        ],
    )


def opportunity_payload(result: OpportunityResult) -> OpportunityPayload:
    return OpportunityPayload(
        source=result.source,
        formula_version=result.formula_version,
        score=result.score,
        weighted_sum=result.weighted_sum,
        coverage=result.coverage,
        freshness=result.freshness,
        confidence=result.confidence,
        components=[
            OpportunityComponentPayload(
                name=component.name,
                weight=component.weight,
                value=component.value,
                contribution=component.contribution,
                source=component.source,
                note_ko=component.note_ko,
                unavailable_reason_ko=component.unavailable_reason_ko,
            )
            for component in result.components
        ],
        missing_components=list(result.missing_components),
        calculation_trace=dict(result.trace),
        disclosure_ko=result.disclosure_ko,
        unavailable_reason_ko=result.unavailable_reason_ko,
    )


def related_payload(row: StoredRelated) -> RelatedKeywordPayload:
    return RelatedKeywordPayload(
        seed_keyword=row.seed_keyword,
        related_keyword=row.related_keyword,
        source=row.source,
        source_rank=row.source_rank,
        monthly_total_searches=_count(
            row.monthly_total_searches, row.value_quality, source=DataSource.CALCULATED
        ),
    )


def _snapshot_payload(snapshot: KeywordSnapshot, *, now: datetime) -> KeywordSnapshotPayload:
    return KeywordSnapshotPayload(
        original_keyword=snapshot.original_keyword,
        normalized_keyword=snapshot.normalized_keyword,
        metrics=(
            None if snapshot.metrics is None else metrics_payload(snapshot.metrics, now=now)
        ),
        trend=None if snapshot.trend is None else trend_payload(snapshot.trend, now=now),
        opportunity=(
            None
            if snapshot.opportunity is None
            else opportunity_payload(snapshot.opportunity)
        ),
        related=[related_payload(row) for row in snapshot.related],
    )


def provider_badges(result: KeywordLookupResult) -> list[ProviderBadge]:
    return [
        ProviderBadge(
            provider="NAVER_SEARCH_AD",
            state=result.searchad_state,
            reason_ko=state_reason_ko(result.searchad_state),
        ),
        ProviderBadge(
            provider="NAVER_DATALAB",
            state=result.datalab_state,
            reason_ko=state_reason_ko(result.datalab_state),
        ),
    ]


def lookup_payload(result: KeywordLookupResult, *, now: datetime) -> KeywordLookupPayload:
    return KeywordLookupPayload(
        query_id=result.query_id,
        project_id=result.project_id,
        requested_at=result.requested_at,
        locale=result.locale,
        providers=provider_badges(result),
        keywords=[_snapshot_payload(snapshot, now=now) for snapshot in result.snapshots],
        notices_ko=list(result.notices_ko),
    )


def recent_payload(report: RecentKeywordsReport) -> RecentKeywordsPayload:
    return RecentKeywordsPayload(
        title_ko=report.title_ko,
        source=report.source,
        window_hours=report.window_hours,
        period_start=report.period_start,
        period_end=report.period_end,
        refreshed_at=report.refreshed_at,
        min_lookups=report.min_lookups,
        entries=[
            RecentKeywordEntryPayload(
                normalized_keyword=entry.normalized_keyword,
                lookup_count=entry.lookup_count,
                last_requested_at=entry.last_requested_at,
            )
            for entry in report.entries
        ],
        suppressed_count=report.suppressed_count,
        methodology_ko=report.methodology_ko,
        scope_ko=report.scope_ko,
        de_identification_ko=report.de_identification_ko,
    )


def list_payload(row: StoredKeywordList) -> KeywordListPayload:
    return KeywordListPayload(
        id=row.id,
        project_id=row.project_id,
        name=row.name,
        description=row.description,
        keywords=list(row.keywords),
        created_at=row.created_at,
        updated_at=row.updated_at,
    )
