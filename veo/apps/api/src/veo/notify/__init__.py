"""운영 알림 — 사람이 화면을 보고 있지 않을 때 사실을 전하는 한 벌의 통로.

#45(한도 경보)가 첫 소비자다. #9(추이·회귀 알림)가 생기면 **이 통로를 재사용한다**
— 알림 경로를 두 벌 만들지 않는다(0-D). 새 알림이 필요하면 여기의 ``send_alert``
를 부르지, 발송 코드를 새로 쓰지 않는다.
"""

from veo.notify.webhook import AlertOutcome, send_alert

__all__ = ["AlertOutcome", "send_alert"]
