"""v3 (2단계 측정) 알고리즘이 지켜야 하는 성질.

v2 시험 파일이 존재하는 이유와 같다 — 손으로 확인한 것은 다음 사람이 물려받지
못한다. v3 이 더한 약속은 넷이고, 각각이 시험으로 고정된다.

1. 분해 항등식      100 − Σ손실 == overall_before_caps. 손실은 검사 단위로
                    귀속되고 scope(URL|SITE)가 붙는다. 도달률은 뺄셈 항이 아니다.
2. 페이지 점수      URL 범위만, 페이지 관문 실패 = ~0, SITE 검사는 오류로 거부.
3. 부재 주장        표본이 전체가 아니면 PASS 불가. 덜 재서 점수가 오르지 않는다.
4. 변화 대응        페이지 재크롤은 URL 판정만 갱신, SITE 값은 날짜를 달고 유지.
                    배점 재분할(검사 추가)이 무관한 페이지 점수를 흔들지 않는다.

그리고 무엇보다: **같은 입력이면 사이트 점수가 v2 와 동일하다.** v3 은 사이트
산식을 바꾸는 판이 아니라 회계(분해)와 하위 화면(페이지)을 다는 판이다.

실행:  .venv/bin/python -m pytest docs/research/prototypes/test_seo_scoring_v3_pages.py -q
"""

from __future__ import annotations

import random
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

import seo_scoring_v2 as v2  # noqa: E402
import seo_scoring_v3_pages as v3  # noqa: E402
from seo_scoring_v3_pages import (  # noqa: E402
    ABSENCE_CHECKS,
    NOT_SAMPLED_ALLOWED,
    PERF_FIELD_CHECKS,
    PERF_LAB_CHECKS,
    SPEC_1_8_0,
    CheckDef,
    CheckInput,
    SampleScope,
    SiteAudit,
    Spec,
    absence_claim,
    lab_sample_pages,
    page_panel,
    page_score,
    site_score,
)

ALL_CHECKS = list(SPEC_1_8_0.checks)
URL_CHECKS = [c for c in ALL_CHECKS if SPEC_1_8_0.checks[c].scope == "URL"]
SITE_CHECKS = [c for c in ALL_CHECKS if SPEC_1_8_0.checks[c].scope == "SITE"]
GATE_CHECKS = [c for c in ALL_CHECKS if SPEC_1_8_0.stages[SPEC_1_8_0.checks[c].stage].is_gate]


def every(status: str) -> list[CheckInput]:
    return [CheckInput(c, status) for c in ALL_CHECKS]


def page_inputs(
    overrides: dict[str, str] | None = None, *, in_perf_sample: bool = False
) -> list[CheckInput]:
    """페이지 하나의 기본 입력 — 전부 통과, 성능은 표본 정책대로.

    실사용자(inp_field)는 어느 페이지에도 붙지 않고(NOT_SAMPLED), 실험실 성능은
    표본에 든 페이지에서만 판정된다.
    """
    overrides = overrides or {}
    inputs = []
    for c in URL_CHECKS:
        status = overrides.get(c)
        if status is None:
            if c in PERF_FIELD_CHECKS:
                status = "NOT_SAMPLED"
            elif c in PERF_LAB_CHECKS:
                status = "PASS" if in_perf_sample else "NOT_SAMPLED"
            else:
                status = "PASS"
        inputs.append(CheckInput(c, status))
    return inputs


def random_site_inputs(seed: int) -> list[CheckInput]:
    rng = random.Random(seed)
    statuses = ["PASS", "PASS", "PASS", "WARNING", "FAIL", "UNKNOWN", "NOT_APPLICABLE"]
    return [
        CheckInput(
            c,
            rng.choice(statuses),
            coverage_ratio=rng.random(),
            confidence=rng.choice([1.0, 0.9, 0.8, 0.65]),
        )
        for c in ALL_CHECKS
    ]


# --------------------------------------------------------------------------- #
# 0. 배점표 무결성 — 숫자는 1.8.0 에서 왔고, v2 와 한 숫자도 다르지 않다
# --------------------------------------------------------------------------- #


def test_v3_tables_carry_exactly_the_v2_numbers() -> None:
    """v3 이 배점을 창작하지 않았음을 v2(=1.8.0 을 옮긴 선례)와 대조로 고정한다."""
    assert set(SPEC_1_8_0.checks) == set(v2.ALLOCATION)
    for check_id, (stage, points, _) in v2.ALLOCATION.items():
        d = SPEC_1_8_0.checks[check_id]
        assert d.stage == stage, check_id
        assert d.points == points, check_id
    for stage, meta in SPEC_1_8_0.stages.items():
        assert meta.points == v2.STAGES[stage]["points"], stage
        assert meta.raw_budget == v2.STAGE_RAW_BUDGET[stage], stage


def test_scopes_match_the_published_spec() -> None:
    """확정 사실과의 대조: 채점 검사 49개 = URL 32 + SITE 17,
    SITE 원배점 합 20.1, 성능(lab 6 + field 1) 원배점 합 8.3."""
    assert len(URL_CHECKS) == 32
    assert len(SITE_CHECKS) == 17
    site_raw = sum(SPEC_1_8_0.checks[c].points for c in SITE_CHECKS)
    assert site_raw == pytest.approx(20.1, abs=1e-9)
    perf_raw = sum(SPEC_1_8_0.checks[c].points for c in NOT_SAMPLED_ALLOWED)
    assert perf_raw == pytest.approx(8.3, abs=1e-9)


def test_page_stage_budgets_are_spec_constants() -> None:
    """페이지 점수의 고정분모 — 단계별 URL 배점 합. 명세가 정해지면 상수다."""
    expected = {
        "S1_BLOCKED": 30.0,
        "S2_IDENTITY": 11.0,
        "S3_MEANING": 16.0,
        "S4_COMPETE": 13.5,
        "S5_CLICK": 7.0,
        "S6_HYGIENE": 2.4,
    }
    for stage, budget in expected.items():
        assert SPEC_1_8_0.url_stage_budget(stage) == pytest.approx(budget, abs=1e-9)


# --------------------------------------------------------------------------- #
# 1. 사이트 점수는 v2 와 같은 수 — v3 은 산식을 바꾸지 않는다
# --------------------------------------------------------------------------- #


def test_the_site_score_equals_v2_on_the_same_inputs() -> None:
    """v2 의 24개 시험이 지키는 모든 성질은 이 동일성으로 v3 에 상속된다."""
    for seed in range(120):
        inputs = random_site_inputs(seed)
        ours = site_score(inputs)
        theirs = v2.score([
            v2.CheckInput(i.check_id, i.status, i.coverage_ratio, i.confidence)
            for i in inputs
        ])
        assert ours.score == theirs.score, f"seed={seed}"


def test_the_extremes_still_hold() -> None:
    assert site_score(every("PASS")).score == 100.0
    assert site_score(every("FAIL")).score == 0.0
    assert site_score(every("UNKNOWN")).score == 0.0


# --------------------------------------------------------------------------- #
# 2. 분해 — 항등식과 귀속
# --------------------------------------------------------------------------- #


def test_decomposition_identity_on_arbitrary_inputs() -> None:
    """**100 − Σ손실 == overall_before_caps.** 임의 판정 조합에서, 오차 1e-9.

    이 항등식이 있어야 "사이트 점수가 왜 이 숫자인가" 를 화면이 손실 목록만으로
    끝까지 설명할 수 있다. 목록에 없는 감점이 존재하면 사용자는 숫자를 검산할 수
    없고, 검산할 수 없는 점수는 신뢰를 만들지 못한다.
    """
    for seed in range(200):
        result = site_score(random_site_inputs(seed))
        explained = 100.0 - sum(loss.lost for loss in result.losses)
        assert explained == pytest.approx(result.quality, abs=1e-9), f"seed={seed}"
        # 손실은 전부 검사 단위이고 scope 가 붙는다 — URL/SITE 로 나눠 설명 가능.
        for loss in result.losses:
            assert loss.scope in {"URL", "SITE"}, loss.check_id


def test_reach_is_multiplication_not_a_loss_entry() -> None:
    """도달률은 뺄셈 항이 아니다. 절반 차단 = 손실 0건 + 도달률 0.5 + 50점.

    관문 실패를 손실 목록에 섞으면 항등식이 깨지거나(합이 안 맞거나) 이중으로
    깎인다. v2 가 관문을 곱셈으로 만든 이유가 분해에서도 유지되어야 한다.
    """
    inputs = [
        CheckInput(
            c,
            "FAIL" if c == "seo.robots.meta_indexable" else "PASS",
            coverage_ratio=0.5 if c == "seo.robots.meta_indexable" else 1.0,
        )
        for c in ALL_CHECKS
    ]
    result = site_score(inputs)
    assert result.losses == []
    assert result.quality == pytest.approx(100.0, abs=1e-9)
    assert result.reach == pytest.approx(0.5, abs=1e-9)
    assert result.score == pytest.approx(50.0, abs=0.01)
    assert [e.check_id for e in result.gate_events] == ["seo.robots.meta_indexable"]


def test_perfect_pages_with_a_lower_site_score_is_fully_explained() -> None:
    """페이지가 전부 100점인데 사이트 점수가 낮으면, 그 차이는 정확히
    SITE 손실 + 도달률이다 — 화면이 해야 하는 설명 그 자체.

    URL 검사가 전부 통과인 사이트에서는 손실 목록에 URL 항목이 있을 수 없고,
    사이트 점수는 도달률 × (100 − SITE손실합) 으로 재구성된다.
    """
    inputs = []
    for c in ALL_CHECKS:
        if c == "seo.robots.meta_indexable":
            inputs.append(CheckInput(c, "FAIL", coverage_ratio=0.3))
        elif c == "seo.onpage.no_duplicate_metadata":
            inputs.append(CheckInput(c, "FAIL", coverage_ratio=0.4))
        elif c == "seo.sd.declared":
            inputs.append(CheckInput(c, "FAIL"))
        else:
            inputs.append(CheckInput(c, "PASS"))
    site = site_score(inputs)

    # 하위 화면: 모든 페이지가 자기 URL 검사를 전부 통과한다 (관문 포함).
    page = page_score(page_inputs())
    assert page.score == 100.0

    assert site.score < 100.0
    assert site.url_loss_total == 0.0
    assert all(loss.scope == "SITE" for loss in site.losses)
    assert site.reach == pytest.approx(0.7, abs=1e-9)
    rebuilt = site.reach * (100.0 - site.site_loss_total)
    assert site.score == pytest.approx(rebuilt, abs=0.01)


# --------------------------------------------------------------------------- #
# 3. 페이지 점수
# --------------------------------------------------------------------------- #


def test_a_perfect_page_outside_the_perf_sample_scores_exactly_100() -> None:
    """표본 밖(NOT_SAMPLED)은 감점이 아니다 — 우리 정책으로 안 잰 것을 그 페이지의
    감점으로 돌리면 고객 탓이 된다(0-J)."""
    result = page_score(page_inputs())
    assert result.score == 100.0
    assert set(result.not_sampled) == PERF_LAB_CHECKS | PERF_FIELD_CHECKS
    assert result.unmeasured == []


def test_a_failed_page_gate_zeroes_that_page() -> None:
    """이 페이지의 robots meta·HTTP 상태가 실패하면 이 페이지는 검색에 존재하지
    않는다. 색인 단위는 페이지다(구글 how-search-works: "not every page that
    Google processes will be indexed")."""
    for gate in ("seo.http.status_ok", "seo.robots.meta_indexable"):
        result = page_score(page_inputs({gate: "FAIL"}))
        assert result.reach == 0.0
        assert result.score == 0.0


def test_an_unverified_page_gate_does_not_invent_a_blockage() -> None:
    """0-A 는 페이지에서도 그대로다 — 오늘 robots.txt 를 못 읽었다고 멀쩡한
    페이지를 0점으로 만들지 않는다. 구글 Lighthouse 가 하는 실수(fetch 타임아웃
    = 0점)를 페이지 단위에서도 반복하지 않는다."""
    result = page_score(page_inputs({"seo.robots.txt_allows_url": "UNKNOWN"}))
    assert result.score == 100.0
    assert result.gate_unverified == ["seo.robots.txt_allows_url"]


def test_the_page_identity_also_holds() -> None:
    """페이지 점수도 검산 가능해야 한다: quality == 100 − Σ손실, score == 도달률×quality."""
    result = page_score(page_inputs({
        "seo.onpage.title_present_and_unique": "FAIL",
        "seo.onpage.single_meaningful_h1": "WARNING",
        "seo.onpage.meta_description_quality": "UNKNOWN",
        "seo.onpage.image_alt_coverage": "NOT_APPLICABLE",
    }))
    assert result.quality == pytest.approx(
        100.0 - sum(loss.lost for loss in result.losses), abs=1e-9
    )
    assert result.score == pytest.approx(result.reach * result.quality, abs=0.01)
    assert all(loss.scope == "URL" for loss in result.losses)


def test_a_site_scope_check_on_a_page_is_an_error() -> None:
    """"본문 중복이 없다" 는 페이지 하나의 성질이 아니다. 조용히 무시하지 않고
    거부한다 — 분모가 다른 두 숫자를 같은 눈금처럼 보이게 하는 것이 우리가
    타사에서 잡아낸 바로 그 결함이다(methodology §2.9)."""
    with pytest.raises(ValueError):
        page_score(page_inputs() + [CheckInput("seo.onpage.no_duplicate_metadata", "PASS")])


def test_not_sampled_outside_the_sampling_policy_is_an_error() -> None:
    """NOT_SAMPLED 는 명세가 표본 정책을 선언한 검사(성능)에만 허용된다.
    아무 데나 붙으면 "안 재기로 했다" 가 절대평가(ADR 0016)를 비껴가는 뒷문이 된다."""
    with pytest.raises(ValueError):
        page_score(page_inputs({"seo.onpage.title_present_and_unique": "NOT_SAMPLED"}))
    with pytest.raises(ValueError):
        site_score([
            CheckInput(c, "NOT_SAMPLED" if c == "seo.perf.lcp_lab" else "PASS")
            for c in ALL_CHECKS
        ])


def test_unknown_on_a_page_keeps_the_denominator() -> None:
    """페이지에서도 세 상태는 다르다: 재려다 실패(UNKNOWN)는 배점을 잃고,
    해당 없음(N/A)과 표본 밖(NOT_SAMPLED)은 잃지 않는다."""
    unknown = page_score(page_inputs({"seo.onpage.image_alt_coverage": "UNKNOWN"}))
    n_a = page_score(page_inputs({"seo.onpage.image_alt_coverage": "NOT_APPLICABLE"}))
    assert n_a.score == 100.0
    assert unknown.score < 100.0
    assert "seo.onpage.image_alt_coverage" in unknown.unmeasured


# --------------------------------------------------------------------------- #
# 4. NOT_SAMPLED — 순위를 바꾸지 않는다 (동일 정책 동일 적용)
# --------------------------------------------------------------------------- #


def test_not_sampled_does_not_reorder_pages() -> None:
    """표본 밖 페이지들 사이의 순위는 측정된 검사만으로 정해진다. 표본 선정은
    명세 고정(중요도 상위)이라 재는 쪽이 표본을 골라 순위를 만들 수 없다."""
    worse = page_score(page_inputs({"seo.onpage.title_present_and_unique": "FAIL"}))
    better = page_score(page_inputs({"seo.onpage.heading_hierarchy": "FAIL"}))
    clean = page_score(page_inputs())
    assert worse.score < better.score < clean.score


def test_not_sampled_and_na_yield_the_same_number_with_different_labels() -> None:
    """NOT_SAMPLED 의 산술은 N/A 와 같다(분모 제외). 다른 것은 화면 문구뿐이다 —
    "이 페이지엔 없다" 와 "표본 밖 — 요청 시 측정" 은 다른 사실이다."""
    sampled_out = page_score(page_inputs({"seo.onpage.title_present_and_unique": "FAIL"}))
    as_na = page_score(page_inputs(
        {"seo.onpage.title_present_and_unique": "FAIL"}
        | {c: "NOT_APPLICABLE" for c in PERF_LAB_CHECKS | PERF_FIELD_CHECKS}
    ))
    assert sampled_out.score == as_na.score
    assert set(sampled_out.not_sampled) == PERF_LAB_CHECKS | PERF_FIELD_CHECKS
    assert sampled_out.not_applicable == []
    assert set(as_na.not_applicable) == PERF_LAB_CHECKS | PERF_FIELD_CHECKS


def test_an_in_sample_page_that_passes_perf_matches_an_out_of_sample_twin() -> None:
    """표본에 들었고 성능을 통과한 페이지와, 표본 밖이라 안 잰 쌍둥이 페이지는
    같은 점수다. 표본에 드는 것 자체가 유불리가 되면 안 된다."""
    inside = page_score(page_inputs(in_perf_sample=True))
    outside = page_score(page_inputs())
    assert inside.score == outside.score == 100.0


def test_the_lab_sample_is_fixed_by_importance_not_by_the_measurer() -> None:
    """표본 선정은 명세(url_importance 상위 5장)가 정하고 동률은 발견 순서다.
    같은 입력이면 같은 표본 — 조작할 자리가 없다."""
    pages = [("/a", 1.0), ("/b", 3.0), ("/c", 2.0), ("/d", 3.0),
             ("/e", 0.5), ("/f", 2.0), ("/g", 1.0)]
    assert lab_sample_pages(pages) == ["/b", "/d", "/c", "/f", "/a"]
    assert lab_sample_pages(pages) == lab_sample_pages(list(pages))


# --------------------------------------------------------------------------- #
# 5. 부재 주장 — 표본으로 존재는 증명되고 부재는 증명되지 않는다
# --------------------------------------------------------------------------- #


def test_an_absence_check_cannot_pass_on_a_partial_sample() -> None:
    """잘린 크롤(100장 상한)이 바로 이 판이 고치는 결함이다 — 다중 페이지라도
    전체가 아니면 "없다" 를 단정할 수 없다(0-A)."""
    truncated = SampleScope(crawl_is_exhaustive=False, page_count=100, declared_url_count=240)
    status, note = absence_claim(truncated, violations_found=0, subject_ko="중복 제목")
    assert status == "UNKNOWN"
    assert "100장" in note  # "본 N장 중에는 없었다" — 무엇을 봤는지 말한다

    # 존재는 표본으로도 증명된다.
    status, _ = absence_claim(truncated, violations_found=3, subject_ko="중복 제목")
    assert status == "FAIL"

    # 부재는 전체를 봤을 때만 증명된다.
    whole = SampleScope(crawl_is_exhaustive=True, page_count=100, declared_url_count=100)
    status, _ = absence_claim(whole, violations_found=0, subject_ko="중복 제목")
    assert status == "PASS"


def test_seeing_fewer_pages_never_raises_the_site_score() -> None:
    """1장 52.23 > 25장 50.11 — 실측으로 잡힌 유인이 다시 생기지 않는다.

    같은 사이트를 (전체 → 잘린 100장 → 1장) 으로 점점 덜 볼수록, 부재형·비교형
    검사가 PASS 에서 UNKNOWN 으로 바뀌고 UNKNOWN 은 배점을 잃으므로 점수는
    단조 비증가다.
    """
    def crawl(scope: SampleScope, single_page: bool) -> float:
        inputs = []
        for c in ALL_CHECKS:
            if c in ABSENCE_CHECKS:
                status, _ = absence_claim(scope, violations_found=0, subject_ko="결함")
            elif single_page and c == "seo.content.no_thin_signal":
                status = "UNKNOWN"  # 페이지 간 비교 검사 — 1장으로는 판단 불가
            else:
                status = "PASS"
            inputs.append(CheckInput(c, status))
        return site_score(inputs).score

    full = crawl(SampleScope(True, 120, 120), single_page=False)
    truncated = crawl(SampleScope(False, 100, 120), single_page=False)
    one_page = crawl(SampleScope(False, 1, 120), single_page=True)

    assert full == 100.0
    assert full > truncated >= one_page


# --------------------------------------------------------------------------- #
# 6. 변화 대응 — 부분 재크롤과 명세 개정
# --------------------------------------------------------------------------- #


def test_refreshing_one_page_updates_url_checks_and_dates_site_values() -> None:
    """페이지를 고친 뒤 그 페이지만 다시 재면: URL 판정은 갱신되고, SITE 판정은
    이전 전체 진단 값에 "YYYY-MM-DD 전체 진단 기준" 이 붙은 채 유지된다."""
    audit = SiteAudit(
        measured_on="2026-07-15",
        outcomes={c: CheckInput(c, "FAIL" if c in ABSENCE_CHECKS else "PASS")
                  for c in SITE_CHECKS},
    )

    before, _ = page_panel(page_inputs({"seo.onpage.title_present_and_unique": "FAIL"}), audit)
    after, context = page_panel(page_inputs(), audit)  # title 을 고치고 재측정

    assert after.score > before.score  # URL 판정은 즉시 갱신
    assert {v.check_id for v in context} <= set(SITE_CHECKS)
    for value in context:
        assert value.as_of == "2026-07-15"
        assert "2026-07-15 전체 진단 기준" in value.note_ko
        # 값 자체는 이전 진단 그대로다 — 페이지 재크롤이 SITE 판정을 만들지 않는다.
        assert value.status == audit.outcomes[value.check_id].status


def resplit_spec() -> Spec:
    """명세 개정 시뮬레이션 — S3(해석)에 URL 검사 하나를 신설하고, 고정분모
    원칙대로 형제(title 6→5)에서 배점을 덜어낸다. 단계 URL 배점 합 16 은 불변."""
    checks = dict(SPEC_1_8_0.checks)
    old = checks["seo.onpage.title_present_and_unique"]
    checks["seo.onpage.title_present_and_unique"] = CheckDef(old.stage, 5, old.scope, old.why)
    checks["seo.onpage.title_length_reasonable"] = CheckDef(
        "S3_MEANING", 1, "URL", "시험용 신설 검사"
    )
    return Spec(stages=SPEC_1_8_0.stages, checks=checks)


def test_adding_a_check_by_resplitting_leaves_unrelated_pages_unchanged() -> None:
    """검사 추가(같은 단계·같은 범위 안 배점 재분할)는 그 검사와 무관한 페이지의
    점수를 바꾸지 않는다. v1 을 죽인 결함(검사를 늘리면 분모가 자라 점수가 변함)이
    페이지 단위에서도 재발하지 않는다는 뜻이다."""
    variant = resplit_spec()
    assert variant.url_stage_budget("S3_MEANING") == pytest.approx(16.0, abs=1e-9)

    fails_h1 = {"seo.onpage.single_meaningful_h1": "FAIL"}
    before = page_score(page_inputs(fails_h1))
    after = page_score(
        page_inputs(fails_h1) + [CheckInput("seo.onpage.title_length_reasonable", "PASS")],
        spec=variant,
    )
    assert after.quality == pytest.approx(before.quality, abs=1e-9)
    assert after.score == before.score


def test_the_check_whose_points_moved_does_change() -> None:
    """위 시험이 공허하지 않다는 확인 — 배점이 실제로 옮겨진 검사(title)를
    실패하는 페이지는 재분할 후 손실이 6/16 에서 5/16 으로 줄어 점수가 달라진다."""
    variant = resplit_spec()
    fails_title = {"seo.onpage.title_present_and_unique": "FAIL"}
    before = page_score(page_inputs(fails_title))
    after = page_score(
        page_inputs(fails_title) + [CheckInput("seo.onpage.title_length_reasonable", "PASS")],
        spec=variant,
    )
    assert after.score > before.score
