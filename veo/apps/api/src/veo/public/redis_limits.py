"""여러 서버가 **하나의 한도**를 함께 센다.

인메모리 리미터는 한 프로세스 안에서만 센다. 워커가 둘이면 실효 한도가 두 배가 되고,
재배포하면 세던 것을 잊는다 — 막으려던 것을 못 막는다(기획서 E6). 그 사실은
:mod:`veo.public.limits` 가 이미 적어 두었고, 여기가 그 자리를 채운다.

**무엇을 막는가.** 공개 진단은 방문자가 시키는 대로 제3자 사이트를 가져온다. 한도가
느슨해지면 VEO 가 남의 서버를 때리는 도구가 된다. 돈 문제가 아니라 책임 문제다.

**Redis 가 죽으면 거절한다.** 통과시키면 장애 시간이 그대로 남용 창구가 되고, 그때
피해를 입는 것은 우리가 아니라 우리가 크롤하는 남의 서버다. 무료 도구가 잠시 멈추는
것과 비교할 수 없다. 이 선택은 화면에 그대로 드러난다 — "잠시 후 다시" 라는 문장이지
"당신이 너무 많이 썼다" 가 아니다.

**검사와 청구가 한 덩어리여야 한다.** 인메모리 구현이 잠금으로 지키는 그 성질을, 여기서는
Lua 스크립트로 지킨다. 여러 통을 따로 검사하고 따로 청구하면 그 사이에 다른 요청이 끼고,
둘 다 통과한다. 그리고 **하나라도 막히면 아무것도 청구하지 않는다** — 대상 호스트 통이
거절했다고 방문자 자신의 몫까지 태우면, 바쁜 피해자 사이트 하나가 애먼 방문자 전부의
한도를 조용히 소진시킨다.
"""

from __future__ import annotations

import logging
import time
from collections.abc import Callable, Sequence
from typing import Any, Final, final

from veo.public.limits import Bucket, RateLimitDecision

__all__ = ["REDIS_UNAVAILABLE_KO", "RedisRateLimiter"]

_log = logging.getLogger(__name__)

#: Redis 에 닿지 못했을 때 방문자가 보는 문장. **이유를 방문자 탓으로 적지 않는다**(0-J) —
#: 한도를 넘긴 것이 아니라 우리 쪽이 잠시 셀 수 없는 상태다.
REDIS_UNAVAILABLE_KO: Final = (
    "지금은 진단을 받을 수 없습니다. 잠시 후 다시 시도해 주십시오."
)

#: 닿지 못했을 때 안내할 대기 시간(초). 장애가 길어질 수 있으므로 짧게 잡지 않는다.
_UNAVAILABLE_RETRY_AFTER: Final = 30

#: 검사와 청구를 한 번에. 하나라도 막히면 **아무것도 청구하지 않고** 그 통을 알려준다.
#:
#: KEYS  = 통 키들
#: ARGV  = now_ms, member, 그리고 통마다 (limit, window_ms)
#:
#: 슬라이딩 창을 정렬 집합으로 센다: 창 밖의 점수를 지우고, 남은 개수를 본다. 고정 창이면
#: :59 에 한도를 다 쓰고 :01 에 또 다 쓸 수 있다.
_ACQUIRE_LUA: Final = """
local now = tonumber(ARGV[1])
local member = ARGV[2]

-- 1단계: 전부 검사한다. 하나라도 막히면 아무것도 청구하지 않는다.
for i = 1, #KEYS do
  local limit = tonumber(ARGV[2 + (i - 1) * 2 + 1])
  local window = tonumber(ARGV[2 + (i - 1) * 2 + 2])
  redis.call('ZREMRANGEBYSCORE', KEYS[i], '-inf', now - window)
  local used = redis.call('ZCARD', KEYS[i])
  if used >= limit then
    local oldest = redis.call('ZRANGE', KEYS[i], 0, 0, 'WITHSCORES')
    local wait = 0
    if oldest[2] then
      wait = math.ceil((tonumber(oldest[2]) + window - now) / 1000)
      if wait < 1 then wait = 1 end
    end
    return {i, wait}
  end
end

-- 2단계: 전부 통과했으니 전부 청구한다.
for i = 1, #KEYS do
  local window = tonumber(ARGV[2 + (i - 1) * 2 + 2])
  redis.call('ZADD', KEYS[i], now, member)
  -- 창보다 오래 살아 있을 이유가 없다. 만료를 걸어 두면 버려진 키가 쌓이지 않는다.
  redis.call('PEXPIRE', KEYS[i], window)
end
return {0, 0}
"""


@final
class RedisRateLimiter:
    """:class:`veo.public.limits.RateLimiter` 의 Redis 구현.

    계약이 같으므로 부르는 쪽은 어느 것이 끼워졌는지 알지 못한다 — 인메모리를 이것으로
    바꾸는 일이 배선 한 줄이어야, 시험은 인메모리로 빠르게 돌고 운영은 이것으로 돈다.
    """

    __slots__ = ("_client", "_clock", "_prefix", "_script")

    def __init__(
        self,
        client: Any,
        *,
        prefix: str = "veo:ratelimit",
        clock: Callable[[], float] = time.time,
    ) -> None:
        self._client = client
        self._prefix = prefix
        # 벽시계를 쓴다 — `monotonic` 은 프로세스마다 기준이 달라서, 여러 서버가 같은
        # 창을 공유해야 하는 이 자리에서는 쓸 수 없다.
        self._clock = clock
        self._script = client.register_script(_ACQUIRE_LUA)

    def acquire(
        self, buckets: Sequence[Bucket], *, now: float | None = None
    ) -> RateLimitDecision:
        if not buckets:
            return RateLimitDecision.allow()

        moment_ms = int((self._clock() if now is None else now) * 1000)
        keys = [f"{self._prefix}:{bucket.scope}:{bucket.key}" for bucket in buckets]
        # 같은 요청의 여러 통에 같은 표식을 쓴다 — 정렬 집합은 같은 값을 덮어쓰므로,
        # 통마다 달라야 각 통이 자기 몫을 센다. 시각을 섞어 충돌을 피한다.
        args: list[Any] = [moment_ms, f"{moment_ms}-{id(buckets):x}"]
        for bucket in buckets:
            args.extend([bucket.limit, bucket.window_seconds * 1000])

        try:
            refused_index, wait = self._script(keys=keys, args=args)
        except Exception:
            # 닿지 못하면 **거절한다.** 통과시키면 장애 시간이 그대로 남용 창구가 되고,
            # 그 피해는 우리가 아니라 우리가 크롤하는 남의 서버가 입는다.
            _log.warning("rate limiter backend unavailable; refusing", exc_info=True)
            return RateLimitDecision(
                allowed=False,
                scope=buckets[0].scope,
                retry_after_seconds=_UNAVAILABLE_RETRY_AFTER,
                message_ko=REDIS_UNAVAILABLE_KO,
                limit=buckets[0].limit,
                window_seconds=buckets[0].window_seconds,
            )

        index = int(refused_index)
        if index == 0:
            return RateLimitDecision.allow()

        refused = buckets[index - 1]
        return RateLimitDecision.refuse(refused, retry_after_seconds=max(int(wait), 1))
