"""비율은 분자보다 분모에서 거짓말한다.

이 파일이 고정하는 것은 거의 전부 **무엇을 분모에서 빼는가**이다. 특히 인용률 —
엔진이 출처를 밝히지 않은 응답을 분모에 넣으면 인용률이 낮게 나오고, **그 낮은 값은
사이트 탓처럼 읽힌다.** 같은 부류의 결함을 어댑터 층에서 이미 한 번 고쳤다.
"""

from __future__ import annotations

import pytest

from veo.observations.metrics import (
    MIN_SAMPLE_FOR_A_RATE,
    AnswerFact,
    visibility_metrics,
    wilson_interval,
)


def _answer(
    *,
    prompt: str = "q1",
    valid: bool = True,
    mentioned: bool = False,
    cited: bool = False,
    support: str | None = "STRUCTURED",
) -> AnswerFact:
    return AnswerFact(
        prompt_id=prompt,
        is_valid=valid,
        mentioned=mentioned,
        cited=cited,
        citation_support=support,
    )


def _metrics(answers, *, complete: bool = True, planned: int = 3):
    return visibility_metrics(answers, prompts_planned=planned, run_is_complete=complete)


class TestTheCitationDenominator:
    def test_answers_without_visible_sources_leave_the_denominator(self) -> None:
        """출처를 밝히지 않은 응답은 "우리를 인용하지 않았다" 가 아니다."""
        answers = [
            _answer(prompt="q1", cited=True, mentioned=True, support="STRUCTURED"),
            _answer(prompt="q2", support="NOT_EXPOSED_BY_PROVIDER"),
            _answer(prompt="q3", support="NOT_EXPOSED_BY_PROVIDER"),
        ]

        result = _metrics(answers)

        assert result.citation_rate.denominator == 1
        assert result.citation_rate.numerator == 1

    def test_no_visible_sources_at_all_is_unmeasurable_not_zero(self) -> None:
        """0%와 측정 불가는 화면에서 정반대의 뜻이다. 앞은 사이트 탓, 뒤는 우리 탓이다."""
        answers = [_answer(prompt=f"q{n}", support="NOT_EXPOSED_BY_PROVIDER") for n in range(5)]

        result = _metrics(answers)

        assert result.citation_rate.value is None
        assert result.citation_rate.percent is None
        assert not result.citation_rate.is_reportable

    def test_that_case_says_what_to_check(self) -> None:
        """'측정 불가' 만 띄우면 고장으로 읽힌다."""
        answers = [_answer(prompt=f"q{n}", support="NOT_EXPOSED_BY_PROVIDER") for n in range(5)]

        result = _metrics(answers)

        assert "모델" in " ".join(result.caveats_ko)

    def test_a_missing_support_value_is_not_counted_as_visible(self) -> None:
        """기록되지 않은 것을 '볼 수 있었다' 로 접으면 다시 거짓 0 이 된다."""
        answers = [_answer(prompt=f"q{n}", support=None) for n in range(5)]

        result = _metrics(answers)

        assert result.citation_rate.denominator == 0


class TestTheMentionDenominator:
    def test_failed_executions_leave_the_denominator(self) -> None:
        """실행이 실패한 것은 언급이 없었던 것이 아니라 재지 못한 것이다."""
        answers = [
            _answer(prompt="q1", mentioned=True),
            _answer(prompt="q2", valid=False),
            _answer(prompt="q3", valid=False),
        ]

        result = _metrics(answers)

        assert result.mention_rate.denominator == 1
        assert result.mention_rate.value == 1.0

    def test_the_dropped_executions_are_explained(self) -> None:
        answers = [_answer(prompt="q1", mentioned=True), _answer(prompt="q2", valid=False)]

        result = _metrics(answers)

        assert any("응답을 받지 못" in note for note in result.caveats_ko)

    def test_nothing_valid_at_all_is_unmeasurable_not_zero(self) -> None:
        answers = [_answer(prompt=f"q{n}", valid=False) for n in range(4)]

        result = _metrics(answers)

        assert result.mention_rate.value is None
        assert result.mention_rate.denominator == 0


class TestThinSamples:
    def test_a_rate_below_the_floor_is_not_reportable(self) -> None:
        """한 번 본 것을 노출률이라고 부를 수 없다."""
        answers = [_answer(prompt="q1", mentioned=True)]

        result = _metrics(answers)

        assert result.mention_rate.value == 1.0
        assert not result.mention_rate.is_reportable
        assert str(MIN_SAMPLE_FOR_A_RATE) in result.mention_rate.note_ko

    def test_enough_samples_become_reportable(self) -> None:
        answers = [_answer(prompt=f"q{n}", mentioned=True) for n in range(MIN_SAMPLE_FOR_A_RATE)]

        result = _metrics(answers)

        assert result.mention_rate.is_reportable


class TestTheConfidenceInterval:
    def test_three_out_of_three_is_not_certainty(self) -> None:
        """정규 근사는 여기서 '100%, 오차 0' 을 준다. 세 번 본 것으로 확신을 주장하게 된다."""
        low, high = wilson_interval(3, 3)

        assert low < 1.0
        assert high == pytest.approx(1.0, abs=0.001)

    def test_zero_out_of_three_is_not_certainty_either(self) -> None:
        low, high = wilson_interval(0, 3)

        assert low == pytest.approx(0.0, abs=0.001)
        assert high > 0.0

    def test_more_samples_narrow_the_interval(self) -> None:
        narrow_low, narrow_high = wilson_interval(50, 100)
        wide_low, wide_high = wilson_interval(5, 10)

        assert (narrow_high - narrow_low) < (wide_high - wide_low)

    def test_an_empty_sample_has_no_interval_to_speak_of(self) -> None:
        assert wilson_interval(0, 0) == (0.0, 0.0)


class TestPartialRuns:
    def test_an_incomplete_run_is_flagged(self) -> None:
        """계획의 일부만 던진 실행의 비율은 계획 전체에 대한 답이 아니다."""
        answers = [_answer(prompt=f"q{n}", mentioned=True) for n in range(3)]

        result = _metrics(answers, complete=False)

        assert result.is_partial_measurement
        assert any("계획한 실행" in note for note in result.caveats_ko)

    def test_a_complete_run_carries_no_partial_caveat(self) -> None:
        answers = [_answer(prompt=f"q{n}", mentioned=True) for n in range(3)]

        result = _metrics(answers, complete=True)

        assert not result.is_partial_measurement
        assert not any("계획한 실행" in note for note in result.caveats_ko)


class TestPromptCoverage:
    def test_it_counts_prompts_not_answers(self) -> None:
        """한 질문을 세 번 물어 세 번 언급됐다고 질문 셋을 덮은 것이 아니다."""
        answers = [
            _answer(prompt="q1", mentioned=True),
            _answer(prompt="q1", mentioned=True),
            _answer(prompt="q1", mentioned=True),
            _answer(prompt="q2"),
            _answer(prompt="q3"),
        ]

        result = _metrics(answers)

        assert result.prompt_coverage.numerator == 1
        assert result.prompt_coverage.denominator == 3


class TestTheShapeOfTheAnswer:
    def test_a_rate_carries_its_denominator(self) -> None:
        """0.0 만 돌려주면 '한 번도 안 됐다' 와 '잴 수 없었다' 가 같은 모양이 된다."""
        answers = [_answer(prompt=f"q{n}") for n in range(3)]

        payload = _metrics(answers).mention_rate.as_dict()

        assert payload["denominator"] == 3
        assert payload["value"] == 0.0
        assert payload["low"] is not None

    def test_the_counts_are_reported_beside_the_rates(self) -> None:
        answers = [
            _answer(prompt="q1", mentioned=True),
            _answer(prompt="q2", valid=False),
            _answer(prompt="q3", support="NOT_EXPOSED_BY_PROVIDER"),
        ]

        result = _metrics(answers)

        assert result.answers_recorded == 3
        assert result.answers_valid == 2
        assert result.answers_with_visible_citations == 1
