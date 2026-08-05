"""같은 호스트에 너무 몰아치지 않는다.

**부하는 우리 편의가 아니라 상대 서버 기준으로 정한다.** 작업의뢰서 §5.2 가 정한 값은
동일 호스트 **최소 1초 간격, 동시 연결 2 이하**다.

2026-08-06 실측: 우리는 동시 4로 간격 없이 돌고 있었다. venomad.com 131장을 **2.5초**에
받아 갔다 — 장당 0.019초다. 우리 쪽 속도로는 좋은 숫자이지만, 그 서버 입장에서는 1초에
50번 두드린 것이다. 진단은 사이트 소유자가 의뢰한 일이지만, 그렇다고 남의 서버를 그렇게
써도 된다는 뜻은 아니다.

호스트 시간당 총량(`HostBudgetGuard`)과는 **다른 것을 막는다** — 저것은 한 시간의 총량,
이것은 한순간의 밀도다. 총량만 있으면 450회를 1분에 몰아 쓸 수 있다.

간격은 **요청을 보내기 직전**에 적용한다. 미리 계산해 두면 실제로 나가는 시점과
어긋나고, 재시도·리다이렉트가 그 계산 밖으로 샌다.
"""

from __future__ import annotations

import threading
import time
from collections.abc import Callable

__all__ = ["HostPacer"]


class HostPacer:
    """호스트별로 마지막 요청 시각을 기억해, 최소 간격이 지날 때까지 기다린다.

    스레드 안전하다. 콘솔 크롤은 여러 스레드가 동시에 도는데, 잠금 없이 두면 두
    스레드가 같은 "마지막 시각" 을 보고 함께 통과한다 — 그러면 간격이 없는 것과 같다.

    **한 프로세스 안에서만 유효하다.** 서버가 여러 대로 늘면 각 대가 따로 셈하므로 실제
    간격은 1/N 로 줄어든다. 그때는 `HostBudgetGuard` 처럼 Redis 로 옮겨야 한다 —
    지금은 API 가 한 대이고(실측), 늘리는 시점에 함께 옮긴다.
    """

    __slots__ = ("_last", "_lock", "_min_interval", "_now", "_sleep")

    def __init__(
        self,
        *,
        min_interval_seconds: float,
        now: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self._min_interval = max(0.0, min_interval_seconds)
        self._last: dict[str, float] = {}
        self._lock = threading.Lock()
        self._now = now
        self._sleep = sleep

    def wait_for(self, host: str) -> float:
        """이 호스트에 지금 요청해도 되는 시점까지 기다린다. 기다린 시간(초)을 돌려준다.

        돌려주는 값은 시험과 관측을 위한 것이다 — 얼마나 참았는지 알 수 없으면 이
        장치가 실제로 동작하는지 확인할 방법이 없다(0-F).
        """
        if self._min_interval <= 0.0 or not host:
            return 0.0

        with self._lock:
            now = self._now()
            earliest = self._last.get(host)
            if earliest is None:
                # 이 호스트의 첫 요청은 기다리지 않는다. 기다릴 이유가 없다.
                self._last[host] = now
                return 0.0
            target = earliest + self._min_interval
            if target <= now:
                self._last[host] = now
                return 0.0
            # **자리를 먼저 잡고 잠금을 놓는다.** 잠금을 쥔 채 자면 다른 호스트로 가는
            # 요청까지 멈춘다. 자리를 잡아 두면 뒤따르는 스레드는 그 뒤로 줄을 선다.
            self._last[host] = target
            waited = target - now

        self._sleep(waited)
        return waited
