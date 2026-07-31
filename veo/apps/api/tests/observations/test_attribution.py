"""같은 이름의 다른 병원을 우리 고객으로 세지 않는다.

## 실측으로 잡은 결함

관측 파이프라인이 쓰던 판별기는 브랜드 이름이 답변 문자열 안에 들어 있으면 언급으로
세었다. 그것뿐이었다.

    답변: "부산 해운대구의 백세온담한의원이 유명합니다."
    고객: 온담한의원 (서울 강남구)

    옛 판별기 : mentioned=True         ← 다른 병원이다
    이 판별기 : NEEDS_REVIEW (0.00)    ← 사람에게 넘긴다

한국 병원 상호는 겹친다. `서울치과`·`중앙병원` 은 저마다 수십 곳이고, `온담한의원` 처럼
고유한 이름조차 `백세온담한의원` 같은 더 긴 상호에 통째로 들어간다. 부분 문자열로 세면
**틀리는 방향이 항상 위쪽**이라 노출률이 실제보다 좋아 보이고, 고객은 확인할 방법이 없다.

동명 업체를 가리는 모듈(`veo.observations.detection`)은 이미 완성되어 있었고 `src/`
안에서 아무도 부르지 않았다. 두 벌 중 **느슨한 쪽이 돌고 있었다** — #20(노출 지표 모듈이
둘이었다)과 같은 모양이라 그때와 같이 느슨한 쪽을 지웠다.

그리고 `brand_identities` 는 주소·전화번호를 이미 받아 저장하고 있었는데, 옛 판별기는
이름과 도메인만 읽었다. **고객이 넣은 전화번호는 측정에 한 번도 쓰이지 않았다.**
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from veo.observations.attribution import DisambiguatingMentionDetector
from veo.observations.detection.disambiguation import BrandProfile
from veo.observations.providers.base import CitationSupport, CostBasis
from veo.observations.providers.storage import RecordedAnswer

SYNTHETIC = "[합성 응답 — 실제 AI 답변 아님]"

#: 가상 사례다. 실재 병원에 대한 지적으로 읽히면 안 된다.
OURS = BrandProfile(
    entity_key="ondam",
    display_name="온담한의원",
    own_domains=("ondam.example",),
    address_terms=("서울 강남구 테헤란로",),
    phone_numbers=("02-123-4567",),
)

#: 이름만으로는 갈리지 않는 상호. 실제로 이런 고객이 훨씬 많다.
GENERIC = BrandProfile(
    entity_key="seoul-dental",
    display_name="서울치과",
    own_domains=("seoul-dental.example",),
    address_terms=("서울 강남구 테헤란로",),
)


def answer(
    text: str,
    *,
    citations: tuple[str, ...] = (),
    support: CitationSupport = CitationSupport.STRUCTURED,
) -> RecordedAnswer:
    return RecordedAnswer(
        engine="OPENAI",
        model="gpt-5",
        model_version="gpt-5-2026-05-01",
        text=f"{SYNTHETIC} {text}",
        citations=citations,
        citation_support=support,
        latency_ms=1200,
        cost_usd=0.001,
        cost_basis=CostBasis.CALCULATED_FROM_USAGE,
        input_tokens=100,
        output_tokens=200,
        executed_at=datetime(2026, 7, 31, 4, 0, tzinfo=UTC),
    )


class TestTheDefectThisReplaced:
    def test_a_longer_business_name_containing_ours_is_not_our_mention(self) -> None:
        """옛 판별기가 `mentioned=True` 를 돌려주던 문장 그대로다."""
        verdict = DisambiguatingMentionDetector(OURS).judge(
            answer("부산 해운대구의 백세온담한의원이 교통사고 치료로 유명합니다.")
        )

        assert verdict.mentioned is False, "다른 병원을 우리 노출로 세면 안 된다"
        assert verdict.needs_review is True, "안 나온 것이 아니라 갈리지 않은 것이다"
        assert verdict.matched_entities == ()

    def test_the_held_finding_says_why_it_was_held(self) -> None:
        """이유 없이 보류된 건은 질문이 아니라 고장으로 읽힌다(0-A).

        이 문장이 비어 있던 시기가 있었다. `assess()` 의 경계 신호가 `spans` 가 빈
        경우의 조기 반환 **아래**에 있었고, 이 경로는 정확히 그 경우에만 도달한다.
        """
        verdict = DisambiguatingMentionDetector(OURS).judge(
            answer("부산 해운대구의 백세온담한의원이 유명합니다.")
        )

        assert verdict.evidence_ko, "보류 사유가 비어 있으면 검수자가 판단할 수 없다"
        assert any("온담한의원" in line for line in verdict.evidence_ko)


class TestWhatTheCustomerDeclaredIsActuallyUsed:
    """흔한 상호를 확정선 위로 올리는 것은 전화번호다. 그 값이 버려지고 있었다."""

    def test_a_generic_name_alone_is_held_for_review(self) -> None:
        bare = BrandProfile(entity_key="seoul-dental", display_name="서울치과")

        verdict = DisambiguatingMentionDetector(bare).judge(
            answer("서울치과에서 임플란트를 받았습니다.")
        )

        assert verdict.needs_review is True
        assert verdict.mentioned is False

    def test_a_declared_phone_number_next_to_the_name_settles_it(self) -> None:
        withphone = BrandProfile(
            entity_key="seoul-dental",
            display_name="서울치과",
            address_terms=("서울 강남구 테헤란로",),
            phone_numbers=("02-987-6543",),
        )

        verdict = DisambiguatingMentionDetector(withphone).judge(
            answer("서울 강남구 테헤란로의 서울치과(02-987-6543)를 추천합니다.")
        )

        assert verdict.mentioned is True
        assert verdict.matched_entities == ("seoul-dental",)

    def test_a_foreign_locality_beside_a_generic_name_keeps_it_held(self) -> None:
        verdict = DisambiguatingMentionDetector(GENERIC).judge(
            answer("대구 수성구의 서울치과가 야간 진료를 합니다.")
        )

        assert verdict.mentioned is False
        assert verdict.needs_review is True


class TestCitations:
    def test_our_own_cited_domain_settles_a_generic_name(self) -> None:
        """도메인은 동명 업체와 공유되지 않는다. 이름이 흔해도 이것으로 갈린다."""
        verdict = DisambiguatingMentionDetector(GENERIC).judge(
            answer(
                "대구 수성구의 서울치과가 야간 진료를 합니다.",
                citations=("https://seoul-dental.example/hours",),
            )
        )

        assert verdict.mentioned is True
        assert verdict.cited is True

    def test_prose_urls_are_not_citations_when_the_engine_returned_none(self) -> None:
        """본문에 주소가 적힌 것은 그 엔진이 우리를 근거로 삼았다는 뜻이 아니다."""
        verdict = DisambiguatingMentionDetector(OURS).judge(
            answer(
                "서울 강남구 테헤란로의 온담한의원 https://ondam.example 을 참고하세요.",
                citations=("https://ondam.example/",),
                support=CitationSupport.NOT_EXPOSED_BY_PROVIDER,
            )
        )

        assert verdict.mentioned is True
        assert verdict.cited is False

    def test_a_citation_never_rides_on_an_unconfirmed_mention(self) -> None:
        """누구인지 모르는 이름에 붙은 인용은 그 사람의 인용이 아니다."""
        verdict = DisambiguatingMentionDetector(OURS).judge(
            answer(
                "부산 해운대구의 백세온담한의원이 유명합니다.",
                citations=("https://another-clinic.example/post",),
            )
        )

        assert verdict.cited is False
        assert verdict.mentioned is False


class TestTheThreeOutcomesStaySeparate:
    def test_a_name_that_never_appears_has_no_confidence_at_all(self) -> None:
        """`confidence=None` 과 `confidence=0.0` 은 다른 사실이다.

        전자는 "이름이 안 나왔다", 후자는 "나왔는데 이 고객인지 모르겠다" 이다. 같은
        칸에 두면 화면에서 구별할 방법이 없다.
        """
        verdict = DisambiguatingMentionDetector(OURS).judge(
            answer("강남 지역 한의원 세 곳을 소개합니다.")
        )

        assert verdict.mentioned is False
        assert verdict.needs_review is False
        assert verdict.confidence is None

    def test_a_held_name_carries_a_confidence_number(self) -> None:
        verdict = DisambiguatingMentionDetector(GENERIC).judge(
            answer("대구 수성구의 서울치과가 야간 진료를 합니다.")
        )

        assert verdict.confidence is not None
        assert verdict.confidence < 0.75

    def test_confirmed_and_held_cannot_both_be_claimed(self) -> None:
        from veo.observations.runner import MentionVerdict

        with pytest.raises(ValueError, match="보류는 아직 언급이 아닙니다"):
            MentionVerdict(mentioned=True, cited=False, needs_review=True)


class TestTheLooseDetectorIsGone:
    def test_no_substring_detector_remains_to_be_picked_by_mistake(self) -> None:
        """두 벌을 남겨 두면 다음 사람이 둘 중 하나를 고르게 된다(0-D)."""
        import veo.observations.runner as runner

        assert not hasattr(runner, "SubstringMentionDetector")
