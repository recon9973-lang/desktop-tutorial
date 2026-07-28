"""The HTTP surface.

Two things are being checked here beyond the usual routing: that the permission matrix is
actually applied, and that **a response with no credential contains no numbers**. The
second is asserted by walking the serialised payload rather than by naming fields, so a
field added later cannot quietly reintroduce a fabricated figure.
"""

from __future__ import annotations

import csv
import io
import uuid
import zipfile
from typing import Any
from xml.etree import ElementTree

import httpx
import pytest
from fastapi.testclient import TestClient
from tests.keywords.conftest import API_PREFIX, make_service
from tests.keywords.naver_fixtures import load

from veo.authz import Principal
from veo.contracts.enums import Role
from veo.keywords.repository import KeywordRepository
from veo.keywords.service import KeywordService


def searchad_ok(request: httpx.Request) -> httpx.Response:
    return httpx.Response(200, json=load("searchad_keywordstool_synthetic.json"))


def datalab_ok(request: httpx.Request) -> httpx.Response:
    return httpx.Response(200, json=load("datalab_search_synthetic.json"))


@pytest.fixture
def working(
    repository: KeywordRepository, service_box: dict[str, KeywordService]
) -> KeywordService:
    service = make_service(
        repository=repository, searchad_handler=searchad_ok, datalab_handler=datalab_ok
    )
    service_box["service"] = service
    return service


@pytest.fixture
def disabled(
    repository: KeywordRepository, service_box: dict[str, KeywordService]
) -> KeywordService:
    service = make_service(
        repository=repository, searchad_credentials=None, datalab_credentials=None
    )
    service_box["service"] = service
    return service


def field_names(node: Any) -> set[str]:
    """Every key appearing anywhere in a serialised payload."""
    names: set[str] = set()
    if isinstance(node, dict):
        for key, value in node.items():
            names.add(key)
            names |= field_names(value)
    elif isinstance(node, list):
        for value in node:
            names |= field_names(value)
    return names


def numbers_under(node: Any, path: str = "") -> list[str]:
    """Every path in ``node`` that holds a number. Booleans are not numbers here."""
    found: list[str] = []
    if isinstance(node, dict):
        for key, value in node.items():
            found.extend(numbers_under(value, f"{path}.{key}"))
    elif isinstance(node, list):
        for index, value in enumerate(node):
            found.extend(numbers_under(value, f"{path}[{index}]"))
    elif isinstance(node, bool):
        pass
    elif isinstance(node, int | float):
        found.append(path)
    return found


# --------------------------------------------------------------------------- #
# Permissions
# --------------------------------------------------------------------------- #


def test_lookup_requires_keyword_run(
    client: TestClient,
    principal_box: dict[str, Principal],
    principal: Principal,
    working: KeywordService,
) -> None:
    read_only = Principal(
        user_id=principal.user_id,
        organization_id=principal.organization_id,
        roles=frozenset({Role.SALES_VIEWER}),
        session_id="read-only",
    )
    principal_box["principal"] = read_only
    response = client.post(f"{API_PREFIX}/keywords/lookups", json={"keywords": ["합성키워드-A"]})
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "PERMISSION_DENIED"


def test_reading_a_lookup_requires_only_keyword_read(
    client: TestClient,
    principal_box: dict[str, Principal],
    principal: Principal,
    working: KeywordService,
) -> None:
    created = client.post(
        f"{API_PREFIX}/keywords/lookups", json={"keywords": ["합성키워드-A"]}
    ).json()
    query_id = created["data"]["query_id"]

    principal_box["principal"] = Principal(
        user_id=principal.user_id,
        organization_id=principal.organization_id,
        roles=frozenset({Role.SALES_VIEWER}),
        session_id="read-only",
    )
    response = client.get(f"{API_PREFIX}/keywords/lookups/{query_id}")
    assert response.status_code == 200


def test_creating_a_keyword_list_requires_keyword_run(
    client: TestClient,
    principal_box: dict[str, Principal],
    principal: Principal,
    working: KeywordService,
) -> None:
    principal_box["principal"] = Principal(
        user_id=principal.user_id,
        organization_id=principal.organization_id,
        roles=frozenset({Role.SALES_VIEWER}),
        session_id="read-only",
    )
    response = client.post(
        f"{API_PREFIX}/keywords/lists",
        json={"project_id": str(uuid.uuid4()), "name": "합성 목록", "keywords": ["합성키워드-A"]},
    )
    assert response.status_code == 403


# --------------------------------------------------------------------------- #
# No credential: a state, not an error, and not a number
# --------------------------------------------------------------------------- #


def test_a_lookup_without_a_credential_succeeds_and_reports_the_state(
    client: TestClient, disabled: KeywordService
) -> None:
    response = client.post(f"{API_PREFIX}/keywords/lookups", json={"keywords": ["합성키워드-A"]})
    assert response.status_code == 200
    body = response.json()
    assert body["error"] is None

    states = {entry["provider"]: entry for entry in body["data"]["providers"]}
    assert states["NAVER_SEARCH_AD"]["state"] == "DISABLED_NO_CREDENTIAL"
    assert states["NAVER_DATALAB"]["state"] == "DISABLED_NO_CREDENTIAL"
    assert states["NAVER_SEARCH_AD"]["reason_ko"]


def test_a_lookup_without_a_credential_returns_no_numbers_at_all(
    client: TestClient, disabled: KeywordService
) -> None:
    body = client.post(
        f"{API_PREFIX}/keywords/lookups", json={"keywords": ["합성키워드-A", "합성키워드-B"]}
    ).json()
    assert numbers_under(body["data"]["keywords"]) == []


def test_a_lookup_without_a_credential_explains_itself_in_korean(
    client: TestClient, disabled: KeywordService
) -> None:
    body = client.post(
        f"{API_PREFIX}/keywords/lookups", json={"keywords": ["합성키워드-A"]}
    ).json()
    assert body["data"]["notices_ko"]
    assert any("자격증명" in notice for notice in body["data"]["notices_ko"])


# --------------------------------------------------------------------------- #
# Source badges and freshness
# --------------------------------------------------------------------------- #


def test_every_measured_value_carries_its_source(
    client: TestClient, working: KeywordService
) -> None:
    body = client.post(
        f"{API_PREFIX}/keywords/lookups", json={"keywords": ["합성키워드-A"]}
    ).json()
    metrics = body["data"]["keywords"][0]["metrics"]
    assert metrics["source"] == "NAVER_SEARCH_AD"
    assert metrics["monthly_pc_searches"]["source"] == "NAVER_SEARCH_AD"
    assert metrics["monthly_total_searches"]["source"] == "CALCULATED"
    assert body["data"]["keywords"][0]["trend"]["source"] == "NAVER_DATALAB"
    assert body["data"]["keywords"][0]["opportunity"]["source"] == "CALCULATED"


def test_every_measured_value_carries_its_quality(
    client: TestClient, working: KeywordService
) -> None:
    body = client.post(
        f"{API_PREFIX}/keywords/lookups", json={"keywords": ["합성키워드-C"]}
    ).json()
    metrics = body["data"]["keywords"][0]["metrics"]
    assert metrics["monthly_pc_searches"]["value"] is None
    assert metrics["monthly_pc_searches"]["quality"] == "BELOW_PROVIDER_THRESHOLD"
    assert metrics["monthly_pc_searches"]["note_ko"]


def test_the_response_meta_carries_source_attribution_and_freshness(
    client: TestClient, working: KeywordService
) -> None:
    body = client.post(
        f"{API_PREFIX}/keywords/lookups", json={"keywords": ["합성키워드-A"]}
    ).json()
    sources = {entry["source"] for entry in body["meta"]["sources"]}
    assert "NAVER_SEARCH_AD" in sources
    assert all(entry["collected_at"] for entry in body["meta"]["sources"])
    assert body["data"]["keywords"][0]["metrics"]["collected_at"]
    assert body["data"]["keywords"][0]["metrics"]["age_seconds"] is not None


def test_a_datalab_trend_is_never_labelled_as_a_search_count(
    client: TestClient, working: KeywordService
) -> None:
    body = client.post(
        f"{API_PREFIX}/keywords/lookups", json={"keywords": ["합성키워드-A"]}
    ).json()
    trend = body["data"]["keywords"][0]["trend"]
    assert trend["unit"] == "RELATIVE_INDEX_0_100"
    # The note has to say, in Korean, that this is not a search volume.
    assert "검색량" in trend["note_ko"]
    # ...and no *field* in the payload may be named as though it held one.
    for name in field_names(trend):
        for forbidden in ("searches", "search_count", "volume", "clicks", "qc_cnt"):
            assert forbidden not in name.lower(), name


# --------------------------------------------------------------------------- #
# Related keywords: filter, sort, page
# --------------------------------------------------------------------------- #


def test_related_keywords_are_paged(client: TestClient, working: KeywordService) -> None:
    created = client.post(
        f"{API_PREFIX}/keywords/lookups", json={"keywords": ["합성키워드-A"]}
    ).json()
    query_id = created["data"]["query_id"]

    response = client.get(
        f"{API_PREFIX}/keywords/lookups/{query_id}/related", params={"page": 1, "page_size": 2}
    )
    assert response.status_code == 200
    body = response.json()
    assert len(body["data"]) <= 2
    assert body["page_info"]["page"] == 1


def test_related_keywords_can_be_filtered_by_substring(
    client: TestClient, working: KeywordService
) -> None:
    created = client.post(
        f"{API_PREFIX}/keywords/lookups", json={"keywords": ["합성키워드-A"]}
    ).json()
    query_id = created["data"]["query_id"]

    body = client.get(
        f"{API_PREFIX}/keywords/lookups/{query_id}/related", params={"contains": "-C"}
    ).json()
    assert body["data"]
    assert all("-c" in row["related_keyword"].lower() for row in body["data"])


def test_related_keywords_sorted_by_volume_put_unmeasured_rows_last(
    client: TestClient, working: KeywordService
) -> None:
    """A row with no number must not sort as if it were zero."""
    created = client.post(
        f"{API_PREFIX}/keywords/lookups", json={"keywords": ["합성키워드-A"]}
    ).json()
    query_id = created["data"]["query_id"]

    rows = client.get(
        f"{API_PREFIX}/keywords/lookups/{query_id}/related",
        params={"sort": "-monthly_total_searches", "page_size": 50},
    ).json()["data"]

    measured = [row for row in rows if row["monthly_total_searches"]["value"] is not None]
    unmeasured = [row for row in rows if row["monthly_total_searches"]["value"] is None]
    assert rows == measured + unmeasured


def test_an_unknown_sort_key_is_rejected(client: TestClient, working: KeywordService) -> None:
    created = client.post(
        f"{API_PREFIX}/keywords/lookups", json={"keywords": ["합성키워드-A"]}
    ).json()
    query_id = created["data"]["query_id"]
    response = client.get(
        f"{API_PREFIX}/keywords/lookups/{query_id}/related", params={"sort": "drop table"}
    )
    assert response.status_code == 422


# --------------------------------------------------------------------------- #
# Recent keywords
# --------------------------------------------------------------------------- #


def test_recent_keywords_never_use_the_forbidden_name(
    client: TestClient, working: KeywordService
) -> None:
    client.post(f"{API_PREFIX}/keywords/lookups", json={"keywords": ["합성키워드-A"]})
    body = client.get(f"{API_PREFIX}/keywords/recent").json()
    assert "실시간 인기검색어" not in repr(body)
    assert body["data"]["title_ko"] == "VEO 최근 조회 키워드"
    assert body["data"]["source"] == "VEO_INTERNAL"
    assert body["data"]["window_hours"] == 24
    assert body["data"]["refreshed_at"]
    assert body["data"]["scope_ko"]
    assert body["data"]["de_identification_ko"]


def test_the_whole_openapi_document_never_says_the_forbidden_name(
    client: TestClient, working: KeywordService
) -> None:
    document = client.get("/openapi.json").text
    assert "실시간 인기검색어" not in document


# --------------------------------------------------------------------------- #
# Export
# --------------------------------------------------------------------------- #


def test_csv_export_carries_the_source_and_quality_of_every_value(
    client: TestClient, working: KeywordService
) -> None:
    created = client.post(
        f"{API_PREFIX}/keywords/lookups", json={"keywords": ["합성키워드-A", "합성키워드-C"]}
    ).json()
    query_id = created["data"]["query_id"]

    response = client.get(
        f"{API_PREFIX}/keywords/lookups/{query_id}/export", params={"format": "csv"}
    )
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    assert "attachment" in response.headers["content-disposition"]

    text = response.content.decode("utf-8-sig")
    rows = list(csv.DictReader(io.StringIO(text)))
    assert rows
    assert "monthly_pc_searches" in rows[0]
    assert "monthly_pc_searches_quality" in rows[0]
    assert "source" in rows[0]
    assert "collected_at" in rows[0]

    suppressed = next(row for row in rows if row["normalized_keyword"] == "합성키워드-c")
    assert suppressed["monthly_pc_searches"] == ""
    assert suppressed["monthly_pc_searches_quality"] == "BELOW_PROVIDER_THRESHOLD"


def test_csv_export_never_writes_zero_for_an_unmeasured_value(
    client: TestClient, working: KeywordService
) -> None:
    created = client.post(
        f"{API_PREFIX}/keywords/lookups", json={"keywords": ["합성키워드-D"]}
    ).json()
    query_id = created["data"]["query_id"]
    text = client.get(
        f"{API_PREFIX}/keywords/lookups/{query_id}/export", params={"format": "csv"}
    ).content.decode("utf-8-sig")
    row = next(iter(csv.DictReader(io.StringIO(text))))
    assert row["monthly_pc_searches"] == ""
    assert row["monthly_pc_searches_quality"] == "SUPPRESSED_BY_PROVIDER"


def test_csv_export_neutralises_formula_injection(
    client: TestClient, repository: KeywordRepository, service_box: dict[str, KeywordService]
) -> None:
    """A keyword beginning with ``=`` must not execute when the file is opened."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={"keywordList": [{"relKeyword": "=cmd|'/c calc'!A1", "monthlyPcQcCnt": 1111}]},
        )

    service_box["service"] = make_service(repository=repository, searchad_handler=handler)
    created = client.post(
        f"{API_PREFIX}/keywords/lookups",
        json={"keywords": ["=cmd|'/c calc'!A1"], "include_trend": False},
    ).json()
    query_id = created["data"]["query_id"]
    text = client.get(
        f"{API_PREFIX}/keywords/lookups/{query_id}/export", params={"format": "csv"}
    ).content.decode("utf-8-sig")
    assert "\n=cmd" not in text
    assert "'=cmd" in text or "\t=cmd" in text


def test_xlsx_export_is_a_real_workbook(client: TestClient, working: KeywordService) -> None:
    created = client.post(
        f"{API_PREFIX}/keywords/lookups", json={"keywords": ["합성키워드-A"]}
    ).json()
    query_id = created["data"]["query_id"]

    response = client.get(
        f"{API_PREFIX}/keywords/lookups/{query_id}/export", params={"format": "xlsx"}
    )
    assert response.status_code == 200
    assert response.headers["content-type"].startswith(
        "application/vnd.openxmlformats-officedocument"
    )

    with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
        assert archive.testzip() is None
        names = set(archive.namelist())
        assert {
            "[Content_Types].xml",
            "_rels/.rels",
            "xl/workbook.xml",
            "xl/_rels/workbook.xml.rels",
            "xl/worksheets/sheet1.xml",
        } <= names

        # Every declared part exists, and every part is well-formed XML. Without this a
        # typo in a namespace or a content type produces a file that only fails when a
        # human opens it in Excel — which is not a place VEO can afford to find out.
        # S314: the XML being parsed is the workbook this test just produced, not
        # untrusted input, so the stdlib parser is the right tool here.
        content_types = ElementTree.fromstring(  # noqa: S314
            archive.read("[Content_Types].xml")
        )
        declared = {
            element.attrib["PartName"].lstrip("/")
            for element in content_types
            if element.tag.endswith("Override")
        }
        assert declared <= names
        for part in names:
            ElementTree.fromstring(archive.read(part))  # noqa: S314

        sheet = archive.read("xl/worksheets/sheet1.xml").decode("utf-8")
        assert "합성키워드-a" in sheet
        assert "1111" in sheet


def test_an_unknown_export_format_is_rejected(
    client: TestClient, working: KeywordService
) -> None:
    created = client.post(
        f"{API_PREFIX}/keywords/lookups", json={"keywords": ["합성키워드-A"]}
    ).json()
    query_id = created["data"]["query_id"]
    response = client.get(
        f"{API_PREFIX}/keywords/lookups/{query_id}/export", params={"format": "pdf"}
    )
    assert response.status_code == 422


# --------------------------------------------------------------------------- #
# Not found, and cross-tenant reads
# --------------------------------------------------------------------------- #


def test_an_unknown_lookup_is_not_found(client: TestClient, working: KeywordService) -> None:
    response = client.get(f"{API_PREFIX}/keywords/lookups/{uuid.uuid4()}")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NOT_FOUND"


def test_another_organizations_lookup_is_not_found_not_forbidden(
    client: TestClient,
    principal: Principal,
    principal_box: dict[str, Principal],
    working: KeywordService,
) -> None:
    created = client.post(
        f"{API_PREFIX}/keywords/lookups", json={"keywords": ["합성키워드-A"]}
    ).json()
    query_id = created["data"]["query_id"]

    principal_box["principal"] = Principal(
        user_id=uuid.uuid4(),
        organization_id=uuid.uuid4(),
        roles=frozenset({Role.SUPER_ADMIN}),
        session_id="other-org",
    )
    response = client.get(f"{API_PREFIX}/keywords/lookups/{query_id}")
    assert response.status_code == 404


def test_the_router_is_reachable_in_the_assembled_application() -> None:
    """The integrator has mounted this router; confirm it is actually served.

    Inverted at integration. The previous version asserted the router was *not* mounted
    by inspecting ``app.routes`` — which cannot detect an included router on this FastAPI
    version, so it passed either way. ``openapi()`` is the honest source of truth.
    """
    from veo.api.app import create_app

    paths = create_app().openapi()["paths"]
    assert any(path.startswith("/api/keywords") for path in paths)
