"""시험이 진짜 바깥으로 나가지 않는지 시험이 지킨다.

2026-08-06 실측으로 잡혔다. 설정은 `apps/api/.env` 를 자동으로 읽고, 개발 장비의 그
파일에는 한국 경유 주소와 열쇠가 들어 있다. 그래서 모의 전송에 428바이트를 넣어 둔
시뮬레이션이 **실제 남의 사이트 본문 559바이트**를 받아 왔다 — `RetryViaKorea` 가
발동했고, 그 경로는 `SafeFetcher` 에 주입한 transport 를 쓰지 않기 때문이다.

`.env` 가 없는 CI 에서는 안 나갔다. 즉 **로컬과 CI 가 다르게 동작**했고, 그 상태에서는
"시험 통과" 가 아무것도 보증하지 않는다(0-F). 규칙을 적어 두는 것으로는 부족하다 —
규칙에는 그것을 지키는 검사가 있어야 한다(0-H).
"""

from __future__ import annotations

from veo.core.settings import get_settings


def test_the_korean_egress_is_off_in_the_suite() -> None:
    """켜져 있으면 시험이 조용히 인터넷을 다녀온다."""
    settings = get_settings()

    assert settings.egress_kr_is_configured() is False, (
        "시험에서 한국 경유가 켜져 있습니다. conftest 가 끄는데도 켜졌다면 "
        "무언가가 그 값을 되살린 것입니다 — 그대로 두면 시험이 실제 외부 서버로 나갑니다."
    )
