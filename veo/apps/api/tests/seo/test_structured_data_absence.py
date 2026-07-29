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
    def test_the_category_stays_in_the_denominator(self) -> None:
        """이 검사가 존재하는 이유. 12.5점이 사라지면 안 된다."""
        score = run_seo_scan(build_context("brochure_na")).score

        structured = next(c for c in score.categories if c.category_id == "structured_data")
        assert structured.status == "SCORED"
        assert structured.score == 0.0

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

        선언이 있으면 네 항목이 함께 채점되므로 하나가 어긋나도 영역 점수의 일부만
        잃는다. 아예 없으면 채점되는 항목이 선언 검사 하나뿐이라 영역이 0이 된다.
        """
        broken = run_seo_scan(build_context("broken_jsonld")).score
        absent = run_seo_scan(build_context("brochure_na")).score

        broken_sd = next(c for c in broken.categories if c.category_id == "structured_data")
        absent_sd = next(c for c in absent.categories if c.category_id == "structured_data")

        assert broken_sd.score is not None
        assert absent_sd.score == 0.0
        assert broken_sd.score > absent_sd.score
