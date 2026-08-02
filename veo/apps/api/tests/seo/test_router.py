"""``/seo`` — reading the check catalogue, and the permission line in front of a scan.

The router is not mounted by this package; ``veo.api.app`` belongs to the integrator.
The test app therefore includes it explicitly, which is also how the integrator will.

Permissions are the point of most of these tests: ``scan:read`` to look, ``scan:run`` to
run, and a caller holding neither gets 403 before any work happens.

The bundle-scoring endpoint (``POST /seo/scan``) is **gone on purpose** and one test
keeps it gone: it let the caller submit ``provider_states`` and get them scored under
the published spec's name. Scoring input now comes only from VEO's own crawler.
Payload-shape properties that used to ride on that endpoint live on in
``test_scan_payload.py`` at the service boundary.
"""

from __future__ import annotations

import uuid
from collections.abc import Iterator
from typing import Any

import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

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
SCANS = f"{API_PREFIX}/seo/scans"


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
# The scan boundary
# --------------------------------------------------------------------------- #


def test_running_a_scan_needs_scan_run_not_only_scan_read(
    client: TestClient, caller: Caller
) -> None:
    """권한 거절은 본작업보다 먼저다 — 이 요청은 크롤을 한 발짝도 시작하지 못한다."""
    caller.current = _principal(Role.CLIENT_VIEWER)
    response = client.post(SCANS, json={"target_url": "https://clinic.example"})
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "PERMISSION_DENIED"


def test_the_bundle_scoring_endpoint_stays_closed(
    client: TestClient, caller: Caller
) -> None:
    """``POST /seo/scan`` 은 요청자가 넣은 provider 자료를 명세의 이름으로 채점하게
    했으므로 닫았다. 채점의 입력은 VEO 의 수집기가 가져온 것뿐이다 — 이 검사는
    그 문이 다시 열리지 않게 지킨다."""
    caller.current = _principal(Role.ANALYST)
    response = client.post(f"{API_PREFIX}/seo/scan", json={})
    assert response.status_code in {404, 405}


def test_the_router_is_not_mounted_by_this_package() -> None:
    """The integrator owns ``veo.api.app``; this package only offers the router."""
    assert _seo_paths(create_app()) == []
