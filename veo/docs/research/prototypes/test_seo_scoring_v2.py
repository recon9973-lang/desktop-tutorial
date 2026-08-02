"""v2 점수 알고리즘이 지켜야 하는 성질.

이 파일이 존재하는 이유는 **배점이 앞으로도 바뀔 것이기 때문**이다. 2026-08-01
구글 Lighthouse 대조로 CLS 를 위생에서 경쟁력으로 올렸고, 검사 두 개를 새로
넣었다. 그때 "합계가 여전히 100인가", "검사를 늘렸는데 점수가 올라가지는 않는가"
를 손으로 확인했는데, 손으로 확인한 것은 다음 사람이 물려받지 못한다.

v1 이 무너진 방식이 정확히 이것이었다. 명세 1.2.0 과 1.6.0 사이에 온페이지 검사가
9개에서 11개로 늘었고, **같은 결함을 가진 같은 사이트의 점수가 66.7 에서 72.7 로
올랐다.** 검사를 추가한 사람은 배점을 정확히 매겼고, 아무도 거짓말을 하지 않았다.
분모가 조용히 늘어났을 뿐이다. 그것을 잡는 시험이 없었다.

실행:  python3 -m pytest docs/research/prototypes/test_seo_scoring_v2.py -q
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

from seo_scoring_v2 import (  # noqa: E402
    ALLOCATION,
    STAGE_RAW_BUDGET,
    STAGES,
    CheckInput,
    score,
)

GATE_CHECKS = [c for c, (s, _, _) in ALLOCATION.items() if STAGES[s].get("is_gate")]
QUALITY_CHECKS = [c for c, (s, _, _) in ALLOCATION.items() if not STAGES[s].get("is_gate")]
ALL_CHECKS = list(ALLOCATION)


def every(status: str, **kw) -> list[CheckInput]:
    return [CheckInput(c, status, **kw) for c in ALL_CHECKS]


# --------------------------------------------------------------------------- #
# 1. 양 끝
# --------------------------------------------------------------------------- #


def test_a_site_that_passes_everything_scores_exactly_100() -> None:
    """만점이 100.0 이 아니면 그 알고리즘으로는 아무도 만점을 받을 수 없다."""
    assert score(every("PASS")).score == 100.0


def test_a_site_that_fails_everything_scores_exactly_0() -> None:
    assert score(every("FAIL")).score == 0.0


def test_a_site_nothing_could_be_measured_on_scores_0() -> None:
    """전부 UNKNOWN 은 0점이다. '못 쟀으니 만점' 은 거짓말이다(ADR 0016)."""
    assert score(every("UNKNOWN")).score == 0.0


# --------------------------------------------------------------------------- #
# 2. 게이트 — 검색에 없는 사이트가 '양호' 를 받지 않는다
# --------------------------------------------------------------------------- #


def test_a_fully_blocked_site_scores_0_however_good_the_rest_is() -> None:
    """v1 은 이 사이트에 74점을 줬다. 그것이 v2 가 존재하는 이유다.

    색인이 전면 차단된 페이지의 완벽한 구조화 데이터는 아무 일도 하지 않는다.
    """
    inputs = [
        CheckInput(c, "FAIL" if c in GATE_CHECKS else "PASS") for c in ALL_CHECKS
    ]
    assert score(inputs).score == 0.0


def test_robots_blocking_the_whole_site_alone_scores_0() -> None:
    """게이트는 하나만 전면 실패해도 0 이다. 관문은 전부 통과해야 한다."""
    inputs = [
        CheckInput(c, "FAIL" if c == "seo.robots.txt_allows_url" else "PASS")
        for c in ALL_CHECKS
    ]
    assert score(inputs).score == 0.0


def test_half_the_pages_blocked_costs_about_half_the_score() -> None:
    """게이트는 비율이다. 절반이 막히면 절반이 사라진다."""
    inputs = [
        CheckInput(c, "FAIL" if c == "seo.robots.meta_indexable" else "PASS",
                   coverage_ratio=0.5 if c == "seo.robots.meta_indexable" else 1.0)
        for c in ALL_CHECKS
    ]
    assert score(inputs).score == pytest.approx(50.0, abs=0.01)


def test_an_unmeasured_gate_does_not_invent_a_blockage() -> None:
    """못 잰 차단은 없는 차단이다(0-A).

    구글은 이것을 반대로 한다 — 2026-08-01 실측에서 robots.txt fetch 타임아웃이
    0점 실패로 기록됐고, 화면에서 '크롤러를 막고 있음' 과 구분되지 않았다.
    같은 사이트가 잴 때마다 SEO 1.00 과 0.92 를 오갔다. 우리가 같은 짓을 하면
    아무 문제 없는 병원 홈페이지가 우리 쪽 네트워크 사정으로 0점을 받는다.
    """
    inputs = [
        CheckInput(c, "UNKNOWN" if c == "seo.robots.txt_allows_url" else "PASS")
        for c in ALL_CHECKS
    ]
    result = score(inputs)
    assert result.score == 100.0
    assert result.gate_unverified == ["seo.robots.txt_allows_url"]


# --------------------------------------------------------------------------- #
# 3. 분모가 움직이지 않는다 — v1 이 죽은 자리
# --------------------------------------------------------------------------- #


def test_the_allocation_of_every_stage_sums_to_its_fixed_budget() -> None:
    """**이 시험이 v1 의 결함을 막는 자물쇠다.**

    v1 은 검사를 추가할 때마다 분모가 자라서, 같은 사이트의 같은 결함이 점점 싸졌다
    (1.2.0 에서 66.7 → 1.6.0 에서 72.7). v2 는 단계 예산을 고정해 그 피해를 단계
    안으로 가뒀지만, 단계 **안에서는** 같은 일이 계속 일어났다 — 검사를 하나 넣으면
    `scale = budget/declared` 가 조용히 기존 실패를 깎아 줬다(90.97 → 91.42).

    그래서 원배점 총합을 상수로 못 박는다. 이제 검사를 추가하려면 형제 검사에서
    덜어내야 하고, **무엇을 덜어낼지가 근거를 대야 하는 판단으로 드러난다.**
    나눗셈이 대신 결정해 주지 않는다.
    """
    for stage, expected in STAGE_RAW_BUDGET.items():
        actual = sum(p for _, (s, p, _) in ALLOCATION.items() if s == stage)
        assert actual == pytest.approx(expected, abs=1e-9), (
            f"{stage} 의 배점 합이 {actual} 다. 고정값은 {expected} 이고, 검사를 "
            f"추가했다면 형제 검사에서 그만큼 덜어내야 한다."
        )


def test_adding_a_check_a_site_passes_does_not_raise_its_score() -> None:
    """v1 의 결함을 정면으로 겨눈 시험.

    측정 범위를 넓혔다는 이유로 사이트의 점수가 올라가서는 안 된다. 사이트는
    변하지 않았기 때문이다.

    위 `test_the_allocation_of_every_stage_sums_to_its_fixed_budget` 가 지켜지는
    한, 검사를 추가하는 사람은 형제 배점을 함께 조정하게 되고 그 조정은 diff 에
    남는다. 이 시험은 그 조정이 실제로 이뤄졌는지를 **행동**으로 확인한다 —
    빠진 검사를 그 단계의 남은 검사들에 비례 배분한 것과 같은 점수가 나와야 한다.
    """
    failing = "seo.onpage.title_present_and_unique"
    dropped = "seo.onpage.heading_hierarchy"
    subset = [c for c in ALL_CHECKS if c != dropped]

    before = score([CheckInput(c, "FAIL" if c == failing else "PASS") for c in subset])
    after = score([CheckInput(c, "FAIL" if c == failing else "PASS") for c in ALL_CHECKS])

    # 검사를 뺀 쪽이 더 후해서는 안 된다. 적게 재고 좋은 점수를 받을 수 없다.
    assert before.score <= after.score + 0.01

    # 그리고 그 차이는 뺀 검사가 그 단계에서 차지하던 몫을 넘지 않는다.
    stage = ALLOCATION[dropped][0]
    share = ALLOCATION[dropped][1] / STAGE_RAW_BUDGET[stage] * STAGES[stage]["points"]
    assert after.score - before.score <= share + 0.01


def test_removing_a_check_a_site_fails_does_not_raise_its_score() -> None:
    """반대 방향도 막는다. 잰 항목을 줄여 점수를 올릴 수 없어야 한다."""
    subset = [c for c in ALL_CHECKS if c != "seo.onpage.heading_hierarchy"]
    full = score([CheckInput(c, "FAIL") for c in ALL_CHECKS])
    part = score([CheckInput(c, "FAIL") for c in subset])
    assert part.score <= full.score + 0.01


def test_a_stage_budget_is_not_diluted_by_the_number_of_checks_in_it() -> None:
    """단계 예산은 고정이고 단계 안에서만 재분배된다."""
    hygiene = [c for c, (s, _, _) in ALLOCATION.items() if s == "S6_HYGIENE"]
    inputs = [CheckInput(c, "FAIL" if c in hygiene else "PASS") for c in ALL_CHECKS]
    result = score(inputs)
    assert result.score == pytest.approx(100.0 - STAGES["S6_HYGIENE"]["points"], abs=0.01)


# --------------------------------------------------------------------------- #
# 4. 단조성 — 나빠지면 점수가 내려간다
# --------------------------------------------------------------------------- #


def test_a_warning_costs_less_than_a_failure() -> None:
    check = "seo.onpage.title_present_and_unique"
    warn = score([CheckInput(c, "WARNING" if c == check else "PASS") for c in ALL_CHECKS])
    fail = score([CheckInput(c, "FAIL" if c == check else "PASS") for c in ALL_CHECKS])
    assert 100.0 > warn.score > fail.score


def test_a_defect_on_more_pages_costs_more() -> None:
    check = "seo.onpage.title_present_and_unique"

    def at(ratio: float) -> float:
        return score([
            CheckInput(c, "FAIL" if c == check else "PASS",
                       coverage_ratio=ratio if c == check else 1.0)
            for c in ALL_CHECKS
        ]).score

    assert at(0.1) > at(0.5) > at(1.0)


def test_an_earlier_stage_costs_more_than_a_later_one() -> None:
    """같은 전면 실패라도 앞 단계가 더 아프다. 그것이 단계를 나눈 이유다."""
    meaning = score([
        CheckInput(c, "FAIL" if c == "seo.onpage.title_present_and_unique" else "PASS")
        for c in ALL_CHECKS
    ])
    hygiene = score([
        CheckInput(c, "FAIL" if c == "seo.html.doctype_standards_mode" else "PASS")
        for c in ALL_CHECKS
    ])
    assert meaning.score < hygiene.score


# --------------------------------------------------------------------------- #
# 5. 해당 없음 — 분모에서 빠지고, 남은 것으로 만점이 가능하다
# --------------------------------------------------------------------------- #


def test_not_applicable_checks_leave_the_denominator(
) -> None:
    """해당 없는 검사가 남아 있으면 그 사이트는 영원히 만점을 못 받는다(ADR 0002).

    구글도 같은 처리를 한다 — notApplicable 감사에는 weight 0 을 준다(실측).
    """
    inputs = [
        CheckInput(c, "NOT_APPLICABLE" if c.startswith("seo.sd.") else "PASS")
        for c in ALL_CHECKS
    ]
    assert score(inputs).score == 100.0


def test_an_all_na_stage_renormalises_instead_of_costing_its_weight() -> None:
    """이전 시험은 위생 단계만 살아남은 사이트가 7.1점이라고 못박았다 — 해당 없음이
    결함처럼 구는 산수였고, 실코드 평가기와도 어긋났다(§6). 1.9.0 이 재정규화를
    공식 규칙으로 발행하며 시험을 이름째 바꾼다(0-I): 살아 있는 단계 안에서 전부
    통과면 100점이다. 해당 없음은 잘못이 아니다."""
    hygiene = [c for c, (s, _, _) in ALLOCATION.items() if s == "S6_HYGIENE"]
    inputs = [
        CheckInput(c, "PASS" if c in hygiene or c in GATE_CHECKS else "NOT_APPLICABLE")
        for c in ALL_CHECKS
    ]
    assert score(inputs).score == pytest.approx(100.0, abs=0.01)


# --------------------------------------------------------------------------- #
# 6. 배점표 자체의 무결성
# --------------------------------------------------------------------------- #


def test_the_stage_budgets_sum_to_100() -> None:
    assert sum(m["points"] for m in STAGES.values()) == pytest.approx(100.0, abs=0.01)


def test_every_check_belongs_to_a_declared_stage() -> None:
    for check_id, (stage, _, _) in ALLOCATION.items():
        assert stage in STAGES, f"{check_id} 가 없는 단계 {stage} 를 가리킨다"


def test_every_check_carries_a_reason() -> None:
    """배점에는 이유가 붙는다. 이유 없는 숫자는 나중에 아무도 변호하지 못한다."""
    for check_id, (_, points, why) in ALLOCATION.items():
        assert points > 0, f"{check_id} 의 배점이 0 이다"
        assert why.strip(), f"{check_id} 에 배점 근거가 없다"


def test_no_check_is_allocated_twice() -> None:
    assert len(ALLOCATION) == len(set(ALLOCATION))


# --------------------------------------------------------------------------- #
# 7. 2026-08-01 구글 대조로 바꾼 것이 실제로 바뀌었는지
# --------------------------------------------------------------------------- #


def test_cls_is_scored_as_a_core_web_vital_not_as_hygiene() -> None:
    """구글은 CLS 에 LCP 와 동등한 25점을 준다(실측).

    위생에 두면 화면이 심하게 덜컹거려도 점수가 거의 안 깎인다. 광고 배너와 늦게
    뜨는 이미지로 버튼이 밀려나는 병원 홈페이지가 그대로 통과해서는 안 된다.
    """
    stage, points, _ = ALLOCATION["seo.perf.cls_lab"]
    assert stage == "S4_COMPETE"
    assert points >= 2.0

    def cost(check: str) -> float:
        return 100.0 - score([
            CheckInput(c, "FAIL" if c == check else "PASS") for c in ALL_CHECKS
        ]).score

    # LCP 보다는 싸고, 위생 항목보다는 확실히 비싸다.
    assert cost("seo.html.doctype_standards_mode") < cost("seo.perf.cls_lab")
    assert cost("seo.perf.cls_lab") < cost("seo.perf.lcp_lab")


def test_the_lab_proxy_costs_less_than_the_field_measurement_it_stands_in_for() -> None:
    """TBT 는 실험실이 INP 를 못 재서 쓰는 대역이다. 우리는 INP 를 직접 읽는다.

    구글이 TBT 에 성능 최대 배점(30)을 주는 것은 대역밖에 없어서다. 대역과 원본에
    둘 다 배점을 주면 같은 성질로 두 번 깎인다.
    """
    def cost(check: str) -> float:
        return 100.0 - score([
            CheckInput(c, "FAIL" if c == check else "PASS") for c in ALL_CHECKS
        ]).score

    assert cost("seo.perf.tbt_lab") < cost("seo.perf.inp_field")


def test_a_cause_costs_less_than_the_outcome_it_produces() -> None:
    """원인과 결과에 같은 배점을 주면 한 문제로 두 번 깎인다.

    구글은 원인 항목(render-blocking, unused-css, font-display …)에 배점 0 을 준다.
    VEO 는 조치가 구체적이라는 이유로 남기되, 결과보다 반드시 싸야 한다.
    """
    def cost(check: str) -> float:
        return 100.0 - score([
            CheckInput(c, "FAIL" if c == check else "PASS") for c in ALL_CHECKS
        ]).score

    assert cost("seo.crawl.crawlable_anchors") < cost("seo.crawl.no_orphan_key_pages")
    assert cost("seo.perf.text_compression") < cost("seo.perf.lcp_lab")
    assert cost("seo.perf.resource_hints") < cost("seo.perf.lcp_lab")


def test_charset_costs_more_than_doctype() -> None:
    """둘 다 위생이지만 실패의 크기가 다르다.

    doctype 이 없으면 렌더링 모드가 바뀔 뿐이고, charset 이 없으면 한글 본문이
    통째로 깨진 채 색인될 수 있다.
    """
    def cost(check: str) -> float:
        return 100.0 - score([
            CheckInput(c, "FAIL" if c == check else "PASS") for c in ALL_CHECKS
        ]).score

    assert cost("seo.html.charset_declared") > cost("seo.html.doctype_standards_mode")
