"""The keyword service: what VEO reports when it can, and when it cannot.

The central case is the one VEO is in today — **no Naver credential at all.** That is not
an error and not an empty success; it is a reported state with no numbers attached.
"""

from __future__ import annotations

import httpx
import pytest
from tests.keywords.conftest import NOW, make_service
from tests.keywords.naver_fixtures import load

from veo.authz import Principal
from veo.contracts.enums import DataSource, ProviderState, ValueQuality
from veo.keywords.repository import KeywordRepository
from veo.keywords.service import KeywordService


def searchad_ok(request: httpx.Request) -> httpx.Response:
    return httpx.Response(200, json=load("searchad_keywordstool_synthetic.json"))


def datalab_ok(request: httpx.Request) -> httpx.Response:
    return httpx.Response(200, json=load("datalab_search_synthetic.json"))


# --------------------------------------------------------------------------- #
# No credential
# --------------------------------------------------------------------------- #


@pytest.fixture
def disabled_service(repository: KeywordRepository) -> KeywordService:
    return make_service(
        repository=repository, searchad_credentials=None, datalab_credentials=None
    )


def test_without_a_credential_the_provider_state_is_reported_not_hidden(
    disabled_service: KeywordService, principal: Principal
) -> None:
    result = disabled_service.lookup(principal=principal, keywords=["합성키워드-A"])
    assert result.searchad_state is ProviderState.DISABLED_NO_CREDENTIAL
    assert result.datalab_state is ProviderState.DISABLED_NO_CREDENTIAL


def test_without_a_credential_there_are_no_metrics_at_all(
    disabled_service: KeywordService, principal: Principal
) -> None:
    snapshot = disabled_service.lookup(principal=principal, keywords=["합성키워드-A"]).snapshots[0]
    assert snapshot.metrics is None
    assert snapshot.trend is None
    assert snapshot.related == ()


def test_without_a_credential_there_is_no_opportunity_score(
    disabled_service: KeywordService, principal: Principal
) -> None:
    """A score of 0 would read as "no opportunity". There is simply no score."""
    snapshot = disabled_service.lookup(principal=principal, keywords=["합성키워드-A"]).snapshots[0]
    assert snapshot.opportunity is None


def test_without_a_credential_the_reason_is_explained_in_korean(
    disabled_service: KeywordService, principal: Principal
) -> None:
    result = disabled_service.lookup(principal=principal, keywords=["합성키워드-A"])
    joined = " ".join(result.notices_ko)
    assert "자격증명" in joined
    assert "측정 불가" in joined or "측정할 수 없" in joined


def test_a_disabled_lookup_is_still_recorded_so_the_question_is_traceable(
    disabled_service: KeywordService, principal: Principal, repository: KeywordRepository
) -> None:
    result = disabled_service.lookup(principal=principal, keywords=["합성키워드-A"])
    assert result.query_id is not None
    stored = repository.load_lookup(
        organization_id=principal.organization_id, query_id=result.query_id
    )
    assert stored is not None
    assert stored.provider_state is ProviderState.DISABLED_NO_CREDENTIAL
    assert stored.metrics == ()


# --------------------------------------------------------------------------- #
# With a credential (synthetic transport)
# --------------------------------------------------------------------------- #


@pytest.fixture
def working_service(repository: KeywordRepository) -> KeywordService:
    return make_service(
        repository=repository, searchad_handler=searchad_ok, datalab_handler=datalab_ok
    )


def test_a_successful_lookup_carries_metrics_with_their_source_and_time(
    working_service: KeywordService, principal: Principal
) -> None:
    result = working_service.lookup(principal=principal, keywords=["합성키워드-A"])
    snapshot = result.snapshots[0]
    assert snapshot.metrics is not None
    assert snapshot.metrics.source is DataSource.NAVER_SEARCH_AD
    assert snapshot.metrics.collected_at == NOW
    assert snapshot.metrics.monthly_pc_searches == 1111
    assert snapshot.metrics.monthly_pc_searches_quality is ValueQuality.EXACT


def test_suppressed_and_zero_survive_the_service_layer_distinct(
    working_service: KeywordService, principal: Principal
) -> None:
    result = working_service.lookup(
        principal=principal, keywords=["합성키워드-B", "합성키워드-C"]
    )
    by_keyword = {snapshot.normalized_keyword: snapshot for snapshot in result.snapshots}

    zero = by_keyword["합성키워드-b"].metrics
    suppressed = by_keyword["합성키워드-c"].metrics
    assert zero is not None
    assert suppressed is not None

    assert zero.monthly_pc_searches == 0
    assert zero.monthly_pc_searches_quality is ValueQuality.EXACT
    assert suppressed.monthly_pc_searches is None
    assert suppressed.monthly_pc_searches_quality is ValueQuality.BELOW_PROVIDER_THRESHOLD


def test_related_keywords_come_back_with_their_source_rank(
    working_service: KeywordService, principal: Principal
) -> None:
    result = working_service.lookup(principal=principal, keywords=["합성키워드-A"])
    related = result.snapshots[0].related
    assert related
    assert [row.source_rank for row in related] == list(range(1, len(related) + 1))
    assert all(row.source is DataSource.NAVER_SEARCH_AD for row in related)


def test_a_trend_series_is_stored_apart_from_the_counts(
    working_service: KeywordService, principal: Principal
) -> None:
    result = working_service.lookup(
        principal=principal, keywords=["합성키워드-A"], include_trend=True
    )
    snapshot = result.snapshots[0]
    assert snapshot.trend is not None
    assert snapshot.trend.source is DataSource.NAVER_DATALAB
    assert snapshot.trend.points
    # The trend carries no field that could be mistaken for a count.
    assert not hasattr(snapshot.trend, "monthly_total_searches")


def test_the_opportunity_score_is_present_and_labelled_as_veos_own(
    working_service: KeywordService, principal: Principal
) -> None:
    result = working_service.lookup(
        principal=principal, keywords=["합성키워드-A"], intent_fit=0.5, content_gap=0.5
    )
    opportunity = result.snapshots[0].opportunity
    assert opportunity is not None
    assert opportunity.source is DataSource.CALCULATED
    assert opportunity.formula_version
    assert opportunity.score is not None


def test_a_provider_failure_degrades_to_no_metrics_rather_than_to_zero(
    repository: KeywordRepository, principal: Principal
) -> None:
    def failing(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, json={"title": "boom"})

    service = make_service(repository=repository, searchad_handler=failing)
    result = service.lookup(principal=principal, keywords=["합성키워드-A"], include_trend=False)
    snapshot = result.snapshots[0]
    assert snapshot.metrics is None
    assert snapshot.opportunity is None
    assert result.searchad_state is ProviderState.DEGRADED
    assert any("측정" in notice for notice in result.notices_ko)


def test_a_datalab_failure_does_not_take_the_searchad_metrics_with_it(
    repository: KeywordRepository, principal: Principal
) -> None:
    def failing(request: httpx.Request) -> httpx.Response:
        return httpx.Response(429, json={"errorMessage": "slow down"})

    service = make_service(
        repository=repository, searchad_handler=searchad_ok, datalab_handler=failing
    )
    result = service.lookup(
        principal=principal, keywords=["합성키워드-A"], include_trend=True
    )
    snapshot = result.snapshots[0]
    assert snapshot.metrics is not None
    assert snapshot.trend is None
    assert result.datalab_state is ProviderState.DEGRADED


def test_keywords_are_normalised_before_they_are_looked_up(
    working_service: KeywordService, principal: Principal
) -> None:
    result = working_service.lookup(principal=principal, keywords=["  합성키워드-A  "])
    snapshot = result.snapshots[0]
    assert snapshot.original_keyword == "  합성키워드-A  "
    assert snapshot.normalized_keyword == "합성키워드-a"


def test_an_empty_keyword_list_is_rejected(
    working_service: KeywordService, principal: Principal
) -> None:
    with pytest.raises(ValueError, match="키워드"):
        working_service.lookup(principal=principal, keywords=[])


def test_duplicate_keywords_are_looked_up_once(
    working_service: KeywordService, principal: Principal
) -> None:
    result = working_service.lookup(
        principal=principal, keywords=["합성키워드-A", "합성키워드-a", "합성키워드-A"]
    )
    assert len(result.snapshots) == 1


# --------------------------------------------------------------------------- #
# Recent keywords — never called "실시간 인기검색어"
# --------------------------------------------------------------------------- #


def test_recent_keywords_are_veos_own_observations_not_a_naver_ranking(
    working_service: KeywordService, principal: Principal
) -> None:
    working_service.lookup(principal=principal, keywords=["합성키워드-A"])
    report = working_service.recent_keywords(principal=principal)

    assert report.source is DataSource.VEO_INTERNAL
    assert report.title_ko in {"VEO 최근 조회 키워드", "최근 24시간 급상승 키워드"}
    assert "실시간 인기검색어" not in report.title_ko
    assert "실시간 인기검색어" not in report.methodology_ko


def test_recent_keywords_state_their_window_scope_and_de_identification(
    working_service: KeywordService, principal: Principal
) -> None:
    working_service.lookup(principal=principal, keywords=["합성키워드-A"])
    report = working_service.recent_keywords(principal=principal, window_hours=24)

    assert report.window_hours == 24
    assert report.period_start < report.period_end
    assert report.scope_ko
    assert report.refreshed_at == NOW
    assert report.de_identification_ko


def test_recent_keywords_only_count_this_organizations_lookups(
    working_service: KeywordService, principal: Principal, repository: KeywordRepository
) -> None:
    import uuid as _uuid

    from veo.contracts.enums import Role

    other = Principal(
        user_id=_uuid.uuid4(),
        organization_id=_uuid.uuid4(),
        roles=frozenset({Role.ANALYST}),
        session_id="other",
    )
    working_service.lookup(principal=principal, keywords=["합성키워드-A"])
    working_service.lookup(principal=other, keywords=["합성키워드-B"])

    mine = working_service.recent_keywords(principal=principal)
    assert [entry.normalized_keyword for entry in mine.entries] == ["합성키워드-a"]


def test_recent_keywords_suppress_entries_below_the_de_identification_threshold(
    working_service: KeywordService, principal: Principal
) -> None:
    """A keyword looked up once by one user is that user's business, not a trend."""
    working_service.lookup(principal=principal, keywords=["합성키워드-A"])
    report = working_service.recent_keywords(principal=principal, min_lookups=2)
    assert report.entries == ()
    assert report.suppressed_count == 1


# --------------------------------------------------------------------------- #
# Keyword lists
# --------------------------------------------------------------------------- #


def test_a_keyword_list_round_trips(
    working_service: KeywordService, principal: Principal
) -> None:
    import uuid as _uuid

    project_id = _uuid.uuid4()
    created = working_service.create_list(
        principal=principal,
        project_id=project_id,
        name="합성 목록",
        description="테스트",
        keywords=["합성키워드-A", "합성키워드-B"],
    )
    fetched = working_service.get_list(principal=principal, list_id=created.id)
    assert fetched is not None
    assert fetched.name == "합성 목록"
    assert fetched.keywords == ("합성키워드-a", "합성키워드-b")


def test_another_organizations_list_is_not_found(
    working_service: KeywordService, principal: Principal
) -> None:
    import uuid as _uuid

    from veo.contracts.enums import Role

    other = Principal(
        user_id=_uuid.uuid4(),
        organization_id=_uuid.uuid4(),
        roles=frozenset({Role.ANALYST}),
        session_id="other",
    )
    created = working_service.create_list(
        principal=other,
        project_id=_uuid.uuid4(),
        name="남의 목록",
        description=None,
        keywords=["합성키워드-A"],
    )
    assert working_service.get_list(principal=principal, list_id=created.id) is None
