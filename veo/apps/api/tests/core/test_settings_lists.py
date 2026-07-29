"""환경변수로 들어온 목록형 설정을 읽는 규칙.

`cors_allowed_origins` 는 `list[str]` 이라, pydantic-settings 는 환경변수 값을 **JSON**
으로 파싱한다. 그래서 사람이 자연스럽게 쓰는 `VEO_CORS_ALLOWED_ORIGINS=https://…` 는
`SettingsError` 를 내고 **앱이 시작조차 못 한다.**

이 실패 방식이 특히 나쁜 이유: 배포 플랫폼에는 "빌드 성공 → 배포 성공 → 헬스체크 실패"
로만 보인다. 오류는 컨테이너 로그 안쪽에 있고, 겉으로는 네트워크 문제처럼 읽힌다.
실제로 2026-07-29 에 이 값 하나 때문에 Railway 배포가 10시간 동안 조용히 실패했고,
그동안 옛 배포가 계속 서비스되어 "배포는 됐는데 코드가 안 바뀐다" 로 나타났다.

그래서 파싱을 관대하게 만든다. 보안 경계인 목록을 **넓히지는 않는다** — 형식만 받아준다.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from veo.core.settings import Settings


class TestCorsAllowedOrigins:
    def test_single_bare_origin(self) -> None:
        """따옴표도 대괄호도 없이 주소 하나. 배포 화면에서 사람이 실제로 넣는 형태다."""
        settings = Settings(cors_allowed_origins="https://veo.seokorea.org")  # type: ignore[arg-type]
        assert settings.cors_allowed_origins == ["https://veo.seokorea.org"]

    def test_comma_separated(self) -> None:
        settings = Settings(  # type: ignore[arg-type]
            cors_allowed_origins="https://veo.seokorea.org, https://veo-staging.example.com"
        )
        assert settings.cors_allowed_origins == [
            "https://veo.seokorea.org",
            "https://veo-staging.example.com",
        ]

    def test_json_array_still_accepted(self) -> None:
        """이미 JSON 으로 넣어 둔 배포를 깨뜨리지 않는다."""
        settings = Settings(  # type: ignore[arg-type]
            cors_allowed_origins='["https://veo.seokorea.org"]'
        )
        assert settings.cors_allowed_origins == ["https://veo.seokorea.org"]

    def test_list_still_accepted(self) -> None:
        settings = Settings(cors_allowed_origins=["https://veo.seokorea.org"])
        assert settings.cors_allowed_origins == ["https://veo.seokorea.org"]

    def test_blank_entries_dropped(self) -> None:
        """줄바꿈이나 꼬리 쉼표가 빈 문자열을 남기면, 그건 '모든 출처' 가 아니라 실수다."""
        settings = Settings(cors_allowed_origins="https://veo.seokorea.org, ,")  # type: ignore[arg-type]
        assert settings.cors_allowed_origins == ["https://veo.seokorea.org"]

    def test_empty_string_is_rejected(self) -> None:
        """빈 값을 조용히 기본값으로 되돌리면 localhost 가 운영에 남는다."""
        with pytest.raises(ValidationError):
            Settings(cors_allowed_origins="   ")  # type: ignore[arg-type]
