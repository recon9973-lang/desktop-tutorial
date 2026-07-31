"""구조화 데이터를 아예 만들지 않은 것은 "해당 없음" 이 아니다.

지금까지 JSON-LD 가 한 줄도 없는 사이트는 구조화 데이터 네 항목이 모두 해당 없음이
되어, **12.5점이 통째로 분모에서 빠졌다.** 그래서 이런 일이 벌어졌다:

    스키마를 만든 사이트    → 분모 100   (구조화 데이터 12.5점을 걸고 채점받는다)
    스키마를 안 만든 사이트 → 분모 87.5  (그 항목이 사라져 나머지로 100점을 받을 수 있다)

**만든 쪽이 더 어려운 시험을 본다.** 연동 영역에서 고친 것과 똑같은 유인이고, "없는 것은
0점 처리하고, 그것을 빼고 환산하면 안 된다" 는 규칙에 정면으로 어긋난다. 같은 영역의
오픈그래프는 없으면 실패로 감점하는데 JSON-LD 만 면제였다는 점에서 일관성도 없었다.

고치는 방향은 네 항목을 실패로 바꾸는 것이 **아니다.** 선언이 하나도 없는 사이트에
"JSON-LD 문법 오류" 라고 적으면 없는 사실을 지어내는 것이다. 대신 **선언 자체를 묻는
항목**을 따로 두고, 나머지 넷은 검증할 대상이 없으므로 해당 없음으로 남긴다.

결과적으로 선언이 없으면 그 영역에서 채점되는 항목은 이 하나뿐이고, 그것이 실패하므로
영역 점수는 0이 된다 — 배점 12.5점은 분모에 그대로 남은 채로. 사용자가 든 예시
그대로다: 20점 항목이 0점이면 나머지가 만점이라도 80점이다.
"""

from __future__ import annotations

from tests.seo.support import build_context, by_id, issues_for

from veo.scoring import CheckStatus
from veo.seo.collectors import StructuredDataCollector
from veo.seo.service import run_seo_scan

COLLECTOR = StructuredDataCollector()
DECLARED = "seo.sd.declared"
DERIVED = (
    "seo.sd.jsonld_parses",
    "seo.sd.required_properties_present",
    "seo.sd.matches_visible_content",
    "seo.sd.google_supported_type",
)


class TestAbsenceIsAFailureNotAnExemption:
    def test_a_site_without_any_structured_data_fails_the_declaration_check(self) -> None:
        result = COLLECTOR.collect(build_context("brochure_na"))

        assert by_id(result)[DECLARED].status is CheckStatus.FAIL

    def test_a_site_with_structured_data_passes_it(self) -> None:
        result = COLLECTOR.collect(build_context("healthy"))

        assert by_id(result)[DECLARED].status is CheckStatus.PASS

    def test_the_derived_checks_stay_not_applicable(self) -> None:
        """선언이 없는데 "문법 오류" 라고 적으면 없는 사실을 지어내는 것이다."""
        outcomes = by_id(COLLECTOR.collect(build_context("brochure_na")))

        for check_id in DERIVED:
            assert outcomes[check_id].status is CheckStatus.NOT_APPLICABLE, check_id

    def test_the_failure_says_what_to_add(self) -> None:
        """병원 고객에게 "구조화 데이터 없음" 만 주면 무엇을 만들지 알 수 없다."""
        drafts = issues_for(COLLECTOR.collect(build_context("brochure_na")), DECLARED)

        assert drafts
        assert drafts[0].remediation_ko
        assert drafts[0].fix_example


class TestTheBudgetNoLongerVanishes:
    def test_the_structured_data_checks_stay_in_the_denominator(self) -> None:
        """이 검사가 존재하는 이유. 구조화 데이터 몫이 사라지면 안 된다.

        처음에는 `structured_data` **영역 점수가 0** 인지 봤다. 명세 1.8.0 이 채점을
        검색 여정 단계로 다시 나누면서 그 영역이 사라졌고, 구조화 데이터 검사들은
        다른 검사와 같은 단계('클릭·표현')에 섞였다. 단계 점수는 이제 0 이 아니다 —
        같은 단계의 다른 검사들이 통과하기 때문이고, 그것은 옳다.

        영역 점수는 재편으로 바뀌지만 **검사가 분모에 남아 점수를 잃는다** 는 사실은
        바뀌면 안 된다. 그것이 원래 지키려던 것이고, 이제 그것을 직접 본다.
        """
        score = run_seo_scan(build_context("brochure_na")).score
        rows = {row["check_id"]: row for row in score.trace["checks"]}

        declared = rows["seo.sd.declared"]
        assert declared["counted_in_budget"] is True, "선언 없음이 분모에서 빠졌다"
        assert declared["penalty"] > 0.0, "선언이 없는데 잃은 점수가 없다"

    def test_a_site_without_schema_is_scored_out_of_one_hundred(self) -> None:
        score = run_seo_scan(build_context("brochure_na")).score

        assert score.effective_weight_total == 100.0

    def test_not_making_schema_is_never_easier_than_making_it(self) -> None:
        """안 만든 쪽의 분모가 더 작으면, 안 만들수록 유리해진다."""
        with_schema = run_seo_scan(build_context("healthy")).score
        without = run_seo_scan(build_context("brochure_na")).score

        assert without.effective_weight_total == with_schema.effective_weight_total

    def test_a_broken_declaration_costs_less_than_no_declaration(self) -> None:
        """선언은 했는데 타입이 어긋난 것과, 아예 없는 것은 같은 무게가 아니다.

        선언이 있으면 나머지 구조화 데이터 검사들이 함께 채점되므로 하나가 어긋나도
        일부만 잃는다. 아예 없으면 그 검사들이 전부 해당 없음이 되고 선언 검사 하나가
        온전히 실패한다.
        """
        broken = run_seo_scan(build_context("broken_jsonld")).score
        absent = run_seo_scan(build_context("brochure_na")).score

        def lost(score) -> float:  # type: ignore[no-untyped-def]
            return sum(
                row["penalty"]
                for row in score.trace["checks"]
                if row["check_id"].startswith("seo.sd.")
            )

        assert lost(absent) > lost(broken)
