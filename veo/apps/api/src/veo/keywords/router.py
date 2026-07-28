"""HTTP surface for Naver keyword intelligence.

**This router is deliberately not mounted.** ``veo.api.app`` belongs to the integrator;
including it there is their call, not this worker's. See ``INTEGRATION_REQUEST.md``.

Conventions inherited from the rest of the API:

* Another organization's row is **404, never 403** — a 403 confirms it exists.
* Korean messages, and a disabled provider is a normal reportable state rather than an
  error. A lookup with no credential returns ``200`` with every provider's state, an
  explanation, and no numbers.
* ``KEYWORD_READ`` reads; ``KEYWORD_RUN`` spends a provider call or changes a saved list.
  Export additionally requires ``REPORT_EXPORT``, because an export leaves the product.

There is no endpoint called ``실시간 인기검색어``. VEO has no lawful, documented source for
a real-time popular-search ranking, so it does not offer one under any name. What
``/keywords/recent`` returns is what VEO actually has — the keywords this organization
looked up, over a stated window, aggregated and de-identified.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Response, status
from sqlalchemy.orm import Session

from veo.api.deps import RequestId, build_meta, ok
from veo.authz import CurrentPrincipal, Permission, require
from veo.contracts.enums import DataSource, ErrorCode
from veo.contracts.envelope import ApiError, ApiResponse, PagedResponse, PageInfo, SourceAttribution
from veo.db.session import get_db
from veo.keywords.export import (
    CSV_CONTENT_TYPE,
    XLSX_CONTENT_TYPE,
    export_csv,
    export_xlsx,
)
from veo.keywords.repository import SqlKeywordRepository, StoredRelated
from veo.keywords.schemas import (
    KeywordListPayload,
    KeywordListRequest,
    KeywordListUpdateRequest,
    KeywordLookupPayload,
    KeywordLookupRequest,
    RecentKeywordsPayload,
    RelatedKeywordPayload,
    list_payload,
    lookup_payload,
    recent_payload,
    related_payload,
)
from veo.keywords.service import KeywordLookupResult, KeywordService
from veo.providers.naver.credentials import datalab_from_settings, searchad_from_settings
from veo.providers.naver.datalab import NaverDataLabClient
from veo.providers.naver.searchad import NaverSearchAdClient

__all__ = ["get_keyword_service", "router"]

router = APIRouter(tags=["keywords"])

RelatedSort = Literal[
    "source_rank",
    "-source_rank",
    "related_keyword",
    "-related_keyword",
    "monthly_total_searches",
    "-monthly_total_searches",
]

ExportFormat = Literal["csv", "xlsx"]


def get_keyword_service(session: Annotated[Session, Depends(get_db)]) -> KeywordService:
    """Build the service for one request.

    Credentials come from deployment settings today. Per-organization credentials from the
    vault are the intended source for a multi-tenant install — the resolvers already exist
    in ``providers/naver/credentials.py`` — and switching to them needs the request in
    ``INTEGRATION_REQUEST.md`` #5 to be answered first, because it changes when the
    credential vault's master key becomes required at startup.

    With nothing configured both clients report ``DISABLED_NO_CREDENTIAL`` and no outbound
    connection is ever opened.
    """
    return KeywordService(
        searchad=NaverSearchAdClient(credentials=searchad_from_settings()),
        datalab=NaverDataLabClient(credentials=datalab_from_settings()),
        repository=SqlKeywordRepository(session),
    )


ServiceDep = Annotated[KeywordService, Depends(get_keyword_service)]
QueryIdPath = Annotated[uuid.UUID, Path(description="저장된 키워드 조회 기록의 식별자입니다.")]
ListIdPath = Annotated[uuid.UUID, Path(description="키워드 목록의 식별자입니다.")]


def _error(status_code: int, code: ErrorCode, message: str) -> HTTPException:
    return HTTPException(
        status_code=status_code, detail=ApiError.of(code, message).model_dump(mode="json")
    )


def _not_found() -> HTTPException:
    """One answer for "not there" and "not yours"."""
    return _error(
        status.HTTP_404_NOT_FOUND, ErrorCode.NOT_FOUND, "요청하신 키워드 기록을 찾을 수 없습니다."
    )


def _invalid(message: str) -> HTTPException:
    return _error(status.HTTP_422_UNPROCESSABLE_ENTITY, ErrorCode.VALIDATION_FAILED, message)


def _sources(result: KeywordLookupResult) -> list[SourceAttribution]:
    """Source badges for the response envelope, one per data family actually present."""
    attributions: list[SourceAttribution] = []

    metric = next(
        (snapshot.metrics for snapshot in result.snapshots if snapshot.metrics is not None),
        None,
    )
    if metric is not None:
        attributions.append(
            SourceAttribution(
                source=DataSource.NAVER_SEARCH_AD,
                provider_state=result.searchad_state,
                collected_at=metric.collected_at,
                api_version=metric.api_version,
                raw_response_hash=metric.raw_response_hash,
                cache_hit=metric.was_cache_hit,
                note_ko="네이버 검색광고가 제공한 절대 검색량·클릭·CTR·경쟁 라벨입니다.",
            )
        )
        attributions.append(
            SourceAttribution(
                source=DataSource.CALCULATED,
                provider_state=result.searchad_state,
                collected_at=metric.collected_at,
                note_ko="기기별 합계와 기회 점수는 VEO가 계산한 값입니다.",
            )
        )

    trend = next(
        (snapshot.trend for snapshot in result.snapshots if snapshot.trend is not None), None
    )
    if trend is not None:
        attributions.append(
            SourceAttribution(
                source=DataSource.NAVER_DATALAB,
                provider_state=result.datalab_state,
                collected_at=trend.collected_at,
                source_period=f"{trend.period_start.isoformat()}~{trend.period_end.isoformat()}",
                note_ko=trend.index_basis_note_ko,
            )
        )
    return attributions


def _now() -> datetime:
    return datetime.now(UTC)


# --------------------------------------------------------------------------- #
# Lookup
# --------------------------------------------------------------------------- #


@router.post(
    "/keywords/lookups",
    response_model=ApiResponse[KeywordLookupPayload],
    summary="키워드 조회 실행",
    description=(
        "네이버 검색광고에서 절대 검색량을, 데이터랩에서 상대 관심도를 조회합니다. "
        "두 값은 단위가 다르므로 절대 합치지 않고 각각 출처 badge와 기준시각을 함께 반환합니다. "
        "자격증명이 없으면 오류가 아니라 '비활성' 상태와 사유를 돌려주며, 이 경우 응답에는 "
        "**어떤 수치도 포함되지 않습니다**. 추정값을 실제 데이터처럼 표시하지 않습니다."
    ),
    dependencies=[Depends(require(Permission.KEYWORD_RUN))],
)
def run_lookup(
    body: KeywordLookupRequest,
    service: ServiceDep,
    principal: CurrentPrincipal,
    request_id: RequestId,
) -> ApiResponse[KeywordLookupPayload]:
    try:
        result = service.lookup(
            principal=principal,
            keywords=body.keywords,
            locale=body.locale,
            project_id=body.project_id,
            include_trend=body.include_trend,
            intent_fit=body.intent_fit,
            content_gap=body.content_gap,
        )
    except ValueError as exc:
        raise _invalid(str(exc)) from None

    return ok(lookup_payload(result, now=_now()), request_id, sources=_sources(result))


@router.get(
    "/keywords/lookups/{query_id}",
    response_model=ApiResponse[KeywordLookupPayload],
    summary="저장된 키워드 조회 기록 열람",
    description=(
        "조회 시점에 기록한 수치를 그대로 보여줍니다. 억제값·구간값·결측값은 저장 시점의 "
        "구분을 그대로 유지하며, 0으로 바뀌지 않습니다."
    ),
    dependencies=[Depends(require(Permission.KEYWORD_READ))],
)
def read_lookup(
    query_id: QueryIdPath,
    service: ServiceDep,
    principal: CurrentPrincipal,
    request_id: RequestId,
) -> ApiResponse[KeywordLookupPayload]:
    result = service.get_lookup(principal=principal, query_id=query_id)
    if result is None:
        raise _not_found()
    return ok(lookup_payload(result, now=_now()), request_id, sources=_sources(result))


@router.get(
    "/keywords/lookups/{query_id}/related",
    response_model=PagedResponse[RelatedKeywordPayload],
    summary="연관 키워드 목록",
    description=(
        "연관 키워드를 필터·정렬·페이지 단위로 반환합니다. 검색량 기준 정렬에서 측정값이 없는 "
        "키워드는 0으로 취급하지 않고 항상 뒤에 배치합니다."
    ),
    dependencies=[Depends(require(Permission.KEYWORD_READ))],
)
def list_related(
    query_id: QueryIdPath,
    service: ServiceDep,
    principal: CurrentPrincipal,
    request_id: RequestId,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=200)] = 50,
    contains: Annotated[str | None, Query(max_length=255)] = None,
    sort: RelatedSort = "source_rank",
) -> PagedResponse[RelatedKeywordPayload]:
    result = service.get_lookup(principal=principal, query_id=query_id)
    if result is None:
        raise _not_found()

    rows = [row for snapshot in result.snapshots for row in snapshot.related]
    if contains:
        needle = contains.casefold()
        rows = [row for row in rows if needle in row.related_keyword.casefold()]

    rows = _sorted_related(rows, sort)
    total = len(rows)
    start = (page - 1) * page_size
    window = rows[start : start + page_size]

    return PagedResponse[RelatedKeywordPayload](
        data=[related_payload(row) for row in window],
        error=None,
        page_info=PageInfo.build(page=page, page_size=page_size, total_items=total),
        meta=build_meta(request_id, sources=_sources(result)),
    )


def _sorted_related(rows: list[StoredRelated], sort: str) -> list[StoredRelated]:
    """Sort related keywords, keeping unmeasured volumes out of the numeric ordering.

    Sorting ``None`` as ``0`` would place every suppressed keyword among the genuinely
    unsearched ones — precisely the confusion the ``*_quality`` flags exist to prevent,
    reintroduced by a sort key. Unmeasured rows go last in both directions.
    """
    descending = sort.startswith("-")
    key = sort.removeprefix("-")

    if key == "related_keyword":
        return sorted(rows, key=lambda row: row.related_keyword, reverse=descending)

    if key == "monthly_total_searches":
        measured = [row for row in rows if row.monthly_total_searches is not None]
        unmeasured = [row for row in rows if row.monthly_total_searches is None]
        measured.sort(
            key=lambda row: row.monthly_total_searches or 0, reverse=descending
        )
        return measured + unmeasured

    return sorted(
        rows,
        key=lambda row: (row.source_rank is None, row.source_rank or 0),
        reverse=descending,
    )


@router.get(
    "/keywords/lookups/{query_id}/export",
    summary="키워드 조회 결과 내보내기 (CSV / XLSX)",
    description=(
        "각 수치 옆에 품질(정확·구간·억제·결측) 열을 함께 내보냅니다. 측정값이 없는 칸은 0이 "
        "아니라 빈 칸입니다. 수식으로 해석될 수 있는 문자로 시작하는 셀은 앞에 작은따옴표를 "
        "붙여 무력화합니다."
    ),
    dependencies=[
        Depends(require(Permission.KEYWORD_READ)),
        Depends(require(Permission.REPORT_EXPORT)),
    ],
    responses={200: {"content": {CSV_CONTENT_TYPE: {}, XLSX_CONTENT_TYPE: {}}}},
)
def export_lookup(
    query_id: QueryIdPath,
    service: ServiceDep,
    principal: CurrentPrincipal,
    format: ExportFormat = "csv",
) -> Response:
    result = service.get_lookup(principal=principal, query_id=query_id)
    if result is None:
        raise _not_found()

    if format == "csv":
        body, media_type, suffix = export_csv(result), CSV_CONTENT_TYPE, "csv"
    else:
        body, media_type, suffix = export_xlsx(result), XLSX_CONTENT_TYPE, "xlsx"

    filename = f"veo-keywords-{query_id}.{suffix}"
    return Response(
        content=body,
        media_type=media_type,
        headers={"content-disposition": f'attachment; filename="{filename}"'},
    )


# --------------------------------------------------------------------------- #
# Recent keywords
# --------------------------------------------------------------------------- #


@router.get(
    "/keywords/recent",
    response_model=ApiResponse[RecentKeywordsPayload],
    summary="VEO 최근 조회 키워드",
    description=(
        "**네이버 인기검색어 순위가 아닙니다.** 지정한 기간 동안 현재 조직이 VEO에서 직접 "
        "조회한 키워드의 횟수를 집계한 VEO 자체 관측치이며, 기준 기간·집계 범위·갱신 시각·"
        "비식별화 규칙을 응답에 함께 표시합니다. 조회한 사용자는 식별하지 않습니다."
    ),
    dependencies=[Depends(require(Permission.KEYWORD_READ))],
)
def read_recent(
    service: ServiceDep,
    principal: CurrentPrincipal,
    request_id: RequestId,
    window_hours: Annotated[int, Query(ge=1, le=720)] = 24,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    min_lookups: Annotated[int, Query(ge=1, le=1000)] = 1,
) -> ApiResponse[RecentKeywordsPayload]:
    try:
        report = service.recent_keywords(
            principal=principal,
            window_hours=window_hours,
            limit=limit,
            min_lookups=min_lookups,
        )
    except ValueError as exc:
        raise _invalid(str(exc)) from None

    return ok(
        recent_payload(report),
        request_id,
        sources=[
            SourceAttribution(
                source=DataSource.VEO_INTERNAL,
                collected_at=report.refreshed_at,
                source_period=(
                    f"{report.period_start.isoformat()}~{report.period_end.isoformat()}"
                ),
                note_ko=report.methodology_ko,
            )
        ],
    )


# --------------------------------------------------------------------------- #
# Keyword lists
# --------------------------------------------------------------------------- #


@router.post(
    "/keywords/lists",
    response_model=ApiResponse[KeywordListPayload],
    status_code=status.HTTP_201_CREATED,
    summary="키워드 목록 생성",
    dependencies=[Depends(require(Permission.KEYWORD_RUN))],
)
def create_keyword_list(
    body: KeywordListRequest,
    service: ServiceDep,
    principal: CurrentPrincipal,
    request_id: RequestId,
) -> ApiResponse[KeywordListPayload]:
    try:
        created = service.create_list(
            principal=principal,
            project_id=body.project_id,
            name=body.name,
            description=body.description,
            keywords=body.keywords,
        )
    except ValueError as exc:
        raise _invalid(str(exc)) from None
    return ok(list_payload(created), request_id)


@router.get(
    "/keywords/lists",
    response_model=PagedResponse[KeywordListPayload],
    summary="키워드 목록 조회",
    dependencies=[Depends(require(Permission.KEYWORD_READ))],
)
def read_keyword_lists(
    service: ServiceDep,
    principal: CurrentPrincipal,
    request_id: RequestId,
    project_id: uuid.UUID | None = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=200)] = 20,
) -> PagedResponse[KeywordListPayload]:
    rows, total = service.list_lists(
        principal=principal, project_id=project_id, page=page, page_size=page_size
    )
    return PagedResponse[KeywordListPayload](
        data=[list_payload(row) for row in rows],
        error=None,
        page_info=PageInfo.build(page=page, page_size=page_size, total_items=total),
        meta=build_meta(request_id),
    )


@router.get(
    "/keywords/lists/{list_id}",
    response_model=ApiResponse[KeywordListPayload],
    summary="키워드 목록 상세",
    dependencies=[Depends(require(Permission.KEYWORD_READ))],
)
def read_keyword_list(
    list_id: ListIdPath,
    service: ServiceDep,
    principal: CurrentPrincipal,
    request_id: RequestId,
) -> ApiResponse[KeywordListPayload]:
    row = service.get_list(principal=principal, list_id=list_id)
    if row is None:
        raise _not_found()
    return ok(list_payload(row), request_id)


@router.put(
    "/keywords/lists/{list_id}",
    response_model=ApiResponse[KeywordListPayload],
    summary="키워드 목록 교체",
    dependencies=[Depends(require(Permission.KEYWORD_RUN))],
)
def replace_keyword_list(
    list_id: ListIdPath,
    body: KeywordListUpdateRequest,
    service: ServiceDep,
    principal: CurrentPrincipal,
    request_id: RequestId,
) -> ApiResponse[KeywordListPayload]:
    try:
        row = service.replace_list(
            principal=principal,
            list_id=list_id,
            name=body.name,
            description=body.description,
            keywords=body.keywords,
        )
    except ValueError as exc:
        raise _invalid(str(exc)) from None
    if row is None:
        raise _not_found()
    return ok(list_payload(row), request_id)


@router.delete(
    "/keywords/lists/{list_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="키워드 목록 삭제",
    dependencies=[Depends(require(Permission.KEYWORD_RUN))],
)
def delete_keyword_list(
    list_id: ListIdPath, service: ServiceDep, principal: CurrentPrincipal
) -> Response:
    if not service.delete_list(principal=principal, list_id=list_id):
        raise _not_found()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
