"""거래처 등록은 사람이 정한다 — 재 본 것과 맡은 것을 가른다.

주소만 넣으면 잰다는 규칙 덕분에 영업 중에 아무 주소나 넣어 볼 수 있는데, 그렇게
만들어진 자리가 거래처 목록에 그대로 섞였다. 목록이 "우리가 맡은 곳"이 아니라 "이 도구를
거쳐 간 주소"를 말하게 되어, 아침에 열어도 할 일이 보이지 않는다(사용자 지적).

`is_active` 와는 다른 축이다. 저것은 **지웠는가**, 이것은 **우리 거래처인가** 이다.
한 칸에 접으면 "재 보기만 한 곳"과 "거래처였다가 끊긴 곳"이 같은 값이 된다.
"""

from __future__ import annotations

from collections.abc import Callable

from fastapi.testclient import TestClient
from tests.resources.support import CUSTOMERS, Tenant, payload


def _create(client: TestClient, name: str, **extra: object) -> dict[str, object]:
    response = client.post(CUSTOMERS, json={"name": name, **extra})
    assert response.status_code == 201, response.text
    return payload(response)


def _names(client: TestClient, query: str = "") -> list[object]:
    response = client.get(f"{CUSTOMERS}{query}")
    assert response.status_code == 200, response.text
    return [row["name"] for row in payload(response)]


class TestTheDefaultIsAClient:
    def test_a_plain_create_is_registered(
        self, client: TestClient, act_as: Callable[..., None], org_a: Tenant
    ) -> None:
        """손으로 등록하는 쪽이 기본이다. 기본을 뒤집으면 값을 빠뜨린 등록이 목록에서
        사라지고, 사장님은 등록한 업체를 찾지 못한다."""
        act_as(org_a.analyst)

        assert _create(client, "온담의원")["is_registered"] is True

    def test_a_scratch_row_says_so(
        self, client: TestClient, act_as: Callable[..., None], org_a: Tenant
    ) -> None:
        act_as(org_a.analyst)

        assert _create(client, "ondam.co.kr", is_registered=False)["is_registered"] is False


class TestTheListCanAskForOneOrTheOther:
    def test_registered_only(
        self, client: TestClient, act_as: Callable[..., None], org_a: Tenant
    ) -> None:
        act_as(org_a.analyst)
        _create(client, "맡은곳")
        _create(client, "재봤을뿐", is_registered=False)

        assert _names(client, "?registered=true") == ["맡은곳"]

    def test_scratch_only(
        self, client: TestClient, act_as: Callable[..., None], org_a: Tenant
    ) -> None:
        """재 보기만 한 자리도 꺼낼 수 있어야 한다 — 그래야 나중에 거래처로 올릴 후보를
        보여 줄 수 있다. 꺼낼 길이 없으면 그 행들은 있으나 마나 한 것이 된다."""
        act_as(org_a.analyst)
        _create(client, "맡은곳")
        _create(client, "재봤을뿐", is_registered=False)

        assert _names(client, "?registered=false") == ["재봤을뿐"]

    def test_no_filter_returns_both(
        self, client: TestClient, act_as: Callable[..., None], org_a: Tenant
    ) -> None:
        """생략은 "거래처만"이 아니라 "둘 다"다. 부르는 곳이 여럿인데 기본이 거르는
        쪽이면, 전부를 뜻한 호출이 조용히 절반만 받는다."""
        act_as(org_a.analyst)
        _create(client, "맡은곳")
        _create(client, "재봤을뿐", is_registered=False)

        assert sorted(_names(client)) == ["맡은곳", "재봤을뿐"]

    def test_the_total_matches_the_filter(
        self, client: TestClient, act_as: Callable[..., None], org_a: Tenant
    ) -> None:
        """총 개수가 거르기 전 값이면 화면은 다음 쪽을 부르러 가고, 영영 차지 않는다."""
        act_as(org_a.analyst)
        _create(client, "맡은곳")
        _create(client, "재봤을뿐", is_registered=False)

        response = client.get(f"{CUSTOMERS}?registered=true")

        assert response.json()["page_info"]["total_items"] == 1


class TestPromotingAScratchRow:
    def test_it_becomes_a_client(
        self, client: TestClient, act_as: Callable[..., None], org_a: Tenant
    ) -> None:
        """"거래처로 등록"은 새 행을 만드는 것이 아니라 있던 행을 올리는 것이다 —
        새로 만들면 그때까지의 진단 이력이 옛 행에 남아 갈라진다."""
        act_as(org_a.analyst)
        scratch = _create(client, "ondam.co.kr", is_registered=False)

        response = client.patch(
            f"{CUSTOMERS}/{scratch['id']}",
            json={"name": "온담의원", "is_registered": True},
        )

        assert response.status_code == 200, response.text
        assert payload(response)["is_registered"] is True
        assert _names(client, "?registered=true") == ["온담의원"]

    def test_it_can_be_put_back(
        self, client: TestClient, act_as: Callable[..., None], org_a: Tenant
    ) -> None:
        """잘못 올린 것을 되돌리는 길이 없으면, 되돌리려고 지우게 된다 — 그러면 이력도
        함께 간다."""
        act_as(org_a.analyst)
        registered = _create(client, "온담의원")

        response = client.patch(
            f"{CUSTOMERS}/{registered['id']}", json={"is_registered": False}
        )

        assert response.status_code == 200, response.text
        assert _names(client, "?registered=true") == []


class TestItIsADifferentAxisFromDeletion:
    def test_a_registered_client_can_still_be_deleted(
        self, client: TestClient, act_as: Callable[..., None], org_a: Tenant
    ) -> None:
        act_as(org_a.analyst)
        registered = _create(client, "온담의원")

        assert client.delete(f"{CUSTOMERS}/{registered['id']}").status_code in (200, 204)
        # 지운 것은 등록 여부와 무관하게 기본 목록에서 빠진다.
        assert _names(client, "?registered=true") == []

    def test_a_scratch_row_is_not_a_deleted_one(
        self, client: TestClient, act_as: Callable[..., None], org_a: Tenant
    ) -> None:
        act_as(org_a.analyst)
        scratch = _create(client, "ondam.co.kr", is_registered=False)

        assert scratch["is_active"] is True
