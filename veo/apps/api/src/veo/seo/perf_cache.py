"""성능 측정 결과를 잠시 기억한다.

**왜 필요한가.** 진단 한 번에 180초가 걸리는데 그중 약 130초가 구글 PageSpeed 를
기다리는 시간이다(2026-08-03 실측: 크롤 172장 47초, 나머지가 성능). 구글은 그 페이지를
실제로 브라우저로 열어 재기 때문에 한 장에 20~60초가 정상이고, 우리가 빠르게 만들 수
있는 부분이 아니다. 줄일 수 있는 것은 **같은 값을 두 번 재지 않는 것**뿐이다.

두 가지를 이 캐시 하나로 푼다.

1. **같은 진단 안에서** — 대표 주소는 크롤이 시작되는 순간 이미 안다. 크롤이 끝나기를
   기다릴 이유가 없어서, 크롤과 동시에 재서 여기 넣어 둔다. 표본 측정이 그 값을 그대로
   집어 간다.
2. **진단과 진단 사이** — 같은 페이지를 몇 분 뒤 다시 재도 값은 거의 같다. 구글의
   현장 데이터(CrUX)는 하루 단위로만 갱신된다.

**한계를 분명히 한다.** 이 기억은 프로세스 안에만 있다. 서버가 다시 뜨면 비고, 여러 대로
늘리면 서버마다 따로 논다. 그래도 정기 재진단 청소와 연달아 도는 진단은 대부분 한
프로세스 안에서 일어나므로 효과가 있다. DB 로 옮기는 것은 그때 가서 할 일이고, 지금
없는 것을 있는 척하지 않기 위해 여기 적어 둔다.

**오래된 값을 조용히 쓰지 않는다.** 수명이 지난 값은 없는 것으로 친다. 캐시가 값을 준
경우 언제 잰 것인지도 함께 주므로, 부르는 쪽이 그 사실을 결과에 실을 수 있다.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any, Final

__all__ = ["PERFORMANCE_CACHE", "CachedMeasurement", "PerformanceCache"]

#: 값을 믿는 기간. 구글의 현장 데이터가 하루 단위로 갱신되므로 그보다 짧게 잡는다 —
#: 사이트를 고치고 바로 다시 재는 담당자가 옛 값을 보면 안 된다.
DEFAULT_TTL: Final = timedelta(hours=6)

#: 한 프로세스가 기억할 최대 개수. 넘으면 오래된 것부터 버린다 — 거래처가 늘어도
#: 메모리가 무한정 자라지 않게.
DEFAULT_MAX_ENTRIES: Final = 500


@dataclass(frozen=True, slots=True)
class CachedMeasurement:
    """기억해 둔 한 건과, **언제 잰 것인지**."""

    value: Any
    measured_at: datetime

    def age_seconds(self, *, now: datetime) -> float:
        return (now - self.measured_at).total_seconds()


class PerformanceCache:
    """URL 하나의 측정 결과를 수명이 다할 때까지 기억한다.

    스레드에서 부른다(크롤과 성능 측정이 동시에 돈다). 잠금은 한 곳에만 두고 짧게 잡는다.
    """

    def __init__(
        self,
        *,
        ttl: timedelta = DEFAULT_TTL,
        max_entries: int = DEFAULT_MAX_ENTRIES,
    ) -> None:
        self._ttl = ttl
        self._max_entries = max_entries
        self._lock = threading.Lock()
        self._entries: dict[tuple[str, str], CachedMeasurement] = {}

    def get(
        self, url: str, strategy: str, *, now: datetime | None = None
    ) -> CachedMeasurement | None:
        """살아 있는 값만 돌려준다. 수명이 지났으면 없는 것과 같다."""
        moment = now or datetime.now(UTC)
        key = (url, strategy)
        with self._lock:
            entry = self._entries.get(key)
            if entry is None:
                return None
            if moment - entry.measured_at > self._ttl:
                # 오래된 값은 여기서 버린다 — 다음 사람이 다시 판단하지 않게.
                del self._entries[key]
                return None
            return entry

    def put(self, url: str, strategy: str, value: Any, *, now: datetime | None = None) -> None:
        moment = now or datetime.now(UTC)
        key = (url, strategy)
        with self._lock:
            self._entries[key] = CachedMeasurement(value=value, measured_at=moment)
            if len(self._entries) > self._max_entries:
                # 가장 오래 전에 잰 것부터 버린다.
                oldest = min(self._entries, key=lambda k: self._entries[k].measured_at)
                del self._entries[oldest]

    def clear(self) -> None:
        with self._lock:
            self._entries.clear()

    def size(self) -> int:
        with self._lock:
            return len(self._entries)


#: 프로세스 하나가 함께 쓰는 기억. 시험은 자기 것을 만들어 쓴다 — 전역을 건드리면
#: 시험끼리 서로의 값을 보게 되고, 그때부터 실패가 순서에 따라 달라진다.
PERFORMANCE_CACHE: Final = PerformanceCache()
