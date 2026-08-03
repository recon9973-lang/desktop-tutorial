"""의료광고 원고 검수 (P2-11) — 위반 판정기가 아니라 검토 신호기.

지키는 성질:

1. 금지 유형의 대표 표현이 걸리고, 걸린 자리(구절·오프셋)가 함께 나온다.
2. **부재도 신호다** — 시술 원고에 부작용 언급이 없으면 그 사실이 표시되고,
   고지가 있으면 조용하다.
3. 점수가 없고, 모든 응답에 "법률 판단이 아니다"라는 면책이 실린다.
4. 평범한 정보성 문장은 걸리지 않는다 — 검수기가 늑대 소년이 되면 아무도 안 읽는다.
"""

from __future__ import annotations

import pytest

pytest.importorskip("pydantic")

from veo.medical.review import DISCLAIMER_KO, review_copy


def categories(text: str) -> set[str]:
    return {finding.category_ko for finding in review_copy(text)}


class TestForbiddenPatterns:
    def test_a_testimonial_is_flagged_with_its_place(self) -> None:
        text = "실제 환자분의 치료 후기를 소개합니다. 3개월 만에 좋아졌어요."
        findings = review_copy(text)

        testimonial = [f for f in findings if f.category_ko == "치료경험담"]
        assert testimonial, "치료 후기 표현이 걸리지 않았다"
        assert "치료 후기" in testimonial[0].excerpt
        assert testimonial[0].offset is not None
        assert "제56조" in testimonial[0].reference_ko

    def test_the_classic_forbidden_phrases_are_each_caught(self) -> None:
        assert "치료효과 보장" in categories("저희는 완치를 약속드립니다.")
        assert "최상급·유일성 표현" in categories("국내 1위 임플란트 전문 병원입니다.")
        assert "비교·비방" in categories("타 병원과 비교해 보십시오.")
        assert "치료 전후 비교" in categories("전후 사진으로 확인하세요.")
        assert "가격 할인·이벤트" in categories("이번 달 보톡스 할인 이벤트! 선착순 10명.")
        assert "근거 불명 수치" in categories("만족도 98%를 자랑합니다.")
        assert "신의료기술 암시" in categories("세계 최초 도입한 최첨단 장비.")
        assert "기사·전문가 의견 가장" in categories("언론에서도 주목한 그 치료법.")


class TestAbsenceIsASignal:
    def test_a_procedure_text_without_side_effect_notes_is_flagged(self) -> None:
        text = "임플란트 식립은 1시간 정도 걸리며 당일 귀가가 가능합니다."
        assert "부작용 고지 확인" in categories(text)

    def test_a_procedure_text_with_side_effect_notes_stays_quiet(self) -> None:
        text = (
            "임플란트 식립은 1시간 정도 걸립니다. 시술 후 통증·부종 등 부작용이 있을 수 "
            "있으며 개인차가 있습니다."
        )
        assert "부작용 고지 확인" not in categories(text)

    def test_a_text_with_no_procedure_mention_needs_no_notes(self) -> None:
        assert "부작용 고지 확인" not in categories("저희 의원의 진료 시간은 평일 9시부터입니다.")


class TestHonestFraming:
    def test_findings_carry_no_score_anywhere(self) -> None:
        finding = review_copy("완치를 보장합니다.")[0]
        for value in vars(finding).values() if hasattr(finding, "__dict__") else []:
            assert not isinstance(value, (int, float)) or value is None
        # dataclass(slots) 라 vars 가 없을 수 있다 — 필드 목록으로 직접 확인한다.
        assert set(type(finding).__dataclass_fields__.keys()) == {
            "rule_id", "category_ko", "guidance_ko", "reference_ko", "excerpt", "offset",
        }, "점수 필드가 생기는 순간 '몇 점이면 안전'이라는 읽기가 생긴다"

    def test_the_disclaimer_says_what_this_is_not(self) -> None:
        assert "법률 판단이 아닙니다" in DISCLAIMER_KO
        assert "심의" in DISCLAIMER_KO

    def test_plain_information_passes_clean(self) -> None:
        text = (
            "본원은 지하철 2호선 역삼역 3번 출구에서 도보 5분 거리에 있습니다. "
            "진료 예약은 전화로 받습니다. 주차장은 건물 지하 1층입니다."
        )
        assert review_copy(text) == []
