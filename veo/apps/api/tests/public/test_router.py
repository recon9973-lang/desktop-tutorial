"""The unauthenticated front door.

Every other router in VEO fails closed without a principal. This one is deliberately
open, so the tests care about different things: that it is reachable with no credential
at all, that it refuses before it works, and that nothing belonging to a paying customer
can come out of it.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from public_support import (
    CLINIC_HTML,
    ServiceClock,
    clinic_site,
    payload_strings,
    public_guard,
    site_transport,
)

from veo.api.app import create_app
from veo.contracts.enums import ErrorCode
from veo.core.settings import get_settings
from veo.providers.naver.searchad import NaverSearchAdClient
from veo.public.leads import InMemoryLeadStore
from veo.public.limits import InMemoryRateLimiter
from veo.public.router import (
    SESSION_HEADER,
    get_lead_store,
    get_public_service,
    get_rate_limiter,
)
from veo.public.router import router as public_router
from veo.public.service import InMemoryPublicResultStore, PublicScanService

TARGET = "https://clinic.example/"


def mounted_paths(application: FastAPI) -> set[str]:
    """Which paths the application actually serves, read from its OpenAPI document.

    Not from ``application.routes``. On this FastAPI version ``include_router`` produces
    an ``_IncludedRouter`` whose ``path`` is ``None``, so walking ``routes`` reports
    nothing for any mounted router — a detector that answers "not mounted" whatever the
    truth is. This helper originally did exactly that, which meant the mounting assertion
    below passed for a reason unrelated to mounting. The same trap is pinned separately
    in ``tests/contract/test_router_mounting.py``.
    """
    return set(application.openapi()["paths"])


@pytest.fixture
def leads() -> InMemoryLeadStore:
    return InMemoryLeadStore()


@pytest.fixture
def limiter() -> InMemoryRateLimiter:
    """One limiter for the whole app under test.

    The router keeps a process-wide limiter, which is right in production and wrong in a
    test suite — one test's requests would count against the next one's. Overriding the
    dependency is also what proves the scan routes and the lead route share a limiter
    rather than each keeping their own.
    """
    return InMemoryRateLimiter()


@pytest.fixture
def service(clock: ServiceClock, limiter: InMemoryRateLimiter) -> PublicScanService:
    return PublicScanService(
        guard=public_guard(),
        transport=site_transport(clinic_site(), serve_unknown_hosts=True),
        limiter=limiter,
        results=InMemoryPublicResultStore(),
        clock=clock,
        searchad=NaverSearchAdClient(credentials=None),
        # 성능 실측도 마찬가지다: 기본값은 설정에서 키를 읽으므로, 여기서 막지
        # 않으면 시험이 개발자 .env 를 타고 진짜 구글로 나간다(0-F).
        performance=lambda context: (context, None),
    )


@pytest.fixture
def app(
    service: PublicScanService, leads: InMemoryLeadStore, limiter: InMemoryRateLimiter
) -> FastAPI:
    application = create_app()
    if not any(path.startswith("/public") for path in mounted_paths(application)):
        application.include_router(public_router)
    application.dependency_overrides[get_public_service] = lambda: service
    application.dependency_overrides[get_lead_store] = lambda: leads
    application.dependency_overrides[get_rate_limiter] = lambda: limiter
    return application


@pytest.fixture
def client(app: FastAPI) -> Iterator[TestClient]:
    with TestClient(app, client=("203.0.113.9", 44321)) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def scan(client: TestClient, *, session: str = "sess-0001", url: str = TARGET) -> Any:
    return client.post(
        "/public/v1/seo-scans",
        json={"urls": [url]},
        headers={SESSION_HEADER: session},
    )


# --------------------------------------------------------------------------- #
# Mounting
# --------------------------------------------------------------------------- #


def test_the_router_is_mounted_by_the_application() -> None:
    """Mounted by the integrator, and asserted here so it cannot quietly come undone.

    This test previously asserted the opposite — it marked the boundary while the public
    package was being built by someone who did not own ``veo/api/app.py``. Now that the
    router is mounted, the same assertion is worth keeping inverted: an endpoint that
    exists but is unreachable fails silently, and the free scan is the front door to the
    product.
    """
    mounted = mounted_paths(create_app())
    assert "/public/v1/seo-scans" in mounted


def test_the_public_surface_is_not_mounted_under_the_authenticated_prefix() -> None:
    """The unauthenticated routes must stay outside ``api_prefix``.

    Not cosmetic: the prefix is how an operator reading an access log — sometimes the
    only evidence left after an incident — tells an authenticated request from an
    anonymous one, and how a proxy applies different rules to each without enumerating
    route names. Mounting the public router under the API prefix would erase that
    distinction while every test above still passed.
    """
    prefix = get_settings().api_prefix
    public_paths = [path for path in mounted_paths(create_app()) if "/public/" in path]

    assert public_paths, "the public routes vanished; this guard would pass by matching nothing"
    for path in public_paths:
        assert not path.startswith(prefix), f"{path} is mounted under the authenticated prefix"


def test_every_public_route_lives_under_the_public_prefix() -> None:
    paths = {str(getattr(route, "path", "")) for route in public_router.routes}
    assert paths == {
        "/public/v1/seo-scans",
        "/public/v1/geo-readiness-scans",
        "/public/v1/keyword-lookups",
        "/public/v1/results/{token}",
        "/public/v1/leads",
    }


# --------------------------------------------------------------------------- #
# Scanning
# --------------------------------------------------------------------------- #


def test_an_anonymous_caller_gets_a_real_diagnosis(client: TestClient) -> None:
    response = scan(client)
    assert response.status_code == 200

    body = response.json()
    assert body["error"] is None
    assert body["meta"]["request_id"]
    data = body["data"]
    assert data["score"]["spec_id"] == "veo.seo.readiness"
    assert data["score"]["is_rank_prediction"] is False
    assert data["summary_ko"]
    assert data["result_token"]


def test_the_response_body_contains_no_evidence_and_no_foreign_url(client: TestClient) -> None:
    body = scan(client).json()
    strings = payload_strings(body["data"])

    assert "excerpt" not in strings
    assert "evidence" not in strings
    for line in CLINIC_HTML.splitlines():
        stripped = line.strip()
        if len(stripped) > 25:
            assert stripped not in strings

    # 문장 속 URL 까지 전부 — 남의 호스트가 하나라도 나가면 실패한다.
    import re
    from urllib.parse import urlsplit

    found = [url for text in strings for url in re.findall(r"https?://[^\s\u201d\u201c\"']+", text)]
    page_hosts = {
        urlsplit(url).hostname
        for url in re.findall(r"https?://[^\s\"'<>]+", CLINIC_HTML)
    }
    # 수집기의 고정 조치 문구가 언급하는 잘 알려진 인프라 호스트. 여기 없는
    # 호스트가 나오면 시험이 이름을 대며 실패한다 — 추가는 의식적 결정이어야 한다.
    well_known = {"schema.org", "www.w3.org", "fonts.gstatic.com", "fonts.googleapis.com"}
    assert {urlsplit(url).hostname for url in found} <= (
        {urlsplit(TARGET).hostname} | page_hosts | well_known
    )


def test_a_geo_readiness_scan_separates_readiness_from_exposure(client: TestClient) -> None:
    response = client.post(
        "/public/v1/geo-readiness-scans",
        json={"urls": [TARGET]},
        headers={SESSION_HEADER: "sess-0002"},
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert "readiness" in data
    assert "exposure" in data
    assert data["readiness"]["is_rank_prediction"] is False


def test_a_keyword_lookup_answers_with_provider_state(client: TestClient) -> None:
    response = client.post(
        "/public/v1/keyword-lookups",
        json={"keywords": ["강남 내과"]},
        headers={SESSION_HEADER: "sess-0003"},
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["searchad_state"].startswith("DISABLED")
    assert data["keywords"][0]["monthly_total_searches"] is None


def test_more_urls_than_allowed_is_a_422_with_a_korean_message(client: TestClient) -> None:
    maximum = get_settings().public_max_urls_per_scan
    response = client.post(
        "/public/v1/seo-scans",
        json={"urls": [TARGET] * (maximum + 1)},
        headers={SESSION_HEADER: "sess-0004"},
    )
    assert response.status_code == 422
    error = response.json()["error"]
    assert any("가" <= ch <= "힣" for ch in error["message"])


def test_a_private_target_is_refused_with_target_url_rejected(app: FastAPI) -> None:
    app.dependency_overrides[get_public_service] = lambda: PublicScanService(
        guard=public_guard("10.0.0.5"),
        transport=site_transport(clinic_site()),
        limiter=InMemoryRateLimiter(),
        results=InMemoryPublicResultStore(),
        searchad=NaverSearchAdClient(credentials=None),
        # 성능 실측도 마찬가지다: 기본값은 설정에서 키를 읽으므로, 여기서 막지
        # 않으면 시험이 개발자 .env 를 타고 진짜 구글로 나간다(0-F).
        performance=lambda context: (context, None),
    )
    with TestClient(app, client=("203.0.113.9", 44321)) as client:
        response = scan(client)
    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == ErrorCode.TARGET_URL_REJECTED.value
    assert "10.0.0.5" not in error["message"]


# --------------------------------------------------------------------------- #
# Limits
# --------------------------------------------------------------------------- #


def test_the_per_ip_limit_answers_429_with_retry_after(client: TestClient) -> None:
    """A different host each time, so only the caller's own bucket can be the one that
    fires — otherwise this would pass on the target-host rule and prove nothing."""
    allowed = get_settings().public_rate_limit_per_hour
    for index in range(allowed):
        assert (
            scan(
                client, session=f"sess-{index:04d}", url=f"https://h{index}.example/"
            ).status_code
            == 200
        )

    refused = scan(client, session="sess-9999", url="https://h99.example/")
    assert refused.status_code == 429
    body = refused.json()
    assert body["error"]["code"] == ErrorCode.RATE_LIMITED.value
    assert body["error"]["retry_after_seconds"] > 0
    assert refused.headers["Retry-After"] == str(body["error"]["retry_after_seconds"])


def test_the_per_session_limit_survives_a_change_of_address(app: FastAPI) -> None:
    allowed = get_settings().public_rate_limit_per_hour
    for index in range(allowed):
        with TestClient(app, client=(f"203.0.113.{index}", 1000)) as client:
            assert (
                scan(
                    client, session="sticky-session", url=f"https://h{index}.example/"
                ).status_code
                == 200
            )

    with TestClient(app, client=("198.51.100.4", 1000)) as client:
        assert scan(client, session="sticky-session", url="https://h99.example/").status_code == 429


def test_a_missing_session_header_falls_back_to_the_address(client: TestClient) -> None:
    response = client.post("/public/v1/seo-scans", json={"urls": [TARGET]})
    assert response.status_code == 200


def test_a_junk_session_header_is_rejected(client: TestClient) -> None:
    response = client.post(
        "/public/v1/seo-scans",
        json={"urls": [TARGET]},
        headers={SESSION_HEADER: "../../etc/passwd"},
    )
    assert response.status_code == 422


# --------------------------------------------------------------------------- #
# Shared results
# --------------------------------------------------------------------------- #


def test_a_result_token_reads_the_same_result_back(client: TestClient) -> None:
    created = scan(client).json()["data"]
    response = client.get(f"/public/v1/results/{created['result_token']}")
    assert response.status_code == 200
    assert response.json()["data"]["score"]["score"] == created["score"]["score"]


def test_an_expired_result_token_is_refused(client: TestClient, clock: ServiceClock) -> None:
    created = scan(client).json()["data"]
    clock.advance(get_settings().public_result_ttl_seconds + 1)

    response = client.get(f"/public/v1/results/{created['result_token']}")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == ErrorCode.NOT_FOUND.value


def test_an_unknown_token_is_indistinguishable_from_an_expired_one(client: TestClient) -> None:
    response = client.get("/public/v1/results/" + "a" * 43)
    assert response.status_code == 404


def test_a_malformed_token_never_reaches_the_store(client: TestClient) -> None:
    assert client.get("/public/v1/results/short").status_code == 404


# --------------------------------------------------------------------------- #
# Leads
# --------------------------------------------------------------------------- #


def test_a_lead_stores_only_what_a_callback_needs(
    client: TestClient, leads: InMemoryLeadStore
) -> None:
    response = client.post(
        "/public/v1/leads",
        json={"name": "김원장", "phone": "010-1234-5678", "site_url": TARGET},
        headers={SESSION_HEADER: "sess-lead"},
    )
    assert response.status_code == 201

    data = response.json()["data"]
    assert data["lead_id"]
    assert data["stored_fields_ko"]
    assert data["retention_note_ko"]
    assert data["consent_note_ko"]

    stored = leads.all_leads()
    assert len(stored) == 1
    record = stored[0]
    assert record.name == "김원장"
    assert record.phone == "010-1234-5678"
    assert record.email is None


def test_a_lead_with_no_contact_channel_is_refused(client: TestClient) -> None:
    response = client.post(
        "/public/v1/leads",
        json={"name": "김원장"},
        headers={SESSION_HEADER: "sess-lead2"},
    )
    assert response.status_code == 422


def test_a_lead_refuses_fields_nobody_asked_for(client: TestClient) -> None:
    """Minimisation is enforced by the schema, not by remembering to ignore extras."""
    response = client.post(
        "/public/v1/leads",
        json={
            "name": "김원장",
            "phone": "010-1234-5678",
            "resident_registration_number": "900101-1234567",
        },
        headers={SESSION_HEADER: "sess-lead3"},
    )
    assert response.status_code == 422


def test_the_lead_response_states_what_was_stored(client: TestClient) -> None:
    data = client.post(
        "/public/v1/leads",
        json={"name": "김원장", "email": "won@example.com"},
        headers={SESSION_HEADER: "sess-lead4"},
    ).json()["data"]

    joined = " ".join(data["stored_fields_ko"])
    assert "이름" in joined
    assert "이메일" in joined
    assert "전화" not in joined


def test_leads_are_rate_limited_too(client: TestClient) -> None:
    allowed = get_settings().public_rate_limit_per_hour
    for index in range(allowed):
        response = client.post(
            "/public/v1/leads",
            json={"name": "김원장", "phone": "010-1234-5678"},
            headers={SESSION_HEADER: f"lead-{index:04d}"},
        )
        assert response.status_code == 201

    refused = client.post(
        "/public/v1/leads",
        json={"name": "김원장", "phone": "010-1234-5678"},
        headers={SESSION_HEADER: "lead-9999"},
    )
    assert refused.status_code == 429


def test_the_openapi_document_describes_the_public_routes_in_korean(app: FastAPI) -> None:
    schema = app.openapi()
    summaries = [
        operation["summary"]
        for path, item in schema["paths"].items()
        if path.startswith("/public")
        for operation in item.values()
        if "summary" in operation
    ]
    assert summaries
    for summary in summaries:
        assert any("가" <= ch <= "힣" for ch in summary)


def test_a_result_expiry_is_reported_to_the_caller(client: TestClient) -> None:
    data = scan(client).json()["data"]
    assert data["result_expires_at"]
