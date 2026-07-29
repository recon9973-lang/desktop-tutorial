"""``/seo/scans`` 의 저장과 ``/seo/scans/history`` 의 조회.

진단은 두 가지로 쓰인다. 영업 단계의 **간편 진단**은 아무 주소나 넣어 보는 것이라 남길
자리가 없고, 계약 고객의 **관리 진단**은 등록된 사이트에 붙어 이력이 쌓여야 한다. 같은
엔드포인트가 `site_id` 유무로 두 경우를 가른다 — 엔진과 채점은 완전히 동일하고, 결과를
어디에 매다느냐만 다르다.

여기서 고정하는 것: 사이트를 지정하지 않은 진단은 **아무것도 남기지 않는다.** 남기려면
어느 사이트의 이력인지가 정해져 있어야 하고, 임의의 주소를 매달 곳은 없다.
"""

from __future__ import annotations

import uuid
from collections.abc import Callable

import pytest
from fastapi.testclient import TestClient
from tests.resources.support import PROJECTS, SITES, Tenant, payload

SCANS = "/api/seo/scans"
HISTORY = "/api/seo/scans/history"


def _site(client: TestClient, origin: str = "https://ondam.example") -> str:
    project = client.post(PROJECTS, json={"slug": f"p-{uuid.uuid4().hex[:8]}", "name": "온담"})
    assert project.status_code == 201, project.text
    site = client.post(
        SITES,
        json={
            "project_id": payload(project)["id"],
            "origin": origin,
            "display_name": "대표 사이트",
        },
    )
    assert site.status_code == 201, site.text
    return str(payload(site)["id"])


class TestHistoryReading:
    def test_a_site_with_no_scans_reads_back_empty(
        self, client: TestClient, act_as: Callable[..., None], make_tenant: Callable[[str], Tenant]
    ) -> None:
        act_as(make_tenant("empty").analyst)
        site_id = _site(client)

        response = client.get(HISTORY, params={"site_id": site_id})

        assert response.status_code == 200, response.text
        assert payload(response)["entries"] == []

    def test_an_unknown_site_is_not_found(
        self, client: TestClient, act_as: Callable[..., None], make_tenant: Callable[[str], Tenant]
    ) -> None:
        act_as(make_tenant("unknown").analyst)

        response = client.get(HISTORY, params={"site_id": str(uuid.uuid4())})

        assert response.status_code == 404

    def test_another_organizations_site_is_not_found_rather_than_forbidden(
        self, client: TestClient, act_as: Callable[..., None], make_tenant: Callable[[str], Tenant]
    ) -> None:
        """403 은 '그 사이트가 존재한다' 는 사실을 확인해 준다. 404 는 아무것도 알려주지 않는다."""
        owner = make_tenant("owner")
        intruder = make_tenant("intruder")
        act_as(owner.analyst)
        site_id = _site(client)

        act_as(intruder.analyst)
        response = client.get(HISTORY, params={"site_id": site_id})

        assert response.status_code == 404


class TestScanRequestShape:
    def test_a_site_that_does_not_exist_is_refused_before_anything_is_fetched(
        self, client: TestClient, act_as: Callable[..., None], make_tenant: Callable[[str], Tenant]
    ) -> None:
        """없는 사이트를 위해 남의 서버에 요청을 보내면 안 된다."""
        act_as(make_tenant("nosite").analyst)

        response = client.post(
            SCANS,
            json={"target_url": "https://example.invalid/", "site_id": str(uuid.uuid4())},
        )

        assert response.status_code == 404

    @pytest.mark.parametrize("blocked", ["http://127.0.0.1/", "http://169.254.169.254/"])
    def test_the_ssrf_guard_still_applies_to_a_signed_in_caller(
        self,
        client: TestClient,
        act_as: Callable[..., None],
        make_tenant: Callable[[str], Tenant],
        blocked: str,
    ) -> None:
        act_as(make_tenant(f"ssrf-{uuid.uuid4().hex[:4]}").analyst)

        response = client.post(SCANS, json={"target_url": blocked})

        assert response.status_code == 422
