"""같은 호스트에 몰아치지 않는다.

작업의뢰서 §5.2: 동일 호스트 **최소 1초 간격, 동시 연결 2 이하**.

2026-08-06 실측에서 우리는 동시 4로 간격 없이 돌고 있었다. venomad.com 131장을
**2.5초**에 받아 갔다 — 장당 0.019초, 그 서버 입장에서는 1초에 50번이다.

호스트 시간당 총량(`HostBudgetGuard`)과 **다른 것을 막는다** — 저것은 한 시간의 총량,
이것은 한순간의 밀도다. 총량만 있으면 450회를 1분에 몰아 쓸 수 있다.

시간을 진짜로 재우지 않는다. 시계와 잠자기를 주입해 **얼마나 재웠는지**를 본다 —
실제로 자면 시험이 느려지고, 느린 시험은 결국 안 돌린다.
"""

from __future__ import annotations

import threading

import pytest

from veo.common.security.pacing import HostPacer


class FakeClock:
    """수동으로 흐르는 시계. 잠들면 그만큼 시간이 간다."""

    def __init__(self) -> None:
        self.now = 1000.0
        self.slept: list[float] = []

    def sleep(self, seconds: float) -> None:
        self.slept.append(seconds)
        self.now += seconds


class TestTheIntervalIsKept:
    def test_the_first_request_to_a_host_does_not_wait(self) -> None:
        clock = FakeClock()
        pacer = HostPacer(min_interval_seconds=1.0, now=lambda: clock.now, sleep=clock.sleep)

        assert pacer.wait_for("a.example") == 0.0
        assert clock.slept == []

    def test_a_second_request_waits_the_remainder(self) -> None:
        """**이 시험이 규칙의 본체다.** 연달아 두드리면 그만큼 기다린다."""
        clock = FakeClock()
        pacer = HostPacer(min_interval_seconds=1.0, now=lambda: clock.now, sleep=clock.sleep)

        pacer.wait_for("a.example")
        clock.now += 0.2  # 0.2초 뒤에 또 부른다
        waited = pacer.wait_for("a.example")

        # 부동소수점이라 정확히 0.8 이 아니다(1001.0 - 1000.2 = 0.7999...).
        assert waited == pytest.approx(0.8)
        assert clock.slept == pytest.approx([0.8])

    def test_a_request_after_the_interval_does_not_wait(self) -> None:
        clock = FakeClock()
        pacer = HostPacer(min_interval_seconds=1.0, now=lambda: clock.now, sleep=clock.sleep)

        pacer.wait_for("a.example")
        clock.now += 5.0
        assert pacer.wait_for("a.example") == 0.0

    def test_another_host_is_not_made_to_wait(self) -> None:
        """간격은 **호스트별**이다. 한 사이트가 느리다고 다른 사이트를 늦추지 않는다."""
        clock = FakeClock()
        pacer = HostPacer(min_interval_seconds=1.0, now=lambda: clock.now, sleep=clock.sleep)

        pacer.wait_for("a.example")
        assert pacer.wait_for("b.example") == 0.0

    def test_zero_interval_disables_it(self) -> None:
        clock = FakeClock()
        pacer = HostPacer(min_interval_seconds=0.0, now=lambda: clock.now, sleep=clock.sleep)

        pacer.wait_for("a.example")
        assert pacer.wait_for("a.example") == 0.0
        assert clock.slept == []


class TestConcurrentCallersQueue:
    def test_threads_do_not_all_slip_through_together(self) -> None:
        """잠금이 없으면 여러 스레드가 같은 "마지막 시각" 을 보고 함께 통과한다 —
        그러면 간격이 없는 것과 같다. 콘솔 크롤은 실제로 여러 스레드가 돈다.

        실제로 재우면 시험이 느려지므로 잠자기는 삼킨다. 확인하는 것은 **자리 배정**이다:
        n 번째 호출은 (n-1) x 간격 만큼 뒤로 밀려야 한다.
        """
        pacer = HostPacer(min_interval_seconds=1.0, now=lambda: 1000.0, sleep=lambda _: None)
        waits: list[float] = []
        lock = threading.Lock()

        def call() -> None:
            waited = pacer.wait_for("a.example")
            with lock:
                waits.append(waited)

        threads = [threading.Thread(target=call) for _ in range(5)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        # 첫 호출 0초, 나머지는 1·2·3·4초 — 겹치는 값이 있으면 함께 빠져나간 것이다.
        assert sorted(waits) == pytest.approx([0.0, 1.0, 2.0, 3.0, 4.0])


class TestConnectionSlots:
    """자리 수는 §5.2 의 "동시 연결 2 이하" 다.

    자리를 하나만 두면 그 요구가 죽은 글자가 된다 — 요청이 전부 한 줄로 서므로
    설정을 1 로 두든 8 로 두든 결과가 같다(2026-08-06 실측: 30쪽 수집이 동시
    1·2·4·8 에서 전부 31.0초).
    """

    def test_the_first_requests_fill_the_slots_without_waiting(self) -> None:
        clock = FakeClock()
        pacer = HostPacer(
            min_interval_seconds=1.0, slots=2, now=lambda: clock.now, sleep=clock.sleep
        )

        assert pacer.wait_for("a.example") == 0.0
        assert pacer.wait_for("a.example") == 0.0
        assert clock.slept == []

    def test_the_request_after_the_slots_are_full_waits(self) -> None:
        """자리가 다 찼으면 가장 먼저 비는 자리를 기다린다."""
        clock = FakeClock()
        pacer = HostPacer(
            min_interval_seconds=1.0, slots=2, now=lambda: clock.now, sleep=clock.sleep
        )
        pacer.wait_for("a.example")
        pacer.wait_for("a.example")

        assert pacer.wait_for("a.example") == pytest.approx(1.0)

    def test_two_slots_let_through_twice_as_many_in_the_same_time(self) -> None:
        """자리 수가 실제로 밀도를 바꾸는지 — 이것이 고친 이유다."""
        one = FakeClock()
        two = FakeClock()
        serial = HostPacer(min_interval_seconds=1.0, slots=1, now=lambda: one.now, sleep=one.sleep)
        paired = HostPacer(min_interval_seconds=1.0, slots=2, now=lambda: two.now, sleep=two.sleep)

        for _ in range(6):
            serial.wait_for("a.example")
            paired.wait_for("a.example")

        assert one.now - 1000.0 == pytest.approx(5.0)
        assert two.now - 1000.0 == pytest.approx(2.0)

    def test_one_slot_behaves_exactly_as_before(self) -> None:
        """더 조여야 할 곳이 생기면 이 값 하나로 돌아갈 수 있어야 한다."""
        clock = FakeClock()
        pacer = HostPacer(
            min_interval_seconds=1.0, slots=1, now=lambda: clock.now, sleep=clock.sleep
        )
        pacer.wait_for("a.example")

        assert pacer.wait_for("a.example") == pytest.approx(1.0)

    def test_a_nonsense_slot_count_does_not_stop_the_scan(self) -> None:
        """0 이나 음수를 설정하면 아무도 통과하지 못한다 — 최소 1 로 받는다."""
        clock = FakeClock()
        pacer = HostPacer(
            min_interval_seconds=1.0, slots=0, now=lambda: clock.now, sleep=clock.sleep
        )

        assert pacer.wait_for("a.example") == 0.0

    def test_slots_are_counted_per_host(self) -> None:
        """다른 사이트를 함께 진단한다고 해서 서로의 자리를 뺏으면 안 된다."""
        clock = FakeClock()
        pacer = HostPacer(
            min_interval_seconds=1.0, slots=2, now=lambda: clock.now, sleep=clock.sleep
        )
        pacer.wait_for("a.example")
        pacer.wait_for("a.example")

        assert pacer.wait_for("b.example") == 0.0
