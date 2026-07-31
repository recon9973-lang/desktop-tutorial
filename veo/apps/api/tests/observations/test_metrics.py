"""비율은 분자보다 분모에서 거짓말한다.

이 파일이 고정하는 것은 거의 전부 **무엇을 분모에서 빼는가**이다. 특히 인용률 —
엔진이 출처를 밝히지 않은 응답을 분모에 넣으면 인용률이 낮게 나오고, **그 낮은 값은
사이트 탓처럼 읽힌다.** 같은 부류의 결함을 어댑터 층에서 이미 한 번 고쳤다.

비율을 *만드는* 규칙(Wilson 구간, 표본 하한, 겹침 판정)은 여기서 다시 시험하지 않는다.
그것은 `veo.observations.sampling` 의 것이고 `test_sampling.py` 가 지킨다. 여기서는
**지표 계층이 그 규칙을 우회하지 않는지**만 본다 — 한 번 우회했었다.
"""

from __future__ import annotations

from veo.observations.metrics import AnswerFact, visibility_metrics
from veo.observations.sampling import (
    MIN_RUNS_FOR_COMPARISON,
    MIN_RUNS_FOR_EXPLORATION,
    SampleAdequacy,
)


def _answer(
    *,
    prompt: str = "q1",
    valid: bool = True,
    mentioned: bool = False,
    cited: bool = False,
    support: str | None = "STRUCTURED",
    engine: str = "OPENAI",
    intent: str = "",
    domains: tuple[str, ...] = (),
) -> AnswerFact:
    return AnswerFact(
        prompt_id=prompt,
        is_valid=valid,
        mentioned=mentioned,
        cited=cited,
        citation_support=support,
        engine=engine,
        intent=intent,
        cited_domains=domains,
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

        assert result.citation_rate.trials == 1
        assert result.citation_rate.successes == 1

    def test_no_visible_sources_at_all_is_unmeasurable_not_zero(self) -> None:
        """0%와 측정 불가는 화면에서 정반대의 뜻이다. 앞은 사이트 탓, 뒤는 우리 탓이다."""
        answers = [_answer(prompt=f"q{n}", support="NOT_EXPOSED_BY_PROVIDER") for n in range(5)]

        result = _metrics(answers)

        assert result.citation_rate.value is None
        assert result.citation_rate.adequacy is SampleAdequacy.NO_DATA
        assert "0%" not in result.citation_rate.percentage_text_ko

    def test_an_empty_citation_denominator_says_why_it_is_empty(self) -> None:
        """"관측 실행이 없습니다" 는 여기서 틀린 설명이다. 실행은 있었고, 출처가 없었다."""
        answers = [_answer(prompt=f"q{n}", support="NOT_EXPOSED_BY_PROVIDER") for n in range(5)]

        note = _metrics(answers).citation_rate.qualifier_ko

        assert "출처" in note
        assert "엔진이" in note

    def test_that_case_says_what_to_check(self) -> None:
        """'측정 불가' 만 띄우면 고장으로 읽힌다."""
        answers = [_answer(prompt=f"q{n}", support="NOT_EXPOSED_BY_PROVIDER") for n in range(5)]

        result = _metrics(answers)

        assert "모델" in " ".join(result.caveats_ko)

    def test_a_missing_support_value_is_not_counted_as_visible(self) -> None:
        """기록되지 않은 것을 '볼 수 있었다' 로 접으면 다시 거짓 0 이 된다."""
        answers = [_answer(prompt=f"q{n}", support=None) for n in range(5)]

        result = _metrics(answers)

        assert result.citation_rate.trials == 0


class TestTheMentionDenominator:
    def test_failed_executions_leave_the_denominator(self) -> None:
        """실행이 실패한 것은 언급이 없었던 것이 아니라 재지 못한 것이다.

        실패 2건을 분모에 넣으면 3/5 = 60% 가 되어 **사이트가 덜 노출된 것처럼**
        읽힌다. 실제로는 다섯 번 중 세 번만 잰 것이고, 잰 세 번은 전부 언급됐다.
        """
        answers = [
            _answer(prompt="q1", mentioned=True),
            _answer(prompt="q2", mentioned=True),
            _answer(prompt="q3", mentioned=True),
            _answer(prompt="q4", valid=False),
            _answer(prompt="q5", valid=False),
        ]

        result = _metrics(answers)

        assert result.mention_rate.trials == 3
        assert result.mention_rate.value == 1.0

    def test_the_dropped_executions_are_explained(self) -> None:
        answers = [_answer(prompt="q1", mentioned=True), _answer(prompt="q2", valid=False)]

        result = _metrics(answers)

        assert any("응답을 받지 못" in note for note in result.caveats_ko)

    def test_nothing_valid_at_all_is_unmeasurable_not_zero(self) -> None:
        answers = [_answer(prompt=f"q{n}", valid=False) for n in range(4)]

        result = _metrics(answers)

        assert result.mention_rate.value is None
        assert result.mention_rate.trials == 0
        assert result.mention_rate.adequacy is SampleAdequacy.NO_DATA


class TestThinSamples:
    """지표 계층이 `sampling` 의 표본 하한을 우회하지 않는지.

    한 번 우회했었다. 이 계층에 같은 계산을 다시 써 넣으면서 **1회 표본에도 퍼센트를
    내주고 경고만 붙이는** 쪽으로 느슨해졌다. 화면에 뜬 숫자는 읽히고 주석은 읽히지
    않으므로, 그것은 규칙을 지킨 것이 아니다.
    """

    def test_one_observation_yields_no_percentage_at_all(self) -> None:
        """한 번 본 것을 노출률이라고 부를 수 없다. 경고를 붙여 내보내는 것으로도 안 된다."""
        answers = [_answer(prompt="q1", mentioned=True)]

        rate = _metrics(answers).mention_rate

        assert rate.value is None
        assert rate.adequacy is SampleAdequacy.TOO_SMALL
        assert "100" not in rate.percentage_text_ko
        assert str(MIN_RUNS_FOR_EXPLORATION) in rate.qualifier_ko

    def test_the_exploration_floor_earns_a_direction_not_a_measurement(self) -> None:
        """3~5회 구간은 값을 주되 방향으로만 준다 — 소수점을 붙이지 않는다."""
        answers = [
            _answer(prompt=f"q{n}", mentioned=True) for n in range(MIN_RUNS_FOR_EXPLORATION)
        ]

        rate = _metrics(answers).mention_rate

        assert rate.value == 1.0
        assert rate.adequacy is SampleAdequacy.DIRECTIONAL
        assert "." not in rate.percentage_text_ko

    def test_the_exploration_floor_is_not_comparison_grade(self) -> None:
        """탐색으로는 충분해도 경쟁사 비교 보고에 실을 수는 없다 (방법론 5회)."""
        answers = [
            _answer(prompt=f"q{n}", mentioned=True) for n in range(MIN_RUNS_FOR_EXPLORATION)
        ]

        payload = _metrics(answers).as_dict()["mention_rate"]

        assert payload["is_comparison_grade"] is False

    def test_the_comparison_floor_is_comparison_grade(self) -> None:
        answers = [
            _answer(prompt=f"q{n}", mentioned=True) for n in range(MIN_RUNS_FOR_COMPARISON)
        ]

        result = _metrics(answers)

        assert result.mention_rate.adequacy is SampleAdequacy.ADEQUATE
        assert result.as_dict()["mention_rate"]["is_comparison_grade"] is True


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

        assert result.prompt_coverage.successes == 1
        assert result.prompt_coverage.trials == 3


class TestTheShapeOfTheAnswer:
    def test_a_rate_carries_its_denominator(self) -> None:
        """0.0 만 돌려주면 '한 번도 안 됐다' 와 '잴 수 없었다' 가 같은 모양이 된다."""
        answers = [_answer(prompt=f"q{n}") for n in range(3)]

        payload = _metrics(answers).as_dict()["mention_rate"]

        assert payload["denominator"] == 3
        assert payload["value"] == 0.0
        assert payload["low"] is not None

    def test_the_payload_hands_the_screen_a_safe_string_to_print(self) -> None:
        """화면이 `value` 를 직접 포맷하면 방향성 값에 소수점이 붙는다."""
        answers = [
            _answer(prompt=f"q{n}", mentioned=True) for n in range(MIN_RUNS_FOR_EXPLORATION)
        ]

        payload = _metrics(answers).as_dict()["mention_rate"]

        assert payload["percent_text_ko"] == "100%"
        assert payload["adequacy"] == "DIRECTIONAL"

    def test_every_rate_says_what_it_is(self) -> None:
        """분모 없는 퍼센트가 오해를 만드는 모양이다. 요약 한 줄에 분모가 들어 있다."""
        answers = [_answer(prompt=f"q{n}", mentioned=True) for n in range(5)]

        summary = _metrics(answers).as_dict()["mention_rate"]["summary_ko"]

        assert "언급률" in summary
        assert "5회 중 5회" in summary

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


class TestSourceDiversity:
    """엔진이 **몇 곳을** 인용하는가.

    우리가 인용됐는지와 다른 질문이고, 인용률을 읽는 방법을 바꾼다. 두 곳만 인용하는
    엔진에서의 20% 와 마흔 곳을 인용하는 엔진에서의 20% 는 같은 뜻이 아니다.
    """

    def test_it_counts_every_cited_domain_not_only_ours(self) -> None:
        answers = [
            _answer(prompt="q1", domains=("ondam.example", "blog.naver.com")),
            _answer(prompt="q2", domains=("ondam.example", "news.example")),
            _answer(prompt="q3", domains=("blog.naver.com",)),
        ]

        diversity = _metrics(answers).source_diversity

        assert diversity.distinct_domains == 3
        assert diversity.total_citations == 5
        assert diversity.top_domains[0] == ("blog.naver.com", 2)

    def test_a_narrow_source_set_says_so(self) -> None:
        """인용 자리가 좁다는 것은 그 자체로 알아야 할 사실이다."""
        answers = [_answer(prompt=f"q{index}", domains=("a.example",)) for index in range(3)]

        diversity = _metrics(answers).source_diversity

        assert diversity.caveat_ko is not None
        assert "1곳뿐" in diversity.caveat_ko

    def test_no_visible_citations_is_unmeasurable_not_zero(self) -> None:
        """0곳이 아니라 측정 불가다. 둘을 같게 그리면 우리가 못 잰 것이 사실이 된다."""
        answers = [
            _answer(prompt="q1", support="NOT_EXPOSED_BY_PROVIDER"),
            _answer(prompt="q2", support="NOT_EXPOSED_BY_PROVIDER"),
        ]

        diversity = _metrics(answers).source_diversity

        assert diversity.is_measurable is False
        assert diversity.caveat_ko is not None
        assert "측정 불가" in diversity.caveat_ko

    def test_a_failed_answer_contributes_no_sources(self) -> None:
        answers = [_answer(prompt="q1", valid=False, domains=("ghost.example",))]

        assert _metrics(answers).source_diversity.distinct_domains == 0


class TestStability:
    """같은 질문을 다시 물었을 때 답이 같았나.

    언급률 50% 는 두 가지 전혀 다른 사실일 수 있다. 절반의 질문이 늘 우리를 말했거나,
    모든 질문이 물을 때마다 뒤집혔거나. 고쳐야 할 것이 전혀 다르다.
    """

    def test_repeats_that_agree_are_consistent(self) -> None:
        answers = [
            _answer(prompt="q1", mentioned=True),
            _answer(prompt="q1", mentioned=True),
            _answer(prompt="q2", mentioned=False),
            _answer(prompt="q2", mentioned=False),
        ]

        stability = _metrics(answers).stability

        assert stability.repeated_groups == 2
        assert stability.consistent_groups == 2
        assert stability.unstable_groups == ()

    def test_a_flipping_prompt_is_named(self) -> None:
        answers = [
            _answer(prompt="q1", mentioned=True),
            _answer(prompt="q1", mentioned=False),
            _answer(prompt="q2", mentioned=True),
            _answer(prompt="q2", mentioned=True),
        ]

        stability = _metrics(answers).stability

        assert stability.unstable_groups == (("q1", "OPENAI"),)
        assert stability.consistent_groups == 1

    def test_engines_are_not_pooled(self) -> None:
        """한 엔진이 늘 말하고 다른 엔진이 한 번도 말하지 않으면, 합친 값은 두 사실을
        모두 지운다."""
        answers = [
            _answer(prompt="q1", engine="OPENAI", mentioned=True),
            _answer(prompt="q1", engine="OPENAI", mentioned=True),
            _answer(prompt="q1", engine="ANTHROPIC", mentioned=False),
            _answer(prompt="q1", engine="ANTHROPIC", mentioned=False),
        ]

        stability = _metrics(answers).stability

        assert stability.repeated_groups == 2
        assert stability.unstable_groups == ()

    def test_asking_once_is_not_stability(self) -> None:
        """한 번 물은 답은 흔들렸는지 알 수 없다. 안정적이라고 세지 않는다."""
        answers = [_answer(prompt="q1", mentioned=True), _answer(prompt="q2", mentioned=True)]

        stability = _metrics(answers).stability

        assert stability.repeated_groups == 0
        assert stability.is_measurable is False
        assert stability.rate.value is None

    def test_a_failed_answer_is_not_a_repetition(self) -> None:
        answers = [
            _answer(prompt="q1", mentioned=True),
            _answer(prompt="q1", valid=False),
        ]

        assert _metrics(answers).stability.repeated_groups == 0


class TestRecommendationPrompts:
    """추천을 묻는 질문에서의 언급률.

    이름 그대로여야 한다. "AI 가 우리를 추천했나" 가 아니다 — 그건 답변 문장을 읽어야
    알 수 있고, 이름만 그렇게 붙이면 재지 않은 것을 잰 것처럼 보고하게 된다.
    """

    def test_only_recommendation_prompts_are_counted(self) -> None:
        answers = [
            _answer(prompt="q1", intent="RECOMMENDATION", mentioned=True),
            _answer(prompt="q2", intent="RECOMMENDATION", mentioned=False),
            _answer(prompt="q3", intent="INFORMATIONAL", mentioned=True),
            _answer(prompt="q4", intent="INFORMATIONAL", mentioned=True),
        ]

        rate = _metrics(answers).recommendation_prompt_mention_rate

        assert rate.successes == 1
        assert rate.trials == 2

    def test_it_says_what_it_does_not_measure(self) -> None:
        answers = [_answer(prompt="q1", intent="RECOMMENDATION", mentioned=True)]

        rate = _metrics(answers).recommendation_prompt_mention_rate

        assert "추천했는지는" in rate.extra_qualifier_ko

    def test_no_recommendation_prompts_is_no_data(self) -> None:
        answers = [_answer(prompt="q1", intent="INFORMATIONAL", mentioned=True)]

        rate = _metrics(answers).recommendation_prompt_mention_rate

        assert rate.trials == 0
        assert rate.value is None
