"""웹훅 한 개로 보내는 운영 알림.

## 왜 웹훅인가

받는 곳을 고르지 않기 위해서다. 슬랙·디스코드·잔디 전부 "URL 로 JSON 을 받으면
채팅에 띄우는" 수신기를 제공하고, 페이로드의 ``text`` 필드는 그중 가장 널리 통하는
모양이다. 메일 서버·푸시 인증서 같은 별도 기반 없이, 운영자가 URL 하나만 넣으면
알림이 산다.

## 정직성 규칙

- URL 이 설정에 없으면 **비활성**이다 — 보낸 척하지 않고 ``DISABLED`` 를 돌려준다.
  화면·로그 어느 쪽도 "알림을 보냈다" 고 말할 근거가 없다(0-E).
- 발송 실패는 삼키고 로그에 남긴다. 알림은 부가 기능이고, 알림이 죽었다고 본업
  (진단·기록)이 죽으면 안 된다. 단, 삼킨 사실은 반드시 로그로 남는다 — 조용한
  실패는 "알림이 잘 오고 있다" 는 착각을 만든다.
- URL 은 https 만 받는다. 웹훅 URL 에는 토큰이 들어 있고(슬랙 형식이 그렇다),
  평문 http 로 보내면 그 토큰이 경로에 노출된다.
"""

from __future__ import annotations

import logging
from enum import StrEnum
from typing import Final

import httpx

from veo.core.settings import Settings, get_settings

__all__ = ["AlertOutcome", "send_alert"]

_log = logging.getLogger(__name__)

#: 알림 하나에 이 이상 기다리지 않는다. 발송은 요청 처리 도중에 일어나므로,
#: 웹훅 수신기가 느리다고 고객 응답이 그만큼 늦어져서는 안 된다.
_TIMEOUT_SECONDS: Final = 3.0


class AlertOutcome(StrEnum):
    SENT = "SENT"
    DISABLED = "DISABLED"  # URL 미설정 — 보낼 곳이 없다
    FAILED = "FAILED"  # 보내려 했으나 실패 — 로그에 남아 있다


def send_alert(
    *,
    title_ko: str,
    body_ko: str,
    source: str,
    settings: Settings | None = None,
    client: httpx.Client | None = None,
) -> AlertOutcome:
    """알림 하나를 보낸다. 결과는 셋 중 하나이고, 예외는 밖으로 나가지 않는다.

    ``source`` 는 어느 기능이 보냈는가다("usage.quota" 등). 수신 채널에서 알림이
    섞일 때 출처 없이는 어느 코드가 보냈는지 찾으러 다니게 된다.
    """
    resolved = settings or get_settings()
    secret = resolved.alert_webhook_url
    if secret is None:
        return AlertOutcome.DISABLED

    url = secret.get_secret_value()
    if not url.startswith("https://"):
        _log.error("alert webhook URL is not https; refusing to send (source=%s)", source)
        return AlertOutcome.FAILED

    payload = {"text": f"*{title_ko}*\n{body_ko}\n_({source})_"}
    try:
        if client is not None:
            response = client.post(url, json=payload, timeout=_TIMEOUT_SECONDS)
        else:
            response = httpx.post(url, json=payload, timeout=_TIMEOUT_SECONDS)
        response.raise_for_status()
    except Exception:
        _log.exception("alert delivery failed (source=%s, title=%s)", source, title_ko)
        return AlertOutcome.FAILED
    return AlertOutcome.SENT
