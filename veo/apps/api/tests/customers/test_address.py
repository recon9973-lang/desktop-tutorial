"""거래처 대장의 소재지.

**상호는 식별자가 아니다.** `서울치과` 는 수십 곳이고, 대장에 이름만 적혀 있으면 어느
서울치과를 맡고 있는지 사람이 목록에서 가리지 못한다.

이 칸이 지키는 것 셋 —

1. 넣은 것이 그대로 돌아온다.
2. **비워도 등록된다.** 필수로 만들면 모를 때 아무거나 채워지고, 지어낸 소재지는 없는
   것보다 나쁘다.
3. 부분 수정에서 **안 보낸 값은 안 바뀐다.** 소재지를 적어 둔 거래처에 이름만 고치러
   들어왔다가 소재지가 지워지면, 지워진 줄도 모른다.

측정용 값이 아니다 — AI 답변과 글자로 대조하는 소재지 표현은
`brand_identities.address_terms` 에 따로 있다. 그쪽은 "답변이 말할 만한 표현"이고
이쪽은 "우편물이 가는 곳"이다.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from veo.customers.schemas import CustomerCreateRequest, CustomerUpdateRequest
from veo.customers.service import UPDATABLE


class TestTheField:
    def test_소재지를_받는다(self) -> None:
        request = CustomerCreateRequest(name="서울치과", address="서울 강남구 테헤란로 1")

        assert request.address == "서울 강남구 테헤란로 1"

    def test_비워도_등록된다(self) -> None:
        """모를 때 아무거나 채워지느니 비어 있는 편이 낫다."""
        assert CustomerCreateRequest(name="서울치과").address is None

    def test_앞뒤_공백을_떼고_저장한다(self) -> None:
        request = CustomerCreateRequest(name="서울치과", address="  대구 북구 옥산로 95  ")

        assert request.address == "대구 북구 옥산로 95"

    def test_건물명_층수까지_들어간다(self) -> None:
        """도로명 + 건물명 + 층수. 실측 venomad.com 이 이 모양이다."""
        long_one = "대구광역시 수성구 용학로 25길 54, 화인탑팰리스 5층"
        assert CustomerCreateRequest(name="베놈", address=long_one).address == long_one

    def test_한없이_긴_값은_거부한다(self) -> None:
        with pytest.raises(ValidationError):
            CustomerCreateRequest(name="서울치과", address="가" * 301)


class TestPartialUpdate:
    def test_소재지만_고칠_수_있다(self) -> None:
        request = CustomerUpdateRequest(address="부산 해운대구 센텀로 1")

        assert request.changes() == {"address": "부산 해운대구 센텀로 1"}

    def test_안_보낸_소재지는_바뀌지_않는다(self) -> None:
        """이름만 고치러 들어왔다가 소재지가 지워지면, 지워진 줄도 모른다."""
        request = CustomerUpdateRequest(name="서울미소치과")

        assert "address" not in request.changes()

    def test_고칠_수_있는_칸_목록에_들어_있다(self) -> None:
        """서비스가 거르는 목록에 없으면 요청은 통과하고 값은 조용히 버려진다."""
        assert "address" in UPDATABLE
