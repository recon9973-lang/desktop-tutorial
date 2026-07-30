"""적게 재면 분모가 줄어드는가 — GEO 쪽 문지기.

SEO 에는 같은 검사가 `tests/seo/test_denominator_is_fixed.py` 로 있었다. GEO 에는
없었고, 그래서 수집기 두 곳이 **못 잰 것을 해당 없음으로 접는** 상태로 남아 있었다.
그 상태에서는 한 장만 보는 영업용 간편 진단이 사이트 전체 진단보다 유리해진다.

## 무엇을 재는가

점수 자체가 표본에 따라 달라지는 것은 **정상이다.** 15장에는 홈 한 장보다 실제 결함이
더 많고, 더 많이 재서 더 많이 찾는 것은 이 도구가 해야 할 일이다.

금지된 것은 **분모가 표본 크기에 따라 움직이는 것**이다. 적게 재서 배점이 빠지면
"덜 재는 편이 유리" 가 성립한다. 그래서 이 파일은 점수를 비교하지 않고 **분모에서 빠진
항목의 목록**을 비교한다.
"""

from __future__ import annotations

from dataclasses import replace

from tests.geo.support import GeoCase, load_case

from veo.geo.service import run_geo_readiness
from veo.scoring import CheckStatus


def excluded_from_the_denominator(case_context: object) -> set[str]:
    report = run_geo_readiness(case_context)  # type: ignore[arg-type]
    return {
        outcome.check_id
        for outcome in report.score.outcomes
        if outcome.status is CheckStatus.NOT_APPLICABLE
    }


def only_the_entry_page(case: GeoCase) -> object:
    """같은 사이트를 **한 장만** 본 것으로 좁힌다. 영업용 간편 진단이 이 모양이다."""
    context = case.context
    primary = context.primary_document
    assert primary is not None
    return replace(
        context,
        documents={primary.final_url: primary},
        sitemap_documents={},
        crawl_is_exhaustive=False,
    )


def test_looking_at_one_page_never_removes_a_check_from_the_denominator() -> None:
    """이것이 '덜 재는 편이 유리' 를 막는 유일한 문장이다.

    한 장만 봤을 때 분모에서 빠지는 항목이 **하나라도 더 많으면**, 그 차이만큼 남은
    항목의 몫이 부풀고 점수가 올라간다. 사이트가 나아진 것이 아니라 우리가 덜 본 것뿐인데.
    """
    case = load_case("hospital_local")

    whole = excluded_from_the_denominator(case.context)
    single = excluded_from_the_denominator(only_the_entry_page(case))

    grew = single - whole
    assert grew == set(), (
        "한 장만 봤을 때 이 항목들이 추가로 분모에서 빠집니다 — "
        f"측정 불가여야 합니다: {sorted(grew)}"
    )


def test_the_checks_we_could_not_judge_are_reported_as_unmeasured() -> None:
    """빠지지 않는다면 어디로 가는가 — 측정 불가로 남아 0점을 받는다.

    실패로 보고하지는 않는다. 사이트의 결함이 아니라 우리가 못 잰 것이다.
    """
    case = load_case("hospital_local")
    report = run_geo_readiness(only_the_entry_page(case))  # type: ignore[arg-type]
    statuses = {outcome.check_id: outcome.status for outcome in report.score.outcomes}

    assert statuses["geo.extract.no_duplicate_answer_blocks"] is CheckStatus.UNKNOWN
    assert statuses["geo.fresh.sitemap_lastmod_reliable"] is CheckStatus.UNKNOWN


def test_the_unmeasured_checks_say_what_would_settle_them() -> None:
    """"측정 불가" 만 띄우면 고장으로 읽힌다. 무엇을 하면 판정되는지 함께 적는다."""
    case = load_case("hospital_local")
    report = run_geo_readiness(only_the_entry_page(case))  # type: ignore[arg-type]
    notes = {
        outcome.check_id: outcome.note or ""
        for outcome in report.score.outcomes
        if outcome.status is CheckStatus.UNKNOWN
    }

    assert "사이트 전체" in notes["geo.extract.no_duplicate_answer_blocks"]
    assert notes["geo.fresh.sitemap_lastmod_reliable"]
