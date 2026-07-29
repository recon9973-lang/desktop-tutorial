"""항목별 판정에 **왜 그렇게 판정했는지** 를 붙여 내보낸다.

지금까지 화면이 받은 항목은 `check_id` · 상태 · 한 줄 메모가 전부였다. 그래서 상세
보기에도 `seo.onpage.heading_hierarchy` 같은 식별자가 그대로 찍혔고, 직원이 그 줄을
보고 할 수 있는 일이 없었다. 어느 페이지가 문제인지, 무엇을 보고 그렇게 판정했는지,
무엇을 바꾸면 되는지가 응답 안에 아예 없었기 때문이다.

정작 그 근거는 수집기가 이미 만들고 있었다. `observed_value` 에 페이지별 관측값이
담기는데 — 제목 길이, 어긋난 제목 단계, 막힌 크롤러 이름 — 스키마에 자리가 없어
API 경계에서 버려졌다. 여기서 하는 일은 새로 재는 것이 아니라 **버리지 않는 것**이다.

제목·영역·심각도는 발행 명세에서 가져온다. 수집기가 정하게 두면 같은 항목의 이름이
수집기마다 달라지고, 명세를 고쳐도 화면이 따라오지 않는다.
"""

from __future__ import annotations

import uuid
from collections.abc import Iterator

import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from tests.seo.support import scan_bundle

from veo.api.app import create_app  # noqa: F401  — 라우터보다 먼저 읽어야 순환 import 를 피한다
from veo.authz.deps import get_principal
from veo.authz.principal import Principal
from veo.contracts.enums import Role
from veo.core.settings import get_settings
from veo.seo.router import router as seo_router
from veo.seo.service import load_seo_spec

API_PREFIX = get_settings().api_prefix
SCAN = f"{API_PREFIX}/seo/scan"


@pytest.fixture
def client() -> Iterator[TestClient]:
    app = FastAPI()
    app.include_router(seo_router, prefix=API_PREFIX)

    def principal(request: Request) -> Principal:
        return Principal(
            user_id=uuid.uuid4(),
            organization_id=uuid.uuid4(),
            roles=frozenset({Role.ANALYST}),
            session_id="outcome-detail-session",
        )

    app.dependency_overrides[get_principal] = principal
    with TestClient(app) as test_client:
        yield test_client


def outcomes(client: TestClient, **overrides: object) -> dict[str, dict]:
    response = client.post(SCAN, json=scan_bundle(**overrides))
    assert response.status_code == 200, response.text
    return {item["check_id"]: item for item in response.json()["data"]["outcomes"]}


class TestEveryOutcomeCarriesItsName:
    def test_an_outcome_has_the_korean_title_from_the_specification(
        self, client: TestClient
    ) -> None:
        """식별자만 주면 화면은 `seo.onpage.heading_hierarchy` 라고 쓸 수밖에 없다."""
        for item in outcomes(client).values():
            assert item["title_ko"], item["check_id"]

    def test_the_title_matches_the_published_specification(self, client: TestClient) -> None:
        spec = load_seo_spec()
        titles = {
            check.id: check.title_ko
            for category in spec.categories
            for check in category.checks
        }

        for check_id, item in outcomes(client).items():
            assert item["title_ko"] == titles[check_id]

    def test_an_outcome_says_which_category_it_belongs_to(self, client: TestClient) -> None:
        """영역별로 묶어 보여주려면 항목이 자기 영역을 알아야 한다."""
        spec = load_seo_spec()
        names = {category.id: category.name_ko for category in spec.categories}

        for item in outcomes(client).values():
            assert item["category_id"] in names
            assert item["category_name_ko"] == names[item["category_id"]]

    def test_an_outcome_carries_its_severity_and_owner(self, client: TestClient) -> None:
        """무엇부터 고칠지와 누가 고칠지는 화면이 다시 계산할 값이 아니다."""
        for item in outcomes(client).values():
            assert item["severity"] in {"BLOCKER", "CRITICAL", "MAJOR", "MINOR", "INFO"}
            assert item["remediation_owner"] in {
                "DEVELOPER",
                "MARKETER",
                "BUSINESS_OWNER",
                "OPERATIONS",
            }


class TestTheObservedValueSurvivesTheApiBoundary:
    def test_a_check_that_recorded_what_it_saw_reports_it(self, client: TestClient) -> None:
        """수집기가 이미 담아 둔 관측값을 스키마가 버리지 않는다."""
        measured = [
            item
            for item in outcomes(client).values()
            if item["status"] in {"PASS", "WARNING", "FAIL"} and item["observed"] is not None
        ]

        assert measured, "판정된 항목 중 관측값을 남긴 것이 하나도 없다면 근거가 사라진 것이다"

    def test_a_failing_check_names_the_page_it_failed_on(self, client: TestClient) -> None:
        """"제목이 중복됩니다" 만으로는 어느 페이지를 고칠지 알 수 없다."""
        blocked = outcomes(client, robots_txt="User-agent: *\nDisallow: /\n")

        failing = [
            item
            for item in blocked.values()
            if item["status"] == "FAIL" and item["observed"] is not None
        ]
        assert failing


class TestGuidanceTravelsWithTheOutcome:
    def test_a_failing_outcome_links_to_its_issue(self, client: TestClient) -> None:
        """수정 방향은 이미 조치 항목에 있다. 항목별 판정에서 찾아갈 수 있어야 한다."""
        body = scan_bundle(robots_txt="User-agent: *\nDisallow: /\n")
        data = client.post(SCAN, json=body).json()["data"]
        blocked = {item["check_id"]: item for item in data["outcomes"]}
        issues = {item["check_id"] for item in data["issues"]}

        failing = {
            check_id for check_id, item in blocked.items() if item["status"] == "FAIL"
        }
        assert failing & issues, "실패한 항목 중 어느 것도 조치 안내를 갖지 못했다"

    def test_an_unknown_outcome_still_has_a_title_to_show(self, client: TestClient) -> None:
        """못 잰 항목이야말로 이름이 필요하다 — 식별자만 보면 고장으로 읽힌다."""
        unknown = [
            item for item in outcomes(client).values() if item["status"] == "UNKNOWN"
        ]

        assert unknown
        assert all(item["title_ko"] for item in unknown)
