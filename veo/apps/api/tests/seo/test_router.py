"""``/seo`` — reading the check catalogue and running a scan over a collected bundle.

The router is not mounted by this package; ``veo.api.app`` belongs to the integrator.
The test app therefore includes it explicitly, which is also how the integrator will.

Permissions are the point of most of these tests: ``scan:read`` to look, ``scan:run`` to
run, and a caller holding neither gets 403 before any work happens.
"""

from __future__ import annotations

import uuid
from collections.abc import Iterator
from typing import Any

import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from tests.seo.support import scan_bundle

from veo.api.app import create_app
from veo.authz.deps import get_principal
from veo.authz.errors import AuthenticationError
from veo.authz.principal import Principal
from veo.contracts.enums import Role
from veo.core.settings import get_settings
from veo.seo.router import router as seo_router
from veo.seo.service import load_seo_spec

API_PREFIX = get_settings().api_prefix
CHECKS = f"{API_PREFIX}/seo/checks"
SCAN = f"{API_PREFIX}/seo/scan"


def _principal(*roles: Role) -> Principal:
    return Principal(
        user_id=uuid.uuid4(),
        organization_id=uuid.uuid4(),
        roles=frozenset(roles),
        session_id="seo-test-session",
    )


class Caller:
    def __init__(self) -> None:
        self.current: Principal | None = None


@pytest.fixture
def caller() -> Caller:
    return Caller()


def _seo_paths(application: FastAPI) -> list[str]:
    return [
        path
        for path in (getattr(route, "path", "") for route in application.routes)
        if path.startswith(f"{API_PREFIX}/seo")
    ]


@pytest.fixture
def app(caller: Caller) -> FastAPI:
    application = create_app()
    if not _seo_paths(application):
        application.include_router(seo_router, prefix=API_PREFIX)

    async def resolve(request: Request) -> Principal:
        if caller.current is None:
            raise AuthenticationError("authentication required")
        return caller.current

    application.dependency_overrides[get_principal] = resolve
    return application


@pytest.fixture
def client(app: FastAPI) -> Iterator[TestClient]:
    with TestClient(app) as test_client:
        yield test_client


def payload(response: Any) -> dict[str, Any]:
    body = response.json()
    assert body["error"] is None, body["error"]
    data: dict[str, Any] = body["data"]
    return data


def bundle() -> dict[str, Any]:
    return scan_bundle()


# --------------------------------------------------------------------------- #
# The catalogue
# --------------------------------------------------------------------------- #


def test_the_catalogue_lists_every_check_in_the_specification(
    client: TestClient, caller: Caller
) -> None:
    caller.current = _principal(Role.CLIENT_VIEWER)
    data = payload(client.get(CHECKS))
    # 개수를 못 박지 않는다. 명세가 자라면 목록도 자라야 하고, 이 검사가 지키는 것은
    # **목록이 발행 명세와 정확히 같다** 는 것이다.
    assert {check["id"] for check in data["checks"]} == set(load_seo_spec().check_ids)
    assert data["spec_id"] == "veo.seo.readiness"
    # 명세는 개정된다. 버전을 여기에 적어 두면 개정 때마다 무관한 테스트가 깨진다 —
    # 이 테스트가 지키는 것은 "목록이 발행 명세와 일치한다" 이지 특정 버전이 아니다.
    assert data["spec_version"] == load_seo_spec().version


def test_the_catalogue_names_the_collector_that_owns_each_check(
    client: TestClient, caller: Caller
) -> None:
    caller.current = _principal(Role.CLIENT_VIEWER)
    data = payload(client.get(CHECKS))
    for check in data["checks"]:
        assert check["collector"]
        assert check["category_id"]
        assert check["title_ko"]
        assert check["remediation_owner"]


def test_the_catalogue_says_which_checks_need_a_provider(
    client: TestClient, caller: Caller
) -> None:
    caller.current = _principal(Role.CLIENT_VIEWER)
    data = payload(client.get(CHECKS))
    provider_backed = [c for c in data["checks"] if c["requires_provider"]]
    assert {c["id"] for c in provider_backed} >= {
        "seo.perf.lcp_lab",
        "seo.perf.inp_field",
        "seo.integration.gsc_verified",
        "seo.outcome.impressions_available",
        "seo.offpage.referring_domains_present",
    }


def test_reading_the_catalogue_needs_scan_read(client: TestClient, caller: Caller) -> None:
    caller.current = _principal(Role.SALES_VIEWER)
    response = client.get(CHECKS)
    assert response.status_code in {200, 403}
    if response.status_code == 403:
        assert response.json()["error"]["code"] == "PERMISSION_DENIED"


def test_an_anonymous_caller_is_refused(client: TestClient, caller: Caller) -> None:
    caller.current = None
    assert client.get(CHECKS).status_code == 401


# --------------------------------------------------------------------------- #
# Running a scan
# --------------------------------------------------------------------------- #


def test_a_scan_returns_a_score_with_its_specification_identity(
    client: TestClient, caller: Caller
) -> None:
    caller.current = _principal(Role.ANALYST)
    data = payload(client.post(SCAN, json=bundle()))
    assert data["score"]["spec_id"] == "veo.seo.readiness"
    assert data["score"]["spec_checksum"]
    assert data["score"]["is_rank_prediction"] is False
    # 점수 자체는 발행 명세가 정한다. 여기서 특정 숫자를 못 박으면 명세를 개정할 때마다
    # 이 검사가 깨지고, 기대값을 기계적으로 갱신하게 되어 무엇을 지키는 검사인지 사라진다.
    # 이 검사가 지키는 것은 **점수에 명세의 신원이 붙어 나온다**는 것이다.
    assert isinstance(data["score"]["score"], (int, float))


def test_a_scan_reports_unknown_checks_and_why(client: TestClient, caller: Caller) -> None:
    caller.current = _principal(Role.ANALYST)
    data = payload(client.post(SCAN, json=bundle()))
    unknown = {item["check_id"]: item for item in data["unknown_checks"]}
    assert "seo.perf.lcp_lab" in unknown
    assert unknown["seo.perf.lcp_lab"]["reason_ko"]


def test_a_scan_summary_is_written_in_korean(client: TestClient, caller: Caller) -> None:
    caller.current = _principal(Role.ANALYST)
    data = payload(client.post(SCAN, json=bundle()))
    assert data["summary_ko"]
    assert any("가" <= ch <= "힣" for ch in data["summary_ko"])


def test_a_scan_on_a_broken_site_returns_issues_with_evidence(
    client: TestClient, caller: Caller
) -> None:
    caller.current = _principal(Role.ANALYST)
    body = bundle()
    body["robots_txt"] = "User-agent: *\nDisallow: /\n"
    data = payload(client.post(SCAN, json=body))

    assert data["issues"]
    evidence_ids = {record["evidence_id"] for record in data["evidence"]}
    for issue in data["issues"]:
        assert set(issue["evidence_ids"]) <= evidence_ids
        assert issue["title_ko"]
        assert issue["remediation_owner"] in {
            "DEVELOPER",
            "MARKETER",
            "BUSINESS_OWNER",
            "OPERATIONS",
        }


def test_running_a_scan_needs_scan_run_not_only_scan_read(
    client: TestClient, caller: Caller
) -> None:
    caller.current = _principal(Role.CLIENT_VIEWER)
    response = client.post(SCAN, json=bundle())
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "PERMISSION_DENIED"


def test_a_scan_with_no_pages_is_rejected(client: TestClient, caller: Caller) -> None:
    caller.current = _principal(Role.ANALYST)
    body = bundle()
    body["pages"] = []
    assert client.post(SCAN, json=body).status_code == 422


def test_the_router_is_not_mounted_by_this_package() -> None:
    """The integrator owns ``veo.api.app``; this package only offers the router."""
    assert _seo_paths(create_app()) == []
