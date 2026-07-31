"""브랜드 식별 — 고객이 **자기가 누구인지** 말할 수 있는가.

## 무엇이 틀려 있었나

`brand_identities` 와 `competitors` 는 처음부터 있었고 읽는 코드도 많았다. 그런데
**쓰는 코드가 `src/` 전체에 0건**이었다. 고객은 자기 상호를 등록할 방법이 없었고,
등록이 없으면 `brand_target_for` 가 거부하므로 **GEO 관측이 아예 돌지 않았다.**

관측기·판별기·검수·점유율을 다 만들어 두고 그 앞단의 한 칸이 비어 있어서 아무것도 못
쓰는 상태였다(0-E).

## 여기서 고정하는 것

1. 등록이 실제로 저장되고, 그 뒤 관측이 요구하는 조건이 충족된다
2. **무엇을 더 넣어야 측정이 되는지** 알려준다 — 효과가 큰 순서로
3. 우리 쪽만 잘 적어 두면 **경고한다** — 그 상태의 점유율은 노출 차이가 아니라 등록
   정보 차이를 보여준다
4. 경고해도 **저장은 된다** — 막으면 경쟁사를 아예 등록하지 않게 되고 점유율이 사라진다
5. 식별자는 바뀌지 않는다 — 바뀌면 과거 관측과 갈라진다
"""

from __future__ import annotations

import uuid
from collections.abc import Callable

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from veo.authz.principal import Principal
from veo.core.settings import get_settings
from veo.db.models.identity import Project

from .support import DATABASE_URL, Tenant, error_code, payload

pytestmark = [
    pytest.mark.requires_postgres,
    pytest.mark.skipif(DATABASE_URL is None, reason="VEO_TEST_DATABASE_URL 이 필요합니다"),
]

PREFIX = get_settings().api_prefix


@pytest.fixture
def project(db: Session, make_tenant: Callable[[str], Tenant]) -> tuple[Tenant, uuid.UUID]:
    tenant = make_tenant("brands")
    row = Project(
        organization_id=tenant.organization_id,
        slug=f"brands-{uuid.uuid4().hex[:8]}",
        name="브랜드 프로젝트",
        locale="ko-KR",
        settings={},
    )
    db.add(row)
    db.commit()
    return tenant, row.id


def brands_url(project_id: uuid.UUID) -> str:
    return f"{PREFIX}/projects/{project_id}/brands"


class TestDeclaringWhoWeAre:
    def test_a_brand_can_finally_be_registered(
        self,
        client: TestClient,
        act_as: Callable[[Principal], None],
        project: tuple[Tenant, uuid.UUID],
    ) -> None:
        tenant, project_id = project
        act_as(tenant.analyst)

        response = client.post(
            brands_url(project_id),
            json={
                "display_name": "온담한의원",
                "is_own_brand": True,
                "own_domains": ["ondam.example"],
                "address_terms": ["서울 강남구 테헤란로"],
                "phone_numbers": ["02-1234-5678"],
            },
        )

        assert response.status_code == 201
        data = payload(response)
        assert data["is_own_brand"] is True
        assert data["identity_strength"] == "SUFFICIENT"
        # 저장할 때 정규화한다. 답변에 (02)1234-5678 로 나와도 맞추려면 한 형태여야 한다.
        assert data["phone_numbers"] == ["0212345678"]

    def test_the_project_can_now_be_observed(
        self,
        client: TestClient,
        act_as: Callable[[Principal], None],
        project: tuple[Tenant, uuid.UUID],
    ) -> None:
        """이것이 이 커밋의 요점이다 — 등록 전에는 관측이 거부됐다."""
        tenant, project_id = project
        act_as(tenant.analyst)

        assert payload(client.get(brands_url(project_id)))["can_observe"] is False

        client.post(
            brands_url(project_id),
            json={"display_name": "온담한의원", "is_own_brand": True},
        )

        assert payload(client.get(brands_url(project_id)))["can_observe"] is True

    def test_only_one_own_brand_per_project(
        self,
        client: TestClient,
        act_as: Callable[[Principal], None],
        project: tuple[Tenant, uuid.UUID],
    ) -> None:
        tenant, project_id = project
        act_as(tenant.analyst)
        client.post(
            brands_url(project_id), json={"display_name": "온담한의원", "is_own_brand": True}
        )

        second = client.post(
            brands_url(project_id), json={"display_name": "다른이름", "is_own_brand": True}
        )

        assert second.status_code == 409


class TestTellingThemWhatIsMissing:
    def test_a_common_name_alone_cannot_be_measured(
        self,
        client: TestClient,
        act_as: Callable[[Principal], None],
        project: tuple[Tenant, uuid.UUID],
    ) -> None:
        """`서울치과` 는 수십 곳이다. 이름만으로는 이 업체라고 말할 수 없다."""
        tenant, project_id = project
        act_as(tenant.analyst)

        data = payload(
            client.post(
                brands_url(project_id),
                json={"display_name": "서울치과", "is_own_brand": True},
            )
        )

        assert data["name_is_generic"] is True
        assert data["identity_strength"] != "SUFFICIENT"
        assert data["gaps_ko"], "무엇을 넣어야 하는지 말하지 않으면 고객은 알 수 없다"

    def test_the_phone_number_is_named_first(
        self,
        client: TestClient,
        act_as: Callable[[Principal], None],
        project: tuple[Tenant, uuid.UUID],
    ) -> None:
        """효과가 큰 순서로 말한다. 주소부터 시키면 시간을 쓰고도 측정이 안 된다."""
        tenant, project_id = project
        act_as(tenant.analyst)

        data = payload(
            client.post(
                brands_url(project_id),
                json={"display_name": "서울치과", "is_own_brand": True},
            )
        )

        assert "전화번호" in data["gaps_ko"][0]

    def test_filling_the_gap_makes_it_measurable(
        self,
        client: TestClient,
        act_as: Callable[[Principal], None],
        project: tuple[Tenant, uuid.UUID],
    ) -> None:
        tenant, project_id = project
        act_as(tenant.analyst)
        created = payload(
            client.post(
                brands_url(project_id),
                json={"display_name": "서울치과", "is_own_brand": True},
            )
        )

        updated = payload(
            client.patch(
                f"{brands_url(project_id)}/{created['id']}",
                json={"phone_numbers": ["02-987-6543"]},
            )
        )

        assert updated["identity_strength"] == "SUFFICIENT"
        assert updated["gaps_ko"] == []

    def test_the_identifier_survives_a_rename(
        self,
        client: TestClient,
        act_as: Callable[[Principal], None],
        project: tuple[Tenant, uuid.UUID],
    ) -> None:
        """바뀌면 지난 관측과 이번 관측이 다른 브랜드처럼 갈라진다."""
        tenant, project_id = project
        act_as(tenant.analyst)
        created = payload(
            client.post(
                brands_url(project_id),
                json={"display_name": "온담한의원", "is_own_brand": True},
            )
        )

        renamed = payload(
            client.patch(
                f"{brands_url(project_id)}/{created['id']}",
                json={"display_name": "온담한방병원"},
            )
        )

        assert renamed["entity_key"] == created["entity_key"]
        assert renamed["display_name"] == "온담한방병원"


class TestBothSidesDescribedTheSame:
    def _declare(
        self, client: TestClient, project_id: uuid.UUID, **over: object
    ) -> dict[str, object]:
        body: dict[str, object] = {"display_name": "이름", "is_own_brand": False}
        body.update(over)
        return payload(client.post(brands_url(project_id), json=body))

    def test_a_thinly_described_rival_is_flagged(
        self,
        client: TestClient,
        act_as: Callable[[Principal], None],
        project: tuple[Tenant, uuid.UUID],
    ) -> None:
        """점유율이 조용히 틀리는 경로가 이것이다.

        우리 쪽만 채워 두면 경쟁사 언급이 더 자주 검수 대기로 떨어져 분자에서 빠지고,
        산술을 한 글자도 안 고치고 우리 점유율이 오른다.
        """
        tenant, project_id = project
        act_as(tenant.analyst)
        client.post(
            brands_url(project_id),
            json={
                "display_name": "온담한의원",
                "is_own_brand": True,
                "phone_numbers": ["02-1234-5678"],
            },
        )
        self._declare(client, project_id, display_name="서울치과")

        data = payload(client.get(brands_url(project_id)))

        assert data["asymmetry_ko"], "비대칭을 말하지 않으면 아무도 모른다"
        assert "서울치과" in data["asymmetry_ko"][0]

    def test_the_warning_does_not_block_the_write(
        self,
        client: TestClient,
        act_as: Callable[[Principal], None],
        project: tuple[Tenant, uuid.UUID],
    ) -> None:
        """막으면 경쟁사를 아예 등록하지 않게 되고, 그러면 점유율 자체가 사라진다."""
        tenant, project_id = project
        act_as(tenant.analyst)
        client.post(
            brands_url(project_id),
            json={
                "display_name": "온담한의원",
                "is_own_brand": True,
                "phone_numbers": ["02-1234-5678"],
            },
        )

        response = client.post(
            brands_url(project_id),
            json={"display_name": "서울치과", "is_own_brand": False},
        )

        assert response.status_code == 201
        assert len(payload(client.get(brands_url(project_id)))["competitors"]) == 1

    def test_a_well_described_rival_raises_no_warning(
        self,
        client: TestClient,
        act_as: Callable[[Principal], None],
        project: tuple[Tenant, uuid.UUID],
    ) -> None:
        tenant, project_id = project
        act_as(tenant.analyst)
        client.post(
            brands_url(project_id),
            json={
                "display_name": "온담한의원",
                "is_own_brand": True,
                "phone_numbers": ["02-1234-5678"],
            },
        )
        self._declare(
            client, project_id, display_name="서울치과", phone_numbers=["02-987-6543"]
        )

        assert payload(client.get(brands_url(project_id)))["asymmetry_ko"] == []


class TestWhoMayDeclare:
    def test_a_read_only_caller_cannot_declare(
        self,
        client: TestClient,
        act_as: Callable[[Principal], None],
        project: tuple[Tenant, uuid.UUID],
    ) -> None:
        """등록하는 것이 곧 비교 집합이고, 비교 집합이 바뀌면 점유율이 바뀐다."""
        tenant, project_id = project
        act_as(tenant.viewer)

        response = client.post(
            brands_url(project_id), json={"display_name": "온담한의원", "is_own_brand": True}
        )

        assert response.status_code == 403

    def test_another_organizations_project_is_not_found(
        self,
        client: TestClient,
        act_as: Callable[[Principal], None],
        project: tuple[Tenant, uuid.UUID],
    ) -> None:
        tenant, _ = project
        act_as(tenant.analyst)

        response = client.get(brands_url(uuid.uuid4()))

        assert response.status_code == 404
        assert error_code(response) == "NOT_FOUND"
