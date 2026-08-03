"""진단이 어느 단계에서 시간을 쓰는가.

**왜 필요한가.** 진단 한 번이 180초 걸린다는 것은 알았는데, 그 안의 내역은 알 수 없었다.
알아내려고 2026-08-03 에 크롤러를 따로 돌려 재야 했다 — 준비 5.7초, 수집 41초, 나머지
약 130초가 구글 성능 측정. 그런 도구가 코드 안에 없어서, 다음에 느려지면 또 처음부터
재게 된다. 그리고 무엇을 고쳤을 때 **실제로 빨라졌는지** 확인할 근거도 없다.

그래서 단계마다 시간을 남긴다. 남기는 곳은 이미 있는 메트릭 싱크(`veo.observability`)
하나뿐이다 — 로그와 메트릭 두 벌로 적으면 둘이 어긋나는 날이 온다(0-D).

**측정이 측정 대상을 느리게 만들면 본말전도다.** 여기서 하는 일은 `time.monotonic()`
두 번과 싱크에 숫자 하나 넘기는 것뿐이다. 실패해도 진단을 멈추지 않는다 — 시간을 못
적는 것과 진단이 죽는 것은 비교할 수 없다.

`monotonic` 을 쓰는 이유: 벽시계는 NTP 보정으로 뒤로 갈 수 있고, 그러면 음수 소요가
나온다. 그것은 "빨랐다" 가 아니라 "시계가 움직였다" 인데 구분되지 않는다.
"""

from __future__ import annotations

import logging
import time
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Final

from veo.observability import get_metric_sink

__all__ = ["SCAN_STAGE_METRIC", "ScanTimings", "stage"]

_log = logging.getLogger(__name__)

#: 단계별 소요(밀리초). 이름은 관측 패키지 규약(`veo_*`)을 따른다.
SCAN_STAGE_METRIC: Final = "veo_scan_stage_duration_ms"


class ScanTimings:
    """한 번의 진단이 단계마다 쓴 시간.

    메트릭으로 나가는 것과 **별개로** 값을 들고 있다. 메트릭은 여러 진단이 뒤섞인
    분포라 "이번 진단이 왜 느렸나" 에는 답하지 못한다 — 그 답은 이 객체가 한다.
    """

    __slots__ = ("_elapsed_ms",)

    def __init__(self) -> None:
        self._elapsed_ms: dict[str, float] = {}

    def record(self, name: str, elapsed_ms: float) -> None:
        # 같은 단계가 두 번 돌면 더한다. 덮어쓰면 앞의 시간이 사라지는데, 그것도
        # 실제로 쓴 시간이다.
        self._elapsed_ms[name] = self._elapsed_ms.get(name, 0.0) + elapsed_ms

    @property
    def elapsed_ms(self) -> dict[str, float]:
        return dict(self._elapsed_ms)

    @property
    def total_ms(self) -> float:
        return sum(self._elapsed_ms.values())

    def summary_ko(self) -> str:
        """사람이 읽는 한 줄. 큰 것부터 — 고칠 곳이 앞에 온다."""
        if not self._elapsed_ms:
            return "단계별 시간 기록 없음"
        ordered = sorted(self._elapsed_ms.items(), key=lambda item: -item[1])
        parts = [f"{name} {ms / 1000:.1f}초" for name, ms in ordered]
        return " · ".join(parts)


@contextmanager
def stage(name: str, timings: ScanTimings | None = None) -> Iterator[None]:
    """이 블록이 쓴 시간을 단계 이름으로 남긴다.

    블록이 예외로 끝나도 **시간은 남긴다**. 실패한 단계가 얼마나 붙들고 있었는지가
    오히려 알고 싶은 값이다 — 조용히 버리면 "왜 3분이나 걸리고 실패했나" 에 답할 수 없다.
    """
    started = time.monotonic()
    try:
        yield
    finally:
        elapsed_ms = (time.monotonic() - started) * 1000
        if timings is not None:
            timings.record(name, elapsed_ms)
        try:
            get_metric_sink().observe(SCAN_STAGE_METRIC, elapsed_ms, {"stage": name})
        except Exception:
            # 시간을 못 적는 것과 진단이 죽는 것은 비교할 수 없다. 다만 **조용히**
            # 넘기지는 않는다 — 그래프가 비어 있는데 이유를 모르면, 안 잰 것과 못 잰
            # 것이 섞인다.
            _log.warning("scan stage timing was not recorded: %s", name, exc_info=True)
