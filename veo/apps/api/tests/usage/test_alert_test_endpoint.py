"""경보가 닿는지 **확인할 길**이 있다.

## 왜 이 창구가 있나

경보는 사고가 났을 때만 울린다. 그래서 알림 주소를 넣은 사람이 **맞는지 확인할 방법이
없었다** — 잘못 넣어 두면 정작 필요한 날 조용하고, 그날까지 아무도 모른다.

사장님께 "Railway 에 이 값을 넣으십시오" 라고 안내하면서 **"성공하면 무엇이 보이는가"
를 말할 수 없었다.** 그것이 이 창구가 생긴 이유다.

## 지키는 것

**주소를 응답에 싣지 않는다.** 사람이 알아야 하는 것은 닿았는지 여부뿐이고, 주소를
화면에 실으면 그 화면을 열 수 있는 사람 모두가 그것을 갖는다.

**실제 경보와 같은 통로로 보낸다.** 시험용 우회로를 따로 두면 그 우회로만 동작하는
상태를 못 잡는다 — 확인했다는 착각이 확인하지 않은 것보다 나쁘다.
"""

from __future__ import annotations

import pathlib

import pytest

pytest.importorskip("pydantic")

from veo.notify import AlertOutcome
from veo.usage.schemas import AlertTestPayload


def router_source() -> str:
    from veo.usage import router

    return pathlib.Path(router.__file__).read_text(encoding="utf-8")


class TestTheAddressNeverLeaves:
    def test_the_payload_has_no_place_for_it(self) -> None:
        assert set(AlertTestPayload.model_fields) == {"outcome", "message_ko"}

    def test_the_router_never_reads_the_secret(self) -> None:
        """`get_secret_value()` 가 여기 있으면 주소가 응답으로 새는 길이 생긴다."""
        assert "get_secret_value" not in router_source()
        assert "alert_webhook_url" not in router_source()


class TestItUsesTheRealChannel:
    def test_it_calls_send_alert(self) -> None:
        assert "send_alert(" in router_source()

    def test_it_says_it_is_a_test(self) -> None:
        """받는 사람이 진짜 사고로 오해하면 안 된다."""
        assert "시험 발송" in router_source()

    def test_it_names_its_source(self) -> None:
        assert 'source="usage.alert_test"' in router_source()


class TestEveryOutcomeTellsTheReaderWhatToDo:
    def test_all_three_have_a_sentence(self) -> None:
        from veo.usage.router import _ALERT_MESSAGES_KO

        for outcome in AlertOutcome:
            assert outcome in _ALERT_MESSAGES_KO, f"{outcome} 에 할 말이 없다"
            assert _ALERT_MESSAGES_KO[outcome].strip()

    def test_disabled_names_the_variable_to_set(self) -> None:
        """"설정 안 됨" 만 말하면 사람이 어디를 고쳐야 하는지 모른다."""
        from veo.usage.router import _ALERT_MESSAGES_KO

        assert "VEO_ALERT_WEBHOOK_URL" in _ALERT_MESSAGES_KO[AlertOutcome.DISABLED]

    def test_sent_does_not_promise_delivery(self) -> None:
        """보낸 것과 도착한 것은 다르다. 채널이 지워졌으면 200 을 받고도 안 보인다."""
        from veo.usage.router import _ALERT_MESSAGES_KO

        assert "확인해" in _ALERT_MESSAGES_KO[AlertOutcome.SENT]


class TestItIsBehindAPermission:
    def test_only_usage_readers_can_send(self) -> None:
        """아무나 누르면 남의 채널로 메시지를 쏘는 단추가 된다."""
        assert "UsageReader" in router_source()
