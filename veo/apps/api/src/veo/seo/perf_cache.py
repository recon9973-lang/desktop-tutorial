"""한 번의 진단 **안에서만** 성능 측정을 나눠 쓴다.

**진단과 진단 사이에는 절대 재사용하지 않는다.** 처음에는 6시간 동안 기억해 두려 했는데,
그것은 이 도구의 목적을 정면으로 막는다 — 담당자는 사이트를 고치고 **다시 재서 확인하려고**
진단을 누른다. 그 순간 옛 값을 돌려주면, 고쳤는데 점수가 그대로인 화면을 보게 되고
"고쳐도 안 바뀌네" 라는 잘못된 결론에 이른다. 빨라진 대가로 도구가 거짓말을 하는 것이라
어떤 시간 단축과도 바꿀 수 없다(사용자 지적: "수정후 확인이 안됨").

그래서 남은 쓸모는 하나다. **같은 진단 안에서** 대표 주소를 크롤과 동시에 재 두고
(:func:`veo.seo.measure_performance.prewarm`), 표본 측정이 몇십 초 뒤 그 값을 집어 간다.
같은 진단 안의 두 시점이므로 그 사이에 사이트가 바뀌었을 리 없다.

수명이 아니라 **범위**로 안전을 만든다: 이 객체는 진단 하나가 만들고 진단이 끝나면
버려진다. 전역 기억이 없으니 옛 값이 살아남을 자리 자체가 없다.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

__all__ = ["CachedMeasurement", "PerformanceCache"]


@dataclass(frozen=True, slots=True)
class CachedMeasurement:
    """기억해 둔 한 건과, 언제 잰 것인지."""

    value: Any
    measured_at: datetime

    def age_seconds(self, *, now: datetime) -> float:
        return (now - self.measured_at).total_seconds()


class PerformanceCache:
    """진단 하나가 쓰는 임시 기억.

    스레드에서 부른다 — 미리 재기가 배경에서 돌고 표본 측정이 본류에서 읽는다.

    **전역 기본 객체를 두지 않는다.** 두는 순간 진단과 진단 사이에 값이 넘어가고,
    고친 뒤 다시 재는 사람이 옛 값을 보게 된다. 쓰는 쪽이 자기 것을 만들어 쓴다.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._entries: dict[tuple[str, str], CachedMeasurement] = {}

    def get(
        self, url: str, strategy: str, *, now: datetime | None = None
    ) -> CachedMeasurement | None:
        del now  # 수명이 없다 — 이 객체가 사는 동안은 전부 이번 진단의 값이다.
        with self._lock:
            return self._entries.get((url, strategy))

    def put(self, url: str, strategy: str, value: Any, *, now: datetime | None = None) -> None:
        moment = now or datetime.now(UTC)
        with self._lock:
            self._entries[(url, strategy)] = CachedMeasurement(value=value, measured_at=moment)

    def clear(self) -> None:
        with self._lock:
            self._entries.clear()

    def size(self) -> int:
        with self._lock:
            return len(self._entries)
