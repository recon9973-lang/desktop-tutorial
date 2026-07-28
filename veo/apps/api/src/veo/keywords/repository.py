"""Persistence for keyword lookups, trends, opportunities and lists.

The service talks to a :class:`KeywordRepository`, not to SQLAlchemy. That seam exists for
one reason beyond testability: the *storage shape* and the *provider shape* are different
on purpose, and something has to translate between them deliberately rather than by
attribute name. A ``SearchCount`` knows it is below the provider's reporting threshold; a
database column knows only that it is ``NULL``. The translation is here, in one place,
where the ``*_quality`` flag that carries the difference cannot be forgotten.

Two shortfalls of the fixed schema are handled here rather than hidden, and both are
written up in ``INTEGRATION_REQUEST.md``:

* ``keyword_metrics`` pairs a ``*_quality`` column with each *count*, but not with the
  click and CTR averages, and not with the calculated total. Those qualities are stored in
  a reserved ``_veo_derived`` block inside ``provider_raw`` — namespaced so it can never
  collide with a Naver key — and read back from there.
* ``keyword_queries`` has a single ``normalized_keyword``. A request for several keywords
  records its first keyword there, and every requested keyword gets its own
  ``keyword_metrics`` row, which is what the table's unique constraint anticipates.
"""

from __future__ import annotations

import uuid
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any, Protocol, final

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from veo.contracts.enums import DataSource, ProviderState, ValueQuality
from veo.db.models.keywords import (
    KeywordList,
    KeywordMetric,
    KeywordOpportunity,
    KeywordQuery,
    KeywordTrend,
    RelatedKeyword,
)

__all__ = [
    "DERIVED_QUALITY_KEY",
    "InMemoryKeywordRepository",
    "KeywordRepository",
    "RecentLookupRow",
    "SqlKeywordRepository",
    "StoredKeywordList",
    "StoredLookup",
    "StoredMetric",
    "StoredOpportunity",
    "StoredRelated",
    "StoredTrend",
    "StoredTrendPoint",
]

#: Namespaced so it cannot be mistaken for — or collide with — a field Naver returned.
DERIVED_QUALITY_KEY = "_veo_derived"


@final
@dataclass(frozen=True, slots=True)
class StoredMetric:
    """One ``keyword_metrics`` row, in the vocabulary the service reads."""

    normalized_keyword: str
    source: DataSource
    api_version: str | None
    collected_at: datetime
    source_period: str | None
    raw_response_hash: str | None
    was_cache_hit: bool

    monthly_pc_searches: int | None
    monthly_pc_searches_quality: ValueQuality
    monthly_mobile_searches: int | None
    monthly_mobile_searches_quality: ValueQuality
    monthly_total_searches: int | None
    monthly_total_searches_quality: ValueQuality

    avg_pc_clicks: float | None
    avg_pc_clicks_quality: ValueQuality
    avg_mobile_clicks: float | None
    avg_mobile_clicks_quality: ValueQuality
    avg_pc_ctr: float | None
    avg_pc_ctr_quality: ValueQuality
    avg_mobile_ctr: float | None
    avg_mobile_ctr_quality: ValueQuality

    competition_index: float | None
    competition_label: str | None
    ad_depth: int | None

    monthly_pc_upper_bound_exclusive: int | None = None
    monthly_mobile_upper_bound_exclusive: int | None = None
    monthly_total_upper_bound_exclusive: int | None = None

    provider_raw: Mapping[str, Any] = field(default_factory=dict)
    partial_reason: str | None = None


@final
@dataclass(frozen=True, slots=True)
class StoredRelated:
    seed_keyword: str
    related_keyword: str
    source: DataSource
    source_rank: int | None
    monthly_total_searches: int | None
    value_quality: ValueQuality


@final
@dataclass(frozen=True, slots=True)
class StoredTrendPoint:
    period_start: date
    relative_index: float


@final
@dataclass(frozen=True, slots=True)
class StoredTrend:
    """A DataLab series. Carries no field that could be read as a search count."""

    normalized_keyword: str
    source: DataSource
    time_unit: str
    device: str
    period_start: date
    period_end: date
    collected_at: datetime
    index_basis_note_ko: str
    unit: str
    points: tuple[StoredTrendPoint, ...]


@final
@dataclass(frozen=True, slots=True)
class StoredOpportunity:
    normalized_keyword: str
    formula_version: str
    source: DataSource
    demand: float | None
    trend: float | None
    intent_fit: float | None
    competition_inverse: float | None
    content_gap: float | None
    confidence: float
    opportunity_score: float | None
    calculation_trace: Mapping[str, Any]
    missing_components: tuple[str, ...]


@final
@dataclass(frozen=True, slots=True)
class StoredLookup:
    id: uuid.UUID
    organization_id: uuid.UUID
    project_id: uuid.UUID | None
    surface: str
    locale: str
    original_keyword: str
    normalized_keyword: str
    requested_at: datetime
    provider_state: ProviderState
    error_code: str | None
    metrics: tuple[StoredMetric, ...] = ()
    related: tuple[StoredRelated, ...] = ()
    trends: tuple[StoredTrend, ...] = ()
    opportunities: tuple[StoredOpportunity, ...] = ()


@final
@dataclass(frozen=True, slots=True)
class RecentLookupRow:
    """An aggregate over this organization's own lookups. No user is identified."""

    normalized_keyword: str
    lookup_count: int
    last_requested_at: datetime


@final
@dataclass(frozen=True, slots=True)
class StoredKeywordList:
    id: uuid.UUID
    organization_id: uuid.UUID
    project_id: uuid.UUID
    name: str
    description: str | None
    keywords: tuple[str, ...]
    created_at: datetime | None = None
    updated_at: datetime | None = None


class KeywordRepository(Protocol):
    """What the keyword service needs from storage, and nothing more."""

    def record_lookup(
        self,
        *,
        organization_id: uuid.UUID,
        project_id: uuid.UUID | None,
        surface: str,
        locale: str,
        original_keyword: str,
        normalized_keyword: str,
        requested_at: datetime,
        provider_state: ProviderState,
        error_code: str | None,
        metrics: Sequence[StoredMetric],
        related: Sequence[StoredRelated],
        trends: Sequence[StoredTrend],
        opportunities: Sequence[StoredOpportunity],
    ) -> uuid.UUID: ...

    def load_lookup(
        self, *, organization_id: uuid.UUID, query_id: uuid.UUID
    ) -> StoredLookup | None: ...

    def recent_lookups(
        self, *, organization_id: uuid.UUID, since: datetime, until: datetime, limit: int
    ) -> tuple[RecentLookupRow, ...]: ...

    def create_list(
        self,
        *,
        organization_id: uuid.UUID,
        project_id: uuid.UUID,
        name: str,
        description: str | None,
        keywords: Sequence[str],
    ) -> StoredKeywordList: ...

    def list_keyword_lists(
        self,
        *,
        organization_id: uuid.UUID,
        project_id: uuid.UUID | None,
        page: int,
        page_size: int,
    ) -> tuple[tuple[StoredKeywordList, ...], int]: ...

    def get_keyword_list(
        self, *, organization_id: uuid.UUID, list_id: uuid.UUID
    ) -> StoredKeywordList | None: ...

    def replace_keyword_list(
        self,
        *,
        organization_id: uuid.UUID,
        list_id: uuid.UUID,
        name: str,
        description: str | None,
        keywords: Sequence[str],
    ) -> StoredKeywordList | None: ...

    def delete_keyword_list(
        self, *, organization_id: uuid.UUID, list_id: uuid.UUID
    ) -> bool: ...


# --------------------------------------------------------------------------- #
# In memory
# --------------------------------------------------------------------------- #


class InMemoryKeywordRepository:
    """A repository for tests and for reasoning about the service in isolation.

    It is *not* a stand-in for the database in production code: nothing imports it from
    ``service.py`` or ``router.py``. It exists so the service's behaviour — especially
    what it does with no credential — can be asserted without a migration.
    """

    def __init__(self) -> None:
        self._lookups: dict[uuid.UUID, StoredLookup] = {}
        self._lists: dict[uuid.UUID, StoredKeywordList] = {}

    def record_lookup(
        self,
        *,
        organization_id: uuid.UUID,
        project_id: uuid.UUID | None,
        surface: str,
        locale: str,
        original_keyword: str,
        normalized_keyword: str,
        requested_at: datetime,
        provider_state: ProviderState,
        error_code: str | None,
        metrics: Sequence[StoredMetric],
        related: Sequence[StoredRelated],
        trends: Sequence[StoredTrend],
        opportunities: Sequence[StoredOpportunity],
    ) -> uuid.UUID:
        query_id = uuid.uuid4()
        self._lookups[query_id] = StoredLookup(
            id=query_id,
            organization_id=organization_id,
            project_id=project_id,
            surface=surface,
            locale=locale,
            original_keyword=original_keyword,
            normalized_keyword=normalized_keyword,
            requested_at=requested_at,
            provider_state=provider_state,
            error_code=error_code,
            metrics=tuple(metrics),
            related=tuple(related),
            trends=tuple(trends),
            opportunities=tuple(opportunities),
        )
        return query_id

    def load_lookup(
        self, *, organization_id: uuid.UUID, query_id: uuid.UUID
    ) -> StoredLookup | None:
        stored = self._lookups.get(query_id)
        if stored is None or stored.organization_id != organization_id:
            return None
        return stored

    def recent_lookups(
        self, *, organization_id: uuid.UUID, since: datetime, until: datetime, limit: int
    ) -> tuple[RecentLookupRow, ...]:
        counts: dict[str, list[Any]] = {}
        for stored in self._lookups.values():
            if stored.organization_id != organization_id:
                continue
            if not since <= stored.requested_at <= until:
                continue
            entry = counts.setdefault(stored.normalized_keyword, [0, stored.requested_at])
            entry[0] += 1
            entry[1] = max(entry[1], stored.requested_at)

        rows = [
            RecentLookupRow(
                normalized_keyword=keyword, lookup_count=count, last_requested_at=last
            )
            for keyword, (count, last) in counts.items()
        ]
        rows.sort(key=lambda row: (-row.lookup_count, row.normalized_keyword))
        return tuple(rows[:limit])

    def create_list(
        self,
        *,
        organization_id: uuid.UUID,
        project_id: uuid.UUID,
        name: str,
        description: str | None,
        keywords: Sequence[str],
    ) -> StoredKeywordList:
        created = StoredKeywordList(
            id=uuid.uuid4(),
            organization_id=organization_id,
            project_id=project_id,
            name=name,
            description=description,
            keywords=tuple(keywords),
        )
        self._lists[created.id] = created
        return created

    def list_keyword_lists(
        self,
        *,
        organization_id: uuid.UUID,
        project_id: uuid.UUID | None,
        page: int,
        page_size: int,
    ) -> tuple[tuple[StoredKeywordList, ...], int]:
        rows = [
            row
            for row in self._lists.values()
            if row.organization_id == organization_id
            and (project_id is None or row.project_id == project_id)
        ]
        rows.sort(key=lambda row: row.name)
        start = (page - 1) * page_size
        return tuple(rows[start : start + page_size]), len(rows)

    def get_keyword_list(
        self, *, organization_id: uuid.UUID, list_id: uuid.UUID
    ) -> StoredKeywordList | None:
        row = self._lists.get(list_id)
        if row is None or row.organization_id != organization_id:
            return None
        return row

    def replace_keyword_list(
        self,
        *,
        organization_id: uuid.UUID,
        list_id: uuid.UUID,
        name: str,
        description: str | None,
        keywords: Sequence[str],
    ) -> StoredKeywordList | None:
        existing = self.get_keyword_list(organization_id=organization_id, list_id=list_id)
        if existing is None:
            return None
        updated = StoredKeywordList(
            id=existing.id,
            organization_id=existing.organization_id,
            project_id=existing.project_id,
            name=name,
            description=description,
            keywords=tuple(keywords),
        )
        self._lists[list_id] = updated
        return updated

    def delete_keyword_list(self, *, organization_id: uuid.UUID, list_id: uuid.UUID) -> bool:
        if self.get_keyword_list(organization_id=organization_id, list_id=list_id) is None:
            return False
        del self._lists[list_id]
        return True


# --------------------------------------------------------------------------- #
# SQLAlchemy
# --------------------------------------------------------------------------- #


def _derived_block(metric: StoredMetric) -> dict[str, Any]:
    """Qualities and bounds the fixed schema has no column for."""
    return {
        "monthly_total_searches_quality": metric.monthly_total_searches_quality.value,
        "avg_pc_clicks_quality": metric.avg_pc_clicks_quality.value,
        "avg_mobile_clicks_quality": metric.avg_mobile_clicks_quality.value,
        "avg_pc_ctr_quality": metric.avg_pc_ctr_quality.value,
        "avg_mobile_ctr_quality": metric.avg_mobile_ctr_quality.value,
        "monthly_pc_upper_bound_exclusive": metric.monthly_pc_upper_bound_exclusive,
        "monthly_mobile_upper_bound_exclusive": metric.monthly_mobile_upper_bound_exclusive,
        "monthly_total_upper_bound_exclusive": metric.monthly_total_upper_bound_exclusive,
        "note_ko": (
            "이 블록은 네이버 응답이 아니라 VEO가 파생한 품질 표시입니다. "
            "전용 컬럼이 없는 항목의 품질을 잃지 않기 위해 함께 저장합니다."
        ),
    }


def _quality(value: Any, fallback: ValueQuality = ValueQuality.MISSING) -> ValueQuality:
    try:
        return ValueQuality(value)
    except ValueError:
        return fallback


class SqlKeywordRepository:
    """The production repository. One session per request, supplied by the caller."""

    def __init__(self, session: Session) -> None:
        self._session = session

    # ------------------------------------------------------------- lookups

    def record_lookup(
        self,
        *,
        organization_id: uuid.UUID,
        project_id: uuid.UUID | None,
        surface: str,
        locale: str,
        original_keyword: str,
        normalized_keyword: str,
        requested_at: datetime,
        provider_state: ProviderState,
        error_code: str | None,
        metrics: Sequence[StoredMetric],
        related: Sequence[StoredRelated],
        trends: Sequence[StoredTrend],
        opportunities: Sequence[StoredOpportunity],
    ) -> uuid.UUID:
        query = KeywordQuery(
            organization_id=organization_id,
            project_id=project_id,
            surface=surface,
            original_keyword=original_keyword,
            normalized_keyword=normalized_keyword,
            locale=locale,
            requested_at=requested_at,
            provider_state=provider_state.value,
            error_code=error_code,
        )
        self._session.add(query)
        self._session.flush()

        for metric in metrics:
            raw = dict(metric.provider_raw)
            raw[DERIVED_QUALITY_KEY] = _derived_block(metric)
            self._session.add(
                KeywordMetric(
                    organization_id=organization_id,
                    keyword_query_id=query.id,
                    normalized_keyword=metric.normalized_keyword,
                    source=metric.source.value,
                    api_version=metric.api_version,
                    collected_at=metric.collected_at,
                    source_period=metric.source_period,
                    raw_response_hash=metric.raw_response_hash,
                    was_cache_hit=metric.was_cache_hit,
                    monthly_pc_searches=metric.monthly_pc_searches,
                    monthly_pc_searches_quality=metric.monthly_pc_searches_quality.value,
                    monthly_mobile_searches=metric.monthly_mobile_searches,
                    monthly_mobile_searches_quality=(
                        metric.monthly_mobile_searches_quality.value
                    ),
                    monthly_total_searches=metric.monthly_total_searches,
                    avg_pc_clicks=metric.avg_pc_clicks,
                    avg_mobile_clicks=metric.avg_mobile_clicks,
                    avg_pc_ctr=metric.avg_pc_ctr,
                    avg_mobile_ctr=metric.avg_mobile_ctr,
                    competition_index=metric.competition_index,
                    competition_label=metric.competition_label,
                    ad_depth=metric.ad_depth,
                    provider_raw=raw,
                    partial_reason=metric.partial_reason,
                )
            )

        for row in related:
            self._session.add(
                RelatedKeyword(
                    organization_id=organization_id,
                    keyword_query_id=query.id,
                    seed_keyword=row.seed_keyword,
                    related_keyword=row.related_keyword,
                    source=row.source.value,
                    source_rank=row.source_rank,
                    monthly_total_searches=row.monthly_total_searches,
                    value_quality=row.value_quality.value,
                )
            )

        for trend in trends:
            for point in trend.points:
                self._session.add(
                    KeywordTrend(
                        organization_id=organization_id,
                        keyword_query_id=query.id,
                        normalized_keyword=trend.normalized_keyword,
                        source=trend.source.value,
                        period_start=point.period_start,
                        period_end=trend.period_end,
                        time_unit=trend.time_unit,
                        device=trend.device,
                        relative_index=point.relative_index,
                        index_basis_note_ko=trend.index_basis_note_ko,
                        collected_at=trend.collected_at,
                    )
                )

        for opportunity in opportunities:
            self._session.add(
                KeywordOpportunity(
                    organization_id=organization_id,
                    keyword_query_id=query.id,
                    normalized_keyword=opportunity.normalized_keyword,
                    formula_version=opportunity.formula_version,
                    source=opportunity.source.value,
                    demand=opportunity.demand,
                    trend=opportunity.trend,
                    intent_fit=opportunity.intent_fit,
                    competition_inverse=opportunity.competition_inverse,
                    content_gap=opportunity.content_gap,
                    confidence=opportunity.confidence,
                    opportunity_score=opportunity.opportunity_score,
                    calculation_trace=dict(opportunity.calculation_trace),
                    missing_components=list(opportunity.missing_components),
                )
            )

        self._session.commit()
        return query.id

    def load_lookup(
        self, *, organization_id: uuid.UUID, query_id: uuid.UUID
    ) -> StoredLookup | None:
        query = self._session.execute(
            select(KeywordQuery)
            .where(KeywordQuery.organization_id == organization_id)
            .where(KeywordQuery.id == query_id)
        ).scalar_one_or_none()
        if query is None:
            return None

        metric_rows = self._session.execute(
            select(KeywordMetric)
            .where(KeywordMetric.organization_id == organization_id)
            .where(KeywordMetric.keyword_query_id == query_id)
            .order_by(KeywordMetric.normalized_keyword)
        ).scalars()

        related_rows = self._session.execute(
            select(RelatedKeyword)
            .where(RelatedKeyword.organization_id == organization_id)
            .where(RelatedKeyword.keyword_query_id == query_id)
            .order_by(RelatedKeyword.source_rank)
        ).scalars()

        trend_rows = self._session.execute(
            select(KeywordTrend)
            .where(KeywordTrend.organization_id == organization_id)
            .where(KeywordTrend.keyword_query_id == query_id)
            .order_by(KeywordTrend.normalized_keyword, KeywordTrend.period_start)
        ).scalars()

        opportunity_rows = self._session.execute(
            select(KeywordOpportunity)
            .where(KeywordOpportunity.organization_id == organization_id)
            .where(KeywordOpportunity.keyword_query_id == query_id)
            .order_by(KeywordOpportunity.normalized_keyword)
        ).scalars()

        return StoredLookup(
            id=query.id,
            organization_id=query.organization_id,
            project_id=query.project_id,
            surface=query.surface,
            locale=query.locale,
            original_keyword=query.original_keyword,
            normalized_keyword=query.normalized_keyword,
            requested_at=query.requested_at,
            provider_state=ProviderState(query.provider_state),
            error_code=query.error_code,
            metrics=tuple(_metric_from_row(row) for row in metric_rows),
            related=tuple(_related_from_row(row) for row in related_rows),
            trends=_trends_from_rows(list(trend_rows)),
            opportunities=tuple(_opportunity_from_row(row) for row in opportunity_rows),
        )

    def recent_lookups(
        self, *, organization_id: uuid.UUID, since: datetime, until: datetime, limit: int
    ) -> tuple[RecentLookupRow, ...]:
        statement = (
            select(
                KeywordQuery.normalized_keyword,
                func.count().label("lookup_count"),
                func.max(KeywordQuery.requested_at).label("last_requested_at"),
            )
            .where(KeywordQuery.organization_id == organization_id)
            .where(KeywordQuery.requested_at >= since)
            .where(KeywordQuery.requested_at <= until)
            .group_by(KeywordQuery.normalized_keyword)
            .order_by(func.count().desc(), KeywordQuery.normalized_keyword)
            .limit(limit)
        )
        return tuple(
            RecentLookupRow(
                normalized_keyword=row.normalized_keyword,
                lookup_count=int(row.lookup_count),
                last_requested_at=row.last_requested_at,
            )
            for row in self._session.execute(statement)
        )

    # --------------------------------------------------------------- lists

    def create_list(
        self,
        *,
        organization_id: uuid.UUID,
        project_id: uuid.UUID,
        name: str,
        description: str | None,
        keywords: Sequence[str],
    ) -> StoredKeywordList:
        row = KeywordList(
            organization_id=organization_id,
            project_id=project_id,
            name=name,
            description=description,
            keywords=list(keywords),
        )
        self._session.add(row)
        self._session.commit()
        self._session.refresh(row)
        return _list_from_row(row)

    def list_keyword_lists(
        self,
        *,
        organization_id: uuid.UUID,
        project_id: uuid.UUID | None,
        page: int,
        page_size: int,
    ) -> tuple[tuple[StoredKeywordList, ...], int]:
        statement = select(KeywordList).where(KeywordList.organization_id == organization_id)
        if project_id is not None:
            statement = statement.where(KeywordList.project_id == project_id)

        total = (
            self._session.scalar(select(func.count()).select_from(statement.subquery())) or 0
        )
        rows = self._session.execute(
            statement.order_by(KeywordList.name, KeywordList.id)
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).scalars()
        return tuple(_list_from_row(row) for row in rows), total

    def get_keyword_list(
        self, *, organization_id: uuid.UUID, list_id: uuid.UUID
    ) -> StoredKeywordList | None:
        row = self._session.execute(
            select(KeywordList)
            .where(KeywordList.organization_id == organization_id)
            .where(KeywordList.id == list_id)
        ).scalar_one_or_none()
        return None if row is None else _list_from_row(row)

    def replace_keyword_list(
        self,
        *,
        organization_id: uuid.UUID,
        list_id: uuid.UUID,
        name: str,
        description: str | None,
        keywords: Sequence[str],
    ) -> StoredKeywordList | None:
        row = self._session.execute(
            select(KeywordList)
            .where(KeywordList.organization_id == organization_id)
            .where(KeywordList.id == list_id)
        ).scalar_one_or_none()
        if row is None:
            return None
        row.name = name
        row.description = description
        row.keywords = list(keywords)
        self._session.commit()
        self._session.refresh(row)
        return _list_from_row(row)

    def delete_keyword_list(self, *, organization_id: uuid.UUID, list_id: uuid.UUID) -> bool:
        row = self._session.execute(
            select(KeywordList)
            .where(KeywordList.organization_id == organization_id)
            .where(KeywordList.id == list_id)
        ).scalar_one_or_none()
        if row is None:
            return False
        self._session.delete(row)
        self._session.commit()
        return True


def _metric_from_row(row: KeywordMetric) -> StoredMetric:
    raw = dict(row.provider_raw or {})
    derived = raw.get(DERIVED_QUALITY_KEY) or {}
    provider_only = {key: value for key, value in raw.items() if key != DERIVED_QUALITY_KEY}
    return StoredMetric(
        normalized_keyword=row.normalized_keyword,
        source=DataSource(row.source),
        api_version=row.api_version,
        collected_at=row.collected_at,
        source_period=row.source_period,
        raw_response_hash=row.raw_response_hash,
        was_cache_hit=row.was_cache_hit,
        monthly_pc_searches=row.monthly_pc_searches,
        monthly_pc_searches_quality=_quality(row.monthly_pc_searches_quality),
        monthly_mobile_searches=row.monthly_mobile_searches,
        monthly_mobile_searches_quality=_quality(row.monthly_mobile_searches_quality),
        monthly_total_searches=row.monthly_total_searches,
        monthly_total_searches_quality=_quality(derived.get("monthly_total_searches_quality")),
        avg_pc_clicks=row.avg_pc_clicks,
        avg_pc_clicks_quality=_quality(derived.get("avg_pc_clicks_quality")),
        avg_mobile_clicks=row.avg_mobile_clicks,
        avg_mobile_clicks_quality=_quality(derived.get("avg_mobile_clicks_quality")),
        avg_pc_ctr=row.avg_pc_ctr,
        avg_pc_ctr_quality=_quality(derived.get("avg_pc_ctr_quality")),
        avg_mobile_ctr=row.avg_mobile_ctr,
        avg_mobile_ctr_quality=_quality(derived.get("avg_mobile_ctr_quality")),
        competition_index=row.competition_index,
        competition_label=row.competition_label,
        ad_depth=row.ad_depth,
        monthly_pc_upper_bound_exclusive=derived.get("monthly_pc_upper_bound_exclusive"),
        monthly_mobile_upper_bound_exclusive=derived.get(
            "monthly_mobile_upper_bound_exclusive"
        ),
        monthly_total_upper_bound_exclusive=derived.get("monthly_total_upper_bound_exclusive"),
        provider_raw=provider_only,
        partial_reason=row.partial_reason,
    )


def _related_from_row(row: RelatedKeyword) -> StoredRelated:
    return StoredRelated(
        seed_keyword=row.seed_keyword,
        related_keyword=row.related_keyword,
        source=DataSource(row.source),
        source_rank=row.source_rank,
        monthly_total_searches=row.monthly_total_searches,
        value_quality=_quality(row.value_quality),
    )


def _trends_from_rows(rows: Sequence[KeywordTrend]) -> tuple[StoredTrend, ...]:
    grouped: dict[tuple[str, str], list[KeywordTrend]] = {}
    for row in rows:
        grouped.setdefault((row.normalized_keyword, row.device), []).append(row)

    series: list[StoredTrend] = []
    for (keyword, device), points in grouped.items():
        ordered = sorted(points, key=lambda point: point.period_start)
        first = ordered[0]
        series.append(
            StoredTrend(
                normalized_keyword=keyword,
                source=DataSource(first.source),
                time_unit=first.time_unit,
                device=device,
                period_start=ordered[0].period_start,
                period_end=first.period_end,
                collected_at=first.collected_at,
                index_basis_note_ko=first.index_basis_note_ko or "",
                unit="RELATIVE_INDEX_0_100",
                points=tuple(
                    StoredTrendPoint(
                        period_start=point.period_start, relative_index=point.relative_index
                    )
                    for point in ordered
                ),
            )
        )
    return tuple(series)


def _opportunity_from_row(row: KeywordOpportunity) -> StoredOpportunity:
    return StoredOpportunity(
        normalized_keyword=row.normalized_keyword,
        formula_version=row.formula_version,
        source=DataSource(row.source),
        demand=row.demand,
        trend=row.trend,
        intent_fit=row.intent_fit,
        competition_inverse=row.competition_inverse,
        content_gap=row.content_gap,
        confidence=row.confidence,
        opportunity_score=row.opportunity_score,
        calculation_trace=dict(row.calculation_trace or {}),
        missing_components=tuple(row.missing_components or ()),
    )


def _list_from_row(row: KeywordList) -> StoredKeywordList:
    return StoredKeywordList(
        id=row.id,
        organization_id=row.organization_id,
        project_id=row.project_id,
        name=row.name,
        description=row.description,
        keywords=tuple(str(keyword) for keyword in (row.keywords or ())),
        created_at=row.created_at,
        updated_at=row.updated_at,
    )
