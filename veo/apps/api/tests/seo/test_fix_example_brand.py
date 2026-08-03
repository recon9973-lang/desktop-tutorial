"""고침 예시 코드의 상호 자리.

이 코드는 **복사해서 사이트에 붙여넣으라고** 내놓는 것이다. 그래서 두 가지가 동시에
지켜져야 한다.

1. 가상의 남의 상호가 박혀 있으면 안 된다. 예전에 "온담의원" 이 하드코딩돼 있었고,
   읽는 사람은 그것을 **자기 사이트에서 측정된 값**으로 읽었다.
2. 아는 업체명은 채워 준다. 자리표시자가 남으면 담당자가 한 번 더 손봐야 하고,
   잊으면 "업체명" 이라는 글자가 그대로 사이트에 올라간다.

그리고 모르는 이름은 **지어내지 않는다** — 틀린 상호를 확신 있게 붙여넣게 만드는 것이
자리표시자보다 나쁘다.
"""

from __future__ import annotations

import pytest

from veo.seo.fix_examples import BRAND_PLACEHOLDER, code_example_for, with_brand

# 자리표시자가 실제로 들어 있는 예시 하나 — 가장 많이 붙여넣는 구조화 데이터.
_WITH_BRAND = "seo.sd.declared"


class TestKnownBrandGetsFilledIn:
    def test_placeholder_is_replaced(self) -> None:
        example = code_example_for(_WITH_BRAND)
        assert example is not None
        assert BRAND_PLACEHOLDER in example  # 전제: 채울 자리가 있다

        filled = with_brand(example, "온담한의원")

        assert filled is not None
        assert "온담한의원" in filled
        assert BRAND_PLACEHOLDER not in filled

    def test_every_occurrence_is_replaced(self) -> None:
        """한 예시에 상호가 두 번 나오는 검사가 있다(화면 이름 = 구조화 데이터 이름)."""
        example = code_example_for("geo.sd.matches_visible_content")
        assert example is not None

        filled = with_brand(example, "참사랑한의원")

        assert filled is not None
        assert BRAND_PLACEHOLDER not in filled
        assert filled.count("참사랑한의원") == example.count(BRAND_PLACEHOLDER)


class TestUnknownBrandKeepsThePlaceholder:
    @pytest.mark.parametrize("brand", [None, "", "   "])
    def test_no_name_no_substitution(self, brand: str | None) -> None:
        """등록된 이름이 없으면 자리표시자 그대로 — 지어내지 않는다."""
        example = code_example_for(_WITH_BRAND)

        assert with_brand(example, brand) == example

    def test_missing_example_stays_missing(self) -> None:
        """예시가 없는 검사는 여전히 없다 — 채울 것이 없다고 만들어 내지 않는다."""
        assert with_brand(None, "온담한의원") is None


class TestNoInventedClinicNames:
    """등록부 어디에도 실재하거나 가상인 특정 상호가 남아 있지 않다."""

    @pytest.mark.parametrize("name", ["온담", "참사랑", "○○"])
    def test_registry_is_free_of_brand_names(self, name: str) -> None:
        from veo.seo import fix_examples

        offenders = [
            check_id
            for check_id in fix_examples._EXAMPLES
            if name in (code_example_for(check_id) or "")
        ]

        assert offenders == [], f"예시 코드에 상호 '{name}' 가 남아 있습니다: {offenders}"
