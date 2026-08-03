"""초대 링크에 박히는 주소.

`console_base_url` 의 기본값은 개발자 컴퓨터(`http://localhost:3000`)다. 운영에서 그 값이
그대로 쓰이면 `http://localhost:3000/invite/…` 가 발급된다 — 복사도 되고 생김새도 멀쩡한데
받는 사람에게는 열리지 않는 주소다. 게다가 토큰은 1회용이라, 그 초대는 이미 소모된 뒤다.
관리자는 "링크를 보냈는데 안 열린다" 는 말을 듣고 재발송을 누를 뿐, 원인은 끝까지 모른다.

그래서 운영에서는 링크를 만들지 않고 거절한다. 거절 문구는 무엇을 설정해야 하는지
(`VEO_CONSOLE_BASE_URL`) 를 이름째 말한다.
"""

from __future__ import annotations

import pytest

from veo.core.settings import ConsoleBaseUrlNotSet, Settings


def _settings(environment: str, console_base_url: str) -> Settings:
    return Settings(  # type: ignore[call-arg]
        environment=environment,  # type: ignore[arg-type]
        console_base_url=console_base_url,
    )


class TestProductionRefusesLoopback:
    @pytest.mark.parametrize(
        "origin",
        [
            "http://localhost:3000",
            "https://localhost",
            "http://127.0.0.1:3000",
            "http://0.0.0.0:8000",
            "",
        ],
    )
    def test_refused(self, origin: str) -> None:
        """서버 자신에게만 닿는 주소는 링크가 될 수 없다 — 포트가 달라도 같은 실수다."""
        with pytest.raises(ConsoleBaseUrlNotSet) as caught:
            _settings("production", origin).invitation_base_url()

        # 문구가 변수 이름을 말해야 관리자가 스스로 고칠 수 있다.
        assert "VEO_CONSOLE_BASE_URL" in str(caught.value)

    def test_real_origin_passes(self) -> None:
        settings = _settings("production", "https://veo.seokorea.org")
        assert settings.invitation_base_url() == "https://veo.seokorea.org"

    def test_whitespace_is_trimmed(self) -> None:
        """배포 화면에 붙여넣은 값에는 공백이 따라오기 쉽다."""
        settings = _settings("production", "  https://veo.seokorea.org  ")
        assert settings.invitation_base_url() == "https://veo.seokorea.org"


class TestLocalKeepsWorking:
    @pytest.mark.parametrize("environment", ["local", "test", "staging"])
    def test_loopback_allowed_off_production(self, environment: str) -> None:
        """개발자 컴퓨터에서는 localhost 가 옳은 값이다. 여기서 막으면 개발이 멈춘다."""
        settings = _settings(environment, "http://localhost:3000")
        assert settings.invitation_base_url() == "http://localhost:3000"
