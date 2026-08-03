"""진단이 어느 단계에서 시간을 쓰는가 — 기록이 남는가.

2026-08-03 에 "진단이 180초 걸린다" 는 말에 답하려다, 그 안의 내역이 코드 어디에도
남지 않는다는 것을 알았다. 크롤러를 따로 돌려 재야 했고, 다음에 느려지면 또 처음부터
재게 된다. 고친 뒤 **실제로 빨라졌는지** 확인할 근거도 없었다.

여기서 지키는 것 셋:

1. 단계마다 시간이 남는다.
2. **실패한 단계도** 시간이 남는다 — "왜 3분이나 걸리고 실패했나" 에 답해야 한다.
3. 기록이 실패해도 **진단은 계속된다** — 시간을 못 적는 것과 진단이 죽는 것은 비교할
   수 없다.
"""

from __future__ import annotations

import pytest

from veo.seo.timing import ScanTimings, stage


class TestItRemembersEachStage:
    def test_a_stage_leaves_its_time(self) -> None:
        timings = ScanTimings()

        with stage("수집", timings):
            pass

        assert "수집" in timings.elapsed_ms
        assert timings.elapsed_ms["수집"] >= 0

    def test_stages_add_up(self) -> None:
        timings = ScanTimings()

        with stage("수집", timings):
            pass
        with stage("채점", timings):
            pass

        assert set(timings.elapsed_ms) == {"수집", "채점"}
        assert timings.total_ms == pytest.approx(
            timings.elapsed_ms["수집"] + timings.elapsed_ms["채점"]
        )

    def test_the_same_stage_twice_is_summed_not_replaced(self) -> None:
        """덮어쓰면 앞의 시간이 사라지는데, 그것도 실제로 쓴 시간이다."""
        timings = ScanTimings()
        timings.record("수집", 100.0)
        timings.record("수집", 50.0)

        assert timings.elapsed_ms["수집"] == 150.0


class TestAFailedStageStillLeavesItsTime:
    def test_the_exception_passes_through(self) -> None:
        timings = ScanTimings()

        with pytest.raises(RuntimeError):
            with stage("성능 측정", timings):
                raise RuntimeError("구글이 답하지 않음")

        # 예외는 그대로 올라가되, 붙들고 있던 시간은 남는다.
        assert "성능 측정" in timings.elapsed_ms


class TestTheSummaryPutsTheSlowestFirst:
    def test_biggest_first(self) -> None:
        """고칠 곳이 앞에 와야 한 줄만 읽고도 어디를 볼지 안다."""
        timings = ScanTimings()
        timings.record("수집", 41_000.0)
        timings.record("성능 측정", 130_000.0)
        timings.record("채점", 900.0)

        summary = timings.summary_ko()

        assert summary.startswith("성능 측정 130.0초")
        assert summary.index("수집") < summary.index("채점")

    def test_nothing_measured_says_so(self) -> None:
        """빈 문자열을 돌려주면 화면에 빈칸이 남고, 안 잰 것인지 0초인지 알 수 없다."""
        assert ScanTimings().summary_ko() == "단계별 시간 기록 없음"


class TestRecordingFailureDoesNotStopTheScan:
    def test_a_broken_sink_is_survivable(self, monkeypatch: pytest.MonkeyPatch) -> None:
        class Broken:
            def observe(self, *_args: object, **_kwargs: object) -> None:
                raise RuntimeError("싱크 고장")

        monkeypatch.setattr("veo.seo.timing.get_metric_sink", lambda: Broken())
        timings = ScanTimings()

        # 터지지 않는다. 그리고 이번 진단의 기록은 그대로 남는다.
        with stage("수집", timings):
            pass

        assert "수집" in timings.elapsed_ms
