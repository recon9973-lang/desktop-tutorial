"""Keyword lookup, trends, opportunity, recent keywords and lists.

The service is where the two Naver families are put side by side without ever being
mixed. It calls Search Ad for counts and DataLab for a relative index, keeps each in its
own type and its own table, and asks :mod:`veo.keywords.opportunity` for a score that is
explicitly VEO's own arithmetic.

When a provider cannot answer — no credential, a rejection, a timeout, an open circuit —
the lookup still succeeds. It returns a recorded query, a stated provider state, a Korean
explanation, and **no numbers**. That is the shape of an honest answer to "what is the
search volume?" when nobody will tell you.
"""

from __future__ import annotations

import uuid
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Final, final

from veo.authz import Principal
from veo.contracts.enums import DataSource, ProviderState
from veo.keywords.normalize import normalize_keyword
from veo.keywords.opportunity import (
    OpportunityInputs,
    OpportunityResult,
    rebuild_result,
    trend_component,
)
from veo.keywords.opportunity import (
    score as score_opportunity,
)
from veo.keywords.repository import (
    KeywordRepository,
    RecentLookupRow,
    StoredKeywordList,
    StoredLookup,
    StoredMetric,
    StoredOpportunity,
    StoredRelated,
    StoredTrend,
    StoredTrendPoint,
)
from veo.providers.naver.datalab import KeywordTrendSeries, NaverDataLabClient
from veo.providers.naver.errors import ProviderFailure, UnknownValue
from veo.providers.naver.searchad import (
    NaverSearchAdClient,
    SearchAdKeywordMetrics,
    SearchAdKeywordResponse,
    SearchCount,
)

__all__ = [
    "MAX_KEYWORDS_PER_REQUEST",
    "RECENT_KEYWORDS_TITLE_KO",
    "KeywordLookupResult",
    "KeywordService",
    "KeywordSnapshot",
    "RecentKeywordEntry",
    "RecentKeywordsReport",
]

MAX_KEYWORDS_PER_REQUEST: Final = 20

#: Never ``실시간 인기검색어``. There is no lawful, documented source for a real-time
#: popular-search ranking, so VEO does not use the name — it reports what it actually has:
#: the keywords this organization looked up, over a stated window.
RECENT_KEYWORDS_TITLE_KO: Final = "VEO 최근 조회 키워드"

_RECENT_METHODOLOGY_KO: Final = (
    "이 목록은 네이버의 인기검색어 순위가 아닙니다. 지정한 기간 동안 이 조직이 VEO에서 직접 "
    "조회한 키워드의 조회 횟수를 집계한 VEO 자체 관측치입니다."
)
_RECENT_SCOPE_KO: Final = (
    "집계 범위: 현재 조직의 VEO 키워드 조회 기록만 포함합니다. 다른 조직의 조회, 네이버 "
    "전체 검색, 외부 트래픽은 포함하지 않습니다."
)
_RECENT_DEIDENTIFICATION_KO: Final = (
    "비식별화 규칙: 조회한 사용자·세션을 식별하지 않고 조직 단위 합계만 표시합니다. "
    "지정한 최소 조회 횟수에 미치지 못한 키워드는 목록에서 제외하고 건수만 알립니다."
)

_DISABLED_NOTICE_SUFFIX_KO: Final = (
    "설정 > 제공자 자격증명에서 키를 등록하면 실제 수치를 조회할 수 있습니다."
)

#: The window a trend lookup requests when the caller does not name one.
_DEFAULT_TREND_DAYS: Final = 365
#: DataLab accepts a limited number of keyword groups per request.
_TREND_BATCH_SIZE: Final = 5


@final
@dataclass(frozen=True, slots=True)
class KeywordSnapshot:
    """One keyword's complete picture, with every absence stated rather than filled."""

    original_keyword: str
    normalized_keyword: str
    metrics: StoredMetric | None
    trend: StoredTrend | None
    opportunity: OpportunityResult | None
    related: tuple[StoredRelated, ...]


@final
@dataclass(frozen=True, slots=True)
class KeywordLookupResult:
    query_id: uuid.UUID | None
    project_id: uuid.UUID | None
    requested_at: datetime
    locale: str
    searchad_state: ProviderState
    datalab_state: ProviderState
    searchad_failure: ProviderFailure | None
    datalab_failure: ProviderFailure | None
    snapshots: tuple[KeywordSnapshot, ...]
    notices_ko: tuple[str, ...]


@final
@dataclass(frozen=True, slots=True)
class RecentKeywordEntry:
    normalized_keyword: str
    lookup_count: int
    last_requested_at: datetime


@final
@dataclass(frozen=True, slots=True)
class RecentKeywordsReport:
    """VEO's own recent-lookup observation, labelled as exactly that."""

    title_ko: str
    source: DataSource
    window_hours: int
    period_start: datetime
    period_end: datetime
    refreshed_at: datetime
    min_lookups: int
    entries: tuple[RecentKeywordEntry, ...]
    suppressed_count: int
    methodology_ko: str = _RECENT_METHODOLOGY_KO
    scope_ko: str = _RECENT_SCOPE_KO
    de_identification_ko: str = _RECENT_DEIDENTIFICATION_KO


class KeywordService:
    def __init__(
        self,
        *,
        searchad: NaverSearchAdClient,
        datalab: NaverDataLabClient,
        repository: KeywordRepository,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self._searchad = searchad
        self._datalab = datalab
        self._repository = repository
        self._clock = clock

    # ----------------------------------------------------------------- lookup

    def lookup(
        self,
        *,
        principal: Principal,
        keywords: Sequence[str],
        locale: str = "ko-KR",
        project_id: uuid.UUID | None = None,
        surface: str = "CONSOLE",
        include_trend: bool = True,
        intent_fit: float | None = None,
        content_gap: float | None = None,
    ) -> KeywordLookupResult:
        pairs = self._normalize_requested(keywords)
        requested_at = self._clock()

        metrics_by_keyword: dict[str, SearchAdKeywordMetrics] = {}
        related_by_keyword: dict[str, tuple[StoredRelated, ...]] = {}
        response_by_keyword: dict[str, SearchAdKeywordResponse] = {}
        searchad_failure: ProviderFailure | None = None

        for _, normalized in pairs:
            outcome = self._searchad.lookup([normalized])
            if isinstance(outcome.value, UnknownValue):
                searchad_failure = searchad_failure or outcome.failure
                continue
            answered = outcome.value
            response_by_keyword[normalized] = answered
            seed_row, related_rows = _split_seed_and_related(answered, normalized)
            if seed_row is not None:
                metrics_by_keyword[normalized] = seed_row
            related_by_keyword[normalized] = related_rows

        trends_by_keyword: dict[str, KeywordTrendSeries] = {}
        datalab_failure: ProviderFailure | None = None
        if include_trend:
            trends_by_keyword, datalab_failure = self._collect_trends(
                [normalized for _, normalized in pairs], now=requested_at
            )

        snapshots: list[KeywordSnapshot] = []
        stored_metrics: list[StoredMetric] = []
        stored_related: list[StoredRelated] = []
        stored_trends: list[StoredTrend] = []
        stored_opportunities: list[StoredOpportunity] = []

        for original, normalized in pairs:
            provider_metrics = metrics_by_keyword.get(normalized)
            response = response_by_keyword.get(normalized)
            series = trends_by_keyword.get(normalized)

            metric = (
                None
                if provider_metrics is None or response is None
                else _to_stored_metric(provider_metrics, normalized, response)
            )
            trend = None if series is None else _to_stored_trend(series, normalized)
            related = related_by_keyword.get(normalized, ())

            opportunity = self._score(
                provider_metrics=provider_metrics,
                series=series,
                intent_fit=intent_fit,
                content_gap=content_gap,
                collected_at=None if response is None else response.collected_at,
                now=requested_at,
            )

            snapshots.append(
                KeywordSnapshot(
                    original_keyword=original,
                    normalized_keyword=normalized,
                    metrics=metric,
                    trend=trend,
                    opportunity=opportunity,
                    related=related,
                )
            )
            if metric is not None:
                stored_metrics.append(metric)
            stored_related.extend(related)
            if trend is not None:
                stored_trends.append(trend)
            if opportunity is not None:
                stored_opportunities.append(_to_stored_opportunity(opportunity, normalized))

        searchad_state = self._provider_state(self._searchad.state, searchad_failure)
        datalab_state = (
            self._provider_state(self._datalab.state, datalab_failure)
            if include_trend
            else self._datalab.state
        )

        query_id = self._repository.record_lookup(
            organization_id=principal.organization_id,
            project_id=project_id,
            surface=surface,
            locale=locale,
            original_keyword=pairs[0][0],
            normalized_keyword=pairs[0][1],
            requested_at=requested_at,
            provider_state=searchad_state,
            error_code=_error_code(searchad_state, searchad_failure),
            metrics=stored_metrics,
            related=stored_related,
            trends=stored_trends,
            opportunities=stored_opportunities,
        )

        return KeywordLookupResult(
            query_id=query_id,
            project_id=project_id,
            requested_at=requested_at,
            locale=locale,
            searchad_state=searchad_state,
            datalab_state=datalab_state,
            searchad_failure=searchad_failure,
            datalab_failure=datalab_failure,
            snapshots=tuple(snapshots),
            notices_ko=_notices(searchad_failure, datalab_failure),
        )

    def get_lookup(
        self, *, principal: Principal, query_id: uuid.UUID
    ) -> KeywordLookupResult | None:
        """Read a recorded lookup back, in the same shape a fresh one has."""
        stored = self._repository.load_lookup(
            organization_id=principal.organization_id, query_id=query_id
        )
        if stored is None:
            return None
        return _result_from_stored(stored)

    # -------------------------------------------------------------- recent

    def recent_keywords(
        self,
        *,
        principal: Principal,
        window_hours: int = 24,
        limit: int = 20,
        min_lookups: int = 1,
    ) -> RecentKeywordsReport:
        """Keywords **this organization** looked up recently. Not a Naver ranking."""
        if window_hours < 1 or window_hours > 24 * 30:
            raise ValueError("집계 기간은 1시간 이상 30일 이하만 지정할 수 있습니다.")
        if min_lookups < 1:
            raise ValueError("최소 조회 횟수는 1 이상이어야 합니다.")

        now = self._clock()
        since = now - timedelta(hours=window_hours)
        rows: Sequence[RecentLookupRow] = self._repository.recent_lookups(
            organization_id=principal.organization_id, since=since, until=now, limit=limit
        )

        kept = [row for row in rows if row.lookup_count >= min_lookups]
        return RecentKeywordsReport(
            title_ko=RECENT_KEYWORDS_TITLE_KO,
            source=DataSource.VEO_INTERNAL,
            window_hours=window_hours,
            period_start=since,
            period_end=now,
            refreshed_at=now,
            min_lookups=min_lookups,
            entries=tuple(
                RecentKeywordEntry(
                    normalized_keyword=row.normalized_keyword,
                    lookup_count=row.lookup_count,
                    last_requested_at=row.last_requested_at,
                )
                for row in kept
            ),
            suppressed_count=len(rows) - len(kept),
        )

    # --------------------------------------------------------------- lists

    def create_list(
        self,
        *,
        principal: Principal,
        project_id: uuid.UUID,
        name: str,
        description: str | None,
        keywords: Sequence[str],
    ) -> StoredKeywordList:
        return self._repository.create_list(
            organization_id=principal.organization_id,
            project_id=project_id,
            name=name,
            description=description,
            keywords=_normalized_unique(keywords),
        )

    def list_lists(
        self,
        *,
        principal: Principal,
        project_id: uuid.UUID | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[tuple[StoredKeywordList, ...], int]:
        return self._repository.list_keyword_lists(
            organization_id=principal.organization_id,
            project_id=project_id,
            page=page,
            page_size=page_size,
        )

    def get_list(
        self, *, principal: Principal, list_id: uuid.UUID
    ) -> StoredKeywordList | None:
        return self._repository.get_keyword_list(
            organization_id=principal.organization_id, list_id=list_id
        )

    def replace_list(
        self,
        *,
        principal: Principal,
        list_id: uuid.UUID,
        name: str,
        description: str | None,
        keywords: Sequence[str],
    ) -> StoredKeywordList | None:
        return self._repository.replace_keyword_list(
            organization_id=principal.organization_id,
            list_id=list_id,
            name=name,
            description=description,
            keywords=_normalized_unique(keywords),
        )

    def delete_list(self, *, principal: Principal, list_id: uuid.UUID) -> bool:
        return self._repository.delete_keyword_list(
            organization_id=principal.organization_id, list_id=list_id
        )

    # ----------------------------------------------------------- internals

    @staticmethod
    def _normalize_requested(keywords: Sequence[str]) -> list[tuple[str, str]]:
        if not keywords:
            raise ValueError("키워드를 하나 이상 입력해 주세요.")
        if len(keywords) > MAX_KEYWORDS_PER_REQUEST:
            raise ValueError(
                f"한 번에 조회할 수 있는 키워드는 최대 {MAX_KEYWORDS_PER_REQUEST}개입니다."
            )
        pairs: list[tuple[str, str]] = []
        seen: set[str] = set()
        for raw in keywords:
            normalized = normalize_keyword(raw)
            if normalized in seen:
                continue
            seen.add(normalized)
            pairs.append((raw, normalized))
        return pairs

    def _collect_trends(
        self, keywords: Sequence[str], *, now: datetime
    ) -> tuple[dict[str, KeywordTrendSeries], ProviderFailure | None]:
        end = now.date()
        start = end - timedelta(days=_DEFAULT_TREND_DAYS)

        collected: dict[str, KeywordTrendSeries] = {}
        failure: ProviderFailure | None = None
        for index in range(0, len(keywords), _TREND_BATCH_SIZE):
            batch = list(keywords[index : index + _TREND_BATCH_SIZE])
            outcome = self._datalab.lookup_trend(
                batch, start_date=start, end_date=end, time_unit="month"
            )
            if isinstance(outcome.value, UnknownValue):
                failure = failure or outcome.failure
                continue
            for series in outcome.value:
                collected[normalize_keyword(series.keyword)] = series
        return collected, failure

    @staticmethod
    def _score(
        *,
        provider_metrics: SearchAdKeywordMetrics | None,
        series: KeywordTrendSeries | None,
        intent_fit: float | None,
        content_gap: float | None,
        collected_at: datetime | None,
        now: datetime,
    ) -> OpportunityResult | None:
        """No official metrics means no score — not a score built out of nothing."""
        if provider_metrics is None:
            return None
        return score_opportunity(
            OpportunityInputs(
                monthly_total_searches=provider_metrics.monthly_total_searches,
                trend=None if series is None else trend_component(series.points),
                intent_fit=intent_fit,
                competition_label=provider_metrics.competition_label,
                content_gap=content_gap,
                collected_at=collected_at,
                now=now,
            )
        )

    @staticmethod
    def _provider_state(
        client_state: ProviderState, failure: ProviderFailure | None
    ) -> ProviderState:
        if client_state is ProviderState.DISABLED_NO_CREDENTIAL:
            return client_state
        if failure is not None:
            return failure.provider_state
        return client_state


def _normalized_unique(keywords: Sequence[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for raw in keywords:
        normalized = normalize_keyword(raw)
        if normalized in seen:
            continue
        seen.add(normalized)
        result.append(normalized)
    if not result:
        raise ValueError("키워드를 하나 이상 입력해 주세요.")
    return result


def _split_seed_and_related(
    response: SearchAdKeywordResponse, normalized_seed: str
) -> tuple[SearchAdKeywordMetrics | None, tuple[StoredRelated, ...]]:
    """Separate the keyword that was asked for from the ones Naver volunteered."""
    seed: SearchAdKeywordMetrics | None = None
    related: list[StoredRelated] = []
    rank = 0
    for row in response.metrics:
        if seed is None and normalize_keyword(row.keyword) == normalized_seed:
            seed = row
            continue
        rank += 1
        total = row.monthly_total_searches
        related.append(
            StoredRelated(
                seed_keyword=normalized_seed,
                related_keyword=normalize_keyword(row.keyword),
                source=DataSource.NAVER_SEARCH_AD,
                source_rank=rank,
                monthly_total_searches=total.value,
                value_quality=total.quality,
            )
        )
    return seed, tuple(related)


def _to_stored_metric(
    metrics: SearchAdKeywordMetrics, normalized_keyword: str, response: SearchAdKeywordResponse
) -> StoredMetric:
    """Provider shape to storage shape, carrying every quality flag across.

    A ``RelativeIndex`` cannot reach this function: its parameter is typed as a Search Ad
    metric, and the check below makes the type error loud rather than latent.
    """
    if not isinstance(metrics, SearchAdKeywordMetrics):
        raise TypeError(
            "only Search Ad metrics may be written to keyword_metrics; got "
            f"{type(metrics).__name__}"
        )

    pc = metrics.monthly_pc_searches
    mobile = metrics.monthly_mobile_searches
    total = metrics.monthly_total_searches
    _assert_is_count(pc, "monthly_pc_searches")
    _assert_is_count(mobile, "monthly_mobile_searches")
    _assert_is_count(total, "monthly_total_searches")

    return StoredMetric(
        normalized_keyword=normalized_keyword,
        source=DataSource.NAVER_SEARCH_AD,
        api_version=response.api_version,
        collected_at=response.collected_at,
        source_period=None,
        raw_response_hash=response.raw_response_hash,
        was_cache_hit=False,
        monthly_pc_searches=pc.value,
        monthly_pc_searches_quality=pc.quality,
        monthly_mobile_searches=mobile.value,
        monthly_mobile_searches_quality=mobile.quality,
        monthly_total_searches=total.value,
        monthly_total_searches_quality=total.quality,
        avg_pc_clicks=metrics.avg_pc_clicks.value,
        avg_pc_clicks_quality=metrics.avg_pc_clicks.quality,
        avg_mobile_clicks=metrics.avg_mobile_clicks.value,
        avg_mobile_clicks_quality=metrics.avg_mobile_clicks.quality,
        avg_pc_ctr=metrics.avg_pc_ctr.value,
        avg_pc_ctr_quality=metrics.avg_pc_ctr.quality,
        avg_mobile_ctr=metrics.avg_mobile_ctr.value,
        avg_mobile_ctr_quality=metrics.avg_mobile_ctr.quality,
        competition_index=metrics.competition_index,
        competition_label=metrics.competition_label,
        ad_depth=metrics.ad_depth,
        monthly_pc_upper_bound_exclusive=pc.upper_bound_exclusive,
        monthly_mobile_upper_bound_exclusive=mobile.upper_bound_exclusive,
        monthly_total_upper_bound_exclusive=total.upper_bound_exclusive,
        provider_raw=dict(metrics.provider_raw),
        partial_reason=(
            "제공자 응답에 VEO가 모르는 필드가 있어 매핑하지 못했습니다: "
            + ", ".join(response.unmapped_fields)
            if response.unmapped_fields
            else None
        ),
    )


def _assert_is_count(value: object, name: str) -> None:
    if not isinstance(value, SearchCount):
        raise TypeError(
            f"{name} must be a SearchCount from the Search Ad adapter; got "
            f"{type(value).__name__}. A relative interest index is not a search count."
        )


def _to_stored_trend(series: KeywordTrendSeries, normalized_keyword: str) -> StoredTrend:
    return StoredTrend(
        normalized_keyword=normalized_keyword,
        source=DataSource.NAVER_DATALAB,
        time_unit=series.time_unit,
        device=series.device,
        period_start=series.period_start,
        period_end=series.period_end,
        collected_at=series.collected_at,
        index_basis_note_ko=series.index_basis_note_ko,
        unit=series.unit,
        points=tuple(
            StoredTrendPoint(
                period_start=point.period_start, relative_index=point.relative_index.value
            )
            for point in series.points
        ),
    )


def _to_stored_opportunity(
    result: OpportunityResult, normalized_keyword: str
) -> StoredOpportunity:
    values = {component.name: component.value for component in result.components}
    return StoredOpportunity(
        normalized_keyword=normalized_keyword,
        formula_version=result.formula_version,
        source=result.source,
        demand=values.get("demand"),
        trend=values.get("trend"),
        intent_fit=values.get("intent_fit"),
        competition_inverse=values.get("competition_inverse"),
        content_gap=values.get("content_gap"),
        confidence=result.confidence,
        opportunity_score=result.score,
        calculation_trace=dict(result.trace),
        missing_components=result.missing_components,
    )


def _error_code(state: ProviderState, failure: ProviderFailure | None) -> str | None:
    """A disabled provider is a state, not an error. Everything else records its code."""
    if state is ProviderState.DISABLED_NO_CREDENTIAL:
        return None
    return None if failure is None else failure.error_code.value


def _notices(*failures: ProviderFailure | None) -> tuple[str, ...]:
    notices: list[str] = []
    for failure in failures:
        if failure is None:
            continue
        notice = failure.reason_ko
        if failure.provider_state is ProviderState.DISABLED_NO_CREDENTIAL:
            notice = f"{notice} {_DISABLED_NOTICE_SUFFIX_KO}"
        if notice not in notices:
            notices.append(notice)
    return tuple(notices)


def _result_from_stored(stored: StoredLookup) -> KeywordLookupResult:
    metrics_by_keyword = {metric.normalized_keyword: metric for metric in stored.metrics}
    trends_by_keyword = {trend.normalized_keyword: trend for trend in stored.trends}
    opportunities_by_keyword = {
        opportunity.normalized_keyword: opportunity for opportunity in stored.opportunities
    }
    related_by_seed: dict[str, list[StoredRelated]] = {}
    for row in stored.related:
        related_by_seed.setdefault(row.seed_keyword, []).append(row)

    keywords = list(
        dict.fromkeys(
            [stored.normalized_keyword, *metrics_by_keyword, *related_by_seed]
        )
    )

    snapshots = tuple(
        KeywordSnapshot(
            original_keyword=(
                stored.original_keyword if keyword == stored.normalized_keyword else keyword
            ),
            normalized_keyword=keyword,
            metrics=metrics_by_keyword.get(keyword),
            trend=trends_by_keyword.get(keyword),
            opportunity=(
                rebuild_result(opportunities_by_keyword[keyword])
                if keyword in opportunities_by_keyword
                else None
            ),
            related=tuple(related_by_seed.get(keyword, ())),
        )
        for keyword in keywords
    )

    state = stored.provider_state
    return KeywordLookupResult(
        query_id=stored.id,
        project_id=stored.project_id,
        requested_at=stored.requested_at,
        locale=stored.locale,
        searchad_state=state,
        datalab_state=(
            ProviderState.ENABLED if stored.trends else ProviderState.DISABLED_NO_CREDENTIAL
        ),
        searchad_failure=None,
        datalab_failure=None,
        snapshots=snapshots,
        notices_ko=(
            "저장된 조회 기록입니다. 조회 시점의 제공자 상태와 수치를 그대로 보여줍니다.",
        ),
    )
