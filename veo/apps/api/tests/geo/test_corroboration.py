"""참고 조회 — 남의 가게 이야기를 우리 고객 평판으로 세지 않는다.

실측에서 "병원마케팅 베놈" 을 조회하니 25건이 걸렸고, 그 중 **18건이 다른 업체**였다.
그대로 셌다면 있지도 않은 평판을 보고서에 적었을 것이다.

여기서 고정하는 것 둘:

* 이름이 스치기만 한 글은 **버리되 세어 둔다.** 조용히 버리면 "검색은 많이 나오는데
  보고서엔 몇 개 없다" 가 설명되지 않는다.
* 참고 자료는 **점수를 움직이지 않는다.** 움직이면 그 순간 참고가 아니라 채점이다.
"""

from __future__ import annotations

from veo.contracts.enums import ProviderState
from veo.geo.corroboration import build_profile, corroboration_payload
from veo.providers.naver.search import SearchItem, SearchOutcome, strip_markup


def item(**over: object) -> SearchItem:
    base: dict[str, object] = {
        "corpus": "blog",
        "source_type": "SOCIAL",
        "title": "온담한의원 다녀왔습니다",
        "description": "강남구 테헤란로에 있는 온담한의원 후기입니다.",
        "url": "https://blog.example/1",
    }
    base.update(over)
    return SearchItem(**base)  # type: ignore[arg-type]


PROFILE = build_profile(
    display_name="온담한의원",
    own_domains=("ondam.example",),
    address_terms=("서울 강남구 테헤란로 1",),
    phone_numbers=("02-123-4567",),
)


class TestTellingBusinessesApart:
    def test_a_similarly_named_business_is_not_counted_as_ours(self) -> None:
        """검색 1위가 "백세온담한의원" 이었다. 다른 병원이다."""
        outcome = SearchOutcome(
            items=(
                item(
                    title="백세온담한의원 이벤트",
                    description="부산 해운대구 백세온담한의원 소식입니다.",
                    url="https://blog.example/other",
                ),
            )
        )

        payload = corroboration_payload(outcome, PROFILE)

        assert payload["sources"] == []
        assert payload["lookup"]["rejected_as_another_business"] == 1

    def test_what_was_dropped_is_counted_not_hidden(self) -> None:
        """버린 것을 안 세면 "왜 이것뿐이냐" 에 답할 수 없다."""
        outcome = SearchOutcome(
            items=(
                item(),
                item(
                    title="백세온담한의원",
                    description="부산 해운대구입니다.",
                    url="https://blog.example/2",
                ),
            )
        )

        lookup = corroboration_payload(outcome, PROFILE)["lookup"]

        assert lookup["considered"] == 2
        assert lookup["accepted"] + lookup["rejected_as_another_business"] == 2


class TestWhatCountsAsAnOutsideVoice:
    def test_a_listing_the_business_manages_is_not_independent(self) -> None:
        """네이버 지역 등록은 사업자가 스스로 관리하는 자리다. 바깥의 목소리가 아니다."""
        outcome = SearchOutcome(
            items=(
                item(
                    corpus="local",
                    source_type="DIRECTORY",
                    title="온담한의원",
                    description="한의원",
                    url="https://place.example/1",
                    address="서울 강남구 테헤란로 1",
                    telephone="02-123-4567",
                ),
            )
        )

        sources = corroboration_payload(outcome, PROFILE)["sources"]

        assert sources, "지역 등록도 자료에는 남는다"
        assert sources[0]["independent"] is False
        assert sources[0]["claimed_profile"] is True

    def test_a_directory_listing_carries_the_facts_we_can_compare(self) -> None:
        outcome = SearchOutcome(
            items=(
                item(
                    corpus="local",
                    source_type="DIRECTORY",
                    title="온담한의원",
                    description="한의원",
                    url="https://place.example/1",
                    address="서울 강남구 테헤란로 1",
                    telephone="02-123-4567",
                ),
            )
        )

        facts = corroboration_payload(outcome, PROFILE)["sources"][0]["facts"]

        assert facts["address"]
        assert facts["telephone"]


class TestWhatWeTellTheReader:
    def test_the_lookup_names_the_engine_it_used(self) -> None:
        """네이버만 봤다는 사실이 빠지면 "웹 전체" 로 읽힌다."""
        payload = corroboration_payload(SearchOutcome(items=(item(),)), PROFILE)

        assert payload["lookup"]["engine"] == "NAVER"

    def test_corpora_we_could_not_reach_are_named(self) -> None:
        """말뭉치 하나가 실패한 것을 감추면 "언급이 적다" 로 읽힌다."""
        outcome = SearchOutcome(items=(), unavailable={"news": "일시적으로 실패했습니다."})

        assert corroboration_payload(outcome, PROFILE)["lookup"]["unavailable"] == {
            "news": "일시적으로 실패했습니다."
        }


class TestMarkup:
    def test_the_bold_tags_naver_adds_are_removed_before_matching(self) -> None:
        """`<b>` 가 남아 있으면 이름 대조가 어긋난다."""
        assert strip_markup("서울 <b>온담한의원</b> 후기") == "서울 온담한의원 후기"

    def test_entities_are_decoded(self) -> None:
        assert strip_markup("A &amp; B") == "A & B"


class TestReferenceDataNeverMovesTheScore:
    """움직이면 그 순간 참고가 아니라 채점이다.

    실측(www.seokorea.org, 8장): 참고 자료 없이 77.431377, 붙여도 77.431377.
    """

    def test_attaching_the_lookup_leaves_the_score_untouched(self) -> None:
        from dataclasses import replace

        from tests.geo.support import load_case

        from veo.geo.collectors.external_verifiability import CORROBORATION_PROVIDER
        from veo.geo.service import run_geo_readiness

        case = load_case("hospital_local")
        without = run_geo_readiness(case.context)

        payload = corroboration_payload(
            SearchOutcome(
                items=(
                    item(
                        corpus="local",
                        source_type="DIRECTORY",
                        title="온담한의원",
                        description="한의원",
                        url="https://place.example/1",
                        address="서울 강남구 테헤란로 1",
                    ),
                    item(url="https://blog.example/9"),
                )
            ),
            PROFILE,
        )
        with_reference = run_geo_readiness(
            replace(
                case.context,
                provider_states={
                    **case.context.provider_states,
                    CORROBORATION_PROVIDER: ProviderState.ENABLED,
                },
                provider_payloads={
                    **case.context.provider_payloads,
                    CORROBORATION_PROVIDER: payload,
                },
            )
        )

        assert with_reference.score.overall_score == without.score.overall_score

    def test_the_reference_area_is_still_declared_outside_the_score(self) -> None:
        from veo.geo.service import GEO_SPEC_ID
        from veo.scoring import latest_published

        spec = latest_published(GEO_SPEC_ID)
        external = next(c for c in spec.categories if c.id == "external_verifiability")

        assert external.contributes_to_score is False
