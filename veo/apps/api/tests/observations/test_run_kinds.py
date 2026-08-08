"""수동 측정은 추이에 못 들어간다 — 그것을 막는 것이 코드의 일이다.

수동 측정은 사람이 그 순간 고른 검색어를 잰 것이다. 조건(엔진·모델·검색모드)이 정기
측정과 **완전히 같아도** 서로 다른 측정이다. 고른 사람이 다르게 만든다:

    "경쟁 비교를 조작하는 데 숫자를 위조할 필요가 없다. 질문만 고르면 된다."
    (docs/adr/0015-prompt-sets-are-audited-artefacts.md:8)

여기 있는 시험은 전부 한 가지를 확인한다. 섞으려 하면 **거부되는가.** 주석으로
"섞지 마세요" 라고 적어 두는 것과, 섞으면 예외가 나는 것은 다르다.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from veo.observations.runs import (
    AccountState,
    MixedRunKindsError,
    ObservationRun,
    RunConditions,
    RunKind,
    SearchMode,
    aggregate_rate,
)

NOW = datetime(2026, 8, 8, 12, 0, tzinfo=UTC)

CONDITIONS = RunConditions(
    engine="OPENAI",
    model="gpt-5",
    model_version="2026-05-01",
    search_mode=SearchMode.BROWSING,
    account_state=AccountState.ANONYMOUS,
)


def run(*, kind: RunKind, mentioned: bool = True, tag: str = "a") -> ObservationRun:
    return ObservationRun(
        run_id=f"r-{kind}-{tag}-{mentioned}",
        prompt_id=f"p-{tag}",
        conditions=CONDITIONS,
        executed_at=NOW,
        kind=kind,
        raw_answer_ref="storage://answers/abc",
        raw_answer_hash="a" * 64,
        brand_mentioned=mentioned,
        brand_cited=False,
    )


def test_a_run_is_scheduled_unless_it_says_otherwise() -> None:
    """이 필드가 생기기 전의 모든 실행은 정기 측정이었다."""
    assert run(kind=RunKind.SCHEDULED).kind is RunKind.SCHEDULED
    assert ObservationRun(
        run_id="r1",
        prompt_id="p1",
        conditions=CONDITIONS,
        executed_at=NOW,
        raw_answer_ref=None,
        raw_answer_hash=None,
        brand_mentioned=False,
        brand_cited=False,
    ).kind is RunKind.SCHEDULED


def test_mixing_manual_and_scheduled_into_one_rate_is_refused() -> None:
    runs = [
        run(kind=RunKind.SCHEDULED, tag="1"),
        run(kind=RunKind.MANUAL, tag="2"),
    ]
    with pytest.raises(MixedRunKindsError) as caught:
        aggregate_rate(runs, label_ko="AI 노출률")

    assert "수동" in str(caught.value)


def test_the_refusal_has_no_override_flag_unlike_mixed_conditions() -> None:
    """조건 섞기에는 예외 통로가 있다. 이쪽에는 없다 — 있으면 켜질 것이기 때문이다."""
    runs = [
        run(kind=RunKind.SCHEDULED, tag="1"),
        run(kind=RunKind.MANUAL, tag="2"),
    ]
    with pytest.raises(MixedRunKindsError):
        aggregate_rate(runs, label_ko="AI 노출률", allow_mixed_conditions=True)


def test_a_manual_only_rate_is_allowed_but_says_it_cannot_be_a_trend_point() -> None:
    runs = [
        run(kind=RunKind.MANUAL, tag="1", mentioned=True),
        run(kind=RunKind.MANUAL, tag="2", mentioned=False),
    ]
    rate = aggregate_rate(runs, label_ko="이 검색어 노출")

    assert rate.successes == 1
    assert rate.trials == 2
    assert "추이" in (rate.extra_qualifier_ko or "")


def test_a_scheduled_only_rate_carries_no_manual_caveat() -> None:
    runs = [
        run(kind=RunKind.SCHEDULED, tag="1", mentioned=True),
        run(kind=RunKind.SCHEDULED, tag="2", mentioned=False),
    ]
    rate = aggregate_rate(runs, label_ko="AI 노출률")

    assert "수동" not in (rate.extra_qualifier_ko or "")


def test_failed_executions_do_not_drag_their_kind_into_the_check() -> None:
    """실패한 실행은 측정이 아니다 — 종류 검사보다 먼저 걸러진다."""
    runs = [
        run(kind=RunKind.SCHEDULED, tag="1"),
        ObservationRun(
            run_id="r-broken",
            prompt_id="p-broken",
            conditions=CONDITIONS,
            executed_at=NOW,
            kind=RunKind.MANUAL,
            raw_answer_ref=None,
            raw_answer_hash=None,
            brand_mentioned=False,
            brand_cited=False,
            error_code="TIMEOUT",
        ),
    ]
    rate = aggregate_rate(runs, label_ko="AI 노출률")
    assert rate.trials == 1


def test_the_kind_travels_in_the_serialised_run() -> None:
    assert run(kind=RunKind.MANUAL).as_dict()["kind"] == "MANUAL"
