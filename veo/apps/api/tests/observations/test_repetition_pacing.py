"""반복을 **연달아 던지지 않는다** — 그리고 못 벌렸으면 그렇게 적는다.

## 무엇이 틀려 있었나

관측 실행기는 한 번 시작하면 반복을 연달아 던졌다. 3회를 몇 초 안에 다 물었다.

그것이 왜 문제인가: **같은 순간에 던진 3회는 서로 독립적인 표본이 아니다.** 그 시각에
그 모델이 어떤 상태였는지, 검색 색인이 무엇을 들고 있었는지가 세 번에 똑같이 묻어난다.
사실상 한 번 본 것을 세 번 센 것에 가깝다. 그런데 Wilson 신뢰구간은 셋이 독립이라고
가정하고 계산되므로 **구간이 실제보다 좁게 나온다.**

좁은 구간이 넓은 구간보다 나쁘다. 더 확신에 차 보이기 때문이다. 그 좁은 구간을 옆에
놓고 경쟁사와 순위를 매기면, 잡음에서 순위를 지어낸 것이 된다(0-C).

기초자료(`GEO_PROMPT_SAMPLING_AND_CONFIDENCE.md`)가 요구하는 것은 "모든 반복은 같은 날
한꺼번에 몰지 말고 시간대를 분산" 이다.

## 여기서 고정하는 것

1. 같은 질문의 반복 사이에 실제로 간격이 든다
2. **다른 질문**은 그 대기에 갇히지 않는다 — 갇히면 실행 시간이 질문 수만큼 곱해진다
3. 간격을 두어도 **측정을 잃지 않는다** — 남은 회차가 조용히 건너뛰기로 넘어가면 안 된다
4. 못 벌렸으면 비율 옆에 "독립 표본이 아니다" 가 붙는다
5. 벌렸어도 캐비엇은 사라지지 않는다 — 한 실행 안에서 벌린 것은 시간대 분산이 아니다
"""

from __future__ import annotations

import threading
from datetime import UTC, datetime, timedelta

import httpx
import pytest

from veo.observations.attribution import DisambiguatingMentionDetector
from veo.observations.metrics import AnswerFact, visibility_metrics
from veo.observations.providers.registry import ProviderRegistry
from veo.observations.providers.storage import InMemoryAnswerStore
from veo.observations.runner import ObservationRunner
from veo.observations.sampling import MIN_SPREAD_BETWEEN_REPETITIONS, RepetitionSpread

from .providers.synthetic import (
    BRAND_PROFILE,
    SYNTHETIC_PRICES,
    balanced_prompt_set,
    conditions,
    openai_payload,
)

START = datetime(2026, 7, 31, 9, 0, tzinfo=UTC)


class FakeTime:
    """시계와 잠들기를 한 쌍으로 묶은 가짜.

    `sleep` 이 실제로 자지 않고 **시계를 앞으로 민다.** 그래야 2분 간격을 시험하는 데
    2분이 들지 않으면서도, 실행기가 보는 시간의 흐름은 진짜와 같아진다.
    """

    def __init__(self) -> None:
        self.now = START
        self.slept: list[float] = []
        self._lock = threading.Lock()

    def clock(self) -> datetime:
        with self._lock:
            # 호출 한 번마다 아주 조금 흐르게 둔다. 시간이 전혀 안 가면 "호출이 끝난
            # 시각" 과 "다음 호출을 던지는 시각" 이 같아져 현실과 달라진다.
            self.now += timedelta(milliseconds=1)
            return self.now

    def sleep(self, seconds: float) -> None:
        with self._lock:
            self.slept.append(seconds)
            self.now += timedelta(seconds=seconds)


def registry() -> ProviderRegistry:
    from pydantic import SecretStr

    from veo.core.settings import ProviderCredentials
    from veo.observations.providers.openai import OpenAIAnswerProvider

    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=openai_payload())

    return ProviderRegistry(
        [
            OpenAIAnswerProvider.from_settings(
                ProviderCredentials(openai_api_key=SecretStr("sk-synthetic-key-for-tests")),
                transport=httpx.MockTransport(handler),
                price_table=SYNTHETIC_PRICES,
            )
        ]
    )


def run_with(interval: timedelta, *, repetitions: int = 3) -> tuple[FakeTime, object]:
    fake = FakeTime()
    runner = ObservationRunner(
        registry=registry(),
        store=InMemoryAnswerStore(),
        detector=DisambiguatingMentionDetector(BRAND_PROFILE),
        max_concurrency=4,
        repetition_interval=interval,
        clock=fake.clock,
        sleep=fake.sleep,
    )
    report = runner.execute(
        balanced_prompt_set(),
        conditions={"OPENAI": conditions()},
        repetitions=repetitions,
    )
    return fake, report


class TestTheRepetitionsAreActuallySpacedOut:
    def test_the_same_question_is_not_asked_twice_in_a_row(self) -> None:
        _fake, report = run_with(timedelta(minutes=2))

        moments: dict[str, list[datetime]] = {}
        for run in report.runs:  # type: ignore[attr-defined]
            moments.setdefault(run.prompt_id, []).append(run.executed_at)

        spread = RepetitionSpread.of(moments)
        assert spread.shortest_gap is not None
        assert spread.shortest_gap >= timedelta(minutes=2)

    def test_it_waited_rather_than_pretending_to(self) -> None:
        """시계만 앞으로 밀고 실제로는 안 기다리면 배포에서 아무것도 안 바뀐다."""
        fake, _ = run_with(timedelta(minutes=2))

        assert fake.slept, "간격을 요구했는데 한 번도 기다리지 않았다"
        assert sum(fake.slept) >= 120

    def test_other_questions_are_not_stuck_behind_the_wait(self) -> None:
        """대기가 질문 수만큼 곱해지면 6문항 3회가 36분이 된다. 회차 사이에만 든다."""
        fake, _report = run_with(timedelta(minutes=2))

        # 반복 3회 → 회차 사이 대기는 2번. 여유를 크게 잡아도 6문항 x 2회분과는
        # 자릿수가 다르다.
        assert sum(fake.slept) < 2 * 120 + 60

    def test_zero_interval_keeps_the_old_behaviour(self) -> None:
        fake, _ = run_with(timedelta(0))

        assert fake.slept == []


class TestSpacingNeverCostsAMeasurement:
    def test_every_planned_run_still_happens(self) -> None:
        """간격을 두려다 남은 회차를 잃으면, 정직해지려다 측정을 버린 것이 된다."""
        _fake, report = run_with(timedelta(minutes=2))

        assert len(report.runs) == 6 * 3  # type: ignore[attr-defined]
        assert report.skipped == ()  # type: ignore[attr-defined]
        assert report.is_complete  # type: ignore[attr-defined]

    def test_the_same_is_true_without_spacing(self) -> None:
        _fake, report = run_with(timedelta(0))

        assert len(report.runs) == 6 * 3  # type: ignore[attr-defined]


class TestWhatTheNumberSaysAboutItself:
    def _facts(self, gap: timedelta) -> list[AnswerFact]:
        return [
            AnswerFact(
                prompt_id="q1",
                is_valid=True,
                mentioned=index % 2 == 0,
                cited=False,
                citation_support="STRUCTURED",
                executed_at=START + gap * index,
            )
            for index in range(5)
        ]

    def test_back_to_back_repetitions_are_declared_not_independent(self) -> None:
        measured = visibility_metrics(
            self._facts(timedelta(seconds=3)), prompts_planned=1, run_is_complete=True
        )

        assert not measured.repetition_spread.is_spread_out
        assert any("독립적인 표본이 아닙니다" in line for line in measured.caveats_ko)
        # 비율 옆까지 따라가야 한다. 주의사항 문단만 보고 숫자를 읽는 사람은 없다.
        assert "실제보다 좁습니다" in measured.mention_rate.qualifier_ko
        assert "실제보다 좁습니다" in measured.citation_rate.qualifier_ko

    def test_spaced_out_repetitions_still_carry_a_caveat(self) -> None:
        """한 실행 안에서 벌린 것은 날짜·시간대가 다른 측정이 아니다."""
        measured = visibility_metrics(
            self._facts(timedelta(minutes=5)), prompts_planned=1, run_is_complete=True
        )

        assert measured.repetition_spread.is_spread_out
        assert any("독립적이지는 않습니다" in line for line in measured.caveats_ko)

    def test_a_single_run_has_nothing_to_say_about_spacing(self) -> None:
        """반복이 없으면 간격도 없다. 없는 경고를 지어내지 않는다."""
        measured = visibility_metrics(
            self._facts(timedelta(seconds=3))[:1], prompts_planned=1, run_is_complete=True
        )

        assert measured.repetition_spread.shortest_gap is None
        assert measured.repetition_spread.caveat_ko is None
        assert not any("독립" in line for line in measured.caveats_ko)

    def test_the_measured_gap_travels_in_the_payload(self) -> None:
        measured = visibility_metrics(
            self._facts(timedelta(seconds=30)), prompts_planned=1, run_is_complete=True
        )

        payload = measured.as_dict()["repetition_spread"]
        assert payload["shortest_gap_seconds"] == 30
        assert payload["measured_pairs"] == 4
        assert payload["is_spread_out"] is False


class TestTheOperatingFloorIsDeclaredNotHidden:
    def test_the_floor_is_a_named_value(self) -> None:
        """숫자가 코드 안에 박혀 있으면 왜 그 값인지 물을 자리가 없다."""
        assert timedelta(0) < MIN_SPREAD_BETWEEN_REPETITIONS

    def test_a_negative_interval_is_refused(self) -> None:
        with pytest.raises(ValueError, match="repetition_interval"):
            ObservationRunner(
                registry=registry(),
                store=InMemoryAnswerStore(),
                detector=DisambiguatingMentionDetector(BRAND_PROFILE),
                repetition_interval=timedelta(seconds=-1),
            )
