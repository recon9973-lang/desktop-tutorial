"""``GET /usage/pagespeed-quota`` — 한도를 읽을 수 있는가.

세는 법은 이미 `tests/usage/test_quota.py` 가 지킨다. 여기서 보는 것은 **그 답이 화면까지
나오는가**다. 세는 법만 있고 부를 곳이 없던 상태가 이 엔드포인트를 만든 이유다(0-E).

이 파일이 지키는 성질 하나가 나머지보다 무겁다:

> **다른 조직이 태운 호출도 남은 양을 줄인다.**

한도는 API 키 하나에 걸리고 키는 하나다. 조직으로 걸러 세는 순간 화면은 "우리는 조금밖에
안 썼는데요" 라고 말하고, 그동안 키는 이미 막혀 있다. 응답이 조직 경계를 넘어 세는 것은
사고가 아니라 이 성질을 지키기 위한 설계다.
"""

from __future__ import annotations

import uuid
from collections.abc import Callable, Iterator
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete
from sqlalchemy.orm import Session
from tests.resources.support import Tenant

from veo.authz.principal import Principal
from veo.contracts.enums import Role
from veo.db.models.analysis import APIUsageEvent
from veo.usage.quota import CALLS_PER_SCAN, PAGESPEED_DAILY_QUOTA

ENDPOINT = "/api/usage/pagespeed-quota"


@pytest.fixture
def usage_rows(db: Session) -> Iterator[Callable[..., None]]:
    """PageSpeed 호출 기록을 심는다. 끝나면 심은 것만 지운다."""
    planted: list[uuid.UUID] = []

    def _plant(
        *,
        organization_id: uuid.UUID | None,
        count: int,
        provider: str = "GOOGLE_PAGESPEED",
        at: datetime | None = None,
    ) -> None:
        moment = at or datetime.now(UTC)
        rows = [
            APIUsageEvent(
                organization_id=organization_id,
                provider=provider,
                operation="runPagespeed",
                was_cache_hit=False,
                cost_krw=0.0,
                created_at=moment,
            )
            for _ in range(count)
        ]
        db.add_all(rows)
        db.commit()
        planted.extend(row.id for row in rows)

    yield _plant

    db.rollback()
    if planted:
        db.execute(delete(APIUsageEvent).where(APIUsageEvent.id.in_(planted)))
        db.commit()


def read(client: TestClient) -> dict:
    response = client.get(ENDPOINT)
    assert response.status_code == 200, response.text
    return response.json()["data"]


class TestTheNumberReachesTheScreen:
    def test_an_untouched_day_reports_the_full_quota(
        self, client: TestClient, act_as: Callable[[Principal], None], org_a: Tenant
    ) -> None:
        act_as(org_a.analyst)

        body = read(client)

        assert body["daily_quota"] == PAGESPEED_DAILY_QUOTA
        assert body["remaining"] == body["daily_quota"] - body["calls_today"]
        assert body["is_exhausted"] is False

    def test_a_recorded_call_moves_both_the_total_and_the_share(
        self,
        client: TestClient,
        act_as: Callable[[Principal], None],
        org_a: Tenant,
        usage_rows: Callable[..., None],
    ) -> None:
        act_as(org_a.analyst)
        before = read(client)

        usage_rows(organization_id=org_a.organization_id, count=3)
        after = read(client)

        assert after["calls_today"] == before["calls_today"] + 3
        assert (
            after["calls_by_this_organization"] == before["calls_by_this_organization"] + 3
        )
        assert after["remaining"] == before["remaining"] - 3


class TestTheShareIsNotTheAnswerToWhatIsLeft:
    """**이 파일에서 가장 중요한 묶음이다.** 흐리면 화면이 확신 있게 틀린 말을 한다."""

    def test_another_organisations_calls_reduce_what_is_left(
        self,
        client: TestClient,
        act_as: Callable[[Principal], None],
        org_a: Tenant,
        org_b: Tenant,
        usage_rows: Callable[..., None],
    ) -> None:
        act_as(org_a.analyst)
        before = read(client)

        # B 가 태운다. A 는 한 번도 안 불렀다.
        usage_rows(organization_id=org_b.organization_id, count=7)
        after = read(client)

        assert after["calls_by_this_organization"] == before["calls_by_this_organization"]
        assert after["calls_today"] == before["calls_today"] + 7
        assert after["remaining"] == before["remaining"] - 7

    def test_the_caveat_travels_with_the_numbers(
        self, client: TestClient, act_as: Callable[[Principal], None], org_a: Tenant
    ) -> None:
        """주의 문구를 응답에서 빼면 화면이 조직 몫을 남은 양처럼 그리게 된다."""
        act_as(org_a.analyst)

        body = read(client)

        assert "전체로만 답할 수 있습니다" in body["caveat_ko"]


class TestOtherProvidersDoNotCountAgainstThisQuota:
    def test_a_different_provider_is_not_counted(
        self,
        client: TestClient,
        act_as: Callable[[Principal], None],
        org_a: Tenant,
        usage_rows: Callable[..., None],
    ) -> None:
        """한도는 제공자마다 다르다. 섞으면 남은 양이 실제보다 적게 보인다."""
        act_as(org_a.analyst)
        before = read(client)

        usage_rows(organization_id=org_a.organization_id, count=4, provider="OPENAI")
        after = read(client)

        assert after["calls_today"] == before["calls_today"]

    def test_yesterdays_calls_are_not_counted(
        self,
        client: TestClient,
        act_as: Callable[[Principal], None],
        org_a: Tenant,
        usage_rows: Callable[..., None],
    ) -> None:
        act_as(org_a.analyst)
        before = read(client)

        usage_rows(
            organization_id=org_a.organization_id,
            count=5,
            at=datetime.now(UTC) - timedelta(days=1, hours=1),
        )
        after = read(client)

        assert after["calls_today"] == before["calls_today"]


class TestTheEstimateUsesTheSampleCapTheScannerUses:
    def test_the_scan_estimate_divides_by_the_published_cap(
        self, client: TestClient, act_as: Callable[[Principal], None], org_a: Tenant
    ) -> None:
        """"몇 번 더 진단할 수 있는가" 는 실제 표본 상한으로만 답할 수 있다."""
        act_as(org_a.analyst)

        body = read(client)

        assert body["calls_per_scan"] == CALLS_PER_SCAN
        assert body["scans_remaining"] == body["remaining"] // body["calls_per_scan"]


class TestOnlyInternalRolesMayRead:
    def test_a_sales_viewer_is_refused(
        self, client: TestClient, act_as: Callable[[Principal], None], org_a: Tenant
    ) -> None:
        """이 응답은 조직 경계를 넘어 센 값이다. 고객을 향한 역할에는 주지 않는다."""
        act_as(org_a.viewer)

        assert client.get(ENDPOINT).status_code == 403

    def test_a_client_viewer_is_refused(
        self, client: TestClient, act_as: Callable[[Principal], None], org_a: Tenant
    ) -> None:
        act_as(
            Principal(
                user_id=org_a.viewer.user_id,
                organization_id=org_a.organization_id,
                roles=frozenset({Role.CLIENT_VIEWER}),
                session_id="session-client-viewer",
                display_name="client",
            )
        )

        assert client.get(ENDPOINT).status_code == 403
