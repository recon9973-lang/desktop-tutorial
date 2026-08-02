"""페이지 점수 — 명세 1.9.0 발행과 함께 실코드가 된 산식의 성질.

프로토타입(docs/research/prototypes/seo_scoring_v3_pages.py, 시험 24개)이 설계를
검증했고, 이 파일은 실코드 :func:`veo.scoring.page.evaluate_page` 가 **발행 명세
1.9.0 위에서** 같은 성질을 갖는지를 지킨다:

1. SITE 범위 검사는 오류다 — 분모가 다른 두 숫자가 같은 눈금처럼 보이면 안 된다.
2. NOT_SAMPLED 는 명세가 표본 정책을 선언한 검사에만 허용된다.
3. 항등식 — quality == 100 - Σ(losses.lost), score == reach x quality.
4. 재정규화 — 판정된 단계가 적은 페이지가 그 이유만으로 감점되지 않는다.
5. 표본 밖은 감점이 아니고, 재려다 실패한 것(UNKNOWN)은 감점이다.
"""

from __future__ import annotations

import pytest

from veo.scoring import CheckOutcome, CheckStatus, evaluate_page, latest_published
from veo.scoring.errors import ScoringSpecError


@pytest.fixture(scope="module")
def spec():  # type: ignore[no-untyped-def]
    return latest_published("veo.seo.readiness")


def url_checks(spec):  # type: ignore[no-untyped-def]
    return [
        check
        for category in spec.categories
        if category.contributes_to_score
        for check in category.checks
        if check.scope == "URL"
    ]


def outcome(check_id: str, status: CheckStatus) -> CheckOutcome:
    return CheckOutcome(
        check_id=check_id,
        status=status,
        confidence=1.0,
        evidence_ids=[f"ev::{check_id}"],
    )


def all_with(spec, overrides: dict[str, CheckStatus]) -> list[CheckOutcome]:  # type: ignore[no-untyped-def]
    return [
        outcome(check.id, overrides.get(check.id, CheckStatus.PASS))
        for check in url_checks(spec)
    ]


class TestTheBoundary:
    def test_a_site_scope_check_is_an_error_not_a_silent_skip(self, spec) -> None:  # type: ignore[no-untyped-def]
        site_check = next(
            check
            for category in spec.categories
            for check in category.checks
            if check.scope == "SITE"
        )
        with pytest.raises(ScoringSpecError, match="SITE"):
            evaluate_page(spec, [outcome(site_check.id, CheckStatus.PASS)])

    def test_not_sampled_outside_the_declared_list_is_an_error(self, spec) -> None:  # type: ignore[no-untyped-def]
        undeclared = next(
            check.id
            for check in url_checks(spec)
            if check.id not in spec.sampled_check_ids
        )
        with pytest.raises(ScoringSpecError, match="NOT_SAMPLED"):
            evaluate_page(spec, all_with(spec, {undeclared: CheckStatus.NOT_SAMPLED}))


class TestTheIdentity:
    def test_quality_is_100_minus_the_sum_of_losses(self, spec) -> None:  # type: ignore[no-untyped-def]
        """화면·고객이 숫자를 검산할 수 있어야 한다 — 손실 합이 곧 잃은 점수다."""
        broken = {
            "seo.onpage.single_meaningful_h1": CheckStatus.FAIL,
            "seo.onpage.meta_description_quality": CheckStatus.WARNING,
        }
        result = evaluate_page(spec, all_with(spec, broken))

        assert result.status == "SCORED"
        assert result.quality == pytest.approx(
            100.0 - sum(loss.lost for loss in result.losses), abs=1e-6
        )
        assert result.score == pytest.approx(result.reach * result.quality, abs=1e-6)

    def test_an_all_pass_page_scores_100(self, spec) -> None:  # type: ignore[no-untyped-def]
        result = evaluate_page(spec, all_with(spec, {}))
        assert result.score == 100.0
        assert result.reach == 1.0


class TestRenormalisation:
    def test_a_page_with_fewer_stages_is_not_punished_for_its_template(self, spec) -> None:  # type: ignore[no-untyped-def]
        """구조화 데이터가 원래 없는 안내 페이지 — 판정된 단계 안에서 전부 통과면 100."""
        two_categories = [c.id for c in spec.categories if c.contributes_to_score][:3]
        partial = [
            outcome(check.id, CheckStatus.PASS)
            for category in spec.categories
            if category.id in two_categories
            for check in category.checks
            if check.scope == "URL"
        ]
        result = evaluate_page(spec, partial)
        assert result.score == 100.0


class TestGates:
    def test_a_blocked_page_loses_by_multiplication(self, spec) -> None:  # type: ignore[no-untyped-def]
        gate_check = next(
            check
            for category in spec.categories
            if category.is_gate
            for check in category.checks
            if check.scope == "URL"
        )
        blocked = evaluate_page(spec, all_with(spec, {gate_check.id: CheckStatus.FAIL}))
        assert blocked.reach < 1.0
        assert blocked.score == pytest.approx(blocked.reach * blocked.quality, abs=1e-6)

    def test_an_unverified_gate_does_not_multiply(self, spec) -> None:  # type: ignore[no-untyped-def]
        """관측하지 않은 차단을 있다고 하면 없는 결함을 지어내는 것이다(0-A)."""
        gate_check = next(
            check
            for category in spec.categories
            if category.is_gate
            for check in category.checks
            if check.scope == "URL"
        )
        result = evaluate_page(spec, all_with(spec, {gate_check.id: CheckStatus.UNKNOWN}))
        assert result.reach == 1.0
        assert gate_check.id in result.gate_unverified


class TestNotSampledVsUnknown:
    def test_the_sampling_policy_costs_the_page_nothing(self, spec) -> None:  # type: ignore[no-untyped-def]
        """표본 밖 성능 7개 전부 — 감점 0, 별도 목록으로만 나온다."""
        skipped = dict.fromkeys(spec.sampled_check_ids, CheckStatus.NOT_SAMPLED)
        result = evaluate_page(spec, all_with(spec, skipped))
        assert result.score == 100.0
        assert sorted(result.not_sampled) == sorted(spec.sampled_check_ids)

    def test_a_measurement_failure_still_costs(self, spec) -> None:  # type: ignore[no-untyped-def]
        """같은 검사가 UNKNOWN(재려다 실패)이면 분모에 남아 점수를 깎는다."""
        failed_to_measure = dict.fromkeys(spec.sampled_check_ids, CheckStatus.UNKNOWN)
        result = evaluate_page(spec, all_with(spec, failed_to_measure))
        assert result.score is not None and result.score < 100.0
        assert sorted(result.unmeasured) == sorted(spec.sampled_check_ids)

    def test_nothing_but_policy_skips_reads_as_not_applicable(self, spec) -> None:  # type: ignore[no-untyped-def]
        skipped = [
            outcome(check_id, CheckStatus.NOT_SAMPLED)
            for check_id in spec.sampled_check_ids
        ]
        result = evaluate_page(spec, skipped)
        assert result.status == "NOT_APPLICABLE"
        assert result.score is None
