"""The comparison engine: refuse, or explain, but never quietly average.

The tests are grouped by the thing that can go wrong:

1. two like measurements compare, and the arithmetic matches a number a person computed;
2. every blocking difference refuses, in Korean, naming the field;
3. the one waiver that exists waives exactly one thing and still reports it;
4. a lopsided pair of coverages produces a low confidence that says why.
"""

from __future__ import annotations

from datetime import timedelta

import pytest
from competitor_support import (
    BASE_MEASURED_AT,
    categories_from,
    category,
    conditions,
    load_fixture,
    measurement,
)

from veo.competitors.comparison import (
    CheckVerdict,
    compare,
)
from veo.scoring import CheckStatus


def pair_of(**condition_overrides: object):  # type: ignore[no-untyped-def]
    """Our site and one competitor, alike except for the overrides given."""
    ours = measurement(
        "us",
        "우리 사이트",
        overall=70.0,
        categories=(category("crawl_indexability", 80.0, scored=("seo.http.status_ok",)),),
        checks={"seo.http.status_ok": CheckStatus.PASS},
    )
    theirs = measurement(
        "rival",
        "경쟁사 A",
        overall=75.0,
        categories=(category("crawl_indexability", 90.0, scored=("seo.http.status_ok",)),),
        checks={"seo.http.status_ok": CheckStatus.PASS},
        measurement_conditions=conditions(**condition_overrides),  # type: ignore[arg-type]
    )
    return ours, theirs


# --------------------------------------------------------------------------- #
# 1. Like measurements compare, and the numbers are the ones a person computed
# --------------------------------------------------------------------------- #


def test_identical_conditions_compare_cleanly() -> None:
    ours, theirs = pair_of()
    result = compare(ours, [theirs])

    assert len(result.pairs) == 1
    pair = result.pairs[0]
    assert pair.comparable is True
    assert pair.refusal_ko is None
    assert pair.blocking_differences == ()
    assert pair.overall_delta == pytest.approx(-5.0)


def test_category_and_overall_deltas_match_the_hand_computed_fixture() -> None:
    fixture = load_fixture("category_deltas.json")
    weights = fixture["category_weights"]

    ours = measurement(
        "us",
        "우리 사이트",
        overall=fixture["ours"]["overall"],
        coverage=fixture["ours"]["coverage"],
        confidence=fixture["ours"]["confidence"],
        categories=categories_from(fixture["ours"]["categories"], weights),
    )
    theirs = measurement(
        "rival",
        "경쟁사 A",
        overall=fixture["theirs"]["overall"],
        coverage=fixture["theirs"]["coverage"],
        confidence=fixture["theirs"]["confidence"],
        categories=categories_from(fixture["theirs"]["categories"], weights),
    )

    pair = compare(ours, [theirs]).pairs[0]

    assert pair.overall_delta == pytest.approx(fixture["expected_overall_delta"])
    computed = {c.category_id: c.delta for c in pair.categories}
    for category_id, expected in fixture["expected_category_delta"].items():
        assert computed[category_id] == pytest.approx(expected), category_id


def test_the_useful_output_is_which_checks_we_fail_that_they_pass() -> None:
    ours = measurement(
        "us",
        "우리 사이트",
        categories=(category("crawl_indexability", 60.0),),
        checks={
            "seo.http.status_ok": CheckStatus.PASS,
            "seo.robots.txt_allows_url": CheckStatus.FAIL,
            "seo.onpage.title_present_and_unique": CheckStatus.PASS,
        },
    )
    theirs = measurement(
        "rival",
        "경쟁사 A",
        categories=(category("crawl_indexability", 90.0),),
        checks={
            "seo.http.status_ok": CheckStatus.PASS,
            "seo.robots.txt_allows_url": CheckStatus.PASS,
            "seo.onpage.title_present_and_unique": CheckStatus.FAIL,
        },
    )

    pair = compare(ours, [theirs]).pairs[0]

    assert [d.check_id for d in pair.we_fail_they_pass()] == ["seo.robots.txt_allows_url"]
    assert [d.check_id for d in pair.they_fail_we_pass()] == [
        "seo.onpage.title_present_and_unique"
    ]


def test_a_check_measured_on_only_one_side_is_not_a_gap_and_is_reported_as_such() -> None:
    ours = measurement(
        "us",
        "우리 사이트",
        checks={
            "seo.perf.lcp_lab": CheckStatus.UNKNOWN,
            "seo.http.status_ok": CheckStatus.PASS,
        },
    )
    theirs = measurement(
        "rival",
        "경쟁사 A",
        checks={
            "seo.perf.lcp_lab": CheckStatus.PASS,
            "seo.http.status_ok": CheckStatus.PASS,
        },
    )

    pair = compare(ours, [theirs]).pairs[0]
    lcp = next(d for d in pair.check_deltas if d.check_id == "seo.perf.lcp_lab")

    assert lcp.comparable is False
    assert lcp.verdict is CheckVerdict.NOT_COMPARABLE
    assert lcp not in pair.we_fail_they_pass()
    assert "seo.perf.lcp_lab" in [d.check_id for d in pair.not_comparable_checks()]


def test_the_shared_denominator_is_stated_and_a_mismatch_is_flagged() -> None:
    ours = measurement(
        "us",
        "우리 사이트",
        categories=(
            category(
                "crawl_indexability",
                80.0,
                scored=("seo.http.status_ok", "seo.robots.txt_allows_url"),
            ),
        ),
    )
    theirs = measurement(
        "rival",
        "경쟁사 A",
        categories=(category("crawl_indexability", 90.0, scored=("seo.http.status_ok",)),),
    )

    delta = compare(ours, [theirs]).pairs[0].categories[0]

    assert delta.shared_check_ids == ("seo.http.status_ok",)
    assert delta.our_only_scored_check_ids == ("seo.robots.txt_allows_url",)
    assert delta.denominators_match is False
    assert "분모" in delta.note_ko


def test_a_category_only_one_side_could_score_yields_no_delta() -> None:
    ours = measurement("us", "우리 사이트", categories=(category("structured_data", None),))
    theirs = measurement("rival", "경쟁사 A", categories=(category("structured_data", 80.0),))

    delta = compare(ours, [theirs]).pairs[0].categories[0]

    assert delta.delta is None
    assert delta.our_score is None
    assert delta.their_score == pytest.approx(80.0)


# --------------------------------------------------------------------------- #
# 2. Every blocking difference refuses, and says which field and why
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("spec_id", "veo.geo.readiness"),
        ("spec_version", "2.0.0"),
        ("spec_checksum", "f" * 64),
        ("collector_version", "veo-collector/2.0.0"),
        ("locale", "en-US"),
        ("device", "DESKTOP"),
        ("renderer", "NONE"),
        ("enabled_providers", ("google_psi", "gsc")),
        ("pages_examined", 200),
        ("measured_at", BASE_MEASURED_AT - timedelta(days=90)),
    ],
)
def test_each_blocking_difference_refuses_with_a_korean_explanation(
    field: str, value: object
) -> None:
    ours, theirs = pair_of(**{field: value})
    pair = compare(ours, [theirs]).pairs[0]

    assert pair.comparable is False
    assert pair.refusal_ko is not None
    assert field in [difference["field"] for difference in pair.blocking_differences]
    assert any(
        difference["explanation_ko"] for difference in pair.blocking_differences
    ), "설명 없는 거부는 숫자보다 나쁘다"


def test_a_refused_comparison_carries_no_deltas_at_all() -> None:
    ours, theirs = pair_of(spec_version="2.0.0")
    pair = compare(ours, [theirs]).pairs[0]

    assert pair.categories == ()
    assert pair.check_deltas == ()
    assert pair.overall_delta is None
    assert pair.confidence is None


def test_one_refused_competitor_does_not_take_the_comparable_ones_down_with_it() -> None:
    ours, good = pair_of()
    _, bad = pair_of(device="DESKTOP")
    bad = bad.with_key("rival-2", "경쟁사 B")

    result = compare(ours, [good, bad])

    assert [p.comparable for p in result.pairs] == [True, False]
    assert result.comparable_count == 1
    assert result.refused_count == 1


# --------------------------------------------------------------------------- #
# 3. The waiver: one thing only, and it stays in the report
# --------------------------------------------------------------------------- #


def test_scope_variance_blocks_by_default() -> None:
    ours, theirs = pair_of(pages_examined=200)
    assert compare(ours, [theirs]).pairs[0].comparable is False


def test_the_waiver_allows_the_comparison_and_still_reports_the_difference() -> None:
    ours, theirs = pair_of(pages_examined=200)
    pair = compare(ours, [theirs], allow_scope_variance=True).pairs[0]

    assert pair.comparable is True
    assert pair.waived_scope_variance is True
    waived_fields = [difference["field"] for difference in pair.waived_differences]
    assert "pages_examined" in waived_fields
    assert "감안" in pair.summary_ko or "표본" in pair.summary_ko


def test_the_waiver_cannot_wave_through_a_methodology_difference() -> None:
    ours, theirs = pair_of(spec_version="2.0.0", pages_examined=200)
    pair = compare(ours, [theirs], allow_scope_variance=True).pairs[0]

    assert pair.comparable is False
    assert "spec_version" in [d["field"] for d in pair.blocking_differences]


def test_asking_for_the_waiver_does_not_claim_a_waiver_that_was_never_used() -> None:
    """Requesting the exception is not the same as having taken it."""
    ours, theirs = pair_of(device="DESKTOP")  # same page count, different device
    pair = compare(ours, [theirs], allow_scope_variance=True).pairs[0]

    assert pair.comparable is False
    assert pair.waived_scope_variance is False
    assert pair.waived_differences == ()


def test_a_tolerated_scope_difference_is_reported_even_without_a_waiver() -> None:
    ours, theirs = pair_of(pages_examined=45)  # within the 3x tolerance
    pair = compare(ours, [theirs]).pairs[0]

    assert pair.comparable is True
    assert pair.waived_scope_variance is False
    assert "pages_examined" in [d["field"] for d in pair.tolerated_differences]


# --------------------------------------------------------------------------- #
# 4. Confidence follows the weakest side, and says so
# --------------------------------------------------------------------------- #


def test_confidence_follows_the_weakest_coverage() -> None:
    ours = measurement("us", "우리 사이트", coverage=0.9)
    theirs = measurement("rival", "경쟁사 A", coverage=0.9)
    assert compare(ours, [theirs]).pairs[0].confidence == pytest.approx(0.9)


def test_a_lopsided_pair_is_barely_a_comparison_and_says_so() -> None:
    ours = measurement("us", "우리 사이트", coverage=0.4)
    theirs = measurement("rival", "경쟁사 A", coverage=0.9)

    pair = compare(ours, [theirs]).pairs[0]

    # min(0.4, 0.9) * (1 - |0.4 - 0.9|) = 0.4 * 0.5
    assert pair.confidence == pytest.approx(0.2)
    assert "40%" in pair.confidence_basis_ko
    assert "90%" in pair.confidence_basis_ko
    assert pair.confidence_level_ko in {"낮음", "매우 낮음"}


def test_the_whole_comparison_takes_the_weakest_pair() -> None:
    ours = measurement("us", "우리 사이트", coverage=0.9)
    strong = measurement("rival-1", "경쟁사 A", coverage=0.9)
    weak = measurement("rival-2", "경쟁사 B", coverage=0.5)

    result = compare(ours, [strong, weak])

    assert result.confidence == pytest.approx(0.5 * (1 - 0.4))
    assert "경쟁사 B" in result.confidence_basis_ko


def test_a_comparison_with_nothing_comparable_has_no_confidence_and_no_number() -> None:
    ours, theirs = pair_of(device="DESKTOP")
    result = compare(ours, [theirs])

    assert result.confidence is None
    assert result.comparable_count == 0
    assert "비교할 수 있는" in result.summary_ko


# --------------------------------------------------------------------------- #
# Shape of the whole thing
# --------------------------------------------------------------------------- #


def test_the_comparison_names_the_set_it_was_computed_against() -> None:
    ours, first = pair_of()
    second = measurement("rival-2", "경쟁사 B")

    result = compare(ours, [first, second])

    assert [member.key for member in result.comparison_set] == ["rival", "rival-2"]
    assert [member.label_ko for member in result.comparison_set] == ["경쟁사 A", "경쟁사 B"]


def test_comparing_against_nobody_is_refused_rather_than_answered() -> None:
    ours = measurement("us", "우리 사이트")
    with pytest.raises(ValueError, match="비교 대상"):
        compare(ours, [])


def test_a_competitor_may_not_share_our_key() -> None:
    ours = measurement("us", "우리 사이트")
    clash = measurement("us", "이름만 다른 같은 키")
    with pytest.raises(ValueError, match="중복"):
        compare(ours, [clash])


def test_the_result_serialises_to_plain_data() -> None:
    ours, theirs = pair_of()
    document = compare(ours, [theirs]).as_dict()

    assert document["baseline"]["label_ko"] == "우리 사이트"
    assert document["pairs"][0]["competitor_label_ko"] == "경쟁사 A"
    assert document["baseline"]["conditions"]["device"] == "MOBILE"
