"""Answer extractability — heuristics, honestly labelled.

Nothing in this module is a measurement of whether an AI engine *would* quote the page.
It measures shape: is there a passage that answers the heading, does it stand on its own,
is the document more content than furniture.
"""

from __future__ import annotations

from tests.geo.support import load_case

from veo.geo.collectors.answer_extractability import AnswerExtractabilityCollector
from veo.geo.extractability import analyse_extractability
from veo.geo.parsing import parse_html
from veo.scoring import CheckStatus

ANSWERED = """
<html><body><main><article>
<h1>전기 주전자 물때 제거 방법</h1>
<p>전기 주전자의 물때는 물과 식초를 1대 1로 섞어 10분 끓인 뒤 헹구면 대부분 제거됩니다.
구연산을 쓸 경우 물 1리터에 구연산 한 큰술을 넣고 같은 방법으로 진행합니다.</p>
<h2>식초를 쓰는 방법</h2>
<p>식초와 물을 같은 양으로 채우고 끓인 다음 30분간 두었다가 버립니다.
이후 맑은 물로 두 번 헹굽니다.</p>
</article></main></body></html>
"""

UNANSWERED = """
<html><body><div id="content">
<h3>안내</h3>
<p>이것은 매우 중요합니다.</p>
<p>그래서 위에서 말씀드린 것처럼 진행하시면 됩니다.</p>
</div></body></html>
"""


def run(name: str) -> dict[str, CheckStatus]:
    result = AnswerExtractabilityCollector().collect(load_case(name).context)
    return {o.check_id: o.status for o in result.outcomes}


# --------------------------------------------------------------------------- #
# Unit level
# --------------------------------------------------------------------------- #


def test_a_page_that_answers_its_heading_is_recognised() -> None:
    signals = analyse_extractability(parse_html(ANSWERED))
    assert signals.direct_answer is not None
    assert "식초" in signals.direct_answer.text


def test_a_page_with_no_answer_passage_reports_none() -> None:
    signals = analyse_extractability(parse_html(UNANSWERED))
    assert signals.direct_answer is None


def test_anaphoric_openings_lower_the_self_contained_ratio() -> None:
    answered = analyse_extractability(parse_html(ANSWERED))
    unanswered = analyse_extractability(parse_html(UNANSWERED))
    assert answered.self_contained_ratio > unanswered.self_contained_ratio


def test_heading_structure_notices_a_missing_h1() -> None:
    assert analyse_extractability(parse_html(ANSWERED)).headings.h1_count == 1
    assert analyse_extractability(parse_html(UNANSWERED)).headings.h1_count == 0


def test_heading_structure_notices_a_skipped_level() -> None:
    skipped = parse_html("<html><body><main><h1>제목</h1><h4>소제목</h4></main></body></html>")
    assert analyse_extractability(skipped).headings.skipped_levels


def test_boilerplate_ratio_falls_when_furniture_dominates() -> None:
    document = load_case("generic_service").context.primary_document
    assert document is not None
    thin = analyse_extractability(parse_html(document.text()))
    rich = analyse_extractability(parse_html(ANSWERED))
    assert 0.0 <= thin.main_content_ratio < rich.main_content_ratio <= 1.0


# --------------------------------------------------------------------------- #
# Collector level
# --------------------------------------------------------------------------- #


def test_a_well_shaped_article_passes_extractability() -> None:
    statuses = run("publisher_article")
    assert statuses["geo.extract.direct_answer_present"] is CheckStatus.PASS
    assert statuses["geo.extract.heading_structure_semantic"] is CheckStatus.PASS
    assert statuses["geo.extract.low_boilerplate_ratio"] is CheckStatus.PASS
    assert statuses["geo.extract.tables_lists_machine_readable"] is CheckStatus.PASS


def test_a_thin_marketing_page_fails_extractability() -> None:
    statuses = run("generic_service")
    assert statuses["geo.extract.direct_answer_present"] is CheckStatus.FAIL
    assert statuses["geo.extract.heading_structure_semantic"] is CheckStatus.FAIL
    assert statuses["geo.extract.low_boilerplate_ratio"] in {
        CheckStatus.FAIL,
        CheckStatus.WARNING,
    }
    assert statuses["geo.extract.passage_self_contained"] in {
        CheckStatus.FAIL,
        CheckStatus.WARNING,
    }


def test_numbers_left_in_prose_fail_the_structure_check() -> None:
    assert run("generic_service")["geo.extract.tables_lists_machine_readable"] is CheckStatus.FAIL


def test_a_page_with_nothing_to_tabulate_is_not_applicable() -> None:
    assert (
        run("corporate_site")["geo.extract.tables_lists_machine_readable"]
        is CheckStatus.NOT_APPLICABLE
    )


def test_a_block_repeated_on_two_urls_is_reported() -> None:
    assert run("generic_service")["geo.extract.no_duplicate_answer_blocks"] in {
        CheckStatus.FAIL,
        CheckStatus.WARNING,
    }


def test_distinct_pages_pass_the_duplication_check_when_the_crawl_saw_the_whole_site() -> None:
    """부재("중복 없음")는 표본이 전체일 때만 증명된다.

    이 시험의 옛 이름에는 뒷조건이 없었다 — 잘린 크롤이 부재를 단정하는 결함을
    이름이 그대로 지키고 있었다(0-I). 2026-08-01 실도메인 8개 실측에서 같은 유형의
    결함이 SEO 쪽에 실제로 나왔다.
    """
    assert run("hospital_local")["geo.extract.no_duplicate_answer_blocks"] is CheckStatus.PASS


def test_a_truncated_crawl_cannot_assert_the_absence_of_duplicates() -> None:
    """100장 상한에 잘린 크롤에서 "중복 없음" 은 표본에 대한 사실일 뿐이다."""
    result = AnswerExtractabilityCollector().collect(
        load_case("hospital_local", crawl_is_exhaustive=False).context
    )
    by_id = {o.check_id: o for o in result.outcomes}
    outcome = by_id["geo.extract.no_duplicate_answer_blocks"]

    assert outcome.status is CheckStatus.UNKNOWN
    assert "확인하지 못했습니다" in (outcome.note or "")


def test_a_confirmed_single_page_site_is_not_applicable_for_duplication() -> None:
    """진짜 1장짜리 사이트에는 중복의 상대가 없다 — 해당 없음이 사실이다.

    publisher_article 은 문서가 하나이고 **sitemap 이 스스로 "페이지가 하나"라고
    선언**한다. 그 두 가지가 모두 있을 때만 해당 없음이 허락된다.
    """
    assert (
        run("publisher_article")["geo.extract.no_duplicate_answer_blocks"]
        is CheckStatus.NOT_APPLICABLE
    )


def test_a_truncated_single_page_crawl_cannot_judge_duplication() -> None:
    """한 장만 **가져온** 것은 "중복이 없다" 가 아니라 못 잰 것이다.

    해당 없음으로 접으면 배점이 분모에서 빠지고, 그러면 **덜 재는 편이 유리해진다.**
    이 시험의 앞판은 크롤 잘림 플래그가 조용히 False 로 남던 시절의 결과(UNKNOWN)를
    픽스처 전체에 단정하고 있었다 — 진짜 1장짜리 사이트까지 못 잰 것으로 세면서(0-I).
    """
    result = AnswerExtractabilityCollector().collect(
        load_case("publisher_article", crawl_is_exhaustive=False).context
    )
    by_id = {o.check_id: o for o in result.outcomes}

    assert by_id["geo.extract.no_duplicate_answer_blocks"].status is CheckStatus.UNKNOWN


def test_extractability_never_claims_direct_observation() -> None:
    result = AnswerExtractabilityCollector().collect(load_case("hospital_local").context)
    for outcome in result.outcomes:
        assert outcome.confidence_level != "DIRECT_OBSERVATION", outcome.check_id
