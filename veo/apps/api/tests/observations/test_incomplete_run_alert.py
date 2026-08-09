"""덜 잰 정기 관측을 **사람에게 알린다.**

## 왜 이 시험이 있나

관측은 이 제품에서 **유일하게 호출마다 돈이 나가는 축**이다(질문 1개 1회 854원).
실패는 이미 저장된다 — `stopped_reason` · `executions_skipped` · `skipped_detail`.
화면도 보여 준다. **그런데 아무도 그 화면을 보고 있지 않다.** 주 1회 자동으로 도는
측정이라(`observation-engine.md` §9) 사람이 그 시각에 앉아 있을 이유가 없다.

조용히 이렇게 될 수 있다 — 엔진 하나의 열쇠가 만료된다 → 그 엔진 몫이 전부 건너뛰어
진다 → 나머지로 비율이 나온다 → 화면은 정상으로 보이고 청구서만 계속 나온다.

`metrics.py` 가 분모를 지키므로 **숫자가 거짓이 되지는 않는다.** 다만 사람이 알기
전까지는 계속 돈만 나간다.
"""

from __future__ import annotations

import pathlib

import pytest

pytest.importorskip("pydantic")

from veo.notify import AlertOutcome
from veo.observations.alerts import ObservationRunFacts, alert_if_incomplete


def facts(**overrides: object) -> ObservationRunFacts:
    base: dict[str, object] = {
        "kind": "SCHEDULED",
        "project_name": "참사랑한의원",
        "prompt_set_name": "핵심 질문",
        "executions_planned": 150,
        "executions_valid": 120,
        "executions_skipped": 30,
        "stopped_reason": None,
        "cost_usd": 12.5,
        "unpriced_calls": 0,
    }
    base.update(overrides)
    return ObservationRunFacts(**base)  # type: ignore[arg-type]


class Recorder:
    def __init__(self, outcome: AlertOutcome = AlertOutcome.SENT) -> None:
        self.calls: list[dict[str, str]] = []
        self._outcome = outcome

    def __call__(self, *, title_ko: str, body_ko: str, source: str) -> AlertOutcome:
        self.calls.append({"title": title_ko, "body": body_ko, "source": source})
        return self._outcome


class TestItTellsWhenMoneyBoughtLessThanPlanned:
    def test_a_scheduled_run_that_skipped_executions_is_told(self) -> None:
        sender = Recorder()
        alert_if_incomplete(facts(), sender=sender)

        assert len(sender.calls) == 1
        assert "참사랑한의원" in sender.calls[0]["title"]

    def test_the_body_carries_the_denominator(self) -> None:
        """"덜 쟀다" 만으로는 사람이 판단하지 못한다. **얼마나** 덜 쟀는지가 있어야 한다."""
        sender = Recorder()
        alert_if_incomplete(facts(), sender=sender)

        body = sender.calls[0]["body"]
        assert "150" in body and "120" in body and "30" in body

    def test_a_stop_reason_is_carried_when_there_is_one(self) -> None:
        sender = Recorder()
        alert_if_incomplete(facts(stopped_reason="BUDGET_EXHAUSTED"), sender=sender)

        assert "BUDGET_EXHAUSTED" in sender.calls[0]["body"]

    def test_it_names_its_source(self) -> None:
        """수신 채널에서 알림이 섞일 때 출처 없이는 어느 코드가 보냈는지 못 찾는다."""
        sender = Recorder()
        alert_if_incomplete(facts(), sender=sender)

        assert sender.calls[0]["source"] == "observations.incomplete_run"


class TestItStaysQuietWhenThereIsNothingToActOn:
    def test_a_complete_run_is_not_told(self) -> None:
        """잘 된 것까지 알리면 채널이 시끄러워지고, 시끄러운 채널은 꺼진다."""
        sender = Recorder()
        outcome = alert_if_incomplete(
            facts(executions_valid=150, executions_skipped=0), sender=sender
        )

        assert sender.calls == []
        assert outcome is AlertOutcome.DISABLED

    def test_a_manual_run_is_not_told(self) -> None:
        """사람이 그 자리에서 단추를 누르고 결과를 보고 있다."""
        sender = Recorder()
        alert_if_incomplete(facts(kind="MANUAL"), sender=sender)

        assert sender.calls == []

    def test_a_run_that_spent_nothing_is_not_told(self) -> None:
        """아무 호출도 못 하고 끝난 것은 잃은 것이 없다 — 작업 실패로 이미 보인다."""
        sender = Recorder()
        alert_if_incomplete(facts(cost_usd=0.0, unpriced_calls=0), sender=sender)

        assert sender.calls == []

    def test_unpriced_calls_count_as_spending(self) -> None:
        """금액을 못 잰 호출도 **돈은 나갔다.** 0 원이라는 뜻이 아니라 모른다는 뜻이다."""
        sender = Recorder()
        alert_if_incomplete(facts(cost_usd=0.0, unpriced_calls=4), sender=sender)

        assert len(sender.calls) == 1
        assert "4회" in sender.calls[0]["body"]
        assert "모른다는 뜻" in sender.calls[0]["body"]


class TestTheAlertNeverBreaksTheMeasurement:
    def test_a_throwing_sender_does_not_escape(self) -> None:
        """잰 값은 이미 저장됐다. 알림을 못 보낸 것이 측정을 실패로 만들면 안 된다."""

        def boom(*, title_ko: str, body_ko: str, source: str) -> AlertOutcome:
            raise RuntimeError("webhook down")

        assert alert_if_incomplete(facts(), sender=boom) is AlertOutcome.FAILED

    def test_no_webhook_configured_is_not_an_error(self) -> None:
        """웹훅 주소가 없는 배포에서도 관측은 그대로 돈다."""
        sender = Recorder(AlertOutcome.DISABLED)

        assert alert_if_incomplete(facts(), sender=sender) is AlertOutcome.DISABLED


class TestTheAmountIsNotRounded:
    def test_the_cost_goes_out_as_measured(self) -> None:
        """사장님 지시 2026-08-09 — 모든 값 자르기. 여기서 반올림하면 청구서와 어긋난다."""
        sender = Recorder()
        alert_if_incomplete(facts(cost_usd=12.3456789), sender=sender)

        assert "12.3456789" in sender.calls[0]["body"]

    def test_the_module_never_rounds(self) -> None:
        from veo.observations import alerts

        source = pathlib.Path(alerts.__file__).read_text(encoding="utf-8")
        assert "round(" not in source


class TestItRunsAtTheEndOfEveryObservation:
    def test_persistence_calls_it(self) -> None:
        """붙여 두지 않으면 이 모듈은 아무도 부르지 않는 코드가 된다."""
        from veo.observations import execution

        source = pathlib.Path(execution.__file__).read_text(encoding="utf-8")
        assert "alert_if_incomplete(" in source

    def test_it_names_the_project_not_an_identifier(self) -> None:
        """UUID 조각을 받아 든 사람은 어느 거래처인지 몰라 콘솔을 뒤져야 한다."""
        from veo.observations import execution

        source = pathlib.Path(execution.__file__).read_text(encoding="utf-8")
        assert "_project_name_of(" in source
