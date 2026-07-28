"""DataLab relative interest, and the structural wall between an index and a count.

A DataLab ``ratio`` is a relative interest index scaled inside its own query window. It is
not a number of searches. The tests below check that separation *structurally* — by type
annotation and by module dependency — rather than by reviewer discipline, because the
mistake this prevents (a 0-100 index rendered as "월간 검색량 100회") is silent.
"""

from __future__ import annotations

import ast
import dataclasses
import inspect
import typing
from datetime import UTC, date, datetime

import httpx
import pytest
from pydantic import SecretStr
from tests.keywords.naver_fixtures import load

from veo.contracts.enums import DataSource, ProviderState
from veo.providers.naver import datalab as datalab_module
from veo.providers.naver import searchad as searchad_module
from veo.providers.naver.datalab import (
    DATALAB_PATH,
    DataLabCredentials,
    KeywordTrendSeries,
    NaverDataLabClient,
    RelativeIndex,
    TrendPoint,
    normalize_datalab,
)
from veo.providers.naver.errors import UNKNOWN, NaverSchemaError
from veo.providers.naver.searchad import SearchCount

COLLECTED_AT = datetime(2026, 7, 28, 3, 0, tzinfo=UTC)
CREDENTIALS = DataLabCredentials(
    client_id=SecretStr("synthetic-client-id"),
    client_secret=SecretStr("synthetic-client-secret"),
)


def series() -> tuple[KeywordTrendSeries, ...]:
    return normalize_datalab(
        load("datalab_search_synthetic.json"),
        collected_at=COLLECTED_AT,
        device="ALL",
    )


# --------------------------------------------------------------------------- #
# Normalisation
# --------------------------------------------------------------------------- #


def test_each_group_becomes_one_series() -> None:
    assert [entry.keyword for entry in series()] == ["합성키워드-A", "합성키워드-B"]


def test_points_carry_a_relative_index_not_a_count() -> None:
    first = series()[0]
    assert first.points[0] == TrendPoint(
        period_start=date(2026, 1, 1), relative_index=RelativeIndex(11.1)
    )
    assert first.points[-1].relative_index.value == 100.0
    assert first.points[-1].relative_index.source is DataSource.NAVER_DATALAB


def test_series_states_its_window_and_unit() -> None:
    first = series()[0]
    assert first.period_start == date(2026, 1, 1)
    assert first.period_end == date(2026, 6, 30)
    assert first.time_unit == "month"
    assert first.device == "ALL"
    assert first.collected_at == COLLECTED_AT


def test_series_carries_the_basis_note_in_korean() -> None:
    note = series()[0].index_basis_note_ko
    assert note
    assert "검색량" in note or "검색 횟수" in note


def test_a_response_without_results_is_a_schema_error() -> None:
    with pytest.raises(NaverSchemaError):
        normalize_datalab({"startDate": "2026-01-01"}, collected_at=COLLECTED_AT, device="ALL")


def test_a_ratio_outside_the_documented_range_is_rejected() -> None:
    payload = {
        "startDate": "2026-01-01",
        "endDate": "2026-01-31",
        "timeUnit": "month",
        "results": [
            {
                "title": "합성그룹",
                "keywords": ["합성키워드"],
                "data": [{"period": "2026-01-01", "ratio": 140.0}],
            }
        ],
    }
    with pytest.raises(NaverSchemaError):
        normalize_datalab(payload, collected_at=COLLECTED_AT, device="ALL")


def test_relative_index_rejects_a_value_outside_zero_to_one_hundred() -> None:
    with pytest.raises(ValueError, match="0"):
        RelativeIndex(101.0)
    with pytest.raises(ValueError, match="0"):
        RelativeIndex(-1.0)


# --------------------------------------------------------------------------- #
# The structural wall
# --------------------------------------------------------------------------- #


def test_a_relative_index_is_not_a_search_count() -> None:
    index = RelativeIndex(50.0)
    assert not isinstance(index, SearchCount)
    assert not isinstance(index, int | float)


def test_a_relative_index_cannot_be_coerced_into_a_number() -> None:
    """No ``__int__``/``__float__``/``__index__``: an index cannot slip into arithmetic.

    Without this, ``int(index)`` succeeds and a 0-100 interest score lands in a column
    that means "monthly searches" with nothing to show it happened.
    """
    index = RelativeIndex(50.0)
    for protocol in ("__int__", "__float__", "__index__", "__add__", "__radd__"):
        assert not hasattr(index, protocol), protocol
    with pytest.raises(TypeError):
        int(index)  # type: ignore[call-overload]
    with pytest.raises(TypeError):
        index + 1  # type: ignore[operator]


def searchad_dataclasses() -> list[type]:
    return [
        obj
        for _, obj in inspect.getmembers(searchad_module, inspect.isclass)
        if dataclasses.is_dataclass(obj) and obj.__module__ == searchad_module.__name__
    ]


def datalab_dataclasses() -> list[type]:
    return [
        obj
        for _, obj in inspect.getmembers(datalab_module, inspect.isclass)
        if dataclasses.is_dataclass(obj) and obj.__module__ == datalab_module.__name__
    ]


def test_no_searchad_type_has_a_field_that_can_hold_a_relative_index() -> None:
    for cls in searchad_dataclasses():
        hints = typing.get_type_hints(cls)
        for name, hint in hints.items():
            rendered = str(hint)
            assert "RelativeIndex" not in rendered, f"{cls.__name__}.{name}"
            assert "TrendPoint" not in rendered, f"{cls.__name__}.{name}"


def test_no_datalab_type_has_a_field_that_can_hold_a_search_count() -> None:
    for cls in datalab_dataclasses():
        hints = typing.get_type_hints(cls)
        for name, hint in hints.items():
            rendered = str(hint)
            assert "SearchCount" not in rendered, f"{cls.__name__}.{name}"


def test_the_two_provider_modules_do_not_import_each_other() -> None:
    """Independent modules, so no refactor can quietly route a ratio into a count."""
    searchad_imports = _imported_module_names(searchad_module)
    datalab_imports = _imported_module_names(datalab_module)
    assert not any("datalab" in name for name in searchad_imports)
    assert not any("searchad" in name for name in datalab_imports)


def _imported_module_names(module: object) -> set[str]:
    tree = ast.parse(inspect.getsource(module))  # type: ignore[arg-type]
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module)
            names.update(f"{node.module}.{alias.name}" for alias in node.names)
    return names


def test_datalab_series_has_no_field_whose_name_suggests_a_count() -> None:
    forbidden = ("searches", "search_count", "volume", "qc_cnt", "clicks")
    for cls in datalab_dataclasses():
        for field in dataclasses.fields(cls):
            lowered = field.name.lower()
            for token in forbidden:
                assert token not in lowered, f"{cls.__name__}.{field.name}"


# --------------------------------------------------------------------------- #
# The client
# --------------------------------------------------------------------------- #


def build_client(handler: object, **kwargs: object) -> NaverDataLabClient:
    return NaverDataLabClient(
        credentials=CREDENTIALS,
        transport=httpx.MockTransport(handler),  # type: ignore[arg-type]
        clock=lambda: COLLECTED_AT,
        **kwargs,  # type: ignore[arg-type]
    )


def test_client_sends_the_documented_headers_and_body() -> None:
    seen: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["path"] = request.url.path
        seen["headers"] = dict(request.headers)
        seen["body"] = request.read().decode("utf-8")
        return httpx.Response(200, json=load("datalab_search_synthetic.json"))

    outcome = build_client(handler).lookup_trend(
        ["합성키워드-A"],
        start_date=date(2026, 1, 1),
        end_date=date(2026, 6, 30),
        time_unit="month",
    )
    assert outcome.value is not UNKNOWN
    assert seen["path"] == DATALAB_PATH
    headers = seen["headers"]
    assert isinstance(headers, dict)
    assert headers["x-naver-client-id"] == "synthetic-client-id"
    assert headers["x-naver-client-secret"] == "synthetic-client-secret"
    body = seen["body"]
    assert isinstance(body, str)
    assert "keywordGroups" in body
    assert "2026-01-01" in body


@pytest.mark.parametrize("status", [401, 403, 429, 500])
def test_a_failing_call_returns_unknown(status: int) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status, json={"errorMessage": "no"})

    client = build_client(handler, sleep=lambda seconds: None)
    outcome = client.lookup_trend(
        ["합성키워드-A"],
        start_date=date(2026, 1, 1),
        end_date=date(2026, 6, 30),
        time_unit="month",
    )
    assert outcome.value is UNKNOWN
    assert outcome.failure is not None


def test_client_without_a_credential_is_disabled_and_never_dials() -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(200, json={})

    client = NaverDataLabClient(
        credentials=None, transport=httpx.MockTransport(handler), clock=lambda: COLLECTED_AT
    )
    assert client.state is ProviderState.DISABLED_NO_CREDENTIAL
    outcome = client.lookup_trend(
        ["합성키워드-A"],
        start_date=date(2026, 1, 1),
        end_date=date(2026, 6, 30),
        time_unit="month",
    )
    assert calls == 0
    assert outcome.value is UNKNOWN
    assert outcome.failure is not None
    assert outcome.failure.provider_state is ProviderState.DISABLED_NO_CREDENTIAL
