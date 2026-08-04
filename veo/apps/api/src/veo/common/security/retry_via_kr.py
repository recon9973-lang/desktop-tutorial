"""직접 받고, **관문 페이지면** 한국에서 한 번 더 받는다.

`SafeFetcher` 와 같은 모양(`fetch(url)`)이라 부르는 쪽은 바뀌지 않는다. 크롤러도 공개
진단도 조립할 때 이것으로 감싸기만 하면 된다.

**언제 다시 받는가.** `collect.readable.looks_like_interstitial` 이 참일 때만이다. 즉
스크립트뿐인 작은 응답 — 실측한 759·760바이트가 그것이다. 잘 받아지는 사이트는 한
걸음도 더 가지 않는다: 실측에서 거래처 4곳 중 2곳만 이 검사를 받았고, 나머지 둘은
싱가포르에서도 정상이었다.

**다시 받아도 안 되면 원래 응답을 쓴다.** 경유가 실패한 것은 대상 사이트의 사실이
아니므로 판정을 바꾸지 않는다. 그때 원래 응답은 `readable` 관문에 걸려 "수집 실패" 로
보고된다 — 있는 그대로다(0-K).
"""

from __future__ import annotations

import logging

from veo.collect.readable import looks_like_interstitial
from veo.common.security.egress_kr import KoreanEgress, KoreanEgressUnavailable
from veo.common.security.fetcher import FetchedDocument, SafeFetcher
from veo.observability import get_metric_sink

__all__ = ["EGRESS_KR_METRIC", "RetryViaKorea"]

_log = logging.getLogger(__name__)

#: 경유가 몇 번 일어났고 어떻게 끝났는가. 이름은 관측 패키지 규약(`veo_*`)을 따른다.
EGRESS_KR_METRIC = "veo_egress_kr_total"


class RetryViaKorea:
    """`SafeFetcher` 를 감싸, 관문 페이지를 만나면 한국에서 다시 받는다."""

    __slots__ = ("_direct", "_egress")

    def __init__(self, direct: SafeFetcher, *, egress: KoreanEgress | None) -> None:
        self._direct = direct
        self._egress = egress

    def fetch(self, url: str, *, method: str = "GET") -> FetchedDocument:
        document = self._direct.fetch(url, method=method)

        if self._egress is None or method != "GET":
            return document
        if not looks_like_interstitial(document.body):
            return document

        try:
            through_korea = self._egress.fetch(url)
        except KoreanEgressUnavailable:
            # 경유 실패는 **대상 사이트의 사실이 아니다.** 원래 응답을 그대로 돌려주면
            # `readable` 관문이 "수집 실패" 로 보고한다. 조용히 넘기지는 않는다.
            _log.warning("한국 관측점으로 다시 받지 못했습니다: %s", url, exc_info=True)
            _observe("unavailable")
            return document

        if looks_like_interstitial(through_korea.body):
            # 한국에서도 관문이 나왔다 — 위치 문제가 아니라는 사실 자체가 관측이다.
            _observe("still_blocked")
            return through_korea

        _observe("recovered")
        return through_korea


def _observe(outcome: str) -> None:
    try:
        get_metric_sink().observe(EGRESS_KR_METRIC, 1.0, {"outcome": outcome})
    except Exception:
        _log.warning("경유 결과를 기록하지 못했습니다: %s", outcome, exc_info=True)
